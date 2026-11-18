#!/usr/bin/env python3
"""Build the static site into dist/.

Content pages are HTML fragments with a small frontmatter block.
This script applies the shared layout, prefixes the GitHub Pages
base path, marks affiliate links, and writes the sitemap and robots.txt.

    python3 scripts/build.py
    python3 scripts/build.py --out /tmp/coop-dist

Do not edit files under dist/. Edit content/, layout/, assets/, or
site.config.json, then build again.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import shutil
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import space_math  # noqa: E402

ALLOWED_KEYS = {
    "title",
    "description",
    "path",
    "updated",
    "published",
    "schema",
    "nav",
    "nav_label",
    "nav_order",
    "affiliate",
    "sitemap",
    "robots",
    "draft",
}
SCHEMAS = {"website", "webpage", "article"}
BOOL_KEYS = {"nav", "affiliate", "sitemap", "draft"}
DATE_KEYS = {"updated", "published"}
MONTHS = (
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
)
CHART_SLOT = '<div id="space-chart" data-chart="standard-run"></div>'
ATTR_RE = re.compile(
    r"(<[a-zA-Z][^>]*?\s(?:href|src)\s*=\s*)([\"'])(/[^\"']*)\2",
    re.IGNORECASE,
)
ANCHOR_RE = re.compile(r"<a\b([^>]*)>", re.IGNORECASE)


class BuildError(SystemExit):
    pass


def load_config(root: Path = ROOT) -> dict:
    path = root / "site.config.json"
    with path.open(encoding="utf-8") as handle:
        config = json.load(handle)
    for key in ("siteName", "tagline", "baseUrl", "basePath", "lang", "repository", "description"):
        if key not in config or not isinstance(config[key], str):
            raise BuildError(f"site.config.json is missing a string value for {key}")
    config["baseUrl"] = config["baseUrl"].rstrip("/")
    base_path = config["basePath"].strip()
    if base_path in ("", "/"):
        base_path = ""
    elif not base_path.startswith("/") or base_path.endswith("/"):
        raise BuildError('basePath must be empty or a path like "/Chicken-coop-guide" with no trailing slash')
    config["basePath"] = base_path
    return config


def parse_frontmatter(text: str, filename: str) -> tuple[dict, str]:
    if not text.startswith("---\n"):
        raise BuildError(f"{filename}: page must start with a --- frontmatter block")
    end = text.find("\n---\n", 4)
    if end == -1:
        raise BuildError(f"{filename}: frontmatter is not closed with ---")
    raw = text[4:end]
    body = text[end + 5 :]
    if body.startswith("\n"):
        body = body[1:]
    meta: dict = {}
    for line_number, line in enumerate(raw.splitlines(), start=2):
        if not line.strip() or line.strip().startswith("#"):
            continue
        if ":" not in line:
            raise BuildError(f"{filename}:{line_number}: expected key: value")
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()
        if key not in ALLOWED_KEYS:
            allowed = ", ".join(sorted(ALLOWED_KEYS))
            raise BuildError(f"{filename}:{line_number}: unknown frontmatter key '{key}'. Allowed: {allowed}")
        if key in meta:
            raise BuildError(f"{filename}:{line_number}: duplicate key '{key}'")
        meta[key] = value
    return normalize_meta(meta, filename), body


def normalize_meta(meta: dict, filename: str) -> dict:
    for key in ("title", "description", "path", "updated", "schema"):
        if key not in meta or meta[key] == "":
            raise BuildError(f"{filename}: frontmatter is missing {key}")
    if meta["schema"] not in SCHEMAS:
        raise BuildError(f"{filename}: schema must be website, webpage, or article")
    public = meta["path"]
    if public != "/" and not (public.startswith("/") and (public.endswith("/") or public.endswith(".html"))):
        raise BuildError(f"{filename}: path must be /, end with /, or be a root-relative .html file")
    for key in DATE_KEYS:
        if key in meta:
            try:
                date.fromisoformat(meta[key])
            except ValueError as exc:
                raise BuildError(f"{filename}: {key} must be YYYY-MM-DD") from exc
    meta.setdefault("published", meta["updated"])
    for key in BOOL_KEYS:
        if key not in meta:
            meta[key] = False if key != "sitemap" else True
            continue
        if meta[key] not in ("true", "false"):
            raise BuildError(f"{filename}: {key} must be true or false")
        meta[key] = meta[key] == "true"
    if "nav_order" in meta:
        if not re.fullmatch(r"-?\d+", meta["nav_order"]):
            raise BuildError(f"{filename}: nav_order must be an integer")
        meta["nav_order"] = int(meta["nav_order"])
    else:
        meta["nav_order"] = 100
    meta.setdefault("nav_label", meta["title"])
    meta.setdefault("robots", "noindex, follow" if public.endswith("404.html") else "index, follow")
    meta["source"] = filename
    return meta


def load_pages(root: Path) -> list[dict]:
    pages = []
    folder = root / "content" / "pages"
    for path in sorted(folder.glob("*.html")):
        if path.name.startswith("_"):
            continue
        meta, body = parse_frontmatter(path.read_text(encoding="utf-8"), path.name)
        if meta["draft"]:
            print(f"skip draft {path.name}")
            continue
        meta["body"] = body
        pages.append(meta)
    paths = [page["path"] for page in pages]
    if len(paths) != len(set(paths)):
        raise BuildError("two pages use the same path")
    if "/" not in paths:
        raise BuildError("a page with path: / is required")
    return pages


def output_relative(public: str) -> Path:
    if public == "/":
        return Path("index.html")
    if public.endswith(".html"):
        return Path(public.lstrip("/"))
    return Path(public.strip("/")) / "index.html"


def canonical_url(config: dict, public: str) -> str:
    if public == "/":
        return config["baseUrl"] + "/"
    return config["baseUrl"] + public


def prefix_root_urls(page: str, base_path: str) -> str:
    if not base_path:
        return page

    def replace(match: re.Match) -> str:
        prefix, quote, url = match.group(1), match.group(2), match.group(3)
        if url.startswith("//"):
            return match.group(0)
        if url == base_path or url.startswith(base_path + "/"):
            return match.group(0)
        return f"{prefix}{quote}{base_path}{url}{quote}"

    return ATTR_RE.sub(replace, page)


def apply_affiliate_rels(page: str) -> str:
    def replace(match: re.Match) -> str:
        attrs = match.group(1)
        if not re.search(r"\bdata-affiliate\b", attrs, re.IGNORECASE):
            return match.group(0)
        attrs = re.sub(r"\srel\s*=\s*([\"']).*?\1", "", attrs, flags=re.IGNORECASE)
        attrs = re.sub(r"\starget\s*=\s*([\"']).*?\1", "", attrs, flags=re.IGNORECASE)
        return f'<a{attrs} rel="sponsored nofollow noopener" target="_blank">'

    return ANCHOR_RE.sub(replace, page)


def assert_affiliate_markup(body: str, meta: dict) -> None:
    flagged = meta["affiliate"]
    for match in ANCHOR_RE.finditer(body):
        attrs = match.group(1)
        sponsored = bool(re.search(r"\bsponsored\b", attrs, re.IGNORECASE))
        marked = bool(re.search(r"\bdata-affiliate\b", attrs, re.IGNORECASE))
        if sponsored and not marked:
            raise BuildError(
                f"{meta['source']}: an affiliate link must use data-affiliate so the build can set rel"
            )
        if marked and not flagged:
            raise BuildError(
                f"{meta['source']}: data-affiliate link requires affiliate: true in frontmatter"
            )


def prepare_body(body: str, meta: dict, config: dict, guidelines: dict) -> str:
    assert_affiliate_markup(body, meta)
    if CHART_SLOT in body:
        body = body.replace(CHART_SLOT, space_math.chart_html(guidelines), 1)
    if 'id="coop-calculator"' in body:
        needle = '<script src="/assets/calculator.js"'
        if needle not in body:
            raise BuildError(f"{meta['source']}: the calculator form needs {needle}")
        payload = json.dumps(guidelines, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c")
        body = body.replace(
            needle,
            f'<script type="application/json" id="space-guidelines">{payload}</script>\n{needle}',
            1,
        )
    body = apply_affiliate_rels(body)
    return prefix_root_urls(body, config["basePath"])


def format_updated(iso: str) -> str:
    parsed = date.fromisoformat(iso)
    return f"{parsed.day} {MONTHS[parsed.month - 1]} {parsed.year}"


def disclosure_html(config: dict) -> str:
    href = f"{config['basePath']}/affiliate-disclosure/"
    return (
        '<aside class="affiliate-note" role="note">'
        "<p><strong>Affiliate links.</strong> If you buy through a marked link on this page, "
        "we may earn a commission. The price you pay does not change. "
        f'<a href="{html.escape(href, quote=True)}">Affiliate disclosure</a>.</p>'
        "</aside>"
    )


def breadcrumb_html(page: dict, config: dict) -> str:
    if page["path"] in ("/", "/404.html"):
        return ""
    home = html.escape(config["basePath"] + "/", quote=True)
    label = html.escape(page["title"])
    return (
        '<nav class="crumbs" aria-label="Breadcrumb"><ol>'
        f'<li><a href="{home}">Home</a></li>'
        f'<li aria-current="page">{label}</li>'
        "</ol></nav>"
    )


def nav_html(pages: list[dict], current: dict, config: dict) -> str:
    items = [page for page in pages if page["nav"]]
    items.sort(key=lambda page: (page["nav_order"], page["nav_label"]))
    links = []
    for page in items:
        href = config["basePath"] + (page["path"] if page["path"] != "/" else "/")
        label = html.escape(page["nav_label"])
        current_attr = ' aria-current="page"' if page["path"] == current["path"] else ""
        links.append(f'<li><a href="{html.escape(href, quote=True)}"{current_attr}>{label}</a></li>')
    return '<nav class="site-nav" aria-label="Primary"><ul>' + "".join(links) + "</ul></nav>"


def footer_html(config: dict) -> str:
    base = config["basePath"]
    links = [
        ("Privacy", f"{base}/privacy/"),
        ("Affiliate disclosure", f"{base}/affiliate-disclosure/"),
        ("Source code", config["repository"]),
    ]
    rendered = "".join(
        f'<li><a href="{html.escape(href, quote=True)}">{html.escape(label)}</a></li>'
        for label, href in links
    )
    return f'<ul class="footer-links">{rendered}</ul>'


def json_ld(page: dict, config: dict) -> str:
    canonical = canonical_url(config, page["path"])
    site = config["siteName"]
    site_url = config["baseUrl"] + "/"
    blocks = []
    if page["schema"] == "website":
        blocks.append(
            {
                "@context": "https://schema.org",
                "@type": "WebSite",
                "name": site,
                "url": site_url,
                "description": config["description"],
                "inLanguage": config["lang"],
            }
        )
    elif page["schema"] == "article":
        blocks.append(
            {
                "@context": "https://schema.org",
                "@type": "Article",
                "headline": page["title"],
                "description": page["description"],
                "datePublished": page["published"],
                "dateModified": page["updated"],
                "inLanguage": config["lang"],
                "mainEntityOfPage": canonical,
                "author": {"@type": "Organization", "name": site, "url": site_url},
                "publisher": {"@type": "Organization", "name": site, "url": site_url},
            }
        )
    else:
        blocks.append(
            {
                "@context": "https://schema.org",
                "@type": "WebPage",
                "name": page["title"],
                "description": page["description"],
                "url": canonical,
                "inLanguage": config["lang"],
                "isPartOf": {"@type": "WebSite", "name": site, "url": site_url},
            }
        )
    if page["path"] not in ("/", "/404.html"):
        blocks.append(
            {
                "@context": "https://schema.org",
                "@type": "BreadcrumbList",
                "itemListElement": [
                    {
                        "@type": "ListItem",
                        "position": 1,
                        "name": "Home",
                        "item": site_url,
                    },
                    {
                        "@type": "ListItem",
                        "position": 2,
                        "name": page["title"],
                        "item": canonical,
                    },
                ],
            }
        )
    parts = []
    for block in blocks:
        payload = json.dumps(block, ensure_ascii=False).replace("<", "\\u003c")
        parts.append(f'<script type="application/ld+json">{payload}</script>')
    return "\n  ".join(parts)


def full_title(page: dict, config: dict) -> str:
    if page["path"] == "/":
        return config["siteName"]
    return f"{page['title']} — {config['siteName']}"


def og_type(page: dict) -> str:
    return "article" if page["schema"] == "article" else "website"


def render_page(page: dict, pages: list[dict], config: dict, layout: str, guidelines: dict) -> str:
    page = dict(page)
    for key in ("title", "description", "nav_label"):
        if isinstance(page.get(key), str):
            page[key] = page[key].replace("[[site_name]]", config["siteName"])
    content = prepare_body(page["body"], page, config, guidelines)
    updated = (
        f'<p class="updated">Updated <time datetime="{page["updated"]}">'
        f"{html.escape(format_updated(page['updated']))}</time></p>"
    )
    tokens = {
        "lang": config["lang"],
        "title": full_title(page, config),
        "description": page["description"],
        "canonical": canonical_url(config, page["path"]),
        "robots": page["robots"],
        "og_type": og_type(page),
        "site_name": config["siteName"],
        "tagline": config["tagline"],
        "base": config["basePath"],
        "json_ld": json_ld(page, config),
        "nav": nav_html(pages, page, config),
        "footer": footer_html(config),
        "disclosure": disclosure_html(config) if page["affiliate"] else "",
        "updated": updated,
        "crumbs": breadcrumb_html(page, config),
        "content": content,
    }
    html_tokens = {"json_ld", "nav", "footer", "disclosure", "updated", "crumbs"}
    content_html = tokens.pop("content")
    rendered = layout
    for key, value in tokens.items():
        replacement = value if key in html_tokens else html.escape(value, quote=True)
        rendered = rendered.replace(f"[[{key}]]", replacement)
    rendered = rendered.replace("[[content]]", content_html)
    # Pages may use [[site_name]] so the visible name has one source.
    rendered = rendered.replace("[[site_name]]", html.escape(config["siteName"]))
    if "[[" in rendered:
        raise BuildError(f"{page['source']}: unreplaced [[token]]. Pages may only use [[site_name]]")
    return rendered


def write_sitemap(pages: list[dict], config: dict, out_dir: Path) -> None:
    urls = []
    for page in pages:
        if not page["sitemap"]:
            continue
        urls.append(
            "  <url>\n"
            f"    <loc>{html.escape(canonical_url(config, page['path']))}</loc>\n"
            f"    <lastmod>{page['updated']}</lastmod>\n"
            "  </url>"
        )
    body = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "\n".join(urls)
        + "\n</urlset>\n"
    )
    (out_dir / "sitemap.xml").write_text(body, encoding="utf-8")


def write_robots(config: dict, out_dir: Path) -> None:
    sitemap = canonical_url(config, "/sitemap.xml")
    text = f"User-agent: *\nAllow: /\n\nSitemap: {sitemap}\n"
    (out_dir / "robots.txt").write_text(text, encoding="utf-8")


def build_site(root: Path = ROOT, out_dir: Path | None = None) -> Path:
    config = load_config(root)
    guidelines = space_math.load_guidelines(root / "data" / "space-guidelines.json")
    pages = load_pages(root)
    for required in ("/privacy/", "/affiliate-disclosure/"):
        if required not in {page["path"] for page in pages}:
            raise BuildError(f"missing required page {required}")
    layout = (root / "layout" / "base.html").read_text(encoding="utf-8")
    destination = out_dir or (root / "dist")
    if destination.exists():
        shutil.rmtree(destination)
    destination.mkdir(parents=True)
    assets = root / "assets"
    if assets.exists():
        shutil.copytree(assets, destination / "assets")
    for page in pages:
        relative = output_relative(page["path"])
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(render_page(page, pages, config, layout, guidelines), encoding="utf-8")
        print(f"wrote {relative.as_posix()}")
    write_sitemap(pages, config, destination)
    write_robots(config, destination)
    cname = config.get("cname", "").strip()
    if cname:
        (destination / "CNAME").write_text(cname + "\n", encoding="utf-8")
    (destination / ".nojekyll").write_text("", encoding="utf-8")
    print(f"built {destination}")
    return destination


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the static site into dist/.")
    parser.add_argument("--out", type=Path, default=None, help="output directory (default: dist)")
    args = parser.parse_args()
    build_site(ROOT, args.out)


if __name__ == "__main__":
    main()
