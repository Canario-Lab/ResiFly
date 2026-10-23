# Plan dodania Wrocławia (WRO) jako szóstego polskiego lotniska ResiFly

Dokument wykonawczy dla Codexa. Przygotowany **23 października 2026 r.** na
podstawie repozytorium w stanie `ac15154cfb6a55c3b54f0d51528e55864cfd4737`.
Przed wdrożeniem ponownie sprawdzić HEAD, instrukcje i konfigurację, ponieważ
numery linii, siatka i ceny mogą się zmienić. Wskazane niżej nazwy funkcji są
punktami nawigacyjnymi, nie instrukcją zastępowania plików historyczną wersją.

**Status wykonania: wdrożono lokalnie 2026-10-23; odbiór wizualny pozostaje otwarty.**
Aktualny postęp i dowody znajdują się w
[raporcie wdrożenia](WDROZENIE_WROCLAWIA_WRO.md). Poniższy plan zachowuje
punkt wyjścia sprzed zmian. Samo przygotowanie planu nie obejmowało
pobierania cen ani potwierdzania nowych tras; weryfikację wykonuje się
podczas wdrożenia i dokumentuje oddzielnie w raporcie.

Ten plan aktualizuje procedurę rozszerzania endpointów po wdrożeniu Gdańska.
Nie należy mechanicznie zamieniać `GDN` na `WRO` w poprzednim planie: wspólny
rejestr, loader Wizz i raporty kompletności już istnieją, a zasady cen oraz
źródła Ryanaira, Bintera i Canaryfly zostały od tamtego czasu poprawione.

## 1. Cel i niezmienne zasady

Docelowa kolejność polskich endpointów:
**WAW, WMI, KTW, KRK, GDN, WRO**. Nowy wpis to Wrocław, `Europe/Warsaw`.
Wspólnym źródłem pozostaje `data/search-airports.json`, odczytywany przez
`scripts.search_airports`; nie tworzyć drugiej listy w kodzie.

Wdrożenie ma obejmować WRO → TFN/TFS oraz TFN/TFS → WRO: loty bezpośrednie
i wszystkie zweryfikowane połączenia z jedną przesiadką zgodne z obecnymi
krokami. Nadal jest dokładnie **pięć kroków głównych**, sześć wariantów 1A–1F
i **dziesięć publicznych feedów**. Nie dodawać kroku 6 ani feedu samego WRO.

Zachować następujące reguły:

- Pełne niezależne kalendarze każdej zapisanej trasy i linii, w obu kierunkach,
  przed dopasowaniem odcinków. Dni lotów jednej linii nie wyznaczają zapytań
  do drugiej. Wyjątek techniczny Canaryfly pozostaje opisany w sekcji źródeł:
  najpierw pełne kalendarze miesięczne, potem szczegóły dostępnych dni.
- Obecne `--days 30` oznacza przedział domknięty: dzień startu i następne
  30 dni, łącznie **31 dat**. Nie zmieniać tej semantyki przy dodawaniu WRO.
- Maksymalnie jedna przesiadka, 120–1440 minut oczekiwania, prawidłowe strefy
  i chronologia. Każdy odcinek musi sam mieścić się w skonfigurowanym oknie.
- Zbierać wszystkie ceny. Filtr maksymalnej ceny działa na stronie.
  Zachować osobno ceny regularne, rezydenckie i WIZZ Discount Club.
- Domyślny widok strony: **Polska → Teneryfa**, maksymalnie **1000 zł**,
  przesiadka do **6 h**, sortowanie po najbliższym terminie. Wyczyść filtry
  przywraca te ustawienia; udostępniony lot nadal odtwarza swój kierunek.
- Jeden dzienny snapshot NBP dla całej kolekcji; Google Flights maksymalnie
  dwa równoległe zapytania łącznie, także podczas retry i weryfikacji rozkładów.
- Oficjalne końcowe ceny Bintera i Canaryfly oraz wspólna reguła opłat dla
  szacunków pozostałych linii pozostają obowiązkowe.
- Zachować identyfikatory i zachowanie obecnych pięciu endpointów na tych
  samych wejściach. Nowe pobranie może dać inne ceny i liczbę wyników.
- Trwałe linki zakupu na każdym odcinku, bez cookies, tokenów i URL-i sesji.
- Najpierw pełny staging z dowodami pokrycia, potem lokalna podmiana całego
  zestawu. Publikację Git wykonać według polecenia użytkownika na etapie
  realizacji; przygotowanie niniejszego planu jej nie obejmuje.

## 2. Punkt wyjścia potwierdzony w aktualnych plikach

| Obszar | Stan obecny i konsekwencja dla WRO |
| --- | --- |
| Endpointy | `data/search-airports.json` ma WAW/WMI/KTW/KRK/GDN, bez WRO. Wszystkie dziewięć allowlist ma ten sam scope. |
| WRO w konfiguracji | Brak wpisów WRO w endpointach, dziewięciu allowlistach i rejestrze Wizz; brak etykiety WRO w `app.js`. W publicznych feedach nie ma WRO. |
| Rejestr i strefy | `scripts/search_airports.py` ładuje listy przy imporcie i sprawdza kody, duplikaty oraz strefy. Kolektory i detektor importują wspólne stałe. Po zmianie danych uruchomić nowe procesy. |
| GDN jako transfer | Jawny wyjątek `step5_variant_b / GDN / KRK`; nie obejmuje WRO ani innych kroków. WRO nie ma obecnie roli transferu do zachowania. |
| 1A/1B | Wspólne `collect_step1.collect_low_cost_legs()` sprawdza iloczyn hubów, wszystkich endpointów, dwóch kierunków i obu linii. `eligibility_evidence` dokumentuje siatkę, ale nie ogranicza pobierania. |
| 1C–1F | Pobieranie low-cost wynika z `polish_routes[].polish_airport` i `airlines`. Samo dopisanie WRO do scope nie uruchomi tych tras. 1D–1F używają wykonawcy low-cost importowanego z 1C. |
| Krok 2 | `route_matrix()` korzysta z rejestru: obecnie 20 skierowanych par na linię, 40 kombinacji trasa–linia. |
| Kroki 3–5 | Zapytania wyznaczają `polish_airports` przy konkretnych hubach/variantach. Scope jest metadanymi, nie zastępstwem tych list. |
| Wizz | `scripts/wizz_schedules.py` już istnieje. Krok 2 czyta wspólny JSON; 1A/1B mają lokalne dane; 1C–1F oraz 4/5 używają danych wspólnych i 1A. Obsługiwane są wyjątki numeru i czasu blokowego po godzinie odlotu. |
| Ryanair | Aktywny kolektor korzysta z `scripts/ryanair_google.py`, `FR` i `RK`. `ryanair_client_version()` jest znacznikiem zgodności `google-flights-http`; dawne funkcje API w pliku nie są aktualnym źródłem. |
| Pokrycie | `scripts.collection_coverage.expected_queries()` buduje plan z macierzy, przed pobieraniem. Feed i osobny sidecar muszą zawierać ten sam kompletny raport i wspólny `run_id`. |
| Runner | `scripts/collect_five_steps.py` zbiera kolejno dziesięć feedów i waliduje całość. Raport ma jeszcze pola `gdn_*`; promocja obecnie kopiuje wyłącznie feedy, bez sidecarów. |
| Cache Ryanaira | Domyślna ścieżka zależy od zakresu dat, a nie `run_id`; sam nowy `run_id` nie gwarantuje świeżych odczytów przy powtórzeniu tego samego okna. Jest obsługiwane nadpisanie `RESIFLY_RYANAIR_GOOGLE_CACHE`. |
| Narzędzia GDN | `verify_wizz_expansion_schedules.py` i `build_gdn_config_patch.py` mają GDN wpisane na stałe. Nie można ich uruchomić dla WRO bez adaptacji. |
| UI | Opcje lotnisk powstają dynamicznie z wyników. Lista w oknie informacyjnym w `index.html` jest tekstem z pięcioma endpointami. |
| Automatyzacja | W badanym stanie nie ma `.github/workflows`. Dodanie WRO nie wymaga tworzenia GitHub Actions. |

