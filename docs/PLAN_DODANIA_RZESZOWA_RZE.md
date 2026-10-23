# Plan dodania Rzeszowa (RZE) jako dziewiątego polskiego lotniska ResiFly

Dokument wykonawczy do późniejszej realizacji przez Codexa. Przygotowany
**23 października 2026 r.** na podstawie repozytorium w commicie
`b2c5f2b7c1612cb507de958720f8d0aebb5e59de`, po wdrożeniu Łodzi i filtra
wielokrotnego wyboru polskich lotnisk. Bieżący checkout:
`codex/add-lodz-lcj`; nie zakładać, że lokalna gałąź `main` wskazuje ten stan.

**Status: kod, konfiguracja i nowa baza wdrożone lokalnie 23.10.2026 na
osobne polecenie użytkownika; odbiór wizualny/schowka otwarty. Publikacja
GitHub osobno autoryzowana 23.10.2026 po lokalnym odbiorze.** Stan i wyniki:
[`WDROZENIE_RZESZOWA_RZE.md`](WDROZENIE_RZESZOWA_RZE.md). Przygotowanie tego
dokumentu nie obejmowało audytu żywych siatek RZE, pobierania nowych kalendarzy,
repricingu, zmiany konfiguracji, promocji bazy ani operacji Git. Obecne huby
podane niżej nie są potwierdzonymi połączeniami z Rzeszowa.

Wiążące pozostają `AGENTS.md`, `docs/FIVE_STEP_FLIGHT_SEARCH.md` i
`docs/COLLECTION_RELIABILITY.md`. Wcześniejsze zgody na publikację LCJ lub
filtra lotnisk nie obejmują RZE. Wdrożenie lokalne otrzymało osobną zgodę,
a po jego zakończeniu użytkownik osobno polecił wysłanie RZE na GitHub.

## 1. Cel i granice zmiany

Docelowa kolejność endpointów:
**WAW, WMI, KTW, KRK, GDN, WRO, POZ, LCJ, RZE**. Nowy wpis rejestru:

```json
{ "iata": "RZE", "name_pl": "Rzeszów", "timezone": "Europe/Warsaw" }
```

Obsłużyć RZE → TFN/TFS i TFN/TFS → RZE: bezpośrednio lub z jedną przesiadką,
we wszystkich dopuszczonych kombinacjach linii. Sprawdzić **pełne siatki**,
a nie tylko miasta przesiadkowe używane obecnie. Nie dopisywać RZE hurtem do
istniejących hubów. Nie deklarować istnienia lotu na podstawie samej nazwy
miasta w wyszukiwarce, historycznej trasy lub szablonu kalendarza.

Zachować następujące reguły:

- Dokładnie **pięć głównych kroków**, warianty 1A–1F i **dziesięć feedów**.
- Pełne, niezależnie zaplanowane kalendarze każdego zapisanego odcinka,
  każdej uczestniczącej linii i obu kierunków. Dopasowanie dopiero po ich
  zebraniu; żadnego zawężania dni jednej linii do dni zwróconych przez drugą.
- `--days 30` to dzień startu i 30 kolejnych dni, czyli **31 dat włącznie**.
  Odloty obu odcinków muszą mieścić się w oknie. Nie zmieniać tej semantyki.
- Jedna przesiadka na tym samym **lotnisku IATA**, 120–1440 minut włącznie,
  poprawna chronologia po przeliczeniu stref czasowych, także nocą i przy DST.
- Wyjątek GDN jako przesiadki pozostaje wyłącznie **5B do KRK**. Nie dopuszczać
  go do RZE, nie robić RZE nowym hubem i nie tworzyć RZE–RZE.
- Dane bez limitu cenowego; na stronie nadal Polska → Teneryfa, maksymalnie
  1000 zł, przesiadka do 6 godzin i sortowanie „najbliższy termin”.
- Oddzielne ceny regularne, rezydenckie i WIZZ Discount Club, bez zmiany ID
  istniejących wyników ani znaczenia linków udostępniania.
- Jeden dzienny zestaw kursów NBP dla całego batcha. Wszystkie zapytania
  Google Flights HTTP, również ponowienia, maksymalnie dwa jednocześnie.
- Binter i Canaryfly: oficjalne końcowe kwoty do zapłaty, nie ceny netto/listy.
  Pozostałe uprawnione odcinki: właściwy jawny szacunek z opłatami.
- Każdy odcinek z trwałym linkiem zakupu, bez tokenów, cookies i danych sesji.
- Zachować uprawnienia starej ósemki. Na tych samych zamrożonych wejściach
  dotychczasowe wyniki, ich ID i ceny mają być identyczne. Nowe pobranie może
  oczywiście zmienić rzeczywistą dostępność i ceny.

## 2. Zweryfikowany punkt wyjścia

Rejestr i `scope.polish_airports` dziewięciu allowlist zawierają obecnie osiem
endpointów. RZE nie występuje w tych plikach, technicznych trasach Wizz,
etykietach `app.js` ani jako endpoint w obecnych wynikach.

Przy przygotowaniu planu obecna baza przeszła `validate_batch` dla okna
**2026-10-23–2026-11-22**, run ID
**`a6f8a0e8-f295-4f20-984e-74607fc6cb08`**. Wszystkie dziesięć sidecarów jest
zgodnych z raportami w feedach. Łącznie **15 030 propozycji** i **32 178
ukończonych pozycji pokrycia**. To historyczny baseline tego planu, nie
prognoza wyniku RZE i nie potwierdzenie aktualności cen w dniu realizacji.

| Feed | Wyniki | Bazowy plan route/day | Kompletne pokrycie |
| --- | ---: | ---: | ---: |
| 1A (`step1`) | 2804 | 6696 | 6696 |
| 1B | 2179 | 1116 | 1116 |
| 1C | 2852 | 3410 | 3410 |
| 1D | 853 | 744 | 744 |
| 1E | 8 | 248 | 248 |
| 1F | 220 | 434 | 558 |
| 2 | 205 | 1984 | 1984 |
| 3 | 5011 | 10974 | 10974 |
| 4 | 199 | 1302 | 1302 |
| 5 | 699 | 5146 | 5146 |

1F zawiera dodatkowo 124 wymagane sprawdzenia szczegółów dostępnych dni.
Pokrycie nie jest liczbą requestów HTTP: Ryanair współdzieli cache, Wizz
pobiera okresy, a Canaryfly pełne miesiące i następnie szczegóły.

Liczba propozycji per endpoint: WAW 1993, WMI 1908, KTW 785, KRK 5092,
GDN 1974, WRO 2251, POZ 815, LCJ 212. Dodatkowo siedem propozycji używa
GDN jako transferu; nie wliczać tej roli jako kolejnego endpointu podróży.

Testy bazowe wykonane bez pobierania nowych kalendarzy: **196 testów Python
i 26 testów JavaScript, wszystkie poprawne**. Komunikaty źródeł drukowane
przez testy korzystające z mocków nie stanowią dowodu pobrania nowych cen.

### Obecne listy hubów — wyłącznie baseline audytu

