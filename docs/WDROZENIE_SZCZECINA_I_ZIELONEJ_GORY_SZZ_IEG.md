# Lokalne wdrożenie SZZ/IEG i wspólnego pobierania źródeł — 24.10.2026

Status: kod, konfiguracja i kompletna nowa baza wdrożone **lokalnie**.
Wznowiono ten sam run, bez odrzucania poprawnych obserwacji. Po walidacji
podmieniono dziesięć feedów i dziesięć raportów; poprzedni komplet jest w backupie.
Otwarty pozostaje wyłącznie odbiór wizualny/realnego schowka w przeglądarce.
Pierwszy odbiór odbył się bez commita/push/PR, zmian workflow ani automatyzacji.
Następnie 24.10.2026 użytkownik autoryzował wysłanie całego pakietu na GitHub.

## Zakres i źródła dowodów

Baseline HEAD `8a50db3704efd708f5b0c3723be93b7e564d7b10`, historyczna gałąź
`codex/add-lodz-lcj`. Zachowano wcześniejsze lokalne zmiany dokumentacyjne.
Kopia 116 plików i ich SHA256: `tmp/szz-ieg-expansion/baseline/` oraz
`baseline-manifest.json`. Obejmuje dotychczasowe dziesięć feedów i sidecary.

Niezależne aktualne odczyty oficjalnych kompletnych sieci FR/Wizz:
`tmp/szz-ieg-expansion/audit-SZZ/` i `audit-IEG/`. Audyt był low-cost-only:
nie należy opisywać go jako ponownego odkrycia całej siatki Bintera.

- SZZ: Ryanair DUB/KRK/LPL/STN, Wizz BGO/OSL. W kroku 3 zapisano
  DUB/KRK/LPL/STN. Aktualne przecięcia nie dały SZZ kroku 4 ani 5.
- IEG: brak bezpośrednich krawędzi FR/Wizz w kompletnych odczytach.
  Nie dodano LOT-u ani oferty z przesiadką wymagającej drugiej przesiadki.
- Żaden nowy endpoint nie miał kwalifikującej się hiszpańskiej nogi FR/Wizz
  do rozszerzenia list rezydenckich 1A–1F. To wykluczenie wynika z osobnej
  polskiej nogi, nie z ograniczania dat rozkładem drugiego przewoźnika.
- Niezależny audyt techniczny Wizz dla SZZ i IEG nie znalazł aktywnych nowych
  bezpośrednich tras na Teneryfę w oknie. Nie dopisano numerów ani czasów z domysłu.

Wspólny rejestr ma 15 endpointów, oba nowe z `Europe/Warsaw`. Wszystkie dziewięć
allowlist ma zgodny scope. Krok 2 pyta pełne 120 par trasa/przewoźnik, również
nieaktywne IEG, TFN i oba kierunki. Dostępność checkboxów nadal wynika z unii
rzeczywistych ofert obu kierunków, nie z samego istnienia kodu w rejestrze.

## Krajowe przesiadki

`domestic_transfers_allowed=true` zastępuje wyjątki GDN/5B/KRK,LUZ.
Walidatory i detektor dopuszczają dowolny inny polski endpoint jako hub,
również przyszły, bez nowej zgody. Self-routes i TFN/TFS jako hub nadal są
zabronione. Nie zmieniono linii, liczby przesiadek ani granic 120–1440 minut.

Aktualny audyt całej siatki, nie tylko nowych endpointów, dodał:

- Step 3: KRK na nodze TFS, z GDN oraz SZZ. Bez zniżki rezydenta.
- Step 5B: WRO przez GDN obok istniejących KRK/LUZ. Korzysta ze zweryfikowanej
  wspólnej trasy Wizz GDN↔TFS. Brak nowych legalnych kombinacji krajowych w 4/5A.

W nowej bazie GDN↔KRK↔TFS daje **31** propozycji (16 do Teneryfy, 15 do
Polski), Ryanair na obu odcinkach. WRO↔GDN↔TFS daje **6** (2 do Teneryfy,
4 do Polski), Ryanair WRO↔GDN i Wizz Air GDN↔TFS. SZZ przez KRK daje zero.
Najkrótsze przesiadki tych dostępnych nowych kombinacji to odpowiednio 8 h
oraz 14 h 10 min, więc domyślne 6 h je ukrywa; można podnieść limit do 24 h.
To nowe kombinacje w naszej konfiguracji, nie twierdzenie o uruchomieniu
nowych tras przez linie. Wcześniejsze ograniczenia pomijały KRK jako krajowy
hub i WRO jako endpoint wariantu przez GDN; obecna ogólna zgoda je zastąpiła.

