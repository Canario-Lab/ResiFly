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
- Do not hand-edit generated result JSON files. Update the collector/builder and
  regenerate them when the user explicitly asks for new data.

