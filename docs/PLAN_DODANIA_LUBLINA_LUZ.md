# Plan dodania Lublina (LUZ) jako jedenastego polskiego lotniska ResiFly

Plan wykonawczy przygotowany **23.10.2026**, po wdrożeniu i publikacji BZG.
Baseline HEAD: `8f9f1d0aa4ac58dbde5658bcb819037192dad06d`, checkout
`codex/add-lodz-lcj`. Historyczna nazwa gałęzi nie opisuje obecnego zakresu.
Repozytorium przed zapisaniem tego planu było czyste.

**Aktualizacja 23.10.2026: realizacja lokalna zatwierdzona.** Użytkownik osobno
udzielił trwałej zgody na GDN w wariancie 5B dla LUZ, obok istniejącego KRK.
Ta decyzja zastępuje wszystkie poniższe domyślne zakazy LUZ/GDN i bramki
oczekujące na zgodę; nie rozszerza innych miast ani wariantów. Pierwszy odbiór
był lokalny. Wdrożenie i pełną bazę ukończono 24.10.2026; następnie użytkownik
osobno zatwierdził wysłanie na GitHub. Faktyczny odbiór i ograniczenia:
[`WDROZENIE_LUBLINA_LUZ.md`](WDROZENIE_LUBLINA_LUZ.md).

**Stan w chwili przygotowania planu: tylko plan.** Nie zmieniono rejestru lotnisk,
allowlist, kolektorów, strony ani publicznych feedów. Nie uruchomiono nowej
kolekcji cen, pełnego discovery LUZ ani technicznego skanu Wizza. Ponownie
sprawdzono obecną bazę i testy; ich mocki nie są pobieraniem nowych lotów.
Przejrzano także wskazane niżej oficjalne strony portów, ale nie zastępuje to
pełnego audytu sieci przewoźników przy realizacji.

