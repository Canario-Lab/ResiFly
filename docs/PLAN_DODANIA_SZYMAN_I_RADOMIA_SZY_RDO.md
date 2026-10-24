# Plan dodania Szyman (SZY) i Radomia (RDO) do ResiFly

Plan wykonawczy z **24.10.2026**, po wdrożeniu Lublina. Baseline HEAD:
`811599d64b93ed65f08563f56ad2e5fb8ac96eb1` — `Add Lublin endpoint and refresh all flight feeds`.
Checkout: `codex/add-lodz-lcj`; historyczna nazwa nie określa zakresu zadania.
Przed przygotowaniem dokumentu repozytorium było czyste.

**Na tym etapie powstał tylko plan.** Odczytano bieżące pliki, zweryfikowano
obecną bazę i testy, odczytano oficjalne pełne grafy tras Ryanaira i Wizz Air
oraz materiały portów/przewoźników. Nie dopisano endpointów, nie zmieniono
allowlist, rozkładów, strony ani publicznych feedów. Nie pobrano nowych
kalendarzy cen, nie uruchomiono pełnego batcha i nie wykonano commita/push.
Testy źródeł używają mocków, a odczyt grafu tras nie jest kolekcją cen.

**Aktualizacja 24.10.2026: użytkownik zatwierdził realizację wyłącznie lokalną.**
Powyższy opis „tylko plan” dokumentuje moment przygotowania, nie stan wdrożenia.
Realizację i pełną nową bazę odebrano lokalnie; wyniki, faktyczne zera NRN/RDO,
testy, ograniczenia i rollback zapisano w
[`WDROZENIE_SZYMAN_I_RADOMIA_SZY_RDO.md`](WDROZENIE_SZYMAN_I_RADOMIA_SZY_RDO.md).
Poniższy plan i jego checklista pozostają zapisem wymagań, nie zastępują raportu.
GitHub tylko po odrębnej zgodzie. Wiążące instrukcje: `AGENTS.md`,
`docs/FIVE_STEP_FLIGHT_SEARCH.md`, `docs/COLLECTION_RELIABILITY.md`.

## 1. Najważniejsze ustalenia i proponowany sposób wdrożenia

1. Dodać **dwa różne endpointy**, SZY i RDO, do obecnych jedenastu.
   Audyt i decyzje osobno dla każdego, ale po zatwierdzeniu całej konfiguracji
   wykonać **jeden nowy pełny batch trzynastu**, zamiast dwóch drogich kolekcji
   jedenastu → dwunastu → trzynastu. Konfigurację pośrednią testować bez cen.
2. Dla SZY oficjalny graf Ryanaira wskazał **STN i NRN** jako wspólne lotniska
   z TFS w kroku 3. **NRN nie ma w obecnej allowliście**, więc to realny
   przykład kandydata zupełnie nowego globalnie, nie tylko dopisania miasta
   do istniejącego huba. Topologia nie potwierdza jeszcze zgodnych godzin/cen.
3. Dla RDO obecne grafy low-cost **nie dały żadnego wspólnego IATA z TFN/TFS**
   w 3, 4, 5A ani 5B. Nie obiecywać wyników ani trzynastego checkboxa na
   realnej bazie. Poprawnie dodany endpoint może pozostać bez ofert przy
   obecnych liniach i limicie jednej przesiadki. Potwierdzić to świeżym audytem
   i pełnymi wymaganymi kalendarzami podczas realizacji.
4. Nie dodawać LOT-u, czarterów, drugiej przesiadki, dojazdów lub zmiany
   lotniska w mieście po to, aby sztucznie uzyskać wyniki Radomia.
5. Zachować trwały wyjątek **GDN / 5B / KRK, LUZ**. Nie rozszerzać go na
   SZY/RDO, inne warianty ani inne polskie huby bez osobnej decyzji.

## 2. Zakres docelowy i niezmienne reguły

Kolejność rejestru po wdrożeniu:

**WAW, WMI, KTW, KRK, GDN, WRO, POZ, LCJ, RZE, BZG, LUZ, SZY, RDO**.

Proponowane rekordy do `data/search-airports.json`, dopiero przy realizacji:

```json
{ "iata": "SZY", "name_pl": "Szymany / Olsztyn–Mazury", "timezone": "Europe/Warsaw" }
{ "iata": "RDO", "name_pl": "Radom", "timezone": "Europe/Warsaw" }
```

To dwa przykładowe rekordy tablicy, nie samodzielny dokument JSON.
SZY oznacza port Olsztyn–Mazury w Szymanach, nie inne lotnisko Olsztyna.
RDO to osobny port, nie alias WAW/WMI ani grupowy kod Warszawy.
Wizz zwrócił nazwę RDO z końcowym CR/LF: tekst normalizować, IATA nie zmieniać.

Niezmienne zasady:

- Dokładnie **5 głównych kroków**, 1A–1F wewnątrz kroku 1, **10 feedów**,
  **10 sidecarów** i **9 allowlist**. Trzynaście oznacza endpointy, nie pliki wyników.
- D z `Atlantic/Canary`; `--days 30` to D–D+30, **31 dat włącznie**.
  Każdą zapisaną nogę każdej linii pytać o całe okno w obu kierunkach,
  niezależnie od kalendarza drugiej linii. Dopasowywać dopiero potem.
- Kierunki Polska → Teneryfa i Teneryfa → Polska osobno, nie podróż powrotna.
  Jeden transfer w tym samym IATA, 120–1440 min włącznie. Odloty obu nóg
  w oknie; przylot może być +1. Chronologia w UTC ze strefami IANA/DST.
- Brak filtra ceny w kolektorach. Domyślne UI nadal Polska → Teneryfa,
  1000 zł, maksymalnie 6 h, najbliższy termin. Ceny regularne/rezydenta/WDC osobno.
- Ryanair FR/RK i Air Europa: własne ceny każdego rejsu, numery i godziny
  tylko Google Flights HTTP; wszystkie obsługiwane grupy ofert. Bez Fare
  Finder, rozwijania minimum dnia, szablonów i promocyjnych fallbacków.
- Google maksymalnie **2 równoległe żądania**, w tym retry; sekwencyjny
  runner i jeden świeży cache route/day Ryanaira dla dziesięciu feedów.
  Nie uruchamiać równolegle dwóch procesów z osobnymi limitami po dwa.
- Jeden dzienny zestaw kursów NBP całego batcha. Binter/Canaryfly zachowują
  oficjalne końcowe regularne i rezydenckie totals, nie kwoty list taryf.
- Pozostałe uprawnione hiszpańskie nogi: jawny szacunek z pełnymi opłatami,
  nie 25% całej ceny. Samo SZY/RDO nie daje żadnej zniżki rezydenckiej.
- Każda noga ma deterministyczny `booking_url` właściwej linii, trasy, jej
  daty i pasażerów. Bez cookies, tokenów, kluczy i sesyjnych linków.
- Zachować uprawnienia i wyniki starej jedenastki na **identycznych
  zamrożonych wejściach**. Nowe żywe ceny mogą się różnić; nie jest to test regresji.
- Nie usuwać sezonowej starej trasy tylko dlatego, że nie działa w nowym oknie.
  Nie włączać automatycznie nowego huba dla wszystkich dawnych endpointów.

## 3. Sprawdzony baseline jedenastu

W trakcie opracowania planu ponownie wykonano `validate_batch(data, D, 30)`
dla **2026-10-24–2026-11-23**. Wynik poprawny: **16 017 propozycji**,
**36 890 ukończonych pozycji pokrycia**, zero braków/nadmiarów, wszystkie
osadzone raporty zgodne z sidecarami i jednym run ID:
**`f9323dee-9fdc-4e2f-8075-a39d53838115`**.

| Feed | Wyniki | Bazowy plan tras/dni | Końcowe pokrycie |
| --- | ---: | ---: | ---: |
| 1A (`step1`) | 2884 | 8928 | 8928 |
| 1B | 2252 | 1488 | 1488 |
| 1C | 2946 | 3534 | 3534 |
| 1D | 886 | 744 | 744 |
| 1E | 8 | 248 | 248 |
| 1F | 225 | 434 | 558 |
| 2 | 211 | 2728 | 2728 |
| 3 | 5647 | 11904 | 11904 |
| 4 | 218 | 1364 | 1364 |
| 5 | 740 | 5394 | 5394 |

