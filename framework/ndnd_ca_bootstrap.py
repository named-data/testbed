#!/usr/bin/env python3
"""Create and publish the persistent Go NDNd root CA identity."""

import base64
import hashlib
import json
import os
import subprocess
import tempfile
from pathlib import Path

import yaml
from Cryptodome.PublicKey import ECC, RSA
from ndn.app_support.security_v2 import parse_certificate
from ndn.encoding import Component, ContentType, Name, SignatureType, parse_data
from ndn.security.validator import verify_ecdsa, verify_ed25519, verify_rsa


def run_ndnd(image: str, ca_home_host: Path, args: list[str], input_data: bytes | None = None,
             mount_ca: bool = False) -> bytes:
    command = ["docker", "run", "--rm"]
    if input_data is not None:
        command.append("-i")
    if mount_ca:
        command.extend(["-v", f"{ca_home_host}:/ca:ro"])
    command.extend([image, *args])
    result = subprocess.run(command, input=input_data, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.decode(errors="replace").strip() or "NDNd CLI failed")
    return result.stdout


def verify_self_signed_root(wire: bytes) -> bool:
    cert = parse_certificate(wire)
    if cert.meta_info.content_type != ContentType.KEY:
        return False
    locator = cert.signature_info.key_locator
    if locator is None or Name.to_bytes(locator.name) not in (
            Name.to_bytes(cert.name[:-2]), Name.to_bytes(cert.name)):
        return False
    _, _, _, pointers = parse_data(wire)
    if cert.signature_info.signature_type == SignatureType.SHA256_WITH_ECDSA:
        return verify_ecdsa(ECC.import_key(bytes(cert.content)), pointers)
    if cert.signature_info.signature_type == SignatureType.SHA256_WITH_RSA:
        return verify_rsa(RSA.import_key(bytes(cert.content)), pointers)
    if cert.signature_info.signature_type == SignatureType.ED25519:
        return verify_ed25519(ECC.import_key(bytes(cert.content)), pointers)
    return False


def atomic_write(path: Path, data: bytes, mode: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
    try:
        os.fchmod(descriptor, mode)
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def main() -> None:
    project_dir = Path(__file__).resolve().parent.parent
    with (project_dir / "config.yml").open() as stream:
        config = yaml.safe_load(stream)
    values = config["globals"]
    if os.environ.get("MANAGED_HOST") != values["ndnd_ca_host"]:
        return

    host_root = Path(os.environ.get("ROOT_DIR", str(project_dir)))
    ca_home = project_dir / "ndnd-root-ca-home" / "ndnd"
    ca_home_host = host_root / "ndnd-root-ca-home" / "ndnd"
    public_dir = project_dir / "dist/file-server/ndnd"
    anchor_path = project_dir / values["ndnd_root_anchor_path"]
    ca_home.mkdir(mode=0o700, parents=True, exist_ok=True)
    ca_home.chmod(0o700)
    key_path = ca_home / "ca.key.pem"
    cert_path = ca_home / "ca.cert.pem"
    image = values["ndnd_ca_image"]
    ca_prefix = Name.normalize(values["ndnd_dv_network"])

    if not key_path.exists() and not cert_path.exists():
        atomic_write(key_path, run_ndnd(image, ca_home_host, ["sec", "keygen", "/ndnd", "ed25519"]), 0o600)
    elif not key_path.exists():
        raise RuntimeError("NDNd CA certificate exists without its private key; refusing to rotate the root")

    if not cert_path.exists():
        cert = run_ndnd(image, ca_home_host, ["sec", "sign-cert", "/ca/ca.key.pem"],
                        key_path.read_bytes(), mount_ca=True)
        atomic_write(cert_path, cert, 0o644)

    cert_wire = run_ndnd(image, ca_home_host, ["sec", "pem-decode"], cert_path.read_bytes())
    pinned_root = base64.b64decode("".join(anchor_path.read_text().split()), validate=True)
    if cert_wire != pinned_root:
        raise RuntimeError("NDNd CA certificate does not match the committed /ndnd trust anchor")
    cert = parse_certificate(cert_wire)
    root_identity = cert.name[:-4]
    if Name.to_bytes(root_identity) != Name.to_bytes(ca_prefix):
        raise RuntimeError(f"NDNd CA cert identity must be {values['ndnd_dv_network']}, got {Name.to_str(root_identity)}")
    if not verify_self_signed_root(cert_wire):
        raise RuntimeError("NDNd CA certificate is not validly self-signed")

    cert_name = Name.to_str(cert.name)
    cert_digest = hashlib.sha256(cert_wire).hexdigest()
    if cert_digest != values["ndnd_root_certificate_sha256"]:
        raise RuntimeError("NDNd CA certificate does not match the pinned testbed fingerprint")
    previous_cert = public_dir / "ndnd-root-previous.ndncert"
    published_cert = public_dir / "ndnd-root.ndncert"
    if published_cert.exists() and published_cert.read_bytes() != cert_wire:
        atomic_write(previous_cert, published_cert.read_bytes(), 0o644)
    atomic_write(published_cert, cert_wire, 0o644)
    profile = {
        "schema_version": 1,
        "ca_prefix": values["ndnd_dv_network"],
        "ca_info": values["ndnd_ca_info"],
        "max_validity_period_seconds": int(values["ndnd_ca_max_validity_period"]),
        "probe_parameters": [],
        "supported_challenges": values["ndnd_ca_supported_challenges"],
        "router_identity_suffix": "/32=DV",
        "root_certificate_url": values["ndnd_root_certificate_url"],
        "root_certificate_name": cert_name,
        "root_certificate_sha256": cert_digest,
        "bootstrap_csr_signing_endpoint": values["ndnd_root_http_ca_url"] + "/sign",
        "trust_schema_url": values["ndnd_trust_schema_url"],
    }
    atomic_write(public_dir / "ndnd-ca-profile.json", (json.dumps(profile, indent=2) + "\n").encode(), 0o644)
    print(f"Prepared Go CA identity {cert_name}")


if __name__ == "__main__":
    main()
