# Plan dodania Szczecina (SZZ) i Zielonej Góry (IEG) oraz przyspieszenia kolekcji

Plan wykonawczy z **24.10.2026**, po publikacji SZY/RDO i NRN.
Baseline HEAD: **`8a50db3704efd708f5b0c3723be93b7e564d7b10`**.
Checkout `codex/add-lodz-lcj` ma historyczną nazwę; nie określa zakresu planu.
Przed przygotowaniem dokumentu checkout był czysty.

**Status historyczny w chwili sporządzania planu:** odczytano kod, zweryfikowano obecną bazę,
pobrano oficjalne pełne mapy tras FR/Wizz i przejrzano źródła przewoźników.
Nie uruchomiono nowych kalendarzy cen, nie dodano endpointów ani allowlist,
nie zmieniono kolektorów, strony, publicznych feedów, limitów ani workflow.
Nie wykonano commita/push. Lokalne dowody planowania są w `tmp/szz-ieg-plan/`.

**Wdrożenie lokalne rozpoczęte 24.10.2026 na osobne polecenie użytkownika.**
Stan wykonania, testy i odbiór opisuje
[`WDROZENIE_SZCZECINA_I_ZIELONEJ_GORY_SZZ_IEG.md`](WDROZENIE_SZCZECINA_I_ZIELONEJ_GORY_SZZ_IEG.md).
Nie traktować historycznego opisu planowania powyżej jako bieżącego stanu kodu.

**Aktualizacja polityki 24.10.2026:** użytkownik trwale zatwierdził wszystkie
krajowe przesiadki w Polsce, bez dalszych zgód dla poszczególnych portów.
Plan obejmuje teraz również migrację tej ogólnej reguły dla całej siatki.
Pierwotna projekcja ograniczona do zagranicznych hubów jest nieaktualna.

## 1. Zatwierdzone nowe zasady i granice zlecenia

Użytkownik wybrał docelowo:

1. Dodać razem **Szczecin–Goleniów (SZZ)** i **Zieloną Górę–Babimost (IEG)**,
   przechodząc z trzynastu do piętnastu endpointów.
2. Przy właściwej pełnej kolekcji zastosować **Google Flights maksymalnie 3**,
   bez osobnej żywej próbki „2 vs 3” i bez dwóch pełnych pobrań dla benchmarku.
3. W Google w danej chwili obsługiwać **jedną rodzinę przewoźnika**; pozostałe
   rodziny czekają. Nie 3 dla Ryanaira plus 3 dla Air Europa.
4. Równolegle do Google mogą pracować **niezależne źródła bezpośrednie**:
   Wizz Air, Binter, Canaryfly i Volotea, z osobnymi ograniczeniami obciążenia.
5. Ocenić efekt na pierwszej właściwej kolekcji, mierząc czas i błędy.
   Trzy nie są potwierdzonym limitem Google ani gwarancją braku blokad.
6. Wszystkie polskie huby są dozwolone także na przyszłość. Nie prosić o
   zgodę na SZZ/KRK ani inne krajowe połączenie. To zmiana ogólnej polityki,
   nie tylko kolejny wyjątek i nie tylko rozszerzenie dla nowych endpointów.

W obecnym kodzie nadal jest `GOOGLE_FLIGHTS_MAX_WORKERS = 2`, a runner jest
sekwencyjny. **Trzy i równoległe źródła nie są jeszcze wdrożone.** Podczas
realizacji zsynchronizować nowe reguły z `AGENTS.md`,
`FIVE_STEP_FLIGHT_SEARCH.md`, `COLLECTION_RELIABILITY.md`, README i testami;
nie udawać, że samo ustalenie w rozmowie zmieniło działanie skryptów.

To zlecenie przygotowania planu nie upoważnia jeszcze do pełnej kolekcji,
podmiany strony lub kolejnego push. Pierwszy odbiór realizacji zaplanować
lokalnie; publikacja wymaga osobnego polecenia.

## 2. Docelowy rejestr i niezmienne zasady produktu

Zachować kolejność obecnej trzynastki, dopisać SZZ i IEG:

**WAW, WMI, KTW, KRK, GDN, WRO, POZ, LCJ, RZE, BZG, LUZ, SZY, RDO, SZZ, IEG**.

Rekordy w `data/search-airports.json`, dopiero przy wdrożeniu:

```json
{ "iata": "SZZ", "name_pl": "Szczecin–Goleniów", "timezone": "Europe/Warsaw" }
{ "iata": "IEG", "name_pl": "Zielona Góra–Babimost", "timezone": "Europe/Warsaw" }
```

To przykładowe elementy tablicy, nie samodzielny dokument JSON. IEG nie jest
aliasem WAW ani lotniskiem w Niemczech. SZZ nie oznacza miejskiego Dąbia.
Odczytywać rejestr przez `scripts.search_airports`, nie mnożyć lokalnych list.

Bez zmian pozostają:

- **Pięć kroków**, warianty 1A–1F, **10 feedów + 10 sidecarów, 9 allowlist**.
  Fazy techniczne pobierania/budowania nie tworzą szóstego kroku wyszukiwania.
- D z `Atlantic/Canary`; D–D+30 to **31 dat włącznie**. Nowy batch zaczyna
  od świeżych danych, nie używa cen poprzedniego uruchomienia.
- Każda zapisana trasa/linia ma niezależny pełny kalendarz obu kierunków.
  Jedna linia nie wyznacza dni zapytań drugiej. Najpierw kalendarze, potem pary.
- Maksymalnie jedna przesiadka w **tym samym IATA**, 120–1440 min włącznie,
  chronologia UTC/IANA/DST; poprawne +1 i własna data odlotu każdej nogi.
- Brak LOT-u, Norwegian, czarterów, zmiany lotniska, dojazdów i drugiej
  przesiadki bez osobnej decyzji. Brak wyników nie uzasadnia takiego rozszerzenia.
- Kolektor nie odrzuca cen. UI nadal Polska → Teneryfa, **1000 zł / 6 h /
  najbliższy termin**. Regularna/rezydenta/WDC zachowane oddzielnie.
- Dotychczasowe reguły końcowych cen Binter/Canaryfly, estymat z opłatami,
  indywidualnych ofert Google i deterministycznych linków pozostają wiążące.
- Pełna lokalna podmiana tylko po kompletnym, spójnym odbiorze całych 20 plików.

## 3. Sprawdzony stan trzynastu i zakres porównania

Odczyt i `validate_batch` dla aktualnego `data/` potwierdziły na etapie planu:

- Okno **2026-10-24–2026-11-23**; run
  **`d98ec327-3fa9-40bd-9a9a-6da358c35bfa`**.
- **15 954 propozycje**, pełne **39 308** pozycji pokrycia, zero braków/nadmiarów.
- Bazowy plan ma 39 184 pozycji; pozostałe 124 to szczegóły Canaryfly
  wymagane przez zebrane miesięczne kalendarze. Nie zamrażać tej liczby na przyszłość.
- 19 282 unikalne route/day Ryanaira; jeden zestaw kursów NBP.
- 35 SZY przez STN; RDO zero. NRN pozostaje skonfigurowany mimo braku
  SZY↔NRN w tym oknie. Nie usuwać go podczas rozszerzenia SZZ/IEG.

Raport poprzedniej realizacji: `WDROZENIE_SZYMAN_I_RADOMIA_SZY_RDO.md`.
246 Python / 42 JS to udokumentowany odbiór tamtej realizacji, nie wynik
przyszłego nowego kodu. Przy wdrożeniu powtórzyć i rozszerzyć testy.

Poprzedni runner nie utrwalał pełnej telemetrii HTTP/monotonicznej każdego
źródła. Daty generowania feedów i czasy plików nie wystarczają do uczciwego
benchmarku całej kolekcji. Nie obiecywać „dwa razy szybciej” ani przypisywać
całej różnicy limitowi Google: zmienia się również zakres 13 → 15.

## 4. Faktyczny audyt tras podczas planowania

Odczytano pełne oficjalne grafy **24.10.2026**, nie tylko obecne huby:
Ryanair 5317 kierunkowych krawędzi, Wizz 2584. Oba odczyty zakończyły się
poprawnie. Surowy snapshot zachowano przed filtrem polityki.

