#!/usr/bin/env python3
"""Serve dist/ at the configured base path.

GitHub Pages will host the site at /Chicken-coop-guide/. Root-relative
links in the built files include that prefix, so opening dist/ with
python -m http.server shows a site whose links point at the wrong place.
This server mounts the built files at the same prefix.

    python3 scripts/build.py
    python3 scripts/preview.py

Then open the URL it prints. For a custom-domain preview, set basePath
to "" in site.config.json, rebuild, and run this again. The site is
then served at http://127.0.0.1:8000/.
"""

from __future__ import annotations

import argparse
import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import build  # noqa: E402


class PreviewHandler(SimpleHTTPRequestHandler):
    dist: Path = ROOT / "dist"
    base_path: str = ""

    def do_GET(self):  # noqa: N802 — stdlib handler name
        parsed = urlparse(self.path)
        path = unquote(parsed.path)
        base = self.base_path
        if path == "/" and base:
            self._redirect(base + "/")
            return
        if base and path == base:
            self._redirect(base + "/")
            return
        if base:
            if path != base and not path.startswith(base + "/"):
                self._send_file(self.dist / "404.html", 404)
                return
            site_path = path[len(base) :] or "/"
        else:
            site_path = path
        target = self._resolve(site_path)
        if target is None:
            self._send_file(self.dist / "404.html", 404)
            return
        self._send_file(target, 200)

    def _resolve(self, site_path: str) -> Path | None:
        if site_path.endswith("/"):
            rel = site_path.strip("/")
            candidate = self.dist / "index.html" if not rel else self.dist / rel / "index.html"
        else:
            rel = site_path.lstrip("/")
            candidate = self.dist / rel
            if not candidate.is_file():
                candidate = self.dist / rel / "index.html"
        try:
            resolved = candidate.resolve()
        except OSError:
            return None
        root = self.dist.resolve()
        if resolved != root and root not in resolved.parents:
            return None
        return resolved if resolved.is_file() else None

    def _redirect(self, location: str) -> None:
        self.send_response(302)
        self.send_header("Location", location)
        self.end_headers()

    def _send_file(self, path: Path, status: int) -> None:
        if not path.is_file():
            message = b"Not found\n"
            self.send_response(404)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(message)))
            self.end_headers()
            self.wfile.write(message)
            return
        data = path.read_bytes()
        self.send_response(status)
        self.send_header("Content-Type", self.guess_type(str(path)))
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def main() -> None:
    parser = argparse.ArgumentParser(description="Preview the built site with the Pages base path.")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--dist", type=Path, default=ROOT / "dist")
    args = parser.parse_args()
    if not args.dist.exists():
        raise SystemExit("dist/ is missing. Run python3 scripts/build.py first.")
    config = build.load_config(ROOT)
    PreviewHandler.dist = args.dist
    PreviewHandler.base_path = config["basePath"]
    server = ThreadingHTTPServer(("127.0.0.1", args.port), PreviewHandler)
    prefix = config["basePath"] + "/"
    print(f"Preview at http://127.0.0.1:{args.port}{prefix}")
    print("Stop with Ctrl-C.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
