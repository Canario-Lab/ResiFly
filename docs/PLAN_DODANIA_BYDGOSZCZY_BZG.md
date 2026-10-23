# Plan dodania Bydgoszczy (BZG) jako dziesiątego polskiego lotniska ResiFly

Plan wykonawczy przygotowany **23.10.2026** na podstawie repozytorium
`7d4f9bf7b834bd7007cf4b8a4b414123dfe65233`, po wdrożeniu i wysłaniu RZE
oraz filtra wielokrotnego wyboru lotnisk. Checkout: `codex/add-lodz-lcj`.
Nazwa tej gałęzi nie oznacza, że jej zawartość kończy się na Łodzi.

**Status: wdrożone lokalnie 23.10.2026 na osobne polecenie użytkownika.**
Pierwszy odbiór był bez commita i push; następnie użytkownik osobno zlecił
publikację całego pakietu BZG na GitHub. Nowa kompletna baza zawiera 187 propozycji BZG;
odbiór wizualny/schowka pozostaje otwarty. Wyniki i dowody realizacji:
[`WDROZENIE_BYDGOSZCZY_BZG.md`](WDROZENIE_BYDGOSZCZY_BZG.md).
Samo przygotowanie planu nie obejmowało wdrażania, zmiany feedów ani operacji
Git. Bydgoszcz używa kodu BZG, potwierdzonego w
[oficjalnym rozkładzie portu](https://plb.pl/rozklad-lotow/).
To sprawdzenie identyfikacji lotniska, nie pełny audyt siatek przewoźników.
Żadna przesiadka BZG nie jest przez ten plan uznana za potwierdzoną.

Wiążące instrukcje: `AGENTS.md`, `docs/FIVE_STEP_FLIGHT_SEARCH.md`,
`docs/COLLECTION_RELIABILITY.md`. Realizacja planu wymaga osobnego polecenia.
Wcześniejsza zgoda na publikację RZE nie obejmuje wdrożenia ani publikacji BZG.

## 1. Cel i niezmienne zasady

Docelowy rejestr, w kolejności obecnej dziewiątki i nowego endpointu:

**WAW, WMI, KTW, KRK, GDN, WRO, POZ, LCJ, RZE, BZG**.

Nowy rekord w `data/search-airports.json`:

```json
{ "iata": "BZG", "name_pl": "Bydgoszcz", "timezone": "Europe/Warsaw" }
```

Obsłużyć BZG → TFN/TFS oraz TFN/TFS → BZG, osobno w obu kierunkach.
Sprawdzić wszystkie dopuszczone rodziny linii i **również zupełnie nowe
wspólne lotniska przesiadkowe, nieobecne w dotychczasowych listach**.

Zachować:

- Dokładnie pięć głównych kroków, sześć wariantów 1A–1F i dziesięć feedów.
  Dziewięć plików allowlist pozostaje dziewięcioma — nie mylić ich liczby
  z dziesięcioma polskimi endpointami lub dziesięcioma feedami.
- Pełne, niezależne okno każdego zapisanego odcinka każdej linii w obu
  kierunkach. Dopasowywać dopiero po pobraniu kompletnych kalendarzy.
  Nie wyznaczać dni jednej linii z lotów drugiej.
- `--days 30`: dzień startu plus 30 kolejnych, **31 dat włącznie**.
  Odloty obu odcinków muszą mieścić się w tym samym oknie. Przylot może
  nastąpić następnego dnia; nie obcinać go przez porównanie samej godziny.
- Maksymalnie jedna przesiadka na tym samym IATA, 120–1440 minut włącznie,
  z poprawną chronologią UTC, strefami IANA i zmianą czasu letniego.
- GDN jako polska przesiadka wyłącznie w istniejącym 5B do KRK.
  Nie rozszerzać wyjątku na BZG; BZG nie staje się nowym hubem.
- Te same linie co obecnie. Nie dodawać LOT-u, czarterów, dojazdów między
  lotniskami ani drugiej przesiadki tylko dlatego, że port ma takie oferty.
- Pełne wyniki bez odrzucania z powodu ceny. Domyślnie na stronie nadal
  Polska → Teneryfa, do 1000 zł, do 6 godzin przesiadki, najbliższy termin.
- Oddzielne ceny regularne, rezydenta i WIZZ Discount Club.
  Zachować znaczenie ID i linków udostępniania.
- Google Flights HTTP najwyżej dwa zapytania jednocześnie, także retry;
  jeden dzienny zestaw NBP dla całego batcha.
- Binter/Canaryfly: oficjalne końcowe totals; pozostałe uprawnione odcinki:
  jawne estymaty uwzględniające pełne niedyskontowane opłaty.
- Tylko deterministyczne linki zakupu per odcinek, bez tokenów i sesji.
- Uprawnienia i rozkłady dotychczasowych dziewięciu endpointów pozostają
  niezmienione, chyba że osobno ujawniono i zatwierdzono potrzebną zmianę.
  Na zamrożonych wejściach stare wyniki, ID, ceny i linki mają być identyczne.

## 2. Zweryfikowany baseline przed BZG

Rejestr i `scope.polish_airports` wszystkich dziewięciu allowlist zawierają
obecnie dziewięć endpointów. BZG nie występuje w konfiguracji, technicznych
rozkładach Wizz ani etykietach strony. Repozytorium przed zapisaniem planu
było czyste, HEAD jak wyżej.

Przy opracowaniu planu ponownie wywołano `validate_batch` bez pobierania cen.
Obecna baza: **2026-10-23–2026-11-22**, run
**`e1d13844-5567-46d6-980d-f819f4fa1752`**. Wszystkie dziesięć sidecarów
odpowiada raportom w feedach; **15 268 propozycji, 33 976 kompletnych pozycji
pokrycia**, zero braków/nadmiarów. To baseline, nie prognoza wyniku BZG ani
gwarancja aktualności tych cen w późniejszym dniu wdrożenia.

| Feed | Obecne wyniki | Bazowy plan tras/dni | Kompletne pokrycie |
| --- | ---: | ---: | ---: |
| 1A (`step1`) | 2797 | 7440 | 7440 |
| 1B | 2171 | 1240 | 1240 |
| 1C | 2853 | 3472 | 3472 |
| 1D | 853 | 744 | 744 |
| 1E | 8 | 248 | 248 |
| 1F | 221 | 434 | 558 |
| 2 | 205 | 2232 | 2232 |
| 3 | 5241 | 11408 | 11408 |
| 4 | 210 | 1364 | 1364 |
| 5 | 709 | 5270 | 5270 |

1F dodatkowo wymaga 124 sprawdzeń szczegółów dostępnych dni po kalendarzach.
Pokrycie nie jest liczbą HTTP: działa cache Ryanaira, okresowe zapytania
Wizza i miesięczne kalendarze Canaryfly.

Wyniki endpointów: WAW 1989, WMI 1904, KTW 781, KRK 5083, GDN 1963,
WRO 2244, POZ 815, LCJ 210, RZE 279. Siedem wyników używa GDN jako transferu;
nie liczyć tej roli jako dodatkowego endpointu podróży.

Ponownie przeszło **208 testów Python i 30 JavaScript**, bez pominiętych.
Mockowane komunikaty pobrań w testach nie oznaczają nowej kolekcji.

### Obecne huby — punkt porównania, nie ograniczenie audytu BZG

| Wariant | Zapisane huby |
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

Nie kopiować uprawnień RZE, LCJ ani POZ do BZG. Te same huby mogą mieć inne
linie, sezony i godziny dla Bydgoszczy. Brak huba w powyższej tabeli nie
pozwala go pominąć przy sprawdzaniu pełnych siatek.

## 3. Mapa plików do wdrożenia i przeglądu

| Obszar | Pliki i odpowiedzialność |
| --- | --- |
| Endpointy | `data/search-airports.json`, loader `scripts/search_airports.py`: dziesiąty wpis i obecny wyjątek GDN. |
| Instrukcje | `AGENTS.md`, `docs/FIVE_STEP_FLIGHT_SEARCH.md`, `docs/COLLECTION_RELIABILITY.md`, `README.md`: bieżący zakres dziesięciu, bez przepisywania historii wcześniejszych wdrożeń. |
| Audyt | `scripts/audit_airport_expansion.py`, `scripts/discover_transfer_routes.py`: pełne sieci, nowe huby, statusy źródeł i decyzje dotyczące BZG. |
| Generator konfiguracji | `scripts/build_gdn_config_patch.py`: jawne `--endpoint BZG`, kopie do review i opisane niżej ograniczenia. |
| Wizz | `scripts/verify_wizz_expansion_schedules.py`, `scripts/wizz_schedules.py`, `scripts/wizz_api.py`, `data/wizz-route-schedules.json`, lokalne rozkłady 1A/1B. |
| 1A–1F | Sześć allowlist przewoźników i `scripts/collect_step1*.py`: osobny audyt tras, prawidłowe źródła, pełne kalendarze i ceny. |
| 2 | `scripts/collect_step2.py`: pełna macierz dziesięciu endpointów, TFN/TFS, obu linii i kierunków. |
| 3–5 | Trzy allowlisty low-cost i kolektory 3–5: konkretne uprawnienia BZG, nowe huby, warianty A/B. |
| Ceny i linki | `data/spanish-resident-fees.json`, `scripts/spanish_resident_fees.py`, `scripts/booking_urls.py`, `scripts/ryanair_google.py`: zachować poprawne zasady. |
| Kompletność | `scripts/collection_coverage.py`, `scripts/collect_five_steps.py`, `scripts/collector_settings.py`: niezależny plan, nowy run/cache, jeden komplet i limit Google. |
| Strona | `app.js`, `index.html`, warunkowo `styles.css`: etykieta BZG, multiselect dziesięciu opcji, kalendarz/wykres/karty/share i wersja cache. |
| Testy | Nowy `tests/test_bzg_expansion.py`; bieżące testy endpointów, Wizz, źródeł, coverage, cen i `tests/test_airport_ui.mjs`. |
| Wynik | Dziesięć wygenerowanych feedów i dziesięć sidecarów; nowy raport `docs/WDROZENIE_BYDGOSZCZY_BZG.md`. |

To lista miejsc do sprawdzenia, nie nakaz edycji każdego modułu.
Kolektory są już sterowane danymi. Kod zmieniać tylko przy wykazanej luce,
nie przez dodawanie `if airport == 'BZG'` w każdym kroku.

## 4. Etap A — bezpieczny start po poleceniu wdrożenia

1. Ponownie odczytać instrukcje, HEAD, status/diff i bieżące rejestry.
   Chronić niezwiązane zmiany. Nie zakładać, że plan nadal opisuje aktualny
   checkout lub że lokalny `main` odpowiada najnowszemu `origin/main`.
2. Do nowego `tmp/bzg-expansion/baseline/` skopiować konfigurację, opłaty,
   rozkłady wspólne/lokalne, kod, testy, dokumentację, `app.js`, `index.html`,
   `styles.css` oraz wszystkie 20 plików wynikowych/raportów. Zapisać SHA-256,
   daty, run ID i stan istniejących zmian. Nie nadpisywać wcześniejszego backupu.
3. Utrwalić wejścia regresji dotychczasowej dziewiątki. Porównanie dwóch
   niezależnych pobrań cen nie zastępuje testu tego samego zamrożonego wejścia.
4. Wybrać dzień startu `D` według `Atlantic/Canary`; używać go jawnie w całym
   przebiegu. Daty 23.10–22.11 z tego dokumentu są historycznym baseline.
5. Dopisać BZG do `search-airports.json`, bez nowych wyjątków transferowych.
   Narzędzia uruchamiać w świeżych procesach — endpointy ładowane przy imporcie.
   Przed tą zmianą CLI z `choices=POLISH_AIRPORTS` nie przyjmie `--endpoint BZG`.
6. Konfiguracja dziesięciu + stare feedy dziewięciu to stan przejściowy,
   nie ukończone wdrożenie i nie kompletna nowa baza BZG.

Nie uruchamiać jeszcze kolekcji cen ani promocji. Domyślnie wdrożenie lokalne;
commit/push lub workflow wymagają odrębnego zakresu. Nowa gałąź, jeśli potrzebna,
z prefiksem `codex/`, bez resetowania istniejącej pracy.

## 5. Etap B — pełny audyt siatek i lista decyzji

### 5.1. Zebranie dowodów, bez automatycznego stosowania zmian

Przykłady do wykonania dopiero podczas wdrożenia; zastąpić `YYYY-MM-DD`:

```bash
.venv/bin/python scripts/audit_airport_expansion.py --endpoint BZG --as-of YYYY-MM-DD --output-directory tmp/bzg-expansion
.venv/bin/python scripts/discover_transfer_routes.py --as-of YYYY-MM-DD --snapshot tmp/bzg-expansion/network-snapshot.json --report tmp/bzg-expansion/discovery-report.json
```

Pierwszy skrypt pobiera pełne oficjalne sieci Ryanaira i Wizza oraz próbuje
sprawdzić Bintera dla wszystkich sąsiadów BZG, nie tylko starych hubów.
Drugi pozostaje dry-run, **bez `--apply`**. Raport może zawierać także nowe
możliwości innych endpointów — nie aktywować ich mimochodem.

Przy RZE `timetable_get` Bintera zwrócił GraphQL E01000 mimo HTTP 200.
Przy BZG ponownie sprawdzić faktyczny stan źródła: błąd zachować jako `failed`,
nie jako pustą siatkę. `--low-cost-only` oznacza Binter `not_checked`.
W takiej sytuacji konieczny niezależny pełny przegląd oficjalnego katalogu
tras/rozkładów Bintera albo jawny blocker. Sam detektor nie dowodzi braku tras.

Oficjalna strona portu może być źródłem pomocniczym, ale lista miast,
rozkład jednego dnia, reklama lotów czy wynik z przesiadką nie wystarczają
do potwierdzenia własnego bezpośredniego odcinka konkretnego przewoźnika.

### 5.2. Przecięcia pełnych sieci, przed porównaniem ze starymi allowlistami

Dla TFN i TFS osobno wyliczyć wszystkie wspólne IATA:

| Wariant | Teneryfa ↔ hub | hub ↔ BZG |
| --- | --- | --- |
| 1A | Binter, uprawniony odcinek | Ryanair lub Wizz Air |
| 3 | Ryanair | Ryanair |
| 4 | Wizz Air | Wizz Air |
| 5A | Ryanair | Wizz Air |
| 5B | Wizz Air | Ryanair |

Przewoźnik jest przypisany do części geograficznej, nie do kolejności lotu
na ekranie. Po odwróceniu podróży nie zamieniać ról A/B. Nawet gdyby audyt
wykazał brak Wizza w BZG, nadal sprawdzić **5B** z Ryanairem po polskiej stronie.
Nie zakładać z góry ani obecności, ani nieobecności Wizza w Bydgoszczy.

Nowe przecięcia sprawdzić również poza unią wszystkich dziewięciu zapisanych
allowlist. Przykład syntetyczny: BZG–NEW Ryanairem oraz NEW–TFS Ryanairem
ma trafić do 3, mimo że NEW nie istniał wcześniej w aplikacji.
Analogicznie BZG–NEW Ryanairem i NEW–TFS Wizzem to kandydat 5B.
To test mechanizmu, nie nazwa realnej nowej trasy.

IATA muszą być identyczne: BVA ≠ ORY/CDG, BGY ≠ MXP, STN ≠ LTN,
BBU ≠ OTP. Nie tworzyć połączenia wyłącznie po wspólnej nazwie miasta.
Krawędź opublikowana w jednej orientacji nie zwalnia z późniejszego pobrania
obu kierunków kalendarza.

### 5.3. Osobny audyt wszystkich wariantów rezydenckich

Standardowy detektor nie pokrywa 1B–1F; jego wynik nie kończy tego etapu.
Dla każdej linii porównać pełną odpowiednią siatkę bezpośrednich odcinków
Teneryfy z pełnym zbiorem sąsiadów low-cost BZG:

| Wariant | Wymagane źródło i decyzja |
| --- | --- |
| 1A Binter | Oficjalne destynacje/rozkład, kwalifikacja do rezydenta; nie ograniczać przeglądu do dotychczasowych sześciu hubów. |
| 1B Iberia/Express | Oficjalna bezpośrednia siatka i uprawnienie rezydenckie; nie zakładać, że jedynym możliwym hubem zawsze będzie MAD. |
| 1C Vueling | Własna strona tras Teneryfy jako źródło nadrzędne, Aena tylko pomocniczo; zbadać także huby spoza obecnej siódemki. |
| 1D Air Europa | Oficjalne strony i faktyczny własny bezpośredni odcinek; reklama pary miast nie oznacza lotu direct. |
| 1E Volotea | Oficjalna strona trasy i publiczny MinPrice; pusta sekcja dynamicznej strony nie dowodzi braku trasy. Bez Google Flights. |
| 1F Canaryfly | Oficjalne trasy oraz GraphQL calendar/search, tylko bezpośredni odcinek międzywyspowy. Bez Google Flights. |

W 1A–1F akceptować tylko kwalifikujące się odcinki ze zniżką rezydenta.
Zagraniczny hub może być dopuszczony w 3–5 z pełną ceną, lecz nie w 1A–1F.
Nie kopiować samej informacji „hiszpański kraj” zamiast rzeczywistej
kwalifikacji konkretnej trasy. Zachować jawne wykluczenia, np. FNC w 1A.

Brak kwalifikującej trasy BZG w wariancie udokumentować; nie dodawać fikcyjnej
relacji. Ten feed nadal zbieramy dla innych endpointów. Odróżniać brak trasy,
brak rejsów w oknie i brak wykonalnej przesiadki od awarii źródła.

### 5.4. Tabela decyzji i bramka akceptacji

Zachować lokalną tabelę/JSON z każdym kandydatem, także odrzuconym/pending:

- Wariant, hub IATA, TFN/TFS, obie linie, uprawnienie BZG i kierunki.
- Oficjalne źródła, data weryfikacji, sezon/uruchomienie i status źródła.
- Klasyfikacja: nowy endpoint w starym hubie, hub nowy dla wariantu,
  hub zupełnie nowy globalnie, nowe TFN/TFS przy istniejącym hubie.
- Strefa IANA, kwalifikacja/mnożnik rezydenta, dostępność opłat.
- Brakujące rozkłady Wizz i odpowiadające im numery/blokowe czasy.
- `ready`, `pending`, `rejected` z przyczyną, docelowy rekord i plan zapytań.

Każdy zaakceptowany kandydat ma przejść ścieżkę: dowód → pełny rekord
konfiguracji → plan kalendarzy → faktyczne wywołania → complete coverage.
Nie kończyć na komunikacie „wykrywacz umie znajdować nowe huby”.

## 6. Etap C — techniczne rozkłady Wizz, także po stronie Teneryfy

```bash
.venv/bin/python scripts/verify_wizz_expansion_schedules.py --endpoint BZG --snapshot tmp/bzg-expansion/network-snapshot.json --from-date YYYY-MM-DD --days 30 --output tmp/bzg-expansion/verified-wizz-schedules.json
```

Oficjalny timetable daje daty, odloty i ceny regularne/WDC, ale nie zastępuje
rejestru numerów i blokowych czasów lotu. Każdy nowy aktywny odcinek Wizz
musi mieć zweryfikowane dane obu kierunków, nie tylko jednego przykładowego dnia.

Zakres `required_routes` obejmuje obecnie cztery skierowane pary BZG/TFN/TFS,
polskie nogi 4/5A, hiszpańskich sąsiadów Wizza i brakujące w rejestrze nogi
Teneryfa–hub w 4/5B. Ta ostatnia obsługa **już istnieje**, ma testy LCJ/RZE;
nie planować jej ponownego „naprawiania”. Porównać wynik z pełną tabelą
zaakceptowanych tras, zwłaszcza osobno dodanymi hubami 1A–1F.

Wymagania:

1. Odczytać cały oficjalny kalendarz nowej trasy i sprawdzić każdą aktywną
   datę/godzinę względem resolvera. Pokrycie jednej godziny nie potwierdza
   pozostałych numerów lub czasów, np. po zmianie rozkładu.
2. Zachować W6/W4/W9. Zróżnicowane obserwacje rozstrzygać dowodem:
   data+godzina > ISO weekday+godzina > godzina > bazowa trasa.
   Korzystać z istniejących pól override, bez arbitralnego wyboru konfliktu.
3. Nie traktować flagi `--complete-times` jako dodatkowego zabezpieczenia:
   jest zadeklarowana, ale nie ma osobnej ścieżki działania w obecnym `main`.
   Niezależne porównanie wszystkich aktywnych odlotów jest konieczne.
4. Zweryfikować wspólny `data/wizz-route-schedules.json` i lokalne wpisy
   1A/1B przez `scripts.wizz_schedules`; dla wspólnej trasy wyniki zgodne.
5. Zachować dotychczasowe wyjątki, szczególnie WRO–LPA, datowe POZ–LTN
   oraz RZE–FCO: W46068, 140 min o 08:35 i 130 min o 10:45/22:45;
   FCO–RZE W46067, 135 min. To baseline, nie dane nowego BZG.
6. `--inactive-probe-date` może dostarczyć techniczny dowód trasy sezonowej,
   ale jej ceny/loty spoza okna nie trafiają do nowego feedu. Brak danych
   pozostaje `pending`; nie wymyślać numeru lub przylotu.
7. Nie zmieniać identity dowodów RZE na BZG. Resume pliku dowodowego tylko
   dla tego samego endpointu, dat i snapshotu.
8. Ceny Wizza nadal z oficjalnego API; bieżącą bazę wersji ustala
   `scripts.wizz_api`, bez stałego numeru API w nowych fragmentach kodu.

Techniczne zapytania Google podlegają temu samemu limitowi dwóch.
Nie uruchamiać ich równolegle z kilkoma kolektorami w osobnych procesach.

## 7. Etap D — konfiguracja dziesięciu, bez rozszerzania innych miast

### 7.1. Rejestry i uprawnienia

Wszystkie dziewięć allowlist otrzymuje dokładny `scope.polish_airports`
z rejestru dziesięciu, również wariant bez kwalifikującej się trasy BZG.
Scope nie oznacza automatycznego uprawnienia do wszystkich hubów.

- 1A/1B zachowują pełne macierze hub × wszystkie endpointy × obie linie
  × oba kierunki. Uzupełnić dowody i techniczne wpisy, nie zawężać zapytań
  do wyników innego przewoźnika.
- 1C–1F: tylko potwierdzone pary `polish_airport: BZG` + właściwe `airlines`
  w `polish_routes`. Nie dopisywać obu linii, jeśli działa tylko jedna.
- 3/4: BZG tylko przy potwierdzonych hubach, kompletne nowe rekordy
  i `airport_timezones`, bez zmiany starej listy endpointów huba.
- 5: osobno A i B; ta sama nazwa huba nie przenosi uprawnienia między nimi.
- Dodać BZG do właściwych `excluded_endpoints` 3/4/5. Zachować wyłącznie
  GDN/5B→KRK; żadnego BZG–BZG, BZG jako huba ani GDN→BZG.
- Nowy hub wymaga nazwy, kraju, prawdziwej strefy IANA, TFN/TFS,
  dozwolonych polskich lotnisk/linii, reguły rezydenta i dowodów.

### 7.2. Generator konfiguracji: sprawdzone możliwości i ograniczenia

```bash
.venv/bin/python scripts/build_gdn_config_patch.py --endpoint BZG --snapshot tmp/bzg-expansion/network-snapshot.json --schedules tmp/bzg-expansion/verified-wizz-schedules.json --from-date YYYY-MM-DD --days 30 --baseline-directory tmp/bzg-expansion/baseline/data --output-directory tmp/bzg-expansion/configuration-review
```

Historyczna nazwa helpera nie zmienia endpointu: trzeba jawnie podać BZG.
Wynik to dziesięć plików review: dziewięć allowlist plus wspólny rozkład Wizz,
nie gotowa kolekcja ani bezwarunkowa zgoda na skopiowanie do `data/`.

Przed zastosowaniem:

1. Helper dla 1A–1F przechodzi po **istniejących hubach**. Nie tworzy sam
   nowego pełnego huba tych rodzin. Nową zaakceptowaną kandydaturę dodać
   z kompletnym rekordem albo rozszerzyć helper i testy; nie zgubić jej milcząco.
2. W istniejącym hubie 3–5 nowe TFN/TFS powoduje
   `Review new Tenerife airports explicitly`. Rozwiązać relację jawnie,
   nie usuwać nowej pary, żeby narzędzie przeszło, i nie dublować IATA.
3. Rozszerzenie wspólnego `tenerife_airports` może odblokować dodatkowe
   trasy starej dziewiątki. Ujawnić wpływ; gdy potrzebne, wyrazić relację
   per endpoint, zamiast przypadkiem rozszerzać wszystkie uprawnienia.
4. Nowe huby 3–5 helper potrafi wygenerować. Sprawdzić zgodność z decyzjami,
   time zones, zniżkami i kompletnymi technicznymi danymi obu nóg Wizz.
5. Generator zastępuje wspólny wpis i override'y tras objętych nowymi
   dowodami. Nie utracić starszych zweryfikowanych wyjątków po zebraniu
   tylko części dat; przejrzeć również trasy inne niż BZG.
6. Przy wspólnej trasie używanej przez 1A/1B sprawdzić zgodność lokalnego
   i wspólnego rejestru także wtedy, gdy nie jest to nowa noga BZG.
7. Regex list IATA jest już uogólniony, a regex słów obejmuje już
   „dziewięć” po RZE. Nie powielać przestarzałego zalecenia naprawy tej
   zmiany. Test idempotencji rozszerzyć o BZG; preferować opis neutralny
   „wszystkie polskie lotniska z rejestru”, zamiast mnożyć stałe liczebniki.
8. Powtórzenie tego samego generowania nie tworzy `/BZG/BZG`, duplikatów
   rekordów/uprawnień/rozkładów ani nowych zmian semantycznych.
9. `verified_on` i tekst dowodu opisywać faktycznie. Przestawienie daty
   nagłówka nie jest ponownym sprawdzeniem wszystkich dawnych tras.

Po review porównać semantycznie stare uprawnienia, strefy i rozkłady z baseline.
Zastosować tylko powiązane z BZG zaakceptowane zmiany oraz konieczne poprawki
wykazane testami. Brak nowego huba w audycie nie oznacza naprawy wszystkich
ogólnych ograniczeń helpera.

## 8. Etap E — źródła cen, kolektory i niezależne pokrycie

| Feed | Niezmienna metoda i kontrola BZG |
| --- | --- |
| 1A | Pełny Binter route/day obu kierunków, niezależna pełna macierz Ryanair/Wizz, wybór cash fare i final imports. |
| 1B | Każdy dzień Iberii/Express Google HTTP, niezależna macierz low-cost, estymata z opłatami i oficjalny link. |
| 1C | Każdy zapisany dzień Vuelinga Google HTTP i pełne zapisane polskie pary/carriers, bez ograniczania dni drugą linią. |
| 1D | Air Europa wyłącznie Google HTTP: wszystkie grupy ofert, pełny numer UX, daty/godziny i własna cena każdego rejsu. |
| 1E | Oficjalny Volotea MinPrice osobno route/day w obu kierunkach; cena z opłatami, kontrola opłat, bez Google. |
| 1F | Wszystkie pełne miesiące Canaryfly obu kierunków, następnie szczegóły wszystkich dostępnych dni i final imports, bez Google. |
| 2 | Pełna macierz BZG/TFN/TFS × obie linie × oba kierunki × wszystkie dni; puste rynki też muszą być poprawnie sprawdzone. |
| 3 | Pełne kalendarze obu nóg Ryanaira, potem matching. |
| 4 | Pełne kalendarze obu nóg Wizza, kompletne numery/przyloty z rejestru, potem matching. |
| 5 | Pełne niezależne kalendarze obu linii, oba warianty i oba kierunki; role geograficzne bez zmian. |

### 8.1. Ceny i linki

- Ryanair/UK: tylko Google HTTP, FR/RK, najniższa indywidualna cena każdego
  rejsu w PLN, numery i godziny z jego oferty. Bez Fare Finder/minimum dnia.
  Wspólny persistent cache route/day dla całego nowego batcha.
- Air Europa: również tylko Google HTTP, bez oficjalnego promocyjnego feedu
  jako fallbacku i bez rozszerzania dziennego minimum na szablon rozkładu.
- Binter: `booking_search` tylko wybiera taryfę gotówkową EUR. Token
  wyłącznie w pamięci do `booking_getImports`, jeden dorosły, `RC` na
  uprawnionej trasie. Suma `mainAmount` regularna, `totalAmount` rezydencka,
  ze wszystkich wymaganych komponentów. PTS nie jest taryfą EUR.
- Canaryfly: analogicznie końcowe imports dla jednego dorosłego, kod `DC`,
  potwierdzenie statusu i komplet komponentów. Nie zapisywać ceny listowej
  jako końcowej i nie zastępować oficjalnego total estymatorem Aeny.
- Iberia/Express, Vueling, Air Europa, Volotea i uprawnione hiszpańskie nogi
  Teneryfy Ryanair/Wizz w 3–5:
  `opłaty_PLN + 0.25 × (cena_regularna_PLN − opłaty_PLN)`.
  Oznaczyć szacunek, nie oficjalną wycenę. Polska noga zawsze pełnopłatna.
- Kierunkowe opłaty tylko przez `scripts.spanish_resident_fees` z kanonicznej
  tabeli. Obecna ważność: 2026-03-01–2026-12-31; sprawdzić całe nowe okno.
  Nowa kwalifikująca hiszpańska para potrzebuje potwierdzonych opłat obu
  kierunków. BZG jako polski endpoint nie wymaga dopisania opłaty Aeny.
- NBP: jeden dzienny cache `tmp/nbp-rates/YYYY-MM-DD.json`, ostatnie
  opublikowane tabele do danego dnia, te same kursy we wszystkich feedach.
  Nie odpytujemy NBP na każdym kroku ani nie używamy cache poprzedniego dnia.
- Każda noga otrzymuje `booking_url` z `scripts.booking_urls` dla swojej
  linii, trasy, daty i pasażerów. Bez tokenów, kluczy, cookies i sesji.
  Google jako źródło cen nie zmienia przewoźnika docelowego zakupu.
- Air Europa: `residentType=SPANISH_RESIDENT_RC`, usuwany po wyłączeniu
  rezydenta; nie `true`. Wizz/Ryanair/Air Europa mają wyszukiwanie trasy/dnia,
  bez gwarancji automatycznego zaznaczenia konkretnego numeru rejsu.
  Volotea/Canaryfly wybór rezydenta w swoim procesie, bez wymyślonych URL flags.

Nie uruchamiać repricingu starych feedów jako substytutu nowej kolekcji BZG.
Nie mieszać cen starego runu z nowymi ani nie recertyfikować starej bazy.

### 8.2. Plan zapytań i przewidywalny wzrost

`scripts.collection_coverage.expected_queries` wylicza zapytania z macierzy
i allowlist przed pobraniem danych. Każda zaakceptowana noga BZG/nowego huba
musi mieć oba kierunki i każdą datę w planie oraz w rzeczywistym wykonawcy.
Testować wywołania pobrań, nie tylko builder gotowych odcinków.

Przy niezmienionej liczbie hubów i oknie 31 dat:

| Zakres | Obecne 9 endpointów | Docelowe 10 |
| --- | ---: | ---: |
| 2: skierowane pary na jednego przewoźnika | 36 | 40 |
| 2: pary trasa/linia obu przewoźników | 72 | 80 |
| 2: pozycje route/day | 2232 | 2480 |
| 1A: pełny plan przy obecnych 6 hubach | 7440 | 8184 |
| 1B: pełny plan przy obecnym MAD | 1240 | 1364 |

Przyrost kroku 2: 248 pozycji, około 11,11%. Nowe huby, TFN/TFS lub dodatkowe
uprawnienia zmienią resztę macierzy. Policzyć rzeczywisty pełny plan po audycie;
nie obiecywać z góry liczby lotów BZG, liczby HTTP ani czasu kolekcji.

Sprawdzone puste dni są kompletne, ale błędna struktura, GraphQL `errors`
przy HTTP 200, brak ceny lub danych rejsu oznaczają błąd przed promocją.
Pokrycie potwierdza ukończenie planu i walidację znanego formatu, nie gwarancję,
że dostawca nigdy nie zwróci poprawnie wyglądających niepełnych danych.

Wspólny limit z `scripts.collector_settings` obowiązuje również retry.
Runner uruchamia feedy kolejno; nie równoleglić kilku procesów Google,
bo osobne ograniczenia ich wątków nie dają globalnego limitu dwóch.

## 9. Etap F — strona, multiselect i wszystkie zależne widoki

Dodać `BZG: "Bydgoszcz (BZG)"` do `airportLabels` w `app.js`.
Etykiety ewentualnych nowych hubów dopiero po audycie. W `index.html`
uzupełnić informację o lotniskach i podnieść wersję JS; CSS tylko jeśli zmieniany.
Nie przebudowywać innych filtrów ani nie zmieniać zaakceptowanego copy.

Zachować istniejący wielokrotny wybór:

- Polskie lotniska: `<details>` z checkboxami; Teneryfa: pojedynczy select.
  Legacy selecty ukryte po polskiej stronie nadal służą kompatybilności.
- `state.polishAirports` to posortowany zbiór, `[]` = wszystkie;
  jawny wybór całego dostępnego zestawu normalizuje się do `[]`.
- Opcje pochodzą z unii endpointów rzeczywistych wyników obu kierunków,
  nie wprost z rejestru. Nie tworzyć fikcyjnej oferty/checkboxa BZG,
  jeżeli pełny batch nie ma żadnego jego wyniku w obu kierunkach.
- Jeśli BZG ma oferty tylko w jednym kierunku, opcja dzięki unii pozostaje
  wybieralna również po odwróceniu kierunku. Zero ofert nie jest błędem UI.
- Wybór BZG + RZE + KRK to suma OR, nie podróż między tymi miastami.
  Zmiana kierunku zachowuje wybór i przenosi go z roli wylotu do przylotu.
- X usuwa tylko dany endpoint; usunięcie ostatniego przywraca wszystkie.
  Reset dat zachowuje lotniska; pełny reset oraz share zdejmują ograniczenie
  lotnisk zgodnie z obecnym mechanizmem.
- `fareCalendarRenderKey` i `resultCardsRenderKey` uwzględniają cały
  znormalizowany wybór, bez starych minimów po zmianie BZG.

Przetestować BZG samo oraz z co najmniej dwoma starymi lotniskami w obu
kierunkach: zgodność cen kart/minimów kalendarza/wykresu, kliknięcie tego samego
ID najtańszego lotu, rozwinięcie karty, cztery kombinacje rezydent/WDC,
osiem sortowań, +1 po północy i działający share także ponad 1000 zł.

Dziesiąty checkbox wymaga kontroli dolnego wiersza, scrolla listy, „Gotowe”,
„Wszystkie”, focusu, Escape i kliknięcia poza menu na desktop oraz około
320 px. Zachować `.search-panel:has(.airport-multi[open])` nad kalendarzem
i progresywne przygotowanie kart. Sam wzrost liczby lotnisk nie wymaga
zmiany układu, jeśli istniejący mieści nową opcję.

## 10. Etap G — testy i konkretne pułapki po RZE

### 10.1. Nowe testy BZG i aktualne macierze

Dodać `tests/test_bzg_expansion.py` z jawnym historycznym zbiorem:

```python
NINE = ("WAW", "WMI", "KTW", "KRK", "GDN", "WRO", "POZ", "LCJ", "RZE")
```

Sprawdzić:

- Dokładny rejestr `NINE + ("BZG",)`, strefę Warsaw i dziewięć zgodnych scope.
  Nie zmieniać liczby plików allowlist z 9 na 10.
- Konkretne zweryfikowane uprawnienia BZG, brak niezatwierdzonych dopisków
  do pozostałych endpointów i brak nowych ról polskich transferów.
- Syntetyczny zupełnie nowy hub NEW: discovery → pełny rekord → oba
  kierunki i całe okno rzeczywistych planów zapytań. Osobno 1A–1F,
  3/4/5A/5B i nowe TFN/TFS istniejącego huba; pending Wizza bez aktywacji.
- Każdy aktywny odlot nowych nóg Wizz rozwiązuje numer, przylot, blok time
  i właściwy override; zachowane stare wspólne/lokalne wyjątki.
- Mocki faktycznych executorów dla BZG i nowych hubów: pełne okno mimo
  pustej drugiej linii; szczegóły Canaryfly dla wszystkich dostępnych dni.
- Step 2: 40 par na przewoźnika, 80 para/linia, 31 dat, również wszystkie
  cztery skierowane BZG/TFN/TFS. Fixture dwóch hubów low-cost: 40 wywołań
  na linię zamiast 36, jeśli test nadal używa dwóch hubów i pełnej macierzy.
- Idempotencja generatora, brak utraty nowego huba, brak samotras,
  brak niesprawdzonych nowych nóg i fałszywych opisów dowodów.
- Własne ceny każdego rejsu Ryanair/Air Europa, wszystkie grupy ofert,
  FR/RK, limity Google/retry, wspólny NBP, końcowe imports i opłaty.

### 10.2. Przejrzeć istniejące testy, nie usuwać historii

Pliki z bieżącymi założeniami liczbowymi:
`test_airport_expansion.py`, `test_wro_expansion.py`, `test_poz_expansion.py`,
`test_lcj_expansion.py`, **`test_rze_expansion.py`**, `test_step2_collector.py`
oraz `test_source_completeness.py`.
Aktualne listy i macierze zmienić 9→10, 36→40, 72→80 tam, gdzie to wynika
z definicji. Nazwy metod uaktualnić, jeśli opisują bieżącą pełną macierz;
nie pozostawiać np. nazwy „sixty_four” po teście 80 par.

Nie robić globalnej zamiany liczb. **Osiem sortowań**, dziewięć plików
allowlist, historyczne SIX/SEVEN/EIGHT i opublikowane wyniki pozostają
sobą. Nowa zmiana ma własny zamrożony NINE.

Konkretne uwagi z obecnego kodu:

1. W `test_rze_expansion.py` aktualne asercje rejestru, planu `72 * 31`
   i executorów `36` wymagają aktualizacji. Natomiast wejścia regresji
   `EIGHT + ("RZE",)` są już jawnie zamrożone i **nie** powinny zawierać BZG.
2. Fixture LCJ w builderach jest już zamrożone do `SEVEN + ("LCJ",)`,
   a POZ do `SIX + ("POZ",)`. Nie powielać starych zaleceń ich naprawy
   ani odtwarzać błędu `direct[:-1]` lub „bieżące minus jedno lotnisko”.
3. W RZE test `old-eight` tworzy plan przez odjęcie tylko RZE z bieżącego
   planu. Po dodaniu BZG nie będzie to literalna ósemka. Albo zamrozić
   historyczny zbiór do EIGHT (bez RZE i BZG), albo uczciwie rozdzielić
   test aktualnego braku RZE od historycznej certyfikacji. Zachować obie
   intencje, nie akceptować starego raportu jako kompletnego dla dziesięciu.
4. Analogicznie nazwy historycznych testów coverage LCJ nie mogą być
   dowodem, że ich fixture faktycznie ogranicza się do siedmiu endpointów.
   Sprawdzić zakres, a brak jednej nogi bieżącej macierzy testować osobno.
5. **JS „ninth RZE checkbox…”** pobiera obecne wyniki bez RZE i dokleja
   syntetyczne RZE. Po nowej kolekcji zostawiłby w tej fixture BZG,
   łamiąc asercję dziewięciu checkboxów. Zamrozić to wejście do dziewięciu
   historycznych endpointów albo rozdzielić test historyczny od aktualnego.
   Nie usuwać testu i nie osłabiać asercji.
6. Nowy test „tenth BZG checkbox” ma fixture wszystkich dziesięciu;
   kolejność kodów: BZG, GDN, KRK, KTW, LCJ, POZ, RZE, WAW, WMI, WRO.
   Obecny test „all available endpoints…” oczekuje pierwszego GDN.
   Po BZG będzie to Bydgoszcz — wyprowadzić oczekiwanie z poprawnego
   dostępnego zestawu/etykiet albo zamrozić jego historyczne wejście.

Na tych samych zamrożonych dziewięciu wejściach porównać przed/po:
wszystkie dziesięć builderów, oba kierunki, oba warianty 5, ID, ceny,
linki i liczbę starych wyników. Zachować uprawnienia RZE 1C/ALC,
3/BRS,DUB,EDI,LTN,MAN,MXP,STN, 4/FCO, 5A/FCO, 5B/MXP i jego rozkłady.

### 10.3. Brzegowe przypadki i testy strony

- 120/1440 min akceptowane, 119/1441 odrzucone; przerwana trasa, inne
  IATA, odwrotna chronologia, self-route i drugi transfer odrzucone.
- Start/koniec okna, dwa różne dni odlotów, zmiana DST i +1 przylotu.
- Stary raport dziewięciu nie certyfikuje dziesięciu. Brak jednego BZG
  route/day, nowego huba lub szczegółów 1F blokuje promocję.
- Różne run ID/okna/kursy, niezgodny sidecar, failure dnia, wadliwe imports,
  brak/przeterminowanie opłaty oraz zmieniony hash przy resume: fail closed.
- W JS: BZG samo i OR ze starymi, dwa kierunki, cztery warianty cen,
  osiem sortowań, chipy X, wszystkie resety, cache, kalendarz/wykres/karta,
  share z odtworzeniem ustawień, droższy share ponad 1000 zł.
- Fixture BZG bez wyników i tylko w jednym kierunku: bez fikcyjnych cen,
  prawidłowa unia opcji i zachowanie wyboru po odwróceniu podróży.
- Mechanizm BZG w rodzinie bez realnej trasy sprawdzić syntetycznie,
  nie dopisywać fikcyjnego lotu do publicznego feedu dla zaliczenia testu.

Przed pełną kolekcją:

```bash
.venv/bin/python -m unittest discover -s tests -p 'test_*.py'
node --test tests/test_airport_ui.mjs
node --check app.js
git diff --check
```

Wynik na starej bazie dziewięciu to regresja + testy syntetyczne BZG,
nie odbiór świeżej bazy. Nowy test danych rzeczywistych wykonać po kolekcji.
Jeśli poprawnie zebrany cały batch nie ma ofert BZG, nie ukrywać tego
skipem opisanym jako sukces pełnej ścieżki — podać jawny wynik oraz zakres
testów syntetycznych. Liczbę testów po zmianie zmierzyć, nie przepisać 208/30.

## 11. Etap H — nowa pełna kolekcja, nie doklejanie BZG

Po zakończonym audycie, konfiguracji i testach zebrać **wszystkie dziesięć
feedów dla dziesięciu endpointów** do unikatowego nowego stagingu.
Nie poprawiać ręcznie feedów, nie kopiować cen/cache RZE pod nową nazwę.

```bash
.venv/bin/python scripts/collect_five_steps.py --from-date YYYY-MM-DD --days 30 --stage-directory tmp/bzg-expansion/batch-YYYY-MM-DD-RUN --workers 4
```

`RUN` w nazwie to etykieta katalogu; właściwy UUID generuje runner i zapisuje
w raportach. Kolejność: `1, 1b, 1c, 1d, 1e, 1f, 2, 3, 4, 5`, sekwencyjnie.
`--workers 4` nie podnosi limitu Google ponad 2. Nowy run dostaje świeży cache,
metadane dat i hash konfiguracji. Nie uruchamiać dodatkowych probe'ów Google
w innych procesach podczas tej kolekcji.

Przy błędzie publiczne 20 plików pozostają stare. Zachować logi,
`validation-report.json` i sidecar `step*-results.collection-report.json`
ze statusem failed w stagingu; nie oczekiwać odrębnej nazwy `.failed.json`.
Usunąć przyczynę, a nie walidację. Przykład przerwania na 3:

```bash
.venv/bin/python scripts/collect_five_steps.py --from-date YYYY-MM-DD --days 30 --stage-directory tmp/bzg-expansion/batch-YYYY-MM-DD-RUN --workers 4 --run-id UUID_Z_PIERWOTNEGO_RAPORTU --refresh-steps 3 4 5
```

Wznawiać wadliwy oraz niewykonane późniejsze kroki z tym samym runem,
oknem i hashem. Po błędzie 1C: `1c 1d 1e 1f 2 3 4 5`, nie od nowa 1A/1B.
Zmiana konfiguracji lub dat wymaga nowego runu/stagingu/cache.
Przejście na kolejny dzień rozstrzygnąć jawnie — walidacja wymaga bieżącego
dnia generacji. Nie przepisywać timestampów, aby ominąć tę bramkę.

## 12. Etap I — odbiór kompletu i faktyczne sprawdzenie strony

```bash
.venv/bin/python scripts/collect_five_steps.py --from-date YYYY-MM-DD --days 30 --stage-directory tmp/bzg-expansion/batch-YYYY-MM-DD-RUN --validate-only
RESIFLY_TEST_DATA_DIRECTORY=tmp/bzg-expansion/batch-YYYY-MM-DD-RUN node --test tests/test_airport_ui.mjs
```

Nie włączać ponownego pobierania tylko w celu sprawdzenia istniejącego stagingu.
Odebrać:

1. Dziesięć poprawnych feedów i dziesięć identycznych sidecarów, jeden run,
   okres i dzienny zestaw kursów, nowy zgodny hash konfiguracji.
2. Wszystkie complete, zero missing/unexpected; plan dziesięciu endpointów,
   wszystkie nowe huby i nogi BZG, szczegóły 1F zgodne z miesięcznym skanem.
3. Tabelę wyników i pokrycia dla każdego feedu, endpointu, kierunku,
   wariantu 5 i nowych hubów. Zero z opisem przyczyny, nie pominięty wiersz.
4. Ciągłość IATA, strefy i UTC, 120–1440 min, odloty obu nóg w oknie,
   numery/godziny, ceny, oddzielne zniżki, unikalne ID i linki bez sesji.
5. Dokładny zbiór unikalnych route/day cache Ryanaira względem planu,
   `status=ok` i wyłącznie `google_flights_http`. Nie przepisać liczby
   16 492 z baseline RZE jako oczekiwania dla BZG.
6. Próbki rzeczywistych BZG w obu kierunkach i każdej występującej rodzinie,
   rozbicie cen, WDC, rezydent, pełne opłaty i oficjalne totals, o ile występują.
7. Zamrożona regresja potwierdza algorytm; porównanie starej i nowej ceny
   na żywo tylko informacyjnie. Zmiana taryfy sama nie dowodzi błędu.
8. Stare publiczne 20 plików nadal odpowiada baseline przed promocją.

Browser QA: izolowana kopia statycznej strony ze stagingiem albo po
bezpiecznej promocji lokalnej. Nie zmieniać produkcyjnej ścieżki feedów
tylko dla testu i nie podmieniać części publicznych plików.

Sprawdzić desktop i około 320 px: dziesięć opcji, menu nad kalendarzem,
BZG+RZE+KRK, zmiana kierunku, minima i kliknięcie tej samej karty,
otwarcie szczegółów, +1, resety, copy/share i brak błędów konsoli.
Sprawdzić rzeczywisty schowek/ponowne otwarcie skopiowanego linku oraz
parametry docelowych linków zakupu bez dokonywania zakupu.

Przy RZE sterowanie przeglądarką było wyłączone w Work. Podczas wdrożenia
BZG sprawdzić to ponownie; nie zakładać automatycznie ani usunięcia, ani
utrzymywania blokady. Przy braku dostępu oznaczyć UI/schowek jako otwarty
odbiór, z dowodami testów logicznych i HTTP, bez udawania wizualnej weryfikacji.

## 13. Etap J — promocja lokalna, weryfikacja i rollback

Po kompletnym odbiorze danych i testów, w zakresie osobnego polecenia wdrożenia:

```bash
.venv/bin/python scripts/collect_five_steps.py --from-date YYYY-MM-DD --days 30 --stage-directory tmp/bzg-expansion/batch-YYYY-MM-DD-RUN --validate-only --promote
```

Runner ponownie waliduje całość, przygotowuje 20 plików i zachowuje stare
w `previous-public-feeds/` z manifestem. Obsłużony błąd podmiany przywraca
stary komplet; nie jest to jedna atomowa transakcja odporna na nagłe zabicie
procesu lub utratę zasilania. Nie usuwać niezależnego baseline.

Po promocji porównać bajtowo wszystkie publiczne feedy/sidecary ze stagingiem,
backup z baseline; ponownie walidować publiczną bazę i testy JS.
Po lokalnym HTTP sprawdzić status 200 i aktualne bajty `index.html`, `app.js`
oraz wszystkich 20 plików, nie tylko nagłówek strony lub parametr `?build=`.

Jeżeli trzeba wycofać BZG, przywrócić spójny pakiet kodu, konfiguracji
i 20 plików sprzed wdrożenia, z zachowaniem niezwiązanych zmian użytkownika.
Samo wgranie feedów dziewięciu pod konfigurację dziesięciu to nie rollback.
Bez `git reset --hard`, globalnego odrzucania plików lub kasowania katalogów.

Utworzyć `docs/WDROZENIE_BYDGOSZCZY_BZG.md` z faktycznymi:

- datą, baseline HEAD/gałęzią, zakresem i stanem Git;
- źródłami pełnych siatek, decyzjami wszystkich wariantów, nowymi globalnymi
  hubami/TFN/TFS, sezonowością, pending/odrzuceniami i błędami;
- konfiguracją BZG, strefami, rozkładami/override'ami i opłatami;
- run ID, okresem, kursami, hashem, ścieżką stagingu/cache i backupu;
- tabelą wyników, obu kierunków i complete coverage każdego feedu/endpointu;
- próbkami danych i linków, liczbami testów, HTTP, wizualnym odbiorem lub
  konkretnym otwartym ograniczeniem;
- wynikiem promocji, porównaniem bajtów i instrukcją spójnego rollbacku;
- brakiem commita/push/workflow, jeśli polecenie obejmowało tylko lokalne wdrożenie.

Bieżące instrukcje i README zaktualizować do dziesięciu endpointów dopiero
przy realizacji. Nie przepisywać dawnych wyników/planów RZE/WRO/POZ/LCJ
jakby od początku zawierały BZG. Źródła Air Europa i opis szacunku opłat
w README zostały poprawione przy RZE — zachować tę zmianę.

## 14. Etap K — GitHub i automatyzacja tylko na osobne polecenie

Po lokalnym wdrożeniu przedstawić wynik i czekać na zgodę publikacji.
Ta część nie jest autoryzacją commita/push. Przy późniejszym poleceniu:
sprawdzić status, testy i remote, jawnie dodać tylko związane pliki,
commit oraz zwykły push bez force do uzgodnionej gałęzi.

Publikowany pakiet: konfiguracja, niezbędny kod/testy, dokumentacja,
wszystkie dziesięć feedów i dziesięć sidecarów z jednego nowego runu.
Nie publikować `tmp/`, lokalnych logów/cache/backupów, tokenów i sesji.
Sam wpis BZG bez spójnej nowej bazy nie kończy wdrożenia.

Nie dodawać teraz workflow pobierającego ceny. Przyszłe GitHub Actions
użyją tego samego rejestru, requirements, pięciu kroków, sekwencyjnego runnera,
cache NBP/Ryanaira i bramek. Discovery osobno od zwykłego odświeżania,
najpierw dry-run/raport i review. Obecny push strony nie dowodzi gotowej
automatycznej kolekcji cen.

## 15. Checklista do realizacji

Stan po osobnym poleceniu wdrożenia; szczegółowe dowody w raporcie realizacji:

- [x] Osobne polecenie wdrożenia, aktualny status/instrukcje i pełny baseline.
- [x] Dziesiąty endpoint BZG, dziewięć scope i niezmieniony wyjątek GDN 5B→KRK.
- [x] Pełne aktualne sieci BZG, także zupełnie nowe huby, prawdziwe statusy źródeł.
- [x] Osobny audyt 1A–1F, 2, 3, 4, 5A/5B i tabela wszystkich decyzji.
- [x] Przegląd nowych globalnych hubów/TFN/TFS: nie znaleziono, bez twierdzenia o naprawie ogólnego helpera.
- [x] Przegląd technicznych danych nowego Wizza: brak aktywnej trasy BZG, zero pending; nie wymyślano rozkładu.
- [x] Uprawnienia/strefy/rozkłady dotychczasowej dziewiątki zachowane, generator idempotentny.
- [x] Prawidłowe końcowe ceny/estymaty, opłaty ważne w całym oknie i trwałe linki.
- [x] Pełne niezależne kalendarze faktycznych executorów i plan dziesięciu.
- [x] Aktualne asercje 40/80, zachowane historyczne fixture i naprawiony zakres testu checkboxa RZE.
- [x] Nowe testy BZG oraz zamrożona regresja dziewięciu we wszystkich builderach.
- [x] Multiselect dziesięciu, OR, oba kierunki, cztery ceny, minima/karty/share/+1 — testy logiki.
- [x] Nowy pełny batch wszystkich dziesięciu feedów, jeden run/NBP, Google ≤ 2.
- [x] Dziesięć feedów i dziesięć raportów: complete, bez braków/nadmiarów.
- [x] Odbiór próbek i HTTP; jawny blocker przeglądarki/schowka.
- [x] Lokalna promocja, kompletne kopie, weryfikacja bajtowa i raport wdrożenia.
- [x] Brak publikacji bez nowej zgody; workflow zbierania cen poza tym zadaniem.
- [ ] Wizualny odbiór desktop/320 px i systemowego schowka — sterowanie przeglądarką wyłączone w Work.

„Gotowe lokalnie” oznacza spójny kod, konfigurację, nową kompletną bazę
i udokumentowany odbiór z jawnymi ograniczeniami. Zero BZG w jakimś wariancie
może być prawidłowe, ale nie może wynikać z pominięcia nowego huba, dnia,
drugiej linii, technicznych danych Wizza ani z ukrycia awarii jako braku lotów.
