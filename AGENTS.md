# ResiFly project rules

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