W 1F dodatkowe 124 pozycje to szczegóły dostępnych dni, po kalendarzach.
Coverage nie jest liczbą HTTP, samolotów ani wyników. Świeży cache Ryanaira
poprzedniego runu ma 18 104 unikalne ukończone route/day; tej liczby/cache
nie przenosić jako celu lub źródła cen nowego wdrożenia.

Ponownie przeszły **234 testy Python i 38 JS**, bez pominiętych.
To stan z przygotowania planu; późniejszy wykonawca sprawdza własny HEAD,
datę, status i wiek danych. Nie podmieniać timestampów starej bazy.

### Obecne huby — punkt porównania, nie granica wyszukiwania

| Wariant | IATA |
| --- | --- |
| 1A Binter | FUE, LPA, MAD, PMI, SVQ, VLC |
| 1B Iberia/Express | MAD |
| 1C Vueling | ALC, BCN, BIO, AGP, SCQ, SVQ, VLC |
| 1D Air Europa | MAD, BIO |
| 1E Volotea | BIO |
| 1F Canaryfly | FUE, LPA |
| 3 Ryanair/Ryanair | AGA, AGP, BGY, BHX, BLQ, BOH, BRS, BUD, BVA, CRL, DUB, EDI, EIN, EMA, FCO, FMM, LBA, LPL, LTN, MAN, MRS, MXP, NAP, NCL, OPO, PSA, RAK, SNN, STN, SVQ, TLS, TSF, VIE, VLC |
| 4 Wizz/Wizz | BBU, BUD, FCO, MXP, OTP, SCQ |
| 5A Ryanair Teneryfa / Wizz Polska | AGA, AGP, BGY, BLQ, BUD, CRL, EIN, FCO, LBA, LPL, LTN, MXP, NAP, OPO, PSA, RAK, SCQ, SVQ, VLC |
| 5B Wizz Teneryfa / Ryanair Polska | BBU, BUD, FCO, GDN, MXP, OTP |

## 4. Dowody tras z 24.10.2026 i ograniczenia ustaleń

### 4.1. Odczyt pełnych oficjalnych grafów bez zbierania cen

Użyto `_http_client`, `fetch_ryanair`, `fetch_wizz`, `direct_neighbors`
z `scripts/discover_transfer_routes.py`. Odczytano wszystkie zwrócone trasy,
nie tylko obecne huby. Grafy zawierały 5317 skierowanych krawędzi Ryanaira
i 2584 Wizza; liczby nie opisują operacji w konkretnym dniu.

