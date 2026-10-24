# ResiFly

Prosta statyczna wyszukiwarka lotów między Teneryfą a Polską. Strona łączy
wyniki z plików `data/step1-results.json`, opcjonalnych wariantów
`data/step1b-results.json`, `data/step1c-results.json`,
`data/step1d-results.json`, `data/step1e-results.json` i
`data/step1f-results.json`, `data/step2-results.json`,
`data/step3-results.json`, `data/step4-results.json` i
`data/step5-results.json` oraz
pozwala filtrować je po kierunku, cenie, dacie, lotnisku, miejscu przesiadki,
przewoźniku i czasie oczekiwania.

## Zbieranie danych

Kanoniczna instrukcja cotygodniowego wyszukiwania jest zapisana w pliku
[`docs/FIVE_STEP_FLIGHT_SEARCH.md`](docs/FIVE_STEP_FLIGHT_SEARCH.md). Zawiera
wspólne zasady, dokładnie pięć kroków wyszukiwania i wymagania dotyczące
wynikowych danych.

Publiczne JSON-y strony są generowane z oficjalnych danych Bintera,
Wizz Air, Volotei i Canaryfly oraz Google Flights HTTP dla Ryanaira (FR/RK),
Iberii/Iberii Express, Vuelinga i Air Europa. Binter i Canaryfly zwracają
końcowe ceny regularne oraz rezydenckie. W krokach 1B–1E i uprawnionych
hiszpańskich odcinkach Teneryfy w 3–5 cena rezydenta jest jawnym szacunkiem:
pełne opłaty plus 25% pozostałej części taryfowej, nie 25% całej ceny.
Kursy pochodzą z jednego dziennego zestawu NBP. Volotea i Canaryfly nie
korzystają z Google Flights. Wyniki
obejmują oba kierunki i nie mają limitu cenowego; maksymalną cenę wybiera
użytkownik na stronie.

Każdy kolektor pobiera najpierw pełne skonfigurowane okno dat każdej zapisanej
trasy i każdej uczestniczącej linii w obu kierunkach. Dopiero potem porównuje
kalendarze i buduje przesiadki. Daty jednej linii nie są wstępnie ograniczane
rozkładem drugiej linii.

```bash
python3 -m venv .venv
.venv/bin/pip install -r scripts/requirements-flight-collector.txt
.venv/bin/python scripts/collect_step1.py --days 30
.venv/bin/python scripts/collect_step1b.py --days 30
.venv/bin/python scripts/collect_step1c.py --days 30
.venv/bin/python scripts/collect_step1d.py --days 30
.venv/bin/python scripts/collect_step1e.py --days 30
.venv/bin/python scripts/collect_step1f.py --days 30
.venv/bin/python scripts/collect_step2.py --days 30
.venv/bin/python scripts/collect_step3.py --days 30
.venv/bin/python scripts/collect_step4.py --days 30
.venv/bin/python scripts/collect_step5.py --days 30
```

Generatory same zapisują `data/step1-results.json`, `data/step1b-results.json`,
`data/step1c-results.json`, `data/step1d-results.json`,
`data/step1e-results.json`, `data/step1f-results.json`, `data/step2-results.json`,
`data/step3-results.json`, `data/step4-results.json` i
`data/step5-results.json`; plików wynikowych nie
należy poprawiać ręcznie.

## Dodawanie nowych lotnisk przesiadkowych

Polskie lotniska końcowe to WAW, WMI, KTW, KRK, GDN, WRO, POZ, LCJ, RZE, BZG, LUZ, SZY i RDO. Ich wspólny rejestr
`data/search-airports.json` jest odczytywany przez `scripts.search_airports`
zarówno w kolektorach, jak i detektorze. Zakres `scope.polish_airports`
każdej allowlisty musi odpowiadać temu rejestrowi. Dodanie endpointu wymaga
osobnego audytu siatki i zapisania konkretnych par lotnisko/przewoźnik;
nie oznacza dopisania go do wszystkich hubów. Historyczny plan Gdańska:
`docs/PLAN_DODANIA_GDANSKA_GDN.md`. Plan dodania Wrocławia (WRO)
jako szóstego endpointu jest zapisany w
[`docs/PLAN_DODANIA_WROCLAWIA_WRO.md`](docs/PLAN_DODANIA_WROCLAWIA_WRO.md).
WRO wdrożono lokalnie zgodnie z tym planem; zakres, wyniki i dowody zawiera
[`docs/WDROZENIE_WROCLAWIA_WRO.md`](docs/WDROZENIE_WROCLAWIA_WRO.md).
Pakiet WRO obejmuje konfigurację, kolektory, testy oraz komplet dziesięciu
odświeżonych feedów z raportami pokrycia.

