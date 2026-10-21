const DATA_SOURCES = [
  { url: "data/step1-results.json" },
  { url: "data/step1b-results.json", optional: true },
  { url: "data/step1c-results.json", optional: true },
  { url: "data/step1d-results.json", optional: true },
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
  sort: document.querySelector("#sort-results"),
  reset: document.querySelector("#reset-filters"),
  calendarMonths: document.querySelector("#calendar-months"),
  calendarLegendSelected: document.querySelector(".calendar-legend-resident"),
  calendarLegendRegular: document.querySelector(".calendar-legend-regular"),
  activeFilters: document.querySelector("#active-filters"),
  count: document.querySelector("#results-count"),
  countNoun: document.querySelector("#results-noun"),
  list: document.querySelector("#results-list"),
  template: document.querySelector("#result-template"),
  purchaseDialog: document.querySelector("#purchase-dialog"),
  purchaseDialogContent: document.querySelector("#purchase-dialog-content"),
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

const carrierLogos = {
  Binter: "assets/logos/binter.svg",
  "Wizz Air": "assets/logos/wizz-air.svg",
  Ryanair: "assets/logos/ryanair.svg",
  Vueling: "assets/logos/vueling.svg",
  "Air Europa": "assets/logos/air-europa.svg?v=20261021-1",
  "Iberia Express": "assets/logos/iberia-express.svg",
};

const carrierPurchaseUrls = {
  Binter: "https://www.bintercanarias.com/es/buscar-vuelos",
  Iberia: "https://www.iberia.com/flights/",
  "Iberia Express": "https://www.iberia.com/flights/",
  Vueling: "https://www.vueling.com/es",
  "Air Europa": "https://www.aireuropa.com/es/es/home",
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

let calendarHighlightTimer;

function scrollToResult(resultId) {
  const card = [...elements.list.querySelectorAll(".flight-card")]
    .find(item => item.dataset.resultId === resultId);
  if (!card) return;

  elements.list.querySelectorAll(".is-calendar-target").forEach(item => {
    item.classList.remove("is-calendar-target");
  });
  card.classList.add("is-calendar-target");
  card.scrollIntoView({
    behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth",
    block: "center",
  });

  window.clearTimeout(calendarHighlightTimer);
  calendarHighlightTimer = window.setTimeout(() => {
    card.classList.remove("is-calendar-target");
  }, 1800);
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
  elements.calendarMonths.setAttribute("aria-busy", "false");
}

function setRangeProgress(input) {
  const min = Number(input.min);
  const max = Number(input.max);
  const progress = ((Number(input.value) - min) / (max - min)) * 100;
  input.style.setProperty("--progress", `${progress}%`);
}

function initializeFilters() {
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
  const configuredLimit = Math.max(100, Math.ceil(highestRegularPrice / 100) * 100);
  elements.price.max = String(configuredLimit);
  elements.price.value = String(configuredLimit);
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
  setRangeProgress(elements.price);
  setRangeProgress(elements.layover);
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
  origin.innerHTML = `<strong>${timePart(first.departure_at)}</strong><span class="airport-code">${first.departure_airport}</span>`;

  const firstLine = createLegLine(first);

  const destination = document.createElement("div");
  destination.className = "airport-stop destination";
  destination.innerHTML = `<strong>${timePart(last.arrival_at)}</strong><span class="airport-code">${last.arrival_airport}</span>`;

  if (isDirectConnection(result)) {
    journey.append(origin, firstLine, destination);
    return journey;
  }

  const second = result.legs[1];

  const transfer = document.createElement("div");
  transfer.className = "transfer-stop";
  const nextDayMarker = datePart(second.departure_at) > datePart(first.arrival_at) ? "*" : "";
  transfer.innerHTML = `<strong>${timePart(first.arrival_at)} · ${result.transfer_airport} · ${timePart(second.departure_at)}${nextDayMarker}</strong><span>${formatDuration(result.layover_minutes)} przerwy</span>`;

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
    ? "1 rezerwacja"
    : `${result.legs.length} osobne bilety`;
  fragment.querySelector(".purchase-button").addEventListener("click", () => showPurchaseDialog(result, filters));

  const details = fragment.querySelector(".price-details");
  details.innerHTML = priceDetails(result, filters);
  const toggle = fragment.querySelector(".details-toggle");
  toggle.addEventListener("click", () => {
    const expanded = toggle.getAttribute("aria-expanded") === "true";
    toggle.setAttribute("aria-expanded", String(!expanded));
    toggle.querySelector("span").textContent = expanded ? "Pokaż szczegóły ceny" : "Ukryj szczegóły ceny";
    details.hidden = expanded;
  });

  return fragment;
}

function renderActiveFilters() {
  const filters = currentFilters();
  const chips = [`Do ${currency.format(filters.maxPrice)}`];
  chips.push(filters.direction === "poland_to_tenerife" ? "Polska → Teneryfa" : "Teneryfa → Polska");
  if (filters.resident) chips.push("Rezydent Teneryfy");
  if (filters.wizzClub) chips.push("Wizz Air Discount Club");
  if (filters.origin !== "all") chips.push(`Wylot: ${filters.origin}`);
  if (filters.destination !== "all") chips.push(`Przylot: ${filters.destination}`);
  if (filters.transfer === "direct") chips.push("Bez przesiadek");
  if (filters.transfer !== "all" && filters.transfer !== "direct") chips.push(`Przez: ${filters.transfer}`);
  if (filters.firstCarrier !== "all") chips.push(`Pierwsza linia: ${filters.firstCarrier}`);
  if (filters.secondCarrier !== "all") chips.push(`Druga linia: ${filters.secondCarrier}`);
  if (filters.transfer !== "direct" && filters.maxLayover < 24 * 60) {
    chips.push(`Przesiadka do ${formatDuration(filters.maxLayover)}`);
  }
  if (filters.dateFrom !== state.document.period_from || filters.dateTo !== state.document.period_to) {
    chips.push(`${filters.dateFrom} – ${filters.dateTo}`);
  }
  elements.activeFilters.replaceChildren(...chips.map(label => {
    const chip = document.createElement("span");
    chip.className = "filter-chip";
    chip.textContent = label;
    return chip;
  }));
}

function renderResults() {
  updateRangeLabels();
  const filters = currentFilters();
  const results = filteredResults(filters);
  renderFareCalendar(results, filters);
  elements.count.textContent = results.length;
  elements.countNoun.textContent = pluralizeResults(results.length);
  renderActiveFilters();
  elements.list.setAttribute("aria-busy", "false");

  if (!results.length) {
    const directSelected = currentFilters().transfer === "direct";
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

  const cards = document.createDocumentFragment();
  for (const result of results) cards.append(createResultCard(result, filters));
  elements.list.replaceChildren(cards);
}

function resetFilters() {
  elements.resident.checked = true;
  elements.wizzClub.checked = false;
  elements.price.value = elements.price.max;
  elements.direction.value = "tenerife_to_poland";
  updateAirportOptions();
  elements.dateFrom.value = state.document.period_from;
  elements.dateTo.value = state.document.period_to;
  elements.origin.value = "all";
  elements.destination.value = "all";
  elements.transfer.value = "all";
  elements.firstCarrier.value = "all";
  elements.secondCarrier.value = "all";
  elements.layover.value = 6;
  elements.sort.value = "price";
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
  filters.forEach(element => element.addEventListener("input", renderResults));
  elements.direction.addEventListener("input", () => {
    updateAirportOptions();
    renderResults();
  });
  elements.reset.addEventListener("click", resetFilters);
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
    renderResults();
  } catch (error) {
    console.error("Nie udało się wczytać danych lotów", error);
    elements.updatedAt.textContent = "Brak danych";
    elements.calendarMonths.setAttribute("aria-busy", "false");
    elements.calendarMonths.innerHTML = `<div class="calendar-loading">Nie udało się wczytać kalendarza cen.</div>`;
    elements.list.setAttribute("aria-busy", "false");
    elements.list.innerHTML = `
      <div class="error-state">
        <strong>Nie udało się wczytać lotów</strong>
        <p>Sprawdź, czy pliki danych kroków 1–5 są dostępne.</p>
      </div>
    `;
  }
}

loadFlights();