Obecne dziesięć feedów ma okno **2026-10-22–2026-11-21**, łącznie
**11 654 propozycje** i osadzony `run_id`
`3451bb82-354a-4785-9f0a-fcc676625f47`. To stan zastanej bazy, nie oczekiwana
liczba po wdrożeniu ani dowód świeżości dzisiejszych cen. Przy audycie w `data/`
nie było oddzielnych plików `step*-results.collection-report.json`.

| Feed | Liczba zastanych propozycji |
| --- | ---: |
| 1A | 2057 |
| 1B | 1996 |
| 1C | 2208 |
| 1D | 787 |
| 1E | 6 |
| 1F | 164 |
| 2 | 199 |
| 3 | 3421 |
| 4 | 172 |
| 5 | 644 |

Dokumenty Gdańska i część opisów README zawierają wcześniejsze stany źródeł
oraz liczebności. Przy sprzeczności stosować aktualne `AGENTS.md`,
`FIVE_STEP_FLIGHT_SEARCH.md`, `COLLECTION_RELIABILITY.md` i bieżący kod.
Nie odtwarzać dawnych fallbacków Ryanaira ani cen netto.

## 3. Etap 0 — zabezpieczyć punkt odniesienia

1. Przeczytać aktualne instrukcje projektu i obie instrukcje kolekcji wskazane
   wyżej. Sprawdzić status, HEAD i ewentualne nakładające się zmiany użytkownika.
2. Pracować lokalnie na gałęzi `codex/add-wroclaw-wro`, jeżeli użytkownik nie
   wskaże innego sposobu. Zachować niezwiązane pliki i zmiany.
3. Utrwalić konfigurację, kod, dziesięć feedów i istniejące sidecary przed
   zmianą. Zapisać też informację o braku sidecara, zamiast go dorabiać.
4. Materiały robocze i raporty umieszczać w `tmp/wro-expansion/`, poza `data/`.
   Przygotować raport baseline: endpointy, huby, pary linia/trasa, okres,
   kursy, źródła, pokrycie, liczby wyników per endpoint/kierunek/wariant.
5. Uruchomić bazowe testy offline. Przygotować niezmienne wejścia do porównania
   istniejącej piątki przed i po rozszerzeniu. Nie porównywać dwóch pobrań
   bieżących cen jako dowodu regresji algorytmu.

Warunek zakończenia: da się odtworzyć poprzedni stan bez destrukcyjnego resetu
i wiadomo, które pliki zostały zmienione w ramach wdrożenia WRO.

## 4. Etap 1 — rozszerzyć wspólny rejestr i zachować politykę transferów

1. W `data/search-airports.json.polish_airports` dopisać po GDN:

   ```json
   { "iata": "WRO", "name_pl": "Wrocław", "timezone": "Europe/Warsaw" }
   ```

2. Korzystać z obecnego `scripts.search_airports`, bez nowej stałej sześciu
   kodów w kolektorach i detektorze. TFN/TFS zachować bez zmiany.
3. Zsynchronizować `scope.polish_airports` wszystkich dziewięciu allowlist
   z rejestrem. Zweryfikować jawnie oczekiwaną szóstkę i unikalność kodów.
4. Zachować dokładnie istniejący wyjątek GDN/5B/KRK. Nie dopisywać WRO do
   `endpoint_transfer_exceptions`, nie rozszerzać wyjątku GDN o WRO.
5. `WRO → hub → TFS/TFN` jest nową rolą endpointu. `KRK → GDN → TFS`
   pozostaje dozwolone. `WRO → GDN → TFS` nie jest automatycznie dozwolone
   przez dotychczasowy wyjątek. Ewentualną propozycję rozszerzenia tej roli
   wypisać poza zakresem migracji.
6. Odrzucać WRO–WRO, transfer równy początkowi/końcowi podróży oraz inne
   niezatwierdzone polskie endpointy używane jako huby.
7. Uaktualnić opisy `excluded_endpoints` zgodnie z polityką danego wariantu.
   W 3/4 WRO jest wykluczone jako transfer. W 5 zachować opis wyjątku GDN;
   nie stosować masowego dopisywania/wykluczania bez uwzględnienia wyjątku.

Warunek zakończenia: świeżo uruchomiony każdy kolektor, detektor i planner
pokrycia widzi identyczne sześć endpointów oraz strefę WRO.

## 5. Etap 2 — zweryfikować całą siatkę otwieraną przez WRO

To jednorazowy audyt rozszerzenia konfiguracji. Późniejsze kolekcje cen
nadal działają tylko na zapisanych, zatwierdzonych listach.

1. Zebrać aktualne oficjalne siatki Ryanaira i Wizz Aira do/z WRO. Zapisać
   snapshot, datę sprawdzenia, dokładne kody lotnisk i przewoźników.
   Źródło siatki Ryanaira może być oficjalne, mimo że ceny pobiera Google.
