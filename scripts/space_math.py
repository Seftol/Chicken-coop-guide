"""Coop, run, nest, and roost arithmetic.

Numbers come from data/space-guidelines.json. assets/calculator.js
implements the same rows. tests/test_site.py fails if the two diverge.

Rates are multiplied by flock size. Overlapping sources are listed as
separate rows and are never averaged or added together.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "space-guidelines.json"

BIRDS = ("bantam", "standard", "large")
HOUSINGS = ("freerange", "run", "indoor")

HOUSING_PHRASE = {
    "freerange": "free-range by day and housed at night",
    "run": "kept in a coop and run",
    "indoor": "housed indoors with no outdoor access",
}


def load_guidelines(path: Path = DATA_PATH) -> dict:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def _ceil_div(numerator: int, denominator: int) -> int:
    return math.ceil(numerator / denominator)


def psu_nests(n: int, data: dict) -> int:
    psu = data["psu"]
    extra_hens = max(0, n - psu["nestFirstHens"])
    return psu["nestFirstBoxes"] + math.ceil(extra_hens / psu["nestAdditionalHens"])


def au_area_m2(n: int, bird: str, data: dict) -> float:
    au = data["rspcaAu"]
    if bird == "bantam":
        included = au["includedBantam"]
        extra = au["extraBantamM2"]
    else:
        included = au["includedLarge"]
        extra = au["extraLargeM2"]
    if n <= included:
        return float(au["baseM2"])
    return float(au["baseM2"]) + extra * (n - included)


def flock_phrase(bird: str, n: int) -> str:
    if bird == "bantam":
        noun = "bantam" if n == 1 else "bantams"
    elif bird == "standard":
        noun = "standard laying hen" if n == 1 else "standard laying hens"
    elif bird == "large":
        noun = "large chicken" if n == 1 else "large chickens"
    else:
        raise KeyError(bird)
    return f"{n} {noun}"


def _row(key, unit, total_low, total_high, source, per_low=None, per_high=None, per_text=None):
    return {
        "key": key,
        "unit": unit,
        "per_low": per_low,
        "per_high": per_high,
        "per_text": per_text,
        "total_low": total_low,
        "total_high": total_high,
        "source": source,
    }


def _sqft(key, rate_low, rate_high, n, source):
    return _row(
        key,
        "sqft",
        rate_low * n,
        rate_high * n,
        source,
        per_low=rate_low,
        per_high=rate_high,
    )


def _m2(key, rate_low, rate_high, n, source):
    return _row(
        key,
        "m2",
        rate_low * n,
        rate_high * n,
        source,
        per_low=rate_low,
        per_high=rate_high,
    )


def _count(key, low, high, per_text, source):
    return _row(key, "count", low, high, source, per_text=per_text)


def _section(section_id, heading, caption, rows, notes=None, intro=""):
    return {
        "id": section_id,
        "heading": heading,
        "caption": caption,
        "intro": intro,
        "notes": list(notes or []),
        "rows": rows,
    }


def compute(bird: str, housing: str, n: int, data: dict | None = None) -> dict:
    if data is None:
        data = load_guidelines()
    if bird not in BIRDS:
        raise ValueError(f"unknown bird size: {bird}")
    if housing not in HOUSINGS:
        raise ValueError(f"unknown housing: {housing}")
    if not isinstance(n, int) or isinstance(n, bool) or n < data["flockMin"] or n > data["flockMax"]:
        raise ValueError(f"flock size must be an integer from {data['flockMin']} to {data['flockMax']}")

    sections = []
    sections.append(_coop_primary(bird, housing, n, data))
    if housing == "indoor":
        sections.append(_coop_table_context(bird, n, data))
    sections.append(_coop_rspca_uk(n, data))
    sections.append(_run_extension(bird, housing, n, data))
    bhwt = _run_bhwt(bird, housing, n, data)
    if bhwt is not None:
        sections.append(bhwt)
    sections.append(_au_section(bird, housing, n, data))
    sections.append(_nests(n, data))
    sections.append(_roosts(bird, n, data))
    return {
        "lead": f"{flock_phrase(bird, n).capitalize()}, {HOUSING_PHRASE[housing]}.",
        "sections": sections,
    }


def _coop_primary(bird, housing, n, data):
    osu = data["osu"]
    uf = data["uf"]
    udel = data["udel"]
    umn = data["umn"]
    psu_bird = data["psu"]["birds"][bird]
    if housing == "indoor":
        return _section(
            "coop-primary",
            "Coop floor",
            "No outdoor access",
            [
                _sqft(
                    "osu-indoor",
                    osu["indoorLow"],
                    osu["indoorHigh"],
                    n,
                    "Oregon State University Extension, EC 1644. Indoor floor when birds have no outdoor access. The publication states this per bird and does not publish a separate bantam or heavy-breed figure.",
                )
            ],
            intro="This is the extension figure written for birds that do not go outside. It is not added to a run.",
        )

    rows = []
    notes = []
    if bird == "bantam":
        rows.append(
            _sqft(
                "psu-table",
                psu_bird["coop"],
                psu_bird["coop"],
                n,
                "Penn State Extension housing table, bantam row. This is the minimum indoor figure in a table that also lists a separate outdoor run. Oregon State, Florida, Delaware, and Minnesota do not publish a bantam coop allowance on the pages cited here, so their per-bird rates are not applied to this row.",
            )
        )
    elif bird == "standard":
        rows.extend(
            [
                _sqft(
                    "psu-min",
                    psu_bird["coop"],
                    psu_bird["coop"],
                    n,
                    "Penn State Extension housing table, laying-hen row. Minimum indoor space, listed beside a separate outdoor run. It is also the low end of Penn State's 1.5–3 sq ft indoor range for birds eight weeks and older.",
                ),
                _sqft(
                    "udel",
                    udel["coopLow"],
                    udel["coopHigh"],
                    n,
                    "University of Delaware Cooperative Extension fact sheet. Indoor space per chicken, with a run listed separately.",
                ),
                _sqft(
                    "point-3",
                    osu["withOutdoorSqft"],
                    osu["withOutdoorSqft"],
                    n,
                    "Three publications meet at this rate: Oregon State, for birds with a run or other outdoor access; Florida's minimum house floor; and the top of Penn State's 1.5–3 sq ft range for birds eight weeks and older. It is also the top of Delaware's range and the bottom of Minnesota's.",
                ),
                _sqft(
                    "umn",
                    umn["coopLow"],
                    umn["coopHigh"],
                    n,
                    "University of Minnesota Extension, raising chickens for eggs. Minimum indoor space per bird. The page describes letting birds out in the morning, and it does not give a run size.",
                ),
            ]
        )
        notes.append(
            "Rows in this group overlap because the sources overlap. Do not add them together."
        )
    else:
        rows.extend(
            [
                _sqft(
                    "psu-table",
                    psu_bird["coop"],
                    psu_bird["coop"],
                    n,
                    "Penn State Extension housing table, large-chicken row. This is the only indoor minimum on these pages that is labeled for large chickens. The table also lists a separate outdoor run.",
                ),
                _sqft(
                    "udel",
                    udel["coopLow"],
                    udel["coopHigh"],
                    n,
                    "University of Delaware Cooperative Extension. Stated per chicken, not as a heavy-breed rate.",
                ),
                _sqft(
                    "general-3",
                    osu["withOutdoorSqft"],
                    osu["withOutdoorSqft"],
                    n,
                    "Oregon State's with-outdoor-access rate and Florida's house minimum, both stated per bird. Neither page adds extra floor area for heavy breeds. Florida notes that dual-purpose birds are larger than smaller layers and may need more space, without giving a second number.",
                ),
                _sqft(
                    "umn",
                    umn["coopLow"],
                    umn["coopHigh"],
                    n,
                    "University of Minnesota Extension. Indoor space per bird, not a heavy-breed rate.",
                ),
            ]
        )
        notes.insert(
            0,
            "Rows in this group overlap because the sources overlap. Do not add them together.",
        )
        notes.append(
            "Penn State's large-chicken minimum is lower than the general 3 sq ft figure used by Oregon State and Florida. Both are shown. They are not combined into a new number."
        )
    if housing == "freerange":
        notes.append(
            "A yard does not reduce the coop. Penn State says to count indoor floor only, because birds are inside at night and in bad weather, and not to treat the outdoor run as part of that indoor allowance."
        )
    else:
        notes.append(
            "Oregon State counts a run as outdoor access. The indoors-only rate on that page is a different case, available under the Indoors only choice."
        )
    return _section(
        "coop-primary",
        "Coop floor",
        "Extension figures for birds that go outside",
        rows,
        notes=notes,
        intro="Night housing. Free-range and coop-and-run use the same coop sources.",
    )


def _coop_table_context(bird, n, data):
    psu = data["psu"]
    if bird == "standard":
        row = _sqft(
            "psu-adult",
            psu["adultLow"],
            psu["adultHigh"],
            n,
            "Penn State Extension, space as birds grow: indoor floor for birds eight weeks and older. The article says to count indoor area only and not to fold the run into it. It does not label this range as housing with no outdoor access.",
        )
        caption = "Penn State adult indoor range, not labeled as indoor-only"
    else:
        rate = psu["birds"][bird]["coop"]
        row = _sqft(
            "psu-table",
            rate,
            rate,
            n,
            "Penn State Extension housing table. This indoor minimum is published in a table that also lists an outdoor run, so it is not an indoor-only allowance.",
        )
        caption = "Penn State table minimum, published with a run"
    return _section(
        "coop-context",
        "Coop floor, other published indoor figure",
        caption,
        [row],
        notes=["Shown so the lower figure is not hidden. It is not the indoors-only rate."],
    )


def _coop_rspca_uk(n, data):
    uk = data["rspcaUk"]
    per_dense = 1 / uk["maxBirdsPerM2"]
    return _section(
        "coop-rspca-uk",
        "Coop floor, RSPCA (United Kingdom)",
        "Pet-chicken housing guidance",
        [
            _m2(
                "rspca-uk-preferred",
                uk["preferredM2"],
                uk["preferredM2"],
                n,
                "RSPCA (UK), keeping chickens as pets: at least this much housing per bird where possible. The page does not reduce it for bantams or increase it for heavy breeds.",
            ),
            _m2(
                "rspca-uk-densest",
                per_dense,
                per_dense,
                n,
                "Same RSPCA (UK) page: if the preferred area is not possible, do not stock more tightly than three birds per square metre of coop.",
            ),
        ],
        notes=[
            "These are housing figures, not a run. The RSPCA (UK) page does not give a numeric run size."
        ],
    )


def _run_extension(bird, housing, n, data):
    if housing == "indoor":
        return _section(
            "run-extension",
            "Run",
            "No outdoor access",
            [],
            intro="Not applicable. Oregon State's indoors-only coop figure is the extension allowance for this choice. Run rates are on the other two housing choices.",
        )
    psu_bird = data["psu"]["birds"][bird]
    uf = data["uf"]
    udel = data["udel"]
    rows = [
        _sqft(
            "psu-run",
            psu_bird["run"],
            psu_bird["run"],
            n,
            "Penn State Extension housing table, outdoor run for this row of the table (bantam, laying hen, or large chicken).",
        )
    ]
    if bird == "standard":
        rows.append(
            _sqft(
                "ext-run",
                uf["runLow"],
                uf["runHigh"],
                n,
                "University of Florida IFAS and University of Delaware Cooperative Extension both state this run range per bird. The low end matches Penn State's laying-hen run.",
            )
        )
    elif bird == "large":
        rows.append(
            _sqft(
                "general-run",
                uf["runLow"],
                uf["runHigh"],
                n,
                "Florida and Delaware state this range per chicken or per bird, without a heavy-breed row. Penn State's large-chicken run is the separate row above.",
            )
        )
    if housing == "freerange":
        intro = (
            "No page cited here gives a square-foot rule for an open yard. "
            "The rates below are for an enclosed run, if you build one for the hours the birds are not out. "
            "They do not replace the coop, and they are not added on top of a yard."
        )
    else:
        intro = (
            "Outdoor run for birds whose daytime space is the run. "
            "A run counts as outdoor access on the Oregon State page, so the coop stays on the with-outdoor figures above."
        )
    return _section(
        "run-extension",
        "Run",
        "Extension outdoor-run rates",
        rows,
        intro=intro,
    )


def _run_bhwt(bird, housing, n, data):
    if housing == "indoor" or bird != "standard":
        return None
    bhwt = data["bhwt"]
    return _section(
        "run-bhwt",
        "Run, British Hen Welfare Trust",
        "Clear run floor for the hens the Trust rehomes",
        [
            _m2(
                "bhwt-excage",
                bhwt["runExCageM2"],
                bhwt["runExCageM2"],
                n,
                "British Hen Welfare Trust, for ex-caged hens. Clear floor only: do not count space under the coop or the space taken by drinkers and feeders. The Trust also wants these hens to be able to free-range when they can.",
            ),
            _m2(
                "bhwt-other",
                bhwt["runOtherM2"],
                bhwt["runOtherM2"],
                n,
                "British Hen Welfare Trust, for hens from other farming systems. Same clear-floor rule. Not applied to the bantam or large-chicken choices: the Trust describes the hens it rehomes as medium-sized ex-commercial birds.",
            ),
        ],
        notes=[
            "These run areas are larger than the US extension run rates. Both are shown. A flock that free-ranges still needs an enclosure of this size, in the Trust's adoption rules, for the times the hens are shut in."
        ],
    )


def _au_section(bird, housing, n, data):
    au = data["rspcaAu"]
    total = au_area_m2(n, bird, data)
    formula = _row(
        "au-formula",
        "m2",
        total,
        total,
        "RSPCA Australia knowledgebase, updated 19 September 2023. Minimum combined coop and run: 3 m² for up to three large birds or six bantams, then at least 0.4 m² more per additional large bird or 0.3 m² more per additional bantam. “Large” here means not a bantam. The page does not add a further amount for heavy breeds.",
    )
    notes = []
    rows = [formula]
    if bird == "bantam":
        notes.append(
            "The 2021 RSPCA Australia article states 2–3.5 m² per hen and does not give a bantam figure, so that range is not applied here."
        )
    else:
        rows.append(
            _m2(
                "au-blog",
                au["blogM2Low"],
                au["blogM2High"],
                n,
                "RSPCA Australia, 18 May 2021: an absolute minimum of this much enclosure per hen, and ideally more. The same article says many commercially sold coops are too small. This is a different, higher statement than the 2023 knowledgebase formula. They are not averaged.",
            )
        )
    if housing == "freerange":
        intro = (
            "Combined coop and run, not a coop figure and not a yard figure. "
            "The knowledgebase says this minimum can suit birds that roam by day and are housed at night. "
            "If they live in the enclosure most of the time, the same page says the enclosure must be significantly larger, without stating how much larger."
        )
    elif housing == "run":
        intro = (
            "Combined coop and run. The knowledgebase says birds kept in the coop or run most of the time need significantly more than this minimum. "
            "It does not say how much more. The 2021 article's per-hen range is the higher RSPCA Australia figure."
        )
    else:
        intro = (
            "Shown for comparison only. The knowledgebase describes a coop plus a run, or daytime ranging, not a closed indoor house. "
            "Do not read this total as an indoors-only floor area."
        )
    return _section(
        "au-combined",
        "RSPCA Australia, coop and run together",
        "Combined enclosure, not a separate coop and run",
        rows,
        notes=notes,
        intro=intro,
    )


def _nests(n, data):
    osu = data["osu"]
    uf = data["uf"]
    umn = data["umn"]
    udel = data["udel"]
    uk = data["rspcaUk"]
    au = data["rspcaAu"]
    rows = [
        _count(
            "osu-per-4",
            _ceil_div(n, osu["nestPer"]),
            _ceil_div(n, osu["nestPer"]),
            "1 per 4 hens",
            "Oregon State University Extension: one nest box for about every four birds. Box about 12 × 12 × 12 inches.",
        ),
        _count(
            "uf-per-5",
            _ceil_div(n, uf["nestPer"]),
            _ceil_div(n, uf["nestPer"]),
            "1 per 5 hens",
            "University of Florida IFAS: at least one nest box for every five hens. Box 12 × 12 × 12 inches.",
        ),
        _count(
            "umn",
            _ceil_div(n, umn["nestFewerPer"]),
            _ceil_div(n, umn["nestMorePer"]),
            "1 per 4–5 hens",
            "University of Minnesota Extension: one nest box per 4 to 5 birds. The lower count is one box per five hens; the higher count is one box per four.",
        ),
        _count(
            "udel",
            _ceil_div(n, udel["nestFewerPer"]),
            _ceil_div(n, udel["nestMorePer"]),
            "1 per 3–4 hens",
            "University of Delaware Cooperative Extension: one box per 3–4 hens. The lower count is one per four; the higher count is one per three.",
        ),
        _count(
            "rspca-uk",
            max(uk["nestMinBoxes"], _ceil_div(n, uk["nestPer"])),
            max(uk["nestMinBoxes"], _ceil_div(n, uk["nestPer"])),
            "1 per 5, at least 2",
            "RSPCA (UK): at least one box per five hens, and at least two boxes for any group. Each box at least 30 × 30 × 30 cm.",
        ),
        _count(
            "rspca-au",
            _ceil_div(n, au["nestFewerPer"]),
            _ceil_div(n, au["nestMorePer"]),
            "1 per 2–4 hens",
            "RSPCA Australia knowledgebase: at least one box for every 2–4 hens. The lower count is one per four; the higher count is one per two. Boxes about 30 × 30 cm.",
        ),
        _count(
            "psu",
            psu_nests(n, data),
            psu_nests(n, data),
            "2 for the first 4, then 1 per 4",
            "Penn State Extension: two nests for the first four hens, then one more nest for every four additional hens. Each nest at least 12 × 12 inches, and larger for larger birds.",
        ),
    ]
    return _section(
        "nests",
        "Nest boxes",
        "Counts for laying hens. Roosters are not included.",
        rows,
        notes=[
            "A one-hen flock is still given two boxes under the Penn State rule and under the RSPCA (UK) minimum of two. The one-per-four and one-per-five rules give that hen one box."
        ],
    )


def _length(key, per, n, unit, source):
    return _row(key, unit, per * n, per * n, source, per_low=per, per_high=per)


def _roosts(bird, n, data):
    psu = data["psu"]["birds"][bird]
    osu = data["osu"]
    umn = data["umn"]
    uk = data["rspcaUk"]
    au = data["rspcaAu"]
    bhwt = data["bhwt"]
    notes = []
    if bird == "bantam":
        rows = [
            _length(
                "psu",
                psu["roostIn"],
                n,
                "in",
                "Penn State Extension: four inches of roost per bantam. The same paragraph sets bantam roosts 12–18 inches off the floor.",
            ),
            _length(
                "rspca",
                uk["roostCm"],
                n,
                "cm",
                "RSPCA (UK) and RSPCA Australia both say at least 15 cm of roost per bird. Neither page publishes a shorter bantam length.",
            ),
        ]
        notes.append(
            "Oregon State's 5–10 inches per bird is not split by size, except that Silkie roosts should be lower (about 1 foot off the floor), which is height rather than length. The British Hen Welfare Trust's 25 cm is for the medium-sized ex-commercial hens it rehomes, so it is not applied to bantams."
        )
    elif bird == "large":
        rows = [
            _length(
                "rspca",
                au["roostCm"],
                n,
                "cm",
                "RSPCA Australia still wants a perch for heavier chickens, set lower, about 30 cm off the floor, and at least 15 cm long per bird. RSPCA (UK) also says at least 15 cm per bird, with the height suited to the birds.",
            ),
            _row(
                "osu",
                "in",
                osu["roostLowIn"] * n,
                osu["roostHighIn"] * n,
                "Oregon State: 5–10 inches of pole per bird, not increased for heavy breeds. Included only for birds that do roost.",
                per_low=osu["roostLowIn"],
                per_high=osu["roostHighIn"],
            ),
            _length(
                "umn",
                umn["roostIn"],
                n,
                "in",
                "University of Minnesota Extension cold-weather page: generally 9 inches of roost per chicken. Not a heavy-breed measurement.",
            ),
        ]
        notes.append(
            "Penn State says not to use perches for large, structured, or meaty breeds, because jumping down can injure legs and joints. RSPCA Australia disagrees in part: it still recommends perches for heavier chickens, at a lower height. This calculator does not pick a winner. Penn State's 6-inch standard-chicken roost and the Trust's 25 cm roost are not applied to this category."
        )
    else:
        rows = [
            _row(
                "osu",
                "in",
                osu["roostLowIn"] * n,
                osu["roostHighIn"] * n,
                "Oregon State University Extension: 5–10 inches of roost pole per bird.",
                per_low=osu["roostLowIn"],
                per_high=osu["roostHighIn"],
            ),
            _length(
                "psu",
                psu["roostIn"],
                n,
                "in",
                "Penn State Extension: six inches per standard-size chicken. Roosts 18–24 inches off the floor and one foot apart, and never more than 4 feet off the floor.",
            ),
            _length(
                "umn",
                umn["roostIn"],
                n,
                "in",
                "University of Minnesota Extension, caring for chickens in cold weather: generally 9 inches of roost per chicken.",
            ),
            _length(
                "rspca",
                uk["roostCm"],
                n,
                "cm",
                "RSPCA (UK) says from 15 cm per chicken. RSPCA Australia says at least 15 cm. The UK page also suggests a perch height of about 40 cm.",
            ),
            _length(
                "bhwt",
                bhwt["roostCm"],
                n,
                "cm",
                "British Hen Welfare Trust adoption guidance: 25 cm of perch per hen, for the ex-commercial hens the Trust rehomes.",
            ),
        ]
        notes.append(
            "The widest span here runs from Oregon State's low end (5 inches) to its high end (10 inches). The Trust's 25 cm is about 9.8 inches, inside that span. Fifteen centimetres is about 5.9 inches."
        )
    return _section(
        "roosts",
        "Roost length",
        "Length, not height. Totals assume every bird roosts at once.",
        rows,
        notes=notes,
    )


def digest(bird: str, housing: str, n: int, data: dict | None = None):
    """Stable structure for the parity test. Floats are rounded."""

    def num(value):
        if value is None:
            return None
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return round(float(value), 5)
        return value

    result = compute(bird, housing, n, data)
    sections = []
    for section in result["sections"]:
        sections.append(
            {
                "id": section["id"],
                "heading": section["heading"],
                "caption": section["caption"],
                "intro": section["intro"],
                "notes": section["notes"],
                "rows": [
                    {
                        "key": row["key"],
                        "unit": row["unit"],
                        "per_text": row["per_text"],
                        "per_low": num(row["per_low"]),
                        "per_high": num(row["per_high"]),
                        "total_low": num(row["total_low"]),
                        "total_high": num(row["total_high"]),
                        "source": row["source"],
                    }
                    for row in section["rows"]
                ],
            }
        )
    return {"lead": result["lead"], "sections": sections}


def chart_html(data: dict | None = None) -> str:
    """Static chart for standard hens. Works without JavaScript."""
    if data is None:
        data = load_guidelines()
    factor = data["sqftToM2"]
    inch_to_cm = data["inchToCm"]
    standard = data["psu"]["birds"]["standard"]
    three = data["osu"]["withOutdoorSqft"]
    if data["uf"]["coopSqft"] != three or data["psu"]["adultHigh"] != three:
        raise SystemExit(
            "The 3 sq ft chart column assumes Oregon State, Florida, and the top of the Penn State adult range still match."
        )
    if data["uf"]["runLow"] != standard["run"] or data["udel"]["runLow"] != standard["run"]:
        raise SystemExit("The 8 sq ft run column assumes Penn State, Florida, and Delaware still share that low end.")
    if data["uf"]["runHigh"] != data["udel"]["runHigh"]:
        raise SystemExit("The upper run column assumes Florida and Delaware still share a high end.")

    start = data["chart"]["from"]
    end = data["chart"]["to"]
    coop_rates = [
        ("1.5 sq ft, Penn State minimum", standard["coop"]),
        ("3 sq ft, shared figure", three),
        ("5 sq ft, Minnesota high", data["umn"]["coopHigh"]),
    ]
    run_rates = [
        ("8 sq ft, Penn State minimum", standard["run"]),
        ("10 sq ft, Florida and Delaware high", data["uf"]["runHigh"]),
    ]

    def area_cell(total_sqft: float) -> str:
        return (
            f"{_num(total_sqft)} sq ft"
            f'<span class="metric">{total_sqft * factor:.2f} m²</span>'
        )

    area_head = "".join(f"<th scope=\"col\">{_escape(label)}</th>" for label, _rate in coop_rates + run_rates)
    area_rows = []
    for birds in range(start, end + 1):
        cells = "".join(
            f"<td>{area_cell(rate * birds)}</td>" for _label, rate in coop_rates + run_rates
        )
        area_rows.append(f"<tr><th scope=\"row\">{birds}</th>{cells}</tr>")

    fitting_rows = []
    for birds in range(start, end + 1):
        per_four = _ceil_div(birds, data["osu"]["nestPer"])
        uk = max(data["rspcaUk"]["nestMinBoxes"], _ceil_div(birds, data["rspcaUk"]["nestPer"]))
        psu = psu_nests(birds, data)
        psu_in = standard["roostIn"] * birds
        osu_in = data["osu"]["roostHighIn"] * birds
        bhwt_cm = data["bhwt"]["roostCm"] * birds
        fitting_rows.append(
            "<tr>"
            f"<th scope=\"row\">{birds}</th>"
            f"<td>{per_four}</td>"
            f"<td>{uk}</td>"
            f"<td>{psu}</td>"
            f"<td>{_length_cell(psu_in, psu_in * inch_to_cm, 'in')}</td>"
            f"<td>{_length_cell(osu_in, osu_in * inch_to_cm, 'in')}</td>"
            f"<td>{_length_cell(bhwt_cm / inch_to_cm, bhwt_cm, 'cm')}</td>"
            "</tr>"
        )

    bantam = data["psu"]["birds"]["bantam"]
    large = data["psu"]["birds"]["large"]
    small = f"""
