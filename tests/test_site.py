"""Build, markup, and calculator tests. No network."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import build  # noqa: E402
import linkcheck  # noqa: E402
import space_math  # noqa: E402


class SiteBuildTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="coop-site-"))
        cls.dist = build.build_site(ROOT, cls.tmp)
        cls.config = build.load_config(ROOT)
        cls.guidelines = space_math.load_guidelines()

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def read(self, relative: str) -> str:
        return (self.dist / relative).read_text(encoding="utf-8")

    def test_pages_exist(self):
        for relative in (
            "index.html",
            "about/index.html",
            "privacy/index.html",
            "affiliate-disclosure/index.html",
            "coop-and-run-size/index.html",
            "404.html",
            "sitemap.xml",
            "robots.txt",
            "assets/site.css",
            "assets/calculator.js",
            ".nojekyll",
        ):
            self.assertTrue((self.dist / relative).exists(), relative)

    def test_base_path_and_canonical(self):
        base = self.config["basePath"]
        home = self.read("index.html")
        guide = self.read("coop-and-run-size/index.html")
        self.assertIn(f'href="{base}/assets/site.css"', home)
        self.assertIn(f'href="{base}/coop-and-run-size/"', home)
        self.assertIn(
            f'<link rel="canonical" href="{self.config["baseUrl"]}/coop-and-run-size/">',
            guide,
        )
        self.assertIn(f'<link rel="canonical" href="{self.config["baseUrl"]}/">', home)
        self.assertIn('rel="sponsored nofollow noopener"', self.affiliate_sample())

    def test_one_h1_and_unique_ids(self):
        for path in self.dist.rglob("*.html"):
            text = path.read_text(encoding="utf-8")
            self.assertEqual(text.count("<h1>"), 1, path)
            ids = []
            for part in text.split('id="')[1:]:
                ids.append(part.split('"', 1)[0])
            self.assertEqual(len(ids), len(set(ids)), path)

    def test_affiliate_banner_only_when_flagged(self):
        banner = "<strong>Affiliate links.</strong>"
        for relative in (
            "index.html",
            "about/index.html",
            "coop-and-run-size/index.html",
        ):
            self.assertNotIn(banner, self.read(relative))

    def test_metadata_and_sitemap(self):
        guide = self.read("coop-and-run-size/index.html")
        self.assertIn('property="og:type" content="article"', guide)
        self.assertIn('"@type": "Article"', guide)
        self.assertIn('"@type": "BreadcrumbList"', guide)
        home = self.read("index.html")
        self.assertIn('"@type": "WebSite"', home)
        missing = self.read("404.html")
        self.assertIn('content="noindex, follow"', missing)
        sitemap = self.read("sitemap.xml")
        self.assertIn(f"{self.config['baseUrl']}/coop-and-run-size/", sitemap)
        self.assertNotIn("404.html", sitemap)
        robots = self.read("robots.txt")
        self.assertIn(f"Sitemap: {self.config['baseUrl']}/sitemap.xml", robots)

    def test_chart_uses_guideline_rates(self):
        guide = self.read("coop-and-run-size/index.html")
        # 20 standard hens × 1.5 sq ft = 30 sq ft = 2.79 m².
        self.assertIn("30 sq ft", guide)
        self.assertIn("2.79 m²", guide)
        # 20 × 10 sq ft of run.
        self.assertIn("200 sq ft", guide)
        self.assertIn("18.58 m²", guide)
        self.assertIn("Penn State per-bird minimums", guide)

    def test_calculator_sources_are_linked(self):
        guide = self.read("coop-and-run-size/index.html")
        for source in self.guidelines["sources"]:
            self.assertIn(source["url"], guide, source["id"])
        allowed = {source["url"] for source in self.guidelines["sources"]}
        allowed.add(self.config["repository"])
        for url in urls_in(guide):
            if url.startswith(self.config["baseUrl"]):
                continue
            if url.rstrip("/") == "https://schema.org":
                continue
            self.assertIn(url, allowed, url)

    def test_internal_links(self):
        failures = linkcheck.check_internal(
            self.dist, self.config["basePath"], self.config["baseUrl"]
        )
        self.assertEqual(failures, [])

    def test_site_name_comes_from_config(self):
        home = self.read("index.html")
        name = self.config["siteName"]
        self.assertIn(f"<h1>{name}</h1>", home)
        self.assertIn(f"<title>{name}</title>", home)
        self.assertIn(f'"name": "{name}"', home)

    def affiliate_sample(self) -> str:
        body = (
            '<p><a href="https://example.com/product" data-affiliate>Product</a> '
            '<a href="/about/">About</a></p>'
        )
        meta = {
            "title": "Sample",
            "description": "Sample page for the affiliate attribute test.",
            "path": "/sample/",
            "updated": "2026-11-18",
            "published": "2026-11-18",
            "schema": "webpage",
            "nav": False,
            "nav_label": "Sample",
            "nav_order": 90,
            "affiliate": True,
            "sitemap": False,
            "robots": "noindex, follow",
            "draft": False,
            "source": "sample",
            "body": body,
        }
        pages = build.load_pages(ROOT)
        layout = (ROOT / "layout" / "base.html").read_text(encoding="utf-8")
        rendered = build.render_page(meta, pages, self.config, layout, self.guidelines)
        self.assertIn("<strong>Affiliate links.</strong>", rendered)
        self.assertIn('target="_blank"', rendered)
        self.assertIn(f'href="{self.config["basePath"]}/about/"', rendered)
        self.assertIn('href="https://example.com/product"', rendered)
        plain = dict(meta, affiliate=False, body='<p><a data-affiliate href="https://example.com">X</a></p>')
        with self.assertRaises(build.BuildError):
            build.prepare_body(plain["body"], plain, self.config, self.guidelines)
        return rendered

    def test_calculator_matches_python(self):
        node = shutil.which("node")
        if node is None:
            self.skipTest("node is not installed")
        script = r"""