Źródła to oficjalny [graf tras Ryanaira](https://www.ryanair.com/api/views/locate/3/routes),
[metadane portów Ryanaira](https://www.ryanair.com/api/views/locate/3/airports/en/active)
oraz `asset/map?languageCode=en-gb` API odczytanego ze
[strony Wizz Air](https://www.wizzair.com/en-gb). Nie utrwalać wersji API
jako nowej stałej w kolektorach. Wykonawca odświeża te dowody w dniu audytu.

| Endpoint | Sąsiedzi Ryanair | Sąsiedzi Wizz Air |
| --- | --- | --- |
| SZY | NRN, STN | DTM |
| RDO | brak w zwróconym grafie | BOJ, LCA, TIA |

Surowe przecięcia z osobno sprawdzonym TFN i TFS:

| Endpoint | 3: FR/FR | 4: Wizz/Wizz | 5A: FR Teneryfa / Wizz Polska | 5B: Wizz Teneryfa / FR Polska |
| --- | --- | --- | --- | --- |
| SZY | TFS przez NRN, STN; TFN brak | brak | brak | brak |
| RDO | brak | brak | brak | brak |

To **wynik topologii**, nie pełny audyt sześciu przewoźników rezydenckich,
nie cena, nie potwierdzenie dostępności i nie kompletne coverage. Nie zapisano
nowych krawędzi do canonical allowlist. Rejestr nadal ma jedenaście endpointów,
więc nie uruchamiano CLI audytu z fałszywym `--endpoint LUZ` zamiast SZY/RDO.

### 4.2. Szymany: nowy NRN oraz rozdzielenie lotnisk i linii

[Oficjalna lista przewoźników Szyman](https://mazuryairport.pl/dla-pasazera/loty/linie-lotnicze/)
przypisuje NRN/STN Ryanair, DTM Wizzowi, a KRK LOT-owi. Kod SZY widać również
w [oficjalnym rozkładzie portu](https://mazuryairport.pl/en/for-the-passenger/flights/timetable/).
Te strony są potwierdzeniem tożsamości i wskazówkami, nie źródłem cen batcha.

Przy realizacji, jeżeli aktualne dowody to podtrzymają:

- **STN**: dopisać wyłącznie SZY do odpowiedniej relacji kroku 3, zachowując
  poprzednie endpointy, TFS i ich uprawnienia.
- **NRN**: kompletny nowy rekord kroku 3: Weeze, Niemcy, `Europe/Berlin`,
  TFS, SZY, dowody obu tras; metadata i klasyfikacja bez zniżki rezydenckiej
  (`1.0`) zgodnie ze schematem allowlisty. Uzupełnić `airport_timezones`,
  liczniki i listę `ineligible_transfer_airports`. To nie hiszpańska trasa,
  więc nie dopisywać sztucznej stawki Aeny. Etykieta UI: `Weeze (NRN)`.
- Sprawdzić SZY↔NRN i NRN↔TFS we wszystkie dni obu kierunków, tak samo STN.
  Nie brać dat jednego odcinka z drugiego. Wynik może być zerowy mimo grafu.
- **NRN ≠ DUS ≠ DTM**, a **STN ≠ LTN/LGW/LHR**. Nie zastępować IATA nazwą miasta
  ani dojazdem. Nie używać starych artykułów z SZY–LTN jako bieżącej krawędzi.
- SZY–KRK LOT nie spełnia obecnych rodzin linii; samo KRK jako nasz endpoint
  również nie daje uprawnienia do roli huba. Nie aktywować go w 3/4/5.
- Obecna strona rozkładu pokazuje końce letnich okresów w październiku 2026.
  Nie uznawać końca tabeli za definitywne zakończenie trasy ani kopiować
  godzin letnich na zimę. Sprawdzić sezon zimowy i zmianę czasu 25.10.2026.

Nie rozlewać NRN na inne polskie miasta tylko dlatego, że globalny detector
znajdzie również ich krawędzie. Zanotować je jako osobne propozycje, poza
rozszerzeniem SZY/RDO, chyba że użytkownik osobno zatwierdzi szerszy zakres.

### 4.3. Radom: obecny brak wspólnego huba jest dopuszczalnym wynikiem

Oficjalna mapa Wizza zwróciła RDO z BOJ/LCA/TIA; mapa Ryanaira nie zwróciła
RDO. Nie oznacza to „Ryanair nigdy nie poleci z Radomia”. Nie znaleziono
wspólnego lotniska Teneryfy dla żadnego dozwolonego wariantu 3–5.

Odczyt [oficjalnej strony portu Radom](https://www.lotniskowarszawa-radom.pl/)
w narzędziu WWW został zablokowany HTTP 403. Nie uznano tego za brak lotów
i nie użyto nieoficjalnego serwisu `lotniskordo.radom.pl` jako źródła
rozstrzygającego. To ograniczenie zapisać również w przyszłym audycie,
jeżeli nadal wystąpi; graf przewoźnika pozostaje oddzielnym poprawnym dowodem.

Wymagania dla Radomia:

- Przejrzeć ponownie **wszystkich** sąsiadów obu przewoźników, oba porty
  Teneryfy TFN/TFS i wszystkich sześciu przewoźników kroku 1.
  Nie ograniczyć sprawdzenia do BOJ/LCA/TIA ani obecnych hubów.
- **LCA ≠ PFO**, **BOJ ≠ VAR**, **FCO ≠ CIA**. Nie skleić RDO–LCA Wizz z lotem
  Ryanaira z innego cypryjskiego lotniska. Nie podmienić LOT-u do FCO na Wizz.
- Nie tworzyć RDO–hub1–hub2–Teneryfa, bo to dwie przesiadki.
- Wizz-only RDO nie oznacza wolnego pominięcia obowiązkowej macierzy Ryanaira
  w kroku 2 oraz 1A/1B. Poprawne puste odpowiedzi zapisać jako sprawdzone.
- Jeśli pełne sprawdzenie pozostanie zerowe, wyraźnie podać: endpoint dodany,
  kalendarze sprawdzone, brak połączeń według obecnych zasad. Nie wymyślać
  propozycji, checkboxa ani regularnej taryfy na podstawie reklamy.
- Ewentualne LOT/czartery/transfer krajowy/zmiana IATA to **osobna decyzja
  produktowa**, nie zadanie ukryte w dodaniu Radomia.

### 4.4. Trwała zgoda GDN i inne polskie przesiadki

Zachować dokładnie obecny rekord:

```json
{ "step": "step5_variant_b", "iata": "GDN", "polish_airports": ["KRK", "LUZ"] }
```

Nie dopisywać SZY/RDO. Jeśli nowy audyt pokaże polski hub, raw evidence
zachować przed filtrem `candidate_intersection()` i oznaczyć
`requires_user_decision`. Brak kandydatury po filtrze polityki nie dowodzi
braku fizycznej trasy. Nie usuwać walidatora ani nie włączać self-routes.

## 5. Mapa plików do sprawdzenia podczas realizacji

| Obszar | Pliki / czynność |
| --- | --- |
| Rejestr | `data/search-airports.json`, `scripts/search_airports.py`: dwa nowe rekordy/strefy; bez poszerzenia wyjątku GDN. |
| Instrukcje | `AGENTS.md`, `docs/FIVE_STEP_FLIGHT_SEARCH.md`, `docs/COLLECTION_RELIABILITY.md`, `README.md`: bieżący zakres 13 dopiero przy wdrożeniu. |
| Audyt | `scripts/audit_airport_expansion.py`, `scripts/discover_transfer_routes.py`: pełne grafy, surowe przecięcia i decyzje osobno SZY/RDO. |
| Konfiguracja | `scripts/build_gdn_config_patch.py`: dwa kontrolowane przebiegi, poprawne łączenie zmian; nie dwa niezależne nadpisania. |
| Wizz | `scripts/verify_wizz_expansion_schedules.py`, `scripts/wizz_schedules.py`, `scripts/wizz_api.py`, `data/wizz-route-schedules.json`, lokalne schedule 1A/1B. |
| 1A | `data/binter-transfer-airports.json`, `scripts/collect_step1.py`. |
| 1B | `data/iberia-transfer-airports.json`, `scripts/collect_step1b.py`. |
| 1C | `data/vueling-transfer-airports.json`, `scripts/collect_step1c.py`. |
| 1D | `data/air-europa-transfer-airports.json`, `scripts/collect_step1d.py`. |
| 1E | `data/volotea-transfer-airports.json`, `scripts/collect_step1e.py`. |
| 1F | `data/canaryfly-transfer-airports.json`, `scripts/collect_step1f.py`. |
| 2 | `scripts/collect_step2.py`: pełna macierz 13 × 2 Tenerife × 2 kierunki × 2 linie. |
| 3 | `data/ryanair-transfer-airports.json`, `scripts/collect_step3.py`: SZY/STN, nowy NRN po audycie; RDO tylko z dowodem. |
| 4 | `data/wizzair-transfer-airports.json`, `scripts/collect_step4.py`: relacje tylko z dowodem, pełne metadata Wizza. |
| 5 | `data/mixed-transfer-airports.json`, `scripts/collect_step5.py`: osobne A/B, nie zmieniać ról przy odwróceniu kierunku. |
| Źródła/wyceny | `scripts/ryanair_google.py`, `scripts/collector_settings.py`, `scripts/spanish_resident_fees.py`, `data/spanish-resident-fees.json`, `scripts/booking_urls.py`. |
| Kompletność | `scripts/collection_coverage.py`, `scripts/collect_five_steps.py`: aktualny plan 13, hash, jeden run/NBP/cache, staging/promotion. |
| Strona | `app.js`, `index.html`, `styles.css` tylko gdy konieczne: etykiety, opis portów, multiselect i wersja JS. |
| Testy | Nowy `tests/test_szy_rdo_expansion.py`, aktualne testy ekspansji/źródeł i `tests/test_airport_ui.mjs`. |
| Odbiór | 10 `data/step*-results.json`, 10 `data/step*-results.collection-report.json`, nowy `docs/WDROZENIE_SZYMAN_I_RADOMIA_SZY_RDO.md`. |

To mapa przeglądu, nie polecenie edycji każdego modułu. Kod już w znacznej
części czyta wspólny rejestr; nie dokładać `if SZY`/`if RDO` do każdego kroku.

## 6. Etap A — baseline, dwa endpointy i audyt bez cen

1. Po nowym poleceniu odczytać instrukcje, HEAD/status/diff, datę Canary
   i obecną konfigurację. Zachować niezwiązane zmiany użytkownika.
2. Utworzyć niekolidujący `tmp/szy-rdo-expansion/baseline-RUN/` z kopią
   kodu/testów/instrukcji, rejestru, 9 allowlist, wspólnych/lokalnych schedule,
   opłat, strony i 20 publicznych plików. Manifest SHA-256, okno i run starej
   bazy. Nie nadpisywać backupów LUZ ani poprzedniej próby.
3. Zamrozić literalny zbiór starej jedenastki oraz historyczne SIX–TEN.
   Nie definiować historii jako `POLISH_AIRPORTS[:-1]` lub „bez ostatniego”.
4. Wybrać D i czas na cały batch/retry przed północą Canary. Na etapie
   konfiguracji nie odświeżać starej bazy tylko w celu „świeżego backupu”.
5. Dopisać **oba** endpointy do rejestru, pozostawić wyjątek GDN nietknięty.
   Uruchamiać świeże procesy — stałe są ładowane przy imporcie.
   CLI `--endpoint` ma `choices=POLISH_AIRPORTS`, więc przed rejestracją nie
   przyjmie SZY/RDO. Nie obchodzić tego cudzą tożsamością dowodów.
6. Zebrać oficjalne pełne sieci, osobne raporty i metadane obu endpointów,
   również nowe globalne huby i nowe TFN/TFS w istniejącym hubie.
   Jeden wspólny snapshot sieci może być współdzielony, ale dowody techniczne
   i decyzje muszą zachować własny `endpoint`, datę i okno.

Przykładowe komendy **dopiero po rejestracji**, z rzeczywistym D:

```bash
.venv/bin/python scripts/audit_airport_expansion.py --endpoint SZY --as-of YYYY-MM-DD --output-directory tmp/szy-rdo-expansion/audit-SZY
.venv/bin/python scripts/audit_airport_expansion.py --endpoint RDO --as-of YYYY-MM-DD --output-directory tmp/szy-rdo-expansion/audit-RDO
```

Audyt zapisuje low-cost snapshot przed wywołaniem Bintera. W poprzednich
rozszerzeniach `timetable_get` Bintera zwracał GraphQL E01000. Jeśli wystąpi
ponownie, zachować `source_status.binter=failed` i błąd. To **nie dowód braku
tras**. Oddzielnie odczytać kompletny oficjalny katalog/rozkład Bintera,
porównać wszystkich sąsiadów nowych endpointów i zapisać wynik. Nie zmieniać
failed na complete bez rzeczywistego dowodu; kolekcja cen Bintera korzysta
z innych operacji i ma własne bramki.

`--low-cost-only` daje `not_checked`, nie potwierdzone zero. Sam powrót exit 0
takiego audytu nie zamyka 1A. Jeśli audyt przerwie się przed `fill_timezones`,
uzupełnić metadata nowych hubów z weryfikacją IANA i ponowić plan offline.
NRN musi dostać `Europe/Berlin`, STN `Europe/London`, nie strefę endpointu.

Uruchomić dry-run i zapisać raport, bez globalnego `--apply` w ciemno:

```bash
.venv/bin/python scripts/discover_transfer_routes.py --snapshot tmp/szy-rdo-expansion/audit-SZY/network-snapshot.json --report tmp/szy-rdo-expansion/discovery-SZY-review.json
.venv/bin/python scripts/discover_transfer_routes.py --snapshot tmp/szy-rdo-expansion/audit-RDO/network-snapshot.json --report tmp/szy-rdo-expansion/discovery-RDO-review.json
```

Detector może pokazać również nowe relacje starej jedenastki. Oddzielić je
od celu SZY/RDO i nie aktywować bez przeglądu zakresu.

## 7. Etap B — zamknięcie wszystkich pięciu kroków dla obu portów

Dla każdego kandydata prowadzić tabelę: endpoint, wariant, hub IATA, TFN/TFS,
obie linie i kierunki, nowy/stary hub, źródła/datowanie/sezon, status
`ready` / `pending_schedule` / `inactive_in_window` / `rejected` /
`source_failed` / `requires_user_decision` wraz z uzasadnieniem.

| Wariant | Obowiązkowy audyt i decyzja |
| --- | --- |
| 1A | Pełna bezpośrednia siatka Bintera z TFN/TFS przecięta z wszystkimi sąsiadami FR/Wizz SZY oraz RDO; nie tylko obecne 6 hubów. Tylko uprawnione trasy rezydenckie. |
| 1B | Osobny przegląd Iberii i Iberia Express z obu portów Teneryfy, zniżka i własny low-cost każdego endpointu; nie zakładać na zawsze tylko MAD. |
| 1C | Oficjalna strona tras Vuelinga jako nadrzędne źródło; Aena tylko pomocniczo. Nowe wspólne IATA też sprawdzić, nie tylko obecne 7. |
| 1D | Oficjalna siatka Air Europa do ustalenia tras; Google HTTP później dla indywidualnych lotów/cen. Bez promo feedu jako zastępstwa. |
| 1E | Oficjalna siatka i publiczny MinPrice Volotei, kwalifikacja resident i własna dozwolona polska noga; nie zakładać wyłącznie BIO. |
| 1F | Oficjalne bezpośrednie międzywyspowe trasy Canaryfly i własny low-cost do Polski; bez dodatkowej przesiadki wewnątrz odcinka Canaryfly. |
| 2 | Cała macierz obu nowych endpointów ↔ TFN/TFS obu linii. Brak w grafie nie zwalnia z pełnego skanu cen. |
| 3 | Wszystkie wspólne IATA FR Teneryfa i FR endpoint, nie tylko allowlista. SZY/NRN i SZY/STN to dzisiejsze kandydatury. |
| 4 | Wszystkie wspólne IATA Wizz/Wizz; nie uznać z góry DTM za połączony z Teneryfą. |
| 5A | FR na nodze Teneryfy + Wizz na nodze Polski. Sprawdzić niezależnie dla SZY i RDO. |
| 5B | Wizz na nodze Teneryfy + FR na nodze Polski. Nie przenieść uprawnień wariantu A ani zgody GDN. |

Materiały do osobnego audytu 1A–1F:
[Binter — wszystkie kierunki](https://www.bintercanarias.com/es/destinos),
[Iberia — Teneryfa/Madryt](https://www.iberia.com/es/vuelos-baratos/Tenerife-Madrid/)
(następnie również pozostała siatka i Express),
[Vueling — loty z Teneryfy](https://www.vueling.com/es/vuelos-baratos-desde-tenerife),
[Air Europa — Teneryfa](https://www.aireuropa.com/es-es/ofertas-de-vuelos-desde-tenerife),
[Volotea — Teneryfa](https://www.volotea.com/es/ofertas-vuelos/tenerife/),
[Canaryfly — loty między wyspami](https://www.canaryfly.es/en/cheap-flights).
Przejrzano je przy planowaniu; dynamiczna/ofertowa strona sama nie dowodzi
kompletności konkretnego okna ani bezpośredniości każdej reklamowanej podróży.

Obecni sąsiedzi SZY/RDO nie dają oczywistej polskiej nogi do hiszpańskiego
huba rezydenckiego. To wstępna obserwacja, nie powód pominięcia 1A–1F.
Nie kwalifikować międzynarodowej trasy Bintera jako resident tylko dlatego,
że lata Binter. W 1A–1F obie nogi muszą być bezpośrednie.

## 8. Etap C — zweryfikowane dane techniczne Wizza

Po decyzjach sieciowych uruchomić osobno:

```bash
.venv/bin/python scripts/verify_wizz_expansion_schedules.py --endpoint SZY --snapshot tmp/szy-rdo-expansion/audit-SZY/network-snapshot.json --from-date YYYY-MM-DD --days 30 --output tmp/szy-rdo-expansion/verified-wizz-SZY.json
.venv/bin/python scripts/verify_wizz_expansion_schedules.py --endpoint RDO --snapshot tmp/szy-rdo-expansion/audit-RDO/network-snapshot.json --from-date YYYY-MM-DD --days 30 --output tmp/szy-rdo-expansion/verified-wizz-RDO.json
```

- Oficjalny timetable dostarcza aktualne daty/odloty i regularne/WDC ceny,
  ale nie pełne numery/przyloty. Zweryfikować numery i czasy blokowe obu
  kierunków potrzebnych nóg; akceptować W6/W4/W9. Nie wymyślać danych.
- Sprawdzić `required_routes()` względem **wszystkich** zaakceptowanych nóg:
  nowe nogi Polski, nowy Wizz hub↔Teneryfa, lokalne potrzeby 1A/1B itd.
  Nie zakładać, że wyliczenie helpera obejmuje każdy ręcznie dodany hub 1C–1F.
- DTM i BOJ/LCA/TIA nie wymagają tworzenia technicznego schedule wyłącznie
  dlatego, że są sąsiadami endpointu. Jest potrzebny, gdy dana noga staje się
  częścią zatwierdzonej trasy lub zwróconego lotu bezpośredniego.
- Przy braku kwalifikującej się trasy Wizz dopuszczalny jest własny materiał
  SZY/RDO z pustą listą obserwacji i potwierdzonym statusem sprawdzeń.
  Nie kopiować 38 obserwacji LUZ lub zer BZG jako dowodu dla nowych portów.
- Aktualny parametr `--complete-times` nie ma osobnej wykonanej gałęzi.
  Odbiór skryptu nie wystarcza: porównać każdy aktywny dzień/zegar timetable
  z wynikiem `resolve_schedule`, w szczególności po zmianie czasu i +1.
- Wyjątki: konkretna data+godzina > dzień tygodnia+godzina > godzina > baza.
  Zachować stare wyjątki WRO/LPA, POZ/LTN, RZE/FCO i LUZ/LTN oraz wspólne
  nogi Teneryfy. Nowa próbka kilku dni nie usuwa dawnych zweryfikowanych dat.
- Brak danych obu kierunków = pending, nie gotowa trasa. Dla sezonowej trasy
  opcjonalna potwierdzona przyszła próbka to tylko dowód techniczny, nie cena
  do obecnego batcha. Wszystkie Google probe'y kolejno/max2, nie obok runnera.

## 9. Etap D — wspólna konfiguracja bez utraty jednego rozszerzenia

### 9.1. Dziewięć allowlist i nowy NRN

- Każdy `scope.polish_airports` ma dokładnie pełne 13 z rejestru, nawet jeśli
  dana rodzina nie ma żadnego nowego uprawnienia SZY/RDO.
- 1A/1B: pełna macierz hub × wszystkie endpointy × obie linie × oba kierunki.
  Nie zmieniać jej na tylko zaobserwowane polskie rynki/daty.
- 1C–1F: dodać tylko potwierdzone `polish_routes` z właściwym endpointem
  i rzeczywistą linią. Brak route do RDO nie oznacza dopisania obu linii.
- 3/4: właściwe huby i konkretne TFN/TFS; SZY do STN oraz kompletny NRN,
  jeśli świeży audyt podtrzyma dowody. RDO tylko jeśli pojawi się dowód.
- 5: osobne warianty i role geograficzne, także przy odwrotnej podróży.
- `excluded_endpoints` uzupełnić o SZY/RDO tam, gdzie wymaga schema;
  istniejący precyzyjny GDN wyjątek nadal ma pierwszeństwo tylko w 5B/KRK,LUZ.
- Nowy hub: IATA, nazwa/kraj, timezone, TFN/TFS, dozwolone endpointy/carriers,
  resident flag/multiplier, źródła, liczniki i spójna klasyfikacja. Samo
  dopisanie napisu NRN w jednej tablicy nie kończy obsługi huba.

### 9.2. Pułapka dwóch przebiegów helpera

`scripts/build_gdn_config_patch.py` ma historyczną nazwę, ale przyjmuje dowolny
**zarejestrowany** `--endpoint`. Działa obecnie dla jednego endpointu naraz.

**Nie generować SZY i RDO niezależnie z tego samego baseline i nie nakładać
ostatniego pełnego pliku na pierwszy. Utraciłoby to uprawnienia/schedule SZY.**

Bezpieczny porządek:

1. Review SZY na kopii konfiguracji baseline.
2. Review RDO na **wyniku zaakceptowanego review SZY**, nie ponownie na baseline.
3. Porównanie semantyczne końcowego zestawu z baseline i obiema tabelami decyzji.
4. Zastosowanie jednego końcowego zestawu źródeł po review, bez feedów.

Przykłady po rejestracji obu endpointów, z własnymi prawdziwymi dowodami:

```bash
.venv/bin/python scripts/build_gdn_config_patch.py --endpoint SZY --snapshot tmp/szy-rdo-expansion/audit-SZY/network-snapshot.json --schedules tmp/szy-rdo-expansion/verified-wizz-SZY.json --from-date YYYY-MM-DD --days 30 --baseline-directory tmp/szy-rdo-expansion/baseline-RUN/data --output-directory tmp/szy-rdo-expansion/review-SZY
.venv/bin/python scripts/build_gdn_config_patch.py --endpoint RDO --snapshot tmp/szy-rdo-expansion/audit-RDO/network-snapshot.json --schedules tmp/szy-rdo-expansion/verified-wizz-RDO.json --from-date YYYY-MM-DD --days 30 --baseline-directory tmp/szy-rdo-expansion/review-SZY --output-directory tmp/szy-rdo-expansion/review-SZY-RDO
```

**Uwaga: samo przekazanie baseline nie zamyka obecnie całej zależności.**
W kodzie helpera sprawdzanie `known` dla nowych hubów czyta wspólny Wizz
schedule z aktywnego `ROOT/data`, a nie wyłącznie z wybranej kopii baseline.
Nowy wspólny schedule z pierwszego review może więc nie zostać rozpoznany
w drugim. Przed użyciem łańcucha poprawić helper, by korzystał konsekwentnie
z wybranego wejściowego zestawu, i dodać test bez zależności od live `data/`.
Alternatywa: po pełnym review bezpiecznie zastosować konfigurację SZY,
potem generować RDO z niej — nadal bez zbierania/promowania częściowej bazy.
Nie deklarować, że obecne dwa polecenia są w pełni izolowanym merge bez tej kontroli.

Pozostałe znane ograniczenia:

- 1A–1F helper obsługuje **istniejące huby**, nie tworzy nowych. Jeśli audyt
  ujawni nowy hub tych rodzin, utworzyć kompletny rekord/plan/executor albo
  rozszerzyć helper z testem całej ścieżki. Nie zgubić kandydata.
- Nowe huby 3–5 helper już tworzy; NRN objąć osobnym testem end-to-end.
  Brak polskiej nazwy/kraju w źródle nie usprawiedliwia niepełnego metadata.
- Nowe TFN/TFS w starym hubie kończy się `Review new Tenerife airports explicitly`.
  Pole `tenerife_airports` jest współdzielone z dawnymi miastami: wyrazić
  nową relację per endpoint we wszystkich konsumentach albo uzyskać zgodę
  na szersze rozszerzenie. Nie dodawać po cichu nowych tras starej jedenastki.
- Helper zastępuje base/override families obserwowanych par. Zachować
  wcześniejsze zweryfikowane wyjątki i zgodność wspólnych/lokalnych 1A/1B.
- Regex opisów obsługuje słowa do „jedenaście”. Opisy „dwanaście/trzynaście”
  znormalizować do neutralnego rejestru albo rozszerzyć z testami. Nie robić
  globalnego replace 11→13, bo wiele liczb dotyczy historii/feedów.
- `verified_on`/`finding` opisują rzeczywiste źródło, endpoint i obserwacje.
  Odświeżenie nagłówka nie poświadcza nowych obserwacji wszystkich dawnych tras.
- Idempotencja: SZY→RDO→SZY i RDO→SZY mają zachować oba rozszerzenia,
  stare uprawnienia i schedule, bez duplikatów endpointów/hubów/override.
  Dopuszczalne różnice kolejności/metadata audytu oddzielić od zmian semantycznych.

## 10. Etap E — ceny, booking links i kompletne kalendarze

Źródła pozostają niezmienione, także dla nowych portów:

| Linia | Dane / wycena |
| --- | --- |
| Ryanair / Ryanair UK | Tylko Google Flights HTTP, FR/RK, wszystkie indywidualne rejsy, własne numery/godziny/PLN; wspólny cache batcha. |
| Wizz Air | Oficjalne bieżące daty/odloty/regularne i WDC; zweryfikowany numer i blok przez wspólny resolver schedule. |
| Binter | `booking_search` wybiera cash EUR, token w pamięci do `booking_getImports`, adult 1, RC na eligible; końcowe regularne/resident ze wszystkich komponentów. PTS pominąć bez utraty poprawnych EUR. |
| Iberia / Express, Vueling, Air Europa | Indywidualne loty i regularne PLN z Google HTTP; resident jako jawny szacunek z opłatami. Air Europa bez branded/promotional feedu. |
| Volotea | Oficjalny publiczny MinPrice, każda trasa/dzień osobno, własne numery/godziny i cena z opłatami. Zwrócone opłaty muszą zgadzać się z rejestrem. Bez Google. |
| Canaryfly | Pełne miesięczne kalendarze obu kierunków, szczegóły każdego dostępnego dnia, final imports adult 1/DC i potwierdzony status; bez Google. |

Binter/Canaryfly: regularna suma `mainAmount`, rezydencka suma `totalAmount`
taryfy, podatków, supplements, service fee i management fee. Brak składnika,
inna waluta lub brak potwierdzenia rezydenta blokuje publikację. Bez estymatora Aeny.

Iberia/Express, Vueling, Air Europa, Volotea oraz uprawnione hiszpańskie nogi
Teneryfy FR/Wizz w 3–5: `opłaty_PLN + 0.25 × (regularna_PLN − opłaty_PLN)`.
Tylko `scripts.spanish_resident_fees` / `data/spanish-resident-fees.json`,
kierunkowo, jeden NBP. Aktualna ważność 2026-03-01–2026-12-31 musi pokryć
każdą datę odlotu nowego okna; przy wdrożeniu później nie zgadywać stawek.
Nowy kwalifikujący hiszpański hub wymaga udokumentowanych opłat obu kierunków.
NRN/STN nie mają tej zniżki. Nie dyskontować polskiej nogi.

Wszystkie 10 feedów mają trwałe `booking_url` **na każdej nodze**, z funkcji
`scripts.booking_urls`. UX używa `residentType=SPANISH_RESIDENT_RC`, usuwanego
przez UI po wyłączeniu rezydenta; nie `true`. Google nie zmienia docelowej
linii zakupu. Volotea/Canaryfly status rezydenta w ich flow bez zmyślonego
parametru. Link route/date nie gwarantuje preselekcji numeru lotu.

Pełne kalendarze wszystkich zapisanych nóg w obu kierunkach **przed** matchingiem,
nawet jeśli dla SZY/RDO inny carrier zwrócił zero. Wizz WDC failure nie jest
upoważnieniem do skopiowania regularnej ceny. HTTP/GraphQL `errors` przy 200,
malformed payload, rejs bez ceny/numeru/godzin lub wadliwe imports to błąd,
nie pusta dostępność. Prawidłowy pusty dzień wolno zapisać jako sprawdzony.

Nie ręcznie edytować generated JSON i nie używać repricingu starej bazy
jako substytutu świeżego batcha trzynastu. Nie doczepiać nowych certyfikatów
do starych cen.

## 11. Etap F — plan zapytań dla trzynastu

`scripts.collection_coverage.expected_queries` wylicza plan niezależnie
od znalezionych lotów. Planner, executor i walidator muszą mieć ten sam
zakres każdej nowej nogi i daty.

Przy obecnych hubach 1A/1B i 31 datach:

| Zakres | Obecne 11 | Pośrednie 12 | Docelowe 13 |
| --- | ---: | ---: | ---: |
| 2: skierowane pary lotnisk na linię | 44 | 48 | 52 |
| 2: pary trasa/przewoźnik obu linii | 88 | 96 | 104 |
| 2: pełne route/day | 2728 | 2976 | 3224 |
| 1A: pełny plan przy 6 hubach | 8928 | 9672 | 10416 |
| 1B: pełny plan przy MAD | 1488 | 1612 | 1736 |

Formuły: krok 2 = `N × 2 Tenerife × 2 kierunki × 2 linie × 31`;
1A = `6 × N × 2 linie × 2 kierunki × 31 + 24 × 31`;
1B = `N × 2 linie × 2 kierunki × 31 + 4 × 31`.
Pośrednia kolumna to kontrola/test, nie nakaz oddzielnej kolekcji 12.

Każdy nowy endpoint zwiększa 1A/1B nawet bez resident-huba w wynikach.
Pozostałe kroki policzyć **po audycie**: nowy NRN zmienia plan 3, kolejne
nowe huby/TFN/TFS/uprawnienia również. Nie sumować mechanicznie starych
36 890 + samych bezpośrednich; 1F dodaje szczegóły po kalendarzach.

Wyliczyć unię unikalnych route/day Ryanaira całego nowego batcha i porównać
z cache. Coverage feedów dubluje niektóre zapytania wspólnych nóg; nie
traktować sumy coverage jako liczby faktycznych wywołań sieciowych.
Google cap 2 dotyczy retry, testów technicznych i wszystkich feedów.

## 12. Etap G — strona i multiselect z opcją pustego Radomia

W `app.js` dodać etykiety:

```javascript
SZY: "Szymany / Olsztyn–Mazury (SZY)",
RDO: "Radom (RDO)",
NRN: "Weeze (NRN)", // dopiero gdy hub zostanie zatwierdzony
```

`index.html`: opis obsługiwanych portów oraz wersja JS
`YYYYMMDD-szy-rdo-1`. CSS tylko jeśli rzeczywiście potrzebny. Nie zmieniać
innych filtrów, copy i domyślnych 1000 zł/6 h/kierunku/sortowania.

Zachować:

- Multiselect OR po stronie Polski, pojedyncze TFN/TFS po stronie Teneryfy;
  kompatybilność legacy selectów, `state.polishAirports` jako posortowany zbiór.
  `[]` = wszystkie; zaznaczenie całego dostępnego zestawu normalizuje do `[]`.
- Opcje powstają z unii endpointów **rzeczywistych wyników obu kierunków**,
  nie całego rejestru. RDO bez ofert w obu kierunkach nie dostaje fikcyjnego
  checkboxa. Nie zmieniać tej zasady bez osobnej decyzji projektowej.
- Gdy port ma wynik tylko w jedną stronę, opcja pozostaje po zmianie kierunku,
  a drugi kierunek może uczciwie pokazać zero. SZY+RDO+LUZ/KRK to OR,
  nie połączenie między tymi portami i nie wymóg dostępności wszystkich.
- Zmiana kierunku zachowuje wybór i przenosi go do pola przylotu/wylotu;
  X usuwa tylko jedną opcję. Reset dat zostawia porty, pełny reset i share
  zdejmują ograniczenie portów zgodnie z aktualną logiką.
- `fareCalendarRenderKey` i `resultCardsRenderKey` zawierają cały zbiór.
  Kalendarz/wykres mają zgodne minima dla OR, kwoty i cel tej samej karty.
- Zachować progresywne przygotowanie kart oraz warstwę otwartego menu ponad
  kalendarzem `.search-panel:has(.airport-multi[open])`.
- Share przywraca właściwy ID, kierunek i zniżki, także lot >1000 zł.
  Oznaczenie +1 nadal czytelne przy przylocie następnego dnia.

Syntetyczny test pełnych 13 opcji, kolejność IATA:
`BZG, GDN, KRK, KTW, LCJ, LUZ, POZ, RDO, RZE, SZY, WAW, WMI, WRO`.
Test pełnego menu nie wymusza 13 checkboxów w realnej bazie, jeśli RDO=0.
Na desktop i około 320 px sprawdzić długą etykietę SZY, ostatni wiersz,
scroll, Gotowe/Wszystkie, focus, Escape i klik poza popupem. Nie przebudowywać
layoutu, jeśli obecny działa. Test Node nie zastępuje oględzin.

## 13. Etap H — testy dwóch portów i zamrożona jedenastka

Nowy `tests/test_szy_rdo_expansion.py`, z literalnym baseline:

```python
ELEVEN = ("WAW", "WMI", "KTW", "KRK", "GDN", "WRO", "POZ", "LCJ", "RZE", "BZG", "LUZ")
TARGET = ELEVEN + ("SZY", "RDO")
```

### 13.1. Rejestr, uprawnienia, helper i coverage

- Dokładne TARGET, Warsaw dla obu, 9 scope, 10 feedów/sidecarów. Nie globalny
  replace liczb. Dotychczasowe SIX/SEVEN/EIGHT/NINE/TEN pozostają historią.
- Faktyczne zaakceptowane SZY/STN i NRN: pełny nowy rekord, strefa Berlin,
  TFS, brak resident; RDO z dowodami albo bez nieuzasadnionych uprawnień.
- Test **rzeczywistej nowej ścieżki NRN**: discovery → configuration →
  route_matrix/executor → expected_queries → matching → walidacja → etykieta.
  Nie wystarczy syntetyczne dopisanie SZY do starego MAD.
- Syntetyczny NEW dla 5B z brakującą jedną nogą Wizza: pending, nie aktywacja;
  nowy hub 1A–1F lub nowe TFN/TFS starego huba, jeśli wystąpi w realnym audycie,
  ma analogiczny test i brak niezamierzonego rozszerzenia dawnych portów.
- GDN w 5B tylko KRK/LUZ przechodzi. SZY/RDO i inne warianty odrzucone,
  raw kandydat zachowuje informację o koniecznej decyzji. Self-routes zakazane.
- `len(list(route_matrix())) == 52`, `104 * 31` dla kroku 2; pośrednie 48/96
  sprawdzone syntetycznie. Mock **wykonawcy** 1A przy dwóch hubach: 52
  wywołania na przewoźnika, pełne okno mimo pustego drugiego kalendarza.
- Brak jednego dnia SZY, RDO, NRN albo wszystkich nowych rynków ma blokować
  publikację. Stare coverage 11 lub 12 nie certyfikuje 13; poprawne RDO=0
  jest czym innym niż pominięte RDO. 1F wymaga wszystkich dostępnych szczegółów.
- Helper: SZY→RDO→SZY zachowuje oba, kolejność odwrotna ma równoważne
  uprawnienia; nie czerpie ukrytego schedule z live data. Osobne dowody
  endpoint/date/window, zero dowodów RDO nie kasuje schedule SZY/LUZ.
- Opisy 11/12/13 i neutralne idempotentne, bez duplikatów IATA i override.

### 13.2. Regresja obecnych lotnisk i bieżące asercje

Przejrzeć `test_airport_expansion.py`, `test_wro_expansion.py`,
`test_poz_expansion.py`, `test_lcj_expansion.py`, `test_rze_expansion.py`,
`test_bzg_expansion.py`, **`test_luz_expansion.py`**, `test_step2_collector.py`,
`test_source_completeness.py` i testy batch/source/Wizz/cen.

- Bieżące asercje rejestru zmienić 11→13, macierzy 44→52/88→104,
  executorów 44→52. W LUZ `TEN + ("LUZ",)` opisuje obecnie live registry,
  ale jego **historyczne** regresje frozen TEN nadal muszą zostać dziesiątką.
- Test source completeness `all_eighty_eight_route_carrier_pairs` dostosować
  do rzeczywistego 104; nie zmieniać niezwiązanych kwot fixture.
- Dodać literalny frozen ELEVEN i porównać wszystkie dziesięć builderów
  przed/po na tych samych wejściach: oba kierunki, A/B, ID, kolejność, ceny,
  sumy i linki. Osobno udowodnić brak poszerzenia dawnych relacji przez NRN.
- Obecne historyczne JS „ninth RZE”, „tenth BZG”, „eleventh LUZ” mają pozytywne
  zbiory 8/9/10. Zachować je; nie zamieniać ich fixture na bieżące 13 ani
  nie definiować historii odejmowaniem wyłącznie najnowszego kodu.
- Dotychczasowe realne testy LUZ muszą dalej przechodzić na nowym stagingu.
  Nie kopiować do nowych testów założenia, że każdy endpoint ma oba kierunki.
  RDO=0 ma jawny poprawny test coverage/zera, nie skip udający odbiór lotu.

### 13.3. Ceny, czas i UI

- Ryanair FR/RK i UX: wiele rejsów dnia, wszystkie offer groups, własna cena;
  limity/retry/cache, brak fallbacków, oficjalne końcowe imports oraz WDC.
- Brak/przeterminowane opłaty, różny run/window/NBP/hash, failed sidecar,
  malformed response, GraphQL errors przy 200 — zachowują starą publiczną bazę.
- 115/119 min odrzucone, 120/1440 przyjęte, 1441 odrzucone; różny IATA,
  przerwana chronologia i dwa transfery odrzucone. Test NRN vs DUS i LCA vs PFO.
- Granice dat, UTC/IANA/DST 25.10.2026, +1 i obie nogi odlotów w oknie.
- JS: SZY samo, RDO samo (syntetyczny), oba + stare porty OR, 4 tryby
  resident/WDC, 8 rzeczywistych sortów: `price`, `regular`, `layover`,
  `departure`, `journey`, `departure_time`, `arrival_time`, `direct`.
- Zgodne minima i kwoty, data/słupek → to samo ID, karty/szczegóły/+1,
  chipy/resety/cache i share >1000. Przed każdym scenariuszem po share
  ustawić porty od nowa — share celowo je czyści, nie zmieniać tej semantyki.
- Osobne fixture: oba nowe =0, tylko SZY, tylko RDO, każdy tylko w jedną
  stronę, pełne 13 syntetycznych opcji. Nie tworzyć fikcyjnych ofert publicznych.

Komendy przed kolekcją, na stagingu i po promocji w odpowiednim zakresie:

```bash
.venv/bin/python -m unittest discover -s tests -p 'test_*.py'
node --test tests/test_airport_ui.mjs
node --check app.js
git diff --check
```

234/38 to baseline, nie obiecana liczba po zmianie. Zapisać prawdziwe pass,
fail i skip; testów realnej nowej bazy nie uznawać za odebrane przed jej zebraniem.

## 14. Etap I — jedna pełna nowa kolekcja trzynastu

Dopiero po zamknięciu audytów, decyzji, Wizz, konfiguracji i testów:

```bash
.venv/bin/python scripts/collect_five_steps.py --from-date YYYY-MM-DD --days 30 --stage-directory tmp/szy-rdo-expansion/batch-YYYY-MM-DD-RUN --workers 2
```

Wyłącznie nowy niekolidujący staging, nowy run UUID i świeży cache Ryanaira,
bez cen/cache LUZ. `RUN` w nazwie katalogu jest etykietą, UUID nadaje runner.
Kolejność sekwencyjna `1, 1b, 1c, 1d, 1e, 1f, 2, 3, 4, 5`.
Jedna konfiguracja trzynastu zamrożona przed startem, jeden D/NBP/config hash.
Nie dopisywać Radomia w połowie batcha Szyman i nie doklejać dwóch nowych
portów do starych feedów jako rzekomo jednego runu.

Publiczne 20 plików pozostają identyczne z baseline aż do promocji.
Nie uruchamiać próbnego kolektora z domyślnym output `data/`: failure może
nadpisać publiczny sidecar na failed obok starego feedu. Wszystko w stagingu.

Przed retry zachować failed `validation-report.json`, `stepX.log` i sidecar
w osobnym katalogu próby; runner je nadpisuje. Nie oczekiwać automatycznego
osobnego `.failed.json`. Ponowić tylko nieudany i niewykonane późniejsze
kroki, z tym samym D/run/hash/cache:

```bash
.venv/bin/python scripts/collect_five_steps.py --from-date YYYY-MM-DD --days 30 --stage-directory tmp/szy-rdo-expansion/batch-YYYY-MM-DD-RUN --workers 2 --run-id UUID_Z_PIERWOTNEGO_RAPORTU --refresh-steps 3 4 5
```

Przykład dotyczy błędu 3. Po błędzie 1C: `1c 1d 1e 1f 2 3 4 5`;
po błędzie 5: tylko `5`. Nie restartować poprawnie ukończonych wcześniejszych
feedów bez przyczyny. Nie osłabiać walidacji ani zmieniać Google parsera
w środku runu. Zmiana konfiguracji/dat/semantyki cache wymaga nowego spójnego runu.

Validator wymaga też daty generacji zgodnej z aktualnym dniem Canary.
Start tuż przed północą grozi odrzuceniem wcześniejszych feedów po północy.
Zarezerwować czas; gdy przekroczono dzień, jawnie rozstrzygnąć zwykle nowy
pełny batch dla nowego D. Nie przepisywać timestampów, kursów i certyfikatów.
Poprzednia pełna kolekcja jedenastu trwała około 87 minut; nie jest to ETA
nowego przebiegu ani gwarancja braku ponowień.

## 15. Etap J — odbiór danych, strony i lokalna promocja

Przed `--validate-only` zachować oryginalny pełny `validation-report.json`
jako `collection-complete-report.json`: walidacja nadpisuje raport i może
nie zachować pierwotnych pól hash/cache. Zachować metadata i logi.

```bash
.venv/bin/python scripts/collect_five_steps.py --from-date YYYY-MM-DD --days 30 --stage-directory tmp/szy-rdo-expansion/batch-YYYY-MM-DD-RUN --validate-only
RESIFLY_TEST_DATA_DIRECTORY=tmp/szy-rdo-expansion/batch-YYYY-MM-DD-RUN node --test tests/test_airport_ui.mjs
```

Obowiązkowy raport przed promocją:

1. Wszystkie 10 schema-v2 feedów i 10 identycznych sidecarów: jeden run,
   okres, dzień generacji, kursy, aktualny config hash i cache identity.
2. Complete coverage 13, zero missing/unexpected, NRN i inne zaakceptowane
   nowe nogi w plannerze i executorze; szczegóły 1F zgodne z kalendarzem.
3. Dokładna równość planowanej unii route/day Ryanaira i unikalnych dobrych
   rekordów cache `google_flights_http`, bez starych/dodatkowych obserwacji.
4. Tabele wszystkich feedów, endpointów, kierunków, wariantów A/B i hubów.
   Dla SZY/RDO osobno: znalezione wszystkie vs widoczne domyślnie 1000/6 h.
5. Uzasadnienia zer: brak topologii, poprawnie pusty kalendarz, godziny poza
   120–1440, sezonowość lub filtr UI. Awaria źródła nie trafia do kategorii zero.
6. Próbki każdej aktywnej rodziny nowych portów, obie strony jeśli istnieją,
   ceny/numery/godziny/sumy i booking URLs; +1 jeśli istnieje w rzeczywistych danych.
   Jeśli RDO=0, pokazać dowód pełnego sprawdzenia zamiast nieistniejącej próbki.
7. Testy zamrożonej jedenastki, nowe testy i kontrola sidecarów/sources/linków,
   brak secrets/session i brak filtrowania ceny w danych.
8. Publiczne 20 nadal bajtowo równe baseline przed promocją — zachować wynik
   jako `pre-promotion-acceptance-report.json` albo równoważny raport.

Browser QA na izolowanej kopii statycznej ze stagingiem albo po bezpiecznej
promocji lokalnej. Nie zmieniać produkcyjnych ścieżek loadera ani nie mieszać
połowy nowych feedów ze starą bazą. Desktop/320 px, menu/etykiety, OR, kierunki,
zniżki/sorty, daty i słupki, karta/share/+1/resety, konsola i systemowy schowek.
Sprawdzić ponowne otwarcie skopiowanego linku oraz parametry zakupu, bez
rezerwacji/płatności. Jeżeli sterowanie przeglądarką niedostępne, jawnie
zapisać otwarty odbiór; HTTP/Node nie poświadczają kontroli wizualnej/schowka.

Po pełnym odbiorze, w zakresie przyszłego polecenia lokalnego wdrożenia:

```bash
.venv/bin/python scripts/collect_five_steps.py --from-date YYYY-MM-DD --days 30 --stage-directory tmp/szy-rdo-expansion/batch-YYYY-MM-DD-RUN --validate-only --promote
```

Promocja ponownie waliduje i podmienia **całe 20** plików z backupem
`previous-public-feeds/`. Obsłużony błąd podmiany przywraca poprzedni zestaw,
ale 20 rename nie jest jedną transakcją odporną na nagłe zabicie/zasilanie.
Nie usuwać niezależnego baseline.

Po promocji: publiczne 20 = staging, backup 20 = baseline bajtowo;
`validate_batch` publicznej bazy, Python/JS, składnia i `git diff --check`.
HTTP ma podawać nowe bajty `index.html`, `app.js` i **wszystkich 20 JSON**,
nową wersję JS/run/okno. Sam `?build=` nie dowodzi aktualności danych.
Zachować `cache: "no-store"` loadera.

Nie dublować działającego serwera. Jeżeli go brak, uruchomić z projektu:

```bash
cd "/Users/piotr/Documents/iCloud Developer/ResiFly"
.venv/bin/python -m http.server 8000 --bind 127.0.0.1
```

Podgląd: `http://127.0.0.1:8000/?build=szy-rdo-local-YYYYMMDD`.
Nie uruchamiać względnej `.venv` z katalogu domowego.

## 16. Dokumentacja końcowa, rollback i osobna publikacja

Utworzyć `docs/WDROZENIE_SZYMAN_I_RADOMIA_SZY_RDO.md` z rzeczywistymi:

- HEAD/status/baseline i datami; oba niezależne audyty, raw intersections,
  źródła/błędy/sezony/pending/decyzje wszystkich 1A–1F, 2, 3, 4, 5A/5B;
- nowym NRN i innymi rzeczywiście zaakceptowanymi hubami/TFN/TFS,
  zachowanymi starymi uprawnieniami i dokładną polityką GDN;
- Wizz obserwacjami/override, fee validity, metodami cen/URL;
- run/D/oknem/NBP/config hash/cache i pełnymi tabelami coverage/wyników,
  osobnymi liczbami SZY/RDO i ofert widocznych przy domyślnych filtrach, powodami zer;
- błędami/retry bez restartu udanych feedów, wynikami testów/HTTP,
  zakresem wizualnego odbioru/schowka, backupem/promocją i stanem Git.

Bieżące instrukcje/rejestry/opis strony uaktualnić do 13 podczas wdrożenia.
Historyczne plany i faktyczne raporty WRO/POZ/LCJ/RZE/BZG/LUZ pozostają
historyczne; nie przepisywać ich liczb na trzynaście.

Rollback to spójny powrót **kodu + rejestrów + konfiguracji + 20 plików**
do baseline jedenastu, z zachowaniem cudzych zmian. Same stare feedy pod
konfiguracją 13 nie są poprawnym rollbackiem. Bez `reset --hard`, globalnego
odrzucania zmian i kasowania workspace. Nie wycofywać poprawnego wdrożenia
prewencyjnie; zachować dowody i poprosić o decyzję przy konflikcie.

GitHub tylko po osobnym poleceniu: status/diff i remote HEAD, jawne staging
powiązanych źródeł/testów/docs oraz wszystkich 20 nowych danych, commit i
zwykły push do uzgodnionego celu bez force. Bez `tmp/`, cache, backupów,
logów i sekretów. Poprzedni push LUZ nie upoważnia do publikacji SZY/RDO.
Ten plan również nie uruchamia ani nie tworzy workflow GitHub Actions.

Przyszłe Actions mają użyć tego samego rejestru/requirements/runnera,
sekwencyjnej kolekcji, jednego NBP/run/cache, Google max2 i bramek coverage.
Discovery osobno, dry-run/artefakt/review przed apply. Sam push strony
nie jest dowodem gotowego automatycznego odświeżania.

## 17. Checklista przyszłego wykonawcy — jeszcze niewykonana

- [ ] Osobne polecenie wdrożenia, aktualne instrukcje/status i pełny baseline 11.
- [ ] SZY/RDO w rejestrze ze strefami, wszystkie 9 scope; GDN tylko 5B/KRK,LUZ.
- [ ] Dwa świeże audyty pełnych grafów i oficjalnych siatek, nowe globalne huby.
- [ ] Zamknięta tabela 1A–1F, 2, 3, 4, 5A/5B osobno dla każdego endpointu.
- [ ] SZY/STN i kompletny nowy NRN sprawdzone, bez pomylenia NRN/DUS/DTM.
- [ ] RDO sprawdzony bez LCA/PFO, LOT/czarterów lub dwóch transferów; uczciwe zera.
- [ ] Binter source failure i port Radom 403 nie zamienione na brak dostępności.
- [ ] Nowe Wizz nogi obu kierunków zweryfikowane albo jawne pending/inactive.
- [ ] Helper bez utraty SZY przy RDO, ukrytego live schedule i starych override.
- [ ] Planner/executor/coverage całych 13; 52/104/3224 oraz 10416/1736 przy starych hubach.
- [ ] Źródła cen, final imports, opłaty ważne w całym oknie, deterministyczne URL.
- [ ] Zamrożone stare 11 i wcześniejsze historie bez regresji; NRN end-to-end.
- [ ] Testy SZY/RDO: osobno/razem/zero/jeden kierunek, syntetyczne 13, 4 tryby/8 sortów.
- [ ] Jeden pełny świeży batch 13, 10 feedów/10 sidecarów, jeden D/run/NBP/hash/cache.
- [ ] Google max2, retry tylko niedokończonych, publiczna baza nienaruszona do promocji.
- [ ] Zero missing/unexpected, cache dokładnie równy nowej unii planu Ryanaira.
- [ ] Tabele i dowody SZY/RDO, domyślne filtry i powody zer, bez fikcyjnego checkboxa RDO.
- [ ] Staging QA, HTTP, wizualny odbiór/schowek lub jawnie zapisane ograniczenia.
- [ ] Lokalna promocja całych 20, bajtowe porównania/backup, ponowna walidacja i raport.
- [ ] Bez commita/push/Actions do osobnego polecenia publikacji.

## 18. Gotowy brief dla Codexa

Po osobnym zleceniu wdróż razem SZY i RDO zgodnie z tym planem oraz aktualnymi
instrukcjami. Dwa niezależne audyty pełnych siatek, w tym huby zupełnie nowe,
potem kompletna połączona konfiguracja i testy, a na końcu jeden świeży
pełny batch trzynastu do nowego stagingu/runu. Nie ograniczaj audytu do starych
allowlist. Sprawdź nowy NRN i STN dla SZY; nie obiecuj Radomiowi połączeń,
jeśli zgodnie z obecnymi liniami i jedną przesiadką ich nie ma.

Zachowaj starą jedenastkę, dokładnie pięć kroków, pełne niezależne kalendarze,
120–1440 minut, źródła cen, końcowe imports, kierunkowe opłaty, limit Google 2,
jedno NBP i deterministyczne linki. Nie rozszerzaj zgody GDN poza 5B/KRK,LUZ.
Nie dodawaj LOT-u/czarterów/dojazdów/drugiej przesiadki. Nie nadpisz zmian
SZY generatorem RDO i nie zgub nowych hubów przez ograniczenia helpera.

Przetestuj nowy NRN, oba endpointy i przypadki zerowe oraz zamrożoną
jedenastkę. Po walidacji 10 feedów/10 sidecarów i odbiorze strony podmień
cały zestaw wyłącznie lokalnie, z backupem i raportem rzeczywistych
wyników/ograniczeń. Niczego nie wysyłaj na GitHub bez kolejnej osobnej zgody.
