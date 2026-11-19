/* Global calculator for the coop-size page.
   The row math is duplicated in scripts/space_math.py.
   tests/test_site.py fails if the two disagree. */
(function (root, factory) {
  var api = factory();
  if (typeof module === "object" && module.exports) {
    module.exports = api;
  } else {
    root.CoopCalc = api;
  }
  if (typeof document !== "undefined") {
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", function () {
        api.init();
      });
    } else {
      api.init();
    }
  }
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  var BIRDS = ["bantam", "standard", "large"];
  var HOUSINGS = ["freerange", "run", "indoor"];
  var HOUSING_PHRASE = {
    freerange: "free-range by day and housed at night",
    run: "kept in a coop and run",
    indoor: "housed indoors with no outdoor access",
  };

  function ceilDiv(numerator, denominator) {
    return Math.ceil(numerator / denominator);
  }

  function psuNests(n, data) {
    var psu = data.psu;
    var extra = Math.max(0, n - psu.nestFirstHens);
    return psu.nestFirstBoxes + Math.ceil(extra / psu.nestAdditionalHens);
  }

  function auAreaM2(n, bird, data) {
    var au = data.rspcaAu;
    var included = bird === "bantam" ? au.includedBantam : au.includedLarge;
    var extra = bird === "bantam" ? au.extraBantamM2 : au.extraLargeM2;
    if (n <= included) return au.baseM2;
    return au.baseM2 + extra * (n - included);
  }

  function flockPhrase(bird, n) {
    var noun;
    if (bird === "bantam") noun = n === 1 ? "bantam" : "bantams";
    else if (bird === "standard") noun = n === 1 ? "standard laying hen" : "standard laying hens";
    else if (bird === "large") noun = n === 1 ? "large chicken" : "large chickens";
    else throw new Error("unknown bird size: " + bird);
    return n + " " + noun;
  }

  function row(key, unit, totalLow, totalHigh, source, perLow, perHigh, perText) {
    return {
      key: key,
      unit: unit,
      per_low: perLow == null ? null : perLow,
      per_high: perHigh == null ? null : perHigh,
      per_text: perText == null ? null : perText,
      total_low: totalLow,
      total_high: totalHigh,
      source: source,
    };
  }

  function sqft(key, rateLow, rateHigh, n, source) {
    return row(key, "sqft", rateLow * n, rateHigh * n, source, rateLow, rateHigh, null);
  }

  function m2(key, rateLow, rateHigh, n, source) {
    return row(key, "m2", rateLow * n, rateHigh * n, source, rateLow, rateHigh, null);
  }

  function count(key, low, high, perText, source) {
    return row(key, "count", low, high, source, null, null, perText);
  }

  function section(id, heading, caption, rows, notes, intro) {
    return {
      id: id,
      heading: heading,
      caption: caption,
      intro: intro || "",
      notes: notes || [],
      rows: rows,
    };
  }

  function length(key, per, n, unit, source) {
    return row(key, unit, per * n, per * n, source, per, per, null);
  }

  function coopPrimary(bird, housing, n, data) {
    var osu = data.osu;
    var udel = data.udel;
    var umn = data.umn;
    var psuBird = data.psu.birds[bird];
    if (housing === "indoor") {
      return section(
        "coop-primary",
        "Coop floor",
        "No outdoor access",
        [
          sqft(
            "osu-indoor",
            osu.indoorLow,
            osu.indoorHigh,
            n,
            "Oregon State University Extension, EC 1644. Indoor floor when birds have no outdoor access. The publication states this per bird and does not publish a separate bantam or heavy-breed figure."
          ),
        ],
        [],
        "This is the extension figure written for birds that do not go outside. It is not added to a run."
      );
    }
    var rows = [];
    var notes = [];
    if (bird === "bantam") {
      rows.push(
        sqft(
          "psu-table",
          psuBird.coop,
          psuBird.coop,
          n,
          "Penn State Extension housing table, bantam row. This is the minimum indoor figure in a table that also lists a separate outdoor run. Oregon State, Florida, Delaware, and Minnesota do not publish a bantam coop allowance on the pages cited here, so their per-bird rates are not applied to this row."
        )
      );
    } else if (bird === "standard") {
      rows.push(
        sqft(
          "psu-min",
          psuBird.coop,
          psuBird.coop,
          n,
          "Penn State Extension housing table, laying-hen row. Minimum indoor space, listed beside a separate outdoor run. It is also the low end of Penn State's 1.5–3 sq ft indoor range for birds eight weeks and older."
        ),
        sqft(
          "udel",
          udel.coopLow,
          udel.coopHigh,
          n,
          "University of Delaware Cooperative Extension fact sheet. Indoor space per chicken, with a run listed separately."
        ),
        sqft(
          "point-3",
          osu.withOutdoorSqft,
          osu.withOutdoorSqft,
          n,
          "Three publications meet at this rate: Oregon State, for birds with a run or other outdoor access; Florida's minimum house floor; and the top of Penn State's 1.5–3 sq ft range for birds eight weeks and older. It is also the top of Delaware's range and the bottom of Minnesota's."
        ),
        sqft(
          "umn",
          umn.coopLow,
          umn.coopHigh,
          n,
          "University of Minnesota Extension, raising chickens for eggs. Minimum indoor space per bird. The page describes letting birds out in the morning, and it does not give a run size."
        )
      );
      notes.push("Rows in this group overlap because the sources overlap. Do not add them together.");
    } else {
      rows.push(
        sqft(
          "psu-table",
          psuBird.coop,
          psuBird.coop,
          n,
          "Penn State Extension housing table, large-chicken row. This is the only indoor minimum on these pages that is labeled for large chickens. The table also lists a separate outdoor run."
        ),
        sqft(
          "udel",
          udel.coopLow,
          udel.coopHigh,
          n,
          "University of Delaware Cooperative Extension. Stated per chicken, not as a heavy-breed rate."
        ),
        sqft(
          "general-3",
          osu.withOutdoorSqft,
          osu.withOutdoorSqft,
          n,
          "Oregon State's with-outdoor-access rate and Florida's house minimum, both stated per bird. Neither page adds extra floor area for heavy breeds. Florida notes that dual-purpose birds are larger than smaller layers and may need more space, without giving a second number."
        ),
        sqft(
          "umn",
          umn.coopLow,
          umn.coopHigh,
          n,
          "University of Minnesota Extension. Indoor space per bird, not a heavy-breed rate."
        )
      );
      notes.push("Rows in this group overlap because the sources overlap. Do not add them together.");
      notes.push(
        "Penn State's large-chicken minimum is lower than the general 3 sq ft figure used by Oregon State and Florida. Both are shown. They are not combined into a new number."
      );
    }
    if (housing === "freerange") {
      notes.push(
        "A yard does not reduce the coop. Penn State says to count indoor floor only, because birds are inside at night and in bad weather, and not to treat the outdoor run as part of that indoor allowance."
      );
    } else {
      notes.push(
        "Oregon State counts a run as outdoor access. The indoors-only rate on that page is a different case, available under the Indoors only choice."
      );
    }
    return section(
      "coop-primary",
      "Coop floor",
      "Extension figures for birds that go outside",
      rows,
      notes,
      "Night housing. Free-range and coop-and-run use the same coop sources."
    );
  }

  function coopTableContext(bird, n, data) {
    var psu = data.psu;
    var item;
    var caption;
    if (bird === "standard") {
      item = sqft(
        "psu-adult",
        psu.adultLow,
        psu.adultHigh,
        n,
        "Penn State Extension, space as birds grow: indoor floor for birds eight weeks and older. The article says to count indoor area only and not to fold the run into it. It does not label this range as housing with no outdoor access."
      );
      caption = "Penn State adult indoor range, not labeled as indoor-only";
    } else {
      var rate = psu.birds[bird].coop;
      item = sqft(
        "psu-table",
        rate,
        rate,
        n,
        "Penn State Extension housing table. This indoor minimum is published in a table that also lists an outdoor run, so it is not an indoor-only allowance."
      );
      caption = "Penn State table minimum, published with a run";
    }
    return section(
      "coop-context",
      "Coop floor, other published indoor figure",
      caption,
      [item],
      ["Shown so the lower figure is not hidden. It is not the indoors-only rate."],
      ""
    );
  }

  function coopRspcaUk(n, data) {
    var uk = data.rspcaUk;
    var perDense = 1 / uk.maxBirdsPerM2;
    return section(
      "coop-rspca-uk",
      "Coop floor, RSPCA (United Kingdom)",
      "Pet-chicken housing guidance",
      [
        m2(
          "rspca-uk-preferred",
          uk.preferredM2,
          uk.preferredM2,
          n,
          "RSPCA (UK), keeping chickens as pets: at least this much housing per bird where possible. The page does not reduce it for bantams or increase it for heavy breeds."
        ),
        m2(
          "rspca-uk-densest",
          perDense,
          perDense,
          n,
          "Same RSPCA (UK) page: if the preferred area is not possible, do not stock more tightly than three birds per square metre of coop."
        ),
      ],
      ["These are housing figures, not a run. The RSPCA (UK) page does not give a numeric run size."],
      ""
    );
  }

  function runExtension(bird, housing, n, data) {
    if (housing === "indoor") {
      return section(
        "run-extension",
        "Run",
        "No outdoor access",
        [],
        [],
        "Not applicable. Oregon State's indoors-only coop figure is the extension allowance for this choice. Run rates are on the other two housing choices."
      );
    }
    var psuBird = data.psu.birds[bird];
    var uf = data.uf;
    var rows = [
      sqft(
        "psu-run",
        psuBird.run,
        psuBird.run,
        n,
        "Penn State Extension housing table, outdoor run for this row of the table (bantam, laying hen, or large chicken)."
      ),
    ];
    if (bird === "standard") {
      rows.push(
        sqft(
          "ext-run",
          uf.runLow,
          uf.runHigh,
          n,
          "University of Florida IFAS and University of Delaware Cooperative Extension both state this run range per bird. The low end matches Penn State's laying-hen run."
        )
      );
    } else if (bird === "large") {
      rows.push(
        sqft(
          "general-run",
          uf.runLow,
          uf.runHigh,
          n,
          "Florida and Delaware state this range per chicken or per bird, without a heavy-breed row. Penn State's large-chicken run is the separate row above."
        )
      );
    }
    var intro =
      housing === "freerange"
        ? "No page cited here gives a square-foot rule for an open yard. The rates below are for an enclosed run, if you build one for the hours the birds are not out. They do not replace the coop, and they are not added on top of a yard."
        : "Outdoor run for birds whose daytime space is the run. A run counts as outdoor access on the Oregon State page, so the coop stays on the with-outdoor figures above.";
    return section("run-extension", "Run", "Extension outdoor-run rates", rows, [], intro);
  }

  function runBhwt(bird, housing, n, data) {
    if (housing === "indoor" || bird !== "standard") return null;
    var bhwt = data.bhwt;
    return section(
      "run-bhwt",
      "Run, British Hen Welfare Trust",
      "Clear run floor for the hens the Trust rehomes",
      [
        m2(
          "bhwt-excage",
          bhwt.runExCageM2,
          bhwt.runExCageM2,
          n,
          "British Hen Welfare Trust, for ex-caged hens. Clear floor only: do not count space under the coop or the space taken by drinkers and feeders. The Trust also wants these hens to be able to free-range when they can."
        ),
        m2(
          "bhwt-other",
          bhwt.runOtherM2,
          bhwt.runOtherM2,
          n,
          "British Hen Welfare Trust, for hens from other farming systems. Same clear-floor rule. Not applied to the bantam or large-chicken choices: the Trust describes the hens it rehomes as medium-sized ex-commercial birds."
        ),
      ],
      [
        "These run areas are larger than the US extension run rates. Both are shown. A flock that free-ranges still needs an enclosure of this size, in the Trust's adoption rules, for the times the hens are shut in.",
      ],
      ""
    );
  }

  function auSection(bird, housing, n, data) {
    var au = data.rspcaAu;
    var total = auAreaM2(n, bird, data);
    var formula = row(
      "au-formula",
      "m2",
      total,
      total,
      "RSPCA Australia knowledgebase, updated 19 September 2023. Minimum combined coop and run: 3 m² for up to three large birds or six bantams, then at least 0.4 m² more per additional large bird or 0.3 m² more per additional bantam. “Large” here means not a bantam. The page does not add a further amount for heavy breeds.",
      null,
      null,
      null
    );
    var notes = [];
    var rows = [formula];
    if (bird === "bantam") {
      notes.push(
        "The 2021 RSPCA Australia article states 2–3.5 m² per hen and does not give a bantam figure, so that range is not applied here."
      );
    } else {
      rows.push(
        m2(
          "au-blog",
          au.blogM2Low,
          au.blogM2High,
          n,
          "RSPCA Australia, 18 May 2021: an absolute minimum of this much enclosure per hen, and ideally more. The same article says many commercially sold coops are too small. This is a different, higher statement than the 2023 knowledgebase formula. They are not averaged."
        )
      );
    }
    var intro;
    if (housing === "freerange") {
      intro =
        "Combined coop and run, not a coop figure and not a yard figure. The knowledgebase says this minimum can suit birds that roam by day and are housed at night. If they live in the enclosure most of the time, the same page says the enclosure must be significantly larger, without stating how much larger.";
    } else if (housing === "run") {
      intro =
        "Combined coop and run. The knowledgebase says birds kept in the coop or run most of the time need significantly more than this minimum. It does not say how much more. The 2021 article's per-hen range is the higher RSPCA Australia figure.";
    } else {
      intro =
        "Shown for comparison only. The knowledgebase describes a coop plus a run, or daytime ranging, not a closed indoor house. Do not read this total as an indoors-only floor area.";
    }
    return section(
      "au-combined",
      "RSPCA Australia, coop and run together",
      "Combined enclosure, not a separate coop and run",
      rows,
      notes,
      intro
    );
  }

  function nests(n, data) {
    var osu = data.osu;
    var uf = data.uf;
    var umn = data.umn;
    var udel = data.udel;
    var uk = data.rspcaUk;
    var au = data.rspcaAu;
    return section(
      "nests",
      "Nest boxes",
      "Counts for laying hens. Roosters are not included.",
      [
        count(
          "osu-per-4",
          ceilDiv(n, osu.nestPer),
          ceilDiv(n, osu.nestPer),
          "1 per 4 hens",
          "Oregon State University Extension: one nest box for about every four birds. Box about 12 × 12 × 12 inches."
        ),
        count(
          "uf-per-5",
          ceilDiv(n, uf.nestPer),
          ceilDiv(n, uf.nestPer),
          "1 per 5 hens",
          "University of Florida IFAS: at least one nest box for every five hens. Box 12 × 12 × 12 inches."
        ),
        count(
          "umn",
          ceilDiv(n, umn.nestFewerPer),
          ceilDiv(n, umn.nestMorePer),
          "1 per 4–5 hens",
          "University of Minnesota Extension: one nest box per 4 to 5 birds. The lower count is one box per five hens; the higher count is one box per four."
        ),
        count(
          "udel",
          ceilDiv(n, udel.nestFewerPer),
          ceilDiv(n, udel.nestMorePer),
          "1 per 3–4 hens",
          "University of Delaware Cooperative Extension: one box per 3–4 hens. The lower count is one per four; the higher count is one per three."
        ),
        count(
          "rspca-uk",
          Math.max(uk.nestMinBoxes, ceilDiv(n, uk.nestPer)),
          Math.max(uk.nestMinBoxes, ceilDiv(n, uk.nestPer)),
          "1 per 5, at least 2",
          "RSPCA (UK): at least one box per five hens, and at least two boxes for any group. Each box at least 30 × 30 × 30 cm."
        ),
        count(
          "rspca-au",
          ceilDiv(n, au.nestFewerPer),
          ceilDiv(n, au.nestMorePer),
          "1 per 2–4 hens",
          "RSPCA Australia knowledgebase: at least one box for every 2–4 hens. The lower count is one per four; the higher count is one per two. Boxes about 30 × 30 cm."
        ),
        count(
          "psu",
          psuNests(n, data),
          psuNests(n, data),
          "2 for the first 4, then 1 per 4",
          "Penn State Extension: two nests for the first four hens, then one more nest for every four additional hens. Each nest at least 12 × 12 inches, and larger for larger birds."
        ),
      ],
      [
        "A one-hen flock is still given two boxes under the Penn State rule and under the RSPCA (UK) minimum of two. The one-per-four and one-per-five rules give that hen one box.",
      ],
      ""
    );
  }

  function roosts(bird, n, data) {
    var psu = data.psu.birds[bird];
    var osu = data.osu;
    var umn = data.umn;
    var uk = data.rspcaUk;
    var au = data.rspcaAu;
    var bhwt = data.bhwt;
    var notes = [];
    var rows;
    if (bird === "bantam") {
      rows = [
        length(
          "psu",
          psu.roostIn,
          n,
          "in",
          "Penn State Extension: four inches of roost per bantam. The same paragraph sets bantam roosts 12–18 inches off the floor."
        ),
        length(
          "rspca",
          uk.roostCm,
          n,
          "cm",
          "RSPCA (UK) and RSPCA Australia both say at least 15 cm of roost per bird. Neither page publishes a shorter bantam length."
        ),
      ];
      notes.push(
        "Oregon State's 5–10 inches per bird is not split by size, except that Silkie roosts should be lower (about 1 foot off the floor), which is height rather than length. The British Hen Welfare Trust's 25 cm is for the medium-sized ex-commercial hens it rehomes, so it is not applied to bantams."
      );
    } else if (bird === "large") {
      rows = [
        length(
          "rspca",
          au.roostCm,
          n,
          "cm",
          "RSPCA Australia still wants a perch for heavier chickens, set lower, about 30 cm off the floor, and at least 15 cm long per bird. RSPCA (UK) also says at least 15 cm per bird, with the height suited to the birds."
        ),
        row(
          "osu",
          "in",
          osu.roostLowIn * n,
          osu.roostHighIn * n,
          "Oregon State: 5–10 inches of pole per bird, not increased for heavy breeds. Included only for birds that do roost.",
          osu.roostLowIn,
          osu.roostHighIn,
          null
        ),
        length(
          "umn",
          umn.roostIn,
          n,
          "in",
          "University of Minnesota Extension cold-weather page: generally 9 inches of roost per chicken. Not a heavy-breed measurement."
        ),
      ];
      notes.push(
        "Penn State says not to use perches for large, structured, or meaty breeds, because jumping down can injure legs and joints. RSPCA Australia disagrees in part: it still recommends perches for heavier chickens, at a lower height. This calculator does not pick a winner. Penn State's 6-inch standard-chicken roost and the Trust's 25 cm roost are not applied to this category."
      );
    } else {
      rows = [
        row(
          "osu",
          "in",
          osu.roostLowIn * n,
          osu.roostHighIn * n,
          "Oregon State University Extension: 5–10 inches of roost pole per bird.",
          osu.roostLowIn,
          osu.roostHighIn,
          null
        ),
        length(
          "psu",
          psu.roostIn,
          n,
          "in",
          "Penn State Extension: six inches per standard-size chicken. Roosts 18–24 inches off the floor and one foot apart, and never more than 4 feet off the floor."
        ),
        length(
          "umn",
          umn.roostIn,
          n,
          "in",
          "University of Minnesota Extension, caring for chickens in cold weather: generally 9 inches of roost per chicken."
        ),
        length(
          "rspca",
          uk.roostCm,
          n,
          "cm",
          "RSPCA (UK) says from 15 cm per chicken. RSPCA Australia says at least 15 cm. The UK page also suggests a perch height of about 40 cm."
        ),
        length(
          "bhwt",
          bhwt.roostCm,
          n,
          "cm",
          "British Hen Welfare Trust adoption guidance: 25 cm of perch per hen, for the ex-commercial hens the Trust rehomes."
        ),
      ];
      notes.push(
        "The widest span here runs from Oregon State's low end (5 inches) to its high end (10 inches). The Trust's 25 cm is about 9.8 inches, inside that span. Fifteen centimetres is about 5.9 inches."
      );
    }
    return section(
      "roosts",
      "Roost length",
      "Length, not height. Totals assume every bird roosts at once.",
      rows,
      notes,
      ""
    );
  }

  function compute(bird, housing, n, data) {
    if (BIRDS.indexOf(bird) === -1) throw new Error("unknown bird size: " + bird);
    if (HOUSINGS.indexOf(housing) === -1) throw new Error("unknown housing: " + housing);
    if (!Number.isInteger(n) || n < data.flockMin || n > data.flockMax) {
      throw new Error("flock size must be an integer from " + data.flockMin + " to " + data.flockMax);
    }
    var sections = [coopPrimary(bird, housing, n, data)];
    if (housing === "indoor") sections.push(coopTableContext(bird, n, data));
    sections.push(coopRspcaUk(n, data));
    sections.push(runExtension(bird, housing, n, data));
    var bhwt = runBhwt(bird, housing, n, data);
    if (bhwt) sections.push(bhwt);
    sections.push(auSection(bird, housing, n, data));
    sections.push(nests(n, data));
    sections.push(roosts(bird, n, data));
    var lead = flockPhrase(bird, n);
    lead = lead.charAt(0).toUpperCase() + lead.slice(1);
    return { lead: lead + ", " + HOUSING_PHRASE[housing] + ".", sections: sections };
  }

  function round5(value) {
    if (value == null) return null;
    return Math.round(Number(value) * 1e5) / 1e5;
  }

  function digest(bird, housing, n, data) {
    var result = compute(bird, housing, n, data);
    return {
      lead: result.lead,
      sections: result.sections.map(function (item) {
        return {
          id: item.id,
          heading: item.heading,
          caption: item.caption,
          intro: item.intro,
          notes: item.notes,
          rows: item.rows.map(function (entry) {
            return {
              key: entry.key,
              unit: entry.unit,
              per_text: entry.per_text,
              per_low: round5(entry.per_low),
              per_high: round5(entry.per_high),
              total_low: round5(entry.total_low),
              total_high: round5(entry.total_high),
              source: entry.source,
            };
          }),
        };
      }),
    };
  }

  function num(value) {
    var rounded = Math.round(Number(value) * 100) / 100;
    if (Math.abs(rounded - Math.round(rounded)) < 1e-9) return String(Math.round(rounded));
    if (Math.abs(rounded - Math.round(rounded * 10) / 10) < 1e-9) return rounded.toFixed(1);
    return rounded.toFixed(2);
  }

  function nearly(a, b) {
    return Math.abs(a - b) < 1e-9;
  }

  function formatAmount(low, high, unit, data) {
    var factor = data.sqftToM2;
    var inchToCm = data.inchToCm;
    if (unit === "count") {
      return nearly(low, high) ? String(low) : low + "–" + high;
    }
    if (unit === "sqft") {
      var metric = function (sqft) {
        return (sqft * factor).toFixed(2);
      };
      if (nearly(low, high)) return num(low) + " sq ft (" + metric(low) + " m²)";
      return num(low) + "–" + num(high) + " sq ft (" + metric(low) + "–" + metric(high) + " m²)";
    }
    if (unit === "m2") {
      var imperial = function (metres) {
        return (metres / factor).toFixed(2);
      };
      if (nearly(low, high)) return num(low) + " m² (" + imperial(low) + " sq ft)";
      return num(low) + "–" + num(high) + " m² (" + imperial(low) + "–" + imperial(high) + " sq ft)";
    }
    if (unit === "in") {
      var cm = function (inches) {
        return num(inches * inchToCm);
      };
      if (nearly(low, high)) return num(low) + " in (" + cm(low) + " cm)";
      return num(low) + "–" + num(high) + " in (" + cm(low) + "–" + cm(high) + " cm)";
    }
    if (unit === "cm") {
      var inches = function (cmValue) {
        return num(cmValue / inchToCm);
      };
      if (nearly(low, high)) return num(low) + " cm (" + inches(low) + " in)";
      return num(low) + "–" + num(high) + " cm (" + inches(low) + "–" + inches(high) + " cm)";
    }
    return "";
  }

  function amountHtml(text) {
    var match = /^(.*?)(\s*\([^()]*\))$/.exec(text);
    if (!match) return escapeHtml(text);
    return escapeHtml(match[1]) + '<span class="metric">' + escapeHtml(match[2].trim()) + "</span>";
  }

  function escapeHtml(text) {
    return String(text)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function render(result, data) {
    if (result.error) {
      return '<p class="calc-error" role="alert">' + escapeHtml(result.error) + "</p>";
    }
    var html = '<p class="results-lead">' + escapeHtml(result.lead) + "</p>";
    html +=
      '<p class="results-read">Each row is one published figure multiplied by the flock size. Overlapping rows are not averaged, and they are not added together.</p>';
    result.sections.forEach(function (item) {
      html += '<section class="result-block">';
      html += "<h3>" + escapeHtml(item.heading) + "</h3>";
      if (item.intro) html += "<p>" + escapeHtml(item.intro) + "</p>";
      if (item.rows.length) {
        html += '<div class="table-scroll">';
        html += "<table>";
        html += "<caption>" + escapeHtml(item.caption) + "</caption>";
        html += "<thead><tr><th scope=\"col\">Per bird</th><th scope=\"col\">This flock</th><th scope=\"col\">Where the figure comes from</th></tr></thead><tbody>";
        item.rows.forEach(function (entry) {
          var per = entry.per_text
            ? entry.per_text
            : entry.per_low == null
              ? "—"
              : formatAmount(entry.per_low, entry.per_high, entry.unit, data);
          var total = formatAmount(entry.total_low, entry.total_high, entry.unit, data);
          html +=
            "<tr><td>" +
            amountHtml(per) +
            "</td><td>" +
            amountHtml(total) +
            "</td><td>" +
            escapeHtml(entry.source) +
            "</td></tr>";
        });
        html += "</tbody></table></div>";
      }
      item.notes.forEach(function (note) {
        html += '<p class="note">' + escapeHtml(note) + "</p>";
      });
      html += "</section>";
    });
    return html;
  }

  function readData() {
    var node = document.getElementById("space-guidelines");
    if (!node) return null;
    return JSON.parse(node.textContent);
  }

  function selected(form, name) {
    var input = form.querySelector('input[name="' + name + '"]:checked');
    return input ? input.value : "";
  }

  function init() {
    var form = document.getElementById("coop-calculator");
    var output = document.getElementById("calc-results");
    if (!form || !output) return;
    var data = readData();
    if (!data) {
      output.innerHTML = '<p class="calc-error" role="alert">Calculator data did not load.</p>';
      return;
    }

    function update() {
      var raw = form.elements["flock-size"].value.trim();
      var flock = Number(raw);
      if (!/^\d+$/.test(raw) || flock < data.flockMin || flock > data.flockMax) {
        output.innerHTML = render(
          {
            error:
              "Enter a whole number of birds from " +
              data.flockMin +
              " to " +
              data.flockMax +
              ". The chart further down covers 2–20 standard hens without JavaScript.",
          },
          data
        );
        return;
      }
      var result = compute(selected(form, "bird"), selected(form, "housing"), flock, data);
      output.innerHTML = render(result, data);
    }

    form.addEventListener("submit", function (event) {
      event.preventDefault();
      update();
    });
    form.addEventListener("input", update);
    form.addEventListener("change", update);
    update();
  }

  return { compute: compute, digest: digest, render: render, init: init, formatAmount: formatAmount };
});