| Wariant | Aktualne huby |
| --- | --- |
| 1A Binter | FUE, LPA, MAD, PMI, SVQ, VLC |
| 1B Iberia/Express | MAD |
| 1C Vueling | ALC, BCN, BIO, AGP, SCQ, SVQ, VLC |
| 1D Air Europa | MAD, BIO |
| 1E Volotea | BIO |
| 1F Canaryfly | FUE, LPA |
| 3 Ryanair/Ryanair | AGA, AGP, BGY, BHX, BLQ, BOH, BRS, BUD, BVA, CRL, DUB, EDI, EIN, EMA, FCO, FMM, LBA, LPL, LTN, MAN, MRS, MXP, NAP, NCL, OPO, PSA, RAK, SNN, STN, SVQ, TLS, TSF, VIE, VLC |
| 4 Wizz/Wizz | BBU, BUD, FCO, MXP, OTP, SCQ |
| 5A Ryanair na Teneryfie / Wizz na Polsce | AGA, AGP, BGY, BLQ, BUD, CRL, EIN, FCO, LBA, LPL, LTN, MXP, NAP, OPO, PSA, RAK, SCQ, SVQ, VLC |
| 5B Wizz na Teneryfie / Ryanair na Polsce | BBU, BUD, FCO, GDN, MXP, OTP |

Nie traktować tej tabeli jako listy ograniczającej wyszukiwanie RZE. Nowy hub
może nie występować w żadnym wierszu. Wynik „brak tras” wymaga kompletnego
audytu źródła; awaria lub niesprawdzone źródło oznacza „nie ustalono”.

## 3. Mapa plików i odpowiedzialności

| Obszar | Pliki i wymagane działanie |
| --- | --- |
| Endpointy | `data/search-airports.json`, `scripts/search_airports.py`: dopisać RZE tylko do danych, utrzymać wspólny loader i precyzyjny wyjątek GDN. |
| Zasady | `AGENTS.md`, `docs/FIVE_STEP_FLIGHT_SEARCH.md`, `docs/COLLECTION_RELIABILITY.md`, `README.md`: aktualny zakres dziewięciu, poprawne źródła i instrukcja odbioru. |
| Audyt | `scripts/audit_airport_expansion.py`, `scripts/discover_transfer_routes.py`: pełne przecięcia siatek, nowe huby, jawne awarie/pending, przegląd tylko zmian RZE. |
| Konfiguracja | `scripts/build_gdn_config_patch.py`: używać jawnego `--endpoint RZE`, nie zmieniać domyślnego GDN; uzupełnić opisane niżej luki. |
| Wizz | `scripts/verify_wizz_expansion_schedules.py`, `scripts/wizz_schedules.py`, `scripts/wizz_api.py`, `data/wizz-route-schedules.json`, lokalne wpisy 1A/1B: pokryć każdy nowy aktywny odcinek i wszystkie warianty godzin. |
| 1A–1F | Sześć plików `data/*transfer-airports.json` przewoźników rezydenckich i `scripts/collect_step1*.py`: osobny audyt siatek, pełne kalendarze, właściwe źródła i ceny. |
| 2 | `scripts/collect_step2.py`: pełna macierz dziewięciu polskich endpointów z TFN/TFS i obiema liniami. |
| 3–5 | `data/ryanair-transfer-airports.json`, `data/wizzair-transfer-airports.json`, `data/mixed-transfer-airports.json`, kolektory 3–5: tylko zweryfikowane uprawnienia RZE i nowe huby. |
| Opłaty i linki | `data/spanish-resident-fees.json`, `scripts/spanish_resident_fees.py`, `scripts/booking_urls.py`: brak duplikacji opłat i brak URL sesyjnych. |
| Kompletność | `scripts/collection_coverage.py`, `scripts/collect_five_steps.py`, `scripts/collector_settings.py`: niezależny plan, wspólny batch, limit Google i promocja całego kompletu. |
| Strona | `app.js`, ewentualnie `index.html`/`styles.css`: etykieta RZE, obecny multiselect, kalendarz/wykres/karty/share, bez przebudowy pozostałych filtrów. |
| Testy | `tests/test_rze_expansion.py` do dodania; istniejące testy endpointów, źródeł, discovery, Wizz, coverage i `tests/test_airport_ui.mjs` do rozszerzenia. |
| Wynik | Dziesięć `data/step*-results.json` i dziesięć `.collection-report.json`, generowane wyłącznie przez kolektory; raport `docs/WDROZENIE_RZESZOWA_RZE.md`. |

To mapa do przeglądu, nie nakaz zmiany każdego pliku kodu. Większość
kolektorów jest już sterowana danymi; zmieniać implementację tylko tam, gdzie
audyt i test wykazują rzeczywistą lukę. Nie wykonywać globalnej zamiany
„osiem” na „dziewięć”: istnieje osiem rodzajów sortowania, historyczne raporty
i zamrożone zestawy wcześniejszych endpointów.

## 4. Etap A — zabezpieczenie stanu i decyzja o zakresie

Wykonać dopiero po poleceniu wdrożenia RZE:

1. Ponownie odczytać aktualne instrukcje, status/diff Git, HEAD, gałąź,
   rejestry i raporty. Ten plan jest oparty na konkretnym stanie, który może
   później ulec zmianie. Chronić niezwiązane zmiany użytkownika.
2. Zapisać w `tmp/rze-expansion/baseline/` kopię konfiguracji, technicznych
   rozkładów, opłat, kodu/testów oraz obecnych 20 plików feedów i sidecarów.
   Zachować również `app.js`, `index.html`, `styles.css` z multiselectem,
   instrukcje, SHA-256 i ID bieżącego batcha. Nie opierać rollbacku wyłącznie
   na Git: późniejsze lokalne zmiany mogą nie być commitowane.
3. Zbudować zamrożone wejścia do porównania starej ósemki; oddzielić test
   braku regresji od porównania dwóch pobrań z różnymi aktualnymi cenami.
4. Ustalić dzień startu według `Atlantic/Canary`. We wszystkich poleceniach
   użyć jawnego dnia i wspólnego `--days 30`, nie daty historycznej z planu.
5. W docelowym etapie dodać RZE do `search-airports.json`, bez ruszania
   wyjątku GDN. Uruchamiać narzędzia w nowych procesach: stałe endpointów są
   ładowane przy imporcie. Przed tym krokiem CLI nie przyjmuje `--endpoint RZE`.
6. Traktować konfigurację dziewięciu endpointów i stare feedy ośmiu jako stan
   przejściowy, a nie ukończone wdrożenie. Stare dane nadal mogą być czytane
   przez stronę, ale nie przejdą certyfikacji jako pełna nowa baza RZE.

Nie robić na tym etapie commita, push, nowego workflow ani automatycznej
promocji. Jeśli potrzebna jest nowa gałąź, domyślny prefiks to `codex/`;
nie zakładać, że wcześniejsza gałąź LCJ jest nazwą wdrożenia RZE.

## 5. Etap B — pełny audyt siatek, również zupełnie nowych przesiadek

### 5.1. Snapshot i zakres dowodu

Po dopisaniu endpointu uruchomić audyt do katalogu roboczego:

```bash
.venv/bin/python scripts/audit_airport_expansion.py --endpoint RZE --as-of YYYY-MM-DD --output-directory tmp/rze-expansion
.venv/bin/python scripts/discover_transfer_routes.py --as-of YYYY-MM-DD --snapshot tmp/rze-expansion/network-snapshot.json --report tmp/rze-expansion/discovery-report.json
```

Powyższe to szablony do przyszłego uruchomienia: zastąpić `YYYY-MM-DD`.
Detector działa bez `--apply`. Nie uruchamiać go jako części zwykłej
późniejszej aktualizacji cen. Nie ograniczać snapshotu do starych hubów.

Audyt zapisuje oficjalne siatki Ryanaira i Wizza, a następnie sprawdza Bintera
dla sąsiadów nowego endpointu. Gdy Binter zawiedzie, snapshot low-cost i status
błędu należy zachować, lecz nie przedstawiać pustej sekcji jako braku tras.
`--low-cost-only` oznacza Binter **niesprawdzony**, nie gotowy kompletny audyt.
Brakujące źródło zweryfikować niezależnie u przewoźnika albo zgłosić blocker.

### 5.2. Niezależne przecięcia siatek podstawowych

Sprawdzić zbiory wszystkich wspólnych lotnisk, dla TFN i TFS oddzielnie:

| Krok | Odcinek geograficzny Teneryfa ↔ hub | Odcinek hub ↔ RZE |
| --- | --- | --- |
| 1A | Binter | Ryanair lub Wizz Air |
| 3 | Ryanair | Ryanair |
| 4 | Wizz Air | Wizz Air |
| 5A | Ryanair | Wizz Air |
| 5B | Wizz Air | Ryanair |

Numery 5A i 5B to warianty kroku 5. Przy odwróceniu podróży przewoźnik
pozostaje przypisany do tej samej geograficznej części, a nie do kolejności
odcinków. Brak Wizza w RZE nie wyklucza 5B z Ryanairem po polskiej stronie.

`discover_candidates` szuka przecięć pełnych grafów przed filtrowaniem przez
stare allowlisty. Nie wystarczy jednak stwierdzić, że narzędzie „to umie”:
zachować jego faktyczny snapshot i raport dla RZE, a potem doprowadzić każdą
zaakceptowaną kandydaturę do konfiguracji, planu zapytań i odbioru pokrycia.
Opublikowana krawędź w jednej orientacji nie zwalnia z pobrania obu kierunków.

Dla każdej kandydatury zapisać w tabeli decyzji:

- wariant, dokładne IATA huba i lotniska Teneryfy, parę linii i kierunki;
- źródła oficjalne z datą, status sezonowy i stan w wybranym oknie;
- czy to nowe uprawnienie RZE w starym hubie, hub nowy dla wariantu, czy hub
  **zupełnie nowy dla całej aplikacji** (porównać unię wszystkich dziewięciu list);
- czy pojawia się nowe TFN/TFS w istniejącym hubie, strefę IANA i zniżkę;
- status `ready`, `pending` lub `rejected` z konkretnym uzasadnieniem;
- docelowy rekord allowlisty, wymagane dane Wizz i opłaty oraz plan kalendarzy.

Nie utożsamiać BVA z ORY/CDG, BGY z MXP, STN z LTN ani BBU z OTP. Dwie linie
latające „do Paryża” nie tworzą przesiadki, jeśli używają innych lotnisk.
Nie tworzyć podróży z dodatkowym dojazdem ani drugim transferem.

### 5.3. Osobny audyt 1A–1F poza standardowym detectorem

Detector nie uzupełnia sam 1B–1F. Dla każdej linii sprawdzić całą odpowiednią
siatkę Teneryfy i jej przecięcie z pełnymi połączeniami low-cost RZE, także
przez huby nieobecne obecnie w jej allowliście:

| Wariant | Nadrzędny dowód siatki i ograniczenie |
| --- | --- |
| 1A Binter | Oficjalne destynacje/rozkłady Bintera, prawdziwy odcinek i uprawnienie rezydenckie; nie uznać błędu API za brak połączeń. |
| 1B Iberia/Express | Oficjalna siatka Iberii/Iberia Express i uprawnione połączenie z Teneryfą; nie tylko dotychczasowy MAD. |
| 1C Vueling | Oficjalna strona tras Teneryfy Vuelinga jest podstawą; Aena jedynie potwierdza. |
| 1D Air Europa | Oficjalne strony tras i potwierdzenie operowanego bezpośredniego odcinka; dane rejsów i ceny wyłącznie Google HTTP. |
| 1E Volotea | Oficjalna strona trasy i publiczny MinPrice; brak Google Flights. |
| 1F Canaryfly | Oficjalne bezpośrednie trasy i GraphQL calendar/search; brak Google Flights. |

Wszystkie 1A–1F wymagają kwalifikacji do zniżki rezydenta. Zagraniczny hub
może kwalifikować się do 3–5 bez zniżki, a nie do 1A–1F. Sama strona
marketingowa pary miast nie jest dowodem bezpośredniego rejsu danej linii.

Jeżeli nie ma żadnego kwalifikującego połączenia RZE w danym wariancie,
udokumentować wynik i nie dopisywać fikcyjnej trasy. Wariant nadal pozostaje
w pełnym batchu dla innych lotnisk. Zero połączeń po dopasowaniu godzin może
być prawidłowe mimo istnienia obu tras; awaria źródła nigdy nie jest takim zerem.

### 5.4. Przegląd decyzji przed zastosowaniem

Podsumować wszystkie pięć kroków i sześć wariantów kroku 1, z liczbą nowych
hubów i uprawnień. Nie używać globalnego `--apply` bez przeglądu: raport może
zawierać niezwiązane nowe trasy starej ósemki. Zatwierdzone zmiany dotyczące
RZE oddzielić od ewentualnego osobnego rozszerzenia siatki pozostałych miast.
Plan nie zatwierdza z góry żadnej trasy ani zmiany allowlisty.

## 6. Etap C — kompletne dane techniczne Wizz

Każdy nowy zapisany aktywny odcinek Wizz wymaga zweryfikowanego numeru lotu,
blokowego czasu lotu i prawidłowej strefy obu lotnisk w obu kierunkach.
Oficjalny kalendarz podaje aktualne daty, odloty i ceny regularne/WDC, ale nie
zastępuje technicznego rejestru numerów i przylotów.

```bash
.venv/bin/python scripts/verify_wizz_expansion_schedules.py --endpoint RZE --snapshot tmp/rze-expansion/network-snapshot.json --from-date YYYY-MM-DD --days 30 --output tmp/rze-expansion/verified-wizz-schedules.json
```

Przed użyciem tego wyniku przetestować i sprawdzić zakres `required_routes`:
narzędzie obejmuje cztery skierowane pary RZE–TFN/TFS, polskie odcinki 4/5A
i hiszpańskich sąsiadów RZE. Ponowny przegląd przy wdrożeniu wykazał, że
obsługa brakujących w rejestrze odcinków **Teneryfa–hub Wizz w 4 i 5B**
już istnieje i ma test z wdrożenia LCJ; nie wymaga ponownej implementacji.
Test zachować, a kompletność zestawu wymaganego sprawdzić względem
wszystkich zaakceptowanych kandydatur 1A–1F, 2, 4 i obu wariantów 5.

