"""Simple HTTP server to serve the live trading dashboard."""
import http.server
import os
import sys

PORT = 8888
DIRECTORY = os.path.join(os.path.dirname(os.path.abspath(__file__)), "live")

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)
    
    def end_headers(self):
        # Allow CORS and no-cache for live updates
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0')
        super().end_headers()

if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else PORT
    with http.server.HTTPServer(("0.0.0.0", port), Handler) as httpd:
        print(f"Dashboard serving at http://localhost:{port}")
        print(f"Open in browser to view live trading data")
        print(f"Press Ctrl+C to stop")
        httpd.serve_forever()
