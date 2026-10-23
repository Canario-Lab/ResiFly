# ResiFly project rules

## Canonical endpoint registry

- Read Polish endpoints and their time zones from `data/search-airports.json`
  through `scripts.search_airports`. The approved endpoints are WAW, WMI,
  KTW, KRK, GDN, WRO, POZ, LCJ, RZE and BZG. Collectors and route discovery must share this registry.
- GDN also retains its existing Step 5 variant B transfer to KRK. The precise
  exception is stored in the endpoint registry; do not enable self-routes or
  silently expand other endpoint-as-transfer roles.

## Canonical five-step flight search

- The complete, durable procedure for recurring flight collection is stored in
  `docs/FIVE_STEP_FLIGHT_SEARCH.md`.
- Read and follow that file before running or changing the weekly collection.
- Keep exactly five search steps. Do not add, remove, or silently reinterpret a
  step without an explicit user decision.
- For every saved route in every step, fetch the complete configured calendar
  window in both directions for each participating carrier before matching or
  comparing legs. Never derive one carrier's query dates from another
  carrier's returned flights.

## Canonical Step 1A Binter transfer-airport list

- The fixed airport allowlist for Step 1A is stored in
  `data/binter-transfer-airports.json`.
- Read the airport codes from that file whenever Step 1A is run. Do not
  rediscover, add, or remove transfer airports during a weekly collection.
- A weekly collection still fetches current schedules and prices for the
  listed airports; being on the allowlist does not imply current availability.
- Check every calendar day in the complete configured window for every saved
  Binter route in both directions, independently of the Wizz Air/Ryanair
  calendar. Match connections only after both full calendars are collected.
- Never turn a failed request or GraphQL error into an empty availability
  list, including GraphQL errors returned with HTTP 200. Preserve the previous
  public feed on failure. Binter loyalty-point (`PTS`) fares are not EUR cash
  fares and may be skipped without discarding the flight's valid EUR fares.
- Treat Binter `booking_search` amounts only as fare-list values used to select
  a cash fare. For every selected fare, use its opaque token in an in-memory
  `booking_getImports` request for one adult (`RC` on eligible routes), and
  save the final payable regular and resident totals reconstructed from fare,
  taxes, supplements, service fee and management fee. Never persist the token.
  Missing or malformed final-price components must fail before publication.
- Update this allowlist only when the user explicitly asks to revise it.
- Keep each Step 1A airport's IANA time zone and resident-discount eligibility
  in `data/binter-transfer-airports.json`. Keep the verified Wizz routes needed
  by Step 1A in that same file under `wizz_route_schedules`. Do not hard-code
  new Step 1A airport knowledge in the collector.

## Canonical Step 1B Iberia transfer-airport list

- Step 1B is a variant within Step 1, not a sixth top-level search step.
- Its fixed Iberia/Iberia Express allowlist is stored in
  `data/iberia-transfer-airports.json`. Only routes eligible for the Canary
  resident discount may be present.
- Generate Step 1B with `scripts/collect_step1b.py` and write the public feed
  to `data/step1b-results.json`.
- Read airport codes, time zones, discount eligibility, multiplier and Wizz
  route metadata from that allowlist. Do not rediscover or hard-code transfer
  airports during a regular price collection.
- Read the regular Iberia/Iberia Express fare in PLN from Google Flights by
  HTTP, without launching a real browser. Calculate the resident estimate by
  subtracting the direction-specific non-discountable fees from
  `data/spanish-resident-fees.json`, applying the allowlist's configured `0.25`
  multiplier only to the remaining fare component, and adding the fees back.
  Label it as an estimate.
- Check every calendar day in the complete configured window for every saved
  Iberia/Iberia Express route in both directions, independently of the Wizz
  Air/Ryanair calendar. Match connections only after both full calendars are
  collected.
- If Google Flights does not return usable Iberia data, fail before overwriting
  the previous `data/step1b-results.json` file. Never invent prices.
