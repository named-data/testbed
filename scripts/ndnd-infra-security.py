#!/usr/bin/env python3
"""Provision NDNd service keychains using the testbed certificate authorities."""

import argparse
import base64
from datetime import datetime, timedelta, timezone
import fcntl
import hashlib
import os
from pathlib import Path
import secrets
import subprocess
import tempfile
import time
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from Cryptodome.PublicKey import ECC, RSA
import yaml
from ndn.app_support.security_v2 import new_cert, parse_certificate
from ndn.encoding import Component, ContentType, MetaInfo, Name, SignatureType, make_data, parse_data
from ndn.security import Sha256WithEcdsaSigner
from ndn.security.validator import verify_ecdsa, verify_ed25519, verify_rsa


def decode_certificate(path):
    return base64.b64decode(''.join(path.read_text().split()), validate=True)


def pem(wire, kind):
    body = base64.encodebytes(wire).decode()
    return f'-----BEGIN NDN {kind}-----\n{body}-----END NDN {kind}-----\n'.encode()


def decode_pem(text, kind):
    body = text.split(f'-----BEGIN NDN {kind}-----', 1)[1].split(f'-----END NDN {kind}-----', 1)[0]
    # NDNd adds explanatory PEM headers when normalizing its files.
    body = '\n'.join(line for line in body.splitlines() if ':' not in line)
    return base64.b64decode(''.join(body.split()), validate=True)


def write_atomic(path, content):
    if path.exists() and path.read_bytes() == content:
        return False
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as stream:
        temporary = Path(stream.name)
        try:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
            stream.close()
            temporary.replace(path)
        finally:
            temporary.unlink(missing_ok=True)
    return True


def import_packet(directory, wire, kind):
    extension = '.key' if kind == 'KEY' else '.cert'
    path = directory / (hashlib.sha256(wire).hexdigest() + extension)
    if path.exists() and decode_pem(path.read_text(), kind) == wire:
        return False
    return write_atomic(path, pem(wire, kind))


def sign_with_root_ca(csr, root_ca_url, secret, before, after):
    query = urlencode({
        'not_before': before.strftime('%Y%m%d%H%M%S'),
        'not_after': after.strftime('%Y%m%d%H%M%S'),
    })
    url = f'{root_ca_url.rstrip("/")}/sign?{query}'
    request = Request(url, data=base64.encodebytes(csr), method='POST',
                      headers={'Authorization': f'Bearer {secret}'})
    with urlopen(request, timeout=30) as response:
        return base64.b64decode(b''.join(response.read().split()), validate=True)


def validity(wire):
    period = parse_certificate(wire).signature_info.validity_period
    return tuple(datetime.strptime(bytes(value).decode(), '%Y%m%dT%H%M%S').replace(tzinfo=timezone.utc)
                 for value in (period.not_before, period.not_after))


def verify_certificate(wire, issuer):
    cert = parse_certificate(wire)
    parent = parse_certificate(issuer)
    if cert.meta_info.content_type != ContentType.KEY or parent.meta_info.content_type != ContentType.KEY:
        return False
    locator = cert.signature_info.key_locator
    if locator is None or Name.to_bytes(locator.name) not in (
            Name.to_bytes(parent.name[:-2]), Name.to_bytes(parent.name)):
        return False
    _, _, _, pointers = parse_data(wire)
    signature_type = cert.signature_info.signature_type
    if signature_type == SignatureType.SHA256_WITH_ECDSA:
        return verify_ecdsa(ECC.import_key(bytes(parent.content)), pointers)
    if signature_type == SignatureType.SHA256_WITH_RSA:
        return verify_rsa(RSA.import_key(bytes(parent.content)), pointers)
    if signature_type == SignatureType.ED25519:
        return verify_ed25519(ECC.import_key(bytes(parent.content)), pointers)
    return False


def get_key(directory, identity):
    keys = list(directory.glob('*.key'))
    if keys:
        if len(keys) != 1:
            raise ValueError('Expected exactly one private service key')
        wire = decode_pem(keys[0].read_text(), 'KEY')
        name, meta, content, pointers = parse_data(wire)
        if (meta.content_type != 9 or len(name) != len(identity) + 2
                or Name.to_bytes(name[:-2]) != Name.to_bytes(identity)
                or bytes(name[-2]) != Component.from_str('KEY')):
            raise ValueError('Existing service key has the wrong identity or format')
        key = ECC.import_key(bytes(content))
        keys[0].chmod(0o600)
        if not key.has_private() or not verify_ecdsa(key.public_key(), pointers):
            raise ValueError('Invalid private service key')
        return name, key, wire

    key = ECC.generate(curve='P-256')
    name = identity + [Component.from_str('KEY'), Component.from_bytes(secrets.token_bytes(8))]
    secret = key.export_key(format='DER', use_pkcs8=False)
    signer = Sha256WithEcdsaSigner(name, secret)
    # NDNd encodes private keys as self-signed Data with ContentTypeSigningKey=9.
    wire = bytes(make_data(name, MetaInfo(content_type=9), secret, signer))
    import_packet(directory, wire, 'KEY')
    return name, key, wire