const fs = require("fs");
const calc = require(process.env.CALC_JS);
const data = JSON.parse(fs.readFileSync(process.env.GUIDE_JSON, "utf8"));
const cases = [];
for (const bird of ["bantam", "standard", "large"]) {
  for (const housing of ["freerange", "run", "indoor"]) {
    for (const n of [1, 3, 6, 7, 20, 40]) {
      cases.push(calc.digest(bird, housing, n, data));
    }
  }
}
process.stdout.write(JSON.stringify(cases));
"""
        completed = subprocess.run(
            [node, "-e", script],
            check=True,
            capture_output=True,
            text=True,
            env={
                **dict(**{k: v for k, v in __import__("os").environ.items()}),
                "CALC_JS": str(ROOT / "assets" / "calculator.js"),
                "GUIDE_JSON": str(ROOT / "data" / "space-guidelines.json"),
            },
        )
        js_cases = json.loads(completed.stdout)
        py_cases = []
        for bird in ("bantam", "standard", "large"):
            for housing in ("freerange", "run", "indoor"):
                for n in (1, 3, 6, 7, 20, 40):
                    py_cases.append(space_math.digest(bird, housing, n, self.guidelines))
        self.assertEqual(js_cases, py_cases)

    def test_known_flock_totals(self):
        result = space_math.digest("standard", "run", 6, self.guidelines)
        rows = {
            (section["id"], row["key"]): row
            for section in result["sections"]
            for row in section["rows"]
        }
        self.assertEqual(rows[("coop-primary", "psu-min")]["total_low"], 9)
        self.assertEqual(rows[("coop-primary", "point-3")]["total_low"], 18)
        self.assertEqual(rows[("coop-primary", "umn")]["total_high"], 30)
        self.assertEqual(rows[("run-extension", "psu-run")]["total_low"], 48)
        self.assertEqual(rows[("run-extension", "ext-run")]["total_high"], 60)
        self.assertEqual(rows[("nests", "psu")]["total_low"], 3)
        self.assertEqual(rows[("nests", "rspca-uk")]["total_low"], 2)
        indoor = space_math.digest("standard", "indoor", 4, self.guidelines)
        indoor_rows = {
            (section["id"], row["key"]): row
            for section in indoor["sections"]
            for row in section["rows"]
        }
        self.assertEqual(indoor_rows[("coop-primary", "osu-indoor")]["total_low"], 32)
        self.assertEqual(indoor_rows[("coop-primary", "osu-indoor")]["total_high"], 40)
        self.assertEqual(space_math.au_area_m2(4, "standard", self.guidelines), 3.4)
        self.assertEqual(space_math.au_area_m2(7, "bantam", self.guidelines), 3.3)
        self.assertEqual(space_math.psu_nests(20, self.guidelines), 6)

    def test_egg_table_matches_formula(self):
        import os
        import re

        page = self.read("how-many-chickens-for-eggs/index.html")
        self.assertIn('id="calculator"', page)
        self.assertIn('id="egg-calculator"', page)
        self.assertIn(f'{self.config["basePath"]}/assets/egg-calculator.js', page)
        self.assertNotIn("Affiliate links.", page)
        self.assertNotIn("data-affiliate", page)
        self.assertIn(f"{self.config['baseUrl']}/how-many-chickens-for-eggs/", self.read("sitemap.xml"))
        for url in EGG_SOURCE_URLS:
            self.assertIn(url, page, url)
        for people, eggs in (("2", "14"), ("4", "28"), ("6", "42")):
            self.assertIn(f'data-people="{people}" data-kind="eggs">{eggs}<', page)
        cells = re.findall(
            r'data-people="(\d+)" data-rate="([a-z0-9-]+)">(\d+)<',
            page,
        )
        self.assertEqual(len(cells), 13, cells)
        seen = set()
        for people, rate_id, text in cells:
            num, den = EGG_RATES[rate_id]
            eggs = int(people) * 7
            self.assertEqual(int(text), hens_needed(eggs, num, den), (people, rate_id))
            seen.add((people, rate_id))
        self.assertEqual(
            seen,
            {
                ("2", "uf-90"),
                ("2", "uf-65"),
                ("2", "ncsu-50"),
                ("4", "uf-90"),
                ("4", "uf-65"),
                ("4", "ncsu-50"),
                ("4", "uq-4"),
                ("4", "uq-5"),
                ("4", "unh-06"),
                ("4", "unh-09"),
                ("6", "uf-90"),
                ("6", "uf-65"),
                ("6", "ncsu-50"),
            },
        )
        node = shutil.which("node")
        if node is None:
            self.skipTest("node is not installed")
        script = r"""
