# Plan wdrożenia Gdańska (GDN) jako piątego polskiego lotniska ResiFly

Dokument historyczny: Gdańsk został już wdrożony. Aktualny plan kolejnego
rozszerzenia, uwzględniający obecną piątkę endpointów i późniejsze poprawki
kolektorów, znajduje się w [PLAN_DODANIA_WROCLAWIA_WRO.md](PLAN_DODANIA_WROCLAWIA_WRO.md).

Dokument dla Codexa realizującego wdrożenie. Przygotowany 22 października 2026 r.
na podstawie lokalnego repozytorium, HEAD `52d504872547341e857ab6b30cb5ad2ea928d00a`.
Numery linii poniżej dotyczą tego stanu i mogą się przesunąć.

To plan przyszłej zmiany. Przy jego przygotowaniu nie zmieniono kolektorów,
allowlist, strony ani publicznych wyników; nie pobierano aktualnej siatki lub cen.
Istnienie trasy w zapisanym rejestrze nie jest potwierdzeniem jej dostępności
w dniu późniejszego wdrożenia.

## 1. Docelowy zakres i zasady

Docelowa lista polskich lotnisk: **WAW, WMI, KTW, KRK, GDN**. GDN to Gdańsk,
strefa `Europe/Warsaw`. Zachować dotychczasową kolejność czterech kodów i dopisać
GDN, jeśli porządek konfiguracji ma wpływ na raporty lub interfejs.

Nadal obowiązuje dokładnie pięć głównych kroków. Krok 1 zawiera warianty 1A–1F.
Strona nadal korzysta z tych samych dziesięciu feedów; nie tworzyć osobnego
kroku ani publicznego feedu „Gdańsk”.

Wdrożenie obejmuje zarówno GDN → Teneryfa, jak i Teneryfa → GDN, loty
bezpośrednie oraz wszystkie kwalifikujące się połączenia z jedną przesiadką
w ramach obecnych przewoźników i reguł poszczególnych kroków.

Podczas realizacji zachować:

- Pełne skonfigurowane kalendarze każdej zapisanej trasy i każdej linii w obu
  kierunkach przed łączeniem odcinków. Daty jednej linii nie ograniczają zapytań
  do drugiej.
- Obecną semantykę `--days 30`: przedział domknięty od dnia startu do start + 30
  dni, czyli 31 dat kalendarzowych. Zmiana tej semantyki wymaga osobnej decyzji.
- Maksymalnie jedną przesiadkę, 120–1440 minut oczekiwania i prawidłową chronologię.
- Wszystkie ceny, również drogie wyniki. Limit ceny działa dopiero na stronie.
- Osobne ceny regularne, rezydenckie i WIZZ Discount Club, o ile źródło je podaje.
- Zniżkę rezydenta wyłącznie na kwalifikującym się odcinku do/z Teneryfy,
  zgodnie z właściwą allowlistą. GDN jako polski endpoint nie tworzy nowego prawa
  do zniżki. Cena rezydencka Canaryfly pozostaje oficjalną ceną konkretnego lotu.
- Dotychczasowe źródła danych każdego wariantu, trwałe linki na poziomie odcinków
  oraz brak cookies, tokenów i adresów sesji w publicznych plikach.
- Limit Google Flights do dwóch równoległych zapytań, dotychczasowe retry oraz
  jeden dzienny zestaw NBP dla całego uruchomienia.
- Dotychczasową identyfikację wyników i zachowanie czterech starych lotnisk przy
  tych samych danych wejściowych.

## 2. Fakty znalezione w obecnych plikach

| Obszar | Stan i znaczenie dla wdrożenia |
| --- | --- |
| Wspólny zakres kolektorów | `scripts/collect_step1.py:39` definiuje cztery `POLISH_AIRPORTS`. Wszystkie pozostałe kolektory importują tę stałą. |
| Strefy endpointów | `scripts/collect_step1.py:47` zawiera bazowe strefy, ale bez GDN. Nie można polegać na przypadkowym dopisaniu strefy z innej allowlisty. |
| Niezależny zakres detektora | `scripts/discover_transfer_routes.py:42` powtarza cztery kody; `ENDPOINTS` powstaje osobno w linii 44. |
| Powielony zakres w danych | Każda z dziewięciu allowlist ma własne `scope.polish_airports` z czterema kodami. |
| Kolektory 1A/1B | Wspólne `collect_low_cost_legs()` w `collect_step1.py:567` buduje pełny iloczyn hubów, polskich lotnisk, dwóch kierunków i dwóch linii. `eligibility_evidence` nie ogranicza tej macierzy. |
| Pułapka Wizz w 1A/1B | `collect_step1.py:366` zwraca pustą listę przed zapytaniem API, jeśli brak technicznego rozkładu. Nowe trasy mogą zniknąć po cichu. |
| Pułapka Ryanair w 1A–1F | `collect_step1.py:421` przechwytuje błąd pobierania i zwraca `[]`. Ten wspólny helper może ukryć nieudany skan GDN jako brak lotów. |
| Kolektory 1C–1F | Rzeczywisty zakres wyznaczają `airports[].polish_routes[]`, z kodem lotniska i listą linii. Samo rozszerzenie `scope` nie dodaje zapytań. |
| Wspólny wykonawca 1C–1F | 1D, 1E i 1F importują faktyczne `collect_low_cost_legs()` z `collect_step1c.py`, mimo posiadania własnych funkcji macierzy. Uwzględnić to przy testowaniu. |
| Bezpośrednie Wizz | `collect_step2.py:52` ma osobne `WIZZ_DIRECT_SCHEDULES`, tylko WAW/KTW ↔ TFS. Nie czyta wspólnego JSON-a. |
| Pozostałe Wizz | 1C–1F oraz kroki 4 i 5 korzystają z loadera w `collect_step4.py:53`, łączącego rejestr wspólny i dane Bintera. |
| GDN jako przesiadka | `mixed-transfer-airports.json:327` zawiera już TFS ↔ GDN Wizz oraz GDN ↔ KRK Ryanair. W obecnym feedzie kroku 5 jest 8 wyników przez GDN, bez GDN jako endpointu. |
| Zapisane rozkłady GDN | W `wizz-route-schedules.json:182` jest GDN → TFS, W61709, 365 min; w linii 428 TFS → GDN, W61710, 330 min. Innych par GDN obecnie tam nie ma. Są to dane zapisane, wymagające sprawdzenia przy wdrożeniu. |
| UI | `app.js:414` ma już etykietę „Gdańsk (GDN)”. Opcje lotnisk i minima kalendarza powstają z rzeczywistych wyników. |
| Tekst strony | `index.html:368` ma sztywną listę czterech polskich lotnisk w oknie informacyjnym. |
| Testy | `tests/test_step2_collector.py:70` oczekuje dokładnie 16 skierowanych par i czterech kodów. Obecnie 78 testów przechodzi; nie ma testów GDN. |
| Publikacja | Kolektory mają `--output` i walidują dokument przed końcowym `write_text`, ale nie ma transakcji całego zestawu dziesięciu feedów. |
| Actions | W badanym repozytorium nie ma `.github/workflows`. Dokumentacja opisuje dopiero przyszłe Actions. |