- Never persist Iberia access tokens, cookies, browser-session URLs or other
  temporary parameters. Every Iberia/Iberia Express leg must instead receive a
  deterministic `booking_url` from `scripts.booking_urls.iberia_booking_url`.

## Canonical Step 1C Vueling transfer-airport list

- Step 1C is a variant within Step 1, not a sixth top-level search step.
- Its fixed Vueling allowlist is stored in
  `data/vueling-transfer-airports.json`. Only Vueling routes eligible for the
  Canary resident discount and having a saved Ryanair/Wizz Air route to a
  target Polish airport may be present.
- Treat Vueling's official Tenerife route page as the primary route source.
  Aena may only be used as corroborating evidence; do not rely on Aena alone.
- Generate Step 1C with `scripts/collect_step1c.py` and write the public feed
  to `data/step1c-results.json`.
- Read transfer airports, Tenerife airports, time zones, discount metadata and
  permitted Polish route/carrier pairs from that allowlist. Do not rediscover
  or hard-code transfer routes during a regular price collection.
- Read regular Vueling fares in PLN from Google Flights by HTTP, without a
  real browser. Calculate the resident estimate with the shared Aena-fee rule
  from `data/spanish-resident-fees.json`; never multiply the whole regular fare
  by `0.25`. Label it as an estimate. If no usable Vueling data is returned,
  fail before overwriting the previous public feed.
- Check every calendar day in the complete configured date window for every
  saved Vueling route in both directions, independently of which dates have a
  matching Wizz Air or Ryanair flight. Match connections only after this full
  Vueling scan.
- Every Vueling leg must contain a deterministic `booking_url` generated by
  `scripts.booking_urls.vueling_booking_url`; never store tokens, cookies or
  browser-session URLs.
- Use the shared `data/wizz-route-schedules.json` registry for Wizz Air route
  numbers and block times needed by Step 1C.

## Canonical Step 1D Air Europa transfer-airport list

- Step 1D is a variant within Step 1, not a sixth top-level search step.
- Its fixed Air Europa allowlist is stored in
  `data/air-europa-transfer-airports.json`. Only Air Europa routes eligible for
  the Canary resident discount and having a saved Ryanair/Wizz Air route to a
  target Polish airport may be present.
- Generate Step 1D with `scripts/collect_step1d.py` and write the public feed
  to `data/step1d-results.json`.
- Read transfer airports, Tenerife airports, time zones, discount metadata,
  permitted Polish route/carrier pairs and accepted Air Europa airline codes
  from that allowlist. Do not rediscover or hard-code transfer routes.
- Google Flights HTTP is the ONLY source of current Air Europa flight numbers,
  departure/arrival dates and times, and individual regular fares in PLN.
  Check all recognized offer groups and keep each flight's own lowest fare.
  Never expand a daily minimum across flights, use timetable templates, or
  fall back to the official promotional/branded route-day fare feed.
- Limit Google Flights to at most TWO concurrent requests using the shared
  `scripts.collector_settings` cap, including retries. Calculate the resident
  estimate by subtracting the direction-specific fixed non-discountable fees
  saved in `data/spanish-resident-fees.json`, applying the saved `0.25`
  multiplier only to the
  remaining fare component, and adding the fixed fees back. Convert those EUR
  fees with the batch's single NBP rate. Explicitly label the result as an
  estimate, not an official resident quote. Never apply `0.25` to the entire
  regular fare and never invent a missing route fee or flight datum.
- Check every calendar day in the complete configured date window for every
  saved Air Europa route in both directions, independently of which dates have
  a matching Wizz Air or Ryanair flight. Match connections only after this
  full Air Europa scan.
- If Google Flights fails, a returned flight lacks a usable price or complete
  number/times, or the full collection yields no usable Air Europa fares,
  fail before overwriting the previous public feed. A verified empty day is
  not a failed request. Source coverage accepts only `google_flights_http`.