Plan dodania Poznania (POZ) jako siódmego endpointu:
[`docs/PLAN_DODANIA_POZNANIA_POZ.md`](docs/PLAN_DODANIA_POZNANIA_POZ.md).
Lokalne wdrożenie POZ i odrębna pełna kolekcja są opisane w
[`docs/WDROZENIE_POZNANIA_POZ.md`](docs/WDROZENIE_POZNANIA_POZ.md).
Po pierwszym lokalnym odbiorze użytkownik osobno autoryzował 23.10.2026
publikację całego pakietu POZ i nowej bazy na GitHub.

Plan dodania Łodzi (LCJ) jako ósmego endpointu:
[`docs/PLAN_DODANIA_LODZI_LCJ.md`](docs/PLAN_DODANIA_LODZI_LCJ.md).
LCJ wdrożono lokalnie na osobne polecenie użytkownika. Nowa pełna kolekcja
dziesięciu feedów zawiera 15 030 propozycji, w tym 212 LCJ. Audyt uwzględnił
także zupełnie nowe huby; wyniki, testy i otwarty odbiór wizualny opisuje
[`docs/WDROZENIE_LODZI_LCJ.md`](docs/WDROZENIE_LODZI_LCJ.md).
Pierwszy odbiór odbył się bez commita i push. Następnie 23.10.2026 użytkownik
osobno autoryzował wysłanie całego pakietu LCJ i nowej bazy na GitHub.
Nie dodano workflow GitHub Actions.

Plan dodania Rzeszowa (RZE) jako dziewiątego endpointu:
[`docs/PLAN_DODANIA_RZESZOWA_RZE.md`](docs/PLAN_DODANIA_RZESZOWA_RZE.md).
RZE wdrożono wyłącznie lokalnie. Nowa pełna baza zawiera 15 268 propozycji,
w tym 279 RZE, z kompletnym pokryciem dziewięciu endpointów. Zakres, dowody
siatek, testy i otwarty odbiór wizualny/schowka opisuje
[`docs/WDROZENIE_RZESZOWA_RZE.md`](docs/WDROZENIE_RZESZOWA_RZE.md).
Pierwszy odbiór RZE odbył się bez commita i push. Następnie 23.10.2026
użytkownik osobno autoryzował publikację całego pakietu RZE i nowej bazy
na GitHub. Nie dodano workflow zbierania cen w GitHub Actions.

Plan dodania Bydgoszczy (BZG) jako dziesiątego endpointu:
[`docs/PLAN_DODANIA_BYDGOSZCZY_BZG.md`](docs/PLAN_DODANIA_BYDGOSZCZY_BZG.md).
BZG wdrożono lokalnie wraz z nową pełną bazą: 15 407 propozycji, w tym
187 BZG (95 Polska → Teneryfa, 92 powrotne), kompletne pokrycie dziesięciu.
Audyt siatek, próbek, testów, ponowień i promocji oraz otwarty odbiór
wizualny/schowka: [`docs/WDROZENIE_BYDGOSZCZY_BZG.md`](docs/WDROZENIE_BYDGOSZCZY_BZG.md).
Pierwszy odbiór odbył się bez commita i push. Następnie 23.10.2026 użytkownik
osobno autoryzował publikację całego pakietu BZG i nowej bazy na GitHub.
Nie dodano workflow zbierania cen w GitHub Actions.