2. Dla lotów bezpośrednich sprawdzić WRO ↔ TFN oraz WRO ↔ TFS u obu linii.
   Macierz ma je badać także wtedy, gdy nie ma opublikowanego rynku.
3. Dla każdego wariantu przesiadkowego przeciąć siatkę WRO z bezpośrednią
   siatką właściwego przewoźnika na odcinku Teneryfy. Rozpatrzyć istniejące
   huby, całkiem nowe huby i pozycje odrzucone dotąd tylko z powodu braku
   dalszego odcinka do któregoś z pięciu endpointów.
4. Nie kopiować listy hubów ani linii z Gdańska. Potwierdzenie Ryanaira na
   WRO–hub nie potwierdza Wizz Aira na tej samej parze i odwrotnie.
5. Dla 1B–1F przeprowadzić osobny audyt oficjalnych tras. Detektor obejmuje
   tylko 1A, 3, 4 i 5; jego raport nie poświadcza pozostałych wariantów.
6. Ponownie sprawdzić powody wykluczeń: Vueling OVD/GRX, Volotea OVD,
   Canaryfly ACE/SPC/VDE oraz wszystkie inne kwalifikujące się nowe trasy.
   To kandydaci do kontroli, nie zadeklarowane połączenia WRO.
7. Zachować wykluczenia merytoryczne, np. FNC w 1A z powodu braku zniżki.
   Oferta partnera na stronie Vuelinga nie dowodzi rejsu Vuelinga do MAD.
8. Rozróżnić potwierdzoną trasę, sezonową/przyszłą, brak trasy, brak danych
   technicznych Wizz i nierozstrzygnięty błąd źródła. Brak lotów w oknie
   nie oznacza automatycznego usunięcia istniejącej sezonowej pozycji.
9. Dla każdej propozycji zapisać `step/variant`, oba odcinki, linie, hub,
   lotnisko Teneryfy, oba kierunki, dowód, datę, status i powód decyzji.
   Wydzielić dodatki WRO od niezwiązanych zmian dotyczących starej piątki.

Obecne `edge_exists()` uznaje opublikowanie dowolnego kierunku za dowód
siatki. Nie uprawnia to do stworzenia lotu powrotnego ani jego ceny:
podczas kolekcji oba kierunki zawsze sprawdzić niezależnie.

### Źródła i ceny, które muszą obowiązywać po rozszerzeniu

| Linia | Bieżące dane i ceny | Cena rezydenta |
| --- | --- | --- |
| Ryanair / Ryanair UK | Wyłącznie Google Flights HTTP; indywidualne rejsy `FR` i `RK`, wszystkie dni i rozpoznane grupy ofert. Bez Fare Finder i powrotu do starego API cenowego. | Tylko kwalifikujący się odcinek Hiszpania–Teneryfa w 3/5: wspólny szacunek z opłatami. Bez zniżki dla bezpośredniego WRO–Teneryfa. |
| Wizz Air | Oficjalne `timetableV2`, oddzielnie regular/WDC; baza API przez `scripts.wizz_api`. Numery i czasy blokowe z zatwierdzonych rejestrów. | Tylko kwalifikujący się odcinek w 4/5: wspólny szacunek z opłatami. Zachować osobne WDC. |
| Binter | Oficjalny `booking_search` do wyboru EUR cash fare, następnie `booking_getImports` dla konkretnej taryfy i jednego dorosłego. | Oficjalna końcowa kwota z kodem `RC` na kwalifikującym się odcinku, ze wszystkimi składnikami. |
| Iberia / Iberia Express | Oficjalne źródła tras; numery, godziny i regularna cena z Google Flights HTTP. | Szacunek wspólną regułą opłat. |
| Vueling | Oficjalna strona tras jest nadrzędna; Aena pomocniczo. Bieżące rejsy/ceny z Google Flights HTTP. | Szacunek wspólną regułą opłat. |
| Air Europa | Trasy z oficjalnych źródeł; numery, godziny i ceny każdego rejsu wyłącznie z Google Flights HTTP. Bez branded minimum dnia i szablonów. | Szacunek wspólną regułą opłat; oficjalny link nadal obsługuje `residentType=SPANISH_RESIDENT_RC`. |
| Volotea | Oficjalny MinPrice, osobno trasa/dzień; żądać i odczytywać `PriceWithFee`. Bez Google Flights. | Szacunek z opłatami. Zwrócone podatki/opłaty muszą zgadzać się ze wspólnym rejestrem. |
| Canaryfly | Oficjalne pełne `booking_calendar`, potem `booking_search` dostępnych dni i `booking_getImports` wybranej taryfy. Bez Google Flights. | Oficjalna końcowa kwota dla jednego dorosłego z kodem `DC`, ze wszystkimi składnikami. |

Binter/Canaryfly: sumować `mainAmount` dla ceny regularnej i `totalAmount`
dla rezydenta przez taryfę, podatki, dopłaty, opłatę serwisową i za obsługę.
Brak składnika/statusu rezydenta blokuje publikację. Opaque token wyłącznie
w pamięci. `booking_search` samo w sobie nie jest ceną końcową; nie wracać
do mnożenia taryfy ani całej ceny przez `0.25`.

## 6. Etap 3 — przygotować i zweryfikować techniczne dane Wizz

1. Wykorzystać istniejący `scripts/wizz_schedules.py`. Nie tworzyć kolejnego
   loadera i nie wpisywać WRO do stałych rozkładów w kodzie kolektorów.
2. Zaadaptować `scripts/verify_wizz_expansion_schedules.py`, aby jawnie
   przyjmował `--endpoint WRO`, zamiast wybierać na sztywno GDN. Pozostałe
   wymagane parametry: snapshot, dzień startu, długość okna i plik dowodów.
3. Zbierać dowody wyłącznie w osobnym pliku WRO z opisem endpointu, zakresu
   i snapshotu. Nie wznawiać go z materiału GDN lub innego okna tylko dlatego,
   że plik już istnieje. Dotyczy to także list `inactive_routes` i `pending`.
4. Weryfikować obie strony każdej potrzebnej pary WRO–hub, wszystkie
   występujące godziny odlotu oraz konkretne numery i czasy blokowe.
   Dla lotów bezpośrednich uwzględnić oba lotniska Teneryfy zgodnie z wynikiem
   kontroli rynku; nie zakładać aktywnego Wizz WRO–TFS/TFN bez dowodu.
5. Przy nowym hubie zbadać też potrzebne Wizz hub–Teneryfa i Teneryfa–hub.
   Wariant 5B korzysta z Wizz na odcinku Teneryfy, choć WRO–hub jest Ryanaira.
   Weryfikator ograniczony wyłącznie do par zawierających WRO nie wystarczy.
