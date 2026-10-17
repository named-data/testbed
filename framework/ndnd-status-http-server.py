#!/usr/bin/env python3

import html
import subprocess
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path not in ("/", "/index.html"):
            self.send_error(404)
            return

        try:
            status = subprocess.run(
                ["nfdc", "status"], capture_output=True, check=True, text=True, timeout=5
            ).stdout
        except (OSError, subprocess.SubprocessError) as error:
            self.send_error(502, str(error))
            return

        body = (
            "<!doctype html><html><head><meta charset=\"utf-8\">"
            "<title>NDNd status</title></head><body><h1>NDNd status</h1><pre>"
            f"{html.escape(status)}</pre></body></html>"
        ).encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


ThreadingHTTPServer(("0.0.0.0", 6380), Handler).serve_forever()