Plan dodania Lublina (LUZ) jako jedenastego endpointu:
[`docs/PLAN_DODANIA_LUBLINA_LUZ.md`](docs/PLAN_DODANIA_LUBLINA_LUZ.md).
LUZ wdrożono lokalnie 24.10.2026 wraz z kompletną nową bazą: 16 017 propozycji,
w tym 47 LUZ (23 Polska → Teneryfa, 24 powrotne), kompletne pokrycie jedenastu
endpointów. Testy: 234 Python i 38 JS bez pominiętych; backup i HTTP sprawdzone.
Szczegóły i pozostały zakres odbioru wizualnego:
[`docs/WDROZENIE_LUBLINA_LUZ.md`](docs/WDROZENIE_LUBLINA_LUZ.md).
Po lokalnej promocji użytkownik osobno autoryzował publikację całego pakietu
LUZ i nowej bazy na GitHub. Bez zmian workflow zbierania cen.

Plan dodania Szyman (SZY) i Radomia (RDO), z jedenastu do trzynastu endpointów:
[`docs/PLAN_DODANIA_SZYMAN_I_RADOMIA_SZY_RDO.md`](docs/PLAN_DODANIA_SZYMAN_I_RADOMIA_SZY_RDO.md).
Obejmuje osobne audyty nowych przesiadek, nowy kandydat NRN dla SZY,
przypadek braku połączeń RDO oraz jeden wspólny pełny batch po wdrożeniu.
Użytkownik zatwierdził wdrożenie wyłącznie lokalne 24.10.2026; bez commita,
push i zmian workflow Actions. Wdrożono lokalnie oba endpointy i nowy hub NRN;
nowa pełna baza ma 15 954 propozycje, w tym 35 SZY przez STN. RDO i SZY↔NRN
nie mają teraz dostępnych dopasowań. Aby zobaczyć SZY, zwiększ limit przesiadki
z domyślnych 6 h do 24 h. Odbiór: 246 Python i 42 JS bez pominiętych, spójne
20 plików, backup, HTTP oraz prawdziwa strona i kopiowanie linku sprawdzone.
Szczegóły i ograniczenia:
[`docs/WDROZENIE_SZYMAN_I_RADOMIA_SZY_RDO.md`](docs/WDROZENIE_SZYMAN_I_RADOMIA_SZY_RDO.md).
Po lokalnym odbiorze użytkownik 24.10.2026 osobno autoryzował wysłanie całego
pakietu SZY/RDO, nowego NRN i aktualnej bazy na GitHub. Bez zmian workflow Actions.

GDN ma stałą zgodę na rolę przesiadki wariantu 5B dla KRK i LUZ, także
w przyszłych kolekcjach (decyzja 23.10.2026). Rejestr zawiera
precyzyjny wyjątek, który nie dopuszcza odcinków GDN–GDN.

Cały zestaw można zebrać lokalnie do stagingu, z jednym dniem i cache NBP:

```bash
.venv/bin/python scripts/collect_five_steps.py --from-date 2026-10-22 --days 30 --stage-directory tmp/flight-batch --workers 4
.venv/bin/python scripts/collect_five_steps.py --from-date 2026-10-22 --days 30 --stage-directory tmp/flight-batch --validate-only --promote
```

Datę w przykładzie zastąpić dniem uruchomienia w `Atlantic/Canary`.
Druga komenda waliduje wszystkie dziesięć feedów przed lokalną podmianą i
zachowuje ich poprzedni komplet w stagingu. Sprawdza też wspólne okno, dzienne
kursy, unikalność ID i poprawność odcinków. Błąd podmiany przywraca poprzedni
komplet; nie jest to pojedyncza atomowa operacja na wszystkich plikach.
Skrypt nie wykonuje żadnej operacji Git.
Zweryfikowane dane Wizz dla bezpośrednich i przesiadkowych lotów czyta wspólny
loader `scripts/wizz_schedules.py`; lokalne rejestry 1A/1B pozostają w allowlistach.
Ryanair w wariantach 1A–1F używa tego samego pełnego kalendarza co krok 2;
zapytanie Fare Finder o najtańszą ofertę z całego miesiąca nie zastępuje
pełnego skanu dat. Także minimum dzienne nie obejmuje wszystkich godzin.
Aktualne numery, godziny i indywidualne ceny Ryanaira pochodzą wyłącznie
z Google Flights HTTP, dla wszystkich dni zapisanych tras, z kodami FR/RK.
Błąd źródła przerywa aktualizację; nie ma powrotu do starego API cenowego.