- Every Air Europa leg must contain a deterministic `booking_url` generated by
  `scripts.booking_urls.air_europa_booking_url`. Use the concrete
  `residentType=SPANISH_RESIDENT_RC` value returned by Air Europa's public
  route endpoint for an eligible resident search and remove it on the website
  when the resident filter is disabled. Do not use the intermediate `true`
  value because the carrier's redirect can stall while resolving it. Never
  persist API keys, cookies, tokens or browser-session URLs.
- Keep full flight numbers (e.g. UX9048), never just UX. The current stable
  official booking link opens a route/date search, NOT an automatically
  preselected flight. Preserve resident/non-resident toggling independently
  of the Google price source. Never invent flight-selection query parameters
  or persist a Google/Amadeus session link to claim exact-flight preselection.
- Use the shared `data/wizz-route-schedules.json` registry and the Step 1A
  Wizz schedule entries for low-cost routes needed by Step 1D.

## Canonical Step 1E Volotea transfer-airport list

- Step 1E is a variant within Step 1, not a sixth top-level search step.
- Its fixed Volotea allowlist is stored in
  `data/volotea-transfer-airports.json`. Only Volotea routes eligible for the
  Canary resident discount and having a saved Ryanair/Wizz Air route to a
  target Polish airport may be present.
- Generate Step 1E with `scripts/collect_step1e.py` and write the public feed
  to `data/step1e-results.json`.
- Read transfer airports, Tenerife airports, time zones, discount metadata and
  permitted Polish route/carrier pairs from that allowlist. Do not rediscover
  or hard-code transfer routes during a regular price collection.
- Read dates, times, flight numbers and regular fares with fees directly from
  Volotea's official public MinPrice endpoint, one saved route/day at a time.
  Check every calendar day in the complete configured date window in both
  directions, independently of which dates currently have a matching Wizz Air
  or Ryanair leg. Match connections only after this complete scan.
  Never use Google Flights for Step 1E and never invent schedule data.
- Calculate the resident estimate with the shared Aena-fee rule from
  `data/spanish-resident-fees.json` and label it as an estimate. When Volotea
  returns its own taxes/fees field, require it to match the shared route fee;
  never discount those fees. A successful empty route/day response means no
  availability, while an endpoint
  error must abort before overwriting the previous public feed.
- Every Volotea leg must contain a deterministic `booking_url` generated by
  `scripts.booking_urls.volotea_booking_url`. It identifies the official route
  and date without cookies, tokens or session data. The passenger confirms
  resident status in Volotea's own passenger selector because its public URL
  format exposes no supported resident parameter.
- Use the shared `data/wizz-route-schedules.json` registry for Wizz Air route
  numbers and block times needed by Step 1E.

## Canonical Step 1F Canaryfly transfer-airport list

- Step 1F is a variant within Step 1, not a sixth top-level search step.
- Its fixed Canaryfly allowlist is stored in
  `data/canaryfly-transfer-airports.json`. Only direct Canaryfly routes
  eligible for the Canary resident discount and having a saved Ryanair/Wizz
  Air route to a target Polish airport may be present.
- Generate Step 1F with `scripts/collect_step1f.py` and write the public feed
  to `data/step1f-results.json`.
- Read transfer airports, Tenerife airports, time zones, discount metadata and
  permitted Polish route/carrier pairs from that allowlist. Do not rediscover
  or hard-code transfer routes during a regular price collection.
- Fetch every complete Canaryfly monthly calendar covering the configured
  window for every saved route in both directions. Only after all calendars
  are complete, fetch flight-specific details for each available day, then
  match those legs with the independently collected full Ryanair/Wizz Air
  calendars. Never prefilter Canaryfly dates from the low-cost timetable.
- Read dates, times and flight numbers from Canaryfly's official public
  `booking_calendar` and `booking_search` GraphQL operations. Treat the
  `booking_search` resident and non-resident amounts only as fare-list values
  used to select a fare. Pass its opaque token in memory to
  `booking_getImports` for one adult with Canaryfly's configured `DC` resident
  code. Save the final regular total as the sum of `mainAmount` and the final
  resident total as the sum of `totalAmount` across fare, taxes, supplements,
  service fee and management fee. Missing or malformed components, or failure
  to confirm resident status, must abort before publication. Never use Google
  Flights for Step 1F and never persist the opaque token.