6. Numery, lokalne daty/godziny i czas wyznaczać na podstawie ofert;
   sprawdzić prefiksy marketingowe Wizz obsługiwane przez źródło. Nie
   obliczać czasu tylko z różnicy godzin lokalnych bez uwzględnienia stref.
7. W `data/wizz-route-schedules.json` dodać potwierdzone oba skierowane wpisy
   z dowodem i datą. Wyjątki trasy/godziny umieścić w
   `flight_number_overrides_by_departure_time`, także `duration_minutes`,
   jeżeli różni się od wartości podstawowej.
8. Do lokalnych `wizz_route_schedules` w allowlistach Bintera i Iberii dodać
   potrzebne pary i odpowiadające im wyjątki. Sprawdzić ich zgodność ze
   wspólnym rejestrem; nie usuwać ani nie nadpisywać wpisów starej piątki.
9. Obecny format override nie rozróżnia dat dla tej samej godziny. Jeśli
   materiał wykaże sprzeczne numery/czasy tej samej pary i godziny w różnych
   dniach, zgłosić konflikt. Rozwiązać go danymi obowiązywania i resolverem
   objętym testami, jeżeli konieczne do tej aktywowanej trasy; nie wybierać
   arbitralnie pierwszego rekordu.
10. Aktywny lot bez danych technicznych ma nadal zatrzymać kolektor.
    Poprawne `400 InvalidMarket` Wizz może oznaczać brak rynku; 503, awaria
    lub wyczerpane retry nie mogą zmienić się w pusty kalendarz.

Weryfikator techniczny może wybierać dni na podstawie kalendarza **tej samej
linii Wizz**. Taki dobór służy dowodom rozkładu i nie zastępuje raportu
pełnej późniejszej kolekcji cen obu uczestniczących linii.

## 7. Etap 4 — zastosować wyłącznie zweryfikowane zmiany konfiguracji

Najpierw uruchomić detektor w trybie podglądu, po rozszerzeniu rejestru i
uruchomieniu nowego procesu:

```text
.venv/bin/python scripts/discover_transfer_routes.py --as-of YYYY-MM-DD --report tmp/wro-expansion/discovery-report.json
```

Następne podglądy można odtworzyć przez `--snapshot` na tym samym materiale.
Uzupełnić braki Wizz i powtórzyć raport. `pending` nie jest aktywowaną trasą.
Brak danych jednego kandydata nie uzasadnia wyłączenia walidacji pozostałych.

`--apply` stosuje cały gotowy raport, a nie tylko WRO. Jeśli zawiera inne
zmiany, przygotować selektywny patch konfiguracji WRO. Można zaadaptować
`scripts/build_gdn_config_patch.py` do jawnego endpointu lub wydzielić z niego
narzędzie ogólne. Przy adaptacji koniecznie:

- Usunąć założenia GDN i tekstowe zamiany „cztery → pięć”; wyprowadzać
  docelowy scope z rejestru i zachować istniejące dowody Gdańska.
- Zachować tryb generowania patcha do przeglądu. Nie pisać ręcznie wyników
  publicznych. Idempotentnie łączyć wpisy źródłowe, bez duplikatów.
- Dodawać WRO tylko do zweryfikowanej pary hub/linia/variant. Stara piątka
  nie dostaje automatycznie nowych par, które wpadły przy pełnym discovery.
- Sprawdzać komplet Wizz również na odcinku Teneryfy w 5B. Stary helper
  nie stanowi samodzielnego zastępstwa `missing_wizz_schedules()`.
- Osobno obsłużyć nowe huby 1B–1F. Pętla po obecnych `airports` w starym
  helperze nie odkrywa i nie dodaje hubów dotąd wykluczonych.
- Uzupełnić scope, strefy, listy uprawnień, liczniki, opisy i dowody.
  Samo `apply_plan()` detektora nie aktualizuje wszystkich tych opisów.
- Nie zmieniać dat historycznych źródeł tak, jakby sprawdzono je ponownie.
  Do wpisu weryfikacji WRO dołączyć faktycznie sprawdzony zakres i datę.

### Przegląd wszystkich dziewięciu allowlist

| Plik | Zastany zakres hubów | Zmiana wymagana przy WRO |
| --- | --- | --- |
| `binter-transfer-airports.json` | FUE, LPA, MAD, PMI, SVQ, VLC | Scope sześciu; dowody WRO; lokalne Wizz numery/czasy/override. Nowy kwalifikujący się hub tylko po potwierdzeniu; FNC nadal wykluczone. |
| `iberia-transfer-airports.json` | MAD | Scope, dowody WRO, lokalne dane Wizz; nowy hub tylko przy potwierdzonym kwalifikującym się bezpośrednim odcinku Iberii/Express. |
| `vueling-transfer-airports.json` | ALC, BCN, BIO, AGP, SCQ, SVQ, VLC | Scope i konkretne `polish_routes` WRO z właściwymi liniami; osobno zweryfikować wykluczenia OVD/GRX i pełną właściwą siatkę. |
| `air-europa-transfer-airports.json` | MAD, BIO | Scope i potwierdzone `polish_routes`; zachować `flight_data_source=google_flights_http` i pełne numery UX. |
| `volotea-transfer-airports.json` | BIO | Scope i rzeczywiście potwierdzone pary WRO/linia, także audyt OVD i pozostałej siatki. Brak WRO nie jest błędem, jeżeli nie ma drugiego odcinka. |
| `canaryfly-transfer-airports.json` | FUE, LPA | Scope i potwierdzone `polish_routes`; ponowna kontrola ACE/SPC/VDE. Zachować konfigurację końcowych cen `booking_getImports` i kod `DC`. |
| `ryanair-transfer-airports.json` | 34 huby, kody z pliku | Dopisać WRO w `airports[].polish_airports` tylko po potwierdzeniu Ryanaira; dodać nowe huby i ich strefy/uprawnienia, jeśli kwalifikują się dzięki WRO. |
| `wizzair-transfer-airports.json` | BBU, BUD, FCO, MXP, OTP, SCQ | Scope i potwierdzone WRO; komplet metadata obu odcinków. Zachować sezonowe pozycje i precyzyjną politykę polskich endpointów jako hubów. |
| `mixed-transfer-airports.json` | A: 19 hubów, B: 6, łącznie 22 różne | Osobno pary WRO wariantu A i B, strefy, uprawnienia, liczniki; wyjątek GDN nadal tylko do KRK w B. |