Każdy kolektor wymaga raportu `collection_coverage` dla wszystkich zapisanych
tras/dni, także przy uruchomieniu samodzielnym. Obok feedu zapisuje
`step*-results.collection-report.json`; błąd Bintera (również GraphQL przy
HTTP 200) nie może udawać braku lotów. Batch dopuszcza tylko komplet dziesięciu
feedów z tego samego `run_id` i zgodnymi raportami. Stare feedy bez raportów
pozostają wyświetlane, ale nie przejdą ponownej promocji bez nowego pobrania.
Wznowienie wybranych kroków wymaga `--run-id` z raportu pierwotnego batcha.
Opis działania i ograniczeń: `docs/COLLECTION_RELIABILITY.md`.

Testy bez pobierania cen:

```bash
.venv/bin/python -m unittest discover -s tests
node --test tests/test_airport_ui.mjs
```

Testy JavaScript sprawdzają produkcyjną logikę strony na lokalnych feedach,
ale nie zastępują wizualnej kontroli w przeglądarce.
Raport wdrożenia GDN: `docs/WDROZENIE_GDANSKA_LOKALNIE.md`.

Kolektory są sterowane plikami danych, a nie wpisanymi na stałe lotniskami w
kodzie. Nowe lotnisko dodaje się do właściwej listy w `data/` razem ze strefą
czasową i regułą zniżki. Krok 1A przechowuje potrzebne dane tras Wizz Air w
`data/binter-transfer-airports.json`; kroki 4 i 5 korzystają ze wspólnego
rejestru `data/wizz-route-schedules.json`. Po uzupełnieniu tych danych nie
trzeba zmieniać kodu kolektora. Warianty 1B, 1C, 1D, 1E i 1F korzystają analogicznie z
`data/iberia-transfer-airports.json`, `data/vueling-transfer-airports.json` i
`data/air-europa-transfer-airports.json` oraz
`data/volotea-transfer-airports.json` i
`data/canaryfly-transfer-airports.json`;
listy zawierają wyłącznie trasy danego przewoźnika objęte zniżką rezydenta
Wysp Kanaryjskich. Dla 1C nadrzędnym źródłem siatki jest oficjalna strona
Vuelinga, a Aena służy tylko jako potwierdzenie pomocnicze.
Warianty 1A–1F sprawdzają pełne okno dat w obu kierunkach,
niezależnie od rozkładu drugiego przewoźnika, i dopiero potem dopasowują
możliwe przesiadki. Wariant 1D weryfikuje trasy na oficjalnych stronach Air
Europa, lecz numery rejsów, daty, godziny i indywidualne ceny pobiera wyłącznie
z Google Flights HTTP. Nie używa szablonów ani promocyjnego minimum dnia.
Wariant 1E pobiera rozkład, numer lotu i cenę bezpośrednio z oficjalnego
publicznego endpointu Volotei, osobno dla każdego dnia pełnego okna dat i w obu
kierunkach; dopiero potem dopasowuje możliwe przesiadki.
Wariant 1F pobiera pełne miesięczne kalendarze oraz szczegóły dostępnych dni z
oficjalnego GraphQL Canaryfly. Przewoźnik zwraca osobno cenę regularną i
rezydencką dla konkretnego lotu.

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

Odcinki Volotei otrzymują oficjalny link do właściwej trasy i dnia, bez tokenu
ani danych sesji. Publiczny format URL Volotei nie ma obsługiwanego parametru
zniżki rezydenta, dlatego status rezydenta trzeba potwierdzić w selektorze
pasażerów na stronie przewoźnika.

Odcinki Canaryfly otrzymują oficjalny link do właściwej trasy i dnia, bez
tokenu ani danych sesji. Wybór ceny rezydenckiej lub regularnej pozostaje w
interfejsie przewoźnika.

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
