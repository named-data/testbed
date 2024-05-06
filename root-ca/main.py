import sys
import yaml

from http.server import BaseHTTPRequestHandler, HTTPServer

CONFIG_FILE = sys.argv[1]
SECRET = '<super-secret>'
HOSTS = { }
PORT = 8777

class MyHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        ip_address = self.get_client_ip()

        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()

        self.wfile.write(f"Received signing request from IP address: {ip_address}".encode('utf-8'))

    def get_client_ip(self) -> str:
        forwarded_for = self.headers.get('X-Forwarded-For')
        if forwarded_for:
            return forwarded_for.split(',')[0].strip()

        return self.client_address[0]

if __name__ == '__main__':
    # Read YAML config
    with open(CONFIG_FILE, 'r') as f:
        config = yaml.safe_load(f)
        SECRET = config['secret']
        HOSTS = config['hosts']
        PORT = config['port']

    # Start server
    server_address = ('', PORT)
    httpd = HTTPServer(server_address, MyHTTPRequestHandler)
    print(f"Starting Root CA server on port {PORT}")
    httpd.serve_forever()