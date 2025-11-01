# SPDX-FileCopyrightText: 2025 2025 robot-visual-perception
#
# SPDX-License-Identifier: MIT

"""PLACEHOLDER"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import json


def hello() -> str:
    return "Hello from backend"


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        response = {"status": "ok", "message": hello()}
        self.wfile.write(json.dumps(response).encode())


if __name__ == "__main__":
    HTTPServer(("0.0.0.0", 8000), Handler).serve_forever()