Wymagania odbioru technicznego:

1. Dla każdego aktywnego odlotu z oficjalnego kalendarza istnieje właściwa
   obserwacja techniczna. Nie poprzestać na jednym dniu lub godzinie trasy.
2. Zachować obsługę kodów W6/W4/W9 i zmian rozkładu. Priorytet rozstrzygnięć:
   data+godzina, dzień tygodnia+godzina, godzina, bazowy wpis trasy.
3. Konflikt numeru lub czasu przy tej samej godzinie rozwiązać dowodem, a nie
   wyborem pierwszej/najczęstszej obserwacji. Używać istniejących pól
   `flight_number_overrides_by_departure_date_and_time` oraz
   `flight_number_overrides_by_departure_weekday_and_time`.
4. Rejestr wspólny oraz lokalne wpisy 1A/1B mają rozwiązywać te same trasy
   identycznie przez `scripts.wizz_schedules`. Zachować istniejące wyjątki,
   w szczególności WRO–LPA oraz datowe/godzinowe POZ–LTN.
5. Wznowienie pliku dowodowego tylko dla tego samego endpointu, snapshotu,
   dat i pełnego okna. Nie przenosić dowodów LCJ/POZ pod nazwę RZE.
6. `--inactive-probe-date` może pomóc ustalić techniczny rozkład sezonowy;
   ceny i loty z tej daty nie trafiają do bieżącego okna. Trasa bez danych
   technicznych pozostaje `pending`, nie staje się aktywna przez zgadywanie.
7. Obecna flaga `--complete-times` jest zadeklarowana, lecz sama nie realizuje
   dodatkowej ścieżki kompletności w `main`; nie traktować jej jako dowodu.

Do aktualnych cen Wizza nadal używać oficjalnego timetable i istniejącego
resolvera wersji API w `scripts.wizz_api`, nie wpisywać nowego numeru API na
sztywno. Techniczne zapytania Google również respektują limit dwóch; nie
uruchamiać kilku niezależnych procesów omijających wspólny limit procesu.

## 7. Etap D — konfiguracja dziewięciu endpointów

### 7.1. Scope, wykluczenia i uprawnienia

We wszystkich dziewięciu allowlistach ustawić `scope.polish_airports` zgodnie
z rejestrem dziewięciu endpointów, także gdy dany wariant nie ma trasy RZE.
Nie jest to równoznaczne z uprawnieniem RZE do każdego huba.

- 1A/1B: zachować metadane lotnisk, strefy, lotniska Teneryfy i uprawnienia
  rezydenckie oraz lokalne wpisy Wizz. Ich kolektory low-cost planują pełną
  macierz hub × endpoint × obie linie × oba kierunki; nie zawężać jej do dni
  lub przewoźników znalezionych w innej części kolekcji.
- 1C–1F: dopisywać zweryfikowane pary `polish_airport: RZE` + `airlines`
  w `polish_routes`, wyłącznie w odpowiednich rekordach hubów.
- 3/4: dopisywać RZE do `polish_airports` tylko potwierdzonych hubów, dodawać
  nowe rekordy i `airport_timezones`, zachować regułę zniżki dla odcinka Teneryfy.
- 5: osobno uprawnienia RZE dla A i B, niezależnie od kierunku podróży.
  Nie przenosić uprawnienia między wariantami na podstawie samego IATA huba.
- Do list wykluczonych endpointów transferowych w 3/4/5 dodać RZE, zachowując
  dokładnie szczególny status GDN w 5B. Nie dodawać do wyjątku nowego celu RZE.
- Nowy hub: pełny rekord schematu, prawdziwa strefa IANA, kraj/nazwa,
  TFN/TFS, dozwolone endpointy/linie, uprawnienie/mnożnik i dowody.
  Sam kod lotniska lub wpis do `scope` nie wystarcza.

### 7.2. Generator konfiguracji — użycie i rzeczywiste ograniczenia

```bash
.venv/bin/python scripts/build_gdn_config_patch.py --endpoint RZE --snapshot tmp/rze-expansion/network-snapshot.json --schedules tmp/rze-expansion/verified-wizz-schedules.json --from-date YYYY-MM-DD --days 30 --baseline-directory tmp/rze-expansion/baseline/data --output-directory tmp/rze-expansion/configuration-review
```

Nazwa narzędzia jest historyczna; `--endpoint RZE` jest wymagane. Wynik do
review obejmuje dziewięć allowlist i wspólny rejestr Wizz, nie jest jeszcze
automatycznie kompletną ani zastosowaną zmianą konfiguracji.

Przed przeniesieniem zmian:

1. **Nowe huby 1A–1F:** helper przechodzi tylko po istniejących rekordach
   tych list. Nowy kwalifikujący hub dopisać po dowodach pełnym rekordem albo
   rozszerzyć helper i testy; nigdy nie zgubić kandydatury bez komunikatu.
2. **Nowe TFN/TFS przy starym hubie 3–5:** helper zatrzymuje się z
   `Review new Tenerife airports explicitly`. Rozstrzygnąć relację danych
   jawnie. Nie usuwać nowego lotniska, żeby „przeszło”, i nie dodawać drugiego
   identycznego IATA ignorowanego potem przez loader.
3. Rozszerzenie wspólnego `tenerife_airports` starego huba może udostępnić
   nową parę także starej ósemce. Sprawdzić skutki; jeśli trzeba, wyrazić
   relację per endpoint bez niezamierzonego rozszerzenia pozostałych miast.
4. Nowe huby 3–5 mogą zostać wygenerowane, ale muszą otrzymać wyłącznie
   zweryfikowane uprawnienia i kompletne dane, zwłaszcza rozkład Wizz.
5. Scalanie dowodów Wizz może zastąpić wcześniejszy wspólny wpis wraz
   z override'ami. Obejrzeć diff wszystkich tras, także wspólnych odcinków
   Teneryfy. Pojedyncza nowa obserwacja nie zastępuje całej historii wyjątków.
6. Zachować idempotencję: ponowne zastosowanie tych samych danych nie może
   tworzyć `/RZE/RZE`, duplikatów hubów, endpointów ani schedule entries.
   Regex list endpointów został już uogólniony przy LCJ; nie naprawiać tej
   historycznej usterki ponownie. Dodać regresję dla dziewiątego endpointu.
7. Opisy liczebności przeglądać świadomie; obecny regex słów obejmuje do
   „osiem”. Preferować neutralne „wszystkie polskie lotniska z rejestru”,
   a nie polegać na automatycznej zamianie przyszłego „dziewięć”.
8. Dowody źródłowe opisywać faktycznie: trasy sprawdzone, nieaktywne,
   pending i błędy osobno. Nie odświeżać samą datą starych dowodów ani nie
   oznaczać wszystkich schedule entries jako zweryfikowanych jednym audytem.

Finalny diff powiązać wprost z tabelą decyzji z etapu B. Każda zaakceptowana
nowa relacja musi wystąpić w konfiguracji i w późniejszym `expected_queries`.

## 8. Etap E — kolektory, ceny i plan kompletności

### 8.1. Wymagania per krok