- Every Canaryfly leg must contain a deterministic `booking_url` generated by
  `scripts.booking_urls.canaryfly_booking_url`. It identifies the official
  route and date without cookies, tokens or session data. Canaryfly exposes
  the resident/non-resident choice inside its own booking flow, not as a
  supported public URL parameter.
- Use the shared `data/wizz-route-schedules.json` registry for Wizz Air route
  numbers and block times needed by Step 1F.

## Verified Wizz calendar overrides

- Resolve all Wizz technical schedules through `scripts.wizz_schedules`.
  Preserve shared and local Step 1A/1B metadata consistently.
- When verified block times or numbers differ at the same departure clock,
  use `flight_number_overrides_by_departure_weekday_and_time` (ISO weekday
  1–7) or `flight_number_overrides_by_departure_date_and_time` for a verified
  date-specific exception. Date overrides take precedence over weekday and
  clock-only overrides. Never arbitrarily select one conflicting observation.

## Shared Spanish resident-estimate fee registry

- The canonical direction-specific non-discountable fee table is
  `data/spanish-resident-fees.json`; collectors must read it through
  `scripts.spanish_resident_fees`. Do not duplicate or guess fee values in
  collector code or route allowlists.
- Apply this estimate only to Iberia/Iberia Express, Vueling, Air Europa,
  Volotea, and eligible Spanish Tenerife legs flown by Ryanair or Wizz Air in
  Steps 3–5. Subtract the fixed fee in PLN, apply the saved multiplier to the
  remaining fare component, then add the full fee back.
- Do not apply this estimator to Binter or Canaryfly. Their official final
  imports operations return flight-specific regular and resident totals,
  which must be preserved.
- Convert all fee amounts with the same NBP EUR/PLN rate used by the batch.
  The registry's validity period must cover every departure date; an expired
  or missing route fee must fail closed before publication.
- `scripts/reprice_spanish_resident_estimates.py` may update only derived
  resident fields and dependent totals in already collected feeds. It must not
  make network requests or change flights, regular fares, booking links,
  collection timestamps, coverage reports, or run IDs.

## Step 2 direct-flight collection

- Generate Step 2 with `scripts/collect_step2.py`.
- Check the complete matrix between WAW, WMI, KRK, KTW, GDN, WRO, POZ, LCJ, RZE, BZG and TFN, TFS in both
  directions for Wizz Air and Ryanair.
- Fetch the complete configured date window for every route/carrier pair before
  producing results; do not prefilter dates with another source.
- Keep every direct flight returned for the configured date window regardless
  of price. The website, not the collector, applies the user's price limit.
- Write the generated public feed to `data/step2-results.json`.

## Canonical Ryanair transfer-airport list

- The fixed Ryanair + Ryanair airport allowlist for Step 3 is stored in
  `data/ryanair-transfer-airports.json`.
- Generate Step 3 with `scripts/collect_step3.py` and write the public feed to
  `data/step3-results.json`.
- Read both the transfer airport code and its eligible Polish airport codes
  from that file whenever Step 3 is run. Do not rediscover, add, or remove
  transfer airports during a weekly collection.
- Read resident-discount eligibility from
  `resident_discount_on_tenerife_leg` in the same file. For an eligible
  Tenerife leg, subtract the direction-specific fees from
  `data/spanish-resident-fees.json`, apply `0.25` only to the fare component,
  and add the fees back. Otherwise use the full fare (`1.0`).
- A weekly collection still fetches current schedules and prices for the
  listed route combinations; being on the allowlist does not imply current
  availability.
- Fetch the complete configured date window for every saved Ryanair leg in
  both directions before matching the two legs.
- Update this allowlist only when the user explicitly asks to revise it.
- Keep transfer-airport time zones in the allowlist's `airport_timezones`
  object so a new airport does not require a collector-code change.

## Canonical Wizz Air transfer-airport list

- The fixed Wizz Air + Wizz Air airport allowlist for Step 4 is stored in
  `data/wizzair-transfer-airports.json`.
- Generate Step 4 with `scripts/collect_step4.py` and write the public feed to
  `data/step4-results.json`.
- Read both the transfer airport code and its eligible Polish airport codes
  from that file whenever Step 4 is run. Do not rediscover, add, or remove
  transfer airports during a weekly collection.
- Read resident-discount eligibility from
  `resident_discount_on_tenerife_leg` in the same file. For an eligible
  Tenerife leg, subtract the direction-specific fees from
  `data/spanish-resident-fees.json`, apply `0.25` only to the fare component,
  and add the fees back. Otherwise use the full fare (`1.0`).
- A weekly collection still fetches current schedules and prices for the
  listed route combinations; being on the allowlist does not imply current
  availability.
- Fetch the complete configured date window for every saved Wizz Air leg in
  both directions before matching the two legs.
- Update this allowlist only when the user explicitly asks to revise it.
- Keep transfer-airport time zones in the allowlist's `airport_timezones`
  object. Keep verified Wizz Air flight numbers, published block times and
  time-specific flight-number overrides in `data/wizz-route-schedules.json`;
  the public Wizz timetable API supplies current dates, departure times and
  fares but omits arrival times and flight numbers. If a new allowlisted route
  becomes active, verify and add its schedule to that data file instead of
  changing the collector or inventing missing data.

## Canonical mixed Ryanair/Wizz Air transfer-airport list

- The fixed mixed-airline airport allowlist for Step 5 is stored in
  `data/mixed-transfer-airports.json`.
- Generate Step 5 with `scripts/collect_step5.py` and write the public feed to
  `data/step5-results.json`.
- Read the route combinations from both variants in that file whenever Step 5
  is run: Ryanair on the Tenerife leg with Wizz Air on the Poland leg, and
  Wizz Air on the Tenerife leg with Ryanair on the Poland leg.
- Check both travel directions separately. The airline assigned to a
  geographical leg remains the same when the direction is reversed.
- Fetch the complete configured date window for every saved leg of both
  carriers before matching mixed-carrier connections. Never use one carrier's
  dates to prefilter requests to the other carrier.
- Read resident-discount eligibility and the Tenerife-leg fare multiplier from
  the matching variant. For an eligible leg use the shared Aena-fee rule from
  `data/spanish-resident-fees.json`; never infer the discount from the carrier
  alone or multiply the whole regular price by `0.25`.
- Do not rediscover, add, or remove transfer airports during a weekly
  collection. Still fetch current schedules and prices for every saved route
  combination.
- Update this allowlist only when the user explicitly asks to revise it.
- Keep transfer-airport time zones in the allowlist's `airport_timezones`
  object. Mixed variants that use Wizz Air read their verified technical route
  data from `data/wizz-route-schedules.json`, without hard-coded route changes
  in the Step 5 collector.

## Flight booking links

- Every Wizz Air leg written to a public results JSON must contain a
  `booking_url` field.
- Generate the URL deterministically with `scripts.booking_urls.wizz_booking_url`.
  Do not copy a browser-session URL and do not store cookies, tokens, or other
  temporary query parameters.
- The Wizz Air URL identifies the route, departure date, and passenger counts.
  It does not guarantee that a particular flight number is preselected when
  more than one flight operates on the same route that day.
- Keep `booking_url` on the individual leg, not only on the whole connection,
  because self-transfer itineraries are purchased one leg at a time.
- Every Ryanair leg written to a public results JSON must also contain a
  `booking_url` field.
- Generate the Ryanair URL deterministically from the departure airport,
  arrival airport, departure date, and passenger counts. Do not copy a
  browser-session URL and do not store cookies, tokens, or other temporary
  query parameters.
- A Ryanair URL identifies the route, departure date, and passenger counts. It
  does not guarantee that a particular flight number is preselected when more
  than one flight operates on the same route that day.
- Keep the Ryanair `booking_url` on the individual leg for the same reason as
  the Wizz Air URL: self-transfer itineraries are purchased one leg at a time.
- Every Iberia and Iberia Express leg written to a public results JSON must
  contain a deterministic `booking_url` generated with
  `scripts.booking_urls.iberia_booking_url`.
- Every Vueling leg written to a public results JSON must contain a
  deterministic `booking_url` generated with
  `scripts.booking_urls.vueling_booking_url`.
- Every Air Europa leg written to a public results JSON must contain a
  deterministic `booking_url` generated with
  `scripts.booking_urls.air_europa_booking_url`.
- Every Volotea leg written to a public results JSON must contain a
  deterministic `booking_url` generated with
  `scripts.booking_urls.volotea_booking_url`.
- Every Canaryfly leg written to a public results JSON must contain a
  deterministic `booking_url` generated with
  `scripts.booking_urls.canaryfly_booking_url`.
- Do not hand-edit generated result JSON files. Update the collector/builder and
  regenerate them when the user explicitly asks for new data.

## Price filtering

- Flight collectors and generated public JSON files must not discard results
  because of price.
- Collect every result that satisfies the route, date, carrier, and connection
  rules. The website applies the user's selected maximum-price filter.
- Keep regular, resident, and Wizz Air Discount Club prices as separate values
  whenever the source provides them.

## Collection completeness and publication

- Read `docs/COLLECTION_RELIABILITY.md` when changing source collection or
  publication. Keep route/day coverage in `scripts.collection_coverage` for
  standalone collectors as well as the full staged batch.
- Google Flights HTTP is the only current source for Ryanair flight numbers,
  dates, times and individual PLN fares. Query every saved route on every day
  of the complete window and retain both `FR` and Ryanair UK `RK` marketing
  codes. Never expand a daily minimum across flights or fall back to Fare
  Finder. Limit all Ryanair Google requests to two concurrent calls, reuse the
  persistent route/day cache across the ten feeds in one batch, and fail closed
  before publication on an unpriced flight, malformed response or failed day.
- A public feed requires complete independently planned route/day coverage.
  All ten feeds in a promoted batch must have matching complete sidecar
  reports, current canonical coverage and the same collection run ID.
- On failure preserve previous public feeds, write an explicit failure report
  and never mix old and new flight prices. Do not attach new completeness
  certificates to old generated feeds; recollection is required.

## Transfer-route detector

- Use `scripts/discover_transfer_routes.py` to check whether the airline route
  networks create new Step 1A, 3, 4, or 5 transfer combinations. Steps 1B,
  1C, 1D, 1E and 1F are reviewed separately because their lists may contain
  only eligible resident-discount routes of Iberia, Vueling, Air Europa,
  Volotea and Canaryfly respectively. Step 1C must be checked against Vueling's own route page,
  Step 1D routes against Air Europa's official route pages (current flight data
  and prices come exclusively from Google Flights), and Step
  1E against Volotea's official route page and public MinPrice endpoint, and
  Step 1F against Canaryfly's official route pages and GraphQL calendar. Step
  2 has no transfer allowlist: its collector always checks the complete fixed
  airport matrix.
- The detector is separate from the five price collectors. Do not run it as
  part of a normal price refresh unless route discovery was explicitly
  requested or separately scheduled.
- Its default mode is a read-only dry run. Use `--apply` only after reviewing
  the printed report. Existing allowlist entries are never removed
  automatically because a missing route may only be seasonal or temporarily
  unpublished.
- The detector may activate a new Wizz Air route only when verified flight
  number and block-time entries for both directions already exist in the Wizz
  schedule registry. If they do not, it must report the route as pending and
  leave that incomplete candidate unchanged. Complete candidates from other
  steps may still be applied.
- The script is suitable for GitHub Actions. A future workflow should install
  `scripts/requirements-flight-collector.txt`, run the detector in dry-run mode
  first, preserve its JSON report as an artifact, and only then run with
  `--apply` under the chosen review policy.

