# Adding a page

One page per change. The build applies the shared layout, the base path, the sitemap, and affiliate-link attributes. Do not edit `dist/`.

## 1. Copy the template

```bash
cp content/pages/_template.html content/pages/your-slug.html
```

Files whose names start with `_` are never built. The template is also `draft: true`, which the build skips and prints. Delete the `draft` line, or set `draft: false`, when the page should be published.

## 2. Fill in the frontmatter

The block at the top of the file is `key: value`, one pair per line. It is not full YAML. Do not wrap values in quotes, and do not split a value across lines.

| Key | Required | Meaning |
| --- | --- | --- |
| `title` | yes | Heading used in the title bar and breadcrumbs. The site name is appended automatically, except on the home page. |
| `description` | yes | Meta description and Open Graph description. One sentence, roughly 150 characters. |
| `path` | yes | Public path: `/`, `/your-slug/`, or `/404.html`. Directory pages must end with `/`. |
| `updated` | yes | `YYYY-MM-DD`. Printed on the page and used as the sitemap `lastmod`. |
| `published` | no | `YYYY-MM-DD`. Defaults to `updated`. Used in Article structured data. |
| `schema` | yes | `article` for a guide, `webpage` for about/policy pages, `website` for the home page only. |
| `nav` | no | `true` to show the page in the header. Default `false`. |
| `nav_label` | no | Short header label. Defaults to `title`. |
| `nav_order` | no | Integer. Lower numbers come first. Home is 10, Guides is 15, the space guide is 20, About is 30. |
| `affiliate` | no | `true` if the page contains affiliate links. Default `false`. The build then inserts the disclosure notice. |
| `sitemap` | no | `false` to omit the page. Default `true`. The 404 page is omitted. |
| `robots` | no | Defaults to `index, follow`, or `noindex, follow` for `404.html`. |
| `draft` | no | `true` skips the page. |

Unknown keys fail the build. That is deliberate, so a typo is not ignored.

`[[site_name]]` in the body, the title, the description, or the nav label is replaced from `site.config.json`. No other `[[token]]` is allowed in a page.

## 3. Write the page

Use ordinary HTML after the frontmatter: one `h1`, then `h2` sections. The layout already provides the header, footer, skip link, and main landmark.

### Guides index

`/guides/` lists every published page whose `schema` is `article`. The build replaces `<div id="guide-index"></div>` on that page with each article’s title and description. Order is `published`, then `path`. Adding an article does not require an edit to `content/pages/guides.html`.

The home page, about, privacy, affiliate disclosure, and the 404 page are not articles, so they are not listed. The template is not built. A draft is not built, so it is not listed. The guides page itself is `schema: webpage`. Do not hand-write the list, and do not put affiliate links on it.

Internal links start at the site root, with no base path:

```html
<a href="/about/">About</a>
<a href="/coop-and-run-size/#chart">the chart</a>
```

The build prefixes `basePath` from `site.config.json` (currently `/Chicken-coop-guide`). A hand-written `/Chicken-coop-guide/about/` link will be prefixed twice and will break.

External citations are normal links. Do not add `rel="nofollow"` to a source.

```html
<a href="https://extension.psu.edu/small-scale-poultry-housing">Penn State Extension</a>
```

### What the page may claim

- A figure that appears on the page you link, with the organisation, the page title, and the date that page prints.
- Imperial and metric for the same quantity. Square metres are square feet × `0.09290304`. Centimetres are inches × `2.54`. Say when a value is rounded.
- That two sources disagree, and show both numbers. Do not average them into a new number.
- Arithmetic on a floor area and a flock size printed in a public listing. Label it as arithmetic. Do not call it a test.

### What the page must not claim

- That this site keeps chickens, has built a coop, or has tested a product.
- A statistic, a percentage of “most coops”, or a breed-by-breed allowance that the cited page does not state.
- Copied paragraphs. A short quotation, marked as a quotation and linked, is fine when the wording itself is the evidence.
- A local law as if it applied outside the place that wrote it.
- An affiliate link before that program has actually been joined, or a tracking ID that has not been issued.

The space guide’s numbers live in `data/space-guidelines.json` and are interpreted by `scripts/space_math.py` and `assets/calculator.js`. Those two files must keep returning the same rows. The test suite checks that. Change a rate in the JSON, update both interpreters if the meaning of a field changes, and update the prose on the page that cites it.

## 4. Affiliate links

Only after the owner has joined the program and given you a real tracking URL.

1. Set `affiliate: true` in the frontmatter. The build adds this notice at the top of that page and no other page:

   > Affiliate links. If you buy through a marked link on this page, we may earn a commission. The price you pay does not change.

2. Mark each paid link. Do not type the `rel` yourself:

   ```html
   <a href="https://www.example.com/product?tag=REAL_ID" data-affiliate>Product name</a>
   ```

   The build rewrites that to `rel="sponsored nofollow noopener"` and `target="_blank"`.

3. A `data-affiliate` link with `affiliate: false` fails the build. A link you marked `rel="sponsored"` yourself, without `data-affiliate`, also fails the build.

Programs named on the disclosure page, none of which are joined yet: Omlet via Awin, Amazon Associates, Chewy, and Tractor Supply. Do not invent an affiliate ID, a campaign parameter, or a link shortener.

Update `content/pages/affiliate-disclosure.html` and `content/pages/privacy.html` when the first real affiliate link is added, so those pages no longer say that no affiliate links exist.

## 5. Build, preview, and check

```bash
python3 scripts/build.py
python3 -m unittest discover -s tests -v
python3 scripts/linkcheck.py
python3 scripts/preview.py
```

Or:

```bash
make check
make preview
```

`preview.py` serves `dist/` at `http://127.0.0.1:8000/Chicken-coop-guide/` so the links match production. The link checker:

- fails if an internal link, asset, or `#fragment` does not exist
- fails if an external link returns 404 or 410
- prints a warning, and does not fail, for timeouts, HTTP 403, and HTTP 429 (some university sites block the checker and still open in a browser)

Read the warning lines. A warning is not proof the URL is alive. Open it.

`linkcheck-report.txt` is written at the repo root and is gitignored.

## 6. What you do not update by hand

- `dist/`
- `sitemap.xml` and `robots.txt` (generated)
- canonical URLs, Open Graph tags, and JSON-LD (generated from the frontmatter and `site.config.json`)
- the header and footer (edit `layout/base.html` only when the chrome itself should change)
- the list on `/guides/` (generated from `schema: article` pages)

## 7. Before you finish

- The new page has one `h1` and a description that says what the page actually decides.
- Every number is traceable to a linked page you opened.
- Internal links use a leading slash and a trailing slash for other pages.
- `python3 -m unittest discover -s tests -v` passes.
- `python3 scripts/linkcheck.py` passes for internal links, and every new external URL either returns success or is a warning you have opened yourself.
- `affiliate` is `false` unless a real joined-program link is on the page.