Nie włączono niezwiązanych z tym zakresem zagranicznych kandydatów BBU/OTP.
Nie usuwano istniejących sezonowych tras/NRN.

## Nowy mechanizm

Po preflight powstaje niezależny, deduplikowany plan źródeł. Pięć kolejek
pracuje równolegle: Google, Wizz, Binter, Canaryfly, Volotea. Google realizuje
FR/RK → IB/I2 → VY → UX, bez nakładania aktywnych rodzin, do trzech rzeczywistych
prób HTTP naraz. Każdy direct provider ma sufit dwóch, również dla imports
i retry. Blokady OS chronią przed dołożeniem slotów przez drugi proces.

Google ma jeden zewnętrzny budżet czterech prób, bez dawnego przypadkowego
4×4. Backoff uwzględnia Retry-After; nadmierne oczekiwanie blokuje przebieg.
Jeden limit Google pochodzi z `collector_settings.py`, nie z parametru workers
poszczególnej linii. Nie ma cichego zejścia z trzech na dwa.

Repozytorium runu zapisuje wyłącznie zweryfikowane, znormalizowane dane,
bez tokenów, cookies i danych sesji. Osobno pełne kalendarze Canaryfly i jego
details. Zachowuje oficjalne końcowe ceny Binter/Canaryfly i regular/WDC Wizza.
Wspólny NBP, konfiguracja, wersja adapterów, daty i run są zamrożone. Pusty
sprawdzony dzień różni się od braku obserwacji; zmiana lub ucięty zapis blokuje.

Po kompletnym źródle dziesięć builderów działa kolejno i wyłącznie z cache,
z osobnym coverage każdego kroku. Nie wykonują sieci, nawet awaryjnie.
Nie zmieniono pięciu kroków, formatów kart, filtrowania 1000 zł/6 h ani cen
pochodnych. Wszystkie ceny są zbierane przed filtrem strony.

## Plan pokrycia poprawionego przebiegu

| Feed | Bazowe route/day |
| --- | ---: |
| 1A | 11904 |
| 1B | 1984 |
| 1C | 3534 |
| 1D | 744 |
| 1E | 248 |
| 1F | 434 |
| 2 | 3720 |
| 3 | 12462 |
| 4 | 1364 |
| 5 | 5456 |

Suma 41850, przed dynamicznymi details Canaryfly. Deduplikowane źródła:
FR 20584, Wizz 11532, Binter 744, IB 124, VY 434, UX 124, Volotea 62,
Canaryfly calendar 124. Nie są to liczby fizycznych zapytań HTTP.

## Przebieg i odbiór

Pierwszą częściową próbę `batch-20261024` przerwano przed jakąkolwiek publikacją:
kontrola wykryła omyłkowe przypisanie SZZ do LBA zamiast LPL w konfiguracyjnym
patchu. Wpis poprawiono, dodano test porównujący pary ze snapshotem sieci.
Ten staging jest wyłącznie diagnostyczny, nie przeniesiono z niego cen.

Poprawiony pełny przebieg: `tmp/szz-ieg-expansion/batch-20261024-v2/`,
log `collection-v2.log`. Okno 24.10–23.11.2026, wszystkie daty w obu kierunkach.
Run: `3a5a1329-a7e2-4b95-a2e5-6b10546a544d`. Pierwsze podejście tego runu zakończyło się
błędem po **1344,89 s (22 min 24,89 s)**. Przy POZ→BRS na 17.11.2026 cztery
próby nie uzyskały użytecznych danych; ostatnia przyczyna:
`Unknown Google Flights Ryanair payload`. Wszystkie 11879 prób HTTP Google
miały status 200; błąd był na poziomie zawartości, nie kodu HTTP.

Dwa ograniczone odczyty diagnostyczne wyłącznie tej relacji/daty wykazały
niekompletną strukturę oraz widoczny tekst „Wczytuję wyniki” bez listy ofert.
Nie zapisano surowego HTML, danych sesji ani tokenów. Nie potraktowano tej
odpowiedzi jako pustej dostępności. Nie ma dowodu, że przyczyną jest sama
równoległość trzech. Nie zmieniono parsera, by tolerował brak danych.

Brak promocji po tej awarii był zamierzonym działaniem fail-closed. Stan
historyczny na koniec pierwszego podejścia (nie aktualny stan po wznowieniu):