<table class="rates">
  <caption>Penn State per-bird minimums for the sizes that are not in the long chart. Other publications do not publish this three-way split.</caption>
  <thead>
    <tr>
      <th scope="col">Penn State row</th>
      <th scope="col">Indoor minimum</th>
      <th scope="col">Outdoor run</th>
      <th scope="col">Roost</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <th scope="row">Bantam</th>
      <td>{area_cell(bantam["coop"])}</td>
      <td>{area_cell(bantam["run"])}</td>
      <td>{_length_cell(bantam["roostIn"], bantam["roostIn"] * inch_to_cm, "in")} per bird</td>
    </tr>
    <tr>
      <th scope="row">Large chicken</th>
      <td>{area_cell(large["coop"])}</td>
      <td>{area_cell(large["run"])}</td>
      <td>No perch length. Penn State says not to use perches for large, structured, or meaty breeds.</td>
    </tr>
  </tbody>
</table>
"""
    return f"""
<div class="table-scroll" tabindex="0" aria-label="Coop and run chart, scroll sideways on a small screen">
<table class="chart">
  <caption>Standard laying hens with a coop and a run. Each cell is birds × the rate in the column heading. Square metres are square feet × 0.09290304, rounded to two decimals. Do not add the coop columns together.</caption>
  <thead>
    <tr>
      <th scope="col">Birds</th>
      {area_head}
    </tr>
  </thead>
  <tbody>
    {''.join(area_rows)}
  </tbody>
