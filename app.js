const DATA_SOURCES = [
  { url: "data/step1-results.json" },
  { url: "data/step1b-results.json", optional: true },
  { url: "data/step1c-results.json", optional: true },
  { url: "data/step1d-results.json", optional: true },
  { url: "data/step1e-results.json", optional: true },
  { url: "data/step1f-results.json", optional: true },
  { url: "data/step2-results.json" },
  { url: "data/step3-results.json" },
  { url: "data/step4-results.json" },
  { url: "data/step5-results.json" },
];

const state = {
  document: null,
  results: [],
};

const elements = {
  updatedAt: document.querySelector("#updated-at"),
  resident: document.querySelector("#resident-filter"),
  wizzClub: document.querySelector("#wizz-club-filter"),
  price: document.querySelector("#price-filter"),
  priceOutput: document.querySelector("#price-output"),
  priceMaxLabel: document.querySelector("#price-max-label"),
  priceContext: document.querySelector("#price-context"),
  direction: document.querySelector("#direction-filter"),
  dateFrom: document.querySelector("#date-from"),
  dateTo: document.querySelector("#date-to"),
  origin: document.querySelector("#origin-filter"),
  destination: document.querySelector("#destination-filter"),
  transfer: document.querySelector("#transfer-filter"),
  firstCarrier: document.querySelector("#first-carrier-filter"),
  secondCarrier: document.querySelector("#second-carrier-filter"),
  layover: document.querySelector("#layover-filter"),
  layoverOutput: document.querySelector("#layover-output"),
  resultsLoadStatus: document.querySelector("#results-load-status"),
  resultsPreparation: document.querySelector("#results-preparation-progress"),
  resultsPreparationPercent: document.querySelector("#results-preparation-percent"),
  resultsPreparationTrack: document.querySelector("#results-preparation-track"),
  resultsHeaderLoadStatus: document.querySelector("#results-header-load-status"),
  resultsHeaderPreparation: document.querySelector("#results-header-preparation-progress"),
  resultsHeaderPreparationPercent: document.querySelector("#results-header-preparation-percent"),
  resultsHeaderPreparationTrack: document.querySelector("#results-header-preparation-track"),
  sort: document.querySelector("#sort-results"),
  reset: document.querySelector("#reset-filters"),
  calendarMonths: document.querySelector("#calendar-months"),
  farePriceChart: document.querySelector("#fare-price-chart"),
  calendarDirectionLabel: document.querySelector("#calendar-direction-label"),
  calendarDirectionSwap: document.querySelector("#calendar-direction-swap"),
  calendarLegendSelected: document.querySelector(".calendar-legend-resident"),
  calendarLegendRegular: document.querySelector(".calendar-legend-regular"),
  calendarActiveFilters: document.querySelector("#calendar-active-filters"),
  activeFilters: document.querySelector("#active-filters"),
  count: document.querySelector("#results-count"),
  countNoun: document.querySelector("#results-noun"),
  list: document.querySelector("#results-list"),
  template: document.querySelector("#result-template"),
  searchInfoButton: document.querySelector("#search-info-button"),
  searchInfoDialog: document.querySelector("#search-info-dialog"),
  purchaseDialog: document.querySelector("#purchase-dialog"),
  purchaseDialogContent: document.querySelector("#purchase-dialog-content"),
  shareStatus: document.querySelector("#share-status"),
};

const currency = new Intl.NumberFormat("pl-PL", {
  style: "currency",
  currency: "PLN",
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

const calendarCurrency = new Intl.NumberFormat("pl-PL", {
  style: "currency",
  currency: "PLN",
  minimumFractionDigits: 0,
  maximumFractionDigits: 2,
});

const chartWeekday = new Intl.DateTimeFormat("pl-PL", {
  weekday: "short",
});

const chartDate = new Intl.DateTimeFormat("pl-PL", {
  day: "numeric",
  month: "short",
});

const longDate = new Intl.DateTimeFormat("pl-PL", {
  weekday: "long",
  day: "numeric",
  month: "long",
});

const shortDate = new Intl.DateTimeFormat("pl-PL", {
  day: "numeric",
  month: "short",
  year: "numeric",
});

const weekday = new Intl.DateTimeFormat("pl-PL", {
  weekday: "long",
});

const monthYear = new Intl.DateTimeFormat("pl-PL", {
  month: "long",
  year: "numeric",
  timeZone: "UTC",
});

const purchaseDate = new Intl.DateTimeFormat("pl-PL", {
  day: "numeric",
  month: "long",
  year: "numeric",
});

const calendarWeekdays = ["Pn", "Wt", "Śr", "Cz", "Pt", "Sb", "Nd"];
const CALENDAR_SCROLL_SETTLE_FALLBACK_MS = 1_200;
const FILTER_RENDER_DELAY_MS = 150;
const DEFAULT_MAX_PRICE = 1000;
const DEFAULT_DIRECTION = "poland_to_tenerife";
const RESULT_BATCH_SIZE = 30;
const BACKGROUND_RESULT_BATCH_SIZE = 5;
const BACKGROUND_RESULT_START_DELAY_MS = 350;
const BACKGROUND_RESULT_FALLBACK_DELAY_MS = 80;
const RESULT_VIEW_CACHE_LIMIT = 4;
const RESULT_CARD_NODE_CACHE_LIMIT = 1_200;

let filterRenderTimer;
let calendarRenderKey = null;
let progressiveResults = [];
let progressiveFilters = null;
let progressiveResultCount = 0;
let progressiveLoadedResultIndexes = new Set();
let progressivePreparedResultCards = new Map();
let progressiveRenderVersion = 0;
let progressiveIdleHandle = null;
let progressiveIdleUsesTimeout = false;
let progressiveCommitPending = false;
let activeResultCacheKey = null;
const resultViewCache = new Map();
const resultCardNodeCache = new Map();
let calendarTargetCard = null;
let calendarNavigationPending = false;
let calendarNavigationTimer = null;
let calendarScrollEndHandler = null;
let shareStatusTimer = null;

const carrierLogos = {
  Binter: "assets/logos/binter.svg",
  "Wizz Air": "assets/logos/wizz-air.svg",
  Ryanair: "assets/logos/ryanair.svg",
  Vueling: "assets/logos/vueling.svg",
  "Air Europa": "assets/logos/air-europa.svg?v=20261021-1",
  "Iberia Express": "assets/logos/iberia-express.svg",
  Volotea: "assets/logos/volotea.svg?v=20261021-1",
  Canaryfly: "assets/logos/canaryfly.svg?v=20261021-1",
};

const carrierPurchaseUrls = {
  Binter: "https://www.bintercanarias.com/es/buscar-vuelos",
  Iberia: "https://www.iberia.com/flights/",
  "Iberia Express": "https://www.iberia.com/flights/",
  Vueling: "https://www.vueling.com/es",
  "Air Europa": "https://www.aireuropa.com/es/es/home",
  Volotea: "https://www.volotea.com/es/",
  Canaryfly: "https://www.canaryfly.es/es/",
  "Wizz Air": "https://wizzair.com/pl-pl",
  Ryanair: "https://www.ryanair.com/pl/pl",
};

function finitePrice(value) {
  const price = Number(value);
  return Number.isFinite(price) ? price : null;
}

function wizzClubPrice(leg) {
  return finitePrice(leg.price_wizz_discount_club_pln);
}

function selectedLegPrice(leg, filters) {
  const regular = finitePrice(leg.price_regular_pln) ?? 0;
  const resident = finitePrice(leg.price_resident_estimated_pln);
  if (filters.resident && leg.resident_discount_eligible && resident !== null && resident < regular) {
    return { value: resident, kind: "resident", regular };
  }

  const club = wizzClubPrice(leg);
  if (filters.wizzClub && leg.carrier === "Wizz Air" && club !== null && club < regular) {
    return { value: club, kind: "wizz-club", regular };
  }

  return { value: regular, kind: "regular", regular };
}

function selectedResultPricing(result, filters) {
  const legs = result.legs.map(leg => selectedLegPrice(leg, filters));
  const total = legs.reduce((sum, leg) => sum + leg.value, 0);
  const regular = finitePrice(result.price_total_regular_pln)
    ?? legs.reduce((sum, leg) => sum + leg.regular, 0);
  return {
    total: Math.round(total * 100) / 100,
    regular,
    hasResident: legs.some(leg => leg.kind === "resident"),
    hasWizzClub: legs.some(leg => leg.kind === "wizz-club"),
  };
}

function selectedPriceCaption(pricing) {
  if (pricing.hasResident && pricing.hasWizzClub) return "Cena po zniżkach";
  if (pricing.hasResident) return "Cena dla rezydenta";
  if (pricing.hasWizzClub) return "Cena z Wizz Discount Club";
  return "Cena lotu";
}

function datePart(iso) {
  return iso.slice(0, 10);
}

function timePart(iso) {
  return iso.slice(11, 16);
}

function dayOffset(referenceTimestamp, timestamp) {
  const reference = Date.parse(`${datePart(referenceTimestamp)}T00:00:00Z`);
  const compared = Date.parse(`${datePart(timestamp)}T00:00:00Z`);
  return Math.max(0, Math.round((compared - reference) / 86_400_000));
}

function createJourneyTime(timestamp, referenceTimestamp, className = "") {
  const time = document.createElement("strong");
  if (className) time.className = className;
  time.append(timePart(timestamp));

  const offset = dayOffset(referenceTimestamp, timestamp);
  if (offset > 0) {
    const marker = document.createElement("sup");
    marker.className = "day-offset";
    marker.textContent = `+${offset}`;
    marker.title = offset === 1 ? "Następnego dnia" : `${offset} dni później`;
    marker.setAttribute("aria-label", marker.title);
    time.append(marker);
  }

  return time;
}

function parseDateOnly(iso) {
  return new Date(`${iso}T12:00:00Z`);
}

function toDateOnly(date) {
  return [
    date.getUTCFullYear(),
    String(date.getUTCMonth() + 1).padStart(2, "0"),
    String(date.getUTCDate()).padStart(2, "0"),
  ].join("-");
}

function capitalized(value) {
  return value.charAt(0).toUpperCase() + value.slice(1);
}

function formatDate(iso) {
  const safeDate = new Date(`${datePart(iso)}T12:00:00Z`);
  const value = longDate.format(safeDate);
  return value.charAt(0).toUpperCase() + value.slice(1);
}

function formatTimestampWithWeekday(iso) {
  const safeDate = new Date(`${datePart(iso)}T12:00:00Z`);
  return `${shortDate.format(safeDate)}, ${timePart(iso)} (${weekday.format(safeDate)})`;
}

function formatPurchaseTimestamp(iso) {
  const safeDate = new Date(`${datePart(iso)}T12:00:00Z`);
  return `${purchaseDate.format(safeDate)}, ${timePart(iso)}`;
}

function formatDuration(minutes) {
  const hours = Math.floor(minutes / 60);
  const remainder = minutes % 60;
  if (!remainder) return `${hours} godz.`;
  return `${hours} godz. ${remainder} min`;
}

function journeyDuration(result) {
  const departure = new Date(result.legs[0].departure_at);
  const arrival = new Date(result.legs.at(-1).arrival_at);
  return Math.round((arrival - departure) / 60000);
}

function isDirectConnection(result) {
  return result.legs.length === 1;
}

function pluralizeResults(count) {
  if (count === 1) return "wynik";
  const lastTwo = count % 100;
  const last = count % 10;
  if (last >= 2 && last <= 4 && !(lastTwo >= 12 && lastTwo <= 14)) return "wyniki";
  return "wyników";
}

function setResultLoadStatus(message, state = "loading") {
  [elements.resultsLoadStatus, elements.resultsHeaderLoadStatus].forEach((status) => {
    status.textContent = message;
    status.classList.toggle("is-loading", state === "loading");
    status.classList.toggle("is-complete", state === "complete");
    status.classList.toggle("is-empty", state === "empty");
  });
}

function resultPreparationDisplays() {
  return [
    {
      container: elements.resultsPreparation,
      percent: elements.resultsPreparationPercent,
      track: elements.resultsPreparationTrack,
    },
    {
      container: elements.resultsHeaderPreparation,
      percent: elements.resultsHeaderPreparationPercent,
      track: elements.resultsHeaderPreparationTrack,
    },
  ];
}

function hideResultPreparationProgress() {
  resultPreparationDisplays().forEach(({ container }) => {
    container.hidden = true;
    container.classList.remove("is-indeterminate", "is-complete");
  });
}

function updateResultPreparationProgress() {
  const total = progressiveResults.length;
  if (!total) {
    hideResultPreparationProgress();
    return;
  }

  const prepared = Math.min(
    total,
    progressiveLoadedResultIndexes.size + progressivePreparedResultCards.size
  );
  const complete = prepared >= total;
  const percent = complete ? 100 : Math.floor((prepared / total) * 100);

  resultPreparationDisplays().forEach(({ container, percent: percentElement, track }) => {
    container.hidden = false;
    container.classList.remove("is-indeterminate");
    container.classList.toggle("is-complete", complete);
    percentElement.textContent = `${percent}%`;
    container.style.setProperty("--prepared-progress", String(prepared / total));
    track.setAttribute("aria-valuenow", String(percent));
    track.setAttribute(
      "aria-valuetext",
      `Przygotowano ${prepared} z ${total} lotów, ${percent}%`
    );
  });
}

function updateResultLoadStatus() {
  const total = progressiveResults.length;
  if (!total) {
    hideResultPreparationProgress();
    setResultLoadStatus("Brak połączeń dla wybranych filtrów.", "empty");
    return;
  }

  updateResultPreparationProgress();

  const visible = elements.list.querySelectorAll(".flight-card").length;
  if (visible >= total) {
    setResultLoadStatus(`Loty na ekranie: ${total}/${total}. Wszystkie są gotowe.`, "complete");
    return;
  }

  setResultLoadStatus(
    `Loty na ekranie: ${visible}/${total}. Pozostałe są przygotowywane…`
  );
}

const airportLabels = {
  TFN: "Teneryfa Północ (TFN)",
  TFS: "Teneryfa Południe (TFS)",
  WAW: "Warszawa Chopina (WAW)",
  WMI: "Warszawa Modlin (WMI)",
  KTW: "Katowice (KTW)",
  KRK: "Kraków (KRK)",
  FUE: "Fuerteventura (FUE)",
  LPA: "Gran Canaria (LPA)",
  MAD: "Madryt (MAD)",
  PMI: "Palma de Mallorca (PMI)",
  ALC: "Alicante (ALC)",
  BCN: "Barcelona (BCN)",
  BIO: "Bilbao (BIO)",
  AGA: "Agadir (AGA)",
  AGP: "Malaga (AGP)",
  BGY: "Mediolan-Bergamo (BGY)",
  BBU: "Bukareszt-Băneasa (BBU)",
  BHX: "Birmingham (BHX)",
  BLQ: "Bolonia (BLQ)",
  BOH: "Bournemouth (BOH)",
  BRS: "Bristol (BRS)",
  BUD: "Budapeszt (BUD)",
  BVA: "Paryż-Beauvais (BVA)",
  CRL: "Bruksela-Charleroi (CRL)",
  DUB: "Dublin (DUB)",
  EDI: "Edynburg (EDI)",
  EIN: "Eindhoven (EIN)",
  EMA: "East Midlands (EMA)",
  FCO: "Rzym-Fiumicino (FCO)",
  FMM: "Memmingen (FMM)",
  GDN: "Gdańsk (GDN)",
  LBA: "Leeds-Bradford (LBA)",
  LPL: "Liverpool (LPL)",
  LTN: "Londyn-Luton (LTN)",
  MAN: "Manchester (MAN)",
  MRS: "Marsylia (MRS)",
  MXP: "Mediolan-Malpensa (MXP)",
  NAP: "Neapol (NAP)",
  NCL: "Newcastle (NCL)",
  OPO: "Porto (OPO)",
  OTP: "Bukareszt-Otopeni (OTP)",
  PSA: "Piza (PSA)",
  RAK: "Marrakesz (RAK)",
  SNN: "Shannon (SNN)",
  SCQ: "Santiago de Compostela (SCQ)",
  STN: "Londyn-Stansted (STN)",
  SVQ: "Sewilla (SVQ)",
  TLS: "Tuluza (TLS)",
  TSF: "Wenecja-Treviso (TSF)",
  VIE: "Wiedeń (VIE)",
  VLC: "Walencja (VLC)",
};

function optionLabel(code) {
  return airportLabels[code] || code;
}

function airportCityLabel(code) {
  return (airportLabels[code] || code).replace(new RegExp(`\\s*\\(${code}\\)$`), "");
}

function addOptions(select, values, formatter = value => value) {
  for (const value of values) {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = formatter(value);
    select.append(option);
  }
}

function resetAirportSelect(select) {
  select.replaceChildren();
  const all = document.createElement("option");
  all.value = "all";
  all.textContent = "Wszystkie lotniska";
  select.append(all);
}

function updateAirportOptions() {
  const direction = elements.direction.value;
  const matching = state.results.filter(result => result.direction === direction);
  const origins = [...new Set(matching.map(result => result.origin_airport))].sort();
  const destinations = [...new Set(matching.map(result => result.destination_airport))].sort();
  resetAirportSelect(elements.origin);
  resetAirportSelect(elements.destination);
  addOptions(elements.origin, origins, optionLabel);
  addOptions(elements.destination, destinations, optionLabel);
}

function lowestPricesByDate(results, filters) {
  const prices = new Map();
  for (const result of results) {
    const date = datePart(result.legs[0].departure_at);
    const pricing = selectedResultPricing(result, filters);
    if (!Number.isFinite(pricing.total) || !Number.isFinite(pricing.regular)) continue;
    const current = prices.get(date);
    if (current === undefined || pricing.total < current.total) {
      prices.set(date, { ...pricing, resultId: result.id });
    }
  }
  return prices;
}

function createCalendarDay(date, rangeStart, rangeEnd, prices) {
  const isoDate = toDateOnly(date);
  const outsideRange = isoDate < rangeStart || isoDate > rangeEnd;
  const price = prices.get(isoDate);
  const clickable = !outsideRange && price !== undefined;
  const cell = document.createElement(clickable ? "button" : "div");

  cell.className = "calendar-day";
  cell.dataset.date = isoDate;
  if (clickable) {
    cell.type = "button";
    cell.classList.add("is-clickable");
    cell.dataset.resultId = price.resultId;
  }

  const dayNumber = document.createElement("span");
  dayNumber.className = "calendar-day-number";
  dayNumber.textContent = String(date.getUTCDate());
  cell.append(dayNumber);

  if (outsideRange) {
    cell.classList.add("is-outside-range");
    cell.setAttribute("aria-label", `${formatDate(isoDate)}, poza zakresem wyszukiwania`);
    return cell;
  }

  const selectedPrice = document.createElement("strong");
  selectedPrice.className = "calendar-day-price";
  if (price === undefined) {
    cell.classList.add("has-no-price");
    selectedPrice.textContent = "—";
    cell.setAttribute("aria-label", `${formatDate(isoDate)}, brak połączeń`);
  } else {
    cell.classList.add("has-price");
    const discounted = price.total < price.regular;
    selectedPrice.textContent = `${calendarCurrency.format(price.total)}${discounted ? "*" : ""}`;
    cell.append(selectedPrice);
    if (discounted) {
      const regularPrice = document.createElement("span");
      regularPrice.className = "calendar-day-regular-price";
      regularPrice.textContent = calendarCurrency.format(price.regular);
      regularPrice.title = "Cena regularna";
      cell.append(regularPrice);
    }
    cell.setAttribute(
      "aria-label",
      `${formatDate(isoDate)}, ${selectedPriceCaption(price).toLowerCase()} ${currency.format(price.total)}${discounted ? `, cena regularna ${currency.format(price.regular)}` : ""}`
    );
    cell.addEventListener("click", () => scrollToResult(price.resultId));
    return cell;
  }
  cell.append(selectedPrice);
  return cell;
}

function setCardDetailsExpanded(card, expanded) {
  const toggle = card.querySelector(".details-toggle");
  const details = card.querySelector(".price-details");
  const shareButton = card.querySelector(".share-flight-button");
  if (!toggle || !details || !shareButton) return;

  toggle.setAttribute("aria-expanded", String(expanded));
  toggle.querySelector("span").textContent = expanded
    ? "Ukryj szczegóły ceny"
    : "Pokaż szczegóły ceny";
  details.hidden = !expanded;
  shareButton.hidden = !expanded;
  if (!expanded) {
    shareButton.textContent = "Kopiuj link do lotu";
    shareButton.classList.remove("is-copied");
  }
}

function showShareStatus(message, { error = false, persistent = false } = {}) {
  window.clearTimeout(shareStatusTimer);
  elements.shareStatus.textContent = message;
  elements.shareStatus.classList.toggle("is-error", error);
  elements.shareStatus.hidden = false;
  shareStatusTimer = persistent
    ? null
    : window.setTimeout(() => {
      elements.shareStatus.hidden = true;
    }, 3_200);
}

function shareUrlForResult(result, filters) {
  const url = new URL(window.location.href);
  url.search = "";
  url.hash = "";
  url.searchParams.set("flight", result.id);
  url.searchParams.set("resident", filters.resident ? "1" : "0");
  url.searchParams.set("wizz", filters.wizzClub ? "1" : "0");
  return url.toString();
}

async function writeClipboardText(text) {
  if (navigator.clipboard && window.isSecureContext) {
    await navigator.clipboard.writeText(text);
    return;
  }

  const textarea = document.createElement("textarea");
  textarea.value = text;
  textarea.setAttribute("readonly", "");
  textarea.style.position = "fixed";
  textarea.style.opacity = "0";
  document.body.append(textarea);
  textarea.select();
  const copied = document.execCommand("copy");
  textarea.remove();
  if (!copied) throw new Error("Browser did not copy the flight link");
}

async function copyFlightLink(result, filters, button) {
  try {
    await writeClipboardText(shareUrlForResult(result, filters));
    button.textContent = "Link skopiowany ✓";
    button.classList.add("is-copied");
    showShareStatus("Link do lotu został skopiowany.");
    window.setTimeout(() => {
      if (!button.isConnected) return;
      button.textContent = "Kopiuj link do lotu";
      button.classList.remove("is-copied");
    }, 2_800);
  } catch (error) {
    console.error("Nie udało się skopiować linku do lotu", error);
    showShareStatus("Nie udało się skopiować linku. Spróbuj ponownie.", { error: true });
  }
}

function clearCalendarTarget() {
  elements.list.querySelectorAll(".is-calendar-target").forEach(card => {
    card.classList.remove("is-calendar-target");
  });
  calendarTargetCard = null;
}

function clearCalendarNavigationGuard() {
  if (calendarNavigationTimer !== null) {
    window.clearTimeout(calendarNavigationTimer);
    calendarNavigationTimer = null;
  }
  if (calendarScrollEndHandler) {
    window.removeEventListener("scrollend", calendarScrollEndHandler);
    calendarScrollEndHandler = null;
  }
  calendarNavigationPending = false;
}

function finishCalendarNavigation() {
  clearCalendarNavigationGuard();
  if (!progressiveCommitPending) return;
  progressiveCommitPending = false;
  commitPreparedResults(progressiveRenderVersion);
}

function guardCalendarNavigation() {
  clearCalendarNavigationGuard();
  calendarNavigationPending = true;
  calendarScrollEndHandler = finishCalendarNavigation;
  window.addEventListener("scrollend", calendarScrollEndHandler, { once: true });
  calendarNavigationTimer = window.setTimeout(
    finishCalendarNavigation,
    CALENDAR_SCROLL_SETTLE_FALLBACK_MS
  );
}

function scrollToResult(resultId) {
  let card = [...elements.list.querySelectorAll(".flight-card")]
    .find(item => item.dataset.resultId === resultId);
  if (!card) {
    ensureResultRendered(resultId);
    card = [...elements.list.querySelectorAll(".flight-card")]
      .find(item => item.dataset.resultId === resultId);
  }
  if (!card) return;

  clearCalendarTarget();
  setCardDetailsExpanded(card, true);
  card.classList.add("is-calendar-target");
  calendarTargetCard = card;
  scheduleProgressiveBackground(progressiveRenderVersion);
  guardCalendarNavigation();
  card.scrollIntoView({
    behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth",
    block: "center",
  });

}

function createCalendarMonth(monthDate, rangeStart, rangeEnd, prices) {
  const card = document.createElement("article");
  card.className = "calendar-month-card";

  const title = document.createElement("h3");
  title.className = "calendar-month-title";
  title.textContent = capitalized(monthYear.format(monthDate));
  card.append(title);

  const weekdays = document.createElement("div");
  weekdays.className = "calendar-weekdays";
  weekdays.setAttribute("aria-hidden", "true");
  for (const label of calendarWeekdays) {
    const day = document.createElement("span");
    day.textContent = label;
    weekdays.append(day);
  }
  card.append(weekdays);

  const grid = document.createElement("div");
  grid.className = "calendar-grid";
  const year = monthDate.getUTCFullYear();
  const month = monthDate.getUTCMonth();
  const firstDay = new Date(Date.UTC(year, month, 1, 12));
  const leadingCells = (firstDay.getUTCDay() + 6) % 7;
  const daysInMonth = new Date(Date.UTC(year, month + 1, 0, 12)).getUTCDate();

  for (let index = 0; index < leadingCells; index += 1) {
    const empty = document.createElement("span");
    empty.className = "calendar-day is-empty";
    empty.setAttribute("aria-hidden", "true");
    grid.append(empty);
  }

  for (let day = 1; day <= daysInMonth; day += 1) {
    grid.append(createCalendarDay(new Date(Date.UTC(year, month, day, 12)), rangeStart, rangeEnd, prices));
  }

  const usedCells = leadingCells + daysInMonth;
  for (let index = usedCells; index < 42; index += 1) {
    const empty = document.createElement("span");
    empty.className = "calendar-day is-empty";
    empty.setAttribute("aria-hidden", "true");
    grid.append(empty);
  }

  card.append(grid);
  return card;
}

function datesInRange(rangeStart, rangeEnd) {
  const dates = [];
  const current = parseDateOnly(rangeStart);
  const end = parseDateOnly(rangeEnd);
  while (current <= end) {
    dates.push(toDateOnly(current));
    current.setUTCDate(current.getUTCDate() + 1);
  }
  return dates;
}

function createFareChartDay(isoDate, price, maxPrice) {
  const date = parseDateOnly(isoDate);
  const day = document.createElement(price ? "button" : "div");
  day.className = "fare-chart-day";

  const priceLabel = document.createElement("strong");
  priceLabel.className = "fare-chart-price";
  priceLabel.textContent = price
    ? `${calendarCurrency.format(price.total)}${price.total < price.regular ? "*" : ""}`
    : "—";

  const plot = document.createElement("span");
  plot.className = "fare-chart-plot";
  const bar = document.createElement("span");
  bar.className = "fare-chart-bar";

  if (price) {
    day.type = "button";
    day.classList.add("is-clickable");
    const proportionalHeight = maxPrice > 0 ? (price.total / maxPrice) * 95 : 12;
    bar.style.setProperty("--fare-bar-height", `${Math.max(12, proportionalHeight)}%`);
    day.setAttribute(
      "aria-label",
      `${formatDate(isoDate)}, ${selectedPriceCaption(price).toLowerCase()} ${currency.format(price.total)}. Pokaż lot.`
    );
    day.addEventListener("click", () => scrollToResult(price.resultId));
  } else {
    day.classList.add("has-no-price");
    day.setAttribute("role", "img");
    day.setAttribute("aria-label", `${formatDate(isoDate)}, brak połączeń`);
  }
  plot.append(bar);

  const dateLabel = document.createElement("span");
  dateLabel.className = "fare-chart-date";
  const weekday = document.createElement("span");
  weekday.textContent = chartWeekday.format(date).replace(".", "");
  const calendarDate = document.createElement("strong");
  calendarDate.textContent = chartDate.format(date).replace(".", "");
  dateLabel.append(weekday, calendarDate);

  day.append(priceLabel, plot, dateLabel);
  return day;
}

function renderFareChart(rangeStart, rangeEnd, prices) {
  const dates = datesInRange(rangeStart, rangeEnd);
  const available = dates.map(date => prices.get(date)).filter(Boolean);
  const totals = available.map(price => price.total);
  const maxPrice = totals.length ? Math.max(...totals) : 0;
  const chart = document.createDocumentFragment();

  for (const isoDate of dates) {
    chart.append(createFareChartDay(isoDate, prices.get(isoDate), maxPrice));
  }

  elements.farePriceChart.style.setProperty("--fare-chart-days", String(dates.length));
  elements.farePriceChart.replaceChildren(chart);
  elements.farePriceChart.setAttribute("aria-busy", "false");
}

function renderFareCalendar(results, filters) {
  const rangeStart = filters.dateFrom;
  const rangeEnd = filters.dateTo;
  const firstMonth = parseDateOnly(state.document.period_from);
  firstMonth.setUTCDate(1);
  const secondMonth = new Date(Date.UTC(
    firstMonth.getUTCFullYear(),
    firstMonth.getUTCMonth() + 1,
    1,
    12
  ));
  const prices = lowestPricesByDate(results, filters);
  const hasDiscountedPrices = [...prices.values()].some(price => price.total < price.regular);
  const hasResidentPrices = [...prices.values()].some(price => price.hasResident);
  const hasWizzClubPrices = [...prices.values()].some(price => price.hasWizzClub);

  elements.calendarLegendSelected.textContent = hasDiscountedPrices
    ? `* ${hasResidentPrices && hasWizzClubPrices
      ? "Cena po wybranych zniżkach"
      : hasResidentPrices
        ? "Cena dla rezydenta"
        : "Cena z Wizz Discount Club"}`
    : "Cena regularna";
  elements.calendarLegendRegular.hidden = !hasDiscountedPrices;

  elements.calendarMonths.replaceChildren(
    createCalendarMonth(firstMonth, rangeStart, rangeEnd, prices),
    createCalendarMonth(secondMonth, rangeStart, rangeEnd, prices)
  );
  renderFareChart(rangeStart, rangeEnd, prices);
  elements.calendarMonths.setAttribute("aria-busy", "false");
}

function setRangeProgress(input) {
  const min = Number(input.min);
  const max = Number(input.max);
  const progress = ((Number(input.value) - min) / (max - min)) * 100;
  input.style.setProperty("--progress", `${progress}%`);
}

function initializeFilters() {
  elements.direction.value = DEFAULT_DIRECTION;
  elements.dateFrom.min = state.document.period_from;
  elements.dateFrom.max = state.document.period_to;
  elements.dateFrom.value = state.document.period_from;
  elements.dateTo.min = state.document.period_from;
  elements.dateTo.max = state.document.period_to;
  elements.dateTo.value = state.document.period_to;

  const highestRegularPrice = Math.max(
    0,
    ...state.results.map(result => finitePrice(result.price_total_regular_pln) ?? 0)
  );
  const configuredLimit = Math.max(DEFAULT_MAX_PRICE, Math.ceil(highestRegularPrice / 100) * 100);
  elements.price.max = String(configuredLimit);
  elements.price.value = String(DEFAULT_MAX_PRICE);
  elements.priceMaxLabel.textContent = `${configuredLimit.toLocaleString("pl-PL")} zł`;
  updateAirportOptions();

  const transfers = [...new Set(state.results.map(result => result.transfer_airport).filter(Boolean))].sort();
  const firstCarriers = [...new Set(state.results.map(result => result.legs[0].carrier))].sort();
  const secondCarriers = [...new Set(
    state.results.filter(result => !isDirectConnection(result)).map(result => result.legs.at(-1).carrier)
  )].sort();
  addOptions(elements.transfer, transfers, optionLabel);
  addOptions(elements.firstCarrier, firstCarriers);
  addOptions(elements.secondCarrier, secondCarriers);
  updateRangeLabels();
}

function updateRangeLabels() {
  const directSelected = elements.transfer.value === "direct";
  if (directSelected) elements.secondCarrier.value = "all";
  elements.priceOutput.textContent = currency.format(Number(elements.price.value));
  elements.priceContext.textContent = elements.resident.checked && elements.wizzClub.checked
    ? "po wybranych zniżkach"
    : elements.resident.checked
      ? "dla rezydenta"
      : elements.wizzClub.checked
        ? "z Wizz Discount Club"
        : "cena regularna";
  elements.layoverOutput.textContent = `${elements.layover.value} godz.`;
  elements.layover.disabled = directSelected;
  elements.layover.closest(".layover-field").classList.toggle("is-disabled", directSelected);
  elements.secondCarrier.disabled = directSelected;
  elements.secondCarrier.closest(".second-carrier-field").classList.toggle("is-disabled", directSelected);
  updateChangedSelectStyles();
  setRangeProgress(elements.price);
  setRangeProgress(elements.layover);
  updateCalendarDirection();
}

function updateChangedSelectStyles() {
  [
    elements.origin,
    elements.destination,
    elements.firstCarrier,
    elements.secondCarrier,
    elements.transfer,
  ].forEach(select => {
    select.closest(".filter-field").classList.toggle(
      "is-filtered",
      select.value !== "all" && !select.disabled
    );
  });
}

function updateCalendarDirection() {
  const tenerifeToPoland = elements.direction.value === "tenerife_to_poland";
  const currentLabel = tenerifeToPoland ? "Teneryfa → Polska" : "Polska → Teneryfa";
  const nextLabel = tenerifeToPoland ? "Polska → Teneryfa" : "Teneryfa → Polska";
  elements.calendarDirectionLabel.textContent = currentLabel;
  elements.calendarDirectionSwap.setAttribute("aria-label", `Zmień kierunek na ${nextLabel}`);
}

function currentFilters() {
  return {
    resident: elements.resident.checked,
    wizzClub: elements.wizzClub.checked,
    maxPrice: Number(elements.price.value),
    dateFrom: elements.dateFrom.value,
    dateTo: elements.dateTo.value,
    origin: elements.origin.value,
    destination: elements.destination.value,
    transfer: elements.transfer.value,
    firstCarrier: elements.firstCarrier.value,
    secondCarrier: elements.secondCarrier.value,
    maxLayover: Number(elements.layover.value) * 60,
    sort: elements.sort.value,
    direction: elements.direction.value,
  };
}

function filteredResults(filters = currentFilters()) {
  const filtered = state.results.filter(result => {
    const departureDate = datePart(result.legs[0].departure_at);
    const direct = isDirectConnection(result);
    const firstCarrier = result.legs[0].carrier;
    const secondCarrier = result.legs.at(-1).carrier;
    const transferMatches =
      filters.transfer === "all" ||
      (filters.transfer === "direct" && direct) ||
      (!direct && result.transfer_airport === filters.transfer);
    return (
      selectedResultPricing(result, filters).total <= filters.maxPrice &&
      result.direction === filters.direction &&
      departureDate >= filters.dateFrom &&
      departureDate <= filters.dateTo &&
      (filters.origin === "all" || result.origin_airport === filters.origin) &&
      (filters.destination === "all" || result.destination_airport === filters.destination) &&
      transferMatches &&
      (filters.firstCarrier === "all" || firstCarrier === filters.firstCarrier) &&
      (filters.secondCarrier === "all" || (!direct && secondCarrier === filters.secondCarrier)) &&
      (direct || result.layover_minutes <= filters.maxLayover)
    );
  });

  const sorters = {
    price: (a, b) => selectedResultPricing(a, filters).total - selectedResultPricing(b, filters).total,
    regular: (a, b) => a.price_total_regular_pln - b.price_total_regular_pln,
    layover: (a, b) => (a.layover_minutes ?? 0) - (b.layover_minutes ?? 0),
    departure: (a, b) => a.legs[0].departure_at.localeCompare(b.legs[0].departure_at),
    journey: (a, b) => journeyDuration(a) - journeyDuration(b),
    departure_time: (a, b) => timePart(a.legs[0].departure_at).localeCompare(timePart(b.legs[0].departure_at)),
    arrival_time: (a, b) => timePart(a.legs.at(-1).arrival_at).localeCompare(timePart(b.legs.at(-1).arrival_at)),
    direct: (a, b) => Number(!isDirectConnection(a)) - Number(!isDirectConnection(b)),
  };

  return filtered.sort((a, b) => {
    const primary = sorters[filters.sort](a, b);
    return primary || a.legs[0].departure_at.localeCompare(b.legs[0].departure_at);
  });
}

function createJourney(result) {
  const first = result.legs[0];
  const last = result.legs.at(-1);
  const journey = document.createDocumentFragment();

  const origin = document.createElement("div");
  origin.className = "airport-stop";
  const originCode = document.createElement("span");
  originCode.className = "airport-code";
  originCode.textContent = first.departure_airport;
  origin.append(createJourneyTime(first.departure_at, first.departure_at), originCode);

  const firstLine = createLegLine(first);

  const destination = document.createElement("div");
  destination.className = "airport-stop destination";
  const destinationCode = document.createElement("span");
  destinationCode.className = "airport-code";
  destinationCode.textContent = last.arrival_airport;
  destination.append(createJourneyTime(last.arrival_at, first.departure_at), destinationCode);

  if (isDirectConnection(result)) {
    journey.append(origin, firstLine, destination);
    return journey;
  }

  const second = result.legs[1];

  const transfer = document.createElement("div");
  transfer.className = "transfer-stop";

  const routeSummary = document.createElement("div");
  routeSummary.className = "transfer-route-summary";

  const arrivalTime = createJourneyTime(
    first.arrival_at,
    first.departure_at,
    "transfer-time"
  );

  const firstSeparator = document.createElement("span");
  firstSeparator.className = "transfer-separator";
  firstSeparator.textContent = "·";

  const location = document.createElement("span");
  location.className = "transfer-location";

  const city = document.createElement("span");
  city.className = "transfer-city";
  city.textContent = airportCityLabel(result.transfer_airport);

  const airportCode = document.createElement("strong");
  airportCode.className = "transfer-airport-code";
  airportCode.textContent = result.transfer_airport;
  location.append(city, airportCode);

  const secondSeparator = firstSeparator.cloneNode(true);

  const departureTime = createJourneyTime(
    second.departure_at,
    first.departure_at,
    "transfer-time"
  );

  routeSummary.append(arrivalTime, firstSeparator, location, secondSeparator, departureTime);

  const layover = document.createElement("span");
  layover.className = "layover-badge";
  layover.textContent = `${formatDuration(result.layover_minutes)} przerwy`;
  transfer.append(routeSummary, layover);

  const secondLine = createLegLine(second);

  journey.append(origin, firstLine, transfer, secondLine, destination);
  return journey;
}

function createLegLine(leg) {
  const line = document.createElement("div");
  line.className = "leg-line";

  const logoPath = carrierLogos[leg.carrier];
  if (logoPath) {
    const logo = document.createElement("img");
    logo.className = "carrier-logo";
    logo.src = logoPath;
    logo.alt = `Logo ${leg.carrier}`;
    line.append(logo);
  } else {
    const fallback = document.createElement("span");
    fallback.className = "carrier-name";
    fallback.textContent = leg.carrier;
    line.append(fallback);
  }

  const track = document.createElement("span");
  track.className = "leg-track";
  track.setAttribute("aria-hidden", "true");

  const description = document.createElement("span");
  description.className = "leg-description";
  description.textContent = `${leg.carrier} · ${leg.flight_number}`;
  line.append(track, description);
  return line;
}

function priceDetails(result, filters) {
  const first = result.legs[0];
  const last = result.legs.at(-1);
  const resultPricing = selectedResultPricing(result, filters);
  const legRows = result.legs.map(leg => {
    const pricing = selectedLegPrice(leg, filters);
    const discounted = pricing.value < pricing.regular;
    const price = discounted
      ? `<span class="regular-inline">(Cena regularna: ~${currency.format(pricing.regular)})</span> ~${currency.format(pricing.value)}`
      : `~${currency.format(pricing.value)}`;
    return `
      <div class="price-row">
        <span>${leg.carrier} ${leg.flight_number}</span>
        <strong>${price}</strong>
      </div>
    `;
  }).join("");
  const totalPrice = `~${currency.format(resultPricing.total)}`;

  return `
    ${legRows}
    <div class="price-row trip-summary-row">
      <span class="trip-timing">
        <span>Wylot: ${formatTimestampWithWeekday(first.departure_at)}</span>
        <span>Przylot: ${formatTimestampWithWeekday(last.arrival_at)}</span>
      </span>
      <strong class="total-price-detail"><span>Razem:</span><span>${totalPrice}</span></strong>
    </div>
  `;
}

function purchaseLegPriceRows(leg, filters) {
  const pricing = selectedLegPrice(leg, filters);
  if (pricing.value < pricing.regular) {
    const selectedLabel = pricing.kind === "resident"
      ? "Cena orientacyjna dla rezydenta"
      : "Cena z Wizz Discount Club";
    return [
      {
        label: `${selectedLabel}: ~${currency.format(pricing.value)}`,
        regular: false,
      },
      {
        label: `Cena regularna: ~${currency.format(pricing.regular)}`,
        regular: true,
      },
    ];
  }

  return [{
    label: `Cena orientacyjna: ~${currency.format(pricing.value)}`,
    regular: false,
  }];
}

function bookingUrlForFilters(leg, filters) {
  const fallback = carrierPurchaseUrls[leg.carrier] || "#";
  const rawUrl = leg.booking_url || fallback;
  if (!leg.booking_url || !["Vueling", "Air Europa"].includes(leg.carrier)) return rawUrl;

  try {
    const url = new URL(rawUrl, window.location.href);
    const useResidentDiscount = filters.resident && leg.resident_discount_eligible;
    if (leg.carrier === "Vueling") {
      url.searchParams.set("dt", useResidentDiscount ? "1" : "0");
    } else if (useResidentDiscount) {
      url.searchParams.set("residentType", "SPANISH_RESIDENT_RC");
    } else {
      url.searchParams.delete("residentType");
    }
    return url.toString();
  } catch (error) {
    console.warn(`Nie udało się dopasować linku ${leg.carrier} do filtra rezydenta`, error);
    return fallback;
  }
}

function createPurchaseStep(leg, index, filters) {
  const step = document.createElement("article");
  step.className = "purchase-step";

  const heading = document.createElement("div");
  heading.className = "purchase-step-heading";

  const number = document.createElement("span");
  number.className = "purchase-step-number";
  number.textContent = String(index + 1);

  const carrier = document.createElement("div");
  carrier.className = "purchase-step-carrier";
  const logoPath = carrierLogos[leg.carrier];
  if (logoPath) {
    const logo = document.createElement("img");
    logo.src = logoPath;
    logo.alt = `Logo ${leg.carrier}`;
    carrier.append(logo);
  }
  const carrierName = document.createElement("strong");
  carrierName.textContent = leg.carrier;
  carrier.append(carrierName);
  heading.append(number, carrier);

  const route = document.createElement("strong");
  route.className = "purchase-step-route";
  route.textContent = `${leg.departure_airport} ${timePart(leg.departure_at)} → ${leg.arrival_airport} ${timePart(leg.arrival_at)}`;

  const timing = document.createElement("div");
  timing.className = "purchase-step-timing";

  const departureTiming = document.createElement("span");
  departureTiming.textContent = `Wylot: ${formatPurchaseTimestamp(leg.departure_at)}`;

  const arrivalTiming = document.createElement("span");
  arrivalTiming.textContent = `Przylot: ${formatPurchaseTimestamp(leg.arrival_at)}`;

  timing.append(departureTiming, arrivalTiming);

  const flightNumber = document.createElement("span");
  flightNumber.className = "purchase-step-flight";
  flightNumber.textContent = `Numer lotu: ${leg.flight_number}`;

  const price = document.createElement("div");
  price.className = "purchase-step-price";
  purchaseLegPriceRows(leg, filters).forEach(row => {
    const priceRow = document.createElement("span");
    priceRow.textContent = row.label;
    if (row.regular) priceRow.className = "purchase-step-price-regular";
    price.append(priceRow);
  });

  const actions = document.createElement("div");
  actions.className = "purchase-step-actions";

  const openLink = document.createElement("a");
  openLink.className = "purchase-open-link";
  openLink.href = bookingUrlForFilters(leg, filters);
  openLink.target = "_blank";
  openLink.rel = "noopener noreferrer";
  openLink.textContent = `Otwórz ${leg.carrier}`;
  if (!leg.booking_url && !carrierPurchaseUrls[leg.carrier]) {
    openLink.hidden = true;
  }

  const kiwiLink = document.createElement("a");
  kiwiLink.className = "purchase-kiwi-link";
  kiwiLink.href = "https://www.kiwi.com/pl/";
  kiwiLink.target = "_blank";
  kiwiLink.rel = "noopener noreferrer";
  kiwiLink.textContent = "Sprawdź na Kiwi.com";

  actions.append(openLink, kiwiLink);
  step.append(heading, route, timing, flightNumber, price, actions);
  return step;
}

function showPurchaseDialog(result, filters) {
  const separateBookings = result.legs.length > 1;
  const intro = document.createElement("p");
  intro.className = "purchase-dialog-intro";
  intro.textContent = separateBookings
    ? `To połączenie składa się z ${result.legs.length} osobnych rezerwacji. Kup każdy odcinek bezpośrednio u przewoźnika.`
    : "Ten lot kupisz jako jedną rezerwację bezpośrednio u przewoźnika.";

  const steps = document.createElement("div");
  steps.className = "purchase-steps";
  result.legs.forEach((leg, index) => steps.append(createPurchaseStep(leg, index, filters)));

  const note = document.createElement("p");
  note.className = "purchase-dialog-note";
  note.textContent = separateBookings
    ? "Przed zapłatą upewnij się, że wszystkie loty są nadal dostępne. Ceny mogą się zmienić na stronach linii."
    : "Przed zapłatą sprawdź aktualną cenę i dostępność na stronie linii.";

  elements.purchaseDialogContent.replaceChildren(intro, note, steps);
  elements.purchaseDialog.showModal();
}

function createResultCard(result, filters) {
  const fragment = elements.template.content.cloneNode(true);
  const card = fragment.querySelector(".flight-card");
  const direct = isDirectConnection(result);
  const pricing = selectedResultPricing(result, filters);
  const discounted = pricing.total < pricing.regular;

  card.dataset.resultId = result.id;
  fragment.querySelector(".date-label").textContent = formatDate(result.legs[0].departure_at);
  fragment.querySelector(".connection-label").textContent = direct ? "Bez przesiadek" : "1 przesiadka";
  fragment.querySelector(".total-duration").textContent = `Łącznie: ${formatDuration(journeyDuration(result))}`;
  const journey = fragment.querySelector(".journey");
  journey.classList.toggle("direct", direct);
  journey.append(createJourney(result));
  fragment.querySelector(".resident-caption").textContent = selectedPriceCaption(pricing);
  fragment.querySelector(".resident-price").textContent = `~${currency.format(pricing.total)}`;
  const regularPrice = fragment.querySelector(".regular-price");
  regularPrice.textContent = discounted
    ? `Cena regularna: ~${currency.format(pricing.regular)}`
    : "";
  regularPrice.hidden = !discounted;
  fragment.querySelector(".purchase-ticket-count").textContent = direct
    ? "Potrzebny 1 bilet"
    : "Potrzebne dwa osobne bilety";
  fragment.querySelector(".purchase-button").addEventListener("click", () => showPurchaseDialog(result, filters));
  const shareButton = fragment.querySelector(".share-flight-button");
  shareButton.addEventListener("click", () => copyFlightLink(result, filters, shareButton));

  const details = fragment.querySelector(".price-details");
  details.innerHTML = priceDetails(result, filters);
  const toggle = fragment.querySelector(".details-toggle");
  toggle.addEventListener("click", () => {
    const expanded = toggle.getAttribute("aria-expanded") === "true";
    if (!expanded && card !== calendarTargetCard) clearCalendarTarget();
    setCardDetailsExpanded(card, !expanded);
  });

  return fragment;
}

function renderActiveFilters(filters = currentFilters()) {
  const chips = [{ label: `Do ${currency.format(filters.maxPrice)}` }];
  chips.push({
    label: filters.direction === "poland_to_tenerife" ? "Polska → Teneryfa" : "Teneryfa → Polska",
  });
  if (filters.resident) {
    chips.push({ label: "Rezydent Wysp Kanaryjskich", removable: "resident" });
  }
  if (filters.wizzClub) {
    chips.push({ label: "WIZZ Discount Club", removable: "wizzClub" });
  }
  if (filters.origin !== "all") {
    chips.push({ label: `Wylot: ${filters.origin}`, removable: "origin" });
  }
  if (filters.destination !== "all") {
    chips.push({ label: `Przylot: ${filters.destination}`, removable: "destination" });
  }
  if (filters.transfer === "direct") {
    chips.push({ label: "Bez przesiadek", removable: "transfer" });
  }
  if (filters.transfer !== "all" && filters.transfer !== "direct") {
    chips.push({ label: `Przez: ${filters.transfer}`, removable: "transfer" });
  }
  if (filters.firstCarrier !== "all") {
    chips.push({ label: `Pierwsza linia: ${filters.firstCarrier}`, removable: "firstCarrier" });
  }
  if (filters.secondCarrier !== "all") {
    chips.push({ label: `Druga linia: ${filters.secondCarrier}`, removable: "secondCarrier" });
  }
  if (filters.transfer !== "direct" && filters.maxLayover < 24 * 60) {
    chips.push({ label: `Przesiadka do ${formatDuration(filters.maxLayover)}` });
  }
  if (filters.dateFrom !== state.document.period_from || filters.dateTo !== state.document.period_to) {
    chips.push({
      label: `${filters.dateFrom} – ${filters.dateTo}`,
      removable: "dateRange",
    });
  }
  for (const container of [elements.calendarActiveFilters, elements.activeFilters]) {
    container.replaceChildren(...chips.map(({ label, removable }) => {
      const chip = document.createElement(removable ? "button" : "span");
      chip.className = "filter-chip";
      if (!removable) {
        chip.textContent = label;
        return chip;
      }

      chip.type = "button";
      chip.classList.add("is-removable");
      chip.dataset.filterKey = removable;
      chip.setAttribute("aria-label", `Wyczyść filtr: ${label}`);
      const chipLabel = document.createElement("span");
      chipLabel.textContent = label;
      const removeIcon = document.createElement("span");
      removeIcon.className = "filter-chip-remove";
      removeIcon.setAttribute("aria-hidden", "true");
      removeIcon.textContent = "×";
      chip.append(chipLabel, removeIcon);
      chip.addEventListener("click", () => {
        clearActiveFilter(removable);
      });
      return chip;
    }));
  }
}

function clearActiveFilter(filterKey) {
  if (filterKey === "resident") {
    elements.resident.checked = false;
    elements.resident.dispatchEvent(new Event("input", { bubbles: true }));
    return;
  }
  if (filterKey === "wizzClub") {
    elements.wizzClub.checked = false;
    elements.wizzClub.dispatchEvent(new Event("input", { bubbles: true }));
    return;
  }
  if (filterKey === "dateRange") {
    elements.dateFrom.value = state.document.period_from;
    elements.dateTo.value = state.document.period_to;
    elements.dateFrom.dispatchEvent(new Event("input", { bubbles: true }));
    return;
  }

  const selectByFilter = {
    origin: elements.origin,
    destination: elements.destination,
    transfer: elements.transfer,
    firstCarrier: elements.firstCarrier,
    secondCarrier: elements.secondCarrier,
  };
  const select = selectByFilter[filterKey];
  if (!select) return;
  select.value = "all";
  select.dispatchEvent(new Event("input", { bubbles: true }));
}

function fareCalendarRenderKey(filters) {
  return JSON.stringify([
    filters.resident,
    filters.wizzClub,
    filters.maxPrice,
    filters.dateFrom,
    filters.dateTo,
    filters.origin,
    filters.destination,
    filters.transfer,
    filters.firstCarrier,
    filters.secondCarrier,
    filters.maxLayover,
    filters.direction,
  ]);
}

function resultCardsRenderKey(filters) {
  return JSON.stringify([
    filters.resident,
    filters.wizzClub,
    filters.maxPrice,
    filters.dateFrom,
    filters.dateTo,
    filters.origin,
    filters.destination,
    filters.transfer,
    filters.firstCarrier,
    filters.secondCarrier,
    filters.maxLayover,
    filters.sort,
    filters.direction,
  ]);
}

function resultCardNodeKey(result, filters) {
  return JSON.stringify([result.id, filters.resident, filters.wizzClub]);
}

function resultCardPricingMode(filters) {
  return `${filters.resident ? 1 : 0}:${filters.wizzClub ? 1 : 0}`;
}

function rememberResultCardNode(cacheKey, card) {
  resultCardNodeCache.delete(cacheKey);
  resultCardNodeCache.set(cacheKey, card);
  while (resultCardNodeCache.size > RESULT_CARD_NODE_CACHE_LIMIT) {
    resultCardNodeCache.delete(resultCardNodeCache.keys().next().value);
  }
}

function cachedResultCardNode(result, filters) {
  const cacheKey = resultCardNodeKey(result, filters);
  const card = resultCardNodeCache.get(cacheKey);
  if (!card || card.dataset.resultId !== result.id) {
    if (card) resultCardNodeCache.delete(cacheKey);
    return null;
  }

  rememberResultCardNode(cacheKey, card);
  return card;
}

function cacheCurrentResultCards() {
  if (!activeResultCacheKey || !progressiveResults.length) return;

  const cardsByIndex = new Map(progressivePreparedResultCards);
  for (const card of elements.list.querySelectorAll(".flight-card")) {
    const index = Number(card.dataset.resultIndex);
    if (
      !Number.isInteger(index) ||
      progressiveResults[index]?.id !== card.dataset.resultId
    ) continue;
    cardsByIndex.set(index, card);
  }
  if (!cardsByIndex.size) return;

  const loadedIndexes = new Set(
    [...progressiveLoadedResultIndexes].filter(index => cardsByIndex.has(index))
  );
  const resultIds = progressiveResults.map(result => result.id);

  resultViewCache.delete(activeResultCacheKey);
  resultViewCache.set(activeResultCacheKey, {
    resultIds,
    cardsByIndex,
    loadedIndexes,
  });
  while (resultViewCache.size > RESULT_VIEW_CACHE_LIMIT) {
    resultViewCache.delete(resultViewCache.keys().next().value);
  }
}

function cachedResultView(cacheKey, results) {
  const cached = resultViewCache.get(cacheKey);
  const valid = cached &&
    cached.resultIds.length === results.length &&
    cached.resultIds.every((resultId, index) => resultId === results[index].id) &&
    [...cached.cardsByIndex].every(([index, card]) =>
      results[index]?.id === card.dataset.resultId
    );

  if (!valid) {
    if (cached) resultViewCache.delete(cacheKey);
    return null;
  }

  resultViewCache.delete(cacheKey);
  resultViewCache.set(cacheKey, cached);
  return cached;
}

function cancelProgressiveIdleWork() {
  if (progressiveIdleHandle === null) return;
  if (progressiveIdleUsesTimeout) {
    window.clearTimeout(progressiveIdleHandle);
  } else {
    window.cancelIdleCallback(progressiveIdleHandle);
  }
  progressiveIdleHandle = null;
  progressiveIdleUsesTimeout = false;
}

function stopProgressiveRendering() {
  progressiveRenderVersion += 1;
  cancelProgressiveIdleWork();
  clearCalendarNavigationGuard();
  progressiveResults = [];
  progressiveFilters = null;
  progressiveResultCount = 0;
  progressiveLoadedResultIndexes = new Set();
  progressivePreparedResultCards = new Map();
  progressiveCommitPending = false;
  activeResultCacheKey = null;
  calendarTargetCard = null;
}

function visibleResultAnchor() {
  const cards = [...elements.list.querySelectorAll(".flight-card")];
  const targetBounds = calendarTargetCard?.isConnected
    ? calendarTargetCard.getBoundingClientRect()
    : null;
  if (targetBounds && targetBounds.bottom > 0 && targetBounds.top < window.innerHeight) {
    return { card: calendarTargetCard, top: targetBounds.top };
  }

  const card = cards.find(item => item.getBoundingClientRect().bottom > 0);
  return card ? { card, top: card.getBoundingClientRect().top } : null;
}

function restoreResultAnchor(anchor) {
  if (!anchor?.card?.isConnected) return;
  const shift = anchor.card.getBoundingClientRect().top - anchor.top;
  if (Math.abs(shift) < 1) return;

  const previousScrollBehavior = document.documentElement.style.scrollBehavior;
  document.documentElement.style.scrollBehavior = "auto";
  window.scrollBy({ top: shift, left: 0, behavior: "auto" });
  document.documentElement.style.scrollBehavior = previousScrollBehavior;
}

function createProgressiveResultCard(index) {
  if (!progressiveResults[index] || !progressiveFilters) return null;
  const result = progressiveResults[index];
  let card = cachedResultCardNode(result, progressiveFilters);
  if (!card) {
    const fragment = createResultCard(result, progressiveFilters);
    card = fragment.querySelector(".flight-card");
    rememberResultCardNode(resultCardNodeKey(result, progressiveFilters), card);
  }
  card.dataset.resultIndex = String(index);
  card.dataset.pricingMode = resultCardPricingMode(progressiveFilters);
  return card;
}

function renderResultAtIndex(index) {
  if (progressiveLoadedResultIndexes.has(index)) return;

  const card = progressivePreparedResultCards.get(index)
    || createProgressiveResultCard(index);
  if (!card) return;

  progressivePreparedResultCards.delete(index);
  const nextCard = [...elements.list.querySelectorAll(".flight-card")]
    .find(item => Number(item.dataset.resultIndex) > index);
  elements.list.insertBefore(card, nextCard || null);
  progressiveLoadedResultIndexes.add(index);
}

function appendInitialResults(expectedVersion = progressiveRenderVersion) {
  if (
    expectedVersion !== progressiveRenderVersion ||
    !progressiveFilters
  ) return;

  while (
    progressiveResultCount < progressiveResults.length &&
    progressiveLoadedResultIndexes.size < RESULT_BATCH_SIZE
  ) {
    const index = progressiveResultCount;
    progressiveResultCount += 1;
    if (progressiveLoadedResultIndexes.has(index)) continue;
    renderResultAtIndex(index);
  }
}

function commitPreparedResults(expectedVersion) {
  if (
    expectedVersion !== progressiveRenderVersion ||
    !progressiveFilters ||
    progressiveResultCount < progressiveResults.length
  ) return;
  if (calendarNavigationPending) {
    progressiveCommitPending = true;
    return;
  }

  const anchor = visibleResultAnchor();
  const renderedCards = new Map(
    [...elements.list.querySelectorAll(".flight-card")]
      .map(card => [Number(card.dataset.resultIndex), card])
  );
  const completeList = document.createDocumentFragment();

  for (let index = 0; index < progressiveResults.length; index += 1) {
    const card = renderedCards.get(index) || progressivePreparedResultCards.get(index);
    if (!card) return;
    completeList.append(card);
  }

  elements.list.replaceChildren(completeList);
  progressiveLoadedResultIndexes = new Set(progressiveResults.map((_, index) => index));
  progressivePreparedResultCards.clear();
  progressiveCommitPending = false;
  restoreResultAnchor(anchor);
  cacheCurrentResultCards();
  updateResultLoadStatus();
}

function prepareNextResultBatch(
  expectedVersion = progressiveRenderVersion,
  batchSize = BACKGROUND_RESULT_BATCH_SIZE,
  deadline = null
) {
  if (
    expectedVersion !== progressiveRenderVersion ||
    !progressiveFilters
  ) return;

  let prepared = 0;
  while (progressiveResultCount < progressiveResults.length && prepared < batchSize) {
    if (
      prepared > 0 &&
      deadline &&
      !deadline.didTimeout &&
      deadline.timeRemaining() < 4
    ) break;

    const index = progressiveResultCount;
    progressiveResultCount += 1;
    if (
      progressiveLoadedResultIndexes.has(index) ||
      progressivePreparedResultCards.has(index)
    ) continue;

    const card = createProgressiveResultCard(index);
    if (card) {
      progressivePreparedResultCards.set(index, card);
      prepared += 1;
    }
  }

  updateResultPreparationProgress();

  if (progressiveResultCount >= progressiveResults.length) {
    cancelProgressiveIdleWork();
    commitPreparedResults(expectedVersion);
  }
}

function scheduleProgressiveBackground(expectedVersion, delayMs = 0) {
  if (
    progressiveIdleHandle !== null ||
    expectedVersion !== progressiveRenderVersion ||
    progressiveResultCount >= progressiveResults.length
  ) return;

  if (delayMs > 0) {
    progressiveIdleUsesTimeout = true;
    progressiveIdleHandle = window.setTimeout(() => {
      progressiveIdleHandle = null;
      progressiveIdleUsesTimeout = false;
      scheduleProgressiveBackground(expectedVersion);
    }, delayMs);
    return;
  }

  const renderWhenIdle = deadline => {
    progressiveIdleHandle = null;
    progressiveIdleUsesTimeout = false;
    if (expectedVersion !== progressiveRenderVersion) return;
    if (deadline && !deadline.didTimeout && deadline.timeRemaining() < 5) {
      scheduleProgressiveBackground(expectedVersion);
      return;
    }
    prepareNextResultBatch(expectedVersion, BACKGROUND_RESULT_BATCH_SIZE, deadline);
    scheduleProgressiveBackground(expectedVersion);
  };

  if ("requestIdleCallback" in window) {
    progressiveIdleUsesTimeout = false;
    progressiveIdleHandle = window.requestIdleCallback(renderWhenIdle, { timeout: 1000 });
  } else {
    progressiveIdleUsesTimeout = true;
    progressiveIdleHandle = window.setTimeout(
      () => renderWhenIdle(null),
      BACKGROUND_RESULT_FALLBACK_DELAY_MS
    );
  }
}

function restoreCachedResultView(cached, expectedVersion) {
  const visibleCards = document.createDocumentFragment();
  const loadedIndexes = new Set();
  const preparedCards = new Map();
  const sortedCards = [...cached.cardsByIndex].sort(([first], [second]) => first - second);

  for (const [index, card] of sortedCards) {
    card.dataset.resultIndex = String(index);
    if (cached.loadedIndexes.has(index)) {
      visibleCards.append(card);
      loadedIndexes.add(index);
    } else {
      preparedCards.set(index, card);
    }
  }

  elements.list.replaceChildren(visibleCards);
  progressiveLoadedResultIndexes = loadedIndexes;
  progressivePreparedResultCards = preparedCards;
  progressiveResultCount = 0;
  while (
    progressiveResultCount < progressiveResults.length &&
    (progressiveLoadedResultIndexes.has(progressiveResultCount) ||
      progressivePreparedResultCards.has(progressiveResultCount))
  ) {
    progressiveResultCount += 1;
  }
  calendarTargetCard = elements.list.querySelector(".is-calendar-target");

  if (progressiveResultCount >= progressiveResults.length) {
    commitPreparedResults(expectedVersion);
  } else {
    updateResultLoadStatus();
  }
}

function restoreReusableVisibleResults(expectedVersion, preserveAnchor = true) {
  const previousCards = [...elements.list.querySelectorAll(".flight-card")];
  if (!previousCards.length || !progressiveFilters) return false;

  const resultIndexes = new Map(
    progressiveResults.map((result, index) => [result.id, index])
  );
  const pricingMode = resultCardPricingMode(progressiveFilters);
  const reusableCards = [];

  for (const card of previousCards) {
    const index = resultIndexes.get(card.dataset.resultId);
    if (index === undefined || card.dataset.pricingMode !== pricingMode) continue;
    card.dataset.resultIndex = String(index);
    reusableCards.push([index, card]);
  }

  if (!reusableCards.length) return false;

  const anchor = preserveAnchor ? visibleResultAnchor() : null;
  const visibleCards = document.createDocumentFragment();
  reusableCards
    .sort(([first], [second]) => first - second)
    .forEach(([, card]) => visibleCards.append(card));

  elements.list.replaceChildren(visibleCards);
  progressiveLoadedResultIndexes = new Set(reusableCards.map(([index]) => index));
  progressivePreparedResultCards = new Map();
  progressiveResultCount = 0;
  while (
    progressiveResultCount < progressiveResults.length &&
    progressiveLoadedResultIndexes.has(progressiveResultCount)
  ) {
    progressiveResultCount += 1;
  }

  appendInitialResults(expectedVersion);
  calendarTargetCard = elements.list.querySelector(".is-calendar-target");
  restoreResultAnchor(anchor);
  updateResultLoadStatus();
  return true;
}

function renderResultCards(results, filters, preserveAnchor = true) {
  cacheCurrentResultCards();
  stopProgressiveRendering();
  const expectedVersion = progressiveRenderVersion;
  const cacheKey = resultCardsRenderKey(filters);
  progressiveResults = results;
  progressiveFilters = filters;
  activeResultCacheKey = cacheKey;

  const cachedView = cachedResultView(cacheKey, results);
  if (cachedView) {
    restoreCachedResultView(cachedView, expectedVersion);
    scheduleProgressiveBackground(expectedVersion, BACKGROUND_RESULT_START_DELAY_MS);
    return;
  }

  if (restoreReusableVisibleResults(expectedVersion, preserveAnchor)) {
    if (progressiveResultCount >= progressiveResults.length) {
      commitPreparedResults(expectedVersion);
    } else {
      scheduleProgressiveBackground(expectedVersion, BACKGROUND_RESULT_START_DELAY_MS);
    }
    return;
  }

  elements.list.replaceChildren();
  appendInitialResults(expectedVersion);
  calendarTargetCard = elements.list.querySelector(".is-calendar-target");
  updateResultLoadStatus();
  scheduleProgressiveBackground(expectedVersion, BACKGROUND_RESULT_START_DELAY_MS);
}

function ensureResultRendered(resultId) {
  const targetIndex = progressiveResults.findIndex(result => result.id === resultId);
  if (targetIndex < 0) return;
  renderResultAtIndex(targetIndex);
  updateResultLoadStatus();
}

function renderResults({ preserveAnchor = true } = {}) {
  window.clearTimeout(filterRenderTimer);
  filterRenderTimer = undefined;
  updateRangeLabels();
  const filters = currentFilters();
  const results = filteredResults(filters);
  const nextCalendarRenderKey = fareCalendarRenderKey(filters);
  if (nextCalendarRenderKey !== calendarRenderKey) {
    renderFareCalendar(results, filters);
    calendarRenderKey = nextCalendarRenderKey;
  }
  elements.count.textContent = results.length;
  elements.countNoun.textContent = pluralizeResults(results.length);
  renderActiveFilters(filters);
  elements.list.setAttribute("aria-busy", "false");

  if (!results.length) {
    stopProgressiveRendering();
    setResultLoadStatus("Brak połączeń dla wybranych filtrów.", "empty");
    const directSelected = filters.transfer === "direct";
    elements.list.innerHTML = `
      <div class="empty-state">
        <strong>Brak lotów dla tych filtrów</strong>
        <p>${directSelected
          ? "W aktualnych danych nie ma lotów bezpośrednich."
          : "Podnieś limit ceny albo wybierz dłuższą przesiadkę."}</p>
      </div>
    `;
    return;
  }

  renderResultCards(results, filters, preserveAnchor);
}

function configureSharedResultFilters(result, params) {
  elements.resident.checked = params.get("resident") !== "0";
  elements.wizzClub.checked = params.get("wizz") === "1";
  elements.price.value = elements.price.max;
  elements.direction.value = result.direction;
  updateAirportOptions();
  elements.dateFrom.value = state.document.period_from;
  elements.dateTo.value = state.document.period_to;
  elements.origin.value = "all";
  elements.destination.value = "all";
  elements.transfer.value = "all";
  elements.firstCarrier.value = "all";
  elements.secondCarrier.value = "all";
  elements.layover.value = elements.layover.max;
}

function sharedResultFromUrl() {
  const params = new URLSearchParams(window.location.search);
  const resultId = params.get("flight");
  if (!resultId) return null;
  const result = state.results.find(candidate => candidate.id === resultId);
  if (!result) {
    showShareStatus("Ten lot nie jest już dostępny w aktualnej bazie.", {
      error: true,
      persistent: true,
    });
    return null;
  }
  configureSharedResultFilters(result, params);
  return result;
}

function scheduleRenderResults({ preserveAnchor = true } = {}) {
  updateRangeLabels();
  window.clearTimeout(filterRenderTimer);
  cacheCurrentResultCards();
  stopProgressiveRendering();
  elements.list.setAttribute("aria-busy", "true");
  setResultLoadStatus("Aktualizuję listę połączeń…");
  filterRenderTimer = window.setTimeout(
    () => renderResults({ preserveAnchor }),
    FILTER_RENDER_DELAY_MS
  );
}

function resetFilters() {
  window.clearTimeout(filterRenderTimer);
  elements.resident.checked = true;
  elements.wizzClub.checked = false;
  elements.price.value = String(DEFAULT_MAX_PRICE);
  elements.direction.value = DEFAULT_DIRECTION;
  updateAirportOptions();
  elements.dateFrom.value = state.document.period_from;
  elements.dateTo.value = state.document.period_to;
  elements.origin.value = "all";
  elements.destination.value = "all";
  elements.transfer.value = "all";
  elements.firstCarrier.value = "all";
  elements.secondCarrier.value = "all";
  elements.layover.value = 6;
  elements.sort.value = "departure";
  renderResults();
}

function bindEvents() {
  const filters = [
    elements.resident,
    elements.wizzClub,
    elements.price,
    elements.dateFrom,
    elements.dateTo,
    elements.origin,
    elements.destination,
    elements.transfer,
    elements.firstCarrier,
    elements.secondCarrier,
    elements.layover,
    elements.sort,
  ];
  const pauseBackgroundWork = () => cancelProgressiveIdleWork();
  const resumeBackgroundWork = () => {
    scheduleProgressiveBackground(
      progressiveRenderVersion,
      BACKGROUND_RESULT_START_DELAY_MS
    );
  };

  [...filters, elements.direction].forEach(element => {
    element.addEventListener("pointerdown", pauseBackgroundWork);
    element.addEventListener("keydown", pauseBackgroundWork);
    element.addEventListener("focus", pauseBackgroundWork);
    element.addEventListener("blur", resumeBackgroundWork);
  });
  filters
    .filter(element => element !== elements.sort)
    .forEach(element => element.addEventListener("input", scheduleRenderResults));
  elements.sort.addEventListener("input", () => {
    scheduleRenderResults({ preserveAnchor: false });
  });
  elements.direction.addEventListener("input", () => {
    updateAirportOptions();
    scheduleRenderResults();
  });
  elements.calendarDirectionSwap.addEventListener("click", () => {
    elements.direction.value = elements.direction.value === "tenerife_to_poland"
      ? "poland_to_tenerife"
      : "tenerife_to_poland";
    elements.direction.dispatchEvent(new Event("input", { bubbles: true }));
  });
  elements.reset.addEventListener("click", resetFilters);
  elements.searchInfoButton.addEventListener("click", () => {
    elements.searchInfoDialog.showModal();
  });
  elements.searchInfoDialog.querySelector("[data-close-search-info]").addEventListener("click", () => {
    elements.searchInfoDialog.close();
  });
  elements.searchInfoDialog.addEventListener("click", event => {
    if (event.target === elements.searchInfoDialog) elements.searchInfoDialog.close();
  });
  elements.purchaseDialog.querySelector("[data-close-purchase]").addEventListener("click", () => {
    elements.purchaseDialog.close();
  });
  elements.purchaseDialog.addEventListener("click", event => {
    if (event.target === elements.purchaseDialog) elements.purchaseDialog.close();
  });
}

async function loadFlights() {
  try {
    const responses = await Promise.all(DATA_SOURCES.map(async source => ({
      source,
      response: await fetch(source.url, { cache: "no-store" }),
    })));
    const failed = responses.find(({ source, response }) => !source.optional && !response.ok);
    if (failed) throw new Error(`HTTP ${failed.response.status}: ${failed.source.url}`);
    const available = responses.filter(({ response }) => response.ok);
    const documents = await Promise.all(available.map(({ response }) => response.json()));
    state.document = {
      generated_at: documents.map(document => document.generated_at).sort().at(-1),
      period_from: documents.map(document => document.period_from).sort().at(-1),
      period_to: documents.map(document => document.period_to).sort()[0],
    };
    state.results = documents.flatMap(document => document.results || []);

    const generated = new Date(state.document.generated_at);
    elements.updatedAt.textContent = `Aktualizacja ${shortDate.format(generated)}`;
    initializeFilters();
    bindEvents();
    const sharedResult = sharedResultFromUrl();
    renderResults({ preserveAnchor: false });
    if (sharedResult) {
      window.requestAnimationFrame(() => scrollToResult(sharedResult.id));
    }
  } catch (error) {
    console.error("Nie udało się wczytać danych lotów", error);
    elements.updatedAt.textContent = "Brak danych";
    elements.calendarMonths.setAttribute("aria-busy", "false");
    elements.calendarMonths.innerHTML = `<div class="calendar-loading">Nie udało się wczytać kalendarza cen.</div>`;
    elements.farePriceChart.setAttribute("aria-busy", "false");
    elements.farePriceChart.innerHTML = `<div class="fare-chart-loading">Nie udało się wczytać wykresu cen.</div>`;
    elements.list.setAttribute("aria-busy", "false");
    setResultLoadStatus("Nie udało się wczytać połączeń.", "empty");
    hideResultPreparationProgress();
    elements.list.innerHTML = `
      <div class="error-state">
        <strong>Nie udało się wczytać lotów</strong>
        <p>Sprawdź, czy pliki danych kroków 1–5 są dostępne.</p>
      </div>
    `;
  }
}

loadFlights();
