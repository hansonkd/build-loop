"""Minimal static file server for the Glass landing page. Runs on port 80."""

import http.server
import os
import socketserver

PORT = int(os.environ.get("LANDING_PORT", "80"))
DIRECTORY = os.path.dirname(os.path.abspath(__file__))


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)


class ReusableTCPServer(socketserver.TCPServer):
    allow_reuse_address = True


if __name__ == "__main__":
    with ReusableTCPServer(("", PORT), Handler) as httpd:
        print(f"Landing page serving on http://0.0.0.0:{PORT}")
        httpd.serve_forever()
