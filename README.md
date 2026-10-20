# ResiFly

Prosta statyczna wyszukiwarka lotów między Teneryfą a Polską. Strona wczytuje
wyniki kroku 1 z pliku `data/step1-results.json` i pozwala filtrować je po
kierunku, cenie, dacie, lotnisku, miejscu przesiadki, przewoźniku i czasie
oczekiwania.

## Zbieranie danych

Kanoniczna instrukcja cotygodniowego wyszukiwania jest zapisana w pliku
[`docs/FIVE_STEP_FLIGHT_SEARCH.md`](docs/FIVE_STEP_FLIGHT_SEARCH.md). Zawiera
wspólne zasady, dokładnie pięć kroków wyszukiwania i wymagania dotyczące
raportów PDF.

Publiczny JSON strony jest generowany z aktualnych danych Binter, Ryanair,
Wizz Air oraz kursu NBP. Obejmuje oba kierunki i wyłącznie połączenia, których
łączna cena regularna jest niższa niż 1000 PLN. To osobna zasada od progu
raportów PDF.

```bash
python3 -m venv .venv
.venv/bin/pip install -r scripts/requirements-flight-collector.txt
.venv/bin/python scripts/collect_step1.py --days 30
```

Generator sam zapisuje `data/step1-results.json`; pliku wynikowego nie należy
poprawiać ręcznie.

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

## Uruchomienie lokalne

```bash
python3 -m http.server 4173
```

Następnie otwórz `http://localhost:4173`.
