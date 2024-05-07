#!/usr/bin/env python3

import sys
import ndn.encoding
import yaml
import base64
import subprocess
import ndn
import ipaddress

from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, HTTPServer

@dataclass
class Config:
    global_prefix: str
    secret: str
    hosts: dict[str, dict]
    port: int

config: Config = None

class MyHTTPRequestHandler(BaseHTTPRequestHandler):
    def which_host_ip(self, address):
        for _, host in config.hosts.items():
            for subnet in host['subnets']:
                if ipaddress.ip_address(address) in ipaddress.ip_network(subnet):
                    return host
        return None

    def sign(self, path, query, data):
        # Check if the secret is correct from query parameter
        if query != f'secret={config.secret}':
            self.send_error(401, "Invalid secret")
            return

        # Check if the host is allowed
        ip_address = self.get_client_ip()
        host = self.which_host_ip(ip_address)
        if not host:
            self.send_error(403, f"Host {ip_address} not allowed")
            return

        # Validate prefix of the CSR
        pfx = host['prefix']
        name = ndn.encoding.ndn_format_0_3.parse_data(base64.b64decode(data))[0]
        if not ndn.encoding.name.Name.is_prefix(pfx, name):
            str_name = ndn.encoding.name.Name.to_str(name)
            self.send_error(400, f"Invalid name {str_name}, expected prefix {pfx}")
            return

        # Sign a certificate for the name
        proc = subprocess.run(['ndnsec', 'cert-gen', '-s', config.global_prefix, '-'], input=data, capture_output=True)

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

        # Store the certificate if path provided
        if path := host.get('cert_file'):
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

    def get_client_ip(self) -> str:
        forwarded_for = self.headers.get('X-Forwarded-For')
        if forwarded_for:
            return forwarded_for.split(',')[0].strip()

        return self.client_address[0]

if __name__ == '__main__':
    # Read YAML config
    with open(sys.argv[1], 'r') as f:
        config = Config(**yaml.safe_load(f))

    # Start server
    server_address = ('', config.port)
    httpd = HTTPServer(server_address, MyHTTPRequestHandler)
    print(f"Starting HTTP CA server on port {config.port}")
    httpd.serve_forever()