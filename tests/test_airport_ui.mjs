// Business-logic integration tests: production app.js + real generated feeds.
// This lightweight element double does not replace visual browser QA.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";
import { test } from "node:test";
import vm from "node:vm";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const feedDirectory = resolve(root, process.env.RESIFLY_TEST_DATA_DIRECTORY || "data");
const steps = ["1", "1b", "1c", "1d", "1e", "1f", "2", "3", "4", "5"];
const documents = steps.map(step => JSON.parse(readFileSync(resolve(feedDirectory, `step${step}-results.json`), "utf8")));
const results = documents.flatMap(document => document.results);

class ElementDouble {
  constructor(tag = "div") {
    this.tagName = tag;
    this.children = [];
    this.attributes = {};
    this.dataset = {};
    this.listeners = {};
    this.value = "";
    this.textContent = "";
    this.style = { setProperty() {} };
    const classes = new Set();
    this.classList = {
      add: (...names) => names.forEach(name => classes.add(name)),
      remove: (...names) => names.forEach(name => classes.delete(name)),
      toggle: (name, enabled) => enabled ? classes.add(name) : classes.delete(name),
      contains: name => classes.has(name),
    };
  }
  append(...children) {
    this.children.push(...children);
    if (!this.value && children[0]?.tagName === "option") this.value = children[0].value;
  }
  replaceChildren(...children) { this.children = []; this.value = ""; this.append(...children); }
  setAttribute(name, value) { this.attributes[name] = value; }
  getAttribute(name) { return this.attributes[name]; }
  addEventListener(name, callback) { (this.listeners[name] ||= []).push(callback); }
  dispatchEvent(event) { (this.listeners[event.type] || []).forEach(callback => callback(event)); }
  closest() { return this; }
}

function harness() {
  const nodes = new Map();
  const context = vm.createContext({
    console, URL, URLSearchParams, Event, Intl,
    document: {
      querySelector: selector => {
        if (!nodes.has(selector)) nodes.set(selector, new ElementDouble());
        return nodes.get(selector);
      },
      createElement: tag => new ElementDouble(tag),
    },
    window: {
      location: new URL("http://127.0.0.1:8000/?build=local-gdn#old"),
      clearTimeout() {}, setTimeout() { return 1; },
    },
    targets: [],
  });
  const source = readFileSync(resolve(root, "app.js"), "utf8");
  assert.match(source, /\nloadFlights\(\);\s*$/);
  vm.runInContext(source.replace(/\nloadFlights\(\);\s*$/, ""), context);
  vm.runInContext(`globalThis.api = {state, elements, updateAirportOptions, filteredResults,
    selectedResultPricing, lowestPricesByDate, renderActiveFilters, clearActiveFilter,
    createCalendarDay, createFareChartDay, parseDateOnly, shareUrlForResult,
    sharedResultFromUrl, configureSharedResultFilters, journeyDuration, dayOffset,
    createJourneyTime, updateRangeLabels, resetFilters, initializeFilters, currentFilters,
    bookingUrlForFilters, createPurchaseStep};
    scrollToResult = id => targets.push(id);
    renderResults = () => {};`, context);
  const api = context.api;
  api.state.document = { period_from: documents[0].period_from, period_to: documents[0].period_to };
  api.state.results = results;
  for (const key of ["origin", "destination", "transfer", "firstCarrier", "secondCarrier"]) api.elements[key].value = "all";
  Object.assign(api.elements.direction, { value: "tenerife_to_poland" });
  Object.assign(api.elements.price, { min: "0", max: "4300", value: "1000" });
  Object.assign(api.elements.layover, { min: "2", max: "24", value: "6" });
  api.elements.resident.checked = true;
  api.elements.wizzClub.checked = false;
  api.elements.sort.value = "departure";
  return { ...api, context };
}

function filters(direction = "poland_to_tenerife", additions = {}) {
  return {
    resident: true, wizzClub: false, maxPrice: 4300,
    dateFrom: documents[0].period_from, dateTo: documents[0].period_to,
    direction, origin: direction === "poland_to_tenerife" ? "GDN" : "all",
    destination: direction === "tenerife_to_poland" ? "GDN" : "all",
    transfer: "all", firstCarrier: "all", secondCarrier: "all",
    maxLayover: 360, sort: "departure", ...additions,
  };
}

test("GDN is a fifth selectable endpoint in each direction", () => {
  const api = harness();
  for (const direction of ["poland_to_tenerife", "tenerife_to_poland"]) {
    api.elements.direction.value = direction;
    api.updateAirportOptions();
    const select = direction === "poland_to_tenerife" ? api.elements.origin : api.elements.destination;
    assert.deepEqual(select.children.map(option => option.value), ["all", "GDN", "KRK", "KTW", "WAW", "WMI"]);
    assert.equal(select.children[1].textContent, "Gdańsk (GDN)");
  }
});

