#!/usr/bin/env python3

import sys
import ndn.encoding
import yaml
import base64
import subprocess
import ndn

from http.server import BaseHTTPRequestHandler, HTTPServer

CONFIG_FILE = sys.argv[1]
GLOBAL_PREFIX = '/ndn'
SECRET = '<super-secret>'
HOSTS = {}
PORT = 8777

class MyHTTPRequestHandler(BaseHTTPRequestHandler):
    def sign(self, path, query, data):
        # Check if the secret is correct from query parameter
        if query != f'secret={SECRET}':
            self.send_error(401, "Invalid secret")
            return

        # Check if the host is allowed
        ip_address = self.get_client_ip()
        host = None
        for test in HOSTS.values():
            if ip_address == test['ip_address']:
                host = test
                break
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
        proc = subprocess.run(['ndnsec', 'cert-gen', '-s', GLOBAL_PREFIX, '-'], input=data, capture_output=True)

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
    with open(CONFIG_FILE, 'r') as f:
        config = yaml.safe_load(f)
        GLOBAL_PREFIX = config['global_prefix']
        SECRET = config['secret']
        HOSTS = config['hosts']
        PORT = config['port']

    # Start server
    server_address = ('', PORT)
    httpd = HTTPServer(server_address, MyHTTPRequestHandler)
    print(f"Starting Root CA server on port {PORT}")
    httpd.serve_forever()