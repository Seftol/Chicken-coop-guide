/* Household egg calculator for the how-many-chickens page.
   Hens = ceil(eggs per week / (7 × eggs per hen per day)).
   tests/test_site.py checks this function against the same formula
   and against the static table in the page. */
(function (root, factory) {
  var api = factory();
  if (typeof module === "object" && module.exports) {
    module.exports = api;
  } else {
    root.EggCalc = api;
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
  var COMPANY_MIN = 3;
  var PEOPLE_MAX = 20;
  var EGGS_PER_PERSON_MAX = 21;
  var TOTAL_MAX = 420;

  /* dailyNum/dailyDen is eggs per hen per day.
     weeklyNum/weeklyDen is 7 × that rate, stored in lowest exact form
     only when the product is already an integer fraction the page can print.
     perWeekText is that weekly rate in the digits used on the page. */
  var RATES = [
    {
      id: "uf-90",
      dailyNum: 9,
      dailyDen: 10,
      weeklyNum: 63,
      weeklyDen: 10,
      dailyText: "0.90",
      perWeekText: "6.3",
      name: "UF/IFAS peak, 0.90 eggs per hen per day",
    },
    {
      id: "unh-09",
      dailyNum: 9,
      dailyDen: 10,
      weeklyNum: 63,
      weeklyDen: 10,
      dailyText: "0.9",
      perWeekText: "6.3",
      name: "UNH first year, 0.9 eggs per hen per day (9 ÷ 10)",
    },
    {
      id: "uq-4",
      dailyNum: 4,
      dailyDen: 7,
      weeklyNum: 4,
      weeklyDen: 1,
      dailyText: "4/7",
      perWeekText: "4",
      name: "University of Queensland, 4 eggs per hen per week",
    },
    {
      id: "uq-5",
      dailyNum: 5,
      dailyDen: 7,
      weeklyNum: 5,
      weeklyDen: 1,
      dailyText: "5/7",
      perWeekText: "5",
      name: "University of Queensland, 5 eggs per hen per week",
    },
    {
      id: "uf-65",
      dailyNum: 13,
      dailyDen: 20,
      weeklyNum: 91,
      weeklyDen: 20,
      dailyText: "0.65",
      perWeekText: "4.55",
      name: "UF/IFAS after about 12 months of lay, 0.65 eggs per hen per day",
    },
    {
      id: "unh-06",
      dailyNum: 3,
      dailyDen: 5,
      weeklyNum: 21,
      weeklyDen: 5,
      dailyText: "0.6",
      perWeekText: "4.2",
      name: "UNH after 13 months, 0.6 eggs per hen per day (the low end of 6 to 7 eggs from 10 hens)",
    },
    {
      id: "ncsu-50",
      dailyNum: 1,
      dailyDen: 2,
      weeklyNum: 7,
      weeklyDen: 2,
      dailyText: "0.5",
      perWeekText: "3.5",
      name: "NC State by the 12th month, 0.5 eggs per hen per day (6 ÷ 12)",
    },
  ];

  function rateById(id) {
    for (var i = 0; i < RATES.length; i++) {
      if (RATES[i].id === id) return RATES[i];
    }
    return null;
  }

  function hensNeeded(eggsPerWeek, dailyNum, dailyDen) {
    if (!Number.isInteger(eggsPerWeek) || eggsPerWeek < 1) {
      throw new Error("eggs per week must be a positive whole number");
    }
    if (!Number.isInteger(dailyNum) || !Number.isInteger(dailyDen) || dailyNum < 1 || dailyDen < 1) {
      throw new Error("rate must be a positive fraction");
    }
    var numerator = eggsPerWeek * dailyDen;
    var denominator = 7 * dailyNum;
    return Math.floor((numerator + denominator - 1) / denominator);
  }

  function birdsToKeep(hens) {
    if (!Number.isInteger(hens) || hens < 0) throw new Error("hen count must be a whole number");
    return Math.max(hens, COMPANY_MIN);
  }

  function weeklyDivision(eggsPerWeek, rate) {
    var numerator = eggsPerWeek * rate.weeklyDen;
    var denominator = rate.weeklyNum;
    var whole = Math.floor(numerator / denominator);
    var remainder = numerator % denominator;
    var hens = remainder === 0 ? whole : whole + 1;
    return { hens: hens, whole: whole, remainder: remainder, numerator: numerator, denominator: denominator };
  }

  function escapeHtml(text) {
    return String(text)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function henWord(n) {
    return n === 1 ? "hen" : "hens";
  }

  function arithmeticText(eggs, rate, detail) {
    var step = "7 × " + rate.dailyText + " = " + rate.perWeekText + " eggs per hen per week. ";
    if (detail.remainder === 0) {
      return (
        step +
        eggs +
        " ÷ " +
        rate.perWeekText +
        " = " +
        detail.hens +
        " exactly, so the egg count is " +
        detail.hens +
        " " +
        henWord(detail.hens) +
        ". The division is arithmetic. It is not a count from a flock, and it is not a test."
      );
    }
    return (
      step +
      eggs +
      " ÷ " +
      rate.perWeekText +
      " = " +
      detail.whole +
      " and " +
      detail.remainder +
      "/" +
      detail.denominator +
      ", which is more than " +
      detail.whole +
      ". The next whole hen is " +
      detail.hens +
      ". That step up is arithmetic. It is not a count from a flock, and it is not a test."
    );
  }

  function companyText(hens) {
    var floor =
      "Separate from the division: the RSPCA in the UK recommends at least three hens that get on well, and Virginia Cooperative Extension says chickens need the company of at least two other chickens. The same Virginia page says hens do not need a rooster to lay eggs. The 3 is that company minimum, not a laying rate.";
    if (hens < COMPANY_MIN) {
      return (
        floor +
        " The egg division comes to " +
        hens +
        ", which is under 3. The larger of " +
        hens +
        " and 3 is 3. Taking the larger number is arithmetic."
      );
    }
    return (
      floor +
      " The egg division comes to " +
      hens +
      ", which is already at least those three birds."
    );
  }

  function render(model) {
    if (model.error) {
      return '<p class="calc-error" role="alert">' + escapeHtml(model.error) + "</p>";
    }
    var plan = birdsToKeep(model.hens);
    var lead;
    if (model.hens < COMPANY_MIN) {
      lead =
        "Plan for 3 hens. The egg division at this rate is " +
        model.hens +
        " " +
        henWord(model.hens) +
        ", and the company minimum is 3.";
    } else {
      lead = plan + " " + henWord(plan) + " at " + model.rate.name + ".";
    }
    var eggsLine;
    if (model.basis === "people") {
      eggsLine =
        model.people +
        " × " +
        model.perPerson +
        " = " +
        model.eggs +
        " eggs per week. That multiplication is arithmetic. One egg a day is 7 a week only because a week has 7 days, which is also arithmetic, not a laying rate.";
    } else {
      eggsLine = model.eggs + " eggs per week, the total you entered.";
    }
    return (
      '<p class="results-lead">' +
      escapeHtml(lead) +
      "</p>" +
      "<p>" +
      escapeHtml(eggsLine) +
      "</p>" +
      "<p>" +
      escapeHtml(arithmeticText(model.eggs, model.rate, model.detail)) +
      "</p>" +
      "<p>" +
      escapeHtml(companyText(model.hens)) +
      "</p>"
    );
  }

  function parseWhole(raw) {
    if (!/^\d+$/.test(raw)) return null;
    var value = Number(raw);
    if (!Number.isInteger(value)) return null;
    return value;
  }

  function selectedRate(form) {
    var input = form.querySelector('input[name="rate"]:checked');
    return input ? rateById(input.value) : null;
  }

  function selectedBasis(form) {
    var input = form.querySelector('input[name="basis"]:checked');
    return input ? input.value : "people";
  }

  function readModel(form) {
    var rate = selectedRate(form);
    if (!rate) return { error: "Choose one sourced laying rate." };
    var basis = selectedBasis(form);
    var eggs;
    var people = null;
    var perPerson = null;
    if (basis === "total") {
      var totalRaw = form.elements["total-eggs"].value.trim();
      var total = parseWhole(totalRaw);
      if (total === null || total < 1 || total > TOTAL_MAX) {
        return {
          error:
            "Enter a whole number of eggs per week from 1 to " +
            TOTAL_MAX +
            ". The table under the form covers 2, 4, and 6 people at one egg a day without JavaScript.",
        };
      }
      eggs = total;
    } else if (basis === "people") {
      var peopleRaw = form.elements.people.value.trim();
      var perRaw = form.elements["eggs-per-person"].value.trim();
      people = parseWhole(peopleRaw);
      perPerson = parseWhole(perRaw);
      if (people === null || people < 1 || people > PEOPLE_MAX) {
        return {
          error:
            "Enter a whole number of people from 1 to " +
            PEOPLE_MAX +
            ". The limit is the form’s, not a flock size from a source.",
        };
      }
      if (perPerson === null || perPerson < 1 || perPerson > EGGS_PER_PERSON_MAX) {
        return {
          error:
            "Enter whole eggs per person per week from 1 to " +
            EGGS_PER_PERSON_MAX +
            ". One egg a day is 7. That 7 is arithmetic.",
        };
      }
      eggs = people * perPerson;
    } else {
      return { error: "Choose whether to count people or a weekly total." };
    }
    var detail = weeklyDivision(eggs, rate);
    if (detail.hens !== hensNeeded(eggs, rate.dailyNum, rate.dailyDen)) {
      return { error: "The weekly rate and the daily rate did not produce the same hen count." };
    }
    return {
      basis: basis,
      people: people,
      perPerson: perPerson,
      eggs: eggs,
      rate: rate,
      hens: detail.hens,
      detail: detail,
    };
  }

  function init() {
    var form = document.getElementById("egg-calculator");
    var output = document.getElementById("egg-results");
    if (!form || !output) return;

    function update() {
      output.innerHTML = render(readModel(form));
    }

    form.addEventListener("submit", function (event) {
      event.preventDefault();
      update();
    });
    form.addEventListener("input", update);
    form.addEventListener("change", update);
    update();
  }

  return {
    RATES: RATES,
    COMPANY_MIN: COMPANY_MIN,
    hensNeeded: hensNeeded,
    birdsToKeep: birdsToKeep,
    init: init,
  };
});
