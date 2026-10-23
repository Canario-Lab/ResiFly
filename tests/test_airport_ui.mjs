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
  contains(target) { return this === target || this.children.some(child => child.contains?.(target)); }
  focus() { this.focused = true; }
}

function harness({ rows = results } = {}) {
  const nodes = new Map();
  const documentListeners = {};
  const context = vm.createContext({
    console, URL, URLSearchParams, Event, Intl,
    document: {
      querySelector: selector => {
        if (!nodes.has(selector)) nodes.set(selector, new ElementDouble());
        return nodes.get(selector);
      },
      createElement: tag => new ElementDouble(tag),
      addEventListener: (name, callback) => (documentListeners[name] ||= []).push(callback),
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
    bookingUrlForFilters, createPurchaseStep, airportPickers, setPolishAirports,
    polishAirportCodes, changeDirection, fareCalendarRenderKey, resultCardsRenderKey,
    bindAirportPickerEvents, closeAirportPickers};
    scrollToResult = id => targets.push(id);
    renderResults = () => {};`, context);
  const api = context.api;
  for (const picker of Object.values(api.airportPickers)) {
    picker.summary.append(picker.value);
    picker.disclosure.append(picker.summary, picker.all, picker.options, picker.done);
  }
  api.state.document = { period_from: documents[0].period_from, period_to: documents[0].period_to };
  api.state.results = rows;
  for (const key of ["origin", "destination", "transfer", "firstCarrier", "secondCarrier"]) api.elements[key].value = "all";
  Object.assign(api.elements.direction, { value: "tenerife_to_poland" });
  Object.assign(api.elements.price, { min: "0", max: "4300", value: "1000" });
  Object.assign(api.elements.layover, { min: "2", max: "24", value: "6" });
  api.elements.resident.checked = true;
  api.elements.wizzClub.checked = false;
  api.elements.sort.value = "departure";
  return { ...api, context, documentListeners };
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

test("Polish airport multiselect is an OR filter in both directions; Tenerife remains single-select", () => {
  const api = harness();
  api.initializeFilters();
  for (const direction of ["poland_to_tenerife", "tenerife_to_poland"]) {
    api.elements.direction.value = direction;
    api.changeDirection();
    api.setPolishAirports(["WRO", "KRK", "KTW"]);
    const selected = {...api.currentFilters(), maxPrice: Infinity, maxLayover: 1440};
    const union = api.filteredResults(selected);
    const separate = ["KRK", "KTW", "WRO"].flatMap(code => api.filteredResults({...selected, polishAirports: [code]}));
    assert.deepEqual(union.map(row => row.id).sort(), separate.map(row => row.id).sort());
    assert.equal(new Set(union.map(row => row.id)).size, union.length);
    const polishSide = direction === "poland_to_tenerife" ? "origin" : "destination";
    const tenerifeSide = polishSide === "origin" ? "destination" : "origin";
    assert.equal(api.elements[polishSide].hidden, true);
    assert.equal(api.airportPickers[polishSide].disclosure.hidden, false);
    assert.equal(api.elements[tenerifeSide].hidden, false);
    assert.equal(api.airportPickers[tenerifeSide].disclosure.hidden, true);
    const tfs = api.filteredResults({...selected, [tenerifeSide]: "TFS"});
    assert.ok(tfs.length > 0);
    assert.deepEqual(tfs.map(row => row.id), union.filter(row => row[`${tenerifeSide}_airport`] === "TFS").map(row => row.id));
    assert.equal(api.airportPickers[polishSide].value.textContent, "Kraków, Katowice +1");
    assert.equal(api.elements[polishSide].classList.contains("is-filtered"), true);
    assert.equal(api.elements[tenerifeSide].classList.contains("is-filtered"), false);
  }
});

test("checkboxes keep focusable nodes, select several airports, and All restores the default", () => {
  const api = harness();
  api.initializeFilters();
  api.bindAirportPickerEvents();
  const picker = api.airportPickers.origin;
  assert.equal(picker.checkboxes.size, api.polishAirportCodes().length);
  picker.disclosure.open = true;
  const krk = picker.checkboxes.get("KRK");
  for (const code of ["KRK", "KTW", "WRO"]) {
    const checkbox = picker.checkboxes.get(code);
    checkbox.checked = true;
    checkbox.dispatchEvent(new Event("change"));
  }
  assert.deepEqual(Array.from(api.currentFilters().polishAirports), ["KRK", "KTW", "WRO"]);
  assert.equal(picker.checkboxes.get("KRK"), krk);
  assert.equal(picker.disclosure.open, true);
  assert.equal(picker.all.getAttribute("aria-pressed"), "false");
  picker.checkboxes.get("KTW").checked = false;
  picker.checkboxes.get("KTW").dispatchEvent(new Event("change"));
  assert.deepEqual(Array.from(api.currentFilters().polishAirports), ["KRK", "WRO"]);
  picker.all.dispatchEvent(new Event("click"));
  assert.deepEqual(Array.from(api.currentFilters().polishAirports), []);
  assert.equal(picker.all.getAttribute("aria-pressed"), "true");
  assert.equal(picker.value.textContent, "Wszystkie lotniska");
  assert.ok([...picker.checkboxes.values()].every(checkbox => !checkbox.checked));
  assert.equal(api.elements.origin.classList.contains("is-filtered"), false);
});

test("direction changes keep the same Polish airports and close the previous popup", () => {
  const api = harness();
  api.initializeFilters();
  api.setPolishAirports(["LCJ", "POZ"]);
  for (const direction of ["tenerife_to_poland", "poland_to_tenerife"]) {
    Object.values(api.airportPickers).forEach(picker => { picker.disclosure.open = true; });
    api.elements.direction.value = direction;
    api.changeDirection();
    assert.deepEqual(Array.from(api.currentFilters().polishAirports), ["LCJ", "POZ"]);
    const side = direction === "poland_to_tenerife" ? "origin" : "destination";
    assert.equal(api.airportPickers[side].value.textContent, "Łódź, Poznań");
    assert.ok(Object.values(api.airportPickers).every(picker => !picker.disclosure.open));
    assert.ok(api.filteredResults().every(row => ["LCJ", "POZ"].includes(row[`${side}_airport`])));
  }
});

test("each airport chip removes only its own airport; removing the last restores all", () => {
  const api = harness();
  api.initializeFilters();
  api.setPolishAirports(["KRK", "KTW", "WRO"]);
  for (const code of ["KTW", "KRK", "WRO"]) {
    api.renderActiveFilters();
    for (const container of [api.elements.calendarActiveFilters, api.elements.activeFilters]) {
      assert.equal(container.children.filter(chip => chip.dataset.filterKey?.startsWith("polishAirport:")).length, api.state.polishAirports.length);
    }
    const before = Array.from(api.state.polishAirports);
    const chip = api.elements.calendarActiveFilters.children.find(chip => chip.dataset.filterKey === `polishAirport:${code}`);
    chip.dispatchEvent(new Event("click"));
    assert.deepEqual(Array.from(api.state.polishAirports), before.filter(value => value !== code));
  }
  assert.equal(api.airportPickers.origin.value.textContent, "Wszystkie lotniska");
});

test("calendar and chart use the union minima and same card for multiple airports in all discount modes", () => {
  const api = harness();
  api.initializeFilters();
  api.setPolishAirports(["KRK", "KTW", "WRO"]);
  for (const direction of ["poland_to_tenerife", "tenerife_to_poland"]) {
    for (const resident of [false, true]) for (const wizzClub of [false, true]) {
      const selected = {...api.currentFilters(), direction, resident, wizzClub, maxPrice: Infinity, maxLayover: 1440};
      const matching = api.filteredResults(selected);
      const prices = api.lowestPricesByDate(matching, selected);
      assert.ok(prices.size > 0);
      for (const [day, price] of prices) {
        const sameDay = matching.filter(row => row.legs[0].departure_at.slice(0, 10) === day);
        assert.equal(price.total, Math.min(...sameDay.map(row => api.selectedResultPricing(row, selected).total)));
      }
      const [day, price] = [...prices][0];
      const calendar = api.createCalendarDay(api.parseDateOnly(day), selected.dateFrom, selected.dateTo, prices);
      const chart = api.createFareChartDay(day, price, price.total);
      calendar.dispatchEvent(new Event("click"));
      chart.dispatchEvent(new Event("click"));
      assert.deepEqual(Array.from(api.context.targets).slice(-2), [price.resultId, price.resultId]);
    }
  }
});

test("airport selection is normalized and invalidates both calendar and result cache keys", () => {
  const api = harness();
  api.initializeFilters();
  const all = api.currentFilters();
  api.setPolishAirports(["WRO", "KRK", "KRK", "NOPE"]);
  const selected = api.currentFilters();
  assert.deepEqual(Array.from(selected.polishAirports), ["KRK", "WRO"]);
  assert.notEqual(api.fareCalendarRenderKey(all), api.fareCalendarRenderKey(selected));
  assert.notEqual(api.resultCardsRenderKey(all), api.resultCardsRenderKey(selected));
  api.setPolishAirports(["KRK", "WRO"]);
  assert.equal(api.resultCardsRenderKey(api.currentFilters()), api.resultCardsRenderKey(selected));
  api.setPolishAirports(api.polishAirportCodes());
  assert.deepEqual(Array.from(api.currentFilters().polishAirports), []);
  assert.equal(api.resultCardsRenderKey(api.currentFilters()), api.resultCardsRenderKey(all));
});

test("date reset keeps airport choices, while full reset and shared flights clear them", () => {
  const api = harness();
  api.initializeFilters();
  api.setPolishAirports(["LCJ", "POZ"]);
  api.elements.dateFrom.value = "2026-11-01";
  api.clearActiveFilter("dateRange");
  assert.deepEqual(Array.from(api.currentFilters().polishAirports), ["LCJ", "POZ"]);
  assert.equal(api.elements.dateFrom.value, documents[0].period_from);
  const row = results.find(row => row.origin_airport === "GDN");
  api.context.window.location = new URL(api.shareUrlForResult(row, {resident: false, wizzClub: true}));
  assert.equal(api.sharedResultFromUrl().id, row.id);
  assert.deepEqual(Array.from(api.currentFilters().polishAirports), []);
  assert.ok(api.filteredResults().some(result => result.id === row.id));
  api.setPolishAirports(["KRK", "WRO"]);
  api.resetFilters();
  assert.deepEqual(Array.from(api.currentFilters().polishAirports), []);
  assert.equal(api.airportPickers.origin.value.textContent, "Wszystkie lotniska");
  assert.equal(api.elements.direction.value, "poland_to_tenerife");
  assert.equal(Number(api.elements.price.value), 1000);
  assert.equal(Number(api.elements.layover.value), 6);
});

test("Done, Escape and outside clicks close the airport popup without losing selection", () => {
  const api = harness();
  api.initializeFilters();
  api.bindAirportPickerEvents();
  api.setPolishAirports(["KRK", "WRO"]);
  const picker = api.airportPickers.origin;
  picker.disclosure.open = true;
  api.documentListeners.click[0]({target: picker.checkboxes.get("KRK")});
  assert.equal(picker.disclosure.open, true);
  picker.done.dispatchEvent(new Event("click"));
  assert.equal(picker.disclosure.open, false);
  assert.equal(picker.summary.focused, true);
  picker.disclosure.open = true;
  let prevented = false;
  api.documentListeners.keydown[0]({key: "Escape", preventDefault() { prevented = true; }});
  assert.equal(picker.disclosure.open, false);
  assert.equal(prevented, true);
  picker.disclosure.open = true;
  api.documentListeners.click[0]({target: api.elements.price});
  assert.equal(picker.disclosure.open, false);
  assert.deepEqual(Array.from(api.currentFilters().polishAirports), ["KRK", "WRO"]);
});

test("all available endpoints remain selectable in each direction", () => {
  const api = harness();
  for (const direction of ["poland_to_tenerife", "tenerife_to_poland"]) {
    api.elements.direction.value = direction;
    api.updateAirportOptions();
    const select = direction === "poland_to_tenerife" ? api.elements.origin : api.elements.destination;
    const available = [...new Set(results.filter(row => row.direction === direction).map(row => direction === "poland_to_tenerife" ? row.origin_airport : row.destination_airport))].sort();
    assert.deepEqual(select.children.map(option => option.value), ["all", ...available]);
    assert.equal(select.children[1].textContent, "Gdańsk (GDN)");
  }
});

function syntheticRzeRows() {
  return ["poland_to_tenerife", "tenerife_to_poland"].map(direction => {
    const row = structuredClone(results.find(r => r.direction === direction && [r.origin_airport, r.destination_airport].includes("LCJ")));
    row.id = `synthetic-rze-${direction}`;
    const side = direction === "poland_to_tenerife" ? "origin_airport" : "destination_airport";
    row[side] = "RZE";
    if (direction === "poland_to_tenerife") row.legs[0].departure_airport = "RZE";
    else row.legs.at(-1).arrival_airport = "RZE";
    return row;
  });
}

test("ninth RZE checkbox, OR selection, chips, cache and direction retention", () => {
  const samples = syntheticRzeRows();
  const api = harness({rows: [...results.filter(r => ![r.origin_airport, r.destination_airport].includes("RZE")), ...samples]});
  api.initializeFilters();
  assert.deepEqual(Array.from(api.polishAirportCodes()), ["GDN", "KRK", "KTW", "LCJ", "POZ", "RZE", "WAW", "WMI", "WRO"]);
  assert.equal(api.airportPickers.origin.checkboxes.size, 9);
  assert.equal(api.airportPickers.origin.checkboxes.get("RZE").value, "RZE");
  const before = api.currentFilters();
  api.setPolishAirports(["RZE", "KRK", "RZE"]);
  assert.deepEqual(Array.from(api.currentFilters().polishAirports), ["KRK", "RZE"]);
  assert.notEqual(api.fareCalendarRenderKey(before), api.fareCalendarRenderKey(api.currentFilters()));
  assert.notEqual(api.resultCardsRenderKey(before), api.resultCardsRenderKey(api.currentFilters()));
  for (const direction of ["poland_to_tenerife", "tenerife_to_poland"]) {
    api.elements.direction.value = direction;
    api.changeDirection();
    const filters = {...api.currentFilters(), maxPrice: Infinity, maxLayover: 1440};
    const union = api.filteredResults(filters);
    assert.deepEqual(union.map(r => r.id).sort(), ["KRK", "RZE"].flatMap(code => api.filteredResults({...filters, polishAirports: [code]})).map(r => r.id).sort());
    assert.ok(union.some(r => r.id === `synthetic-rze-${direction}`));
  }
  api.clearActiveFilter("polishAirport:RZE");
  assert.deepEqual(Array.from(api.currentFilters().polishAirports), ["KRK"]);
  api.clearActiveFilter("polishAirport:KRK");
  assert.deepEqual(Array.from(api.currentFilters().polishAirports), []);
  api.setPolishAirports(Array.from(api.polishAirportCodes()));
  assert.deepEqual(Array.from(api.currentFilters().polishAirports), []);
});

test("RZE one-way availability remains selectable after direction reversal; no offer means no fabricated checkbox", () => {
  const without = results.filter(r => ![r.origin_airport, r.destination_airport].includes("RZE"));
  const api = harness({rows: [...without, syntheticRzeRows()[0]]});
  api.initializeFilters();
  api.setPolishAirports(["RZE"]);
  api.elements.direction.value = "tenerife_to_poland";
  api.changeDirection();
  assert.ok(api.airportPickers.destination.checkboxes.has("RZE"));
  assert.deepEqual(Array.from(api.currentFilters().polishAirports), ["RZE"]);
  assert.equal(api.filteredResults({...api.currentFilters(), maxPrice: Infinity, maxLayover: 1440}).length, 0);
  const empty = harness({rows: without});
  empty.initializeFilters();
  assert.equal(empty.airportPickers.origin.checkboxes.has("RZE"), false);
});

test("collected RZE calendar, chart, multiselect and share agree in both directions and all discounts", t => {
  if (!results.some(r => [r.origin_airport, r.destination_airport].includes("RZE"))) {
    t.skip("Old eight-endpoint feeds: run again on the fresh RZE staging before promotion");
    return;
  }
  const api = harness();
  api.initializeFilters();
  for (const direction of ["poland_to_tenerife", "tenerife_to_poland"]) for (const resident of [false, true]) for (const wizzClub of [false, true]) {
    api.elements.direction.value = direction;
    api.changeDirection();
    api.setPolishAirports(["RZE"]);
    const filters = {...api.currentFilters(), resident, wizzClub, maxPrice: Infinity, maxLayover: 1440};
    const rows = api.filteredResults(filters);
    assert.ok(rows.length > 0, direction);
    assert.ok(rows.every(r => [r.origin_airport, r.destination_airport].includes("RZE")));
    const criteria = {
      price: r => api.selectedResultPricing(r, filters).total,
      regular: r => r.price_total_regular_pln,
      layover: r => r.layover_minutes ?? 0,
      departure: r => r.legs[0].departure_at,
      journey: r => api.journeyDuration(r),
      departure_time: r => r.legs[0].departure_at.slice(11, 16),
      arrival_time: r => r.legs.at(-1).arrival_at.slice(11, 16),
      direct: r => Number(r.legs.length !== 1),
    };
    for (const [sort, value] of Object.entries(criteria)) {
      const sorted = api.filteredResults({...filters, sort});
      assert.equal(sorted.length, rows.length);
      for (let n = 1; n < sorted.length; n++) assert.ok(value(sorted[n - 1]) <= value(sorted[n]), sort);
    }
    const minima = api.lowestPricesByDate(rows, filters);
    for (const [day, price] of minima) {
      assert.equal(price.total, Math.min(...rows.filter(r => r.legs[0].departure_at.slice(0, 10) === day).map(r => api.selectedResultPricing(r, filters).total)));
    }
    const [day, price] = [...minima][0];
    api.createCalendarDay(api.parseDateOnly(day), filters.dateFrom, filters.dateTo, minima).dispatchEvent(new Event("click"));
    api.createFareChartDay(day, price, price.total).dispatchEvent(new Event("click"));
    assert.deepEqual(Array.from(api.context.targets).slice(-2), [price.resultId, price.resultId]);
    const row = rows.find(r => r.id === price.resultId);
    api.context.window.location = new URL(api.shareUrlForResult(row, {resident, wizzClub}));
    assert.equal(api.sharedResultFromUrl().id, row.id);
    assert.deepEqual(Array.from(api.currentFilters().polishAirports), []);
    assert.equal(api.elements.direction.value, direction);
    assert.equal(api.elements.resident.checked, resident);
    assert.equal(api.elements.wizzClub.checked, wizzClub);
    assert.ok(api.filteredResults().some(r => r.id === row.id));
  }
  const expensive = results.find(r => r.origin_airport === "RZE" && r.price_total_regular_pln > 1000);
  if (expensive) {
    api.context.window.location = new URL(api.shareUrlForResult(expensive, {resident: false, wizzClub: false}));
    assert.equal(api.sharedResultFromUrl().id, expensive.id);
    assert.ok(Number(api.elements.price.value) >= expensive.price_total_regular_pln);
    assert.ok(api.filteredResults().some(r => r.id === expensive.id));
  }
});

test("RZE overnight marker and date reset keep the multi-airport selection", () => {
  const api = harness({rows: [...results, ...syntheticRzeRows()]});
  api.initializeFilters();
  api.setPolishAirports(["RZE", "KRK"]);
  const time = api.createJourneyTime("2026-11-02T00:55:00+01:00", "2026-11-01T18:00:00+00:00");
  assert.equal(time.children[1].tagName, "sup");
  assert.equal(time.children[1].textContent, "+1");
  api.elements.dateFrom.value = "2026-11-01";
  api.elements.dateTo.value = "2026-11-01";
  api.clearActiveFilter("dateRange");
  assert.equal(api.elements.dateFrom.value, documents[0].period_from);
  assert.equal(api.elements.dateTo.value, documents[0].period_to);
  assert.deepEqual(Array.from(api.currentFilters().polishAirports), ["KRK", "RZE"]);
});

test("WRO is a sixth selectable endpoint with calendar and chart minima in all discount modes", () => {
  const api = harness();
  for (const direction of ["poland_to_tenerife", "tenerife_to_poland"]) {
    api.elements.direction.value = direction;
    api.updateAirportOptions();
    const select = direction === "poland_to_tenerife" ? api.elements.origin : api.elements.destination;
    assert.equal(select.children.find(option => option.value === "WRO")?.textContent, "Wrocław (WRO)");
    for (const resident of [false, true]) for (const wizzClub of [false, true]) {
      const selected = filters(direction, {
        origin: direction === "poland_to_tenerife" ? "WRO" : "all",
        destination: direction === "tenerife_to_poland" ? "WRO" : "all",
        resident, wizzClub, maxPrice: Infinity, maxLayover: 1440,
      });
      const matching = api.filteredResults(selected);
      assert.ok(matching.length > 0, direction);
      assert.ok(matching.every(result => [result.origin_airport, result.destination_airport].includes("WRO")));
      const prices = api.lowestPricesByDate(matching, selected);
      for (const [day, price] of prices) {
        const sameDay = matching.filter(result => result.legs[0].departure_at.slice(0, 10) === day);
        assert.equal(price.total, Math.min(...sameDay.map(result => api.selectedResultPricing(result, selected).total)));
      }
      const [day, price] = [...prices][0];
      const calendar = api.createCalendarDay(api.parseDateOnly(day), selected.dateFrom, selected.dateTo, prices);
      const chart = api.createFareChartDay(day, price, price.total);
      calendar.listeners.click[0]();
      chart.listeners.click[0]();
      assert.deepEqual(Array.from(api.context.targets).slice(-2), [price.resultId, price.resultId]);
    }
  }
});

test("WRO shared links restore their own direction and discount settings", () => {
  const api = harness();
  api.initializeFilters();
  assert.equal(api.elements.direction.value, "poland_to_tenerife");
  for (const direction of ["poland_to_tenerife", "tenerife_to_poland"]) {
    const result = results.find(result => result.direction === direction &&
      [result.origin_airport, result.destination_airport].includes("WRO"));
    assert.ok(result);
    api.context.window.location = new URL(api.shareUrlForResult(result, { resident: false, wizzClub: true }));
    assert.equal(api.sharedResultFromUrl().id, result.id);
    assert.equal(api.elements.direction.value, direction);
    assert.equal(api.elements.resident.checked, false);
    assert.equal(api.elements.wizzClub.checked, true);
    assert.ok(api.filteredResults().some(candidate => candidate.id === result.id));
  }
});

test("POZ calendar, chart and share agree in both directions and all discount modes", () => {
  const api = harness();
  for (const direction of ["poland_to_tenerife", "tenerife_to_poland"]) {
    api.elements.direction.value = direction;
    api.updateAirportOptions();
    const select = direction === "poland_to_tenerife" ? api.elements.origin : api.elements.destination;
    assert.equal(select.children.find(option => option.value === "POZ")?.textContent, "Poznań (POZ)");
    for (const resident of [false, true]) for (const wizzClub of [false, true]) {
      const selected = filters(direction, {
        origin: direction === "poland_to_tenerife" ? "POZ" : "all",
        destination: direction === "tenerife_to_poland" ? "POZ" : "all",
        resident, wizzClub, maxPrice: Infinity, maxLayover: 1440,
      });
      const matching = api.filteredResults(selected);
      assert.ok(matching.length > 0, direction);
      const prices = api.lowestPricesByDate(matching, selected);
      for (const [day, price] of prices) {
        const sameDay = matching.filter(result => result.legs[0].departure_at.slice(0, 10) === day);
        assert.equal(price.total, Math.min(...sameDay.map(result => api.selectedResultPricing(result, selected).total)));
      }
      const [day, price] = [...prices][0];
      api.createCalendarDay(api.parseDateOnly(day), selected.dateFrom, selected.dateTo, prices).listeners.click[0]();
      api.createFareChartDay(day, price, price.total).listeners.click[0]();
      assert.deepEqual(Array.from(api.context.targets).slice(-2), [price.resultId, price.resultId]);
      const result = matching.find(row => row.id === price.resultId);
      api.context.window.location = new URL(api.shareUrlForResult(result, {resident, wizzClub}));
      assert.equal(api.sharedResultFromUrl().id, result.id);
      assert.equal(api.elements.direction.value, direction);
      assert.equal(api.elements.resident.checked, resident);
      assert.equal(api.elements.wizzClub.checked, wizzClub);
      assert.ok(api.filteredResults().some(row => row.id === result.id));
      for (const segment of result.legs) {
        const url = new URL(api.bookingUrlForFilters(segment, selected));
        assert.equal(url.protocol, "https:");
        assert.ok(!["token", "session", "cookie"].some(key => url.searchParams.has(key)));
      }
    }
  }
});

test("LCJ calendar, chart and share agree in both directions and all discount modes", () => {
  const api = harness();
  for (const direction of ["poland_to_tenerife", "tenerife_to_poland"]) {
    api.elements.direction.value = direction;
    api.updateAirportOptions();
    const select = direction === "poland_to_tenerife" ? api.elements.origin : api.elements.destination;
    assert.equal(select.children.find(option => option.value === "LCJ")?.textContent, "Łódź (LCJ)");
    for (const resident of [false, true]) for (const wizzClub of [false, true]) {
      const selected = filters(direction, {
        origin: direction === "poland_to_tenerife" ? "LCJ" : "all",
        destination: direction === "tenerife_to_poland" ? "LCJ" : "all",
        resident, wizzClub, maxPrice: Infinity, maxLayover: 1440,
      });
      const matching = api.filteredResults(selected);
      assert.ok(matching.length > 0, direction);
      assert.ok(matching.every(row => [row.origin_airport, row.destination_airport].includes("LCJ")));
      const prices = api.lowestPricesByDate(matching, selected);
      for (const [day, price] of prices) {
        const sameDay = matching.filter(row => row.legs[0].departure_at.slice(0, 10) === day);
        assert.equal(price.total, Math.min(...sameDay.map(row => api.selectedResultPricing(row, selected).total)));
      }
      const [day, price] = [...prices][0];
      const calendar = api.createCalendarDay(api.parseDateOnly(day), selected.dateFrom, selected.dateTo, prices);
      const chart = api.createFareChartDay(day, price, price.total);
      calendar.listeners.click[0]();
      chart.listeners.click[0]();
      assert.deepEqual(Array.from(api.context.targets).slice(-2), [price.resultId, price.resultId]);
      assert.match(chart.getAttribute("aria-label"), /zł/);
      const row = matching.find(row => row.id === price.resultId);
      api.context.window.location = new URL(api.shareUrlForResult(row, {resident, wizzClub}));
      assert.equal(api.sharedResultFromUrl().id, row.id);
      assert.equal(api.elements.direction.value, direction);
      assert.equal(api.elements.resident.checked, resident);
      assert.equal(api.elements.wizzClub.checked, wizzClub);
      assert.ok(api.filteredResults().some(candidate => candidate.id === row.id));
      for (const segment of row.legs) {
        const url = new URL(api.bookingUrlForFilters(segment, selected));
        assert.equal(url.protocol, "https:");
        assert.equal(url.hostname, {Ryanair: "www.ryanair.com", Vueling: "tickets.vueling.com"}[segment.carrier]);
        assert.ok(!["token", "session", "cookie"].some(key => url.searchParams.has(key)));
      }
    }
  }
});

test("LCJ synthetic overnight marker and date reset preserve existing behaviour", () => {
  const api = harness();
  // Synthetic timestamps test formatting even when a collection has no overnight LCJ offer.
  const time = api.createJourneyTime("2026-11-02T01:15:00+01:00", "2026-11-01T22:00:00+01:00");
  assert.equal(time.children.at(-1).textContent, "+1");
  api.initializeFilters();
  api.elements.origin.value = "LCJ";
  api.elements.dateFrom.value = documents[0].period_to;
  api.elements.dateTo.value = documents[0].period_to;
  api.clearActiveFilter("dateRange");
  assert.equal(api.elements.origin.value, "LCJ");
  assert.equal(api.elements.dateFrom.value, documents[0].period_from);
  assert.equal(api.elements.dateTo.value, documents[0].period_to);
});

test("POZ overnight marker and date chip reset retain the complete window", () => {
  const api = harness();
  const overnight = results.find(row => row.destination_airport === "POZ" &&
    api.dayOffset(row.legs[0].departure_at, row.legs.at(-1).arrival_at) === 1);
  assert.ok(overnight);
  const time = api.createJourneyTime(overnight.legs.at(-1).arrival_at, overnight.legs[0].departure_at);
  assert.equal(time.children.at(-1).textContent, "+1");
  api.initializeFilters();
  api.elements.dateFrom.value = documents[0].period_to;
  api.elements.dateTo.value = documents[0].period_to;
  api.clearActiveFilter("dateRange");
  assert.equal(api.elements.dateFrom.value, documents[0].period_from);
  assert.equal(api.elements.dateTo.value, documents[0].period_to);
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

test("all eight sort orders sort whole GDN, WRO, POZ and LCJ result sets", () => {
  const api = harness();
  for (const endpoint of ["GDN", "WRO", "POZ", "LCJ"]) for (const direction of ["poland_to_tenerife", "tenerife_to_poland"]) {
    const selected = filters(direction, {
      origin: direction === "poland_to_tenerife" ? endpoint : "all",
      destination: direction === "tenerife_to_poland" ? endpoint : "all",
    });
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
      assert.ok(sorted.length > 0, `${endpoint}/${direction}`);
      assert.equal(sorted.length, api.filteredResults(selected).length);
      for (let index = 1; index < sorted.length; index++) assert.ok(criterion(sorted[index - 1]) <= criterion(sorted[index]), sort);
    }
  }
});

test("GDN, WRO, POZ and LCJ airport chips clear the selection back to all", () => {
  const api = harness();
  for (const endpoint of ["GDN", "WRO", "POZ", "LCJ"]) {
    api.elements.origin.value = endpoint;
    api.renderActiveFilters(filters("poland_to_tenerife", {origin: endpoint}));
    for (const container of [api.elements.calendarActiveFilters, api.elements.activeFilters]) {
      const chip = container.children.find(child => child.dataset.filterKey === "origin");
      assert.equal(chip.attributes["aria-label"], `Wyczyść filtr: Wylot: ${endpoint}`);
      chip.listeners.click[0]();
      assert.equal(api.elements.origin.value, "all");
    }
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
  for (const endpoint of ["GDN", "WRO", "POZ", "LCJ"]) {
    const result = results.find(result => result.origin_airport === endpoint && result.price_total_regular_pln > 1000);
    assert.ok(result);
    api.context.window.location = new URL(api.shareUrlForResult(result, { resident: false, wizzClub: false }));
    assert.equal(api.sharedResultFromUrl().id, result.id);
    assert.ok(Number(api.elements.price.value) >= result.price_total_regular_pln);
    assert.ok(api.filteredResults().some(candidate => candidate.id === result.id));
  }
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