</table>
</div>
<p class="scroll-hint">On a small screen, scroll the tables sideways. The first column is the flock size.</p>
<div class="table-scroll" tabindex="0" aria-label="Nest and roost chart">
<table class="chart">
  <caption>Nest boxes and roost length for the same standard hens. Nest columns are separate rules, not a range to add. The 10-inch roost is the top of Oregon State's 5–10 inch range. The 25 cm roost is the British Hen Welfare Trust figure.</caption>
  <thead>
    <tr>
      <th scope="col">Birds</th>
      <th scope="col">Nests, 1 per 4 (Oregon State)</th>
      <th scope="col">Nests, 1 per 5 and at least 2 (RSPCA UK)</th>
      <th scope="col">Nests, Penn State rule</th>
      <th scope="col">Roost, 6 in (Penn State)</th>
      <th scope="col">Roost, 10 in (Oregon State high)</th>
      <th scope="col">Roost, 25 cm (BHWT)</th>
    </tr>
  </thead>
  <tbody>
    {''.join(fitting_rows)}
  </tbody>
</table>
</div>
{small}
"""


def _length_cell(inches: float, cm: float, source_unit: str) -> str:
    if source_unit == "in":
        return f"{_num(inches)} in ({_cm(cm)} cm)"
    return f"{_cm(cm)} cm ({_num(inches)} in)"


def _num(value: float) -> str:
    rounded = round(float(value), 2)
    if abs(rounded - round(rounded)) < 1e-9:
        return str(int(round(rounded)))
    if abs(rounded - round(rounded, 1)) < 1e-9:
        return f"{rounded:.1f}"
    return f"{rounded:.2f}"


def _cm(value: float) -> str:
    return _num(value)


def _escape(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )
