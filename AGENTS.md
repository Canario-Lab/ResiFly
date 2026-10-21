# ResiFly project rules

## Canonical five-step flight search

- The complete, durable procedure for recurring flight collection is stored in
  `docs/FIVE_STEP_FLIGHT_SEARCH.md`.
- Read and follow that file before running or changing the weekly collection.
- Keep exactly five search steps. Do not add, remove, or silently reinterpret a
  step without an explicit user decision.

## Canonical Step 1A Binter transfer-airport list

- The fixed airport allowlist for Step 1A is stored in
  `data/binter-transfer-airports.json`.
- Read the airport codes from that file whenever Step 1A is run. Do not
  rediscover, add, or remove transfer airports during a weekly collection.
- A weekly collection still fetches current schedules and prices for the
  listed airports; being on the allowlist does not imply current availability.
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
- Prefer the actual Iberia fare returned with the `CANARIAS` resident discount.
  Use the configured `0.25` multiplier only as an explicitly labelled fallback.
- Never persist Iberia access tokens, cookies, browser-session URLs or other
  temporary parameters. Every Iberia/Iberia Express leg must instead receive a
  deterministic `booking_url` from `scripts.booking_urls.iberia_booking_url`.

## Step 2 direct-flight collection

- Generate Step 2 with `scripts/collect_step2.py`.
- Check the complete matrix between WAW, WMI, KRK, KTW and TFN, TFS in both
  directions for Wizz Air and Ryanair.
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
  `resident_discount_on_tenerife_leg` in the same file. Apply the `0.25`
  multiplier only to the Tenerife leg when its transfer airport is listed as
  eligible; otherwise use the full fare (`1.0`).
- A weekly collection still fetches current schedules and prices for the
  listed route combinations; being on the allowlist does not imply current
  availability.
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
  `resident_discount_on_tenerife_leg` in the same file. Apply the `0.25`
  multiplier only to the Tenerife leg when its transfer airport is listed as
  eligible; otherwise use the full fare (`1.0`).
- A weekly collection still fetches current schedules and prices for the
  listed route combinations; being on the allowlist does not imply current
  availability.
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
- Read resident-discount eligibility and the Tenerife-leg fare multiplier from
  the matching variant. Never infer the discount from the carrier alone.
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
- Do not hand-edit generated result JSON files. Update the collector/builder and
  regenerate them when the user explicitly asks for new data.

## Price filtering

- Flight collectors and generated public JSON files must not discard results
  because of price.
- Collect every result that satisfies the route, date, carrier, and connection
  rules. The website applies the user's selected maximum-price filter.
- Keep regular, resident, and Wizz Air Discount Club prices as separate values
  whenever the source provides them.

## Transfer-route detector

- Use `scripts/discover_transfer_routes.py` to check whether the airline route
  networks create new Step 1A, 3, 4, or 5 transfer combinations. Step 1B is
  reviewed separately because its list may contain only Iberia routes eligible
  for the Canary resident discount. Step 2 has no transfer allowlist: its
  collector always checks the complete fixed airport matrix.
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