## 3. Kolejność realizacji

### Etap 0 — utrwalić punkt odniesienia

1. Przeczytać aktualne `AGENTS.md` i `docs/FIVE_STEP_FLIGHT_SEARCH.md`.
2. Sprawdzić aktualny HEAD, status i zmiany użytkownika. Utworzyć gałąź roboczą
   z prefiksem `codex/`. Nie dołączać niezwiązanych plików.
3. Zachować dotychczasowy działający zestaw konfiguracji i dziesięciu feedów do
   porównań oraz ewentualnego wycofania. Staging i raporty umieszczać w `tmp/`.
4. Uruchomić testy bazowe, zapisać ich wynik i zebrać raport konfiguracji:
   endpointy, trasy per krok/wariant/linia/kierunek, brakujące rozkłady Wizz.
5. Przygotować niezmienne, syntetyczne kalendarze do porównania zachowania starej
   czwórki przed i po zmianie. Porównywanie dwóch odrębnych pobrań aktualnych cen
   nie dowodzi regresji: rozkład i cena mogły się zmienić.

Punkt odniesienia z audytu: wszystkie dziesięć publicznych feedów ma zakres
2026-10-22–2026-11-21; łącznie 4423 wyniki. Żaden nie ma GDN jako endpointu.
W kroku 5 osiem wyników ma GDN jako przesiadkę. Tych liczb nie traktować jako
oczekiwanej liczby wyników późniejszego aktualnego pobrania.

### Etap 1 — ustalić jedno źródło polskich endpointów

Rekomendowana realizacja: dodać `data/search-airports.json` oraz niewielki moduł
`scripts/search_airports.py`. Są to nowe pliki proponowane przez ten plan,
nie istniejące elementy repozytorium.

1. Rejestr ma zawierać zatwierdzone kody, nazwy i strefy polskich endpointów:
   WAW/WMI/KTW/KRK/GDN. Strefy Teneryfy można pozostawić w dotychczasowym miejscu
   albo przenieść do tego samego rejestru, zachowując TFN/TFS.
2. Moduł ma udostępniać niezmienną listę endpointów i mapę stref. Używać tylko
   standardowych zależności i odczytu lokalnego; import nie wykonuje zapytań HTTP.
3. `collect_step1.py` ma pobierać te wartości z modułu. Może nadal eksportować
   stare nazwy, aby obecne importy kolektorów działały bez szerokiego refaktoru.
4. Detektor ma czytać ten sam rejestr zamiast własnej krotki czterech kodów.
5. GDN ma być dostępne z `Europe/Warsaw` już przy uruchomieniu pojedynczego
   kolektora, niezależnie od kolejności importów i wcześniejszego wykonania kroku 5.
6. Wszystkie dziewięć `scope.polish_airports` zsynchronizować z zatwierdzoną
   piątką. Jeżeli pozostają kopiami metadanych, test ma wymuszać ich zgodność.
7. Sprawdzić poprawność kodów, unikalność i poprawność IANA time zone. Rozdzielić
   konfigurację endpointów od rzeczywistych dopuszczonych tras przez każdy hub.

Warunek zakończenia: kolektory i detektor widzą dokładnie tę samą piątkę;
zmiana zakresu w jednym miejscu nie zostawia drugiej listy czterech kodów.

### Etap 2 — jawnie zachować istniejącą rolę przesiadkową GDN

Rekomendowana polityka dla tego wdrożenia: **GDN zostaje endpointem i zachowuje
dotychczasowe poprawne połączenia jako przesiadka do innych polskich lotnisk**.
Dodanie endpointu nie jest powodem skasowania obecnego wariantu przez GDN do KRK.

1. Zachować rekord GDN w wariancie
   `wizzair_tenerife_ryanair_poland`, jego strefę i brak uprawnienia do zniżki.
2. Rozróżniać rolę kodu w konkretnym połączeniu. Poprawne są np. GDN → hub → TFS
   oraz KRK → GDN → TFS, jeżeli trasy są zatwierdzone i kalendarze na to pozwalają.
3. Odrzucać odcinek GDN → GDN, transfer równy faktycznemu początkowi/końcowi
   podróży i pozorne przesiadki z powielonym lotniskiem.
4. Obecny detektor odejmuje wszystkie `ENDPOINTS` od transferów. Po dodaniu GDN
   przestałby je wykrywać, a stary wpis pozostałby w allowliście, ponieważ `--apply`
   niczego nie usuwa. Dodać jawną obsługę wyjątku GDN w wyborze kandydatów.
   Objąć nią oba odejmowania endpointów w `candidate_intersection()`, obecnie
   linie 182 i 187; GDN pozostaje w `POLISH_AIRPORTS`. Osobno filtrować
   `transfer == polish` dla konkretnej pary.
   Wyjątek w tym wdrożeniu zachowuje zatwierdzony wariant 5B/GDN/KRK.
   Nie aktywować nim automatycznie nowych ról GDN jako transferu w innych
   krokach lub do innych polskich endpointów. Takie propozycje raportować
   osobno; rozszerzenie endpointów o GDN działa normalnie we wszystkich krokach.
