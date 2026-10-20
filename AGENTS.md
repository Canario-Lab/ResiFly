# ResiFly project rules

## Canonical five-step flight search

- The complete, durable procedure for recurring flight collection is stored in
  `docs/FIVE_STEP_FLIGHT_SEARCH.md`.
- Read and follow that file before running or changing the weekly collection.
- Keep exactly five search steps. Do not add, remove, or silently reinterpret a
  step without an explicit user decision.

## Canonical Binter transfer-airport list

- The fixed airport allowlist for Step 1 is stored in
  `data/binter-transfer-airports.json`.
- Read the airport codes from that file whenever Step 1 is run. Do not
  rediscover, add, or remove transfer airports during a weekly collection.
- A weekly collection still fetches current schedules and prices for the
  listed airports; being on the allowlist does not imply current availability.
- Update this allowlist only when the user explicitly asks to revise it.

## Canonical Ryanair transfer-airport list

- The fixed Ryanair + Ryanair airport allowlist for Step 3 is stored in
  `data/ryanair-transfer-airports.json`.
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

## Canonical Wizz Air transfer-airport list

- The fixed Wizz Air + Wizz Air airport allowlist for Step 4 is stored in
  `data/wizzair-transfer-airports.json`.
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

## Canonical mixed Ryanair/Wizz Air transfer-airport list

- The fixed mixed-airline airport allowlist for Step 5 is stored in
  `data/mixed-transfer-airports.json`.
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
- Do not hand-edit generated result JSON files. Update the collector/builder and
  regenerate them when the user explicitly asks for new data.

