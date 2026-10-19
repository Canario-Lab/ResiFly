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
  transfer: document.querySelector("#transfer-filter"),
  carrier: document.querySelector("#carrier-filter"),
  layover: document.querySelector("#layover-filter"),
  layoverOutput: document.querySelector("#layover-output"),
  sort: document.querySelector("#sort-results"),
  reset: document.querySelector("#reset-filters"),
  activeFilters: document.querySelector("#active-filters"),
  count: document.querySelector("#results-count"),
  countNoun: document.querySelector("#results-noun"),
  list: document.querySelector("#results-list"),
  template: document.querySelector("#result-template"),
};

const currency = new Intl.NumberFormat("pl-PL", {
  style: "currency",
  currency: "PLN",
  minimumFractionDigits: 2,
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

function datePart(iso) {
  return iso.slice(0, 10);
}

function timePart(iso) {
  return iso.slice(11, 16);
}

function formatDate(iso) {
  const safeDate = new Date(`${datePart(iso)}T12:00:00Z`);
  const value = longDate.format(safeDate);
  return value.charAt(0).toUpperCase() + value.slice(1);
}

function formatTimestamp(iso) {
  const safeDate = new Date(`${datePart(iso)}T12:00:00Z`);
  return `${shortDate.format(safeDate)}, ${timePart(iso)}`;
}

function formatDuration(minutes) {
  const hours = Math.floor(minutes / 60);
  const remainder = minutes % 60;
  if (!remainder) return `${hours} godz.`;
  return `${hours} godz. ${remainder} min`;
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

  const transfers = [...new Set(state.results.map(result => result.transfer_airport))].sort();
  const carriers = [...new Set(state.results.map(result => result.legs.at(-1).carrier))].sort();
  addOptions(elements.transfer, transfers, optionLabel);
  addOptions(elements.carrier, carriers);
  updateRangeLabels();
}

function updateRangeLabels() {
  elements.priceOutput.textContent = currency.format(Number(elements.price.value));
  elements.layoverOutput.textContent = `${elements.layover.value} godz.`;
  setRangeProgress(elements.price);
  setRangeProgress(elements.layover);
}

function currentFilters() {
  return {
    maxPrice: Number(elements.price.value),
    dateFrom: elements.dateFrom.value,
    dateTo: elements.dateTo.value,
    origin: elements.origin.value,
    transfer: elements.transfer.value,
    carrier: elements.carrier.value,
    maxLayover: Number(elements.layover.value) * 60,
    sort: elements.sort.value,
  };
}

function filteredResults() {
  const filters = currentFilters();
  const filtered = state.results.filter(result => {
    const departureDate = datePart(result.legs[0].departure_at);
    const secondCarrier = result.legs.at(-1).carrier;
    return (
      result.price_total_resident_estimated_pln <= filters.maxPrice &&
      departureDate >= filters.dateFrom &&
      departureDate <= filters.dateTo &&
      (filters.origin === "all" || result.origin_airport === filters.origin) &&
      (filters.transfer === "all" || result.transfer_airport === filters.transfer) &&
      (filters.carrier === "all" || secondCarrier === filters.carrier) &&
      result.layover_minutes <= filters.maxLayover
    );
  });

  const sorters = {
    price: (a, b) => a.price_total_resident_estimated_pln - b.price_total_resident_estimated_pln,
    regular: (a, b) => a.price_total_regular_pln - b.price_total_regular_pln,
    layover: (a, b) => a.layover_minutes - b.layover_minutes,
    departure: (a, b) => a.legs[0].departure_at.localeCompare(b.legs[0].departure_at),
  };

  return filtered.sort((a, b) => {
    const primary = sorters[filters.sort](a, b);
    return primary || a.legs[0].departure_at.localeCompare(b.legs[0].departure_at);
  });
}

function createJourney(result) {
  const first = result.legs[0];
  const second = result.legs[1];
  const journey = document.createDocumentFragment();

  const origin = document.createElement("div");
  origin.className = "airport-stop";
  origin.innerHTML = `<strong>${timePart(first.departure_at)}</strong><span class="airport-code">${first.departure_airport}</span>`;

  const firstLine = document.createElement("div");
  firstLine.className = "leg-line";
  firstLine.innerHTML = `<span>${first.carrier} · ${first.flight_number}</span>`;

  const transfer = document.createElement("div");
  transfer.className = "transfer-stop";
  transfer.innerHTML = `<strong>${timePart(first.arrival_at)} · ${result.transfer_airport}</strong><span>${formatDuration(result.layover_minutes)} przerwy</span>`;

  const secondLine = document.createElement("div");
  secondLine.className = "leg-line";
  secondLine.innerHTML = `<span>${second.carrier} · ${second.flight_number}</span>`;

  const destination = document.createElement("div");
  destination.className = "airport-stop destination";
  destination.innerHTML = `<strong>${timePart(second.arrival_at)}</strong><span class="airport-code">${second.arrival_airport}</span>`;

  journey.append(origin, firstLine, transfer, secondLine, destination);
  return journey;
}

function priceDetails(result) {
  const [first, second] = result.legs;
  return `
    <div class="price-row">
      <span>${first.carrier} ${first.flight_number} · regularna ${currency.format(first.price_regular_pln)}</span>
      <strong>około ${currency.format(first.price_resident_estimated_pln)}</strong>
    </div>
    <div class="price-row">
      <span>${second.carrier} ${second.flight_number}</span>
      <strong>${currency.format(second.price_regular_pln)}</strong>
    </div>
    <div class="price-row">
      <span>Wylot ${formatTimestamp(first.departure_at)} · przylot ${formatTimestamp(second.arrival_at)}</span>
      <strong>Razem około ${currency.format(result.price_total_resident_estimated_pln)}</strong>
    </div>
  `;
}

function createResultCard(result) {
  const fragment = elements.template.content.cloneNode(true);
  const card = fragment.querySelector(".flight-card");
  const saving = result.price_total_regular_pln - result.price_total_resident_estimated_pln;

  card.dataset.resultId = result.id;
  fragment.querySelector(".date-label").textContent = formatDate(result.legs[0].departure_at);
  fragment.querySelector(".journey").append(createJourney(result));
  fragment.querySelector(".resident-price").textContent = currency.format(result.price_total_resident_estimated_pln);
  fragment.querySelector(".regular-price").textContent = `Cena regularna: ${currency.format(result.price_total_regular_pln)}`;
  fragment.querySelector(".saving-pill").textContent = `oszczędzasz około ${currency.format(saving)}`;

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
  if (filters.transfer !== "all") chips.push(`Przez: ${filters.transfer}`);
  if (filters.carrier !== "all") chips.push(filters.carrier);
  if (filters.maxLayover < 24 * 60) chips.push(`Przesiadka do ${formatDuration(filters.maxLayover)}`);
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
  const results = filteredResults();
  elements.count.textContent = results.length;
  elements.countNoun.textContent = pluralizeResults(results.length);
  renderActiveFilters();
  elements.list.setAttribute("aria-busy", "false");

  if (!results.length) {
    elements.list.innerHTML = `
      <div class="empty-state">
        <strong>Brak lotów dla tych filtrów</strong>
        <p>Podnieś limit ceny albo wybierz dłuższą przesiadkę.</p>
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
  elements.transfer.value = "all";
  elements.carrier.value = "all";
  elements.layover.value = 24;
  elements.sort.value = "price";
  renderResults();
}

function bindEvents() {
  const filters = [
    elements.price,
    elements.dateFrom,
    elements.dateTo,
    elements.origin,
    elements.transfer,
    elements.carrier,
    elements.layover,
    elements.sort,
  ];
  filters.forEach(element => element.addEventListener("input", renderResults));
  elements.reset.addEventListener("click", resetFilters);
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
