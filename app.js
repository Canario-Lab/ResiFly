const DATA_URL = "data/test-results-waw.json";

const state = {
  document: null,
  results: [],
};

const elements = {
  updatedAt: document.querySelector("#updated-at"),
  price: document.querySelector("#price-filter"),
  priceOutput: document.querySelector("#price-output"),
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
};

const carrierPurchaseUrls = {
  Binter: "https://www.bintercanarias.com/es/buscar-vuelos",
  "Wizz Air": "https://wizzair.com/pl-pl",
  Ryanair: "https://www.ryanair.com/pl/pl",
};

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

function optionLabel(code) {
  const labels = {
    FUE: "Fuerteventura (FUE)",
    LPA: "Gran Canaria (LPA)",
    MAD: "Madryt (MAD)",
    PMI: "Palma de Mallorca (PMI)",
    SVQ: "Sewilla (SVQ)",
    VLC: "Walencja (VLC)",
  };
  return labels[code] || code;
}

function addOptions(select, values, formatter = value => value) {
  for (const value of values) {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = formatter(value);
    select.append(option);
  }
}

function lowestPricesByDate(results) {
  const prices = new Map();
  for (const result of results) {
    const date = datePart(result.legs[0].departure_at);
    const resident = Number(result.price_total_resident_estimated_pln);
    const regular = Number(result.price_total_regular_pln);
    if (!Number.isFinite(resident) || !Number.isFinite(regular)) continue;
    const current = prices.get(date);
    if (current === undefined || resident < current.resident) {
      prices.set(date, { resident, regular, resultId: result.id });
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

  const residentPrice = document.createElement("strong");
  residentPrice.className = "calendar-day-price";
  if (price === undefined) {
    cell.classList.add("has-no-price");
    residentPrice.textContent = "—";
    cell.setAttribute("aria-label", `${formatDate(isoDate)}, brak połączeń`);
  } else {
    cell.classList.add("has-price");
    residentPrice.textContent = `${calendarCurrency.format(price.resident)}*`;
    const regularPrice = document.createElement("span");
    regularPrice.className = "calendar-day-regular-price";
    regularPrice.textContent = calendarCurrency.format(price.regular);
    regularPrice.title = "Cena regularna";
    cell.append(residentPrice, regularPrice);
    cell.setAttribute(
      "aria-label",
      `${formatDate(isoDate)}, cena dla rezydenta ${currency.format(price.resident)}, cena regularna ${currency.format(price.regular)}`
    );
    cell.addEventListener("click", () => scrollToResult(price.resultId));
    return cell;
  }
  cell.append(residentPrice);
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
  const prices = lowestPricesByDate(results);

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
  elements.layoverOutput.textContent = `${elements.layover.value} godz.`;
  elements.layover.disabled = directSelected;
  elements.layover.closest(".layover-field").classList.toggle("is-disabled", directSelected);
  setRangeProgress(elements.price);
  setRangeProgress(elements.layover);
}

function currentFilters() {
  return {
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
      result.price_total_resident_estimated_pln <= filters.maxPrice &&
      departureDate >= filters.dateFrom &&
      departureDate <= filters.dateTo &&
      (filters.origin === "all" || result.origin_airport === filters.origin) &&
      result.destination_airport === filters.destination &&
      transferMatches &&
      (filters.firstCarrier === "all" || firstCarrier === filters.firstCarrier) &&
      (filters.secondCarrier === "all" || (!direct && secondCarrier === filters.secondCarrier)) &&
      (direct || result.layover_minutes <= filters.maxLayover)
    );
  });

  const sorters = {
    price: (a, b) => a.price_total_resident_estimated_pln - b.price_total_resident_estimated_pln,
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

function priceDetails(result) {
  const first = result.legs[0];
  const last = result.legs.at(-1);
  const hasResidentEstimate = result.price_total_resident_estimated_pln < result.price_total_regular_pln;
  const legRows = result.legs.map(leg => {
    const discounted =
      leg.resident_discount_eligible && leg.price_resident_estimated_pln < leg.price_regular_pln;
    const price = discounted
      ? `<span class="regular-inline">(Cena regularna: ~${currency.format(leg.price_regular_pln)})</span> ~${currency.format(leg.price_resident_estimated_pln)}`
      : `~${currency.format(leg.price_regular_pln)}`;
    return `
      <div class="price-row">
        <span>${leg.carrier} ${leg.flight_number}</span>
        <strong>${price}</strong>
      </div>
    `;
  }).join("");
  const totalPrice = `~${currency.format(
    hasResidentEstimate
      ? result.price_total_resident_estimated_pln
      : result.price_total_regular_pln
  )}`;

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

function purchaseLegPriceLabel(leg) {
  const hasResidentEstimate =
    leg.resident_discount_eligible && leg.price_resident_estimated_pln < leg.price_regular_pln;
  const price = hasResidentEstimate ? leg.price_resident_estimated_pln : leg.price_regular_pln;
  return `${hasResidentEstimate ? "Cena orientacyjna dla rezydenta" : "Cena orientacyjna"}: ~${currency.format(price)}`;
}

function createPurchaseStep(leg, index) {
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

  const timing = document.createElement("span");
  timing.className = "purchase-step-timing";
  timing.textContent = `Wylot: ${formatPurchaseTimestamp(leg.departure_at)} · Przylot: ${formatPurchaseTimestamp(leg.arrival_at)}`;

  const flightNumber = document.createElement("span");
  flightNumber.className = "purchase-step-flight";
  flightNumber.textContent = `Numer lotu: ${leg.flight_number}`;

  const price = document.createElement("span");
  price.className = "purchase-step-price";
  price.textContent = purchaseLegPriceLabel(leg);

  const actions = document.createElement("div");
  actions.className = "purchase-step-actions";

  const openLink = document.createElement("a");
  openLink.className = "purchase-open-link";
  openLink.href = carrierPurchaseUrls[leg.carrier] || "#";
  openLink.target = "_blank";
  openLink.rel = "noopener noreferrer";
  openLink.textContent = `Otwórz ${leg.carrier}`;
  if (!carrierPurchaseUrls[leg.carrier]) {
    openLink.hidden = true;
  }

  actions.append(openLink);
  step.append(heading, route, timing, flightNumber, price, actions);
  return step;
}

function showPurchaseDialog(result) {
  const separateBookings = result.legs.length > 1;
  const intro = document.createElement("p");
  intro.className = "purchase-dialog-intro";
  intro.textContent = separateBookings
    ? `To połączenie składa się z ${result.legs.length} osobnych rezerwacji. Kup każdy odcinek bezpośrednio u przewoźnika.`
    : "Ten lot kupisz jako jedną rezerwację bezpośrednio u przewoźnika.";

  const steps = document.createElement("div");
  steps.className = "purchase-steps";
  result.legs.forEach((leg, index) => steps.append(createPurchaseStep(leg, index)));

  const note = document.createElement("p");
  note.className = "purchase-dialog-note";
  note.textContent = separateBookings
    ? "Przed zapłatą upewnij się, że wszystkie loty są nadal dostępne. Ceny mogą się zmienić na stronach linii."
    : "Przed zapłatą sprawdź aktualną cenę i dostępność na stronie linii.";

  const kiwiLink = document.createElement("a");
  kiwiLink.className = "purchase-kiwi-link";
  kiwiLink.href = "https://www.kiwi.com/pl/";
  kiwiLink.target = "_blank";
  kiwiLink.rel = "noopener noreferrer";
  kiwiLink.textContent = "Sprawdź i kup na Kiwi.com";

  elements.purchaseDialogContent.replaceChildren(intro, note, steps, kiwiLink);
  elements.purchaseDialog.showModal();
}

function createResultCard(result) {
  const fragment = elements.template.content.cloneNode(true);
  const card = fragment.querySelector(".flight-card");
  const direct = isDirectConnection(result);
  const hasResidentEstimate = result.price_total_resident_estimated_pln < result.price_total_regular_pln;

  card.dataset.resultId = result.id;
  fragment.querySelector(".date-label").textContent = formatDate(result.legs[0].departure_at);
  fragment.querySelector(".connection-label").textContent = direct ? "Bez przesiadek" : "1 przesiadka";
  fragment.querySelector(".total-duration").textContent = `Łącznie: ${formatDuration(journeyDuration(result))}`;
  const journey = fragment.querySelector(".journey");
  journey.classList.toggle("direct", direct);
  journey.append(createJourney(result));
  fragment.querySelector(".resident-caption").textContent = hasResidentEstimate ? "Cena dla rezydenta" : "Cena lotu";
  fragment.querySelector(".resident-price").textContent = `~${currency.format(result.price_total_resident_estimated_pln)}`;
  const regularPrice = fragment.querySelector(".regular-price");
  regularPrice.textContent = hasResidentEstimate
    ? `Cena regularna: ~${currency.format(result.price_total_regular_pln)}`
    : "";
  regularPrice.hidden = !hasResidentEstimate;
  fragment.querySelector(".purchase-ticket-count").textContent = direct
    ? "1 rezerwacja"
    : `${result.legs.length} osobne bilety`;
  fragment.querySelector(".purchase-button").addEventListener("click", () => showPurchaseDialog(result));

  const details = fragment.querySelector(".price-details");
  details.innerHTML = priceDetails(result);
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
  if (filters.origin !== "all") chips.push(`Wylot: ${filters.origin}`);
  chips.push(`Przylot: ${filters.destination}`);
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
  for (const result of results) cards.append(createResultCard(result));
  elements.list.replaceChildren(cards);
}

function resetFilters() {
  elements.price.value = 500;
  elements.dateFrom.value = state.document.period_from;
  elements.dateTo.value = state.document.period_to;
  elements.origin.value = "all";
  elements.destination.value = "WAW";
  elements.transfer.value = "all";
  elements.firstCarrier.value = "all";
  elements.secondCarrier.value = "all";
  elements.layover.value = 6;
  elements.sort.value = "price";
  renderResults();
}

function bindEvents() {
  const filters = [
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
    const response = await fetch(DATA_URL, { cache: "no-store" });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    state.document = await response.json();
    state.results = state.document.results || [];

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
        <p>Sprawdź, czy plik data/test-results-waw.json jest dostępny.</p>
      </div>
    `;
  }
}

loadFlights();