5. `selection_method.excluded_endpoints` ma opisywać rzeczywistą politykę.
   Nie dopisywać tam GDN bez uwzględnienia wyjątku. Nie zmieniać przy okazji roli
   WAW/WMI/KTW/KRK jako transferów, jeśli nie zostało to osobno uzgodnione.
6. Testy mają obejmować oba kierunki starej trasy przez GDN oraz nową rolę GDN
   jako endpointu. Stare numery lotów i hashe ID zachowują się tak samo przy tych
   samych wejściach.

Jeżeli właściciel później zażąda GDN wyłącznie jako endpointu, potrzebna będzie
osobna jawna migracja: rekord transferu, timezone, lista ineligible, liczniki i
testy. Nie dokonywać jej milcząco w ramach tego planu. Techniczne rozkłady
GDN ↔ TFS pozostają potrzebne również wtedy, w kroku 2.

### Etap 3 — zweryfikować całą siatkę wynikającą z dodania GDN

Ten etap jest jednorazową kontrolą siatki przed aktywacją. Zwykłe późniejsze
odświeżanie cen nadal używa zapisanych allowlist.

1. Zebrać aktualne oficjalne siatki bezpośrednich tras Ryanair i Wizz Air z GDN
   i do GDN, rozróżniając konkretne kody lotnisk oraz przewoźników.
2. Dla kroku 2 sprawdzić pełne GDN ↔ TFN i GDN ↔ TFS dla obu linii. Nie zakładać
   istnienia trasy tylko dlatego, że dodano GDN do macierzy.
3. Dla przesiadek przeciąć te siatki z dozwolonymi bezpośrednimi siatkami linii
   obsługujących odcinek Teneryfy w każdym wariancie. Sprawdzić:
   - GDN przez istniejący hub;
   - nowy hub, który dopiero dzięki GDN spełnia warunki;
   - kandydata wcześniej odrzuconego wyłącznie z powodu braku dalszej trasy
     do poprzedniej czwórki.
4. Nie ograniczać audytu do obecnych hubów. Szczególnie ponownie sprawdzić
   zapisane wykluczenia: Vueling OVD/GRX; Volotea OVD; Canaryfly ACE/SPC/VDE.
   To kandydaci do kontroli, nie potwierdzone nowe trasy.
5. Zachować wykluczenia o innej przyczynie: FNC w 1A z powodu braku zniżki;
   MAD w 1C nie staje się trasą Vuelinga przez samo dodanie GDN.
6. Sprawdzać aktualne źródła właściwe dla wariantu:

| Wariant | Weryfikacja siatki i późniejsze źródło cen |
| --- | --- |
| 1A Binter | Oficjalna siatka/rozkład Bintera, uprawnienie do zniżki; ceny i loty z obecnego GraphQL. |
| 1B Iberia/Express | Oficjalne bezpośrednie trasy ze zniżką; regularne ceny z Google Flights przez HTTP. |
| 1C Vueling | Oficjalna strona tras Vuelinga jest nadrzędna; Aena tylko pomocniczo; ceny z Google Flights przez HTTP. |
| 1D Air Europa | Lista tras z zapisanych oficjalnych źródeł; od 22.10.2026 numery rejsów, godziny i ceny tylko z Google Flights HTTP, maksymalnie 2 zapytania równolegle. Bez minimum dnia i szablonów. |
| 1E Volotea | Oficjalna strona tras i MinPrice; odrębne zapytania o każdy dzień i oba kierunki. Bez Google Flights. |
| 1F Canaryfly | Oficjalne trasy i GraphQL: pełne kalendarze miesięczne, następnie szczegóły dostępnych dni. Bez Google Flights. |
| 2–5 | Oficjalne siatki Ryanair/Wizz i obecne publiczne źródła rozkładów/cen; Wizz wymaga technicznych danych uzupełniających. |

7. Zapisać raport weryfikacji z datą, źródłem i dokładną kombinacją
   `krok/wariant, przewoźnik, origin, destination`, statusem:
   potwierdzona / sezonowa lub przyszła / brak trasy / oczekuje na dane Wizz /
   brak rozstrzygnięcia. Brak lotów w aktualnym oknie nie usuwa sezonowej trasy.
8. Mapy sieci bywają jednostronne. Obecne `edge_exists()` uznaje dowolny
   opublikowany kierunek za dowód siatki; kolektory muszą mimo to sprawdzić
   oba kierunki osobno i nie tworzyć lotu powrotnego z lotu wylotowego.
9. Wyodrębnić zmiany związane z rozszerzeniem o GDN. Pełny raport detektora może
   pokazać także niezwiązane zmiany bieżącej siatki; nie stosować ich automatycznie
   przy okazji dodawania piątego lotniska.

Warunek zakończenia: każda nowa dozwolona kombinacja ma dowód i status;
nie ma założenia, że GDN obsługuje wszystkie dotychczasowe huby.

### Etap 4 — uzupełnić techniczne rozkłady Wizz i usunąć pułapki ładowania

1. Zweryfikować zapisane GDN ↔ TFS: numery, czas blokowy obu kierunków,
   obowiązujący okres oraz ewentualne różne numery zależne od godziny.
2. Każdą nową parę GDN ↔ hub obsługiwaną przez Wizz uzupełnić o oba skierowane
   rekordy: `origin`, `destination`, `flight_number`, `duration_minutes`.
   Wyjątki godzinowe dodać w `flight_number_overrides_by_departure_time`.
3. Dane umieścić tam, skąd faktycznie korzysta wariant:
   - 1A: `binter-transfer-airports.json.wizz_route_schedules`;
   - 1B: `iberia-transfer-airports.json.wizz_route_schedules`;
   - 1C–1F, 4 i 5: wspólny `wizz-route-schedules.json`, z uwzględnieniem
     obecnego łączenia z wpisami 1A.