def provision(directory, site_home, site_prefix, anchors_path, force=False, renew_before_days=30,
              service='repo', root_ca_url='', root_cert_path=None, identity=None):
    # Serialize overlapping cron/manual renewal runs without rotating the key.
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    directory.chmod(0o700)
    with (directory / '.security.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        return provision_locked(directory, site_home, site_prefix, anchors_path, force, renew_before_days,
                    service, root_ca_url, root_cert_path, identity)


def provision_locked(directory, site_home, site_prefix, anchors_path, force, renew_before_days,
                     service, root_ca_url, root_cert_path, identity):
    if service not in ('repo', 'merkle', 'dv', 'ca'):
        raise ValueError('Unsupported NDNd service')
    if service == 'ca':
        config = {}
    else:
        with (directory / f'{service}.yml').open() as stream:
            config = yaml.safe_load(stream)[service]
    if service == 'dv':
        identity = Name.normalize(config['router'] + '/32=DV')
        expected_identity = Name.normalize(site_prefix + '/32=DV')
        if not root_ca_url or not os.environ.get('NDND_ROOT_CA_SECRET'):
            raise ValueError('DV credential provisioning requires the NDNd root CA URL and NDND_ROOT_CA_SECRET')
        if root_cert_path is None:
            raise ValueError('DV credential provisioning requires the NDNd root certificate path')
    elif service == 'ca':
        if not identity:
            raise ValueError('Site CA provisioning requires an explicit identity')
        identity = Name.normalize(identity)
        expected_identity = Name.normalize(site_prefix)
        if not root_ca_url or not os.environ.get('NDND_ROOT_CA_SECRET'):
            raise ValueError('Site CA provisioning requires the NDNd root CA URL and NDND_ROOT_CA_SECRET')
        if root_cert_path is None:
            raise ValueError('Site CA provisioning requires the NDNd root certificate path')
    else:
        expected_identity = Name.normalize(identity or (site_prefix + '/ndnd/' + service))
        identity = Name.normalize(config['name'])
        if not Name.is_prefix(Name.normalize(site_prefix), expected_identity):
            raise ValueError('Service identity must be beneath the site prefix')
    if Name.to_bytes(identity) != Name.to_bytes(expected_identity):
        raise ValueError(f'Invalid {service} identity {Name.to_str(identity)}')

    now = datetime.now(timezone.utc)
    if service in ('dv', 'ca'):
        issuer = decode_certificate(root_cert_path)
        root = parse_certificate(issuer)
        root_identity = root.name[:-4]
        expected_root = Name.normalize('/ndnd')
        if Name.to_bytes(root_identity) != Name.to_bytes(expected_root):
            raise ValueError(f'NDNd CA certificate identity must be /ndnd, got {Name.to_str(root_identity)}')
        if service == 'dv' and Name.to_str(root.name) not in config.get('trust_anchors', []):
            raise ValueError('DV configuration does not trust the configured NDNd root certificate')
        if not verify_certificate(issuer, issuer):
            raise ValueError('NDNd root certificate is not self-signed by its own key')
        anchor_wires = [issuer]
        signing_issuer = issuer
        root_before, root_after = validity(issuer)
        site_before = root_before
        site_after = root_after
    else:
        site_cert_path = site_home / 'site.ndncert'
        if not site_cert_path.exists():
            site_cert_path = site_home / 'ca.ndncert'
        site_wire = decode_certificate(site_cert_path)
        site = parse_certificate(site_wire)
        if Name.to_bytes(site.name[:-4]) != Name.to_bytes(Name.normalize(site_prefix)):
            raise ValueError('Site certificate has the wrong identity')
        available = {}
        for path in anchors_path.glob('*.base64'):
            wire = decode_certificate(path)
            available[Name.to_str(parse_certificate(wire).name)] = wire
        anchor_wires = [available[name] for name in config['trust_anchors']]
        if not anchor_wires:
            raise ValueError('At least one pinned trust anchor is required')
        issuer = next((wire for wire in anchor_wires if verify_certificate(site_wire, wire)), None)
        if issuer is None:
            raise ValueError('Site certificate does not verify against a pinned testbed root')
        signing_issuer = site_wire
        site_before, site_after = validity(site_wire)
        root_before, root_after = validity(issuer)
    # ndn-cxx rounds NotBefore up to a whole second when issuing a certificate.
    # Wait for that boundary rather than accepting a certificate before it is valid.
    starts = max(site_before, root_before)
    if now < starts <= now + timedelta(seconds=1):
        time.sleep((starts - now).total_seconds())
        now = datetime.now(timezone.utc)
    if not max(site_before, root_before) <= now < min(site_after, root_after):
        raise ValueError('Site certificate or issuing root is not currently valid')

    keys = directory / 'keys'
    keys.mkdir(mode=0o700, exist_ok=True)
    keys.chmod(0o700)
    key_name, key, key_wire = get_key(keys, identity)
    cert_path = directory / f'{service}.ndncert'
    cert_wire = decode_certificate(cert_path) if cert_path.exists() else None
    margin = timedelta(days=renew_before_days)
    renew = force or cert_wire is None
    if cert_wire is not None:
        cert = parse_certificate(cert_wire)
        before, after = validity(cert_wire)
        renew |= (not before <= now < after - margin
                  or Name.to_bytes(cert.name[:-2]) != Name.to_bytes(key_name)
                  or bytes(cert.content) != key.public_key().export_key(format='DER')
                  or not verify_certificate(cert_wire, signing_issuer)
                  or before < max(site_before, root_before)
                  or after > min(site_after, root_after))

    if renew:
        before = max(now - timedelta(minutes=5), site_before, root_before).replace(microsecond=0)
        after = min(now + timedelta(days=90), site_after, root_after).replace(microsecond=0)
        if service in ('dv', 'ca'):
            after = min(after, before + timedelta(days=90))
        if after <= now + margin:
            raise ValueError('Renew the site/root certificate before issuing a service certificate')
        signer = Sha256WithEcdsaSigner(key_name, key.export_key(format='DER', use_pkcs8=False))
        _, csr = new_cert(key_name, Component.from_str('self'),
                          key.public_key().export_key(format='DER'), signer, before, after)
        if service in ('dv', 'ca'):
            cert_wire = sign_with_root_ca(csr, root_ca_url, os.environ['NDND_ROOT_CA_SECRET'], before, after)
        elif site_cert_path.name == 'ca.ndncert':
            site_key_wire = decode_pem((site_home / 'ca.key.pem').read_text(), 'KEY')
            _, _, secret, _ = parse_data(site_key_wire)
            site_key = ECC.import_key(bytes(secret))
            if site_key.public_key().export_key(format='DER') != bytes(site.content):
                raise ValueError('Site CA private key does not match its certificate')
            site_signer = Sha256WithEcdsaSigner(site.name[:-2], site_key.export_key(format='DER', use_pkcs8=False))
            _, cert_wire = new_cert(key_name, Component.from_str('site'),
                                   key.public_key().export_key(format='DER'), site_signer, before, after)
        else:
            command = ['ndnsec', 'cert-gen', '-s', site_prefix,
                       '-S', before.strftime('%Y%m%d%H%M%S'), '-E', after.strftime('%Y%m%d%H%M%S'), '-']
            result = subprocess.run(command, input=base64.encodebytes(csr), stdout=subprocess.PIPE,
                                    env={**os.environ, 'HOME': str(site_home)}, check=True, timeout=30)
            cert_wire = base64.b64decode(b''.join(result.stdout.split()), validate=True)
        cert = parse_certificate(cert_wire)
        actual_before, actual_after = validity(cert_wire)
        if (Name.to_bytes(cert.name[:-2]) != Name.to_bytes(key_name)
                or bytes(cert.content) != key.public_key().export_key(format='DER')
                or not verify_certificate(cert_wire, signing_issuer)
                or not before <= actual_before <= now < actual_after <= after):
            raise ValueError('Site CA returned an invalid service certificate')

    # Prepare every credential before marking it for a service reload.
    changed = import_packet(keys, key_wire, 'KEY')
    certificates = [*anchor_wires, cert_wire]
    if service not in ('dv', 'ca'):
        certificates.insert(len(anchor_wires), site_wire)
    for wire in certificates:
        changed |= import_packet(keys, wire, 'CERT')
    changed |= write_atomic(cert_path, base64.encodebytes(cert_wire))
    if service == 'ca':
        changed |= write_atomic(directory / 'ca.cert.pem', pem(cert_wire, 'CERT'))
        changed |= write_atomic(directory / 'ca.key.pem', pem(key_wire, 'KEY'))
    if changed:
        write_atomic(directory / '.security-changed', b'\n')
    print(f"NDNd {service} {Name.to_str(identity)}: {'credentials updated' if changed else 'credentials current'}")
    return changed


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', type=Path, required=True)
    parser.add_argument('--site-home', type=Path)
    parser.add_argument('--site-prefix', required=True)
    parser.add_argument('--anchors', type=Path, required=True)
    parser.add_argument('--service', choices=('repo', 'merkle', 'dv', 'ca'), default='repo')
    parser.add_argument('--identity')
    parser.add_argument('--root-ca-url', default='')
    parser.add_argument('--root-cert', type=Path)
    parser.add_argument('--force', action='store_true')
    args = parser.parse_args()
    provision(args.directory, args.site_home, args.site_prefix, args.anchors, args.force,
              service=args.service, root_ca_url=args.root_ca_url, root_cert_path=args.root_cert,
              identity=args.identity)