Nawet jeśli 1E/1F nie zyskają trasy WRO, ich scope ma zawierać szóstkę,
a raport audytu ma wyjaśnić brak kwalifikującego się odcinka. Nie dopisywać
fikcyjnej trasy dla dodatniej liczby wyników w każdym wariancie.

## 8. Etap 5 — sprawdzić wpływ na kolektory, opłaty i plan pokrycia

### Macierze pobierania

| Kolektor | Co ma obejmować po rozszerzeniu |
| --- | --- |
| `collect_step1.py` — 1A | Każdy zapisany hub × sześć endpointów × dwa kierunki × Wizz/Ryanair; oddzielnie pełny kalendarz Bintera i końcowe ceny każdego wybranego lotu. |
| `collect_step1b.py` | Analogiczna pełna macierz low-cost z własnymi Wizz metadata; pełne niezależne dni Iberii/Express z Google. |
| `collect_step1c.py` | Wszystkie i tylko zapisane pary hub/endpoint/linia, wraz z WRO po weryfikacji; pełny niezależny skan Vuelinga. |
| `collect_step1d.py` | Własna allowlista trafia do współdzielonego wykonawcy z 1C; pełne indywidualne rejsy Air Europa, bez minimum dnia. |
| `collect_step1e.py` | Własna allowlista low-cost i każdy zapisany Volotea route/day w obu kierunkach, z ceną z opłatami. |
| `collect_step1f.py` | Własne low-cost, wszystkie miesiące Canaryfly w obu kierunkach, szczegóły dostępnych dni i końcowe ceny, niezależnie od rozkładu low-cost. |
| `collect_step2.py` | Dokładnie 24 skierowane pary na linię i 48 kombinacji trasa–linia: sześć endpointów × dwa lotniska Teneryfy × dwa kierunki × dwie linie. |
| `collect_step3.py` | Wszystkie zapisane WRO–hub i hub–Teneryfa Ryanaira w obu kierunkach, każdy dzień, kody FR/RK. |
| `collect_step4.py` | Analogicznie Wizz, wraz z kompletnymi danymi numerów/czasów obu odcinków i WDC. |
| `collect_step5.py` | A: Ryanair na odcinku Teneryfy, Wizz na odcinku WRO. B: Wizz na Teneryfie, Ryanair na odcinku WRO. Odwrócenie podróży nie zamienia przypisania linii. |

W kroku 2 wzrost wynosi **40 → 48 kombinacji, czyli 20%**. Nie jest to
prognoza wzrostu całej bazy ani czasu pracy: nowe huby i liczba dopasowań
mają własny koszt. Przy niezmienionych sześciu hubach 1A low-cost rośnie
ze 120 do 144 kombinacji; przy jednym hubie 1B z 20 do 24. Jeżeli pojawią
się nowe huby, przeliczyć te wartości ponownie.

W `collection_coverage.expected_queries()` sprawdzić rzeczywiste zaplanowane
pary i wszystkie daty. Dla pustych rynków WRO nadal musi istnieć udane
sprawdzenie każdego wymaganego dnia; brak wyniku nie jest brakiem zapytania.
Oczekiwań nie wyprowadzać z pobranych lotów ani dat drugiej linii.

### Opłaty i ceny rezydenckie

1. Korzystać z `scripts.spanish_resident_fees` i jedynego rejestru
   `data/spanish-resident-fees.json`. Wzór to
   `opłata_PLN + mnożnik × (regularna_PLN − opłata_PLN)`.
2. Samo WRO nie wymaga polskiej opłaty Aena: zniżka dotyczy właściwego
   odcinka hiszpańskiego. Nie dodawać WRO do tabeli opłat z tego powodu.
3. Nowy kwalifikujący się hub w Hiszpanii wymaga zweryfikowanej opłaty dla
   obu kierunków i okresu obejmującego całe okno. Dla wysp lub typu trasy
   nieobsługiwanego przez obecny rejestr rozszerzyć model na podstawie dowodów;
   nie przypisywać mu automatycznie stawki dla półwyspu.
4. Obecny rejestr obowiązuje do **2026-12-31**. Przy późniejszym wdrożeniu
   skontrolować wszystkie daty; wygasłej stawki nie omijać ani nie zgadywać.
5. Binter/Canaryfly zachowują końcowe kwoty przewoźnika, bez estymatora Aeny.
   Skrypty `reprice_*` nie dodają siatki WRO i nie zastępują nowej kolekcji.
6. Waluty nowych zagranicznych hubów porównać z `NBP_SHARED_CURRENCIES`
   oraz `SOURCE_CURRENCIES` odpowiednich kroków. WRO samo nie wymaga
   nowej waluty; nowy rynek może jej wymagać. Snapshot NBP ma być kompletny
   już przy pierwszym pobraniu i wspólny dla całego batcha.

## 9. Etap 6 — przygotować świeży batch i poprawną promocję raportów

Te dwa zastane szczegóły runnera trzeba uwzględnić przed podmianą bazy WRO.

### Świeżość cache Ryanaira

1. Wybrać nowy katalog stagingu dla nowego batcha WRO. Ustawić
   `RESIFLY_RYANAIR_GOOGLE_CACHE` na nowy plik w tym katalogu i przekazać
   tę samą ścieżkę wszystkim procesom dziesięciu kolektorów.
2. Zalecana mała poprawka runnera: ustalać plik cache z katalogu stagingu
   i `run_id`, przekazywać go w środowisku subprocessów oraz zapisywać ścieżkę
   w raporcie wykonania. Nowy run otrzymuje nowy plik; wznowienie tego samego
   runu korzysta z tego samego pliku i identycznych dat/konfiguracji.
3. Nie uznawać samego nowego `RESIFLY_COLLECTION_RUN_ID` za izolację cache:
   obecny domyślny cache jest wspólny dla identycznego okna niezależnie od ID.
4. Nie usuwać globalnie starych cache użytkownika. Odizolować nowy batch
   ścieżką. Nie ładować ręcznie diagnostycznego cache poprzedniego pobrania.

### Zgodna promocja feedów i sidecarów

1. Rozszerzyć `promote_batch()` o przygotowanie, backup i podmianę wszystkich
   **20 plików**: dziesięciu feedów i dziesięciu odpowiadających sidecarów.
   Przed pierwszą podmianą walidować cały staging tak jak dotychczas.
2. Obsłużyć zastany brak sidecarów: backup zapisuje ten fakt. Nie wyciągać
   starego raportu z feedu i nie przedstawiać go jako nowego sprawdzenia.