4. Dla kroku 2 rekomendowane jest wykorzystanie wspólnego rejestru zamiast
   powiększania osobnej stałej w kodzie. Wydzielić niewielki loader do nowego
   `scripts/wizz_schedules.py`, dostępny dla kroku 2 i kroku 4.
5. Przed usunięciem `WIZZ_DIRECT_SCHEDULES` przenieść do danych również wszystkie
   cztery dotychczasowe wpisy WAW/KTW ↔ TFS. W obecnym wspólnym JSON-ie tych
   czterech wpisów nie ma. Zachować ich dotychczasowe zachowanie i zweryfikować
   dane; samo podpięcie obecnego wspólnego JSON-a zepsułoby stare bezpośrednie Wizz.
6. Nie importować loadera z `collect_step4` do `collect_step2`: krok 4 już
   importuje `wizz_timetable` z kroku 2. Nowy moduł ma uniknąć cyklu importów.
7. Zachować obowiązek przechowywania danych 1A i 1B w ich lokalnych allowlistach.
   Dla powielonych par kontrolować zgodność; ustalić jawne pierwszeństwo źródeł.
   Loader nie może milcząco zmieniać numeru, długości lotu lub obsługi override.
   Obecny loader i wykonawca 1A/1B w ogóle nie obsługują wyjątków godzinowych.
   Jeżeli nowa zweryfikowana para ich potrzebuje, rozszerzyć zarówno odczyt
   danych, jak i rzeczywisty wybór numeru lotu w `collect_step1.collect_wizz_route()`
   oraz dodać test dwóch różnych godzin tej samej pary. Sam wpis w JSON-ie
   nie uruchomi tej obsługi.
8. W 1A/1B zlikwidować możliwość potraktowania aktywnej trasy Wizz bez metadata
   jako prawidłowego zera. Najpierw wykonać zapytanie o pełny zakres regularnych
   lotów, następnie dla aktywnej pary wymagać zweryfikowanych danych technicznych.
   Ponieważ te dwa warianty skanują pełną macierz, nie wolno wymagać fikcyjnych
   rozkładów dla wszystkich nieistniejących rynków.
9. Prawidłowy brak dostępności pozostaje zerem. Aktywny lot bez numeru/czasu ma
   przerwać publikację z jasną informacją, co należy zweryfikować.
10. Przy przeniesieniu zapytania Wizz w 1A/1B przed sprawdzenie schedule
    dodać rozpoznanie poprawnej odpowiedzi `400 InvalidMarket` jako braku rynku,
    tak jak w kroku 2. Obecny wykonawca 1A/1B nie ma tego rozróżnienia i pełny
    iloczyn lotnisk zawiera także nieistniejące rynki. Innych błędów HTTP i
    wyczerpanych retry nie zamieniać w brak dostępności.

Warunek zakończenia: każda aktywowana para Wizz ma komplet obu kierunków,
a brak danych technicznych jest widoczny przed zastąpieniem dobrego feedu.

Przed etapem kolekcji poprawić także wspólną obsługę Ryanaira w 1A–1F:
`collect_step1.collect_ryanair_route()` obecnie przechwytuje dowolny
`RuntimeError` z pobierania i zwraca pustą listę. Rozdzielić prawidłowy, rozpoznany
brak rynku/dostępności od błędu sieci, HTTP lub wyczerpanych ponowień. Błąd ma
dotrzeć do wywołującego kolektora i zablokować publikację całego stagingu.
Dotyczy to również 1D–1F przez wykonawcę low-cost importowany z 1C.
Sprawdzić też limit `200` wyników zapytania Fare Finder w tym helperze: jeśli
odpowiedź może być ucięta, obsłużyć pełne pobranie według mechanizmu źródła
lub jawnie wykryć niekompletność, zanim zostanie ogłoszony pełny skan.

### Etap 5 — poprawić detektor i przejrzeć jego dry-run

1. Użyć wspólnego zakresu z etapu 1 oraz polityki podwójnej roli GDN z etapu 2.
2. Zaktualizować tekst raportu kroku 2, który obecnie wylicza cztery kody.
3. Uruchomić `discover_transfer_routes.py` bez `--apply`, z raportem do `tmp/`.
   Zachować materiał źródłowy/snapshot potrzebny do odtworzenia analizy.
4. Sprawdzić dodatki dla 1A, 3, 4 i obu wariantów 5. Detektor nie obsługuje 1B–1F;
   te pięć wariantów wymaga osobnego przeglądu i zmiany allowlist.
5. Sprawdzić także rozszerzenia już istniejących hubów o GDN, nie tylko całkiem
   nowe rekordy hubów.
6. Uzupełnić metadata Wizz i powtórzyć raport. Jedna niekompletna para może
   obecnie zatrzymać w `pending` całego kandydata; raport musi wyjaśniać tę
   przyczynę. Nie usuwać kontroli kompletności, aby wymusić `ready`.
7. `apply_plan()` obecnie aktualizuje rekordy, strefy, listy discount i liczniki,
   ale nie synchronizuje `scope`, `excluded_endpoints` ani opisów. Dopilnować
   synchronizacji w migracji i sprawdzać ją testem.
8. Zastosować wyłącznie przejrzany zakres dodatków związanych z GDN. Obecne
   `--apply` stosuje cały raport; jeśli zawiera inne zmiany, użyć ograniczonego
   mechanizmu zastosowania albo jawnego patcha źródłowych allowlist.
9. Zachować tryb domyślny bez zapisu i zasadę braku automatycznego usuwania tras.
   Powtórny dry-run/apply na tym samym snapshocie ma być idempotentny.

### Etap 6 — zaktualizować wszystkie dziewięć allowlist

Wszystkie poniższe pliki wymagają przeglądu, nawet jeśli wynik weryfikacji
nie uzasadni dodania GDN do konkretnego huba:

| Plik | Obecny zakres hubów | Wymagana operacja |
| --- | --- | --- |
| `data/binter-transfer-airports.json` | FUE, LPA, MAD, PMI, SVQ, VLC | Dopisać GDN do scope; uzupełnić dowody, lokalne Wizz metadata i ewentualne nowe kwalifikujące się huby. `eligibility_evidence` jest dowodem, a nie limitem skanu. |
| `data/iberia-transfer-airports.json` | MAD | Scope, dowody GDN/przewoźnik, lokalne Wizz metadata, ewentualny nowy hub tylko po potwierdzeniu zniżki. Poprawić tekst „wszystkie cztery”. |
| `data/vueling-transfer-airports.json` | ALC, BCN, BIO, AGP, SCQ, SVQ, VLC | Scope i konkretne `polish_routes` dla GDN; ponowna kontrola OVD/GRX i całej kwalifikującej się siatki Vuelinga. |
| `data/air-europa-transfer-airports.json` | MAD, BIO | Scope i `polish_routes`; nowy hub wymaga weryfikacji oficjalnej trasy i zniżki, a indywidualne dane rejsów i ceny zbiera Google Flights HTTP. |
| `data/volotea-transfer-airports.json` | BIO | Scope i `polish_routes`; ponowna kontrola OVD i pozostałej kwalifikującej się siatki, z oficjalnego źródła. |
| `data/canaryfly-transfer-airports.json` | FUE, LPA | Scope i `polish_routes`; kontrola ACE/SPC/VDE i pozostałej bezpośredniej siatki kwalifikującej się do zniżki. |
| `data/ryanair-transfer-airports.json` | 34 rekordy hubów | Scope i GDN w `airports[].polish_airports` tylko przy potwierdzonym Ryanair; nowe huby, strefy, reguły zniżki, opisy i liczniki. |
| `data/wizzair-transfer-airports.json` | BBU, BUD, FCO, MXP, OTP, SCQ | Scope i potwierdzone GDN w `polish_airports`; metadata obu kierunków; ponowna ocena uwagi o GDN jako hubie, bez automatycznego usuwania jej sensu. |
| `data/mixed-transfer-airports.json` | Wariant A: 19, B: 5 | Scope i osobne dodatki w obu wariantach; zachować stary transfer GDN; poprawić politykę wykluczeń, opisy, listy zniżek i liczniki. |

Dla kroków 3–5 nie wystarcza globalny scope. Ich `polish_airports` przy konkretnym
hubie faktycznie decyduje, jakie odcinki są pobierane i łączone.

Dla 1C–1F `polish_routes[].airlines` też jest regułą wykonania: potwierdzenie
Ryanair nie uprawnia do automatycznego dopisania Wizz na tej samej parze.

W wariancie A kroku 5 Ryanair pozostaje na odcinku Teneryfy, a Wizz na odcinku
Polski. W wariancie B jest odwrotnie. Przypisanie nie zmienia się po odwróceniu
kierunku podróży.

Przy nowym hubie uzupełnić jego strefę w wymaganym formacie, uprawnienie i
mnożnik zniżki, listę kwalifikujących się lotnisk Teneryfy, dowody i datę
faktycznej weryfikacji. Przeliczyć `result_count`, liczniki wariantów,
`unique_transfer_airport_count`, eligible/ineligible i odpowiadające im opisy.
Nie zmieniać daty historycznego źródła tak, jakby zostało sprawdzone ponownie.

Jeżeli nowy zagraniczny hub powoduje pojawienie się nowej waluty źródłowej,
sprawdzić `SOURCE_CURRENCIES` w krokach 3–5, `NBP_SHARED_CURRENCIES` w
`collect_step1.py:44` i obsługę przeliczenia w pozostałych kolektorach.
Komplet walut musi być znany przy pierwszym dziennym pobraniu NBP; cache
niekompletny dla nowej konfiguracji nie może zostać uznany za gotowy.
Samo GDN nie wymaga nowej waluty ani zmiany formatu kursów NBP.

### Etap 7 — upewnić się, że każdy kolektor rzeczywiście skanuje nowy zakres

| Kolektor | Co wykazać przed pobraniem produkcyjnym |
| --- | --- |
| `collect_step1.py` (1A) | Każdy zapisany hub × pięć polskich endpointów × dwa kierunki × dwie linie low-cost; potwierdzone Wizz nie są pomijane bez zapytania. Pełny kalendarz Bintera niezależny od low-cost. |
| `collect_step1b.py` | Analogiczny pełny iloczyn low-cost; użycie własnych Wizz metadata; pełne niezależne dni Iberii, limit Google Flights 2. |
| `collect_step1c.py` | Tylko zatwierdzone `polish_routes`, z GDN tam, gdzie potwierdzone; pełne dni Vuelinga i właściwe źródło cen. |
| `collect_step1d.py` | Wykonawca low-cost z 1C obejmuje jego własną allowlistę GDN; pełne niezależne kalendarze indywidualnych ofert Air Europa z Google Flights. |
| `collect_step1e.py` | Analogiczna obsługa GDN, zapytanie MinPrice o każdą trasę i każdy dzień, puste odpowiedzi odróżnione od błędów. |
| `collect_step1f.py` | Analogiczna obsługa GDN, pełne kalendarze miesięczne i szczegóły wszystkich dostępnych dni Canaryfly. |
| `collect_step2.py` | Dokładnie 20 skierowanych par lotnisk na linię, 40 kombinacji para/linia. Obejmuje GDN ↔ TFN/TFS dla Wizz i Ryanair; brak rynku nie jest zmyślonym lotem. |
| `collect_step3.py` | Pobranie obu kierunków wszystkich zapisanych Ryanair GDN ↔ hub i pełnych odcinków Teneryfy. |
| `collect_step4.py` | Analogicznie Wizz, komplet technicznych rozkładów i wyjątków godzinowych. |
| `collect_step5.py` | Oba warianty, oba kierunki, pełne kalendarze obu linii; dodatkowo istniejąca przesiadka przez GDN. |

W kroku 2 wzrost macierzy wynosi 16 → 20 skierowanych par na linię, czyli 25%.
Nie oznacza to wzrostu całej kolekcji o 25%: dochodzą także nowe huby i liczba
dopasowań między odcinkami. Zachować limity zapytań, zamiast podnosić workers
w celu ukrycia wzrostu czasu pobierania. Powtarzane odcinki w obrębie jednego
skanu deduplikować po przewoźniku, trasie i zakresie, bez użycia wczorajszych cen.