| Feed | Co sprawdzić dla RZE i nowych hubów |
| --- | --- |
| 1A | Pełny Binter dzień po dniu w obu kierunkach, niezależna macierz Ryanair/Wizz, cash fare + final imports, potem builder obu kierunków. |
| 1B | Pełne dni Iberii/Express Google HTTP w obu kierunkach, niezależna macierz low-cost, opłaty + szacunek rezydenta, link Iberii. |
| 1C | Każdy zapisany dzień Vuelinga Google HTTP i pełne zapisane polskie pary obu linii, potem dopasowanie i link Vuelinga. |
| 1D | Wszystkie grupy indywidualnych ofert Air Europa Google HTTP, pełny numer UX i godziny, najniższa cena własna danego rejsu, bez szablonów. |
| 1E | Oficjalny Volotea MinPrice dla każdego zapisanego route/day w obu kierunkach, bez Google; kontrola zwróconych opłat i stałych opłat rejestru. |
| 1F | Najpierw komplet miesięcy Canaryfly obu kierunków, potem szczegóły wszystkich dostępnych dni i końcowe imports; pełne niezależne kalendarze low-cost. |
| 2 | RZE–TFN, RZE–TFS i oba odwrócenia, osobno Ryanair/Wizz i cały okres, także rzetelne potwierdzenie pustych route/day. |
| 3 | Wszystkie zapisane nogi Ryanaira po obu stronach każdego huba i obu kierunków, następnie matching. |
| 4 | Pełne kalendarze Wizza po obu stronach, komplet numerów i przylotów z rejestru, następnie matching. |
| 5 | Niezależnie oba kalendarze linii, warianty A/B i oba kierunki; przewoźnik przypisany geograficznie. |

Nie zmieniać logiki kolektorów przez wpisanie RZE na sztywno. Oprzeć je
o kanoniczny loader, metadane hubów i zapisane uprawnienia. Sprawdzić także
rzeczywiste wywołania funkcji pobierających, nie tylko `build_connections`.

### 8.2. Źródła i poprawność cen

- Ryanair/Ryanair UK: wyłącznie `google_flights_http`, FR i RK, pełne numery,
  daty/godziny i najniższa cena każdego rejsu w PLN. Współdzielony persistent
  route/day cache całego batcha. Bez Fare Finder i kopiowania minimum dnia.
- Air Europa: wyłącznie Google HTTP dla aktualnych rejsów i ich cen. Brak
  użytecznej ceny/numeru/godzin lub błędny dzień zatrzymuje feed; promocja
  oficjalnego branded feedu nie jest fallbackiem.
- Binter: `booking_search` służy wyborowi taryfy cash; token wyłącznie
  w pamięci trafia do `booking_getImports`, jeden dorosły z RC na uprawnionej
  trasie. Zapis końcowych sum regularnych/rezydenckich ze wszystkich
  komponentów. PTS można pominąć bez utraty poprawnej taryfy EUR tego rejsu.
- Canaryfly: analogicznie końcowe `booking_getImports`, jeden dorosły z DC;
  suma `mainAmount` regularna i `totalAmount` rezydencka, potwierdzony status.
  Brak lub wadliwy komponent oznacza błąd, nie zgodę na cenę netto.
- Dla Iberii/Express, Vuelinga, Air Europa, Volotei i uprawnionych hiszpańskich
  odcinków Teneryfy Ryanair/Wizz w 3–5 stosować wspólny szacunek:

  `cena_rezydenta = opłaty_PLN + 0.25 × (cena_regularna_PLN − opłaty_PLN)`.

  Nie mnożyć całej ceny przez 0.25. Oznaczać szacunek, nie oficjalną wycenę.
  Nie stosować tego estymatora do oficjalnych totals Bintera/Canaryfly.
- Opłaty są kierunkowe, przez `scripts.spanish_resident_fees`. Rejestr
  obecnie obejmuje odloty 2026-03-01–2026-12-31; przy realizacji sprawdzić
  całe nowe okno. Nowy uprawniony hiszpański odcinek wymaga obu kierunków
  opłat z właściwych dowodów. Samo RZE nie potrzebuje wpisu opłat Aena.
- NBP: jeden dzienny zestaw przez istniejący cache `tmp/nbp-rates/`, te same
  kursy dla wszystkich feedów i przeliczeń opłat. Nie odpytujemy NBP od nowa
  dla każdego kroku. Dzień bez publikacji tabeli wymaga ostatniej dostępnej
  tabeli zgodnie z istniejącym loaderem, nie wymyślonego kursu.
- Nie uruchamiać repricingu starej bazy jako substytutu nowej kolekcji RZE.
  Narzędzie repricingu nie dodaje lotów, nie pobiera danych i nie wystawia
  nowego poświadczenia kompletności.

### 8.3. Linki i zniżki na stronie

Każda noga ma deterministyczny `booking_url` z odpowiedniej funkcji w
`scripts.booking_urls`. Testować trasę, datę, pasażerów i wariant rezydencki,
nie utrwalać tokenów/API keys/cookies/sesji źródła cen.

Air Europa zachowuje `residentType=SPANISH_RESIDENT_RC` dla rezydenta i
usuwa go po wyłączeniu filtra; nie stosować pośredniego `true`. Link otwiera
oficjalne wyszukiwanie trasy i dnia, nie automatycznie wybrany numer rejsu.
Także Wizz/Ryanair nie gwarantują preselektowania konkretnego rejsu.
Canaryfly/Volotea wybór rezydenta mają w swoim procesie rezerwacji; nie
dorabiać nieobsługiwanych parametrów URL. Źródło Google nie zmienia tych zasad.

### 8.4. Plan zapytań i przewidywalny wzrost macierzy

`scripts.collection_coverage.expected_queries` ma odzwierciedlać aktualną
konfigurację dziewięciu endpointów, niezależnie od faktycznie zwróconych lotów.
Sprawdzić obecność każdego nowego huba i każdej kierunkowej nogi w planie.
Potwierdzony pusty dzień jest pozycją kompletną; błąd, również GraphQL przy
HTTP 200, nie może być pustym dniem.

Raport pokrycia poświadcza wykonanie zaplanowanych zapytań, nie gwarantuje,
że zewnętrzny dostawca nigdy nie pominął rejsu. Kontrola wszystkich grup
ofert, próbek konkretnych lotów i zachowania parsera pozostaje konieczna.

Przy **niezmienionej liczbie hubów** i oknie 31 dat przewidywalne minimum:

| Zakres | Osiem endpointów | Dziewięć endpointów |
| --- | ---: | ---: |
| Krok 2: skierowane pary na jedną linię | 32 | 36 |
| Krok 2: pary trasa/linia obu linii | 64 | 72 |
| Krok 2: route/day | 1984 | 2232 |
| 1A: route/day, z obecnymi sześcioma hubami | 6696 | 7440 |
| 1B: route/day, z obecnym MAD | 1116 | 1240 |

Wzrost kroku 2 to 248 pozycji, czyli 12,5%. Nowe huby/TFN/TFS/uprawnienia
zmienią inne wielkości; policzyć je po zatwierdzeniu konfiguracji, a nie
obiecywać konkretnej liczby lotów RZE, czasu pobierania lub liczby HTTP.