3. Przy obsłużonej awarii odtworzyć poprzednie feedy i sidecary, a nowy
   sidecar usunąć, jeśli przed próbą go nie było. Zachować pierwszą kopię
   poprzedniego stanu i wyczyścić wyłącznie własne pliki tymczasowe promocji.
4. Po udanej podmianie porównać publiczne 20 plików ze stagingiem i wykonać
   walidację całego katalogu publicznego, z tym samym oknem oraz run ID.
5. Nie opisywać tej operacji jako pojedynczej transakcji odpornej na nagłe
   zabicie procesu. Obecny model to przygotowane pliki i rollback obsłużonych
   błędów; większa przebudowa publikacji nie jest warunkiem samego WRO.

W `validate_batch()` dodać raport WRO per kierunek/wariant, najlepiej jako
mapy dla wszystkich endpointów, zachowując dotychczasowe informacje o GDN.
Oddzielnie raportować GDN jako transfer; nie zaliczać go do wyników endpointu.
Nie zmieniać schematu `results` ani funkcji haszujących ID dla samego raportu.

## 10. Etap 7 — interfejs, linki i dokumentacja

1. W `app.js.airportLabels` dodać `WRO: "Wrocław (WRO)"`. Kalendarz,
   wykres, karty i selektory mają nadal działać wspólnymi funkcjami.
2. W `index.html` dopisać Wrocław do listy w oknie informacji. Zachować GDN
   i pozostałe miasta. Nie przebudowywać wyglądu w ramach rozszerzenia siatki.
3. Opcje lotnisk nadal wynikają z danych wybranego kierunku. Jeśli poprawny
   skan nie zwróci oferty WRO, nie wymuszać pustej opcji bez osobnej decyzji
   o zmianie zachowania produktu. Wyjaśnić taki przypadek w raporcie.
4. Zachować domyślne Polska → Teneryfa / 1000 zł / 6 h / najbliższy termin,
   wyłączanie drugiej linii dla lotów direct, X filtrów i reset zakresu dat.
5. Sprawdzić z WRO kalendarz i wykres wskazujące tę samą najtańszą kartę,
   cztery tryby resident/WDC, sortowanie całego zbioru, dogrywanie kart,
   zakotwiczenie wybranego lotu i ponowne wykorzystanie cache kart.
6. `scripts.booking_urls` przyjmuje kody lotnisk Wizz/Ryanaira ogólnie;
   sprawdzić WRO jako origin/destination, datę i pasażerów. Każdy odcinek
   ma własny link. Nie używać linku całej podróży do zakupu obu biletów.
7. Zachować linki pozostałych linii. Air Europa nadal otwiera trasę/dzień,
   nie gwarantuje wyboru numeru rejsu; przełącznik rezydenta usuwa/dodaje
   właściwy parametr. Nie dopisywać WRO do kanaryjskich slugów Canaryfly.
8. Sprawdzić udostępniony lot WRO w obu kierunkach, także powyżej 1000 zł,
   oraz link istniejącego lotu starej piątki. Domyślny kierunek nie może
   nadpisać kierunku odtwarzanego z linku.
9. Przy zmianie `app.js` podnieść jego parametr wersji w HTML. CSS zmieniać
   tylko jeśli wynika to z rzeczywistej potrzeby układu.
10. Uaktualnić aktywne `AGENTS.md`, kanoniczną instrukcję, README i opisy
    allowlist do sześciu endpointów, macierzy 48 i faktycznie zweryfikowanej
    siatki. Poprawić także nieaktualny opis fallbacku Ryanaira w README.
    Historycznych raportów GDN i przykładowych fixture nie przepisywać.

## 11. Etap 8 — testy, które mają wykazać poprawność rozszerzenia

Zachować testy Gdańska jako regresję. Nie zastępować ich wszystkich przypadkami
WRO. Testy wymagające jawnego zakresu produkcji zaktualizować do szóstki;
syntetycznych liczników nie podnosić automatycznie.

| Obszar / istniejące pliki testów | Wymagane zachowanie |
| --- | --- |
| `test_airport_expansion.py`, `test_allowlist_metadata.py` | Jawne sześć kodów, WRO/Europe/Warsaw niezależnie od kolejności importów, dziewięć zgodnych scope, brak duplikatów/self-route i wyjścia poza dozwolone pary. |
| `test_step2_collector.py` | 24 skierowane pary i obie linie w planie pokrycia, w tym cztery kierunkowe pary WRO/TFN/TFS. Z 20 na 24 zmienia się liczba par na linię, nie liczba dat. |
| `test_airport_expansion.py` — macierz 1A/1B | Dwa syntetyczne huby × sześć endpointów × dwa kierunki to 24 wywołania na linię, wcześniej 20. WRO jest pytane przez obie linie także przy pustych wynikach. |
| Testy 1A/1B i Wizz | Lokalne i wspólne numery/czasy/override WRO są zgodne; aktywna nieznana para kończy się błędem, InvalidMarket poprawnym zerem; dwie różne godziny tego samego dnia zachowują osobne rejsy. |
| Testy 1C–1F | Rzeczywisty wykonawca low-cost z 1C dostaje właściwą allowlistę. WRO tylko przy zapisanej parze i linii; oba kierunki, pełne niezależne kalendarze. Nie wymagać WRO w produkcyjnym 1E/1F bez trasy. |
| Testy 3/4/5 | WRO jako endpoint w obu kierunkach i obu wariantach mieszanych, właściwa linia na odcinku, brak zniżki na polskim odcinku. |
| `test_route_discovery.py` | WRO rozszerza istniejący hub i otwiera nowy; brak Wizz jednej strony daje pending; selektywne apply zachowuje starą piątkę, nie usuwa sezonowych tras i jest idempotentne. |
| Rola GDN | KRK ↔ GDN ↔ TFS nadal działa. GDN–WRO jako dodatkowa rola transferu oraz WRO–WRO są odrzucane przez detektor, macierze i walidator wyników. |
| `test_ryanair_google.py`, `test_source_completeness.py` | Pełne dni WRO, FR/RK, indywidualna cena każdego rejsu, różne godziny jednego dnia, poprawne puste dni; błędy lub rejs bez ceny blokują zapis. |
| Testy cen Bintera/Canaryfly | Nadal końcowe imports ze wszystkimi składnikami; właściwy RC/DC; brak składowej lub potwierdzenia statusu blokuje publikację. Token nie trafia do danych. |
| `test_spanish_resident_fees.py` | Szacunek z pełnymi opłatami w obu kierunkach; nowy hiszpański hub bez reguły i data po ważności blokują zapis; oficjalne kwoty Bintera/Canaryfly pozostają bez zmian. |
| `test_collection_reliability.py`, `test_wizz_api.py` | Google max 2 także retry; jeden dzienny NBP; aktualna wersja Wizz; awaria dowolnego źródła zachowuje poprzednie publiczne pliki. |
| `test_five_step_batch.py` | Pełna szóstka, zgodne run ID, odrzucenie starego pięcioendpointowego raportu i brakującego dnia WRO; nowy run ma świeży cache, wznowienie wspólny; promocja/rollback feedów i sidecarów, także przy ich wcześniejszym braku. |
| `test_booking_urls.py`, `test_airport_ui.mjs` | Linki WRO obu kierunków, domyślne ustawienia, minima kalendarza/wykresu, chipy X, reset, wszystkie sortowania, udostępnianie, `+1`, lot direct i cztery tryby zniżek. |
| Regresja pięciu endpointów | Te same wejścia i zatwierdzone stare trasy dają identyczne ID, ceny i dopasowania dla WAW/WMI/KTW/KRK/GDN; wyjątek transferowy GDN nadal działa. |

