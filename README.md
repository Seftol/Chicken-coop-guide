# Backyard Coop Guide

A small static site about backyard chicken housing: coop and run size first, with flock planning and egg laying to follow. Figures are taken from public sources and shown in imperial and metric units. The site does not keep chickens and does not claim to have tested products.

The working name is **Backyard Coop Guide**. It lives in [`site.config.json`](site.config.json) as `siteName` and is used for the header, the page titles, the footer, and structured data. Page sentences that should use the same name contain `[[site_name]]`.

It is built to be published at <https://seftol.github.io/Chicken-coop-guide/>. The capital C in the repository name is part of the base path.

## Commands

```bash
python3 scripts/build.py
python3 -m unittest discover -s tests -v
python3 scripts/linkcheck.py
python3 scripts/preview.py
```

`make check` runs the build, the tests, and the link check. `make preview` builds and serves the site.

Open the preview at the URL the server prints, which includes `/Chicken-coop-guide/`. Do not use `python3 -m http.server` inside `dist/`. Built links already contain the base path, so that server will point them at the wrong place.

## Layout

| Path | Role |
| --- | --- |
| `site.config.json` | Site name, canonical origin, base path, repository URL |
| `content/pages/` | One HTML file per page, with frontmatter |
| `layout/base.html` | Shared header, footer, and meta tags |
| `assets/` | CSS, the calculator script, the favicon |
| `data/space-guidelines.json` | Numeric inputs for the space calculator |
| `scripts/build.py` | Writes `dist/` |
| `scripts/preview.py` | Local server at the real base path |
| `scripts/linkcheck.py` | Internal links must resolve; external failures are reported |
| `dist/` | Generated. Do not edit |

Adding a page is documented in [CONTRIBUTING.md](CONTRIBUTING.md). The sitemap, the base path, and the affiliate-link attributes are applied by the build. They are not hand-edited.

## Publishing

Pushes to `main` run [`.github/workflows/pages.yml`](.github/workflows/pages.yml), which builds the site and deploys `dist/` with GitHub Actions. Pull requests build, test, and check links, and do not deploy.

GitHub will not use that workflow until the repository owner sets **Settings → Pages → Build and deployment → Source** to **GitHub Actions**. The workflow cannot flip that setting by itself. It only has to be done once. The first deployment can also create the `github-pages` environment.

The live URL is <https://seftol.github.io/Chicken-coop-guide/>.

## Custom domain later

1. In `site.config.json`, set `baseUrl` to `https://example.com` (no trailing slash) and `basePath` to `""`.
2. Optional: set `cname` to `example.com`. The build writes that into `dist/CNAME`.
3. At the DNS host, follow GitHub’s custom-domain instructions, then set the domain under Settings → Pages.
4. Rebuild. Root-relative links become `/about/` instead of `/Chicken-coop-guide/about/`.

Leave `basePath` as `/Chicken-coop-guide` for the current GitHub Pages project URL. The path is case-sensitive.

## Affiliate links

No affiliate program has been joined, and the site has no tracking IDs. When one is joined, the rules are in [CONTRIBUTING.md](CONTRIBUTING.md). Pages that declare `affiliate: true` get a disclosure notice at the top automatically.