test("GDN calendar minima agree with flight pricing in both directions and all discount modes", () => {
  const api = harness();
  for (const direction of ["poland_to_tenerife", "tenerife_to_poland"]) {
    for (const resident of [false, true]) for (const wizzClub of [false, true]) {
      const selected = filters(direction, { resident, wizzClub });
      const matching = api.filteredResults(selected);
      assert.ok(matching.length > 0);
      assert.ok(matching.some(result => result.legs.length === 1));
      assert.ok(matching.some(result => result.legs.length === 2));
      for (const result of matching) assert.ok([result.origin_airport, result.destination_airport].includes("GDN"));
      const prices = api.lowestPricesByDate(matching, selected);
      for (const [day, price] of prices) {
        const sameDay = matching.filter(result => result.legs[0].departure_at.slice(0, 10) === day);
        assert.equal(price.total, Math.min(...sameDay.map(result => api.selectedResultPricing(result, selected).total)));
        assert.ok(sameDay.some(result => result.id === price.resultId));
      }
    }
  }
});

test("all eight sort orders sort the whole GDN result set", () => {
  const api = harness();
  const selected = filters();
  const criteria = {
    price: result => api.selectedResultPricing(result, selected).total,
    regular: result => result.price_total_regular_pln,
    layover: result => result.layover_minutes ?? 0,
    departure: result => result.legs[0].departure_at,
    journey: result => api.journeyDuration(result),
    departure_time: result => result.legs[0].departure_at.slice(11, 16),
    arrival_time: result => result.legs.at(-1).arrival_at.slice(11, 16),
    direct: result => Number(result.legs.length !== 1),
  };
  for (const [sort, criterion] of Object.entries(criteria)) {
    const sorted = api.filteredResults({ ...selected, sort });
    assert.equal(sorted.length, api.filteredResults(selected).length);
    for (let index = 1; index < sorted.length; index++) assert.ok(criterion(sorted[index - 1]) <= criterion(sorted[index]), sort);
  }
});

test("both GDN filter chips clear the airport back to all", () => {
  const api = harness();
  api.elements.origin.value = "GDN";
  api.renderActiveFilters(filters());
  for (const container of [api.elements.calendarActiveFilters, api.elements.activeFilters]) {
    const chip = container.children.find(child => child.dataset.filterKey === "origin");
    assert.equal(chip.attributes["aria-label"], "Wyczyść filtr: Wylot: GDN");
    chip.listeners.click[0]();
    assert.equal(api.elements.origin.value, "all");
  }
});

test("calendar and chart target exactly the same cheapest GDN result", () => {
  const api = harness();
  const selected = filters();
  const prices = api.lowestPricesByDate(api.filteredResults(selected), selected);
  const [day, price] = [...prices][0];
  const calendar = api.createCalendarDay(api.parseDateOnly(day), selected.dateFrom, selected.dateTo, prices);
  const chart = api.createFareChartDay(day, price, price.total);
  calendar.listeners.click[0]();
  chart.listeners.click[0]();
  assert.deepEqual(Array.from(api.context.targets), [price.resultId, price.resultId]);
  assert.match(calendar.getAttribute("aria-label"), /zł/);
  assert.match(chart.getAttribute("aria-label"), /zł/);
});

test("GDN share URLs restore the exact result and discount settings", () => {
  const api = harness();
  const result = results.find(result => result.origin_airport === "GDN");
  const url = new URL(api.shareUrlForResult(result, { resident: false, wizzClub: true }));
  assert.equal(url.searchParams.get("flight"), result.id);
  assert.equal(url.searchParams.get("build"), null);
  assert.equal(url.hash, "");
  api.context.window.location = url;
  assert.equal(api.sharedResultFromUrl().id, result.id);
  assert.equal(api.elements.direction.value, "poland_to_tenerife");
  assert.equal(api.elements.resident.checked, false);
  assert.equal(api.elements.wizzClub.checked, true);
  assert.equal(api.elements.dateFrom.value, documents[0].period_from);
  assert.equal(api.elements.dateTo.value, documents[0].period_to);
  assert.equal(api.elements.layover.value, "24");
});

test("overnight GDN arrivals get the +1 marker", () => {
  const api = harness();
  const result = results.find(result => result.destination_airport === "GDN" && result.legs.at(-1).arrival_at.slice(0, 10) > result.legs[0].departure_at.slice(0, 10));
  assert.ok(result);
  const time = api.createJourneyTime(result.legs.at(-1).arrival_at, result.legs[0].departure_at);
  assert.equal(time.children.at(-1).textContent, "+1");
});