| Źródło | Poprawne logiczne obserwacje | Braki |
| --- | ---: | ---: |
| Ryanair | 11749 | 8835 |
| Wizz Air | 11532 | 0 |
| Binter | 698 | 46 — kolejka anulowana po błędzie Google |
| Canaryfly | 248 (calendar + details) | 0 |
| Volotea | 62 | 0 |
| Iberia | 0 | 124 — rodzina jeszcze nie rozpoczęta |
| Vueling | 0 | 434 — rodzina jeszcze nie rozpoczęta |
| Air Europa | 0 | 124 — rodzina jeszcze nie rozpoczęta |

Razem 24289/33852, brak 9563, nadmiar 0. W cache Ryanaira są ponadto
poprawne pojedyncze dni nieukończonych tras; nie poświadczają całego okna.
Nie powstał wtedy certyfikat `sources/complete.json` ani żaden nowy publiczny feed.
SHA256 wszystkich **20** dotychczasowych plików publicznych zgadzały się wtedy
z baseline. Do zakończenia wznowienia strona zachowała poprzednią bazę trzynastu
portów, bez mieszania starych i nowych cen.

Analiza osi czasu potwierdziła rzeczywiste maksimum Google=3, pozostałe
źródła=2 oraz jednoczesną pracę każdej direct kolejki z Google. Wizz zakończył
się po 282,24 s, Canaryfly po 105,47 s, Volotea po 6,30 s. Wizz miał 30
przejściowych odpowiedzi 503 oraz 178 poprawnych InvalidMarket HTTP400;
jego pełna kolejka zakończyła się poprawnie. Pozostałe źródła nie miały błędów
HTTP. Nie porównujemy procentowo do osobnej kolekcji Google=2, bo użytkownik
zlecił od razu właściwy przebieg na 3. Dowody: `final-run-audit.json` oraz
archiwum raportów `failed-attempt-1/`. Bieżące raporty w stagingu dotyczą już
zakończonego wznowienia.

Nie uruchomiono samoczynnie kolejnego przebiegu po wyczerpaniu budżetu prób,
nie obniżono limitu do dwóch ani nie zmieniono źródła. Wznowienie nastąpiło
dopiero po decyzji użytkownika. Przy tym samym runie i identycznych
konfiguracji/adapterach zachowano jego poprawne obserwacje. Inny
dzień/okno/konfiguracja/adapter oznacza nowy run.

### Wznowienie autoryzowane przez użytkownika

24.10.2026 użytkownik polecił: „Tak. Nie zaczynaj od początku”. Wznowiono
dokładnie run `3a5a1329-a7e2-4b95-a2e5-6b10546a544d`, w tym samym stagingu,
z identycznymi hashami konfiguracji/adapterów, datami i NBP. Google nadal 3.
Pierwsza awaria i jej telemetria są zachowane w `failed-attempt-1/`.
Log wznowienia: `tmp/szz-ieg-expansion/collection-resume-1.log`.

Wizz/Canaryfly/Volotea skorzystały z już kompletnych zapisów, Binter pobrał
wyłącznie 46 brakujących dni tras, Ryanair użył wcześniejszych poprawnych
tras/dni i dokończył brakującą część. Problem POZ→BRS na 17.11 zwrócił teraz
poprawną odpowiedź znanego formatu z zerem ofert FR/RK. Nie zmieniono parsera
ani nie zamieniono błędu w pusty dzień. Cały plan, w tym wszystkie pozostałe
daty tej trasy i rodziny Google, zakończył się kompletnie.

Wznowienie źródeł trwało **1044,66 s (17 min 24,66 s)**. Razem oba podejścia
zbierania źródeł to **2389,56 s (39 min 49,56 s)** aktywnego czasu, bez przerwy
na decyzję użytkownika, budowania i testów. Nie jest to pomiar przyspieszenia
względem limitu 2. Google FR/RK, IB/I2, VY i UX działały kolejno; rzeczywiste
maksimum pozostało 3. Wznowienie nie miało błędów HTTP. Binter ponownie
pracował równolegle z Google, do dwóch prób HTTP naraz. Pozostałe bezpośrednie
źródła nie wymagały powtórnego pobierania kalendarzy.

Dowód: `tmp/szz-ieg-expansion/resume-1-final-audit.json`. Manifest i certyfikat
zachowują ten sam run, NBP EUR/PLN **4.3917**, konfigurację SHA256
`d10e53b6bc33029cf37119e471b37c8c22314e4c6f84fef9e1b6fc7371773ed9`
i adaptery SHA256
`8b3090cba6d57af6d2eac71078394c7013023489f70e84218515475409fd5c28`.

### Kompletna nowa baza i lokalna promocja

