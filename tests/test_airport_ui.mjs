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
const steps = ["1", "1b", "1c", "1d", "1e", "1f", "2", "3", "4", "5", "6"];
const documents = steps.map(step => JSON.parse(readFileSync(resolve(feedDirectory, `step${step}-results.json`), "utf8")));
const results = documents.flatMap(document => document.results);

test("partial update label distinguishes inherited full-base dates from rebuilt feeds", () => {
  const api = harness();
  const full = { generated_at: "2026-10-24T10:00:00+00:00" };
  assert.match(api.collectionUpdateLabel([full]), /^Aktualizacja /);
  assert.doesNotMatch(api.collectionUpdateLabel([full]), /częściowa/);
  const partial = { generated_at: "2026-10-25T12:00:00+00:00", data_lineage: {
    mode: "incremental", updated_at: "2026-10-25T11:00:00+00:00",
    last_full_collection_at: full.generated_at,
  }};
  assert.match(api.collectionUpdateLabel([partial]), /Aktualizacja częściowa 25.*pełna baza 24/);
});

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
  const source = readFileSync(resolve(root, process.env.RESIFLY_TEST_APP_PATH || "app.js"), "utf8");
  assert.match(source, /\nloadFlights\(\);\s*$/);
  vm.runInContext(source.replace(/\nloadFlights\(\);\s*$/, ""), context);
  vm.runInContext(`globalThis.api = {state, elements, updateAirportOptions, filteredResults,
    selectedResultPricing, lowestPricesByDate, renderActiveFilters, clearActiveFilter,
    createCalendarDay, createFareChartDay, parseDateOnly, shareUrlForResult,
    sharedResultFromUrl, configureSharedResultFilters, journeyDuration, dayOffset,
    createJourneyTime, updateRangeLabels, resetFilters, initializeFilters, currentFilters,
    bookingUrlForFilters, createPurchaseStep, airportPickers, setPolishAirports,
    polishAirportCodes, changeDirection, fareCalendarRenderKey, resultCardsRenderKey, DATA_SOURCES, carrierLogos,
    bindAirportPickerEvents, closeAirportPickers, optionLabel, collectionUpdateLabel};
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
    assert.equal(select.children[1].textContent, api.optionLabel(available[0]));
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
  // Freeze historical eight, then add the ninth endpoint explicitly.
  const eight = new Set(["WAW", "WMI", "KTW", "KRK", "GDN", "WRO", "POZ", "LCJ"]);
  const api = harness({rows: [...results.filter(r => [r.origin_airport, r.destination_airport].some(code => eight.has(code))), ...samples]});
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

function syntheticLuzRows() {
  return syntheticRzeRows().map(row => {
    row.id = row.id.replace("rze", "luz");
    if (row.direction === "poland_to_tenerife") {
      row.origin_airport = row.legs[0].departure_airport = "LUZ";
    } else row.destination_airport = row.legs.at(-1).arrival_airport = "LUZ";
    return row;
  });
}

const frozenEleven = new Set(["WAW", "WMI", "KTW", "KRK", "GDN", "WRO", "POZ", "LCJ", "RZE", "BZG", "LUZ"]);
function syntheticNewAirportRows(code) {
  return syntheticLuzRows().map(row => {
    row.id = row.id.replace("luz", code.toLowerCase());
    if (row.direction === "poland_to_tenerife") row.origin_airport = row.legs[0].departure_airport = code;
    else row.destination_airport = row.legs.at(-1).arrival_airport = code;
    return row;
  });
}

test("fifteen synthetic endpoints: SZZ/IEG labels, OR selection, chips and direction", () => {
  const old = new Set([...frozenEleven, "SZY", "RDO"]);
  const base = results.filter(r => [r.origin_airport,r.destination_airport].some(c => old.has(c)));
  // RDO can have no real offers, so complete the synthetic fifteen explicitly.
  const existing = new Set(base.flatMap(r => [r.origin_airport,r.destination_airport]));
  const rows = [...base,...[...old].filter(c => !existing.has(c)).flatMap(syntheticNewAirportRows),
                ...syntheticNewAirportRows("SZZ"),...syntheticNewAirportRows("IEG")];
  const api=harness({rows}); api.initializeFilters();
  assert.equal(api.polishAirportCodes().length,15);
  assert.equal(api.optionLabel("SZZ"),"Szczecin–Goleniów (SZZ)");
  assert.equal(api.optionLabel("IEG"),"Zielona Góra–Babimost (IEG)");
  api.setPolishAirports(["SZZ","IEG","KRK","SZZ"]);
  for(const direction of ["poland_to_tenerife","tenerife_to_poland"]) {
    api.elements.direction.value=direction; api.changeDirection();
    assert.deepEqual(Array.from(api.currentFilters().polishAirports),["IEG","KRK","SZZ"]);
    const f={...api.currentFilters(),maxPrice:Infinity,maxLayover:1440};
    assert.deepEqual(api.filteredResults(f).map(r=>r.id).sort(),["IEG","KRK","SZZ"].flatMap(c=>api.filteredResults({...f,polishAirports:[c]})).map(r=>r.id).sort());
  }
  api.clearActiveFilter("polishAirport:SZZ");
  assert.deepEqual(Array.from(api.currentFilters().polishAirports),["IEG","KRK"]);
  api.clearActiveFilter("dateRange");
  assert.deepEqual(Array.from(api.currentFilters().polishAirports),["IEG","KRK"]);
});

test("SZZ/IEG calendar, chart, share, discounts, sorts and zero-offer semantics", () => {
  const base=results.filter(r=>!["SZZ","IEG"].some(c=>[r.origin_airport,r.destination_airport].includes(c)));
  for(const code of ["SZZ","IEG"]) {
    const empty=harness({rows:base}); empty.initializeFilters();
    assert.ok(!empty.airportPickers.origin.checkboxes.has(code));
    const sample=syntheticNewAirportRows(code);
    const api=harness({rows:[...base,...sample]}); api.initializeFilters();
    for(const direction of ["poland_to_tenerife","tenerife_to_poland"]) for(const resident of [false,true]) for(const wizzClub of [false,true]) {
      api.elements.direction.value=direction; api.changeDirection(); api.setPolishAirports([code]);
      const f={...api.currentFilters(),resident,wizzClub,maxPrice:Infinity,maxLayover:1440};
      const matches=api.filteredResults(f); assert.ok(matches.length);
      for(const [day,price] of api.lowestPricesByDate(matches,f)) {
        assert.equal(price.total,Math.min(...matches.filter(r=>r.legs[0].departure_at.slice(0,10)===day).map(r=>api.selectedResultPricing(r,f).total)));
        api.createCalendarDay(api.parseDateOnly(day),f.dateFrom,f.dateTo,api.lowestPricesByDate(matches,f)).listeners.click[0]();
        const bar=api.createFareChartDay(day,price,price.total); bar.listeners.click[0]();
        assert.match(bar.getAttribute("aria-label"),/zł/);
        assert.deepEqual(Array.from(api.context.targets).slice(-2),[price.resultId,price.resultId]);
      }
      for(const sort of ["price","regular","layover","departure","journey","departure_time","arrival_time","direct"])
        assert.deepEqual(api.filteredResults({...f,sort}).map(r=>r.id).sort(),matches.map(r=>r.id).sort());
      api.context.window.location=new URL(api.shareUrlForResult(matches[0],f));
      assert.equal(api.sharedResultFromUrl().id,matches[0].id);
      assert.equal(api.elements.resident.checked,resident);
      assert.equal(api.elements.wizzClub.checked,wizzClub);
    }
  }
});

test("complete fifteen-endpoint real source coverage and SZZ/IEG availability", t => {
  const direct=documents[6].collection_coverage;
  if(!["SZZ","IEG"].every(c=>direct?.routes.some(r=>[r.origin,r.destination].includes(c))))
    return t.skip("Run on the complete fifteen-endpoint staging before promotion");
  assert.equal(direct.status,"complete");
  assert.equal(direct.expected_queries,120*31);
  assert.equal(direct.completed_queries,direct.expected_queries);
  const api=harness(); api.initializeFilters();
  for(const code of ["SZZ","IEG"]) {
    const all=results.filter(r=>[r.origin_airport,r.destination_airport].includes(code));
    assert.equal(api.polishAirportCodes().includes(code),all.length>0);
    for(const carrier of ["Ryanair","Wizz Air"]) for(const tenerife of ["TFN","TFS"])
      for(const [o,d] of [[code,tenerife],[tenerife,code]]) {
        const route=direct.routes.find(r=>r.carrier===carrier && r.origin===o && r.destination===d);
        assert.equal(route.days.length,31); assert.ok(route.days.every(day=>day.status==="checked"));
      }
  }
});

test("thirteen synthetic options keep SZY and RDO distinct and filter an OR union", () => {
  const base = results.filter(r => [r.origin_airport, r.destination_airport].some(c => frozenEleven.has(c)));
  const api = harness({rows: [...base, ...syntheticNewAirportRows("SZY"), ...syntheticNewAirportRows("RDO")]});
  api.initializeFilters();
  assert.deepEqual(Array.from(api.polishAirportCodes()), ["BZG", "GDN", "KRK", "KTW", "LCJ", "LUZ", "POZ", "RDO", "RZE", "SZY", "WAW", "WMI", "WRO"]);
  assert.equal(api.airportPickers.origin.checkboxes.size, 13);
  assert.equal(api.optionLabel("SZY"), "Szymany / Olsztyn–Mazury (SZY)");
  assert.equal(api.optionLabel("RDO"), "Radom (RDO)");
  assert.equal(api.optionLabel("NRN"), "Weeze (NRN)");
  api.setPolishAirports(["SZY", "RDO", "LUZ", "SZY"]);
  assert.deepEqual(Array.from(api.currentFilters().polishAirports), ["LUZ", "RDO", "SZY"]);
  const old = api.currentFilters();
  api.setPolishAirports(["SZY", "RDO", "KRK"]);
  assert.notEqual(api.fareCalendarRenderKey(old), api.fareCalendarRenderKey(api.currentFilters()));
  assert.notEqual(api.resultCardsRenderKey(old), api.resultCardsRenderKey(api.currentFilters()));
  for (const direction of ["poland_to_tenerife", "tenerife_to_poland"]) {
    api.elements.direction.value = direction; api.changeDirection();
    assert.deepEqual(Array.from(api.currentFilters().polishAirports), ["KRK", "RDO", "SZY"]);
    const f = {...api.currentFilters(), maxPrice: Infinity, maxLayover: 1440};
    assert.deepEqual(api.filteredResults(f).map(r => r.id).sort(), ["KRK", "RDO", "SZY"].flatMap(c => api.filteredResults({...f,polishAirports:[c]})).map(r => r.id).sort());
  }
  api.clearActiveFilter("polishAirport:RDO");
  assert.deepEqual(Array.from(api.currentFilters().polishAirports), ["KRK", "SZY"]);
  api.clearActiveFilter("dateRange");
  assert.deepEqual(Array.from(api.currentFilters().polishAirports), ["KRK", "SZY"]);
  api.resetFilters();
  assert.deepEqual(Array.from(api.currentFilters().polishAirports), []);
});

test("new endpoints with zero or one-way results never fabricate a checkbox or reverse flight", () => {
  const base = results.filter(r => [r.origin_airport,r.destination_airport].some(c => frozenEleven.has(c)));
  for (const code of ["SZY", "RDO"]) {
    const empty = harness({rows: base}); empty.initializeFilters();
    assert.ok(!empty.polishAirportCodes().includes(code));
    assert.ok(!empty.airportPickers.origin.checkboxes.has(code));
    for (const direction of ["poland_to_tenerife", "tenerife_to_poland"]) {
      const sample = syntheticNewAirportRows(code).find(r => r.direction === direction);
      const api = harness({rows:[...base,sample]}); api.initializeFilters();
      api.setPolishAirports([code]);
      api.elements.direction.value = direction === "poland_to_tenerife" ? "tenerife_to_poland" : "poland_to_tenerife";
      api.changeDirection();
      assert.ok(api.polishAirportCodes().includes(code));
      assert.deepEqual(Array.from(api.currentFilters().polishAirports), [code]);
      assert.equal(api.filteredResults({...api.currentFilters(),maxPrice:Infinity,maxLayover:1440}).length,0);
    }
  }
});

test("SZY and RDO calendar/chart, all discounts and sorts, share and overnight remain consistent", () => {
  const base = results.filter(r => [r.origin_airport,r.destination_airport].some(c => frozenEleven.has(c)));
  const api = harness({rows:[...base,...syntheticNewAirportRows("SZY"),...syntheticNewAirportRows("RDO")]});
  api.initializeFilters();
  for (const code of ["SZY", "RDO"]) for (const direction of ["poland_to_tenerife", "tenerife_to_poland"])
    for (const resident of [false,true]) for (const wizzClub of [false,true]) {
      api.elements.direction.value = direction; api.changeDirection(); api.setPolishAirports([code]);
      const f = {...api.currentFilters(),resident,wizzClub,maxPrice:Infinity,maxLayover:1440};
      const matches = api.filteredResults(f); assert.ok(matches.length);
      const minima = api.lowestPricesByDate(matches,f);
      for (const [day,price] of minima) {
        assert.equal(price.total,Math.min(...matches.filter(r => r.legs[0].departure_at.slice(0,10)===day).map(r => api.selectedResultPricing(r,f).total)));
        api.createCalendarDay(api.parseDateOnly(day),f.dateFrom,f.dateTo,minima).listeners.click[0]();
        const bar = api.createFareChartDay(day,price,price.total); bar.listeners.click[0]();
        assert.match(bar.getAttribute("aria-label"),/zł/);
        assert.deepEqual(Array.from(api.context.targets).slice(-2),[price.resultId,price.resultId]);
      }
      for (const sort of ["price","regular","layover","departure","journey","departure_time","arrival_time","direct"])
        assert.deepEqual(api.filteredResults({...f,sort}).map(r => r.id).sort(),matches.map(r => r.id).sort());
      const row = matches[0]; api.context.window.location=new URL(api.shareUrlForResult(row,f));
      assert.equal(api.sharedResultFromUrl().id,row.id);
      assert.equal(api.elements.resident.checked,resident); assert.equal(api.elements.wizzClub.checked,wizzClub);
      assert.deepEqual(Array.from(api.currentFilters().polishAirports),[]);
      assert.ok(api.filteredResults().some(r => r.id===row.id));
    }
  for (const code of ["SZY","RDO"]) {
    const expensive=syntheticNewAirportRows(code)[0]; expensive.id += "-expensive";
    expensive.price_total_regular_pln=2100; expensive.legs[0].price_regular_pln+=2100;
    api.state.results.push(expensive);
    api.context.window.location=new URL(api.shareUrlForResult(expensive,{resident:false,wizzClub:false}));
    assert.equal(api.sharedResultFromUrl().id,expensive.id); assert.ok(Number(api.elements.price.value)>=2100);
  }
  assert.equal(api.createJourneyTime("2026-11-02T00:55:00+01:00","2026-11-01T18:00:00+00:00").children.at(-1).textContent,"+1");
});

test("complete thirteen-endpoint batch checks real SZY/RDO availability without requiring invented offers", t => {
  const direct=documents[6].collection_coverage;
  if (direct?.status!=="complete" || !["SZY","RDO"].every(c => direct.routes.some(r => [r.origin,r.destination].includes(c))))
    return t.skip("Thirteen-endpoint collection absent: rerun on complete staging before promotion");
  assert.equal(direct.expected_queries,direct.routes.length*31);
  assert.equal(direct.completed_queries,direct.expected_queries);
  const api=harness(); api.initializeFilters();
  for (const code of ["SZY","RDO"]) {
    const all=results.filter(r => [r.origin_airport,r.destination_airport].includes(code));
    assert.equal(api.polishAirportCodes().includes(code),all.length>0);
    if (!all.length) continue; // Complete checked source coverage proves the empty case.
    for (const direction of ["poland_to_tenerife","tenerife_to_poland"]) for (const resident of [false,true]) for (const wizzClub of [false,true]) {
      api.elements.direction.value=direction; api.changeDirection(); api.setPolishAirports([code]);
      const f={...api.currentFilters(),resident,wizzClub,maxPrice:Infinity,maxLayover:1440};
      const matches=api.filteredResults(f);
      assert.deepEqual(matches.map(r => r.id).sort(),all.filter(r => r.direction===direction).map(r => r.id).sort());
      const criteria={price:r=>api.selectedResultPricing(r,f).total,regular:r=>r.price_total_regular_pln,layover:r=>r.layover_minutes??0,
        departure:r=>r.legs[0].departure_at,journey:r=>api.journeyDuration(r),departure_time:r=>r.legs[0].departure_at.slice(11,16),arrival_time:r=>r.legs.at(-1).arrival_at.slice(11,16),direct:r=>Number(r.legs.length!==1)};
      for (const [sort,key] of Object.entries(criteria)) {
        const sorted=api.filteredResults({...f,sort});
        for(let i=1;i<sorted.length;i++) assert.ok(key(sorted[i-1])<=key(sorted[i]),sort);
      }
      for (const [day,price] of api.lowestPricesByDate(matches,f)) {
        api.createFareChartDay(day,price,price.total).listeners.click[0]();
        assert.equal(api.context.targets.at(-1),price.resultId);
      }
      if(matches.length) {
        const row=matches[0]; api.context.window.location=new URL(api.shareUrlForResult(row,f));
        assert.equal(api.sharedResultFromUrl().id,row.id);
        assert.equal(api.elements.resident.checked,resident); assert.equal(api.elements.wizzClub.checked,wizzClub);
      }
    }
  }
});

test("eleventh LUZ checkbox, OR union, direction, chips, caches and resets", () => {
  const ten = new Set(["WAW", "WMI", "KTW", "KRK", "GDN", "WRO", "POZ", "LCJ", "RZE", "BZG"]);
  const rows = [...results.filter(r => [r.origin_airport, r.destination_airport].some(c => ten.has(c))), ...syntheticLuzRows()];
  const api = harness({rows});
  api.initializeFilters();
  assert.deepEqual(Array.from(api.polishAirportCodes()), ["BZG", "GDN", "KRK", "KTW", "LCJ", "LUZ", "POZ", "RZE", "WAW", "WMI", "WRO"]);
  assert.equal(api.airportPickers.origin.checkboxes.size, 11);
  assert.equal(api.airportPickers.origin.checkboxes.get("LUZ").value, "LUZ");
  assert.equal(api.optionLabel("LUZ"), "Lublin (LUZ)");
  const before = api.currentFilters();
  api.setPolishAirports(["LUZ", "BZG", "KRK", "LUZ"]);
  assert.deepEqual(Array.from(api.currentFilters().polishAirports), ["BZG", "KRK", "LUZ"]);
  assert.notEqual(api.fareCalendarRenderKey(before), api.fareCalendarRenderKey(api.currentFilters()));
  assert.notEqual(api.resultCardsRenderKey(before), api.resultCardsRenderKey(api.currentFilters()));
  for (const direction of ["poland_to_tenerife", "tenerife_to_poland"]) {
    api.elements.direction.value = direction;
    api.changeDirection();
    const f = {...api.currentFilters(), maxPrice: Infinity, maxLayover: 1440};
    const union = api.filteredResults(f);
    assert.deepEqual(union.map(r => r.id).sort(), ["LUZ", "BZG", "KRK"].flatMap(c => api.filteredResults({...f, polishAirports: [c]})).map(r => r.id).sort());
    assert.ok(union.some(r => r.id === `synthetic-luz-${direction}`));
  }
  api.renderActiveFilters(api.currentFilters());
  const chip = api.elements.activeFilters.children.find(c => c.dataset.filterKey === "polishAirport:LUZ");
  assert.ok(chip);
  chip.listeners.click[0]();
  assert.deepEqual(Array.from(api.currentFilters().polishAirports), ["BZG", "KRK"]);
  api.setPolishAirports(["LUZ", "BZG", "KRK"]);
  api.clearActiveFilter("dateRange");
  assert.deepEqual(Array.from(api.currentFilters().polishAirports), ["BZG", "KRK", "LUZ"]);
  api.setPolishAirports(api.polishAirportCodes());
  assert.deepEqual(Array.from(api.currentFilters().polishAirports), []);
  api.resetFilters();
  assert.equal(api.elements.direction.value, "poland_to_tenerife");
  assert.equal(Number(api.elements.price.value), 1000);
  assert.equal(Number(api.elements.layover.value), 6);
});

test("LUZ zero and one-way availability never invent a result or checkbox", () => {
  const base = results.filter(r => ![r.origin_airport, r.destination_airport].includes("LUZ"));
  const empty = harness({rows: base});
  empty.initializeFilters();
  assert.ok(!empty.polishAirportCodes().includes("LUZ"));
  assert.ok(!empty.airportPickers.origin.checkboxes.has("LUZ"));
  const api = harness({rows: [...base, syntheticLuzRows()[0]]});
  api.initializeFilters(); api.setPolishAirports(["LUZ"]);
  api.elements.direction.value = "tenerife_to_poland"; api.changeDirection();
  assert.ok(api.airportPickers.destination.checkboxes.has("LUZ"));
  assert.deepEqual(Array.from(api.currentFilters().polishAirports), ["LUZ"]);
  assert.equal(api.filteredResults({...api.currentFilters(), maxPrice: Infinity, maxLayover: 1440}).length, 0);
});

test("LUZ calendar/chart same card, all discounts, eight sorts, share and overnight", () => {
  const rows = [...results.filter(r => ![r.origin_airport, r.destination_airport].includes("LUZ")), ...syntheticLuzRows()];
  const api = harness({rows}); api.initializeFilters();
  for (const direction of ["poland_to_tenerife", "tenerife_to_poland"]) for (const resident of [false,true]) for (const wizzClub of [false,true]) {
    api.elements.direction.value = direction; api.changeDirection(); api.setPolishAirports(["LUZ"]);
    const f = {...api.currentFilters(), resident, wizzClub, maxPrice: Infinity, maxLayover: 1440};
    const matches = api.filteredResults(f); assert.ok(matches.length);
    const minima = api.lowestPricesByDate(matches, f);
    for (const [day, price] of minima) {
      assert.equal(price.total, Math.min(...matches.filter(r => r.legs[0].departure_at.slice(0,10) === day).map(r => api.selectedResultPricing(r,f).total)));
      api.createCalendarDay(api.parseDateOnly(day), f.dateFrom, f.dateTo, minima).listeners.click[0]();
      const bar = api.createFareChartDay(day,price,price.total); bar.listeners.click[0]();
      assert.match(bar.getAttribute("aria-label"), /zł/);
      assert.deepEqual(Array.from(api.context.targets).slice(-2), [price.resultId,price.resultId]);
    }
    for (const sort of ["price","regular","layover","departure","journey","departure_time","arrival_time","direct"]) {
      assert.deepEqual(api.filteredResults({...f,sort}).map(r => r.id).sort(), matches.map(r => r.id).sort());
    }
    const row = matches[0];
    api.context.window.location = new URL(api.shareUrlForResult(row,f));
    assert.equal(api.sharedResultFromUrl().id,row.id);
    assert.equal(api.elements.resident.checked,resident);
    assert.equal(api.elements.wizzClub.checked,wizzClub);
    assert.deepEqual(Array.from(api.currentFilters().polishAirports),[]);
    assert.ok(api.filteredResults().some(r => r.id === row.id));
  }
  const expensive = syntheticLuzRows()[0]; expensive.id="synthetic-luz-expensive";
  expensive.price_total_regular_pln = 2100;
  expensive.legs[0].price_regular_pln += 2100;
  api.state.results.push(expensive);
  api.context.window.location = new URL(api.shareUrlForResult(expensive,{resident:false,wizzClub:false}));
  assert.equal(api.sharedResultFromUrl().id,expensive.id);
  assert.ok(Number(api.elements.price.value) >= 2100);
  const clock = api.createJourneyTime("2026-11-02T00:55:00+01:00","2026-11-01T18:00:00+00:00");
  assert.equal(clock.children.at(-1).textContent,"+1");
});

test("real LUZ offers both directions are checked after the eleven-endpoint collection", t => {
  const eleven = documents.every(d => d.collection_coverage?.status === "complete" &&
    d.collection_coverage?.routes?.some?.(r => r.origin === "LUZ" || r.destination === "LUZ")) || results.some(r => [r.origin_airport,r.destination_airport].includes("LUZ"));
  if (!eleven) return t.skip("LUZ collection not yet present: rerun on new staging before promotion");
  const api = harness(); api.initializeFilters();
  for (const direction of ["poland_to_tenerife","tenerife_to_poland"]) {
    const matches = results.filter(r => r.direction === direction && [r.origin_airport,r.destination_airport].includes("LUZ"));
    assert.ok(matches.length, direction);
    api.elements.direction.value = direction; api.changeDirection(); api.setPolishAirports(["LUZ"]);
    for (const resident of [false,true]) for (const wizzClub of [false,true]) {
      // Sharing intentionally clears airport restrictions. Each scenario
      // starts with a fresh explicit LUZ selection instead of inheriting All.
      api.setPolishAirports(["LUZ"]);
      const f = {...api.currentFilters(),resident,wizzClub,maxPrice:Infinity,maxLayover:1440};
      assert.deepEqual(api.filteredResults(f).map(r => r.id).sort(),matches.map(r => r.id).sort());
      const minima=api.lowestPricesByDate(matches,f);
      for (const [day,price] of minima) {
        assert.equal(price.total,Math.min(...matches.filter(r => r.legs[0].departure_at.slice(0,10)===day).map(r => api.selectedResultPricing(r,f).total)));
        api.createCalendarDay(api.parseDateOnly(day),f.dateFrom,f.dateTo,minima).listeners.click[0]();
        api.createFareChartDay(day,price,price.total).listeners.click[0]();
        assert.deepEqual(Array.from(api.context.targets).slice(-2),[price.resultId,price.resultId]);
      }
      const criteria={price:r=>api.selectedResultPricing(r,f).total, regular:r=>r.price_total_regular_pln,
        layover:r=>r.layover_minutes??0, departure:r=>r.legs[0].departure_at, journey:r=>api.journeyDuration(r),
        departure_time:r=>r.legs[0].departure_at.slice(11,16), arrival_time:r=>r.legs.at(-1).arrival_at.slice(11,16),direct:r=>Number(r.legs.length!==1)};
      for (const [sort,key] of Object.entries(criteria)) {
        const sorted=api.filteredResults({...f,sort});
        for(let i=1;i<sorted.length;i++) assert.ok(key(sorted[i-1])<=key(sorted[i]),sort);
      }
      const row=matches[0]; api.context.window.location=new URL(api.shareUrlForResult(row,f));
      assert.equal(api.sharedResultFromUrl().id,row.id);
      assert.equal(api.elements.resident.checked,resident); assert.equal(api.elements.wizzClub.checked,wizzClub);
      assert.ok(api.filteredResults().some(r=>r.id===row.id));
    }
  }
});

function syntheticBzgRows() {
  return syntheticRzeRows().map(row => {
    row.id = row.id.replace("rze", "bzg");
    if (row.direction === "poland_to_tenerife") {
      row.origin_airport = "BZG";
      row.legs[0].departure_airport = "BZG";
    } else {
      row.destination_airport = "BZG";
      row.legs.at(-1).arrival_airport = "BZG";
    }
    return row;
  });
}

test("tenth BZG checkbox, OR union, cache keys and individual airport chips", () => {
  const nine = new Set(["WAW", "WMI", "KTW", "KRK", "GDN", "WRO", "POZ", "LCJ", "RZE"]);
  const api = harness({rows: [...results.filter(r => [r.origin_airport, r.destination_airport].some(code => nine.has(code))), ...syntheticBzgRows()]});
  api.initializeFilters();
  assert.deepEqual(Array.from(api.polishAirportCodes()), ["BZG", "GDN", "KRK", "KTW", "LCJ", "POZ", "RZE", "WAW", "WMI", "WRO"]);
  assert.equal(api.airportPickers.origin.checkboxes.size, 10);
  assert.equal(api.airportPickers.origin.checkboxes.get("BZG").value, "BZG");
  const before = api.currentFilters();
  api.setPolishAirports(["RZE", "BZG", "KRK", "BZG"]);
  assert.deepEqual(Array.from(api.currentFilters().polishAirports), ["BZG", "KRK", "RZE"]);
  assert.notEqual(api.fareCalendarRenderKey(before), api.fareCalendarRenderKey(api.currentFilters()));
  assert.notEqual(api.resultCardsRenderKey(before), api.resultCardsRenderKey(api.currentFilters()));
  for (const direction of ["poland_to_tenerife", "tenerife_to_poland"]) {
    api.elements.direction.value = direction;
    api.changeDirection();
    const f = {...api.currentFilters(), maxPrice: Infinity, maxLayover: 1440};
    assert.deepEqual(Array.from(f.polishAirports), ["BZG", "KRK", "RZE"]);
    const union = api.filteredResults(f).map(r => r.id).sort();
    const separate = ["BZG", "KRK", "RZE"].flatMap(code => api.filteredResults({...f, polishAirports: [code]})).map(r => r.id).sort();
    assert.deepEqual(union, separate);
  }
  api.clearActiveFilter("polishAirport:BZG");
  assert.deepEqual(Array.from(api.currentFilters().polishAirports), ["KRK", "RZE"]);
  api.setPolishAirports(api.polishAirportCodes());
  assert.deepEqual(Array.from(api.currentFilters().polishAirports), []);
});

test("BZG one-way and no-offer fixtures respect the union and direction retention", () => {
  const without = results.filter(r => ![r.origin_airport, r.destination_airport].includes("BZG"));
  const api = harness({rows: [...without, syntheticBzgRows()[0]]});
  api.initializeFilters();
  api.setPolishAirports(["BZG"]);
  api.elements.direction.value = "tenerife_to_poland";
  api.changeDirection();
  assert.ok(api.airportPickers.destination.checkboxes.has("BZG"));
  assert.deepEqual(Array.from(api.currentFilters().polishAirports), ["BZG"]);
  assert.equal(api.filteredResults({...api.currentFilters(), maxPrice: Infinity, maxLayover: 1440}).length, 0);
  const empty = harness({rows: without});
  empty.initializeFilters();
  assert.equal(empty.airportPickers.origin.checkboxes.has("BZG"), false);
});

test("collected BZG prices, eight sorts, calendar/chart targets and shared links agree", t => {
  if (!results.some(r => [r.origin_airport, r.destination_airport].includes("BZG"))) {
    t.skip("Pre-BZG data: repeat on the complete new staging and report any verified zero explicitly");
    return;
  }
  const api = harness();
  api.initializeFilters();
  for (const direction of ["poland_to_tenerife", "tenerife_to_poland"]) for (const resident of [false, true]) for (const wizzClub of [false, true]) {
    api.elements.direction.value = direction;
    api.changeDirection();
    api.setPolishAirports(["BZG"]);
    const f = {...api.currentFilters(), resident, wizzClub, maxPrice: Infinity, maxLayover: 1440};
    const rows = api.filteredResults(f);
    assert.ok(rows.length > 0, direction);
    assert.ok(rows.every(r => [r.origin_airport, r.destination_airport].includes("BZG")));
    const criteria = {
      price: r => api.selectedResultPricing(r, f).total, regular: r => r.price_total_regular_pln,
      layover: r => r.layover_minutes ?? 0, departure: r => r.legs[0].departure_at,
      journey: r => api.journeyDuration(r), departure_time: r => r.legs[0].departure_at.slice(11, 16),
      arrival_time: r => r.legs.at(-1).arrival_at.slice(11, 16), direct: r => Number(r.legs.length !== 1),
    };
    for (const [sort, value] of Object.entries(criteria)) {
      const sorted = api.filteredResults({...f, sort});
      assert.equal(sorted.length, rows.length);
      for (let n = 1; n < sorted.length; n++) assert.ok(value(sorted[n - 1]) <= value(sorted[n]), sort);
    }
    const minima = api.lowestPricesByDate(rows, f);
    for (const [day, price] of minima) assert.equal(price.total, Math.min(...rows.filter(r => r.legs[0].departure_at.slice(0, 10) === day).map(r => api.selectedResultPricing(r, f).total)));
    const [day, price] = [...minima][0];
    api.createCalendarDay(api.parseDateOnly(day), f.dateFrom, f.dateTo, minima).dispatchEvent(new Event("click"));
    api.createFareChartDay(day, price, price.total).dispatchEvent(new Event("click"));
    assert.deepEqual(Array.from(api.context.targets).slice(-2), [price.resultId, price.resultId]);
    const row = rows.find(r => r.id === price.resultId);
    api.context.window.location = new URL(api.shareUrlForResult(row, f));
    assert.equal(api.sharedResultFromUrl().id, row.id);
    assert.equal(api.elements.direction.value, direction);
    assert.equal(api.elements.resident.checked, resident);
    assert.equal(api.elements.wizzClub.checked, wizzClub);
    assert.deepEqual(Array.from(api.currentFilters().polishAirports), []);
    assert.ok(api.filteredResults().some(r => r.id === row.id));
  }
  const expensive = results.find(r => r.origin_airport === "BZG" && r.price_total_regular_pln > 1000);
  if (expensive) {
    api.context.window.location = new URL(api.shareUrlForResult(expensive, {resident: false, wizzClub: false}));
    assert.equal(api.sharedResultFromUrl().id, expensive.id);
    assert.ok(Number(api.elements.price.value) >= expensive.price_total_regular_pln);
    assert.ok(api.filteredResults().some(r => r.id === expensive.id));
  }
});

test("BZG overnight marker, date reset and full reset preserve existing semantics", () => {
  const api = harness({rows: [...results, ...syntheticBzgRows()]});
  api.initializeFilters();
  api.setPolishAirports(["BZG", "RZE", "KRK"]);
  const time = api.createJourneyTime("2026-11-02T00:55:00+01:00", "2026-11-01T18:00:00+00:00");
  assert.equal(time.children[1].tagName, "sup");
  assert.equal(time.children[1].textContent, "+1");
  api.elements.dateFrom.value = api.elements.dateTo.value = "2026-11-01";
  api.clearActiveFilter("dateRange");
  assert.equal(api.elements.dateFrom.value, documents[0].period_from);
  assert.equal(api.elements.dateTo.value, documents[0].period_to);
  assert.deepEqual(Array.from(api.currentFilters().polishAirports), ["BZG", "KRK", "RZE"]);
  api.resetFilters();
  assert.deepEqual(Array.from(api.currentFilters().polishAirports), []);
  assert.equal(api.elements.direction.value, "poland_to_tenerife");
  assert.equal(Number(api.elements.price.value), 1000);
  assert.equal(Number(api.elements.layover.value), 6);
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

test("Step 6 is required and easyJet has working carrier filters in both directions", () => {
  const api = harness(); api.initializeFilters();
  const source = api.DATA_SOURCES.find(row => row.url === "data/step6-results.json");
  assert.ok(source); assert.notEqual(source.optional, true);
  assert.match(api.carrierLogos.easyJet, /easyjet\.svg/);
  for (const direction of ["poland_to_tenerife", "tenerife_to_poland"]) {
    const selected = filters(direction, {origin:"all", destination:"all", maxPrice:Infinity, maxLayover:1440,
      firstCarrier: direction === "tenerife_to_poland" ? "easyJet" : "all",
      secondCarrier: direction === "poland_to_tenerife" ? "easyJet" : "all"});
    const matches = api.filteredResults(selected);
    assert.ok(matches.length);
    for (const row of matches) {
      assert.equal(row.legs[direction === "poland_to_tenerife" ? 1 : 0].carrier, "easyJet");
      assert.ok(["Ryanair", "Wizz Air"].includes(row.legs[direction === "poland_to_tenerife" ? 0 : 1].carrier));
    }
    const minima = api.lowestPricesByDate(matches, selected);
    for (const [day, price] of minima) {
      api.createCalendarDay(api.parseDateOnly(day), selected.dateFrom, selected.dateTo, minima).listeners.click[0]();
      api.createFareChartDay(day, price, price.total).listeners.click[0]();
      assert.deepEqual(Array.from(api.context.targets).slice(-2), [price.resultId,price.resultId]);
    }
    const row = matches[0];
    api.context.window.location = new URL(api.shareUrlForResult(row, selected));
    assert.equal(api.sharedResultFromUrl().id, row.id);
  }
});

test("easyJet discount toggles preserve regular fare and deterministic one-adult booking link", () => {
  const api = harness();
  const row = results.find(r => r.legs.some(leg => leg.carrier === "easyJet"));
  assert.ok(row);
  const leg = row.legs.find(leg => leg.carrier === "easyJet");
  for (const resident of [false,true]) for (const wizzClub of [false,true]) {
    const f = filters(row.direction, {resident,wizzClub});
    const price = api.selectedResultPricing({...row, legs:[leg], price_total_regular_pln:leg.price_regular_pln},f);
    assert.equal(price.total, leg.price_regular_pln);
    const link = new URL(api.bookingUrlForFilters(leg,f));
    assert.equal(link.hostname,"www.easyjet.com"); assert.equal(link.pathname,"/deeplink");
    assert.equal(link.searchParams.get("dep"),leg.departure_airport);
    assert.equal(link.searchParams.get("dest"),leg.arrival_airport);
    assert.equal(link.searchParams.get("dd"),leg.departure_at.slice(0,10));
    assert.equal(link.searchParams.get("apax"),"1");
    assert.equal(link.searchParams.has("residentType"),false);
    const purchase = api.createPurchaseStep(leg,0,f);
    const action = purchase.children.find(child => child.className === "purchase-step-actions").children[0];
    assert.equal(action.href,leg.booking_url); assert.equal(action.textContent,"Otwórz easyJet");
  }
});
