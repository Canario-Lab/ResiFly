# ResiFly

Prosta statyczna wyszukiwarka lotów między Teneryfą a Polską. Strona łączy
wyniki z plików `data/step1-results.json`, `data/step2-results.json`,
`data/step3-results.json` i `data/step4-results.json` oraz
pozwala filtrować je po kierunku, cenie, dacie, lotnisku, miejscu przesiadki,
przewoźniku i czasie oczekiwania.

## Zbieranie danych

Kanoniczna instrukcja cotygodniowego wyszukiwania jest zapisana w pliku
[`docs/FIVE_STEP_FLIGHT_SEARCH.md`](docs/FIVE_STEP_FLIGHT_SEARCH.md). Zawiera
wspólne zasady, dokładnie pięć kroków wyszukiwania i wymagania dotyczące
wynikowych danych.

Publiczne JSON-y strony są generowane z aktualnych danych Binter, Ryanair,
Wizz Air oraz kursu NBP. Obejmują oba kierunki i nie mają limitu cenowego;
maksymalną cenę wybiera użytkownik na stronie.

```bash
python3 -m venv .venv
.venv/bin/pip install -r scripts/requirements-flight-collector.txt
.venv/bin/python scripts/collect_step1.py --days 30
.venv/bin/python scripts/collect_step2.py --days 30
.venv/bin/python scripts/collect_step3.py --days 30
.venv/bin/python scripts/collect_step4.py --days 30
```

Generatory same zapisują `data/step1-results.json`, `data/step2-results.json`,
`data/step3-results.json` i `data/step4-results.json`; plików wynikowych nie
należy poprawiać ręcznie.

## Linki do zakupu Wizz Air

Każdy odcinek Wizz Air zapisywany w wynikowym JSON-ie musi zawierać pole
`booking_url`. Link jest generowany z lotniska wylotu, lotniska przylotu i daty
przez funkcję `scripts.booking_urls.wizz_booking_url`. Nie zależy od sesji
przeglądarki i nie może zawierać cookies ani tymczasowych tokenów.

Przykład:

```json
{
  "carrier": "Wizz Air",
  "flight_number": "W61474",
  "departure_airport": "MAD",
  "departure_at": "2026-11-17T19:15:00+01:00",
  "arrival_airport": "WAW",
  "booking_url": "https://www.wizzair.com/en-gb/booking/select-flight/MAD/WAW/2026-11-17/null/1/0/0/null"
}
```

Adres otwiera właściwą trasę i dzień. Numer lotu nie jest częścią adresu, więc
jeżeli tego samego dnia dostępnych jest kilka lotów, użytkownik wybiera właściwy
po godzinie.

Linki Ryanair są generowane analogicznie, ale prowadzą do oficjalnego Fare
Finder Ryanaira z ustawioną trasą i dokładnym dniem. Ten ekran jest stabilniejszy
od bezpośredniego widoku zakupu, który potrafi zatrzymać się na pustym wyniku.
Istniejące pliki wynikowe można bez ponownego pobierania cen odświeżyć poleceniem:

```bash
.venv/bin/python scripts/refresh_booking_urls.py
```

## Uruchomienie lokalne

```bash
python3 -m http.server 4173
```

Następnie otwórz `http://localhost:4173`.
