#!/usr/bin/env python3

import sys
import ndn.encoding
import yaml
import base64
import subprocess
import ndn
import ipaddress
import os
from datetime import datetime, timedelta
from urllib.parse import parse_qs

from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, HTTPServer

@dataclass
class Config:
    global_prefix: str
    secret: str
    hosts: dict[str, dict]
    port: int
    signer_backend: str = 'ndnsec'
    ndnd_ca_image: str = ''
    ndnd_ca_host_dir: str = ''

config: Config = None


def is_ndnd_csr_name(prefix: str, name: list[bytes]) -> bool:
    prefix_name = ndn.encoding.Name.normalize(prefix)
    if len(name) != len(prefix_name) + 4 or name[:len(prefix_name)] != prefix_name:
        return False
    component = ndn.encoding.Component
    return (name[len(prefix_name)] == component.from_str('KEY')
            and name[len(prefix_name) + 2] == component.from_str('self')
            and component.get_type(name[-1]) == component.TYPE_VERSION)


class MyHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/health':
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain; charset=utf-8')
            self.end_headers()
            self.wfile.write(b'ok\n')
            return
        self.send_error(404)

    def which_host_ip(self, address: str) -> dict|None:
        for _, host in config.hosts.items():
            for subnet in host['subnets']:
                if ipaddress.ip_address(address) in ipaddress.ip_network(subnet):
                    return host
        return None

    def sign(self, path: str, query: str, data: bytes) -> None:
        # Check if the secret is correct from query parameter
        try:
            params = parse_qs(query, strict_parsing=True)
        except ValueError:
            self.send_error(400, "Invalid query parameters")
            return
        authorization = self.headers.get('Authorization')
        if authorization != f'Bearer {config.secret}' and params.get('secret') != [config.secret]:
            self.send_error(401, "Invalid secret")
            return

        # Check if the host is allowed
        ip_address = self.address_string()
        host = self.which_host_ip(ip_address)
        if not host:
            self.send_error(403, f"Host {ip_address} not allowed")
            return

        # Validate prefix of the CSR
        pfx = host['prefix']
        name = ndn.encoding.ndn_format_0_3.parse_data(base64.b64decode(data))[0]
        if config.signer_backend == 'ndnd-go':
            valid_name = is_ndnd_csr_name(pfx, name)
            ca_prefix = host.get('ca_prefix')
            if ca_prefix:
                valid_name |= is_ndnd_csr_name(ca_prefix, name)
        else:
            valid_name = ndn.encoding.name.Name.is_prefix(pfx, name)
        if not valid_name:
            str_name = ndn.encoding.name.Name.to_str(name)
            self.send_error(400, f"Invalid name {str_name}, expected prefix {pfx}")
            return

        not_before = params.get('not_before', [])
        not_after = params.get('not_after', [])
        if bool(not_before) != bool(not_after) or len(not_before) > 1 or len(not_after) > 1:
            self.send_error(400, "Both validity bounds must be provided once")
            return

        if not_before:
            try:
                start = datetime.strptime(not_before[0], '%Y%m%d%H%M%S')
                end = datetime.strptime(not_after[0], '%Y%m%d%H%M%S')
            except ValueError:
                self.send_error(400, "Invalid certificate validity bounds")
                return
            if end <= start or end - start > timedelta(days=90):
                self.send_error(400, "Certificate validity must be positive and no longer than 90 days")
                return

        if config.signer_backend == 'ndnd-go':
            if not config.ndnd_ca_image or not config.ndnd_ca_host_dir:
                self.send_error(500, "NDNd Go signer is not configured")
                return
            try:
                csr_wire = base64.b64decode(b''.join(data.split()), validate=True)
            except ValueError:
                self.send_error(400, "Invalid base64 CSR")
                return
            csr_pem = (b'-----BEGIN NDN CERT-----\n' + base64.encodebytes(csr_wire)
                       + b'-----END NDN CERT-----\n')
            command = ['docker', 'run', '--rm', '-i', '-v',
                       f'{config.ndnd_ca_host_dir}:/ca:ro', config.ndnd_ca_image,
                       'sec', 'sign-cert', '/ca/ca.key.pem']
            if not_before:
                command.extend(['--start', not_before[0], '--end', not_after[0]])
            proc = subprocess.run(command, input=csr_pem, capture_output=True, timeout=30)
            if proc.returncode == 0:
                decoded = subprocess.run(
                    ['docker', 'run', '--rm', '-i', config.ndnd_ca_image, 'sec', 'pem-decode'],
                    input=proc.stdout, capture_output=True, timeout=30)
                if decoded.returncode != 0:
                    proc = decoded
                else:
                    proc.stdout = base64.encodebytes(decoded.stdout)
        elif config.signer_backend == 'ndnsec':
            command = ['ndnsec', 'cert-gen', '-s', config.global_prefix]
            if not_before:
                command.extend(['-S', not_before[0], '-E', not_after[0]])
            command.append('-')
            proc = subprocess.run(command, input=data, capture_output=True, timeout=30)
        else:
            self.send_error(500, "Unsupported signer backend")
            return

        if proc.returncode != 0:
            self.send_error(500, f"Failed to sign certificate: {proc.stderr}")
            return

        # Log the certificate name
        certificate = proc.stdout
        cert_name = ndn.encoding.ndn_format_0_3.parse_data(base64.b64decode(certificate))[0]
        print(f"Issued certificate: {ndn.encoding.name.Name.to_str(cert_name)}")

        # Send the signed certificate
        self.send_response(200)
        self.end_headers()
        self.wfile.write(certificate)

        # This cache is consumed as the host's site certificate, not as a
        # general log of every descendant certificate signed for that host.
        identity = ndn.encoding.name.Name.to_str(cert_name[:-4]) if len(cert_name) >= 4 else ''
        ca_prefix = host.get('ca_prefix')
        path = host.get('ca_cert_file') if ca_prefix and identity == ca_prefix else host.get('cert_file')
        expected_identity = ca_prefix if ca_prefix and identity == ca_prefix else pfx
        if path and identity == expected_identity:
            with open(path, 'wb') as f:
                f.write(certificate)

    def do_POST(self):
        # Check if the path is correct
        parts = self.path.split('?')

        # Get the path and query parameters
        path = parts[0]
        query = parts[1] if len(parts) > 1 else ''

        # Get the request body
        content_length = int(self.headers['Content-Length'])
        data = self.rfile.read(content_length)
        if not data:
            self.send_error(400, "Empty request body")
            return

        if path == '/sign':
            return self.sign(path, query, data)

        return self.send_error(404)

    def address_string(self) -> str:
        """Override base class function to use header"""
        forwarded_for = self.headers.get('X-Forwarded-For')
        if forwarded_for:
            return forwarded_for.split(',')[0].strip()

        return self.client_address[0]

    def log_request(self, code='-', size='-') -> None:
        # Legacy callers put the root CA secret in the query string.
        requestline = self.requestline.split('?', 1)[0]
        self.log_message('"%s" %s %s', requestline, str(code), str(size))

if __name__ == '__main__':
    # Read YAML config
    with open(sys.argv[1], 'r') as f:
        config_data = yaml.safe_load(f)
    if os.environ.get('NDND_ROOT_CA_SECRET'):
        config_data['secret'] = os.environ['NDND_ROOT_CA_SECRET']
    config_data['ndnd_ca_image'] = os.environ.get('NDND_CA_IMAGE', config_data.get('ndnd_ca_image', ''))
    config_data['ndnd_ca_host_dir'] = os.environ.get('NDND_CA_HOST_DIR', config_data.get('ndnd_ca_host_dir', ''))
    if not config_data.get('secret'):
        raise RuntimeError('HTTP CA secret must be configured')
    config = Config(**config_data)

    # Start server
    server_address = ('', config.port)
    httpd = HTTPServer(server_address, MyHTTPRequestHandler)
    print(f"Starting HTTP CA server on port {config.port}")
    httpd.serve_forever()