### Etap 8 — UI, linki i dokumentacja

1. W `index.html` dopisać Gdańsk do listy lotnisk w oknie informacyjnym.
   Generowanie tej informacji z rejestru jest opcjonalnym uspójnieniem;
   przebudowa ładowania całej strony nie jest wymagana.
2. Zachować istniejącą etykietę GDN w `app.js`; nie dodawać drugiego wpisu.
3. Sprawdzić dynamiczne opcje GDN w obu kierunkach. Obecnie UI pokazuje
   endpoint tylko wtedy, gdy ma go w wynikach danego kierunku. Brak wyniku
   oznacza brak opcji; pokazanie na stałe lotniska bez wyników byłoby osobną
   zmianą produktu, nie warunkiem dodania piątego endpointu.
4. Kalendarz, wykres, aktywne chipy, reset, zamiana kierunku, sortowanie,
   podświetlenie pięciu zmienionych pól, cache kart i udostępnianie wymagają
   testów regresji. Nie potrzebują osobnej logiki „tylko dla GDN”.
5. `booking_urls.py` obsługuje dowolny prawidłowy kod IATA dla Wizz i Ryanair.
   Zweryfikować GDN jako początek i koniec odcinka. Nie dopisywać GDN do
   kanaryjskich slugów Canaryfly: jego odcinek pozostaje na Wyspach Kanaryjskich.
6. `refresh_booking_urls.py` nie zastępuje pełnej regeneracji wyników.
7. Zaktualizować `AGENTS.md`, kanoniczny dokument i README: pięć endpointów,
   macierz kroku 2, przykłady kierunków 1A–1E i 5, opisy wariantów oraz
   sformułowania „cztery/czterech”. W dokumencie kanonicznym są to m.in.
   linie 16, 99, 119, 151, 182, 216, 265, 332 i 371.
8. Opisy konkretnych tras 1E/1F aktualizować zgodnie z faktycznie zweryfikowaną
   siatką. Nie dopisywać GDN do opisu linii, która nie ma takiego odcinka.
9. W README odróżnić dodanie polskiego endpointu od dodania transferu i opisać
   rejestr, weryfikację siatki, testy oraz etapową publikację całej bazy.
10. Jeżeli zmieni się JS/CSS, podnieść ich wersje w `index.html`. Zmiana samej
    treści HTML nie wymaga wymyślania nowego mechanizmu cache.

Nie zastępować wszystkich wystąpień WAW/WMI/KTW/KRK przez nowy zestaw kodów.
Pojedyncze przykłady linków, historyczne dane i syntetyczne fixture testów
pozostają poprawne. `data/test-results-waw.json` nie jest jedenastym feedem
ładowanym przez stronę i nie służy do dopisywania wyników GDN.

### Etap 9 — testy automatyczne i ręczna akceptacja

Uruchomić całą obecną serię testów i dodać testy istotnych zachowań:

| Obszar / pliki | Wymagane sprawdzenia |
| --- | --- |
| Nowy rejestr i `tests/test_allowlist_metadata.py` | Oczekiwana lista to jawnie pięć zatwierdzonych kodów; GDN ma strefę bez ładowania innych kroków; dziewięć scope zgodnych; dozwolone pary nie wychodzą poza zakres; brak self-route. |
| `tests/test_step2_collector.py` | Zmiana oczekiwanych 16 na 20; jawna obecność wszystkich czterech kierunkowych par GDN/TFN/TFS; każda badana przez obie linie; GDN w obu kierunkach przechodzi budowanie/walidację. |
| Wizz | Aktywne GDN ↔ TFS korzysta z danych rejestru; stare WAW/KTW nadal działają; aktywna nieznana para kończy się błędem; override po godzinie działa; lokalne i wspólne metadata nie przeczą sobie. |
| Puste rynki i błędy low-cost | Wizz `400 InvalidMarket` oznacza brak rynku; 503/wyczerpane retry oznaczają błąd; Ryanair w 1A–1F nie zamienia błędu źródła w `[]`; ewentualne ucięcie odpowiedzi Fare Finder jest wykrywane. |
| `tests/test_step1_collector.py`, `test_step1b_collector.py` | GDN jest rzeczywiście skanowane dla wszystkich zapisanych hubów; brak schedule nie staje się cichym brakiem aktywnego lotu; pełne niezależne kalendarze. |
| `tests/test_step1c_collector.py`–`test_step1f_collector.py` | GDN dozwolone wyłącznie dla zapisanej pary hub/linia; oba kierunki i poprawne zniżki; faktyczny współdzielony wykonawca z 1C otrzymuje właściwą allowlistę. |
| `tests/test_step3_collector.py`–`test_step5_collector.py` | GDN jako endpoint w obu kierunkach, oba warianty mieszane, pełne kalendarze i właściwy przewoźnik na odcinku geograficznym. |
| Rola transferu GDN | Istniejące KRK ↔ GDN ↔ TFS nadal powstaje; GDN jako endpoint działa równocześnie; nie powstaje GDN ↔ GDN ani transfer równy endpointowi. Kontrolować osobno detektor, macierz zapytań i walidację, aby błędne zapytanie nie było wykonywane przed odrzuceniem wyniku. |
| `tests/test_route_discovery.py` | Nowy hub dzięki GDN, rozszerzenie istniejącego huba, braki jednego kierunku Wizz jako pending, wyjątek transferowy GDN, zgodny scope, idempotencja i brak usuwania sezonowych tras. |
| `tests/test_booking_urls.py` | GDN jako origin i destination Wizz/Ryanair; dokładna data i brak parametrów sesji. |
| `tests/test_collection_reliability.py`, `test_wizz_api.py` | Nadal Google Flights max 2, jeden dzienny NBP i dynamiczna wersja API Wizz; błąd źródła nie zastępuje dobrego publicznego zestawu. |
| Regresja starej czwórki | Przy niezmiennych kalendarzach, konfiguracji ich tras i cenach: te same ID, kierunki, kwoty i dopasowania, z uwzględnieniem wyłącznie jawnie zatwierdzonych dodatków. |