Kod **LUZ**, nie LUB, potwierdza [oficjalna karta operacyjna portu Lublin](https://www.airport.lublin.pl/en/dane-operacyjno-techniczne/).
Wiążące zasady: `AGENTS.md`, `docs/FIVE_STEP_FLIGHT_SEARCH.md`,
`docs/COLLECTION_RELIABILITY.md`. Realizacja wymaga nowego polecenia.
Wcześniejsza zgoda na GitHub dla BZG nie obejmuje wdrożenia/publikacji LUZ.

## 1. Cel, zakres i niezmienne reguły

Docelowy rejestr, z zachowaniem obecnej kolejności:

**WAW, WMI, KTW, KRK, GDN, WRO, POZ, LCJ, RZE, BZG, LUZ**.

Nowy rekord w `data/search-airports.json`, dopiero podczas wdrożenia:

```json
{ "iata": "LUZ", "name_pl": "Lublin", "timezone": "Europe/Warsaw" }
```

Obsłużyć LUZ → TFN/TFS i TFN/TFS → LUZ oddzielnie. Audyt ma szukać także
**zupełnie nowych wspólnych IATA, których nie ma w żadnej obecnej allowliście**,
nowych hubów dla danego wariantu i nowego TFN/TFS w istniejącym hubie.
Nie kopiować połączeń BZG, RZE, LCJ ani listy przykładowych miast z tego planu.

Zachować:

- Dokładnie **pięć głównych kroków**, sześć wariantów 1A–1F, **dziesięć feedów**
  i dziesięć sidecarów. Dziewięć plików allowlist pozostaje dziewięcioma.
  Jedenasty endpoint nie oznacza jedenastego feedu ani jedenastej allowlisty.
- Dzień startu D według `Atlantic/Canary`, `--days 30`: **31 dat włącznie**.
  Każda zapisana noga każdego przewoźnika w obu kierunkach ma niezależny pełny
  kalendarz. Nie wybierać jej dat z rozkładu drugiej linii.
- Dopasowywanie dopiero po kompletnych kalendarzach. Odloty obu nóg w tym samym
  oknie, przylot może być +1. Maksymalnie jedna przesiadka, ten sam IATA,
  120–1440 min włącznie, poprawne UTC/IANA/DST.
- GDN jako polski hub wyłącznie 5B dla KRK i LUZ. Osobna zgoda użytkownika
  z 23.10.2026 jest trwała i obejmuje przyszłe kolekcje (sekcja 4).
- Obecne rodziny linii. Bez dodawania LOT-u, czarterów, innych przewoźników,
  dojazdów między lotniskami lub drugiej przesiadki bez osobnej decyzji.
- Brak limitu ceny w kolektorach. Strona nadal domyślnie Polska → Teneryfa,
  1000 zł, do 6 h przesiadki, najbliższy termin. Oddzielne ceny regularne,
  rezydenta i WIZZ Discount Club.
- Ryanair i Air Europa: bieżące numery/godziny/indywidualne PLN tylko z Google
  Flights HTTP. Wszystkie rozpoznane grupy ofert, FR/RK, bez minimum dnia
  rozciąganego na inne rejsy, Fare Finder i promocyjnych fallbacków.
- Google najwyżej dwa równoległe żądania, także retry i techniczne sprawdzenia.
  Jeden dzienny zestaw NBP i świeży cache Ryanaira dla całego nowego runu.
- Binter i Canaryfly: oficjalne końcowe totals. Pozostałe uprawnione odcinki:
  jawne estymaty z pełnymi niedyskontowalnymi opłatami, nie 25% całej ceny.
- Trwałe `booking_url` na każdej nodze, bez tokens/cookies/sesji. Nie obiecywać
  automatycznego zaznaczenia numeru lotu, jeżeli link wskazuje tylko trasę/datę.
- Dotychczasowe uprawnienia, strefy i techniczne rozkłady dziesięciu zachowane.
  Na tych samych zamrożonych wejściach stare wyniki/ID/ceny/linki nie zmieniają
  się. Różnica cen między dwoma żywymi pobraniami nie zastępuje tej regresji.

## 2. Zweryfikowany baseline po BZG

Rejestr i scope wszystkich dziewięciu allowlist mają dziesięć endpointów.
LUZ nie występuje w obecnej konfiguracji, rejestrze Wizz, kodzie strony
ani testach. Ponowne `validate_batch` podczas opracowania planu przeszło.

Okno obecnej bazy: **2026-10-23–2026-11-22**, run
**`e0322930-e323-4c8c-9f08-459723852a72`**. Wszystkie osadzone raporty są
`complete`, sidecary identyczne, zero braków/nadmiarów: **15 407 propozycji,
35 464 pozycji pokrycia**. To baseline, nie przyszły wynik LUZ ani gwarancja
aktualności tych cen w dniu późniejszego wdrożenia.

| Feed | Wyniki | Bazowy plan tras/dni | Kompletne pokrycie |
| --- | ---: | ---: | ---: |
| 1A (`step1`) | 2777 | 8184 | 8184 |
| 1B | 2174 | 1364 | 1364 |
| 1C | 2844 | 3534 | 3534 |
| 1D | 853 | 744 | 744 |
| 1E | 8 | 248 | 248 |
| 1F | 221 | 434 | 558 |
| 2 | 203 | 2480 | 2480 |
| 3 | 5408 | 11718 | 11718 |
| 4 | 210 | 1364 | 1364 |
| 5 | 709 | 5270 | 5270 |

1F dodaje 124 wymagane sprawdzenia szczegółów po kompletnych kalendarzach.
Pokrycie nie jest liczbą HTTP ani liczbą rejsów. Cache Ryanaira tego runu:
17 360 unikalnych route/day; nie kopiować tej liczby/cache jako celu dla LUZ.

Endpointy: WAW 1980, WMI 1896, KTW 773, KRK 5069, GDN 1958, WRO 2241,
POZ 817, LCJ 209, RZE 277, BZG 187. GDN jako transfer: 7 wyników, tylko 5B/KRK.
Ponownie przeszło **220 testów Python i 34 JS, bez pominiętych**.

Wyniki BZG nie są szablonem uprawnień LUZ: BZG ma 1C/ALC i 3/BHX,BRS,DUB,LTN,STN;
obecne zera 1A/1B/1D/1E/1F/2/4/5 nie dowodzą takich samych zer dla Lublina.

### Obecne huby — punkt porównania, nie granica audytu

| Wariant | Zapisane IATA |
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

## 3. Mapa plików i kolejność zależności

| Obszar | Pliki / zadanie przy realizacji |
| --- | --- |
| Endpoint | `data/search-airports.json`, `scripts/search_airports.py`: jedenasty kod/strefa i zatwierdzony wyjątek GDN/5B dla KRK oraz LUZ. |
| Bieżące instrukcje | `AGENTS.md`, `docs/FIVE_STEP_FLIGHT_SEARCH.md`, `docs/COLLECTION_RELIABILITY.md`, `README.md`: zakres jedenastu dopiero przy wdrożeniu. |
| Pełne sieci | `scripts/audit_airport_expansion.py`, `scripts/discover_transfer_routes.py`: snapshot, raw intersections, statusy źródeł i decyzje LUZ. |
| Konfiguracja | `scripts/build_gdn_config_patch.py`: jawne `--endpoint LUZ`, review kopii, kontrola nowych hubów i uprawnień. |
| Wizz | `scripts/verify_wizz_expansion_schedules.py`, `scripts/wizz_schedules.py`, `scripts/wizz_api.py`, `data/wizz-route-schedules.json`, lokalne 1A/1B. |
| 1A–1F | Sześć przewoźniczych `*-transfer-airports.json`, `scripts/collect_step1*.py`: trasy, źródła, ceny, kalendarze i linki. |
| 2 | `scripts/collect_step2.py`: pełna macierz jedenastu / TFN/TFS / obu linii / obu kierunków. |
| 3–5 | Trzy allowlisty low-cost i `collect_step3.py`, `collect_step4.py`, `collect_step5.py`: właściwe relacje LUZ i osobne warianty. |
| Ceny/URL | `scripts/booking_urls.py`, `scripts/ryanair_google.py`, `scripts/spanish_resident_fees.py`, `data/spanish-resident-fees.json`. |
| Kompletność | `scripts/collection_coverage.py`, `scripts/collect_five_steps.py`, `scripts/collector_settings.py`: plan jedenastu, jeden run/NBP, limit 2, fail closed. |
| Strona | `app.js`, `index.html`, warunkowo `styles.css`: Lublin, jedenasta opcja, minima/karty/share i cache wersji. |
| Testy | Nowy `tests/test_luz_expansion.py`; istniejące aktualne asercje, zamrożone historie i `tests/test_airport_ui.mjs`. |
| Artefakty | Dziesięć feedów i dziesięć sidecarów; nowy `docs/WDROZENIE_LUBLINA_LUZ.md` z faktycznym odbiorem. |

To mapa przeglądu, nie nakaz edycji każdego modułu. Większość kodu korzysta
już z rejestru. Nie dodawać specjalnego `if airport == 'LUZ'` do każdego kroku.
Porządek: baseline → rejestr → pełny audyt → decyzje → rozkłady Wizz →
konfiguracja/review → testy → pełna kolekcja → odbiór → promocja lokalna.
GitHub dopiero na osobne polecenie.

## 4. Szczególne ryzyka Lublina do rozstrzygnięcia w audycie

### 4.1. Wizz UK i więcej niż jeden przewoźnik na tej samej parze

[Oficjalny rozkład Lublina](https://www.airport.lublin.pl/odloty/), przejrzany
23.10.2026, pokazuje m.in. Luton z kodami W9 oraz FR, Maastricht i Bergamo.
To wskazówki do audytu, nie zatwierdzona lista przesiadek ani kompletna siatka.
Nie powielać założenia BZG o braku Wizza. Nie scalać Ryanair/Wizz na jednej
trasie w jedną taryfę lub jedno zapytanie. Dla Wizza zachować W6/W4/W9,
zweryfikować oba kierunki, różne godziny/sezony oraz ceny regularne i WDC.

LTN ≠ STN, BGY ≠ MXP/LIN, MST ≠ EIN. Sama nazwa Londyn/Mediolan nie wystarcza.
Każde nowe wspólne lotnisko, w tym spoza powyższej tabeli, przechodzi pełną
ścieżkę konfiguracji i kalendarzy. Nawet dwa dostępne odcinki mogą nie dać
żadnego połączenia w przedziale 2–24 h, jak LTN przy ostatnim batchu BZG.

### 4.2. Maastricht i pułapka mieszania sezonów/przewoźników

[Oficjalny rozkład Maastricht](https://www.maa.nl/en/flights/flight-schedule/)
rozdziela sezony 2026/2027; daty sezonowej relacji Lublin różnią się też od
wybranych pozycji październikowego rozkładu Lublina. Port opublikował ponadto
[komunikat o zakończeniu operacji Ryanaira od 26.10.2025](https://www.maa.nl/ryanair-beeindigt-vluchten-vanaf-maa/).
Nie sklejać starej trasy Ryanaira, sezonowego lotu LUZ i oferty Teneryfy
z innego roku lub innej linii. Ustalić aktualny carrier, dokładne IATA,
okres i obie nogi w tym samym oknie. MST jest przykładem kontroli nowego
globalnie huba, **nie potwierdzoną kandydaturą do aktywacji**.

Sprzeczne materiały zachować w raporcie i rozstrzygnąć aktualną siatką
przewoźnika oraz pełnym kalendarzem. Nie wybierać wygodniejszej daty, aby
uzyskać wynik. Nie wprowadzać Transavii/TUI tylko na podstawie ofert portu.

### 4.3. GDN — trwała zgoda użytkownika, nie automatyczne rozszerzenie

Oficjalna tablica Lublina zawiera odcinek do Gdańska. Dlatego w raw
intersections osobno ocenić LUZ ↔ GDN Ryanairem i GDN ↔ Teneryfa Wizzem.
Użytkownik osobno zatwierdził 23.10.2026 trwałe rozszerzenie
`step5_variant_b / GDN / KRK, LUZ`. Zgoda obowiązuje również przyszłe kolekcje.

`candidate_intersection()` filtruje role przed raportem kandydatów. Trzeba
zachować surowy dowód LUZ/GDN, a precyzyjny wyjątek rozszerzyć w rejestrze,
nie przez usunięcie walidatora. Samo dopisanie endpointu nie daje zgody dla
innych polskich hubów, miast lub wariantów.

Po otrzymanej zgodzie zaktualizować precyzyjny
wyjątek rejestru i odpowiedni rekord GDN wariantu 5B, instrukcje, plan zapytań
obu linii/kierunków i testy. Nadal bez GDN w innych wariantach, innych polskich
hubów, samotras lub drugiej przesiadki.
LOT przez WAW i czartery również pozostają poza obecnym zakresem linii.

## 5. Etap A — start wdrożenia i pełne dowody sieci

1. Po osobnym poleceniu ponownie odczytać instrukcje, status/diff, HEAD,
   rejestry i datę. Nie utożsamiać lokalnego `main` z aktualnym `origin/main`.
2. Utworzyć nowy, niekolidujący `tmp/luz-expansion/baseline/`. Skopiować
   konfigurację/opłaty, wspólne i lokalne rozkłady, kod/testy/docs, stronę/CSS
   i wszystkie 20 publicznych plików. Manifest SHA-256, run ID, daty i opis
   zastanych zmian. Nie nadpisywać backupu BZG ani wcześniejszej próby LUZ.
3. Zamrozić wejścia regresji obecnych dziesięciu. Zachować osobno wcześniejsze
   SIX/SEVEN/EIGHT/NINE. Nie używać „bieżący rejestr minus ostatni” jako historii.
4. Wybrać D według Wysp Kanaryjskich i jawnie używać D w całym runie.
   Zarezerwować czas na pełną kolekcję i retry przed zmianą dnia generacji.
   Jeśli zastana baza ma już poprzedni dzień generacji, odnotować jej wiek
   w baseline; nie przepisywać dat ani nie zbierać od nowa dziesięciu tylko
   w celu przygotowania backupu. Celem jest jeden nowy pełny batch jedenastu,
   a stara baza nie otrzymuje poświadczenia świeżości przez samą migrację.
5. Dopisać LUZ do rejestru i zatwierdzonego wyjątku GDN/5B obok KRK. Uruchamiać
   świeże procesy: stałe są ładowane przy imporcie. Obecne `choices=POLISH_AIRPORTS`
   nie przyjmie `--endpoint LUZ` przed tą zmianą; nie obchodzić tego fałszywym
   endpointem BZG ani podmianą identity jego pliku dowodowego.

Poniższe polecenia są **do przyszłego wdrożenia**, z rzeczywistą datą D:

```bash
.venv/bin/python scripts/audit_airport_expansion.py --endpoint LUZ --as-of YYYY-MM-DD --output-directory tmp/luz-expansion
.venv/bin/python scripts/discover_transfer_routes.py --as-of YYYY-MM-DD --snapshot tmp/luz-expansion/network-snapshot.json --report tmp/luz-expansion/discovery-report.json
```

Drugi skrypt pozostaje dry-run, bez `--apply`. Pierwszy pobiera całe sieci
Ryanaira/Wizza i próbuje Bintera dla wszystkich sąsiadów LUZ, nie tylko
dotychczasowych hubów. Wynik dla innych endpointów nie daje zgody na ich
równoczesną migrację. Nie usuwać starych sezonowych tras.

Przy BZG Binter `timetable_get` zwracał GraphQL E01000 mimo HTTP 200,
choć osobna kolekcja cen `booking_search`/imports działała. Ponownie sprawdzić
źródło: `failed` zachować jako błąd, a `--low-cost-only` oznacza `not_checked`.
Taki snapshot nie poświadcza braku tras Bintera. Konieczny niezależny pełny
przegląd oficjalnego katalogu/rozkładów albo jawny blocker. Uzupełnić także
metadane/strefy, jeśli audit przerwał się przed `fill_timezones`.

### Przecięcia i decyzje każdego wariantu

Dla TFN i TFS osobno, przed filtrem starych allowlist, wyliczyć:

| Wariant | Teneryfa ↔ hub | hub ↔ LUZ |
| --- | --- | --- |
| 1A | Binter, kwalifikująca trasa | Ryanair lub Wizz |
| 3 | Ryanair | Ryanair |
| 4 | Wizz | Wizz |
| 5A | Ryanair | Wizz |
| 5B | Wizz | Ryanair |

Role linii są geograficzne i nie zamieniają się po odwróceniu kierunku podróży.
Sprawdzić oba warianty 5 niezależnie od obecności Wizza po stronie Lublina.
Nowe globalnie `NEW`: LUZ–NEW + NEW–TFS ma zostać ocenione, nawet jeśli NEW
nie występowało w aplikacji. To syntetyczny test, nie nazwa realnego huba.

Detektor nie zastępuje osobnego audytu 1B–1F. Każdą pełną właściwą siatkę
bezpośrednich odcinków Teneryfy przeciąć z pełną siecią low-cost LUZ:

| Wariant | Wymagany dowód / ograniczenie |
| --- | --- |
| 1A | Oficjalna siatka Bintera, kwalifikacja rezydenta; także huby spoza obecnej szóstki. |
| 1B | Własne bezpośrednie Iberia/Express; nie zakładać z góry wyłącznie MAD. |
| 1C | Własna strona tras Vuelinga z Teneryfy jako nadrzędne źródło; Aena pomocniczo. |
| 1D | Własna bezpośrednia Air Europa; marketing pary miast nie dowodzi direct. |
| 1E | Oficjalna strona Volotei i MinPrice; bez Google, pusta dynamiczna sekcja nie jest dowodem nieistnienia. |
| 1F | Oficjalne trasy i GraphQL Canaryfly; tylko direct, bez wewnętrznej przesiadki. |

W 1A–1F tylko kwalifikujące się trasy rezydenckie; zagraniczny hub może być
w 3–5 z pełną ceną, nie w rezydenckiej rodzinie 1. Sam kraj ES nie zastępuje
sprawdzenia kwalifikacji konkretnej relacji; zachować wykluczenia, np. FNC.

Utrwalić tabelę/JSON wszystkich decyzji, także `pending`, `rejected`,
`requires_user_decision`: wariant, IATA, TFN/TFS, obie linie, kierunki,
źródła/data/sezon/status, nowy-stary hub, strefa, zniżka/opłaty, brakujące
Wizz schedules, przyczyna i pełny docelowy rekord. Osobno odnotować surowe
przecięcia wykluczone polityką. Nie mylić braku trasy, braku lotów w oknie,
braku wykonalnej przesiadki, braku ceny i awarii źródła.

Brama: dowód → zaakceptowana decyzja → pełny rekord → oba kalendarze
w planie i executorze → complete coverage. Sam komunikat discovery nie kończy audytu.

## 6. Etap B — techniczne rozkłady Wizz, również po stronie Teneryfy

```bash
.venv/bin/python scripts/verify_wizz_expansion_schedules.py --endpoint LUZ --snapshot tmp/luz-expansion/network-snapshot.json --from-date YYYY-MM-DD --days 30 --output tmp/luz-expansion/verified-wizz-schedules.json
```

Publiczny timetable dostarcza daty, odloty i ceny, nie pełne numery/przyloty.
Nowa noga Wizz wymaga zweryfikowanych technicznych danych obu kierunków.
Nie przepisywać godzin LUZ z tablicy jednego dnia do całego kalendarza.

`required_routes()` obejmuje cztery skierowane pary LUZ/TFN/TFS, nogi polskie
4/5A, hiszpańskich sąsiadów Wizza oraz brakujące techniczne nogi Teneryfa–hub
4/5B. Ostatnia funkcja już istnieje — nie planować jej ponownego „naprawiania”.
Porównać wyjście z pełną tabelą decyzji, w tym osobnymi nowymi hubami 1A–1F.
W razie luki rozszerzyć wejście/audyt i test, nie pominąć odcinka.

Wymagania odbioru technicznego:

1. Odczytać pełny oficjalny kalendarz. Każdy aktywny odlot musi rozwiązać
   numer, przylot i czas blokowy przez `scripts.wizz_schedules`, z dowodem
   właściwej reguły sezonowej, dnia tygodnia lub daty.
2. Zachować W6/W4/**W9** i różne zegary. Priorytet resolvera:
   data+godzina > ISO weekday+godzina > godzina > bazowa trasa.
   Sprzecznych obserwacji nie rozstrzygać arbitralnie najczęstszą wartością.
3. `--complete-times` jest obecnie zadeklarowane, ale nie ma osobnej ścieżki
   w `main`. Końcowy check weryfikatora porównuje zegary trasy, nie stanowi
   samodzielnego dowodu pełnego mapowania każdej daty/override'u. Dodać
   niezależne sprawdzenie aktywnych odlotów i konfliktów. Sąsiednia data może
   potwierdzić techniczną regułę, ale nie cenę ani dostępność wyprzedanego dnia.
4. Dopiero kompletne dowody obu kierunków dopuszczają aktywację. Brak pełnego
   numeru, czasu lub rozstrzygnięcia konfliktu to `pending`, nie szablon lotu.
5. `--inactive-probe-date` może sprawdzić opublikowaną trasę sezonową poza
   oknem. Ani jej lot, ani cena spoza okna nie mogą trafić do publicznych feedów.
6. Wspólny `data/wizz-route-schedules.json` i lokalne wpisy 1A/1B muszą być
   zgodne. Nie zgubić starszych override'ów podczas podmiany nowego dowodu.
7. Zachować WRO–LPA, datowe POZ–LTN oraz RZE–FCO: W46068, 140 min o 08:35,
   130 min o 10:45/22:45; FCO–RZE W46067, 135 min. BZG obecnie nie ma
   technicznego wpisu Wizz — nie dorabiać go tylko przy migracji LUZ.
8. Dowody mają identity endpoint/dat/snapshotu. Resume wyłącznie dla tej
   samej identity, bez przemianowania pliku BZG/RZE na LUZ. Bazę API Wizza
   nadal ustala `scripts.wizz_api`, nie wpisywać stałego numeru wersji.

Techniczne Google jest sekwencyjne/ograniczone tak, by łącznie nie przekroczyć
dwóch. Nie prowadzić równolegle technicznego audytu i kilku kolektorów Google.
Nie przenosić cen z rozpoznania technicznego do przyszłego nowego runu cen.

## 7. Etap C — konfiguracja jedenastu i kontrola generatora

### 7.1. Dziewięć allowlist, konkretne pary zamiast kopii BZG

W każdym `scope.polish_airports` dokładnie jedenaście kodów z rejestru,
nawet jeśli dany wariant nie ma kwalifikującej się trasy LUZ.

- 1A/1B: nadal pełne macierze hub × wszystkie endpointy × obie linie
  × oba kierunki. Uzupełnić prawdziwe `eligibility_evidence` / `polish_routes`
  i lokalne schedule, ale nie zawężać executorów do dat drugiej linii.
- 1C–1F: wyłącznie potwierdzone `polish_airport: LUZ` i właściwe `airlines`
  w `polish_routes`. Jeśli działa jedna linia, nie dopisywać automatycznie obu.
- 3/4: LUZ przy właściwych hubach i TFN/TFS. Nowy hub wymaga pełnego rekordu
  oraz `airport_timezones`. Nie nadpisywać starej listy `polish_airports` huba.
- 5: relacje A i B niezależne; wspólny IATA nie przenosi uprawnień między nimi.
- Dodać LUZ do właściwych `excluded_endpoints` 3/4/5. Bez LUZ–LUZ, LUZ jako
  huba. GDN→LUZ jest dozwolone tylko w 5B na podstawie osobnej trwałej zgody.
- Nowy rekord: IATA, nazwa, kraj i IANA timezone, TFN/TFS, polskie lotniska,
  carrier pairs, kwalifikacja/mnożnik i źródła. Nie zgadywać strefy z nazwy kraju.
- Zachować wszystkie wcześniejsze uprawnienia, np. BZG 1C/ALC oraz pięć hubów
  3, RZE/FCO/MXP, i techniczne wyjątki obecnych dziesięciu. Zero w świeżym
  oknie nie usuwa zapisanej sezonowej trasy.

### 7.2. Review helpera, bez ukrytej utraty nowych połączeń

```bash
.venv/bin/python scripts/build_gdn_config_patch.py --endpoint LUZ --snapshot tmp/luz-expansion/network-snapshot.json --schedules tmp/luz-expansion/verified-wizz-schedules.json --from-date YYYY-MM-DD --days 30 --baseline-directory tmp/luz-expansion/baseline/data --output-directory tmp/luz-expansion/configuration-review
```

Historyczna nazwa helpera nie jest endpointem. Wynik to dziesięć dokumentów
review: dziewięć allowlist i wspólny Wizz schedule, nie nowa baza ani bezwarunkowa
zgoda na zastosowanie plików. Obecne ograniczenia sprawdzone w kodzie:

1. Dla **1A–1F helper iteruje po istniejących hubach**. Nowego huba tych rodzin
   nie doda sam. Zaakceptowany nowy hub utworzyć kompletnie albo rozszerzyć
   helper i testy przed kolekcją. Nie ograniczyć audytu do tego, co wygenerował.
2. W istniejącym hubie 3–5 nowe TFN/TFS powoduje
   `Review new Tenerife airports explicitly`. Nie zgubić nowej pary,
   nie powielać IATA ani nie usunąć wyjątku walidacji dla wygody.
3. Pole `tenerife_airports` jest współdzielone z dawnymi endpointami huba.
   Rozszerzenie go może niechcący odblokować nowe relacje starej dziesiątki.
   Wyrazić potrzebną relację per endpoint i objąć nią planner/executor/builder/
   validator, albo uzyskać wyraźną zgodę na szerszą zmianę. Nie rozszerzać innych
   miast po cichu. Porównać stare relacje semantycznie z baseline.
4. Nowe huby 3–5 są już obsługiwane. Zweryfikować pełne rekordy, strefy,
   zniżki i wszystkie potrzebne nogi Wizza, nie dopisywać ich drugi raz ręcznie.
5. Helper zastępuje wspólny wpis i override'y tras objętych nowym materiałem.
   Nie kasować starszych zweryfikowanych dat/tygodni po audycie tylko kilku dni.
   Sprawdzić również wspólne trasy bez LUZ i lokalne kopie w 1A/1B.
6. Regex list IATA jest uogólniony i obejmuje końcówkę `/BZG` — nie wymaga
   kolejnej jednorazowej zamiany. Regex słów kończy się jednak na „dziewięć”.
   Aktualne opisy są zwykle neutralne; gdy wystąpi „wszystkie dziesięć…”,
   znormalizować do „wszystkie polskie lotniska z rejestru endpointów”
   i dodać test. Nie deklarować obsługi słowa „dziesięć” bez sprawdzenia.
7. Powtórne generowanie ma być semantycznie identyczne: bez `/LUZ/LUZ`,
   duplikatów rekordów, carrier pairs, schedule lub override'ów.
8. `verified_on` i `sources.finding` opisać zgodnie z faktycznym audytem LUZ.
   Przestawienie nagłówka nie poświadcza nowych obserwacji dla dawnych tras.
   Nie kopiować liczby „0 obserwacji Wizz” z BZG do Lublina.

Review kończy się porównaniem każdej decyzji z faktycznymi plikami i planem
zapytań. Zastosować tylko zaakceptowane zmiany LUZ i niezbędne, wykazane testami
poprawki. Jeżeli nie było nowego huba, nie ogłaszać naprawy wszystkich
ogólnych ograniczeń helpera. Nie zmieniać konfiguracji podczas pełnego batcha.

## 8. Etap D — ceny, źródła, linki i pełne kalendarze

| Feed | Niezmienna metoda; zakres LUZ do sprawdzenia |
| --- | --- |
| 1A | Wszystkie zapisane Binter route/day obu kierunków, niezależna pełna macierz low-cost, cash fare i końcowe imports. |
| 1B | Każdy dzień Iberii/Express Google HTTP + pełna macierz low-cost, estymata z opłatami, link oficjalny. |
| 1C | Każdy dzień Vuelinga Google HTTP, niezależne pełne zapisane pary/carriers polskiej nogi. |
| 1D | Air Europa tylko Google HTTP, pełne numery UX i daty/godziny oraz własne indywidualne PLN każdego rejsu. |
| 1E | Oficjalny MinPrice Volotei per route/day obu kierunków, cena z opłatami, bez Google i szablonu godzin. |
| 1F | Pełne miesiące Canaryfly obu kierunków, potem szczegóły każdego dostępnego dnia i końcowe imports; bez Google. |
| 2 | Cała macierz LUZ/TFN/TFS, obie linie i kierunki, wszystkie daty; również poprawnie puste rynki. |
| 3 | Pełne kalendarze obu nóg Ryanaira dla wszystkich zaakceptowanych hubów, potem matching. |
| 4 | Pełne kalendarze obu nóg Wizza i kompletne numery/przyloty, potem matching. |
| 5 | Pełne niezależne kalendarze obu przewoźników, oba warianty i kierunki, bez zamiany ról. |

W 1A/1B LUZ zwiększa pełną macierz nawet przy braku potwierdzonego hubu
rezydenckiego dla tego endpointu. W 1C–1F/3–5 tylko właściwe zapisane
relacje, ale zawsze ich pełne okno. Puste daty nie są pomijanymi zapytaniami.

### Końcowe ceny i estymaty

- Ryanair/UK: Google HTTP FR/RK, wszystkie grupy ofert, najniższa własna cena
  każdego rejsu w PLN. Bez przepisania minimum dnia, innych numerów/godzin
  i ceny starego runu. Wspólny świeży persistent cache trasa/dzień dla dziesięciu feedów.
- Air Europa: również wyłącznie indywidualne oferty Google, bez oficjalnego
  promocyjnego feedu lub rozkładu z szablonu jako zastępstwa.
- Binter: `booking_search` wybiera gotówkową taryfę EUR, token wyłącznie
  w pamięci do `booking_getImports`, jeden dorosły, `RC` na uprawnionej trasie.
  Regularna = suma `mainAmount`, rezydent = suma `totalAmount` taryfy, podatków,
  dopłat, opłaty serwisowej i za obsługę. PTS pomijać, poprawnych EUR nie usuwać.
- Canaryfly: oficjalne imports, jeden dorosły, kod `DC`, potwierdzenie statusu
  i wszystkie komponenty. Nie traktować kwoty listy taryf jako końcowej ceny.
  Nie stosować do tych dwóch linii estymatora Aeny.
- Iberia/Express, Vueling, Air Europa, Volotea i uprawnione hiszpańskie nogi
  Teneryfy Ryanair/Wizz w 3–5: `opłaty_PLN + 0.25 × (regularna_PLN − opłaty_PLN)`.
  Jawny szacunek, nie oficjalna cena rezydenta. Polska noga zawsze pełnopłatna.
- Tylko kierunkowe opłaty z `data/spanish-resident-fees.json` przez wspólny
  loader. Obecna ważność 2026-03-01–2026-12-31 musi pokryć **całe** nowe okno,
  także przy D blisko końca roku. Brak/przeterminowanie stawki to blokada,
  nie zgadywanie wartości. Nowy kwalifikujący hiszpański hub potrzebuje dowodów
  opłat obu kierunków; sam polski LUZ nie wymaga dodania opłaty Aeny.
- Jeden dzienny NBP, `tmp/nbp-rates/YYYY-MM-DD.json`, zgodne waluty/kursy
  wszystkich feedów, bez wykorzystania pliku poprzedniej daty jako nowego D.
- Wizz regularne i WDC osobno. Błąd taryfy WDC nie jest upoważnieniem do
  skopiowania regularnej kwoty, utrzymania starej taryfy lub fikcyjnego rabatu.

Każda noga ma `booking_url` z właściwej funkcji `scripts.booking_urls` dla
linii, IATA, jej daty odlotu i pasażerów. Bez kluczy, tokenów, cookies lub
browser-session URL. Air Europa: `residentType=SPANISH_RESIDENT_RC`, usuwany
po wyłączeniu rezydenta; nie `true`. Google jako źródło cen nie zmienia linii
docelowej zakupu. Volotea/Canaryfly: wybór rezydenta w ich flow, bez zmyślonych
parametrów. Wizz/Ryanair/Air Europa linki route/date bez gwarancji preselection.

Nie wykonywać repricingu istniejącej bazy jako substytutu nowej kolekcji LUZ.
Nie poprawiać ręcznie wygenerowanych JSON-ów ani dopisywać im certyfikatów jedenastu.

## 9. Etap E — plan zapytań i znany przyrost macierzy

Plan z `scripts.collection_coverage.expected_queries` musi powstać z pełnych
zapisanych macierzy, nie ze znalezionych lotów. Każda zaakceptowana noga LUZ
lub nowego huba ma oba kierunki i każdą datę zarówno w planie, jak i executorze.

Przy niezmienionych hubach i oknie 31 dat:

| Zakres | Obecne 10 endpointów | Docelowe 11 |
| --- | ---: | ---: |
| 2: skierowane pary na jednego przewoźnika | 40 | 44 |
| 2: pary trasa/przewoźnik obu linii | 80 | 88 |
| 2: route/day | 2480 | 2728 |
| 1A: pełny plan przy obecnych 6 hubach | 8184 | 8928 |
| 1B: pełny plan przy obecnym MAD | 1364 | 1488 |

Krok 2 rośnie o 248 pozycji, czyli 10%. Resztę policzyć po audycie:
nowe huby/TFN/TFS/uprawnienia zmieniają zapytania innych kroków. 1F dodaje
szczegóły po kalendarzach, więc bazowy `expected_queries()` nie jest sam
pełną końcową liczbą tego wariantu. Nie obiecywać liczby ofert LUZ, HTTP
ani czasu pobierania na podstawie tych mnożeń.

Google cap w `scripts.collector_settings` obowiązuje również retry.
Runner sekwencyjny; kilka procesów z osobnymi semaforami nie zapewnia wspólnie
limitu dwóch. Wyliczyć dokładną unię unikalnych route/day Ryanaira dla
nowego batcha i sprawdzić ją względem cache, nie zakładać ponownie 17 360.

Błąd HTTP, GraphQL `errors` przy 200, nieznana struktura, niepełny numer/godzina,
rejs bez ceny lub wadliwe imports oznaczają fail closed. Poprawny pusty dzień
jest dozwolony. Coverage dowodzi ukończenia planu i walidacji znanego formatu,
nie absolutnej gwarancji, że zewnętrzny dostawca nigdy niczego nie pominie.

## 10. Etap F — strona i jedenasty checkbox

W `app.js`: `LUZ: "Lublin (LUZ)"` w `airportLabels`. Etykiety nowych hubów
wyłącznie po audycie. W `index.html` opis lotnisk i nowa wersja JS
`YYYYMMDD-luz-1`; CSS tylko gdy rzeczywiście potrzebny. Nie zmieniać copy,
innych filtrów, ośmiu sortowań ani domyślnych 1000 zł/6 h.

Zachować obecny wielokrotny wybór polskich lotnisk:

- `<details>`/checkboxy po polskiej stronie, pojedynczy select Teneryfy.
  Legacy selecty zachowują dotychczasową kompatybilność.
- `state.polishAirports`: znormalizowany posortowany zbiór, `[]` = wszystkie;
  zaznaczenie całego dostępnego zestawu również normalizuje się do `[]`.
- Opcje z unii endpointów **rzeczywistych** wyników obu kierunków, nie
  automatycznie z rejestru. Pełny, poprawny batch bez LUZ w obu kierunkach
  nie dostaje fikcyjnego checkboxa/oferty. Jeden kierunek z ofertą utrzymuje
  opcję również po odwróceniu kierunku, z uczciwym zerem w drugim.
- LUZ + BZG + KRK to OR, nie trasa między tymi lotniskami. Kierunek zachowuje
  wybór i przenosi go między wylotem/przylotem. X usuwa tylko jedną opcję.
- Reset dat zachowuje lotniska, pełny reset i share zdejmują ich ograniczenie
  według aktualnego mechanizmu. Share oferty ponad 1000 zł podnosi limit dla niej.
- Klucze `fareCalendarRenderKey` i `resultCardsRenderKey` obejmują cały zbiór.
  Zmiana LUZ nie zostawia starych minimów/cache ani starej listy kart.
- Zachować progresywne przygotowanie kart i warstwę
  `.search-panel:has(.airport-multi[open])` ponad kalendarzem.

Testować LUZ samo i OR z dwoma dotychczasowymi lotniskami, oba kierunki,
cztery kombinacje rezydent/WDC, osiem sortowań, zgodne sumy cen/minima,
kliknięcie daty i słupka prowadzące do tego samego ID, szczegóły karty,
share i +1 po północy. Kwoty oraz domyślne liczby ofert podać z nowej bazy,
nie z przykładowego zrzutu lub BZG.

Syntetyczna pełna jedenastka w kolejności IATA:
`BZG, GDN, KRK, KTW, LCJ, LUZ, POZ, RZE, WAW, WMI, WRO`.
Przetestować dolny wiersz, scroll, Gotowe, Wszystkie, focus, Escape i klik
poza popupem na desktop i około 320 px. Nie przebudowywać układu, jeśli
obecny poprawnie mieści opcję; testy logiki nie zastępują odbioru wizualnego.

## 11. Etap G — testy, ze szczególnym uwzględnieniem migracji po BZG

### 11.1. Nowe testy LUZ i zamrożona dziesiątka

Dodać `tests/test_luz_expansion.py`, z literalną historią:

```python
TEN = ("WAW", "WMI", "KTW", "KRK", "GDN", "WRO", "POZ", "LCJ", "RZE", "BZG")
```

Sprawdzić:

- Dokładny rejestr `TEN + ("LUZ",)`, Warsaw i dziewięć dokładnych scope.
  Nadal 10 feedów, 9 allowlist, 8 sortowań i 4 kombinacje zniżek.
- Każde rzeczywiście zatwierdzone uprawnienie LUZ, brak niezamierzonych
  relacji starych miast, brak self-route/nowego endpoint-as-transfer.
- Pełną macierz kroku 2: `len(list(route_matrix())) == 44`, 88 par/linia,
  `88 * 31` pozycji. Nie używać `len(generator)`.
- Mocki **faktycznych executorów**, nie tylko builderów: przy dwóch hubach
  low-cost 44 wywołania na linię zamiast 40, pełne okno obu kierunków mimo
  pustego kalendarza drugiej linii. Każdy nowy hub/noga w niezależnym planie.
- Syntetyczny zupełnie nowy hub NEW dla 3 i 5B, oraz nowe TFN/TFS starego huba:
  discovery → kompletny rekord → planner/executor/coverage, bez zgubienia
  nowej relacji lub poszerzenia wszystkich dawnych endpointów.
- Dla rzeczywistego nowego huba 1A–1F obowiązkowo analogiczny test jego
  kompletnej ścieżki. Sam test, że istniejący MAD przyjmie LUZ, nie testuje
  ograniczenia helpera tworzącego tylko dotychczasowe huby tych rodzin.
- Wizz: oba kierunki, W9 oraz W4/W6, każdy aktywny zegar/datę i resolver,
  priorytety override, pending bez wymyślonego numeru, zachowane stare wyjątki.
- Raw LUZ/GDN ma osobną trwałą zgodę. GDN/5B/KRK i GDN/5B/LUZ przechodzą;
  inne warianty/miasta i LUZ/LUZ są odrzucane. Testować wszystkie granice wyjątku.
- Własne ceny rejsów Ryanair/Air Europa, FR/RK i wszystkie grupy ofert,
  cap/retry, wspólny NBP, oficjalne imports, opłaty, URL i WDC bez fallbacku.

Na identycznych zamrożonych wejściach TEN porównać przed/po wszystkie dziesięć
builderów, oba kierunki, oba warianty 5, kolejność/ID/ceny/linki i liczbę
starych wyników. Mechanizm rodziny bez realnej LUZ trasy sprawdzić
syntetycznie (np. MAD), ale nie wpisywać takiego lotu do publicznego feedu.

### 11.2. Konkretne bieżące asercje do aktualizacji

Przejrzeć `test_airport_expansion.py`, `test_wro_expansion.py`,
`test_poz_expansion.py`, `test_lcj_expansion.py`, `test_rze_expansion.py`,
**`test_bzg_expansion.py`**, `test_step2_collector.py`, `test_source_completeness.py`
oraz batch/source/Wizz/price tests. Aktualne asercje zmienić 10→11, 40→44,
80→88 **wyłącznie tam, gdzie opisują bieżące endpointy/macierz**.

Konkretne pułapki sprawdzone w obecnym kodzie:

1. BZG ma `POLISH_AIRPORTS == NINE + ("BZG",)`, bieżące 40/80 i executor 40.
   Te asercje mają objąć LUZ. Jego regresje `NINE + ("BZG",)` pozostają jednak
   historyczną dziesiątką; nie dopisywać LUZ do tamtych zamrożonych wejść.
2. Coverage test BZG „old-nine” usuwa z aktualnego planu tylko BZG. Po LUZ
   odziedziczyłby LUZ i nie byłby dziewiątką. Zamrozić do literalnego NINE
   (origin/destination polski z tego zbioru) albo rozdzielić intencje historyczną
   i „bieżąca macierz bez BZG”. Zachować odrzucanie obu niepełnych certyfikatów.
3. RZE „old-eight” obecnie wyklucza RZE i BZG. Po LUZ również odziedziczyłby
   nowy endpoint. Preferować pozytywne ograniczenie do EIGHT, nie rosnącą
   w każdym wdrożeniu listę wykluczeń. Pierwotne fixture EIGHT pozostaje sobą.
4. JS **„ninth RZE checkbox…”** wyklucza RZE/BZG, a **„tenth BZG checkbox…”**
   tylko BZG przed dodaniem syntetycznej próbki. Na świeżej bazie LUZ oba
   odziedziczą LUZ i złamią oczekiwanie 9/10. Zamrozić je do odpowiednich
   historycznych zbiorów, pozostawić liczbę checkboxów 9/10 i dodać osobny 11.
5. „all available endpoints…” już wyprowadza pierwszą etykietę przez
   `optionLabel(available[0])`. Nie powtarzać starej naprawy stałego GDN;
   zachować dynamiczny test i sprawdzić dostępność LUZ w obu kierunkach.
6. `test_source_completeness.py` ma metodę `all_eighty_route_carrier_pairs`
   i oczekiwanie 80. Zmienić aktualną macierz i nazwę na 88, nie przerabiać
   niezwiązanych cen/liczb w fixture.
7. SIX/SEVEN/EIGHT/NINE i wcześniejsze builders LCJ/POZ są już zamrożone.
   Nie odtwarzać błędów `direct[:-1]` ani odejmowania ostatniego endpointu.
   Historyczne 10 wynikowych plików helpera również pozostaje liczbą 10.
8. `refresh_endpoint_text`: stara lista kończąca się BZG, docelowa z LUZ,
   słowo „dziesięć”, neutralny opis i drugie uruchomienie muszą być idempotentne.

Nie robić globalnego replace `10 → 11`. Część dziesiątek dotyczy feedów,
część historycznej bazy, a nie docelowej liczby polskich portów.

### 11.3. Granice, kompletność i interakcje strony

- 119/1441 min odrzucone, 120/1440 przyjęte; także 115 min nadal odrzucone.
  Inny IATA, przerwana/odwrotna chronologia, self-route lub dwa transfery: błąd.
- Start/koniec okna, obie daty odlotu, +1 przylotu, DST i lokalne/UTC czasy.
- Stary certyfikat dziesięciu nie certyfikuje jedenastu. Brak wszystkich
  8 rynków LUZ jednego dnia, pojedynczego route/day, nowego huba albo
  szczegółów 1F musi blokować publikację, nie być testem „zero lotów”.
- Mieszane run ID/okna/kursy, sidecar niezgodny z feedem, uszkodzony format,
  wadliwe imports, przeterminowane opłaty lub zmieniony hash przy resume: fail closed.
- JS: jedenasty checkbox i OR LUZ+BZG+KRK, wszystkie kierunki/tryby cen/
  sorty, chipy, resety, cache, minima/kwoty kalendarza i wykresu, to samo ID
  karty, share z odtworzeniem ustawień i share ponad 1000 zł, indeks +1.
- Osobne fixture: zero LUZ, tylko jeden kierunek, pełna jedenastka. Żadnej
  wymyślonej oferty/checkboxa, gdy rzeczywisty komplet nie ma lotu LUZ.

Przed kolekcją, a następnie odpowiednie kontrole po promocji:

```bash
.venv/bin/python -m unittest discover -s tests -p 'test_*.py'
node --test tests/test_airport_ui.mjs
node --check app.js
git diff --check
```

Baseline 220/34 nie jest obiecaną liczbą po zmianie: wynik faktycznie zmierzyć.
Test danych LUZ może być jawnie pominięty przed nową kolekcją, ale musi zostać
ponowiony na stagingu. Gdy kompletny batch faktycznie da zero LUZ, podać
to wprost wraz z powodem i testami syntetycznymi, nie nazywać skipa odbiorem
rzeczywistej ścieżki. Nie usuwać testu w celu uzyskania zielonego wyniku.

## 12. Etap H — jeden nowy pełny batch, bez doklejania LUZ

Po zakończonym audycie, konfiguracji, weryfikacji Wizz i testach zebrać
**wszystkie dziesięć feedów dla jedenastu endpointów**, nie tylko nowe loty LUZ.
Wyłącznie nowy, niekolidujący staging i run/cache, bez cen/obserwacji z runu BZG.

```bash
.venv/bin/python scripts/collect_five_steps.py --from-date YYYY-MM-DD --days 30 --stage-directory tmp/luz-expansion/batch-YYYY-MM-DD-RUN --workers 2
```

`RUN` to etykieta katalogu, właściwy UUID generuje runner. Kolejność pozostaje
`1, 1b, 1c, 1d, 1e, 1f, 2, 3, 4, 5`, sekwencyjnie. Początkowe dwa workery
ograniczają również obciążenie oficjalnego Wizza: ostatni batch BZG wymagał
ponowienia WDC WAW–RAK po 503 i zakończył ten krok z `--workers 2`.
Nie jest to gwarancja braku błędów źródła. Większe `--workers` nigdy nie
podnosi Google cap 2; nie uruchamiać równoległych probe'ów Google.

Zamrozić konfigurację przed startem; metadata cache zapisuje daty/run/hash
rejestru, Wizz schedules, opłat i allowlist. Nie podmieniać parsera lub
normalizacji danych w trakcie jednego batcha. Konieczna zmiana wpływająca
na cache/wyniki wymaga nowego spójnego przebiegu, nie omijania identity.

### Przerwanie, retry i dzień generacji

Publiczne 20 plików pozostają poprzednie do promocji. Nie uruchamiać
pojedynczego kolektora z domyślnym outputem `data/` jako próby: przy błędzie
może zmienić publiczny sidecar na failed obok starego feedu. Wszystko do stagingu.

Przed wznowieniem zachować osobne kopie nieudanego `stepX.log`,
`validation-report.json` i `stepX-results.collection-report.json` z failed.
Runner przy retry nadpisuje te ścieżki. Nie oczekiwać osobnego `.failed.json`.
Nie kasować poprawnego cache; sam wzrost jego licznika nie jest jednak
certyfikatem całej kolekcji. Nie uruchamiać drugiego procesu na tym samym cache.

Po błędzie 1C wznowić tylko 1C i niewykonane późniejsze kroki:

```bash
.venv/bin/python scripts/collect_five_steps.py --from-date YYYY-MM-DD --days 30 --stage-directory tmp/luz-expansion/batch-YYYY-MM-DD-RUN --workers 2 --run-id UUID_Z_PIERWOTNEGO_RAPORTU --refresh-steps 1c 1d 1e 1f 2 3 4 5
```

Po błędzie 3: `--refresh-steps 3 4 5`. Po błędzie ostatniego kroku tylko:

```bash
.venv/bin/python scripts/collect_five_steps.py --from-date YYYY-MM-DD --days 30 --stage-directory tmp/luz-expansion/batch-YYYY-MM-DD-RUN --workers 2 --run-id UUID_Z_PIERWOTNEGO_RAPORTU --refresh-steps 5
```

To te same daty, run ID i hash, bez restartowania udanych 1A/1B itd.
Nieznany payload Google lub HTTP 503 Wizza nie staje się pustym dniem,
brakiem WDC ani upoważnieniem do innego źródła. Usuwać przyczynę, nie walidację.

Zmiana konfiguracji/dat wymaga nowego runu/stagingu/cache. Bieżący validator
wymaga też dnia generacji zgodnego z dniem odbioru w `Atlantic/Canary`.
Wielogodzinny przebieg przekraczający północ wymaga jawnego rozstrzygnięcia,
zwykle nowego pełnego batcha dla nowego D; nie przepisywać timestampów,
kursów lub run ID na starych wynikach. Ustalić to przed późnym startem.

## 13. Etap I — odbiór całej bazy i rzeczywistej strony

```bash
.venv/bin/python scripts/collect_five_steps.py --from-date YYYY-MM-DD --days 30 --stage-directory tmp/luz-expansion/batch-YYYY-MM-DD-RUN --validate-only
RESIFLY_TEST_DATA_DIRECTORY=tmp/luz-expansion/batch-YYYY-MM-DD-RUN node --test tests/test_airport_ui.mjs
```

Walidacja nie jest ponownym pobraniem. **Przed pierwszym `--validate-only`
zachować kopię oryginalnego kompletnego `validation-report.json` jako
`collection-complete-report.json`**: walidacja nadpisuje raport runnera i może
nie zachować hasha/ścieżki cache z pierwotnej kolekcji. Metadata i logi zachować.

Odebrać i zapisać dowody:

1. Dziesięć feedów schema 2 i dziesięć zgodnych sidecarów; jeden run, okres,
   dzień generacji, zestaw kursów, zgodna konfiguracja/cache identity.
2. Complete coverage jedenastu, zero missing/unexpected, wszystkie nowe
   huby/nogi LUZ, szczegóły Canaryfly zgodne z miesięcznymi kalendarzami.
3. Tabele feedów, endpointów, kierunków, wariantów 5 i nowych hubów.
   Jawne zera z powodem. Oddzielnie liczba wszystkich LUZ oraz widocznych
   przy 1000 zł/6 h, żeby filtrowania nie mylić z brakującą bazą.
4. Chronologia, ten sam IATA, 120–1440 min, obie nogi odlotów w oknie,
   pełne numery/godziny, osobne ceny/WDC/estymaty/imports, sumy i unikalne ID.
5. Dokładna równość planowanej unii route/day Ryanaira i cache: unikalne
   klucze, `status=ok`, `google_flights_http`, bez starszych/dodatkowych rekordów.
6. Wszystkie URL deterministyczne per noga, poprawna trasa/data/pasażerowie,
   usuwanie/dodawanie residentType UX przez filtr, brak secrets/session.
7. Realne próbki LUZ obu kierunków i każdej aktywnej rodziny, również +1
   oraz rozbicie cen. Zamrożona regresja sprawdza mechanizm; zmiana ceny
   w nowym pobraniu sama nie dowodzi błędu kolektora.
8. Publiczne 20 plików nadal identyczne z baseline przed promocją, bez częściowej
   podmiany. Zachować raport tej kontroli jako pre-promotion acceptance.

Browser QA na izolowanej statycznej kopii ze stagingiem albo po bezpiecznej
promocji lokalnej. Nie zmieniać produkcyjnych ścieżek feedów dla testu
i nie podmieniać części `data/` obok starych plików.

Desktop i około 320 px: jedenasta opcja (jeżeli są oferty), ostatni wiersz/
scroll menu, LUZ+BZG+KRK, kierunek, ceny/kwoty/minima, klik daty i słupka
w tę samą kartę, szczegóły, +1, wszystkie resety, share i konsola.
Sprawdzić systemowy schowek i ponowne otwarcie skopiowanego linku,
parametry zakupu bez dokonywania rezerwacji/płatności.

Przy BZG sterowanie przeglądarką było wyłączone w Work. Podczas LUZ sprawdzić
to ponownie, bez założenia, że blokada zniknęła. Nie obchodzić wyłączonego
sterowania inną metodą. Brak dostępu oznacza jawnie otwartą kontrolę wizualną/
schowka, nie zaliczenie jej testami Node lub HTTP.

## 14. Etap J — lokalna promocja, HTTP i spójny rollback

Po odbiorze danych i testów, w zakresie nowego polecenia wdrożenia:

```bash
.venv/bin/python scripts/collect_five_steps.py --from-date YYYY-MM-DD --days 30 --stage-directory tmp/luz-expansion/batch-YYYY-MM-DD-RUN --validate-only --promote
```

Runner ponownie waliduje całość, przygotowuje wszystkie 20 plików i zachowuje
poprzednie w `previous-public-feeds/` z manifestem. Obsłużony błąd podmiany
przywraca poprzednie pliki; 20 rename'ów nie jest pojedynczą transakcją
odporną na nagłe zabicie procesu/utratę zasilania. Nie usuwać niezależnego baseline.

Po promocji:

- bajtowo publiczne 20 = staging, backup 20 = baseline;
- ponowne `validate_batch` na publicznych danych i testy Python/JS;
- HTTP 200 i aktualne bajty `index.html`, `app.js` i wszystkich 20 JSON-ów,
  nowa wersja JS i run ID, nie tylko strona tytułowa/parametr `?build=`;
- `git diff --check`, składnia JS i Python, końcowy status związanych zmian.

Serwer uruchamiać z katalogu projektu; nie z katalogu domowego i nie dublować
już działającego procesu na porcie 8000. Gdy potrzebne uruchomienie:

```bash
cd "/Users/piotr/Documents/iCloud Developer/ResiFly"
.venv/bin/python -m http.server 8000 --bind 127.0.0.1
```

Podgląd: `http://127.0.0.1:8000/?build=luz-local-YYYYMMDD`.
Sprawdzić, że serwer rzeczywiście podaje ten checkout. `loadFlights()` już
używa `cache: "no-store"`; nie usuwać tego zabezpieczenia ani nie traktować
samego nowego query parametru jako dowodu nowej bazy.

Rollback wymaga spójnego przywrócenia kodu, rejestrów i 20 plików sprzed LUZ,
z zachowaniem zastanych niezwiązanych zmian. Same feedy dziesięciu pod
konfiguracją jedenastu to nie rollback. Bez `git reset --hard`, globalnego
odrzucania plików, nadpisywania użytkownika lub kasowania całego workspace.
Nie wykonywać wycofania prewencyjnie po poprawnej promocji.

Utworzyć `docs/WDROZENIE_LUBLINA_LUZ.md`: data/HEAD/baseline, prawdziwe źródła
i statusy audytu, pełne decyzje wszystkich wariantów i raw GDN, nowe huby/
TFN/TFS, sezonowość/odrzucone/pending, schedule/override/opłaty, run/okno/
NBP/hash/cache, tabele wyników i coverage, próbki/URL, błędy i ponowienia,
testy/HTTP/wizualne ograniczenia, promocja/backup/rollback i rzeczywisty stan Git.
Bieżące instrukcje do jedenastu uaktualnić dopiero wtedy. Nie przepisywać
historycznych planów/wyników GDN/WRO/POZ/LCJ/RZE/BZG na jedenaście.

## 15. Etap K — GitHub i przyszła automatyzacja tylko osobno

Pierwsze wdrożenie domyślnie lokalne. Osobno przedstawić wynik i czekać
na zgodę publikacji. Dotychczasowy push BZG nie upoważnia do push LUZ.
Po nowym poleceniu: status/diff, testy i zdalny HEAD, jawne staging tylko
powiązanych plików, commit i zwykły push do uzgodnionej gałęzi, bez force.

Pakiet publikacji: konfiguracja, konieczny kod/testy, dokumentacja i wszystkie
dziesięć feedów/sidecarów z nowego wspólnego runu. Bez `tmp/`, cache, logów,
backupów, kluczy i sesji. Sam wpis LUZ bez spójnej bazy nie kończy wdrożenia.

Nie dodawać workflow pobierania cen w tym zadaniu. Przyszłe Actions użyją
tego samego rejestru, requirements i runnera, pięciu kroków, sekwencyjnych
kolektorów, cache NBP/Ryanaira i tych samych bramek. Discovery osobno od
zwykłego odświeżania, najpierw dry-run i artefakt/review. Nie równoleglić jobów
Google tak, by sumarycznie przekroczyły 2. Sam push strony nie jest dowodem
gotowego automatycznego codziennego odświeżania.

## 16. Checklista realizacji — obecnie niewykonana

- [ ] Nowe polecenie wdrożenia, aktualne instrukcje/status i pełny baseline.
- [ ] Jedenasty LUZ, dziewięć scope i trwała polityka GDN — wyłącznie 5B/KRK,LUZ.
- [ ] Pełne świeże sieci LUZ, także zupełnie nowe globalne huby i TFN/TFS.
- [ ] Audyt 1A–1F, 2, 3, 4, 5A/5B; tabela ready/pending/rejected/polityka.
- [ ] Wyjaśnione Wizz UK, wspólny LTN dwóch linii, sezony MST i raw GDN.
- [ ] Wszystkie nowe huby przechodzą do pełnych rekordów/plannerów/executorów, bez luk helpera.
- [ ] Zweryfikowane oba kierunki nowych nóg Wizz i aktywne godziny/override'y.
- [ ] Stare uprawnienia/strefy/schedule zachowane; generator idempotentny.
- [ ] Aktualne ceny źródłowe, końcowe imports, opłaty ważne w całym oknie, trwałe URL.
- [ ] Asercje 44/88 i historyczne fixture RZE/BZG zamrożone bez LUZ.
- [ ] Nowe testy LUZ, frozen TEN i stare SIX/SEVEN/EIGHT/NINE bez regresji.
- [ ] Jedenasty multiselect, OR, oba kierunki, cztery ceny, sorty, minima/karty/share/+1.
- [ ] Wszystkie dziesięć nowych feedów: jeden run/D/NBP/hash, Google max 2.
- [ ] Complete 10 feedów/10 sidecarów, zero missing/unexpected; cache równy planowi.
- [ ] Próbki i liczby LUZ obu kierunków/każdej aktywnej rodziny, jawne zera i liczby domyślne.
- [ ] Testy na nowym stagingu, HTTP, wizualny odbiór/schowek albo jawne ograniczenie.
- [ ] Lokalna promocja wszystkich 20, kopie i porównania bajtowe, raport/rollback.
- [ ] Bez commita/push/workflow do osobnego polecenia publikacji.

## 17. Gotowy brief dla wykonawcy

Wdróż LUZ na podstawie tego planu i bieżących instrukcji projektu, dopiero
po wyraźnym zleceniu. Najpierw audyt pełnych sieci i nowych przesiadek, potem
kompletna konfiguracja/techniczne schedule i testy. Zachowaj dotychczasową
dziesiątkę, pięć kroków, źródła cen, limit Google 2, pełne niezależne kalendarze,
granice 120–1440 i precyzyjny wyjątek GDN/5B tylko dla KRK i LUZ zgodnie
z trwałą decyzją użytkownika. Nie kopiuj uprawnień BZG
i nie ograniczaj nowych hubów do starych plików. Zbierz wszystkie dziesięć
feedów od nowa do nowego stagingu/runu, obsłuż retry bez restartowania udanych
kroków i bez mieszania starej bazy. Po pełnym odbiorze podmień cały zestaw
lokalnie z backupem i udokumentuj rzeczywiste wyniki/ograniczenia.
Nie wysyłaj niczego na GitHub bez kolejnego osobnego polecenia.
