import os
from http.server import BaseHTTPRequestHandler as a, HTTPServer as b
PORT = int(os.environ.get("PORT", 8080))
class A(a):
    def do_GET(self):
        body = b"@tellycloudbots"
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
if __name__ == "__main__":
    server = b(("0.0.0.0", PORT), A)
    print(f"Port Bonded at {PORT}")
    server.serve_forever()