Źródła: **33852/33852** certyfikowane obserwacje, braki 0, nadmiar 0,
łącznie z 124 dynamicznymi szczegółami Canaryfly. Dziesięć feedów ma razem
**41974/41974** obserwacje coverage i ten sam run. Buildery działały kolejno
wyłącznie z cache; żadnych cen nie przeniesiono ze starego publicznego runu.

| Feed | Nowe propozycje |
| --- | ---: |
| 1A | 2893 |
| 1B | 2242 |
| 1C | 2885 |
| 1D | 883 |
| 1E | 8 |
| 1F | 225 |
| 2 | 213 |
| 3 | 5784 |
| 4 | 216 |
| 5 | 738 |
| **Razem** | **16087** |

SZZ: **145** ofert (71 Polska→Teneryfa, 74 odwrotnie), przez DUB 33, LPL 21,
STN 91. Przy domyślnych 1000 zł/6 h: 13 do Teneryfy i 19 do Polski.
Zapisane KRK nie daje obecnie dopasowania w granicach 120–1440 minut;
nie usunięto trasy ani nie wymyślono dodatkowej oferty. IEG: **0** ofert po
kompletnym sprawdzeniu; rejestr i macierz są gotowe, checkbox bez rzeczywistej
oferty nie jest sztucznie wyświetlany.

Przed promocją ponownie sprawdzono SHA256 starego kompletu 20 plików.
Następnie `--validate-only --promote` podmieniło je wyłącznie lokalnie,
zachowując `batch-20261024-v2/previous-public-feeds/`. Backup odpowiada baseline
bajtowo. Bieżące 20 plików odpowiada stagingowi bajtowo i ponownie przeszło
`validate_batch`. Wszystkie 23 sprawdzane zasoby HTTP (HTML, JS, rejestr,
dziesięć feedów i dziesięć raportów) zwracają 200 i dokładnie lokalne pliki.
Dowody: `stage-acceptance.json`, `public-acceptance.json`, `local-promotion.log`
w `tmp/szz-ieg-expansion/`.

Lokalna strona: `http://127.0.0.1:8000/?build=szz-ieg-local-20261024`.

## Testy i ograniczenia odbioru

Testy Python: **259 OK**. Testy UI na świeżym stagingu oraz po lokalnej
promocji: **45 OK, bez pominiętych**. Obejmują rzeczywisty pełny zakres
15 endpointów. Syntetyczne testy obejmują
15 checkboxów, OR, kierunki, chipy, kalendarz/wykres, kwoty, share i zniżki.
Zamrożona trzynastka zachowuje wyniki 1A–1F, 2, 3, 4 i obu wariantów 5.

Dodatkowy integracyjny test offline wszystkich dziesięciu builderów: OK.
Zamrożone nogi posłużyły wyłącznie za fixture w automatycznie usuwanym katalogu
tymczasowym. Wszystkie wywołania transportu curl_cffi (moduł i Session) były
zastąpione błędem. Każdy builder zakończył się poprawnie, a pełna walidacja
dziesięciu feedów/sidecarów przeszła. Nie jest to kolekcja aktualnych cen,
nie dokonano promocji fixture i nie przeniesiono z niego żadnych danych.
Dowód: `tmp/szz-ieg-expansion/offline-build-check.log`.

Automatyczny odbiór przeglądarkowy jest obecnie niedostępny: narzędzie zwraca
`Local browser use is disabled in Work settings`. Bez zmiany tego ustawienia
nie należy twierdzić, że obejrzano desktop/320 px lub rzeczywiste kopiowanie
linku. Testy logiki UI nie zastępują wizualnego odbioru.

Kod, kompletna kolekcja, testy, backup, lokalna promocja i HTTP są zakończone.
Do ręcznego sprawdzenia pozostaje prawdziwy widok desktop/320 px i realny
schowek po włączeniu dostępu do przeglądarki. Nie ma podstaw do uznawania tego
wizualnego odbioru za wykonany. HEAD pozostał
`8a50db3704efd708f5b0c3723be93b7e564d7b10` podczas pierwszego lokalnego odbioru.

## Autoryzacja publikacji — 24.10.2026

Po lokalnym odbiorze użytkownik polecił: „Wyślij na github”. Publikacja obejmuje
rejestry 15 portów, wspólną politykę krajowych przesiadek, kolejki źródeł i cache,
dziesięć nowych feedów z raportami, testy oraz dokumentację. Bez workflow Actions,
bez artefaktów `tmp/`, tokenów i danych sesji. Przed wysłaniem ponownie
zweryfikowano kompletność publicznego batcha i bajtową zgodność ze stagingiem.