const calc = require(process.env.EGG_JS);
const rates = calc.RATES.map((rate) => ({
  id: rate.id,
  dailyNum: rate.dailyNum,
  dailyDen: rate.dailyDen,
  weeklyNum: rate.weeklyNum,
  weeklyDen: rate.weeklyDen,
}));
const samples = [];
for (const rate of calc.RATES) {
  for (const eggs of [1, 7, 14, 28, 42, 100]) {
    samples.push([rate.id, eggs, calc.hensNeeded(eggs, rate.dailyNum, rate.dailyDen)]);
  }
}
process.stdout.write(JSON.stringify({
  companyMin: calc.COMPANY_MIN,
  rates,
  samples,
  floor: [calc.birdsToKeep(1), calc.birdsToKeep(2), calc.birdsToKeep(3), calc.birdsToKeep(8)],
}));
"""
        completed = subprocess.run(
            [node, "-e", script],
            check=True,
            capture_output=True,
            text=True,
            env={**os.environ, "EGG_JS": str(ROOT / "assets" / "egg-calculator.js")},
        )
        payload = json.loads(completed.stdout)
        self.assertEqual(payload["companyMin"], 3)
        self.assertEqual(payload["floor"], [3, 3, 3, 8])
        self.assertEqual({item["id"] for item in payload["rates"]}, set(EGG_RATES))
        for item in payload["rates"]:
            num, den = EGG_RATES[item["id"]]
            self.assertEqual((item["dailyNum"], item["dailyDen"]), (num, den))
            self.assertEqual(
                item["weeklyNum"] * den,
                item["weeklyDen"] * 7 * num,
                item["id"],
            )
        for rate_id, eggs, js_hens in payload["samples"]:
            num, den = EGG_RATES[rate_id]
            self.assertEqual(js_hens, hens_needed(eggs, num, den), (rate_id, eggs))


EGG_RATES = {
    "uf-90": (9, 10),
    "unh-09": (9, 10),
    "uq-4": (4, 7),
    "uq-5": (5, 7),
    "uf-65": (13, 20),
    "unh-06": (3, 5),
    "ncsu-50": (1, 2),
}

EGG_SOURCE_URLS = (
    "https://extension.unh.edu/blog/2025/07/all-about-eggs-audio",
    "https://extension.unh.edu/resource/producing-your-own-eggs",
    "https://qaafi.uq.edu.au/blog/2022/04/keeping-chickens-home",
    "https://pubs.nmsu.edu/_circulars/CR477.pdf",
    "https://ask.ifas.ufl.edu/publication/PS029/pdf",
    "https://content.ces.ncsu.edu/keeping-garden-chickens-in-north-carolina",
    "https://www.rspca.org.uk/adviceandwelfare/pets/chickens",
    "https://www.vt.edu/content/dam/pubs_ext_vt_edu/APSC/apsc-172/APSC-172.pdf",
    "https://livestockconservancy.org/heritage-breeds/heritage-breed-chickens-comparison-chart/",
)


def hens_needed(eggs_per_week: int, daily_num: int, daily_den: int) -> int:
    """Smallest whole hen count at or above eggs / (7 × daily rate)."""
    numerator = eggs_per_week * daily_den
    denominator = 7 * daily_num
    return (numerator + denominator - 1) // denominator


def urls_in(page: str) -> list[str]:
    urls = []
    for chunk in page.split("https://")[1:]:
        url = "https://" + chunk.split('"', 1)[0].split("<", 1)[0].split(" ", 1)[0]
        url = url.rstrip(").,")
        urls.append(url)
    return urls


if __name__ == "__main__":
    unittest.main()
