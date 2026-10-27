"""Local server that mimics GitHub Pages URL resolution (/foo -> foo.html,
unknown paths -> 404.html)."""
import http.server, os
from pathlib import Path

ROOT = Path(__file__).parent / "docs"

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=str(ROOT), **kw)

    def translate_path(self, path):
        fs = Path(super().translate_path(path))
        if not fs.exists() and fs.with_suffix(".html").exists():
            return str(fs.with_suffix(".html"))
        return str(fs)

    def send_error(self, code, message=None, explain=None):
        page = ROOT / "404.html"
        if code != 404 or not page.exists():
            return super().send_error(code, message, explain)
        body = page.read_bytes()
        self.send_response(404)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    print(f"Serving {ROOT} at http://localhost:{port}")
    http.server.ThreadingHTTPServer(("", port), Handler).serve_forever()