Dodać przypadki graniczne: 119/120 i 1440/1441 minut oczekiwania, przejście
przez północ, zmiana czasu, lokalne godziny `Europe/Warsaw` i `Atlantic/Canary`,
przylot następnego dnia oraz początek/koniec skonfigurowanego okna.

Test pełnego pokrycia dat ma zawierać dzień, w którym jedna linia lata,
a druga nie; obie nadal muszą być zapytane o pełny zakres. Brak dostępności
trasy/dnia jest poprawnym wynikiem, błąd HTTP lub niekompletne dane nim nie są.
Nie wymagać dodatnich wyników GDN w każdym wariancie, jeśli poprawny skan ich
nie znalazł. Zachować istniejące zasady walidacji całego feedu.

Testy snapshotów rzeczywistych allowlist aktualizować dopiero po weryfikacji:
zwłaszcza sztywne BIO/WAW/KRK w `test_step1e_collector.py` i FUE/LPA w
`test_step1f_collector.py` oraz `test_allowlist_metadata.py`. Syntetyczne liczniki
w innych testach nie zmieniają się automatycznie tylko dlatego, że zakres
produkcyjny urósł z czterech do pięciu.

Ręczna akceptacja strony na desktopie i telefonie:

- Wybrać GDN jako wylot i jako przylot, zmienić kierunek, użyć X i resetu.
- Sprawdzić oba zestawy aktywnych filtrów i kolory pięciu zmienianych pól.
- Porównać minimum kalendarza/wykresu z ceną wskazanej karty GDN dla czterech
  kombinacji resident/WDC; jeśli zniżka nie przysługuje, cena pozostaje właściwa.
- Kliknąć dzień i słupek przed 100% przygotowania; ma otworzyć się właściwy lot.
- Sprawdzić sortowanie, w tym domyślny najbliższy termin; dogrywanie nie
  przeskakuje z otwartej karty wybranej z kalendarza.
- Wykonać GDN → wszystkie → GDN oraz 6 h → 13 h → 6 h → 13 h i sprawdzić
  ponowne wykorzystanie przygotowanych kart oraz responsywność filtrów.
- Skopiować link lotu GDN, otworzyć go po pełnym odświeżeniu; sprawdzić także
  stary link czterech lotnisk, jeśli lot nadal istnieje w aktualnej bazie.
- Sprawdzić oficjalne linki zakupu odcinków i marker następnego dnia.
- Zmierzyć czas przygotowania i pamięć większej bazy. Obecny batch pięciu kart
  i limity cache pozostają punktem odniesienia; nie podnosić ich automatycznie.

### Etap 10 — wykonać pełną kolekcję do stagingu

1. Ustalić jeden dzień startu według `Atlantic/Canary` i przekazywać go jawnie
   we wszystkich wywołaniach `--from-date`. Nie opierać wspólnego dnia na
   oddzielnych `date.today()` procesów, szczególnie na runnerze w UTC.
2. Użyć tego samego `--days 30`, tego samego zakresu konfiguracji i tego samego
   dziennego cache NBP we wszystkich dziesięciu wywołaniach.
3. Uruchomić kolejno 1A, 1B, 1C, 1D, 1E, 1F, 2, 3, 4, 5. Dla każdego ustawić
   `--output` w katalogu stagingu, zachowując docelową nazwę pliku. Nie dopisywać
   ręcznie lotów do publicznych JSON-ów i nie doklejać starych cen.
4. Każdy proces ma zakończyć się poprawnie. Jeśli którykolwiek wariant zawiedzie,
   przerwać publikację i zachować poprzedni cały działający zestaw.
5. Zapisać raport wykonania: zaplanowane i zakończone trasy, pełne daty obu linii,
   prawidłowe puste odpowiedzi, błędy, wynikowe liczby per krok, wariant,
   kierunek, endpoint, osobno GDN jako transfer. Sama liczba wyników nie dowodzi
   pełnego skanu.

Każdy z obecnych kolektorów ma wymagane opcje, np. szablon wywołania:

```text
.venv/bin/python scripts/collect_step2.py --from-date <DZIEŃ_STARTU> --days 30 --output <STAGING>/step2-results.json
```

To szablon dla wykonawcy, nie polecenie uruchamiane podczas przygotowania planu.
Wszystkie nazwy wyjściowe: `step1-results.json`, `step1b-results.json`,
`step1c-results.json`, `step1d-results.json`, `step1e-results.json`,
`step1f-results.json`, `step2-results.json`, `step3-results.json`,
`step4-results.json`, `step5-results.json`.

### Etap 11 — zweryfikować całą bazę i opublikować spójny komplet

Przed zastąpieniem publicznych plików sprawdzić cały staging:

1. Dziesięć oczekiwanych plików istnieje, poprawnie się parsuje i przechodzi
   właściwą walidację kolektora, także pliki ładowane przez UI jako opcjonalne.
2. Wszystkie mają dokładnie ten sam `period_from` i `period_to`, właściwy
   krok/wariant, poprawny zakres endpointów i metadane źródeł/kursów.
3. Wyniki mają prawidłową trasę i kierunek, połączone lotniska odcinków,
   zgodne godziny, przesiadkę i ceny; każdy odcinek ma trwały booking URL.
4. ID są unikalne w całym zbiorze, a nie tylko w pojedynczym feedzie. Wyjaśnić
   ewentualne powtórzenia; nie usuwać arbitralnie różnych wariantów cenowych.
5. GDN jest obecne w macierzy i raportach wykonanych zapytań nawet tam, gdzie
   nie znalazło lotu. Trasa z brakującym Wizz schedule nie przechodzi jako zero.
6. Sprawdzić zachowanie starej czwórki na utrwalonych wejściach i wyjaśnić różnice
   aktualnego pobrania. Sprawdzić, że stare połączenia przez GDN nie zniknęły
   wskutek nowego zakresu endpointów.
