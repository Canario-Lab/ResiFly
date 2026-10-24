# Lublin (LUZ) — lokalne wdrożenie

Status 24.10.2026: wdrożono lokalnie z kompletną nową bazą i backupem
poprzednich 20 plików. Następnie użytkownik osobno autoryzował wysłanie
całego pakietu na GitHub. Nie dodano workflow GitHub Actions.

## Zakres i trwała decyzja GDN

LUZ jest jedenastym polskim endpointem, strefa `Europe/Warsaw`.
Kanoniczny `data/search-airports.json` obejmuje wszystkie kolektory i discovery.
Zgoda użytkownika z 23.10.2026 jest trwała: GDN jako hub **wyłącznie 5B dla
KRK i LUZ**, także w kolejnych kolekcjach. Inne miasta, warianty i samotrasy
nie zostały odblokowane. Zapisano to w rejestrze, AGENTS i bieżącej procedurze.

Baseline: HEAD `8f9f1d0aa4ac58dbde5658bcb819037192dad06d`, branch
`codex/add-lodz-lcj`. Zastane zmiany README i plan LUZ zachowano.
`tmp/luz-expansion/baseline/` zawiera 110 plików kodu/konfiguracji/testów/docs/
strony i wszystkie 20 plików starej bazy. Manifest SHA-256 w katalogu nadrzędnym.
Stary run: `e0322930-e323-4c8c-9f08-459723852a72`, 15 407 propozycji.

## Świeży audyt całych sieci, nie tylko istniejących hubów

Oficjalne pełne sieci pobrane 23.10.2026:

- Ryanair LUZ: BGY, DUB, GDN, GRO, LTN, TPS.
- Wizz LUZ: BOJ, LTN, MST, RJK, SPU.

Przecięto je osobno z TFN/TFS obu przewoźników, przed ograniczeniem do dawnych
hubów. Brak nowego globalnego wspólnego IATA. MST, TPS, GRO, BOJ, RJK i SPU
nie mają wymaganej bezpośredniej nogi Teneryfy w obecnych sieciach Ryanair/Wizz;
nie łączono dawnych lub przyszłych sezonów i innych linii. GRO nie jest BCN,
LTN nie jest STN, BGY nie jest MXP. Nie dopisywano innych endpointów.

| Wariant | Zatwierdzone relacje LUZ |
| --- | --- |
| 1A Binter | brak; niezależna pełna macierz low-cost LUZ nadal obowiązuje |
| 1B Iberia | brak; niezależna pełna macierz low-cost LUZ nadal obowiązuje |
| 1C Vueling | brak |
| 1D Air Europa | brak |
| 1E Volotea | brak |
| 1F Canaryfly | brak |
| 2 | wszystkie LUZ/TFN/TFS, obie linie i kierunki, każda data |
| 3 Ryanair/Ryanair | BGY, DUB, LTN (TFS) |
| 4 Wizz/Wizz | brak |
| 5A Ryanair Teneryfa / Wizz Polska | LTN (TFS) |
| 5B Wizz Teneryfa / Ryanair Polska | GDN (TFS), ze stałą zgodą |

To lista tras do pełnego zebrania, nie obietnica dostępnych przesiadek w oknie.
Szczegółowe decyzje, raw intersections i statusy: `tmp/luz-expansion/route-decisions.json`.

### Źródła i ograniczenia rodzin rezydenckich

Jedyny hiszpański sąsiad low-cost LUZ to GRO. Osobno przejrzano wszystkie rodziny:

