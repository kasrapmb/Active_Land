"""Local UI preview only; never use this server in production."""
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
class Handler(SimpleHTTPRequestHandler):
    def translate_path(self, path):
        path = path.split('?', 1)[0]
        if path == '/':
            return str(ROOT / 'catalog/templates/catalog/home.html')
        if path.startswith('/static/catalog/'):
            name = path.removeprefix('/static/catalog/')
            if name in ('style.css', 'app.js'):
                return str(ROOT / 'catalog/static/catalog' / name)
        return str(ROOT / 'tools/__not_found__')
if __name__ == '__main__':
    ThreadingHTTPServer(('127.0.0.1', 8000), Handler).serve_forever()