7. Dopiero po przejściu całej walidacji przenieść komplet wygenerowanych plików
   do `data/` i opublikować konfigurację, kod, dokumentację i dane jako jeden
   spójny stan. Nie wdrażać kolejno pojedynczych feedów po sukcesie każdego kroku.
8. Zweryfikować stan wdrożenia i stronę już z docelowej wersji: GDN, kalendarz,
   filtry, link do karty, link zakupu, stare endpointy.
9. Zachować raport wdrożenia i prostą możliwość odtworzenia poprzedniego
   kompletnego stanu. Ewentualne wycofanie obejmuje kod, konfigurację i dane,
   nie pojedynczy losowy JSON. Nie używać destrukcyjnego resetu zmian użytkownika.

Powód walidacji zestawu: `app.js:2003` pokazuje najnowsze `generated_at`, ale
`period_from/period_to` liczy jako przecięcie zakresów wszystkich wczytanych
feedów. Stary opcjonalny feed może zawęzić kalendarz mimo świeżego napisu
„Aktualizacja”. Wdrożenie GDN musi wykluczyć taką mieszaną bazę.

Nie jest konieczne przebudowanie całego schematu feedów. Wspólny identyfikator
uruchomienia/wersji scope może być pomocnym rozszerzeniem, jeśli wykonawca
potrzebuje automatycznie potwierdzać spójność; powinien być zgodny z obecnym UI.

## 4. Wymagania dla przyszłego GitHub Actions

W badanym stanie nie ma workflow do poprawienia. Jeżeli podczas realizacji
workflow już powstanie, sprawdzić go według poniższych zasad. Tworzenie całej
automatyzacji nie jest wymagane tylko po to, aby dodać GDN.

- Czytać ten sam rejestr endpointów i te same zatwierdzone allowlisty.
- Wyznaczyć jeden dzień/okno w czasie `Atlantic/Canary` i przekazać je wszystkim
  procesom, niezależnie od strefy maszyny runnera.
- Instalować `scripts/requirements-flight-collector.txt`, uruchomić testy i
  zbierać dziesięć feedów w stagingu, najlepiej w jednym jobie.
- W wielu jobach przekazać ten sam dzienny snapshot NBP jako artefakt.
- Zachować Google Flights max 2 łącznie; oddzielne równoległe joby 1B/1C
  nie mogą obchodzić tego limitu.
- Zwiększyć w razie pomiarów budżet czasu pracy, bez zwiększania na ślepo
  równoległości i bez skracania kalendarza nowej siatki.
- Detektor tras pozostaje osobnym zadaniem. Odświeżenie cen nie uruchamia
  automatycznie `--apply` ani nie dopisuje tras.
- Przechowywać raporty tras, błędów i kompletności jako artefakty.
- Publikować dopiero po walidacji całego zestawu; błąd dowolnego źródła
  nie powoduje wdrożenia częściowej nowej bazy.

## 5. Kryteria zakończenia dla Codexa

- [ ] Jeden kanoniczny zakres WAW/WMI/KTW/KRK/GDN; detektor i kolektory zgodne.
- [ ] GDN ma `Europe/Warsaw` także przy samodzielnym uruchomieniu każdego kroku.
- [ ] Przejrzano wszystkie dziewięć allowlist i całą kwalifikującą się siatkę,
      w tym huby wcześniej odrzucone wyłącznie z powodu starej czwórki.
- [ ] Każda aktywowana para GDN/hub/linia jest potwierdzona; sezonowość i
      brak dostępności odróżniono od błędu lub braku weryfikacji.
- [ ] Wizz ma metadata obu kierunków; krok 2 widzi GDN oraz zachowuje dotychczasowe
      cztery bezpośrednie wpisy WAW/KTW; 1A/1B nie gubią aktywnej trasy po cichu.
- [ ] GDN działa jako endpoint i zachowuje dotychczasową rolę przesiadki;
      brak self-route i niezamierzonej zmiany polityki innych polskich lotnisk.
- [ ] Krok 2 sprawdza 20 skierowanych par na linię; wszystkie kroki skanują
      pełne okna obu linii i obu kierunków.
- [ ] Zniżki, źródła, limit Google, NBP, linki i reguły przesiadek zachowane.
- [ ] Testy starej czwórki i nowe przypadki GDN przechodzą; brak regresji ID.
- [ ] UI z GDN, kalendarz, wykres, filtry, cache i udostępnianie sprawdzone.
- [ ] Dokumentacja i opis zakresu na stronie zawierają piąte lotnisko.
- [ ] Dziesięć aktualnych feedów z tego samego okna wygenerowano, zwalidowano
      razem i opublikowano w jednym kompletnym stanie.
- [ ] Raport końcowy wymienia liczbę tras i wyników GDN/stara czwórka według
      kroku, wariantu i kierunku oraz wszystkie nierozstrzygnięte pozycje.

Pozycja `pending` nie jest wdrożoną trasą. Jeżeli pozostają istotne braki
w weryfikacji lub metadata, raport ma je wymienić wprost; nie ogłaszać pełnego
pokrycia „wszystkich możliwych połączeń GDN”, gdy część wymaganych tras pominięto.

## 6. Kontrole wykonane przy przygotowaniu planu

- Przejrzano kanoniczne instrukcje, wszystkie dziewięć allowlist, rejestry Wizz,
  kolektory 1A–1F i 2–5, detektor, wspólne moduły, testy, README i kod strony.
- Sprawdzono lokalne metadane wszystkich dziesięciu publicznych feedów oraz
  wystąpienia GDN jako endpointu i przesiadki.
- Uruchomiono `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m unittest discover -s tests`:
  **78 testów, OK**. To stan bazowy, nie test wykonanego wdrożenia GDN.
- Nie wykonano kolekcji cen, live discovery, zmian źródłowych allowlist,
  commitów ani publikacji. Jedynym nowym plikiem jest niniejszy plan.
- Zastane nieśledzone obrazy `assets/poland-tenerife-ticket-v1.png` i
  `assets/poland-tenerife-ticket-v3.png` pozostawiono bez zmian.
