#!/usr/bin/env python3
"""Check links in the built site.

Internal links must resolve. A missing page, asset, or fragment fails
the run. External links are requested and reported. A definite 404 or
410 fails the run. Timeouts, HTTP 403, and HTTP 429 are reported and
do not fail the run, because many extension sites block automated
clients while still loading in a browser.

    python3 scripts/build.py
    python3 scripts/linkcheck.py
    python3 scripts/linkcheck.py --internal-only
"""

from __future__ import annotations

import argparse
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import unquote, urljoin, urlparse
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import build  # noqa: E402

USER_AGENT = (
    "Mozilla/5.0 (compatible; BackyardCoopGuideLinkCheck/1.0; +https://github.com/Seftol/Chicken-coop-guide)"
)
SKIP_SCHEMES = {"mailto", "tel", "javascript"}
# These responses usually mean a bot wall or a temporary limit, not a dead URL.
WARN_STATUSES = {401, 403, 408, 429, 500, 502, 503, 504}


class LinkParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.refs: list[tuple[str, str]] = []
        self.ids: set[str] = set()

    def handle_starttag(self, tag, attrs):
        attr = dict(attrs)
        if "id" in attr:
            self.ids.add(attr["id"])
        if tag in {"a", "link"} and attr.get("href"):
            self.refs.append((tag, attr["href"].strip()))
        if tag in {"img", "script"} and attr.get("src"):
            self.refs.append((tag, attr["src"].strip()))


def iter_html(dist: Path):
    yield from sorted(dist.rglob("*.html"))


def page_url(html_path: Path, dist: Path) -> str:
    rel = html_path.relative_to(dist).as_posix()
    if rel == "index.html":
        return "/"
    if rel.endswith("/index.html"):
        return "/" + rel[: -len("index.html")]
    return "/" + rel


def resolve_internal(url_path: str, dist: Path) -> Path | None:
    path = unquote(url_path.split("?", 1)[0])
    if path.endswith("/"):
        rel = path.strip("/")
        candidate = dist / "index.html" if not rel else dist / rel / "index.html"
    else:
        rel = path.lstrip("/")
        candidate = dist / rel
        if not candidate.is_file():
            nested = dist / rel / "index.html"
            if nested.is_file():
                candidate = nested
    try:
        resolved = candidate.resolve()
        dist_resolved = dist.resolve()
    except OSError:
        return None
    if dist_resolved != resolved and dist_resolved not in resolved.parents:
        return None
    return resolved if resolved.is_file() else None


def check_internal(dist: Path, base_path: str, base_url: str) -> list[str]:
    failures: list[str] = []
    for html_path in iter_html(dist):
        parser = LinkParser()
        text = html_path.read_text(encoding="utf-8")
        parser.feed(text)
        here = page_url(html_path, dist)
        ids_by_file: dict[Path, set[str]] = {html_path.resolve(): parser.ids}
        for _tag, ref in parser.refs:
            if not ref or ref.startswith("#"):
                fragment = ref[1:] if ref.startswith("#") else ""
                if fragment and fragment not in parser.ids:
                    failures.append(f"{here}: fragment #{fragment} is missing on this page")
                continue
            parsed = urlparse(ref)
            if parsed.scheme in SKIP_SCHEMES:
                continue
            fragment = ""
            strip_base = False
            if parsed.scheme in {"http", "https"}:
                absolute = parsed._replace(fragment="").geturl()
                if absolute == base_url or absolute.startswith(base_url + "/"):
                    url_path = absolute[len(base_url) :] or "/"
                    fragment = parsed.fragment
                else:
                    continue
            else:
                joined = urljoin(here, ref)
                parsed_joined = urlparse(joined)
                url_path = parsed_joined.path or "/"
                fragment = parsed_joined.fragment
                strip_base = True
            if strip_base and base_path:
                if url_path == base_path:
                    url_path = "/"
                elif url_path.startswith(base_path + "/"):
                    url_path = url_path[len(base_path) :] or "/"
                else:
                    failures.append(f"{here}: {ref} does not start with the site base path {base_path}")
                    continue
            target = resolve_internal(url_path, dist)
            if target is None:
                failures.append(f"{here}: internal link not found: {ref}")
                continue
            if fragment:
                if target not in ids_by_file:
                    nested = LinkParser()
                    nested.feed(target.read_text(encoding="utf-8"))
                    ids_by_file[target] = nested.ids
                if fragment not in ids_by_file[target]:
                    failures.append(f"{here}: fragment #{fragment} is missing in {ref}")
    return failures