Uwzględnić 119/120 i 1440/1441 minut, przylot po północy, zmianę czasu,
granice okna i lokalne strefy. Sprawdzać pełne daty, nie tylko napis godziny.
Przynajmniej jeden przypadek powinien mieć lot jednej linii w dniu bez
drugiej: oba kalendarze nadal muszą być pobrane w pełni.

Uruchomienie testów offline:

```bash
.venv/bin/python -m unittest discover -s tests
node --check app.js
node --test tests/test_airport_ui.mjs
git diff --check
```

Testy JS odczytują publiczne feedy albo katalog wskazany przez
`RESIFLY_TEST_DATA_DIRECTORY`. Po kolekcji uruchomić je również na stagingu.
Nie opierać testów liczby ofert na sztywnym oczekiwaniu dodatnich wyników WRO
w każdym wariancie: pokrycie ma odróżnić brak możliwości od braku sprawdzenia.

## 12. Etap 9 — zebrać nową pełną bazę do stagingu

Ten etap wykonuje się dopiero podczas wdrożenia, nie podczas czytania planu.

1. Ustalić jeden dzień startu w `Atlantic/Canary`, jawnie przekazać go jako
   `--from-date`. Użyć tego samego `--days 30` i niezmienionej konfiguracji
   przez cały run. Nie polegać na osobnych `date.today()` procesów runnera.
2. Wybrać nowy katalog, np. `tmp/wro-expansion/batch-YYYY-MM-DD-RUN`, i świeży
   cache Ryanaira zgodnie z etapem 6. Kursy NBP mogą pochodzić ze wspólnego
   poprawnego snapshotu tego dnia; nie trzeba odpytywać ich na każdym kroku.
3. Korzystać z `scripts/collect_five_steps.py`, który nada jeden run ID i
   wykona kolejno 1A, 1B, 1C, 1D, 1E, 1F, 2, 3, 4, 5.
4. Zbierać cały zakres sześciu endpointów i wszystkich zatwierdzonych tras,
   a nie tylko dopisywać WRO do wczorajszych JSON-ów. Stary raport piątki
   nie może poświadczyć kompletności szóstki.
5. Nie uruchamiać obok siebie kolektorów ani weryfikatora technicznego,
   które razem przekroczą Google max 2. Sekwencyjny batch i cap w każdym
   procesie zachowują limit; równoległe osobne procesy mają własne limity.
6. Każdy z dziesięciu feedów musi mieć sidecar i status complete. Przy błędzie
   zatrzymać publikację, zachować log i raport failed, nie uzupełniać starymi
   lotami/cenami. Wznowienie wymaga tego samego run ID, dat i konfiguracji.
7. `--refresh-steps` służy wznowieniu nieudanego/niezakończonego zakresu tego
   samego runu, nie połączeniu nowego WRO ze starymi cenami pięciu endpointów.
   Jeśli zmieniono konfigurację albo minął dzień, rozpocząć świeży run.

Szablony poleceń (zastąpić znaczniki; nie wykonywać ich podczas przygotowania
samego dokumentu):

```text
.venv/bin/python scripts/collect_five_steps.py --from-date YYYY-MM-DD --days 30 --stage-directory tmp/wro-expansion/batch-YYYY-MM-DD-RUN --workers 4

.venv/bin/python scripts/collect_five_steps.py --from-date YYYY-MM-DD --days 30 --stage-directory tmp/wro-expansion/batch-YYYY-MM-DD-RUN --run-id RUN_ID_Z_RAPORTU --refresh-steps 3 4 5

.venv/bin/python scripts/collect_five_steps.py --from-date YYYY-MM-DD --days 30 --stage-directory tmp/wro-expansion/batch-YYYY-MM-DD-RUN --validate-only
```

Pierwsze dwa wywołania wymagają ustawienia wspólnej świeżej ścieżki
`RESIFLY_RYANAIR_GOOGLE_CACHE`, jeżeli runner nie robi już tego automatycznie.
Numery kroków wznowienia w przykładzie zastąpić faktycznie brakującymi.
Obecny `validate_batch()` wymaga daty `generated_at` bieżącego dnia
kanaryjskiego; wznowienie po północy może wymagać nowej pełnej kolekcji.
Nie zmieniać timestamps w JSON-ach, aby przejść ten warunek.

## 13. Etap 10 — odbiór stagingu, lokalna podmiana i ewentualna publikacja

Przed lokalną promocją sprawdzić:

1. Dziesięć feedów schema 2, dziesięć zgodnych sidecarów, dokładnie te same
   daty, jeden run ID, właściwe źródła i ten sam zestaw dziennych kursów.
2. `expected_queries` odpowiada bieżącej konfiguracji szóstki. Każdy
   zaplanowany WRO route/day jest sprawdzony, również przy zerze lotów.
   Canaryfly ma także szczegóły dni dostępnych według pełnego kalendarza.
3. Unikalność ID globalnie, właściwe endpointy/kierunki, dozwolone huby,
   poprawne łączenie lotnisk, numery i godziny odcinków, 2–24 h przesiadki,
   wszystkie ceny i sumy, uprawnienia i linki, brak tokenów.
4. Wyniki WRO rozbite na kierunki, krok/variant, linię i hub. Osobno stara
   piątka i GDN jako transfer. Liczby wyników nie zastępują raportu pokrycia.
5. Wszystkie nowe dozwolone pary mają dowody; pending i brak rynku są
   opisane uczciwie. Nie ogłaszać kompletnego rozszerzenia, jeżeli pominięto
   nierozstrzygnięte wymagane trasy lub brakujące metadata.