Google limit dwóch realizuje wspólne `scripts.collector_settings` w procesie.
Runner uruchamia feedy sekwencyjnie. Zachować to: nie uruchamiać kolektorów,
technicznych probe'ów i niezależnych weryfikatorów Google równolegle w kilku
procesach, bo ich osobne semafory nie dają globalnego limitu dwóch.

## 9. Etap F — strona i obecny wielokrotny wybór lotnisk

Punktem wyjścia jest **nowy multiselect**, nie dawny pojedynczy select.
Dodać `RZE: "Rzeszów (RZE)"` do `airportLabels` w `app.js`, a etykiety
ewentualnych nowych hubów tylko po audycie. Nie przebudowywać pozostałych
filtrów ani nie cofać ostatniej funkcji wyboru wielu polskich lotnisk.

Obecny mechanizm:

- Polska strona korzysta z `<details>` i checkboxów, Teneryfa nadal z
  pojedynczego selecta. Ukryte legacy selecty pozostają dla kompatybilności.
- `state.polishAirports` jest posortowanym zbiorem; `[]` oznacza wszystkie.
  Jawne zaznaczenie pełnego dostępnego zestawu normalizuje się do `[]`.
- Opcje pochodzą z unii polskich endpointów **wyników obu kierunków**, nie
  wprost z rejestru. Nie dodawać RZE na sztywno do checkboxów niezależnie od
  danych. Jeżeli pełna poprawna kolekcja da zero ofert RZE w obu kierunkach,
  opisać ten wynik i obecną zasadę UI; nie produkować sztucznego wyniku/ceny.
- Jeśli RZE ma oferty tylko w jednym kierunku, dzięki unii opcja jest
  dostępna w obu. Zero wyników drugiego kierunku może być prawidłowe.
- Zmiana kierunku zachowuje polskie lotniska i przenosi je między rolą
  wylotu a przylotu. RZE + KRK oznacza sumę ofert, a nie trasę RZE–KRK.
- X na chipie usuwa tylko to lotnisko; ostatnie usunięcie daje wszystkie.
  Reset dat zachowuje lotniska, pełny reset i otwarcie udostępnionego lotu
  czyszczą ich ograniczenie zgodnie z obecnym zachowaniem.
- Oba klucze cache kalendarza i kart uwzględniają znormalizowany multiselect.

Sprawdzić RZE samodzielnie i z co najmniej dwoma starymi lotniskami w obu
kierunkach: wynik OR, minima kalendarza/wykresu dla wybranego zbioru, kliknięcie
tego samego ID karty, cztery warianty rezydent/WDC, osiem sortowań, +1 po
północy, czyszczenie dat i udostępnianie konkretnej propozycji.

Nie usuwać istniejącej poprawki warstw
`.search-panel:has(.airport-multi[open])`: otwarte menu musi być nad
kalendarzem. Przy dziewięciu checkboxach sprawdzić dolny wiersz i przyciski,
scroll listy, szerokość małego ekranu, „Wszystkie”, „Gotowe”, Escape, kliknięcie
poza menu, focus klawiatury oraz wznowienie przygotowywania kart w tle.

Zmieniając zasoby produkcyjne, podnieść odpowiednią wersję cache w
`index.html`; nie używać starego `?build=poz-local...` jako dowodu świeżego JS.
Nie zmieniać copy niezwiązanego z RZE ani domyślnych filtrów.

## 10. Etap G — testy przed pobieraniem pełnej bazy

### 10.1. Konfiguracja, discovery i rzeczywiste zapytania

Dodać `tests/test_rze_expansion.py` i rozszerzyć właściwe testy istniejące:

- Dokładny rejestr dziewięciu, strefa RZE, wszystkie dziewięć scope, brak
  duplikatów i poprawny jedyny wyjątek GDN→KRK w 5B.
- Nowe potwierdzone uprawnienia RZE: obecne we właściwym wariancie, brak
  niezatwierdzonych dopisków do innych hubów/linii/endpointów.
- Syntetyczny `RZE–NEW–TFS`, z hubem nieobecnym we wszystkich starych
  listach: discovery → rekord konfiguracji → komplet obu kierunków zapytań.
  Osobno Wizz pending, 5A/5B i nowe TFN/TFS istniejącego huba.
- Nowy hub 1A–1F nie może zniknąć w helperze. Powtórne generowanie jest
  idempotentne, zachowuje stare schedule overrides i prawdziwe opisy dowodów.
- Weryfikator obejmuje nowe Wizz Teneryfa–hub w 4 i 5B. Każdy aktywny odlot
  rozwiązuje numer/przylot z właściwą datą/weekday/clock override.
- Mocki faktycznych executorów wszystkich kolektorów potwierdzają pełne okno
  obu kierunków i obu linii, również gdy druga linia nie zwraca lotów.
- Krok 2: 36 skierowanych par na przewoźnika, 72 para/linia; 31 dni dla
  każdej. Dla fixture dwóch hubów low-cost odpowiednie 32 → 36 na linię.
- Canaryfly pełne miesiące, potem wszystkie dostępne dni, nie tylko dni
  z pasującym rozkładem Ryanaira/Wizza. Raport wymaga też tych szczegółów.
- Ryanair FR/RK i Air Europa: własne ceny rejsów w różnych grupach ofert,
  brak ceny/brak danych/failure abort, verified empty odrębne od failure.
- Google równoległość nie przekracza dwóch, także retry; NBP ten sam batchowy
  dla wszystkich feedów i przeliczenia opłat.

### 10.2. Regresja starej ósemki — nie aktualizować historii bezmyślnie

Obecne `tests/test_airport_expansion.py`, `test_wro_expansion.py`,
`test_poz_expansion.py`, `test_lcj_expansion.py`, `test_step2_collector.py`
i `test_source_completeness.py` mają założenia liczbowe obecnego stanu.
Aktualne macierze zmienić 8 → 9, 32 → 36 i 64 → 72 tam, gdzie to wynika
z definicji. Nie zmieniać historycznych stałych SIX/SEVEN w dziewięć.

W testach LCJ jest konkretna pułapka wymagająca naprawy fixture przy RZE:

- `test_resident_builders_both_directions_and_frozen_seven_regression`
  buduje wejście z bieżącego `POLISH_AIRPORTS`, a potem odejmuje tylko LCJ.
  Po rozszerzeniu zostawiłby RZE w rzekomej starej siódemce. Zamrozić wejście
  tego historycznego testu do jawnego `SEVEN + LCJ`.
- `test_frozen_seven_direct_and_transfer_results_and_ids_unchanged` podobnie
  generuje aktualny zestaw i odejmuje LCJ w części transferowej. Ograniczyć
  fixture i porównanie do właściwego historycznego zbioru endpointów.
- Nie osłabiać asercji, nie usuwać testu i nie „naprawiać” go zaakceptowaniem
  zmienionych starych cen/ID. Nie przywracać dawnego błędu POZ polegającego
  na wyprowadzaniu historycznej szóstki z `direct[:-1]`.

