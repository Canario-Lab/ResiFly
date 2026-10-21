# ResiFly

Prosta statyczna wyszukiwarka lotów między Teneryfą a Polską. Strona łączy
wyniki z plików `data/step1-results.json`, opcjonalnych wariantów
`data/step1b-results.json`, `data/step1c-results.json` i
`data/step1d-results.json`, `data/step2-results.json`,
`data/step3-results.json`, `data/step4-results.json` i
`data/step5-results.json` oraz
pozwala filtrować je po kierunku, cenie, dacie, lotnisku, miejscu przesiadki,
przewoźniku i czasie oczekiwania.

## Zbieranie danych

Kanoniczna instrukcja cotygodniowego wyszukiwania jest zapisana w pliku
[`docs/FIVE_STEP_FLIGHT_SEARCH.md`](docs/FIVE_STEP_FLIGHT_SEARCH.md). Zawiera
wspólne zasady, dokładnie pięć kroków wyszukiwania i wymagania dotyczące
wynikowych danych.

Publiczne JSON-y strony są generowane z aktualnych danych Binter, Ryanair,
Wizz Air, Google Flights dla Iberii/Iberii Express i Vuelinga, oficjalnego
feedu taryfowego Air Europa dla 1D oraz kursu NBP. W krokach 1B, 1C i 1D cena
rezydenta jest jawnym oszacowaniem 25% regularnej ceny odpowiedniego
przewoźnika. Air Europa nie korzysta z Google Flights. Wyniki
obejmują oba kierunki i nie mają limitu cenowego; maksymalną cenę wybiera
użytkownik na stronie.

```bash
python3 -m venv .venv
.venv/bin/pip install -r scripts/requirements-flight-collector.txt
.venv/bin/python scripts/collect_step1.py --days 30
.venv/bin/python scripts/collect_step1b.py --days 30
.venv/bin/python scripts/collect_step1c.py --days 30
.venv/bin/python scripts/collect_step1d.py --days 30
.venv/bin/python scripts/collect_step2.py --days 30
.venv/bin/python scripts/collect_step3.py --days 30
.venv/bin/python scripts/collect_step4.py --days 30
.venv/bin/python scripts/collect_step5.py --days 30
```

Generatory same zapisują `data/step1-results.json`, `data/step1b-results.json`,
`data/step1c-results.json`, `data/step1d-results.json`, `data/step2-results.json`,
`data/step3-results.json`, `data/step4-results.json` i
`data/step5-results.json`; plików wynikowych nie
należy poprawiać ręcznie.

## Dodawanie nowych lotnisk przesiadkowych

Kolektory są sterowane plikami danych, a nie wpisanymi na stałe lotniskami w
kodzie. Nowe lotnisko dodaje się do właściwej listy w `data/` razem ze strefą
czasową i regułą zniżki. Krok 1A przechowuje potrzebne dane tras Wizz Air w
`data/binter-transfer-airports.json`; kroki 4 i 5 korzystają ze wspólnego
rejestru `data/wizz-route-schedules.json`. Po uzupełnieniu tych danych nie
trzeba zmieniać kodu kolektora. Warianty 1B, 1C i 1D korzystają analogicznie z
`data/iberia-transfer-airports.json`, `data/vueling-transfer-airports.json` i
`data/air-europa-transfer-airports.json`;
listy zawierają wyłącznie trasy danego przewoźnika objęte zniżką rezydenta
Wysp Kanaryjskich. Dla 1C nadrzędnym źródłem siatki jest oficjalna strona
Vuelinga, a Aena służy tylko jako potwierdzenie pomocnicze.
Wariant 1D korzysta wyłącznie z oficjalnych stron i feedu Air Europa; zapisane
szablony rozkładu mają okres ważności i muszą zostać ponownie zweryfikowane po
jego zakończeniu.

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

Odcinki Iberii i Iberii Express otrzymują analogiczny, trwały link z trasą,
datą, liczbą pasażerów oraz kodem rezydenta Wysp Kanaryjskich. Link nie zawiera
tokenu ani danych sesji przeglądarki.

Odcinki Vuelinga otrzymują oficjalny podstawowy deeplink przewoźnika z trasą,
datą, pasażerami i parametrem zniżki rezydenta. Link również nie zawiera tokenu
ani danych sesji.

Odcinki Air Europa otrzymują oficjalny deeplink przewoźnika z trasą, datą,
liczbą pasażerów i kodem rezydenta `SPANISH_RESIDENT_RC`, zwracanym przez
publiczny endpoint Air Europa dla zapisanych tras. Strona ResiFly dodaje go
tylko wtedy, gdy filtr rezydenta jest zaznaczony, i usuwa go dla ceny
regularnej. Link nie zawiera klucza feedu, tokenu ani danych sesji.

Linki Ryanair są generowane analogicznie i prowadzą bezpośrednio do oficjalnego
ekranu wyboru lotu Ryanaira z ustawioną trasą i dokładnym dniem. Istniejące
pliki wynikowe można bez ponownego pobierania cen odświeżyć poleceniem:

```bash
.venv/bin/python scripts/refresh_booking_urls.py
```

## Uruchomienie lokalne

```bash
python3 -m http.server 4173
```

Następnie otwórz `http://localhost:4173`.