Źródła: [Ryanair routes](https://www.ryanair.com/api/views/locate/3/routes),
[Ryanair airports](https://www.ryanair.com/api/views/locate/3/airports/en/active),
[oficjalna mapa Wizz](https://www.wizzair.com/en-gb) przez endpoint `asset/map`.
Odczyt grafu tras nie jest pobraniem kalendarza cen ani dowodem operowania
każdego dnia w kolejnym miesiącu.

| Endpoint | Wszyscy sąsiedzi FR w grafie | Wszyscy sąsiedzi Wizz w grafie | Kandydaci zgodni z obecną polityką |
| --- | --- | --- | --- |
| SZZ | DUB, KRK, LPL, STN | BGO, OSL | Krok 3: TFS przez DUB, KRK, LPL, STN |
| IEG | brak | brak | Na dziś brak 3/4/5A/5B |

W żadnym z dwóch grafów nie było bezpośredniego SZZ/IEG↔TFN/TFS. Nie zwalnia
to z pełnej macierzy kroku 2. Wizz/Wizz i oba mieszane warianty nie dały
obecnie wspólnych IATA. Nie zastępować OSL lotniskiem TRF ani STN lotniskiem LTN.

### 4.1. Szczecin: trzy zagraniczne huby, nie tylko sprawdzenie starych wpisów

Pełne przecięcie grafów daje DUB, LPL, STN i surowego KRK dla FR/FR.
DUB/LPL/STN są już globalnie w naszej liście: dopisać do nich **SZZ**, bez
nowego globalnego huba i bez poszerzania uprawnień innych endpointów.
Sprawdzić każde z czterech skierowań endpoint↔hub↔TFS przez pełne okno.
Godziny i ceny dopiero z właściwej kolekcji Google; nie przenosić rozkładu
innego polskiego miasta na Szczecin.

[Oficjalny rozkład SZZ](https://airport.com.pl/loty/rozklad-przylotow-odlotow/)
potwierdza wymienione kierunki oraz sezonowość KRK. Zawiera m.in. literówkę
zakresu roku przy DUB i zmienne numery/godziny STN, więc nie jest szablonem
bieżących rejsów Google. Nie poprawiać tych danych arbitralnym zgadywaniem.
Surowy kandydat sezonowy może istnieć mimo braku lotów w aktualnym oknie.

### 4.2. Wszystkie krajowe przesiadki są trwale zatwierdzone

Graf rzeczywiście pokazuje **SZZ–KRK–TFS Ryanair/Ryanair**. Obecny kod jeszcze
usuwa KRK jako nasz endpoint. Użytkownik 24.10.2026 zatwierdził jednak na stałe
**wszystkie krajowe przesiadki**. Ten kandydat nie wymaga już dodatkowej zgody.
Zachować surowy dowód trasy i przeprowadzić normalną weryfikację kalendarzy,
nie udawać, że zgoda gwarantuje aktualny lot lub właściwą godzinę.

Podczas realizacji:

- Zapisać ogólną politykę w kanonicznym rejestrze i wspólnym loaderze;
  szczegółowy schemat dopracować z testami, bez ręcznych wyjątków na każdą parę.
- Zmienić `candidate_intersection`, `validate_polish_transfer`, helper,
  walidatory konfiguracji i właściwe macierze kroków 3/4/5 tak, aby port
  w Polsce nie był odrzucany wyłącznie dlatego, że jest endpointem.
- Ponownie przejrzeć krajowe przecięcia **wszystkich piętnastu endpointów**,
  w tym starej trzynastki i nowych globalnie krajowych hubów. Nie dopisać
  wyłącznie SZZ/KRK i nie zostawić dawnych ukrytych wykluczeń innych portów.
- GDN dla KRK/LUZ pozostaje legalny, ale nie jest już jedyną uprawnioną parą.
  Historyczne `endpoint_transfer_exceptions` nie mogą blokować nowej reguły.
- Dla każdego rzeczywistego kandydata nadal ustalić linie, TFN/TFS, oba
  kierunki, numery/czasy i pełne kalendarze; aktualizować allowlisty po review.
  Zgoda nie nakazuje automatycznej redetekcji podczas zwykłego odświeżania cen.
- Nie dodawać LOT-u/Norwegian/czarterów, drugiej przesiadki, zmiany IATA,
  self-routes lub odcinka do tego samego portu. Noga kończąca się w Hiszpanii
  nie staje się rezydencka tylko dlatego, że poprzedza ją lot krajowy w Polsce.

Przeliczyć plan source/coverage i fixtures po pełnym audycie krajowych tras.
Nie używać pierwotnej projekcji z dawnym zakazem jako docelowej walidacji.

### 4.3. Zielona Góra: możliwe uczciwe zero

IEG nie wystąpił jako aktywny port w pobranych grafach FR/Wizz; oba odczyty
były kompletne, a nie zastąpione pustą listą po błędzie. Nie oznacza to braku
całego ruchu pasażerskiego z Babimostu.

[Oficjalny LOT](https://www.lot.com/pl/pl/loty/loty-z-polski/loty-z-zielonej-gory)
opisuje połączenie do Warszawy i ofertę z przesiadką; nie traktować reklamowanej
listy dalszych miast jako bezpośrednich krawędzi IEG. LOT nie jest obecną
polską nogą żadnego z naszych pięciu kroków. Nie dodawać go pod pozorem
wdrażania endpointu ani nie kopiować cen z reklam do Google/Wizz.

IEG dodać do wszystkich obowiązkowych macierzy. Jeśli pełna kolekcja nadal
zwróci zero, tak napisać w odbiorze i nie fabrykować karty ani checkboxa.
Brak w grafie nie upoważnia do pominięcia kalendarzy 1A/1B/2.

### 4.4. Warianty rezydenckie: odrębna kwalifikacja wszystkich sześciu

Wszyscy aktualni sąsiedzi SZZ leżą w Polsce/Irlandii/Wielkiej Brytanii/Norwegii,
a IEG nie ma polskiej nogi FR/Wizz. Nie ma zatem dzisiaj wspólnego
hiszpańskiego/kanaryjskiego huba uprawnionej nogi krajowej 1A–1F.
To wniosek z pełnej polskiej siatki i zasad eligibility, nie z ograniczenia
przeglądu do dawnych list lub z błędu Bintera.

Przejrzano oficjalne materiały:
[Binter](https://www.bintercanarias.com/es/destinos),
[Iberia](https://www.iberia.com/es/vuelos-baratos/Tenerife-Madrid/),
[Vueling](https://www.vueling.com/es/vuelos-baratos-desde-tenerife),
[Air Europa](https://www.aireuropa.com/es-es/ofertas-de-vuelos-desde-tenerife),
[Volotea](https://www.volotea.com/es/ofertas-vuelos/tenerife/),
[Canaryfly](https://www.canaryfly.es/en/cheap-flights).
Strony ofertowe nie dowodzą kompletności rozkładu ani bezpośredniości każdej
reklamowanej podróży. Nie pobierano teraz kalendarzy/imports ani nie zgłaszamy
świeżego sukcesu Binter `timetable_get`. Dawny E01000 nie jest wynikiem „zero”.

Przy realizacji ponowić pełny audyt i kwalifikację oddzielnie dla każdego
wariantu. Jeśli pojawi się hiszpański sąsiad, sprawdzić również nowy globalnie
hub: oficjalną trasę z konkretnego TFN/TFS, zniżkę, obie linie, oba kierunki,
strefę i fee registry. Vueling z własnej strony tras, Aena tylko pomocniczo.

### 4.5. Dowody i ograniczenia aktualnego planu

`tmp/szz-ieg-plan/network-snapshot.json` — pełne grafy i statusy;
`route-review.json` — surowe/przefiltrowane kandydatury, oba porty osobno;
`coverage-projection.json` — wyłącznie obliczenia offline. Zachowano również
nieudany odczyt DNS w sandboxie przed udanym połączeniem z uprawnieniami sieci.
Porażki nie zamieniono w potwierdzone zera. Pliki `tmp/` nie są publiczną bazą.

## 5. Dlaczego obecnego runnera nie wolno po prostu uruchomić równolegle

Przegląd kodu wykazał:

1. `collect_five_steps.py` uruchamia dziesięć subprocessów **kolejno**.
   W poszczególnych `main()` najpierw zbierane są low-cost, a dopiero potem
   drugi przewoźnik. Binter może więc czekać na Google, choć to inny serwis.
2. `collector_settings.py` ustala 2; `ryanair_google.py` ma własny
   `threading.BoundedSemaphore`. To limit **jednego procesu**, nie wszystkich
   subprocessów lub innych klientów Google. 3 równoległe procesy mogłyby
   wysłać po 3, a nie 3 łącznie.
3. Wspólny `GoogleFlightsClient` z `collect_step1b.py` obsługuje również
   Vueling, Air Europa, Ryanair i techniczne sprawdzenia Wizza. Nie ma dziś
   wspólnego międzyprocesowego właściciela rodziny Google.
4. Cache Ryanaira jest współdzielony w runie, ale zapisy JSONL i blokady
   `_cache_lock` są procesowe. Nie projektowano go jako wielu równoległych
   piszących procesów. Są też potencjalnie dublowane odczyty tego samego klucza.
5. Wizz jest zbierany wielokrotnie w różnych krokach i przez różne funkcje
   `collect_wizz_route`/`wizz_timetable`. Trzeba zachować osobno regular/WDC
   oraz zgodność wspólnych i lokalnych schedule 1A/1B.
6. `collection_coverage._active` to **jeden globalny tracker procesu**.
   Nie uruchamiać dziesięciu decorated `main()` w jednym ThreadPoolExecutor:
   raporty mogłyby trafić do obcego kroku lub wejścia odmówią uruchomienia.
7. Importy/`configure_airports_from_allowlist` i dane techniczne mają stan
   modułowy. Nie zmieniać go jednocześnie podczas kolekcji różnych źródeł.
8. Pierwszy odczyt NBP i rozwiązanie wersji Wizz trzeba wykonać przed startem
   pul. Inaczej można zdublować odczyty/zapisy lub rozjechać metadane.
9. Ryanair ma ponowienia parsera wokół klienta mającego własne ponowienia HTTP.
   Podniesienie workers nie może przypadkowo zwiększyć również budżetu retry.

Samo `GOOGLE_FLIGHTS_MAX_WORKERS = 3` albo kilka poleceń w tle **nie realizuje
ustalonej polityki**. Wymagane są kolejki źródeł, jeden właściciel Google,
wspólne poprawne obserwacje i budowanie wyników bez dalszej sieci.

## 6. Mapa plików wdrożenia

| Obszar | Istniejące pliki / zakres |
| --- | --- |
| Endpointy | `data/search-airports.json`, `scripts/search_airports.py`: oba nowe porty, strefy i ogólna zgoda krajowych hubów zamiast wyjątków dla każdej pary. |
| Instrukcje | `AGENTS.md`, `docs/FIVE_STEP_FLIGHT_SEARCH.md`, `docs/COLLECTION_RELIABILITY.md`, `README.md`: zakres 15, globalne Google 3, jedna rodzina i równoległe serwisy. |
| Audyt | `scripts/audit_airport_expansion.py`, `scripts/discover_transfer_routes.py`: pełne sieci, raw przed polityką, własne dowody SZZ/IEG. |
| Konfiguracja | `scripts/build_gdn_config_patch.py`, wszystkie 9 `data/*transfer-airports.json`: łączenie zmian i zakresów, SZZ/DUB/LPL/STN. |
| Wizz technical | `scripts/verify_wizz_expansion_schedules.py`, `scripts/wizz_schedules.py`, `scripts/wizz_api.py`, `data/wizz-route-schedules.json`, lokalne schedule 1A/1B. |
| Runner | `scripts/collect_five_steps.py`: plan źródeł, równoległe pule, fazy, cache-only builders, telemetry, resume, preflight/promotion. |
| Google | `scripts/collector_settings.py`, `scripts/collect_step1b.py::GoogleFlightsClient`, `scripts/ryanair_google.py`, klienci w 1B/1C/1D i verifier Wizza. |
| Oficjalne źródła | `scripts/collect_step1.py`, `collect_step2.py`, `collect_step4.py`, `collect_step1e.py`, `collect_step1f.py`: wspólne adaptery źródeł, bez utraty obecnych walidacji. |
| Builders 10 | `scripts/collect_step1.py`, `collect_step1b.py` … `collect_step1f.py`, `collect_step2.py` … `collect_step5.py`: osobny zakres kroku i odczyt bieżącego cache. |
| Pokrycie | `scripts/collection_coverage.py`: plan niezależny od ofert, poprawna ewidencja źródła/wielu konsumentów, Canaryfly calendar/details. |
| Ceny/linki | `scripts/spanish_resident_fees.py`, fee JSON i `scripts/booking_urls.py`: regresja, nie wymiana zasad. |
| UI | `app.js`, `index.html`; CSS tylko przy rzeczywistym problemie układu. |
| Testy | Testy source/batch/Google/ekspansji i `tests/test_airport_ui.mjs`; nowe testy SZZ/IEG oraz source pipeline/scheduler. |
| Odbiór | Nowy `docs/WDROZENIE_SZCZECINA_I_ZIELONEJ_GORY_SZZ_IEG.md`, osobne raporty sieci/cen/wydajności. |

Proponowane **nowe moduły**, nazwy do utworzenia dopiero podczas realizacji:
`scripts/source_plan.py`, `source_repository.py`, `source_scheduler.py`,
`collection_metrics.py`. Odpowiedzialności opisane niżej; nie są to obecnie
dostępne narzędzia ani dodatkowe kroki wyszukiwania.

## 7. Etap A — bezpieczny baseline i konfiguracja piętnastu

1. Na świeżo odczytać instrukcje, status, HEAD, D i istniejące zmiany.
   Zachować wszystkie niezwiązane pliki, nie robić globalnego resetu.
2. Utworzyć nowy `tmp/szz-ieg-expansion/baseline-RUN/`, bez nadpisania dawnych
   backupów. Kopia kodu, instrukcji, testów, UI, rejestru, 9 allowlist,
   shared/local schedules, fee table i wszystkich **20** publicznych plików.
   Manifest SHA-256, run/okno/NBP starej bazy, stan indeksu i HEAD.
3. Zamrozić literalny **THIRTEEN** równy obecnej trzynastce. Zachować także
   historyczne SIX–ELEVEN; nie robić historii przez `POLISH_AIRPORTS[:-2]`.
4. Dopisać **oba** endpointy do rejestru. Restartować procesy po edycji:
   stałe i `choices=POLISH_AIRPORTS` są rozwiązywane przy imporcie.
5. Zebrać aktualne pełne grafy i decyzje obu endpointów. Do czasu rejestracji
   nie uruchamiać audytu jako rzekomego LUZ/RDO zamiast SZZ/IEG.
6. Dla IEG brak metadata FR/Wizz uzupełnić z rzeczywistego rejestru endpointu
   i oficjalnych źródeł, nie z udawanego aktywnego węzła przewoźnika.
7. Oddzielić nowe wyniki dawnych portów od zakresu SZZ/IEG. Nie stosować
   globalnego detector `--apply` bez przeglądu każdej zmiany.

Komendy istniejących narzędzi, **po rejestracji i przy wdrożeniu**, z prawdziwym D:

```bash
.venv/bin/python scripts/audit_airport_expansion.py --endpoint SZZ --as-of YYYY-MM-DD --output-directory tmp/szz-ieg-expansion/audit-SZZ
.venv/bin/python scripts/audit_airport_expansion.py --endpoint IEG --as-of YYYY-MM-DD --output-directory tmp/szz-ieg-expansion/audit-IEG
```

Binter `timetable_get` wcześniej zwracał E01000. Jeśli znów zawiedzie, zachować
failed/source error i udane grafy low-cost; osobny oficjalny katalog/rozkład
ma domknąć decyzję 1A. `--low-cost-only` oznacza not_checked, nie complete.
Nie zmieniać błędu discovery w brak lotów i nie traktować go jako błędu
oddzielnego, prawidłowego kolektora cen `booking_search`/`booking_getImports`.

### 7.1. Każdy krok musi mieć jawną decyzję dla każdego nowego portu

| Wariant | Zakres sprawdzenia |
| --- | --- |
| 1A | Wszystkie uprawnione bezpośrednie trasy Bintera TFN/TFS przecięte ze wszystkimi sąsiadami FR/Wizz obu portów, również nowe globalne huby. Pełne niskokosztowe macierze wszystkich endpointów nadal obowiązkowe. |
| 1B | Osobny przegląd Iberia/Express i eligibility; nie zakładać na zawsze tylko MAD. Pełna macierz low-cost, pełny kalendarz Iberii niezależny od niego. |
| 1C | Własna strona Vuelinga, wszystkie wspólne kwalifikujące się IATA; `polish_routes` tylko z dowodem. |
| 1D | Oficjalna siatka Air Europa do tras, później tylko Google do aktualnych indywidualnych rejsów i cen. |
| 1E | Oficjalna siatka Volotei i MinPrice, eligibility; nie przypisywać Google. |
| 1F | Bezpośrednie Canaryfly i własna polska noga, pełne miesięczne kalendarze przed szczegółami. |
| 2 | Oba endpointy × oba Tenerife × oba kierunki × FR/Wizz; także rynki bez krawędzi w grafie. |
| 3 | Całe przecięcie FR/FR; SZZ/DUB,KRK,LPL,STN oraz pozostałe krajowe kandydatury całej siatki. |
| 4 | Całe przecięcie Wizz/Wizz, również poza dawną allowlistą. |
| 5A/5B | Każdy wariant i kierunek oddzielnie, role przewoźników geograficznie nie zmieniają się przy odwróceniu podróży. |

Tabela decyzji: endpoint, wariant, hub/TFN/TFS, przewoźnicy, źródła/datowanie,
status ready/pending_schedule/inactive_in_window/source_failed/rejected/
requires_user_decision i powód. Zero po filtrowaniu ≠ brak surowej kandydatury.

### 7.2. Wizz i bezpieczne łączenie dwóch rozszerzeń

- Zweryfikować technical schedules obu kierunków wszystkich potrzebnych nóg,
  w tym nowych hubów Teneryfy, nie tylko nowego endpointu. Używać własnych
  dowodów `--endpoint SZZ` i `--endpoint IEG`, właściwego okna i daty snapshotu.
- Jeżeli aktywne okażą się tylko bezpośrednie macierze zerowe, zachować własne
  dowody zera; nie kopiować obserwacji SZY/LUZ. Nie dodawać SZZ–BGO/OSL tylko
  po to, żeby istniały wpisy, jeśli nie tworzą zatwierdzonej trasy.
- Numery i blokowe czasy muszą być prawdziwe; data+zegar > weekday+zegar >
  sam zegar > baza. Zachować dawne wyjątki i zgodność 1A/1B/shared.
- Verifier również używa Google. Uruchamiać go **przed** batch albo przez
  tę samą blokadę/właściciela; nigdy jako ukryty dodatkowy ruch obok trzech.
  Cena Wizza nadal wyłącznie z oficjalnego timetable, nie z technicznych probe'ów.
- SZZ review z baseline, IEG review z **wyniku SZZ**, nie oba z tej samej kopii.
  Powtórzenie i odwrotna kolejność mają dawać równoważną konfigurację.
- Helper już czyta shared schedule z wybranego baseline — naprawione przy
  SZY/RDO. Zachować tę poprawkę. W razie potrzeby rozszerzyć jego opisy słowne
  o czternaście/piętnaście, bez ponownego wprowadzenia live `ROOT/data`.
- Wszystkie 9 `scope.polish_airports` równe 15; zachować stare uprawnienia
  i NRN, wdrożyć ogólną krajową zgodę zamiast ograniczenia do wyjątku GDN.
  Nowy hub tylko z pełnym rekordem/strefą/eligibility/źródłami.
- 1A/1B pełne macierze; 1C–1F tylko potwierdzone pary/carriers, nie oba
  przewoźniki z automatu. W 3 dodać SZZ do DUB/KRK/LPL/STN i zweryfikowane
  krajowe kombinacje innych endpointów; podobnie przejrzeć 4 i oba warianty 5.

## 8. Etap B — jeden plan źródeł przed pierwszym żądaniem ceny

Zaprojektować `source_plan` na podstawie **niezależnych** `expected_queries`
wszystkich dziesięciu feedów, macierzy i allowlist. Żaden plan nie powstaje
z lotów innej linii. Zbudować mapowanie: potrzeba kroku → klucz obserwacji
źródła → lista konsumentów. Deduplikować transport, nie usuwać potrzeb pokrycia.

Plan ma zawierać provider, rodzinę marketingową, origin/destination,
pełny dzień lub okno/miesiąc, typ regular/WDC/resident, adult=1, walutę,
rodzaj calendar/details i wersję adaptera. Wizz pobierający całe okno jednym
zapytaniem nadal potwierdza każdy dzień; Canaryfly pobiera całe miesiące
pokrywające okno, a szczegóły dopiero po kompletnych kalendarzach.

Przed pulami:

1. Jeden run UUID, D/okno, snapshot wszystkich konfiguracji i schedule.
2. Jeden NBP A/B dla D, opublikowane kursy nie późniejsze niż D; sobota nie
   wymaga fikcyjnego sobotniego notowania. Zweryfikować wszystkie potrzebne waluty.
3. Zwalidować kierunkowe fee i okres ważności całego okna.
4. Rozwiązać oficjalną wersję Wizz API raz, bez wpisywania jej na stałe.
5. Zamrozić konfigurację/strefy; nie modyfikować ich w pracujących wątkach.
6. Zidentyfikować run/cache i uzyskać blokadę właściciela kolekcji. Odmówić
   drugiemu runnerowi/standalone, który próbowałby ominąć globalne limity.

Przejęcie gotowych cen z poprzedniego publicznego feedu lub dawnego cache
SZY/RDO nie jest optymalizacją. Nowy run oznacza nowe obserwacje źródeł.

## 9. Etap C — kolejki źródeł, Google 3 i rzeczywiste równoległe pobieranie

Docelowy przebieg techniczny (nadal te same pięć kroków):

```text
PRE-FLIGHT: rejestry / niezależny plan / NBP / fee / Wizz API / blokady
  │
  └─ pięć równoległych gałęzi pobierania:
       ├─ GOOGLE: FR/RK → IB/I2 → VY → UX; jedna rodzina, maks. 3 HTTP
       ├─ WIZZ: regular + WDC; osobna pula
       ├─ BINTER: search → final imports; osobna pula
       ├─ CANARYFLY: miesiące → details/imports; osobna pula
       └─ VOLOTEA: MinPrice route/day; osobna pula

BRAMKA: wszystkie wymagane obserwacje jednego bieżącego runu kompletne
  ↓
10 builderów/raportów KOLEJNO, CACHE-ONLY
  ↓
walidacja całych 20 plików → lokalna promocja
```

Direct pools zaczynają po preflight, nie czekają na skończenie FR. FR/RK
to rodzina Ryanaira, IB/I2 to obecna rodzina Iberia/Express; każda zachowuje
własne kody i rejsy. Porządek rodzin można ustalić deterministycznie jak wyżej,
ale **nie może być nakładania ich aktywnego ruchu Google**.
Wszystkie cztery direct pools są niezależnymi równoległymi gałęziami:
Canaryfly nie czeka na Wizz, a Volotea nie czeka na Canaryfly.

### 9.1. Globalne Google 3 — właściwe miejsce ograniczenia

- Ustawić wspólny sufit **3**. Stary komentarz „verified safe” nie może
  sugerować, że nowy limit jest już sprawdzony lub oficjalnie gwarantowany.
- Jedna centralna pula trzech workerów i właściciel aktywnej rodziny.
  Sufit egzekwować **przy każdej faktycznej próbie HTTP**, także retry,
  a nie tylko wokół zlecenia wysokiego poziomu.
- Nie zostawiać dodatkowego semafora FR=2, który faktycznie obetnie nowe 3;
  nie nakładać dwóch tych samych blokad tak, by wywołać deadlock.
- Zmiana rodziny dopiero po opróżnieniu aktywnych żądań, retry i oczekujących
  prób poprzedniej. Cache-only reads nie zajmują slotu HTTP.
- `GoogleFlightsClient._request` musi znać kontekst właściciela i transport
  wspólnego schedulera. Wszystkie call sites, również standalone/verifier,
  podlegają tej samej polityce. Klient/session osobno na worker, nie jedna
  niesprawdzona współdzielona sesja HTTP.
- Obecne zapytanie Google jest route/date, bez filtra linii; HTML może zawierać
  różne linie. „Jedna rodzina naraz” oznacza właściciela pracy i parsera,
  nie twierdzenie, że Google technicznie zwróci tylko tego przewoźnika.
- Poprawne own-flight PLN, wszystkie rozpoznane grupy ofert, FR i RK,
  pełne numery/godziny pozostają bez zmian. Żadnego daily minimum → szablon.
- Nie uruchamiać jednocześnie subprocessów Google z prywatnymi semaforami.
  Centralny broker jest jedynym piszącym/wykonującym; osobny standalone musi
  uzyskać tę samą globalną blokadę procesu albo odmówić rozpoczęcia.
- Przy pierwszym pełnym przebiegu od razu 3. Bez żywego stress testu lub
  powtórnej bazy na 2. Testy limitów na mockach są obowiązkowe i nie są takim testem.

### 9.2. Źródła bezpośrednie i ich limity

Na pierwszy właściwy przebieg zachować ostrożne, niezależne pule:

| Źródło | Praca równoległa względem Google | Początkowy limit aktywnego HTTP |
| --- | --- | ---: |
| Google | jedna rodzina na raz | 3 globalnie |
| Wizz Air | tak, oficjalny timetable regular/WDC | 2 globalnie dla Wizz |
| Binter | tak, search i końcowe imports | 2 globalnie dla Binter |
| Canaryfly | tak, kalendarze i końcowe szczegóły | 2 globalnie dla Canaryfly |
| Volotea | tak, MinPrice | 2 globalnie dla Volotea |

Dwójki direct to proponowana kontrola pierwszego przebiegu, nie deklaracja
oficjalnych limitów przewoźników. Nie zwiększać ich bez potrzeby tylko dlatego,
że Google podniesiono do 3. Wszystkie wywołania do danego backendu, w tym
imports/retry/rozwiązanie API, muszą uwzględniać wspólny budżet. Jeżeli dwa
adaptery korzystają z tego samego rzeczywistego backendu, nie traktować nazw
linii jako dowodu niezależności — współdzielić właściwy limit hosta/usługi.

Binter i Canaryfly: token wybranej taryfy tylko w pamięci podczas final imports.
Nie zapisywać go nawet w wewnętrznym cache/logach, nie publikować kwot netto.
Wizz: rozróżniać regular/WDC w kluczach i zachować retry, błąd WDC nie może
zostać zastąpiony regularną ceną. Volotea nadal wyłącznie oficjalne MinPrice.

### 9.3. Retry i przerwanie błędnego runu

- Zdefiniować jednego właściciela ponowień i jawny łączny budżet. Obecne
  zagnieżdżone pętle FR/klienta wymagają audytu, nie przypadkowego 4×4 prób.
  Nie zwiększać budżetu retry razem z workers. Zachować backoff i respektować
  Retry-After, jeśli źródło go zwraca.
- Telemetria próby musi liczyć rzeczywisty request i jego zakończenie w finally,
  również exception, timeout, 429/5xx lub odpowiedź nieparsowalną.
- Prawidłowe zero/InvalidMarket według istniejących walidatorów ≠ failed.
  Brak payloadu/ceny/pełnych danych i GraphQL errors HTTP 200 są błędami.
- Po wyczerpaniu prób zatrzymać przydzielanie nowej pracy, bez dodawania czwartego
  requestu, omijania CAPTCHA lub cichego powrotu do innych źródeł cen.
  Aktywne zadania bezpiecznie domknąć; zachować poprawne części bieżącego runu.
- Brak automatycznego ukrytego „jednak 2” i ogłoszenia sukcesu testu trzech.
  Jeśli 3 zawodzi, jawny raport i decyzja użytkownika; stara publiczna baza bez zmian.

## 10. Etap D — wspólny cache, coverage i dziesięć builderów bez sieci

### 10.1. Repozytorium obserwacji

Każde źródło zapisuje poprawne obserwacje do trwałego repozytorium tego runu.
Można zachować JSONL Ryanaira i dodać analogiczne magazyny innych providerów;
wymaga to **jednego piszącego** na magazyn, atomowych manifestów i deduplikacji
single-flight danego klucza. Nie dopisywać z wielu subprocessów do tego samego
JSONL. Nie wprowadzać zewnętrznej usługi/kolejki lub nowej płatnej zależności.

Manifest: schema/adapter/parser version, run, D/okno, fingerprint requestu,
hash rejestru/9 allowlist/shared+local schedule/fees, NBP, tryb Google=3,
źródła i limity. Nie zmieniać konfiguracji w połowie i nie kontynuować
nieidentyfikowalnego cache. Po zmianie danych merytorycznych nowy run.

- Brak klucza, niekompletna odpowiedź i poprawne puste `flights=[]` to różne
  stany. Sukces dopiero po zakończeniu wszystkich wymaganych walidacji.
- FR own regular quotes przechowywać bez stosowania reguł konkretnej przesiadki.
  Resident estimates dodawać zgodnie z allowlistą konsumenta, nie mutować cache.
- Wizz: jeden zweryfikowany odczyt regular i, gdy wymagany, WDC dla trasy/okna.
  Wspólny adapter transportu dla istniejących implementacji w 1A/2/4/1C;
  materializacja przy zamrożonych zgodnych schedule. Rozbieżności numerów/bloków
  między local/shared muszą blokować, nie wybierać pierwszego wariantu.
- Klucze Wizz uwzględniają priceType i pasażerów. Puste regular pozwala zachować
  obecne pomijanie niepotrzebnego WDC; nie dopisywać zmyślonego wyniku WDC.
- Binter final imports i Canaryfly final imports zachować oficjalnie, z pełnymi
  składnikami/walidacją i oznaczeniem pochodzenia, bez opaque tokenu.
- Canaryfly zapisać **osobno pełne kalendarze i obserwacje details**. Nie odtwarzać
  listy wymaganych dni kalendarza z końcowych znalezionych par lub samych legs.
- Cache reads zwracają odseparowane kopie/niemutowalne dane. Przecena nogi
  w jednym kroku nie może zmienić kwoty regularnej w innym.
- Nowe raporty źródeł nie są publicznymi feedami; publiczny format można zachować.

### 10.2. Zachowanie raportów pokrycia

Źródło i każdy krok mają własny plan/raport. Nie przypisywać `_active` do
kilku kroków naraz. W fazie source korzystać z osobnej, jawnie przekazywanej
ewidencji, a nie z globalnego trackera publicznego collectora.

Po kompletnym źródle jego konsumenci rejestrują dokładnie potrzebne klucze
na podstawie zweryfikowanej obserwacji tego samego runu. Jeden odczyt może
potwierdzić kilka potrzeb różnych kroków; **nie oznacza kilku żądań HTTP**.
Nie kopiować całego source report do każdego feedu ani certyfikatu starego feedu.

W Canaryfly pełny calendar plan jest niezależny, a details plan wynika wyłącznie
z jego poprawnie zebranych dostępnych dni. Brak jednego wymaganego details
blokuje 1F i całą promocję. Binter success musi obejmować końcowe imports.
Metody pokrycia muszą pozostać zgodne z `METHODS`, nie dodać „cache” jako
nowego rzekomego źródła ceny.

### 10.3. Budowanie dziesięciu feedów

Po bramce kompletności źródeł runner uruchamia obecne kroki/builders **kolejno**,
z tym samym run/oknem/NBP i wymuszonym **cache-only**. To pozwala zachować
obecny tracker `_active` i izolację modułów między subprocessami.

Wspólny adapter/repository podać jawnie lub przez zweryfikowany kontekst,
nie runtime monkeypatchować globalnych funkcji różnych kolektorów.
Brak cache w tej fazie ma być błędem, **nie awaryjnym zapytaniem sieciowym**.
Dotyczy to Google, NBP, Wizz API discovery i wszystkich direct clientów.
Nie może pojawić się „jeszcze kilka” requestów innej rodziny po fazie Google.

Zachować obecne `build_connections`, sortowanie deterministyczne, ID, ceny,
booking URLs i walidatory. Regresję wykazać na identycznych zamrożonych danych,
nie przez porównywanie dwóch żywych kolekcji z różnymi cenami.
Każdy feed i sidecar powstaje od nowa z aktualnych obserwacji, bez edycji ręcznej.

## 11. Projekcja zakresu piętnastu — nie certyfikat nowej kolekcji

**Pierwotna projekcja jest nieaktualna po ogólnej zgodzie krajowych przesiadek.**
Obliczenia w `tmp/szz-ieg-plan/coverage-projection.json` dotyczą dawnej polityki
(SZZ przez trzy zagraniczne huby, bez KRK i innych nowych krajowych kombinacji).
Zachowano je wyłącznie jako historyczny artefakt planowania, nie plan do wykonania.

Podczas wdrożenia najpierw ponowić audyt krajowych kombinacji całej siatki,
zaktualizować politykę/macierze/allowlisty i dopiero wtedy wyprowadzić aktualne
`expected_queries` oraz deduplikowany source plan. Sama zmiana SZZ/KRK
nie wystarcza: reguła obejmuje również dotychczasowe endpointy i przyszłe porty.
Nie używać dawnych liczb 41 602 / 20 460 / 21 142 jako warunku kompletności.

Krok 2: **15 × 2 Tenerife × 2 kierunki = 60 tras kierunkowych**, obie linie
dają **120 par trasa/przewoźnik**, razy 31 = **3720**. Nie pozostawić dawnych
52 tras / 104 par ani nie ograniczyć do tras aktywnych.

W nowym raporcie oddzielnie podać bazowy plan każdego feedu, deduplikowane
potrzeby poszczególnych rodzin oraz fizyczne próby HTTP i retry. Wizz pobiera
okna regular/WDC, Canaryfly pełne miesiące/search/imports — route/day coverage
nie jest liczbą fizycznych zapytań. Details Canaryfly nadal są dynamiczne;
nie kopiować dawnej liczby 124. Finalny plan i actual completed muszą być
identyczne, bez braków/nadmiarów i bez pominięcia nowych legalnych krajowych tras.

## 12. Etap E — testy offline przed jednym właściwym pobraniem

Nie wykonywać osobnego żywego eksperymentu Google. Testy jednostkowe i
integracyjne na mockach/frozen fixtures są nadal konieczne.

### 12.1. Scheduler, izolacja i cache

- Mock HTTP + bariery/zegar: aktywne Google nigdy >3, przy obciążeniu osiąga 3;
  ani retry, standalone, verifier, Vueling/UX/IB nie omijają sufitów.
- Dwie rodziny Google nigdy nie mają nakładających się aktywnych requestów;
  handover po drenażu retry. Wyjątek zwalnia slot, brak deadlocków.
- Jednocześnie Google i co najmniej jedna bezpośrednia pula faktycznie pracują;
  nie wystarczy sprawdzić obecność ThreadPoolExecutor w kodzie.
- Direct limity obejmują wszystkie operacje/retry danego backendu. Oddzielne
  sessions; lock procesu wyklucza drugiego runnera i klienta standalone.
- Ten sam klucz potrzebny w kilku krokach powoduje jeden odczyt źródła;
  regular/WDC nie mieszają się. Concurrent cache hit/miss, single writer,
  przerwany ostatni zapis i niekompletny manifest nie certyfikują sukcesu.
- Inne D/okno/config/run/parser/NBP/policy odrzucone; stare ceny nie przechodzą.
- Wstrzyknąć 429/503, timeout, consent/malformed Google, GraphQL errors HTTP200,
  unpriced flight, missing imports/WDC/details. Publiczne 20 plików bez zmian,
  jawny failed report, brak nowych zleceń po fatalnym błędzie.
- Coverage kilku konsumentów nie przenika między krokami; oryginalne źródła
  pozostają `google_flights_http`, `timetableV2`, itd., nie „cache”.
- Wszystkie transporty w fazie budowania mockować jako wyjątek: kompletne
  repozytorium daje 10 poprawnych feedów bez choćby jednego requestu;
  brak klucza blokuje, nie dociąga brakującego dnia po cichu.
- Finalne kwoty i resident pola jednego konsumenta nie mutują cache/innego kroku.
- Pomiary: aktywne liczniki i monotoniczne czasy poprawne także przy exception,
  brak sekretów w logach i eventach; zapis telemetrii nie zakłóca źródeł.

### 12.2. Endpointy, wszystkie kroki i zachowanie starej trzynastki

- Rejestr 15, poprawne strefy, wszystkie 9 scope i pełna macierz 60/120.
- SZZ/DUB,LPL,STN, role obu nóg i oba kierunki; własne kwoty każdej godziny,
  granice 120/1440, odrzucenie 119/1441, +1/DST i zakaz zmiany IATA.
- SZZ/KRK oraz inne rzeczywiste krajowe kandydatury są dozwolone bez dalszej
  zgody. Testy odkrywania i walidacji obejmują również dawne endpointy,
  przyszły nowy endpoint i port krajowy jako hub; self-routes nadal zabronione.
  Dawne testy zakazu wszystkiego poza GDN/5B muszą odzwierciedlać nową politykę,
  nie usuwać zabezpieczeń czasu, linii, stref i liczby przesiadek.
- IEG z pustymi źródłami przechodzi pełny plan 1A/1B/2, nie short-circuit.
  Aktywny nowy Wizz bez schedule musi zablokować, nie wymyślić numeru.
- Collector executors naprawdę przechodzą wszystkie zaplanowane daty obu
  nowych endpointów niezależnie od zer lub innych dat drugiej linii.
- Coverage brakujący SZZ, IEG, jeden dzień lub cała dawna trzynastka blokuje;
  raport dla 13/14 nie może poświadczyć 15. Canaryfly details osobno.
- Helper SZZ→IEG→SZZ i IEG→SZZ zachowuje uprawnienia obu; wybrany baseline
  schedule, idempotencja i stare overrides. Nie usuwa sezonowego NRN ani SZY/STN.
- Frozen THIRTEEN we wszystkich dziesięciu builderach: te same wejścia dają
  identyczne stare wyniki, ceny regular/rezydent/WDC, ID i linki obu kierunków,
  wariantów 5 i uprawnionego GDN. Nie wymagać identyczności żywych cen.
- Opłaty Aeny z właściwego kierunku i jednej waluty; Binter/Canaryfly pozostają
  final imports, nie estimator. Cena ponad 1000 nadal zapisana w feedzie.
- Nowe testy np. `tests/test_szz_ieg_expansion.py`, `test_source_pipeline.py`,
  `test_source_scheduler.py`; aktualizacja żywych tuple/counts w istniejących
  testach, bez przerabiania historycznych SIX–THIRTEEN na aktualny rejestr.

### 12.3. Strona i multiselect

- `app.js` etykiety **Szczecin–Goleniów (SZZ)** i **Zielona Góra–Babimost (IEG)**;
  `index.html` opis wszystkich 15 i nowa wersja JS. Nie zmieniać layoutu/kolorów
  i limitów tylko z okazji rozszerzenia.
- Po objęciu wszystkich 15 portów z obecnego wykazu zmienić/usunąć obecną
  notę „Kolejne lotniska w Polsce wkrótce”. Nie zastępować jej twierdzeniem,
  że obejmujemy wszystkich przewoźników lub każdą możliwą podróż z tych portów.
- Dostępność checkboxów wynika z unii realnych ofert obu kierunków. IEG=0
  nie musi tworzyć piętnastej opcji; nie oznacza to braku obsługi endpointu.
- Syntetyczne 15 portów, SZZ/IEG osobno, oba + dawny port jako OR, tylko jeden
  kierunek, oba zero; zaznaczenie zachowane po zmianie kierunku.
- Cztery tryby zniżek, osiem sortów, kwoty/minima dat i wykresu, kliknięcie
  daty/słupka do tej samej karty, +1, copy/share/booking links każdej nogi.
- Przy rzeczywistym nowym batchu nie wymuszać istnienia ofert IEG. Jeżeli SZZ
  znika pod 1000/6 h, jawnie opisać i sprawdzić większe limity, nie zmieniać defaultu.
- Desktop i około 320 px: długie nazwy, ostatni wiersz, scroll, Gotowe/Escape,
  brak uciętych checkboxów. Rzeczywiste copy→paste→otwarcie tej samej karty.
  Jeśli narzędzie nie wymusi dokładnie 320, podać faktyczną szerokość/ograniczenie.

Komendy testów, bez pobierania cen:

```bash
.venv/bin/python -m unittest discover -s tests
node --test tests/test_airport_ui.mjs
node --check app.js
git diff --check
```

Nie ogłaszać zaliczonego odbioru na podstawie samych mocków HTTP: potem
potrzebne są prawdziwy pełny batch, walidacja, HTTP i przeglądarka.

## 13. Etap F — jeden nowy pełny batch ze źródłami równolegle

Po konfiguracji 15 i przejściu testów:

1. Wybrać D z Canary i czas na ukończenie przed północą. `validate_batch`
   sprawdza datę generowania względem bieżącego dnia. Jeśli przejdzie północ,
   nie osłabiać walidatora; jawnie zdecydować o nowym runie.
2. Nowy `tmp/szz-ieg-expansion/batch-D-RUN/`, UUID, świeży source repository,
   jeden preflight i wyliczony kanoniczny plan 15. Bez kolekcji pośredniej 14.
3. Wystartować Google **od razu 3 / jedna rodzina** i równoległe direct pools.
   Nie uruchamiać obok starych kolektorów, verifiera lub nowego discovery.
4. Zbierać postęp i telemetry; każdy dzień każdej zapisanej trasy z całego okna.
   Sukces jednej linii nie zastępuje brakujących dni innej.
5. Bramka kompletności source repository i zgodności provenance/manifestu.
6. Dziesięć builderów kolejno, cache-only; własne coverage i nowe 20 plików.
7. Walidacja `validate_batch` + źródła/limity/telemetry. Dopiero wtedy lokalna
   promocja całego kompletu z backupem, bez Git.

Docelowo zachować publiczny CLI runnera. **Poniższe `--google-workers` jest
proponowanym nowym parametrem do implementacji, dziś go nie ma.**
Oddzielić go od istniejącego `--workers` dla direct; ustawienia większe niż
3 nie mogą podnosić sufitu, także w standalone. Docelowy domyślny limit
Google to 3; wpis „3” w poleceniu ma być potwierdzony rzeczywistymi licznikami.

```bash
# Dopiero po implementacji source pipeline i nowej opcji:
.venv/bin/python scripts/collect_five_steps.py --from-date YYYY-MM-DD --days 30 --stage-directory tmp/szz-ieg-expansion/batch-D-RUN --workers 2 --google-workers 3
# Dopiero po kompletnym odbiorze stagingu:
.venv/bin/python scripts/collect_five_steps.py --from-date YYYY-MM-DD --days 30 --stage-directory tmp/szz-ieg-expansion/batch-D-RUN --validate-only --promote
```

Runner ma nadal obsługiwać osobne `--validate-only`, `--promote` i świadome
resume. Nie uruchamiać powyższego polecenia na starym runnerze i nie uznawać
`--workers 3` za dowód globalnego Google 3 lub równoległych źródeł.

### 13.1. Błędy i wznowienie

- Stara publiczna baza i jej sidecary pozostają razem nietknięte do sukcesu.
  Błąd źródła zapisuje failed raport w stagingu, nie nowy certyfikat starego JSON.
- Wznowienie tylko z tym samym run/D/oknem/config/NBP/wersją i polityką.
  Użyć wyłącznie poprawnych obserwacji **tego runu**; brakujące/nieudane pobrać
  ponownie z tymi samymi globalnymi limitami i zasadą jednej rodziny.
- Obserwacje potwierdzone są niezmienne w ramach runu. Nie odświeżać ceny
  jednego współdzielonego klucza bez unieważnienia wszystkich zależnych feedów.
  Nowa pełna świeżość wszystkich cen oznacza nowy run, nie mieszanie zestawów.
- Przy zmianie semantyki `--refresh-steps` doprecyzować zależności: wybór kroku
  nie może ominąć wspólnej kolejki lub pozostawić starego zależnego feedu.
  Po resume zawsze walidować wszystkie dziesięć, nie tylko odtworzone.
- Nie wracać automatycznie do starego feedu jako wyniku nowej kolekcji,
  nie wypełniać dziury minimum dnia, template lub dawnymi cenami.

### 13.2. Zgodność z przyszłym GitHub Actions, bez wdrażania workflow teraz

Nowy runner nadal działa bez przeglądarki i interakcji: instalacja istniejącego
requirements, jeden kontrolowany proces, jawne parametry i exit code, logi oraz
artefakty source/coverage/performance. Wyłącznie lokalna blokada pliku nie
ograniczy równoległych jobów na różnych maszynach. Przyszły workflow musi
uruchamiać **jeden job zbierający**, bez macierzy jobów dla linii, i zapewnić
wzajemne wykluczenie nachodzących runów. Jeden batch/NBP/source repository
w jednym środowisku. Oddzielne joby źródeł Google bez zewnętrznego wspólnego
koordynatora nie spełnią limitu trzech; nie proponować ich jako optymalizacji.
Cache i artefakty wolno wznowić tylko z pasującym run/oknem/hash/wersją;
wykluczyć `tmp/`, cookies i tokens z commita/publicznego deployu.
Nie tworzyć teraz workflow, harmonogramu, automatyzacji ani nowej usługi.

## 14. Jak mierzymy przyspieszenie bez osobnego testu 2 vs 3

Zapisać `performance-report.json` i zdarzenia/request counters w stagingu.
Nie bazować na obserwacji „wydaje się szybciej” lub sumie logów kroków.

Minimalne pola:

- UTC start/end i **monotoniczne elapsed**: preflight, całe zbieranie,
  każdy provider/rodzina Google, budowanie każdego feedu, walidacja, promocja.
- Planned unique observations, zakończone/failed/empty, cache hits/misses,
  faktyczne HTTP attempts/success/errors, retries, 429/5xx/timeouts/parser errors.
- Aktywne i max in-flight globalnie Google oraz na provider, owner timeline
  rodzin i retry; dowód braku równoczesnych rodzin i osiągnięcia 3 przy obciążeniu.
- Czas nakładania Google z direct sources, czas oczekiwania na limity/backoff,
  średnia/mediana/p95 czasu próby, rozmiar cache i opóźnienia jego zapisu.
- Osobno source coverage i liczba znalezionych rejsów/propozycji. Zero ofert
  nie jest dowodem oszczędności pracy ani brak requestu nie jest sukcesem.
- Run/config/version/NBP i okno; czasy wszystkich prób, w tym nieudanych runów
  i resume, bez usuwania niewygodnej porażki z podsumowania wydajności.

Bezpieczne logi zawierają provider/trasę/datę/typ/status/czas/attempt, nie cookies,
tokens, klucze, opaque imports ani sesyjne URL/pełne poufne payloady.
Zapis dziennika/manifestu przez jednego właściciela, bez wyścigu wielu wątków.

Model oczekiwanego efektu:

```text
sekwencyjne źródła: suma czasów źródeł + budowanie/walidacja
równoległe źródła:  najdłuższa gałąź źródeł + budowanie/walidacja
Google:            rodziny nadal kolejno, ale do 3 requestów w ich wnętrzu
```

To orientacyjny model, nie gwarantowany benchmark. FR już wcześniej miał cache
w obrębie runu, więc nie przypisywać mu ponownie całej oszczędności. Zyskiem
jest 3 zamiast 2, nakładanie serwisów i usunięcie pozostałych duplikatów, np. Wizz.
Z telemetrii jednego runu można oszacować czas bez nakładania źródeł, ale trzeba
oznaczyć go jako estymację, nie wykonany drugi przebieg.

Porównanie z poprzednią bazą normalizować liczbą unikalnych potrzeb, datami,
rzeczywistymi HTTP i błędami. 13 → 15 zwiększa plan. Jeśli nie ma wiarygodnego
poprzedniego czasu startu/czasów źródeł, uczciwie podać ograniczenie zamiast
tworzyć procent oszczędności. Przyszłe kolekcje będą miały porównywalne pomiary.

Warunek sukcesu jakościowego: pełna spójna baza oraz limit ≤3 i jedna rodzina.
Skrócony czas nie usprawiedliwia brakujących dni, utraty WDC, końcowych fees,
nieprawidłowych linków lub cichego obcięcia propozycji ponad 1000 zł.

## 15. Odbiór lokalny, raport i rollback

Przed promocją porównać stare publiczne 20 plików bajtowo z baseline.
Po promocji: publiczne=staging, backup=baseline; ponowna walidacja obecnej
konfiguracji, testy JS na publicznych plikach, HTTP index/app + wszystkich 20,
rzeczywista przeglądarka i schowek. Nie zmieniać daty feedu tylko po to,
aby przeszedł walidację; nowy certyfikat wymaga nowych właściwych danych.

Promocja ma rollback obsłużonych błędów, ale 20 podmian nie jest jedną
transakcją odporną na utratę zasilania. Powrót do trzynastu wymaga spójnego
przywrócenia rejestru/allowlist/kodu i wszystkich 20 plików, nie samych cen.
Osobno można wycofać source pipeline przy zachowanej konfiguracji 15 tylko
po świadomej decyzji i testach; nie robić tego jako ukrytego fallbacku runu 3.
Zachować nowe source artefakty i zastane zmiany użytkownika, bez globalnego resetu.

W `WDROZENIE_SZCZECINA_I_ZIELONEJ_GORY_SZZ_IEG.md` podać:

- HEAD/baseline, faktyczne zmiany, audyty nowych portów i krajowych tras całej
  siatki, ogólną zgodę użytkownika i jej spójne wdrożenie;
- D/okno, UUID, configuration/source-policy hash, NBP, źródła/codes i wersje;
- Tabelę wszystkich 10 feedów i completed/missing/unexpected, zgodność 20 plików;
- Pełne liczby SZZ i IEG w obu kierunkach oraz przy default 1000/6 h, powody zer;
- Rzeczywiste source requests, cache reuse i faktyczne Google max=3/owner timeline;
- Performance report, błędy, retry, resume i ograniczenia porównania 13/15;
- Wyniki testów bez ukrytych skipów, przeglądarki/HTTP/copy/share/+1;
- Backup/rollback i lokalny podgląd; brak publikacji, jeśli nie ma osobnej zgody.

## 16. Checklista przed uznaniem wdrożenia za gotowe

- [ ] Jeden baseline trzynastu i 20 plików, osobne prawdziwe SZZ/IEG evidence.
- [ ] 15 portów/stref, 9 scope, pełna macierz 60/120 i wszystkie dni obu linii.
- [ ] Pełne nowe wspólne IATA, SZZ/DUB,KRK,LPL,STN i audyt krajowych kombinacji całej siatki.
- [ ] IEG zero nie udaje błędu ani nie pomija kolekcji; LOT nie został dopisany.
- [ ] Wszystkie 1A–1F i 3/4/5 mają decyzje, nowe Wizz metadata kompletne lub pending.
- [ ] Ogólna krajowa zgoda w rejestrze/loaderze/discovery/walidacji/testach, bez pytań o kolejne porty; NRN i dawne schedules zachowane.
- [ ] Instrukcje/testy/ustawienia Google zsynchronizowane z decyzją 3, nie tylko liczba w jednym pliku.
- [ ] Jeden Google owner, max 3 również przy retry, verifierze i drugim procesie.
- [ ] Direct rzeczywiście nakładają się z Google; ich własne limity nie są mnożone przez kroki.
- [ ] NBP/API/config przygotowane przed pulami; żadnych wyścigów `_active`/modułowych rejestrów.
- [ ] Single-flight/cache identity/single writer; brak tokenów i starych cen; WDC osobno.
- [ ] Binter/Canaryfly final imports, Volotea oficjalnie, Google own fares, opłaty/rezydent bez regresji.
- [ ] Źródła kompletne przed matching; 10 builderów cache-only z siecią blokowaną w testach.
- [ ] Coverage per-source/per-step prawidłowe, Canaryfly details dynamiczne, brak dnia blokuje promocję.
- [ ] Frozen THIRTEEN we wszystkich 10 builderach, pełne testy limitów i obu nowych endpointów.
- [ ] UI syntetyczne 15 i rzeczywiste zera, OR, kierunki, ceny, kalendarz/wykres/karta/share/+1.
- [ ] Jeden właściwy pełny nowy batch 15, bez osobnej żywej próbki i bez pośredniego batcha 14.
- [ ] Telemetria faktycznej równoległości/czasu/błędów i uczciwe ograniczenia pomiaru przyspieszenia.
- [ ] Spójna lokalna promocja 20, backup=baseline, publiczne=staging, HTTP i przeglądarka sprawdzone.
- [ ] Raport faktów/powodów zer/rollback, żadnego commita/push bez nowego polecenia.

## 17. Instrukcja dla Codexa po zatwierdzeniu realizacji

> Wdróż razem SZZ i IEG zgodnie z tym planem i aktualnymi regułami projektu.
> Najpierw audyt pełnych siatek i konfiguracja 15, następnie source pipeline:
> Google jedna rodzina na raz, maksymalnie 3 rzeczywiste żądania łącznie
> z retry, równolegle ograniczone niezależne serwisy Wizz/Binter/Canaryfly/Volotea.
> Nie uruchamiaj kilku obecnych kolektorów Google z prywatnymi semaforami.
> Zapewnij wspólny bieżący source cache, brak wyścigów coverage, cache-only
> budowanie wszystkich dziesięciu feedów i fail-closed całego batcha.
> Zachowaj pięć kroków, pełne niezależne kalendarze, ceny końcowe, zniżki,
> schedules, booking URLs i defaulty UI. Wszystkie krajowe przesiadki są
> trwale dozwolone; wdroż ogólną politykę i sprawdź krajowe kombinacje dla
> całej siatki, nie tylko SZZ/KRK. Nie pytaj ponownie o zgodę na polski hub.
> Nie dodawaj LOT-u dla IEG i nie
> usuwaj NRN. Przejdź testy offline, potem zbierz jedną pełną bazę 15
> od razu przy Google=3, bez osobnego żywego testu 2 vs 3. Zapisz czasy,
> max in-flight, owner timeline, błędy i retries, uczciwie oceń przyspieszenie.
> Po pełnym odbiorze podmień lokalnie całe 20 plików z backupem, sprawdź
> HTTP/UI/kalendarz/wykres/share i opisz fakty w raporcie. Nic na GitHub
> bez osobnego polecenia; nie twórz workflow Actions ani nowych usług.

## 18. Odbiór samego planu 24.10.2026

Ponownie przeszły **246 testów Python i 42 JS**, zero pominiętych. To testy
obecnego kodu przy limicie 2 i mockowanych źródłach, nie dowód działania
przyszłego source pipeline lub powodzenia Google=3.
Aktualny batch trzynastu przeszedł odczytową walidację; projekcja piętnastu
została policzona offline. `git diff` potwierdza brak zmian `data/`,
`scripts/`, testów, `app.js`, `index.html` i CSS. Powstał ten
dokument i odnośnik w README, a ignorowane `tmp/` zawiera dowody planowania.
Nie pobrano nowych cen i nie wykonano operacji publikujących Git.
Po nowej decyzji użytkownika zaktualizowano instrukcje `AGENTS.md` i
`FIVE_STEP_FLIGHT_SEARCH.md` oraz niniejszy plan/README; zapisano trwałą notatkę
pamięci. Kod/rejestr/allowlisty nadal wymagają opisanej migracji. Nie pobierano
nowych grafów ani cen wyłącznie w celu zapisania tej decyzji.