Nowy test RZE ma własne jawne `EIGHT = (WAW, WMI, KTW, KRK, GDN, WRO, POZ,
LCJ)`. Na zamrożonych tych samych danych porównać identyczne stare wyniki,
ich ID, liczby, ceny i linki we wszystkich dziesięciu builderach, obu
kierunkach i obu mieszanych wariantach. Zachować m.in. LCJ 1C ALC/AGP i sześć
hubów Ryanaira AGP/BGY/BHX/CRL/DUB/STN, o ile nowy osobny audyt nie daje
podstaw do innej jawnej decyzji. Nie usuwać starych tras z powodu sezonowości.

### 10.3. Przesiadki, kompletność i strona

- Przesiadki 120 i 1440 minut przechodzą, 119 i 1441 nie. Odwrotna
  chronologia, inne IATA przesiadki, self-route i drugi transfer odrzucane.
- Start/koniec okna, zmiana czasu letniego, odlot/przylot następnego dnia,
  pierwszy i drugi odcinek w różnych datach, prawidłowy znacznik +1.
- RZE w 1A–1F/2/3/4/5A/5B sprawdzić również syntetycznie tam, gdzie realny
  audyt nie wykazał trasy; test mechanizmu nie jest deklaracją żywego lotu.
- Stary raport ośmiu lotnisk nie certyfikuje dziewięciu. Brak jednego RZE
  route/day, nowego huba lub wymaganych szczegółów 1F blokuje publikację.
- Błąd źródła, wadliwe imports, brak opłaty, przeterminowane opłaty, różny
  run ID/okno/sidecar oraz zmiana konfiguracji przy resume kończą się błędem
  i zachowaniem poprzednich publicznych feedów wraz z raportami.
- `tests/test_airport_ui.mjs`: rozszerzyć test „all eight endpoints...” o RZE
  i dziewięć opcji przy fixture z ofertami wszystkich dziewięciu. Kolejność
  kodów sortowana: GDN, KRK, KTW, LCJ, POZ, RZE, WAW, WMI, WRO.
- Testować RZE + stare endpointy, OR, normalizację całego wyboru, kierunki,
  chip X, reset dat, pełny reset, cache, cztery ceny, kalendarz/wykres/kartę,
  osiem sortowań i share droższego lotu ponad domyślne 1000 zł.
- Fixture bez ofert RZE i z RZE tylko w jednym kierunku muszą działać bez
  fikcyjnych opcji/cen i bez utraty wyboru przy zmianie kierunku.

Uruchomić offline, przed pełną kolekcją:

```bash
.venv/bin/python -m unittest discover -s tests -p 'test_*.py'
node --test tests/test_airport_ui.mjs
```

Testy UI na starych feedach są testem regresji; nową pełną ścieżkę danych
RZE testować syntetycznie, a po kolekcji ponownie na stagingu. Liczbę testów
po rozszerzeniu podać rzeczywistą, nie przepisać 196/26 jako nowy wynik.

## 11. Etap H — nowa pełna kolekcja do osobnego stagingu

Po zamknięciu audytu, konfiguracji i testów zebrać **wszystkie dziesięć
feedów dla dziewięciu endpointów**, a nie tylko loty RZE doklejone do starej
bazy. Nie poprawiać JSON-ów ręcznie i nie podpinać nowych raportów pod stare
ceny. Nie uruchamiać cen, dopóki trasy Wizz, opłaty i plany są niekompletne.

```bash
.venv/bin/python scripts/collect_five_steps.py --from-date YYYY-MM-DD --days 30 --stage-directory tmp/rze-expansion/batch-YYYY-MM-DD-RUN --workers 4
```

Wybrać unikatowy nowy katalog. `RUN` w ścieżce jest czytelną etykietą,
nie samym UUID; właściwy `run_id` generuje runner i zapisuje w raporcie.
Zachować go do ewentualnego wznowienia.

Runner uruchamia `1, 1b, 1c, 1d, 1e, 1f, 2, 3, 4, 5` sekwencyjnie.
`--workers 4` nie znosi limitu dwóch Google. Nowy batch dostaje własny cache
Ryanaira, identyfikację runu, dat i hash bieżącej konfiguracji. Nie importować
cache z poprzedniego runu ani nie kopiować starych feedów do stagingu.

W razie awarii zachować logi, `step*-results.collection-report.json` ze
statusem `failed` w stagingu i `validation-report.json`, poprawić przyczynę,
nie podmieniać publicznej bazy. Nie oczekiwać osobnego pliku `.failed.json`:
obecny wrapper zapisuje raport niepowodzenia pod ścieżką sidecara.
Przykład wznowienia, jeżeli przerwa nastąpiła na kroku 3:

```bash
.venv/bin/python scripts/collect_five_steps.py --from-date YYYY-MM-DD --days 30 --stage-directory tmp/rze-expansion/batch-YYYY-MM-DD-RUN --workers 4 --run-id UUID_Z_PIERWOTNEGO_RAPORTU --refresh-steps 3 4 5
```

Wznowić wadliwy krok oraz wszystkie niewykonane późniejsze kroki; np. po
błędzie 1C są to `1c 1d 1e 1f 2 3 4 5`. Wspólne ID nie pozwala mieszać
starych i nowych batchy. Po zmianie konfiguracji lub okna rozpocząć nowy run
z nowym stagingiem i cache; istniejąca kontrola hash celowo blokuje resume.
Jeśli aktualizacja przeciąga się na kolejny dzień, jawnie zdecydować o nowym
batchu dla nowego dnia zamiast cicho przesunąć część okna/cen.

## 12. Etap I — walidacja stagingu i odbiór lokalny

```bash
.venv/bin/python scripts/collect_five_steps.py --from-date YYYY-MM-DD --days 30 --stage-directory tmp/rze-expansion/batch-YYYY-MM-DD-RUN --validate-only
RESIFLY_TEST_DATA_DIRECTORY=tmp/rze-expansion/batch-YYYY-MM-DD-RUN node --test tests/test_airport_ui.mjs
```

Nie uruchamiać powtórnej kolekcji tylko po to, żeby obejrzeć dane. Sprawdzić:

1. Komplet dziesięciu feedów, poprawne modele, jedno okno/dzień batcha,
   wspólne kursy NBP i identyczny `collection_coverage.run_id`.
2. Dziesięć kompletnych sidecarów identycznych z raportami osadzonymi;
   pokrycie zgodne z aktualnym niezależnym planem dziewięciu endpointów.
3. Wszystkie zapisane nowe huby i odcinki RZE obecne w planie, brak błędnych
   lub niesprawdzonych dni, szczegóły Canaryfly zgodne z miesięcznym skanem.
4. Tabela wyników i pokrycia per feed, per endpoint i kierunek, osobno nowe
   huby RZE i propozycje GDN-transfer. Zera z przyczyną, nie pominięte wiersze.
5. Unikalność ID, ciągłość lotnisk/stref, prawidłowa długość przesiadki,
   komplet cen/numerów/godzin/linków, brak tokenów i sesji w publicznych plikach.
6. Próbki każdej rzeczywiście występującej rodziny i obu kierunków RZE;
   regularne vs rezydent/WDC, Binter/Canaryfly końcowe totals, estymaty z opłatami.
7. Ceny i dostępność starej ósemki z nowej kolekcji porównać ze starym
   snapshotem informacyjnie, a identyczność algorytmów udowodnić testem
   zamrożonych wejść. Zmiana ceny na żywo nie jest sama w sobie regresją.