def external_urls(dist: Path, base_url: str) -> list[str]:
    found: list[str] = []
    seen: set[str] = set()
    for html_path in iter_html(dist):
        parser = LinkParser()
        parser.feed(html_path.read_text(encoding="utf-8"))
        for _tag, ref in parser.refs:
            parsed = urlparse(ref)
            if parsed.scheme not in {"http", "https"}:
                continue
            if ref.startswith(base_url):
                continue
            cleaned = parsed._replace(fragment="").geturl()
            if cleaned not in seen:
                seen.add(cleaned)
                found.append(cleaned)
    return found


def fetch_status(url: str, timeout: float) -> tuple[str, str]:
    request = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "*/*"})
    try:
        with urlopen(request, timeout=timeout) as response:
            response.read(256)
            status = getattr(response, "status", 200)
            return ("ok" if 200 <= status < 400 else "fail", f"{status} {response.geturl()}")
    except HTTPError as exc:
        if exc.code in WARN_STATUSES:
            return ("warn", f"{exc.code} {url}")
        if exc.code in {404, 410}:
            return ("fail", f"{exc.code} {url}")
        return ("warn", f"{exc.code} {url}")
    except URLError as exc:
        return ("warn", f"connection failed ({exc.reason}) {url}")
    except Exception as exc:  # noqa: BLE001 — report the failure, do not crash the run
        return ("warn", f"{type(exc).__name__} {url}")


def check_external(urls: list[str], timeout: float, workers: int) -> tuple[list[str], list[str]]:
    failures: list[str] = []
    warnings: list[str] = []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(fetch_status, url, timeout): url for url in urls}
        for future in as_completed(futures):
            kind, detail = future.result()
            if kind == "fail":
                failures.append(detail)
            elif kind == "warn":
                warnings.append(detail)
    return failures, warnings


def main() -> None:
    parser = argparse.ArgumentParser(description="Check links in dist/.")
    parser.add_argument("--dist", type=Path, default=ROOT / "dist")
    parser.add_argument("--internal-only", action="store_true")
    parser.add_argument("--timeout", type=float, default=25)
    parser.add_argument("--workers", type=int, default=6)
    args = parser.parse_args()
    if not args.dist.exists():
        raise SystemExit("dist/ is missing. Run python3 scripts/build.py first.")
    config = build.load_config(ROOT)
    internal = check_internal(args.dist, config["basePath"], config["baseUrl"])
    external_fail: list[str] = []
    external_warn: list[str] = []
    if not args.internal_only:
        urls = external_urls(args.dist, config["baseUrl"])
        print(f"checking {len(urls)} external links")
        external_fail, external_warn = check_external(urls, args.timeout, args.workers)
    lines = ["Internal links"]
    lines.extend(f"  FAIL {item}" for item in internal)
    if not internal:
        lines.append("  ok")
    lines.append("External links")
    lines.extend(f"  FAIL {item}" for item in sorted(external_fail))
    lines.extend(f"  WARN {item}" for item in sorted(external_warn))
    if not external_fail and not external_warn:
        lines.append("  ok" if not args.internal_only else "  skipped")
    report = "\n".join(lines) + "\n"
    print(report)
    (ROOT / "linkcheck-report.txt").write_text(report, encoding="utf-8")
    if internal or external_fail:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