- [Binter — pełny katalog](https://www.bintercanarias.com/es/destinos): brak GRO.
  `timetable_get` zwrócił GraphQL E01000; snapshot zachowuje `failed`, nie pustą
  dostępność. Niezależny katalog rozstrzyga brak nowej kwalifikującej się trasy.
- [Iberia Tenerife/Madrid](https://www.iberia.com/es/vuelos-baratos/Tenerife-Madrid/)
  i lista operatora TFN potwierdzają MAD, nie GRO. Strona indeksu Iberia Express
  miała redirect loop; nie utożsamiono tego z zerem dostępności. Dodatkowa
  [lista portu GRO](https://www.aena.es/es/girona-costa-brava/aerolineas-y-destinos/destinos-aeropuerto.html)
  nie zawiera bezpośredniej Teneryfy.
- [Własne trasy Vuelinga z Teneryfy](https://www.vueling.com/es/vuelos-baratos-desde-tenerife):
  sprawdzono także huby spoza dawnych list; brak przecięcia LUZ, bez utożsamiania
  Girony z Barceloną. Aena nie zastępuje strony Vuelinga.
- [Air Europa](https://www.aireuropa.com/es-es/ofertas-de-vuelos-desde-tenerife):
  brak GRO w rynkach z Teneryfy; marketing lotów łączonych nie dowodzi direct.
- [Volotea](https://www.volotea.com/es/ofertas-vuelos/tenerife/): dynamiczna część
  strony nie jest dowodem braku. Opublikowane rynki i lista operatora TFS/GRO
  niezależnie nie dają pary do LUZ; nie aktywowano nowego huba.
- [Canaryfly](https://www.canaryfly.es/en/cheap-flights): siatka międzywyspowa
  nie przecina sieci LUZ; żadnych nowych relacji.

## Wizz i zachowanie dotychczasowej dziesiątki

38 indywidualnych obserwacji technicznych Google dla LUZ↔LTN: W92065/W92066.
24.10 czasy 165/160 min; późniejsze zegary 175/155 min. Każdy aktywny odlot
pełnego oficjalnego kalendarza LUZ/LTN (16/15) dopasowano do dokładnej obserwacji
data+godzina i resolvera, nie tylko najczęstszej wartości. GDN/TFS (5/6)
rozwiązuje istniejące zweryfikowane metadane. Brak aktywnych LUZ/TFN/TFS Wizz.
Audyt techniczny nie dostarcza cen do nowej bazy.

Wszystkie wcześniejsze rekordy uprawnień i schedule zachowano semantycznie;
usunięcie wyłącznie nowych relacji LUZ daje dokładny baseline dziesięciu.
Zachowano wyjątki WRO/LPA, POZ/LTN, RZE/FCO. Nie rozszerzono nowych hubów
ani TFN/TFS dla dawnych miast. Generator dziesięciu dokumentów jest idempotentny.

Pełny plan 24.10–23.11 (31 dat): 1A 8928, 1B 1488, 1C 3534, 1D 744,
1E 248, 1F bazowo 434 plus wymagane szczegóły, 2 2728, 3 11904, 4 1364,
5 5394. Wszystkie nogi obu przewoźników niezależnie; matching dopiero potem.

## Testy i odbiór

Przed kolekcją: 234 testy Python OK; 38 testów JS, 37 OK i jeden jawnie
oczekujący na prawdziwą bazę LUZ. Frozen TEN/SIX/SEVEN/EIGHT/NINE, dokładny
wyjątek GDN, pełne macierze 44/88 i route/day, nowe globalne syntetyczne huby
oraz prawdziwy executor, fail closed starego coverage, W9 i granice 120–1440.
Node i git diff check przechodzą. Po kolekcji wszystkie 38 JS przeszło na
stagingu bez pominięć; ponownie przeszło 234 Python. Test rzeczywistego LUZ
odtwarza jawny wybór lotniska po każdym share, który zgodnie z projektem
czyści ograniczenia lotnisk. Nie zmieniano przy tym kodu filtrów ani feedów.

Uruchomiono nowy pełny batch 24.10–23.11 po kanaryjskiej północy:
`f9323dee-9fdc-4e2f-8075-a39d53838115`, staging
`tmp/luz-expansion/batch-2026-10-24`. Hash zamrożonej konfiguracji:
`1c228017f91bfc513e85260967fb5746f69839e30888fd34453b300cb3bb7e75`.
Plan unii Ryanaira i rzeczywisty cache są identyczne: 18 104 unikalne poprawne
route/day, wyłącznie `google_flights_http`, bez starych ani dodatkowych wpisów.
Jeden zestaw NBP dla 24.10.2026, EUR/PLN 4.3917. Google max 2.
Cała kolekcja zakończyła się bez wznowienia, w kolejności 1A–1F, 2, 3, 4, 5.

| Feed | Wyniki | Kompletne pokrycie | LUZ |
| --- | ---: | ---: | ---: |
| 1A | 2884 | 8928 | 0 |
| 1B | 2252 | 1488 | 0 |
| 1C | 2946 | 3534 | 0 |
| 1D | 886 | 744 | 0 |
| 1E | 8 | 248 | 0 |
| 1F | 225 | 558 | 0 |
| 2 | 211 | 2728 | 0 |
| 3 | 5647 | 11904 | 39 |
| 4 | 218 | 1364 | 0 |
| 5 | 740 | 5394 | 8 |

Łącznie **16 017 propozycji**, **36 890 pozycji kompletnego pokrycia**,
zero missing/unexpected; dziesięć osadzonych raportów identycznych z sidecarami.
Wszystkie feedy mają jeden run, okno i kursy. Walidacja obejmuje chronologię,
pełne numery/godziny, sumy cen, 120–1440 min i trwałe linki zakupu per noga.

LUZ: **47 propozycji**, 23 Polska → Teneryfa, 24 powrotne. Krok 3: 39
(BGY 1, DUB 29, LTN 9). Krok 5A: 8 przez LTN. Krok 5B/GDN ma pełne
31 dni Ryanair w każdym kierunku, ale zero aktualnych lotów LUZ↔GDN,
więc nie tworzy wyników. Stała zgoda i zapis trasy zostają na przyszłość.
Brak bezpośrednich lotów LUZ jest wynikiem pełnej macierzy, nie pominięcia.
Przy domyślnych 1000 zł/6 h/rezydent/WDC off: 4 propozycje do Teneryfy,
0 powrotnych; zwiększenie filtrów udostępnia pozostałe z pełnej bazy.

## Lokalna promocja, HTTP i UI

Przed promocją potwierdzono, że publiczne 20 plików są identyczne z baseline.
Zachowano oryginalny `collection-complete-report.json` i osobny
`pre-promotion-acceptance-report.json`. Runner ponownie zwalidował całość
i podmienił wszystkie 20 plików, zachowując `previous-public-feeds/manifest.json`.
Po promocji: publiczne pliki są bajtowo identyczne ze stagingiem, a wszystkie
20 backupów z baseline. Ponowny `accept_batch.py` i walidacja zakończyły się
powodzeniem. Lokalny HTTP potwierdził aktualne bajty kodu i wszystkich
20 plików danych (22 sprawdzenia), wersję JS `20261024-luz-1` i nowy run.

Przeglądarka załadowała aktualizację 24.10, daty 24.10–23.11 i wszystkie
jedenaście checkboxów, w tym Lublin. Rzeczywisty wybór LUZ pokazał 4 domyślne
oferty z poprawnymi kwotami kalendarza/wykresu, numerami W92065 i FR3513.
Odbiór wizualny pełnego desktopu, komplet interakcji przy 320 px i systemowy
schowek nie zostały jeszcze ukończone; nie zastępuje ich test Node/HTTP.

Rollback wymaga spójnego przywrócenia kodu, rejestrów i całych 20 plików
z `tmp/luz-expansion/baseline/`, zachowując zastane zmiany planu/README.
Nie przywracać samych starych feedów pod konfiguracją jedenastu endpointów.
Nie wykonywano resetu, usuwania unrelated plików ani operacji force.