8. Browser QA nowego zestawu: szeroki ekran i około 320 px, multiselect RZE
   i zestaw mieszany, menu nad kalendarzem, karty, kalendarz/wykres, share,
   +1, wszystkie istniejące resety i brak błędów konsoli.

Podgląd stagingu przygotować w izolowanej kopii statycznej strony z danymi
stagingu albo wykonać przeglądarkowy odbiór po bezpiecznej lokalnej promocji.
Nie zmieniać produkcyjnej ścieżki danych tylko na potrzeby testu i nie
podmieniać po cichu części publicznej bazy. Ponownie ustalić dostępność
przeglądarki: wcześniejszy problem z narzędziem z historycznego raportu LCJ
nie oznacza, że blokada nadal występuje. Jeśli nie można wykonać QA lub
sprawdzić schowka, jawnie pozostawić ten punkt otwarty zamiast twierdzić,
że testy Node są odbiorem wizualnym.

## 13. Etap J — lokalna promocja i raport wdrożenia

Dopiero gdy komplet przeszedł odbiór, zgodnie z osobną zgodą na wdrożenie
lokalne:

```bash
.venv/bin/python scripts/collect_five_steps.py --from-date YYYY-MM-DD --days 30 --stage-directory tmp/rze-expansion/batch-YYYY-MM-DD-RUN --validate-only --promote
```

Runner waliduje i podmienia dziesięć feedów oraz dziesięć raportów, zachowując
poprzedni komplet w stagingu. Obsłużony błąd podmiany powoduje przywrócenie
starego kompletu; nie jest to jedna atomowa transakcja na 20 plikach odporna
na dowolne przerwanie zasilania. Zachować niezależny baseline i sprawdzić
stan po promocji, również przy błędzie.

Nie przywracać tylko feedów ośmiu endpointów pod konfigurację dziewięciu
i nie ogłaszać takiej mieszanki pełnym rollbackiem. Przy wycofaniu wdrożenia
przywrócić spójny pakiet kodu/konfiguracji/20 plików sprzed RZE, zachowując
niezwiązane zmiany użytkownika. Żadnego `git reset --hard` ani globalnego
odrzucania zmian. Przy złożonym współdzielonym diff najpierw ustalić zakres.

Zapisać `docs/WDROZENIE_RZESZOWA_RZE.md` z:

- faktyczną datą, commit baseline, zakresem lokalnych zmian i stanem Git;
- dowodami siatek, nowymi hubami, decyzjami odrzuconymi/pending i ograniczeniami;
- macierzą tras RZE każdego wariantu, strefami, rozkładami i opłatami;
- run ID, oknem, kursami, hashem konfiguracji, ścieżką stagingu i backupu;
- tabelą wyników i complete coverage wszystkich dziesięciu feedów i kierunków;
- wynikami testów oraz faktycznym odbiorem UI/linków/schowka lub otwartym punktem;
- potwierdzeniem braku commita/push/nowego workflow, jeśli zakres był lokalny.

Zaktualizować bieżące instrukcje do dziewięciu endpointów. W `README.md`
naprawić przy okazji wdrożenia istniejące nieaktualne opisy źródeł: 1D nie
korzysta już z oficjalnego feedu cen Air Europa, lecz z Google HTTP; szacunek
nie wynosi 25% całej ceny. Te błędne akapity nie są instrukcją nadrzędną wobec
AGENTS/FIVE_STEP. Nie przepisywać historycznych planów i wyników WRO/POZ/LCJ
tak, jakby od początku obejmowały RZE; dodać odnośnik do nowego raportu.

## 14. Etap K — GitHub i ewentualne Actions dopiero osobno

Niniejszy plan nie zleca publikacji. Po lokalnym odbiorze pokazać użytkownikowi
stan i czekać na polecenie wysłania. Dopiero wtedy przegląd diff/testów,
sprawdzenie gałęzi i zdalnego stanu, jawne staging konkretnych plików,
commit oraz zwykły push bez force. Zachować niezwiązane pliki i dane prywatne.
Nie publikować cache, logów sesyjnych, tokenów ani całego `tmp/`.

Pakiet do ewentualnej publikacji obejmuje konfigurację, potrzebne zmiany
kodu/testów, dokumentację i cały zwalidowany komplet 20 plików. Sam kod RZE
bez świeżej spójnej bazy nie daje użytkownikom kompletnego wdrożenia.

Przyszłe GitHub Actions to osobne zadanie. Nie dodawać teraz workflow.
Docelowo użyje tego samego rejestru, requirements, pięciu kroków, runnera,
limitów Google, NBP i bramek kompletności. Discovery oddzielnie od normalnego
pobierania cen, najpierw dry-run i raport do review. Istniejące publikowanie
GitHub Pages nie jest dowodem gotowego workflow zbierającego ceny.

## 15. Checklista wykonawcy i warunek „gotowe”

Stan po realizacji lokalnej, z dowodami w raporcie wdrożenia:

- [x] Osobne polecenie wdrożenia RZE, aktualny przegląd zasad/statusu i baseline.
- [x] Rejestr dziewięciu oraz zachowany jedyny wyjątek GDN 5B→KRK.
- [x] Pełne siatki RZE, nie tylko stare huby; prawdziwe statusy źródeł.
- [x] Audyt 1A–1F, 2, 3, 4, 5A i 5B oraz tabela wszystkich decyzji.
- [x] Nowe globalnie huby i nowe TFN/TFS rozliczone — audyt nie wykazał takich dodatków.
- [x] Wszystkie aktywne nowe odcinki Wizz mają komplet zweryfikowanych danych.
- [x] Dziewięć poprawnych scope, tylko zatwierdzone uprawnienia i strefy IANA.
- [x] Poprawne ceny końcowe/estymaty, kierunkowe opłaty ważne dla całego okna.
- [x] Rzeczywiste niezależne macierze collectorów i pełny plan coverage.
- [x] Aktualne oraz historyczne fixture poprawne; regresja zamrożonej ósemki.
- [x] Automatyczne testy UI RZE/multiselect/minima/karty/share/+1 przechodzą.
- [ ] Ręczny odbiór wizualny desktop/320 px i systemowego schowka — sterowanie przeglądarką wyłączone w Work.
- [x] Wszystkie offline testy przechodzą, brak osłabionych asercji kompletności.
- [x] Nowy pełny batch dziewięciu endpointów, jeden run i kursy, Google ≤ 2.
- [x] Dziesięć feedów i dziesięć zgodnych sidecarów przechodzi walidację.
- [x] Próbki faktycznych danych odebrane; otwarta blokada odbioru przeglądarkowego jawnie opisana.
- [x] Bezpieczna lokalna promocja, ponowna kontrola i raport z dowodami/rollbackiem.
- [x] Brak publikacji bez nowej zgody użytkownika; Actions poza tym wdrożeniem.

„Gotowe lokalnie” oznacza cały spójny pakiet i udokumentowane pokrycie,
nie tylko obecność Rzeszowa na liście filtrów. Liczba wyników RZE może być
zerowa w którymś wariancie, ale nie może to wynikać z pominiętego audytu,
niepobranego kalendarza, utraconego nowego huba ani ukrytej awarii źródła.