6. Testy offline i JS na stagingu przeszły. Kontrola przeglądarki obejmuje
   WRO jako wylot/przylot, kalendarz/słupek → właściwa karta, link zakupu,
   udostępnianie, `+1`, filtrowanie i stare endpointy.
7. Zmierzyć większy zbiór: czas przygotowania, płynność filtrów i pamięć na
   desktopie oraz w wąskim układzie. Nie podnosić automatycznie workers,
   batchów kart ani limitów cache dla samego wzrostu siatki.

Do podglądu stagingu przygotować lokalną kopię strony w `tmp/` z tymi
feedami i wskazać ją serwerowi HTTP; nie trzeba podmieniać `data/`, żeby
ocenić WRO w przeglądarce. Zachować rzeczywiste testy GDN na tej samej bazie.

Dopiero po spełnieniu warunków i poprawieniu promocji sidecarów z etapu 6:

```text
.venv/bin/python scripts/collect_five_steps.py --from-date YYYY-MM-DD --days 30 --stage-directory tmp/wro-expansion/batch-YYYY-MM-DD-RUN --validate-only --promote
```

Po lokalnej podmianie ponownie sprawdzić 20 plików, publiczną walidację
i stronę. Raport końcowy `docs/WDROZENIE_WROCLAWIA_WRO.md` ma podawać zakres
tras, wyniki WRO/starej piątki/GDN transfer, daty, run ID, cache, kursy,
testy, nierozstrzygnięte pozycje i lokalizację backupu. Nie dodawać sesyjnych
URL-i ani tokenów do raportu.

Jeżeli użytkownik poleci wysłanie na GitHub, publikować spójny komplet kodu,
konfiguracji, dokumentacji, dziesięciu feedów i sidecarów. Po push sprawdzić
docelową stronę. Wycofanie obejmuje spójny zestaw poprzedniej konfiguracji,
kodu i danych, z poszanowaniem zastanych zmian użytkownika.

## 14. Wymagania dla przyszłego GitHub Actions

Tworzenie workflow nie jest częścią dodania WRO, chyba że użytkownik rozszerzy
zadanie. Przyszły workflow powinien używać tego samego kodu i konfiguracji:

- Instalować `scripts/requirements-flight-collector.txt` i uruchamiać testy.
- Wyznaczać jeden dzień w `Atlantic/Canary`, bez polegania na UTC runnera.
- Wykonywać dziesięć kolektorów kolejno w jednym jobie, z jednym run ID,
  cache Ryanaira ograniczonym do runu i jednym dziennym snapshotem NBP.
- Zachować Google max 2 łącznie. Oddzielne równoległe joby nie współdzielą
  automatycznie semafora; nie traktować ich limitów jako limitu globalnego.
- Rejestrować logi, audyt konfiguracji, raporty pokrycia i wynik walidacji
  jako artefakty; nie publikować częściowego sukcesu.
- Detektor siatki uruchamiać osobno. Normalny refresh cen nie zmienia allowlist.
- Budżet czasu dostosować do pomiarów nowej siatki; nie skracać okna ani nie
  zwiększać równoległości źródła w celu uzyskania zielonego przebiegu.
- Publikować spójny zestaw dopiero po walidacji; kontrolować również
  obowiązywanie tabeli opłat, końcowe imports Binter/Canaryfly i trwałe linki.

## 15. Checklista zakończenia wdrożenia

- [ ] Rejestr i dziewięć scope zawierają dokładnie WAW/WMI/KTW/KRK/GDN/WRO.
- [ ] WRO ma Europe/Warsaw; kolektory, detektor i coverage czytają ten sam rejestr.
- [ ] Zweryfikowano istniejące i nowe huby wszystkich wariantów, także dawne wykluczenia zależne od polskiej siatki.
- [ ] Każda aktywowana para ma dowód właściwego przewoźnika; pending nie udaje gotowej trasy.
- [ ] Wizz ma oba kierunki i wszystkie potrzebne numery/czasy/override w odpowiednich rejestrach.
- [ ] Zachowano GDN/5B/KRK; nie rozszerzono milcząco roli polskich endpointów jako transferów.
- [ ] Krok 2 planuje 24 skierowane pary na linię, 48 kombinacji i pełne 31 dat przy days 30.
- [ ] Każdy pozostały krok faktycznie skanuje nowe zatwierdzone pary i niezależne kalendarze obu linii.
- [ ] Ryanair i Air Europa nadal używają Google; Binter/Canaryfly nadal końcowych imports RC/DC.
- [ ] Szacunki stosują wspólną ważną tabelę opłat; żadna nowa opłata nie jest zgadnięta.
- [ ] Google max 2, jeden dzienny NBP i świeży cache Ryanaira wspólny wyłącznie dla tego runu.
- [ ] Testy WRO i regresji całej piątki przechodzą; zachowanie ID i domyślne filtry są zachowane.
- [ ] UI pokazuje Wrocław, a kalendarz, wykres, linki i udostępnianie działają w obu kierunkach.
- [ ] Całe dziesięć nowych feedów ma zgodne sidecary i kompletny bieżący plan pokrycia z jednym run ID.
- [ ] Promocja/backup/rollback obejmuje feedy i sidecary; po podmianie publiczne pliki są zgodne ze stagingiem.
- [ ] Raport wdrożenia opisuje wyniki, pokrycie, backup i wszystkie ograniczenia; publikacja zgodna z poleceniem użytkownika.

## 16. Co sprawdzono przy przygotowaniu tego planu

- Przeczytano bieżące instrukcje kolekcji i bezpieczeństwa, historyczny plan
  oraz raport Gdańska; sprawdzono rejestry, dziewięć allowlist, wspólne moduły,
  funkcje kolektorów i ich współdzielenie, detektor, narzędzia GDN, runner,
  testy, README i fragmenty interfejsu dotyczące endpointów.
- Odczytano lokalne metadane i liczebności dziesięciu feedów oraz policzono
  obecne plany tras/dni przez `expected_queries`, bez zapytań do przewoźników.
- Uruchomiono bazowe testy: **154 Python — OK; 12 JavaScript — OK**.
  To testy aktualnej wersji pięciu endpointów, nie wykonanego wdrożenia WRO.
- Nie uruchamiano live discovery, kolektorów cen ani skryptów naprawy cen;
  nie zmieniono rejestru, allowlist, aplikacji ani publicznych wyników.
- Zapisano ten plan i odnośniki dokumentacyjne. Nie wykonano commita ani push.