test("direct GDN flights disable second carrier and reset restores Poland to Tenerife", () => {
  const api = harness();
  api.elements.transfer.value = "direct";
  api.elements.secondCarrier.value = "Ryanair";
  api.updateRangeLabels();
  assert.equal(api.elements.secondCarrier.disabled, true);
  assert.equal(api.elements.secondCarrier.value, "all");
  assert.equal(api.elements.layover.disabled, true);
  api.resetFilters();
  assert.equal(api.elements.origin.value, "all");
  assert.equal(api.elements.destination.value, "all");
  assert.equal(api.elements.direction.value, "poland_to_tenerife");
  assert.equal(api.elements.sort.value, "departure");
  assert.equal(Number(api.elements.price.value), 1000);
  assert.equal(Number(api.elements.layover.value), 6);
});

test("initial price limit is 1000 PLN without discarding more expensive flights", () => {
  const api = harness();
  const originalCount = api.state.results.length;
  api.initializeFilters();
  assert.equal(api.elements.direction.value, "poland_to_tenerife");
  assert.equal(Number(api.elements.price.value), 1000);
  assert.ok(Number(api.elements.price.max) > 1000);
  assert.equal(Number(api.elements.layover.value), 6);
  const defaults = api.currentFilters();
  const displayed = api.filteredResults(defaults);
  assert.ok(displayed.length > 0);
  assert.ok(displayed.every(result => api.selectedResultPricing(result, defaults).total <= 1000));
  const expanded = { ...defaults, maxPrice: Number(api.elements.price.max) };
  const expandedResults = api.filteredResults(expanded);
  assert.ok(expandedResults.length > displayed.length);
  assert.ok(expandedResults.some(result => api.selectedResultPricing(result, expanded).total > 1000));
  assert.equal(api.state.results.length, originalCount);
  api.elements.price.value = api.elements.price.max;
  api.resetFilters();
  assert.equal(Number(api.elements.price.value), 1000);
});

test("1000 PLN remains selectable when all loaded fares are lower", () => {
  const api = harness();
  api.state.results = api.state.results.filter(result => result.price_total_regular_pln < 1000);
  api.initializeFilters();
  assert.equal(Number(api.elements.price.max), 1000);
  assert.equal(Number(api.elements.price.value), 1000);
});

test("a shared flight above 1000 PLN still opens with its explicit price settings", () => {
  const api = harness();
  api.initializeFilters();
  const result = results.find(result => result.origin_airport === "GDN" && result.price_total_regular_pln > 1000);
  assert.ok(result);
  api.context.window.location = new URL(api.shareUrlForResult(result, { resident: false, wizzClub: false }));
  assert.equal(api.sharedResultFromUrl().id, result.id);
  assert.ok(Number(api.elements.price.value) >= result.price_total_regular_pln);
  assert.ok(api.filteredResults().some(candidate => candidate.id === result.id));
});

test("Google-sourced Air Europa keeps official route/date links and resident toggling", () => {
  const api = harness();
  const leg = {
    carrier: "Air Europa", flight_number: "UX9048", departure_airport: "MAD", arrival_airport: "TFN",
    departure_at: "2026-11-01T15:00:00+01:00", arrival_at: "2026-11-01T16:55:00+00:00",
    price_source: "Google Flights", price_scope: "individual_flight_offer",
    price_regular_pln: 659, price_resident_estimated_pln: 164.75, resident_discount_eligible: true,
    booking_url: "https://www.aireuropa.com/es/es/deeplink?departure_airport=MAD&arrival_airport=TFN&departure_date=20261101&adults=1&residentType=SPANISH_RESIDENT_RC",
  };
  for (const resident of [true, false, true]) {
    const selected = filters("poland_to_tenerife", { resident });
    const url = new URL(api.bookingUrlForFilters(leg, selected));
    assert.equal(url.hostname, "www.aireuropa.com");
    assert.equal(url.searchParams.get("departure_airport"), "MAD");
    assert.equal(url.searchParams.get("arrival_airport"), "TFN");
    assert.equal(url.searchParams.get("departure_date"), "20261101");
    assert.equal(url.searchParams.get("residentType"), resident ? "SPANISH_RESIDENT_RC" : null);
    const step = api.createPurchaseStep(leg, 0, selected);
    assert.equal(step.children.find(child => child.className === "purchase-step-flight").textContent, "Numer lotu: UX9048");
    const link = step.children.find(child => child.className === "purchase-step-actions").children[0];
    assert.equal(link.href, url.toString());
  }
  assert.equal(new URL(api.bookingUrlForFilters({ ...leg, resident_discount_eligible: false }, filters())).searchParams.get("residentType"), null);
});
