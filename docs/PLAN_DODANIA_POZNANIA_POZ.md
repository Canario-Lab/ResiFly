# Plan dodania Poznania (POZ) jako siódmego polskiego lotniska ResiFly

Dokument wykonawczy do późniejszej realizacji przez Codexa. Przygotowany
**23 października 2026 r.** na podstawie lokalnego repozytorium w stanie
`1d3134ca60152d51aa0eca0c86828ea3d8a2d2e1`, po wdrożeniu Wrocławia.

**Status: wdrożone lokalnie 23.10.2026 na polecenie użytkownika;
po pierwszym lokalnym odbiorze użytkownik osobno autoryzował publikację
całego pakietu na GitHub. Odbiór wizualny pozostaje otwarty.** Wynik i dowody:
[`WDROZENIE_POZNANIA_POZ.md`](WDROZENIE_POZNANIA_POZ.md).
Poniższy opis punktu wyjścia dokumentuje moment przygotowania planu:
nie sprawdzano wtedy na żywo siatki Poznania, nie pobierano nowych cen
i nie zmieniono publicznych feedów.
Żadna wymieniona niżej pozycja do audytu nie oznacza potwierdzonej trasy POZ.
Przed wdrożeniem ponownie odczytać aktualne instrukcje, HEAD i konfigurację.

Plan zastępuje dla tego rozszerzenia historyczny punkt wyjścia planu WRO,
ale nie przepisuje historii GDN/WRO. Wiążące pozostają `AGENTS.md`,
`docs/FIVE_STEP_FLIGHT_SEARCH.md` i `docs/COLLECTION_RELIABILITY.md`.
Raport WRO: [WDROZENIE_WROCLAWIA_WRO.md](WDROZENIE_WROCLAWIA_WRO.md).

## 1. Cel, granice zadania i warunki niezmienne

Docelowy rejestr, z zachowaniem kolejności dotychczasowej szóstki:
**WAW, WMI, KTW, KRK, GDN, WRO, POZ**. Nowy wpis:

```json
{ "iata": "POZ", "name_pl": "Poznań", "timezone": "Europe/Warsaw" }
```

Obsłużyć POZ → TFS/TFN i TFS/TFN → POZ, bezpośrednio oraz z jedną
przesiadką, we wszystkich wariantach, dla których potwierdzono oba odcinki.
Nadal jest **pięć głównych kroków**, sześć wariantów 1A–1F i **dziesięć
feedów**. Nie tworzyć kroku 6 ani oddzielnej bazy Poznania.

Zachować:

- Pełne niezależne kalendarze każdej zapisanej trasy i przewoźnika w obu
  kierunkach, zanim zostaną dopasowane przesiadki. Nie wyznaczać dni jednej
  linii na podstawie lotów drugiej. Canaryfly: najpierw pełne miesięczne
  kalendarze, następnie szczegóły dostępnych dni.
- `--days 30` to dzień startu oraz 30 kolejnych dni, **31 dat włącznie**.
  Nie zmieniać tej semantyki. Każdy odcinek mieści się w ustalonym oknie.
- Jedna przesiadka, **120–1440 minut**, poprawne lokalne daty i strefy.
- Wszystkie ceny w danych; filtrowanie wyłącznie na stronie. Zachować
  osobne wartości regularne, rezydenckie i WIZZ Discount Club.
- Domyślne Polska → Teneryfa, **1000 zł**, **6 h**, najbliższy termin.
  Udostępniony lot nadal przywraca swój kierunek i ustawienia.
- Jeden dzienny zestaw kursów NBP, z datą uruchomienia w `Atlantic/Canary`.
  Google Flights HTTP maksymalnie **dwa równoległe zapytania łącznie**,
  także podczas retry i technicznej weryfikacji Wizz.
- Ryanair wyłącznie Google Flights HTTP, indywidualne rejsy FR/RK; żadnego
  powrotu do Fare Finder, minimum dnia ani starego API cenowego.
- Binter i Canaryfly: oficjalne końcowe kwoty `booking_getImports`.
  Pozostałe kwalifikujące się linie: wspólna reguła niedyskontowanych opłat.
- Trwały link zakupu na każdym odcinku, bez tokenów, cookies i sesji.
- Dotychczasowe trasy, rozkłady i wyjątki obecnych sześciu endpointów.
  Na identycznych wejściach mają pozostać te same wyniki i ID. Nowe pobranie
  może naturalnie zmienić ceny, dostępność oraz liczbę propozycji.
- Dokładnie istniejący wyjątek **GDN jako transfer w 5B wyłącznie do KRK**.
  Nie dopuszczać przez to POZ–GDN ani POZ–WRO, samoprzesiadek lub POZ–POZ.
- Najpierw staging i komplet raportów; dopiero potem lokalna podmiana.
  Poprzednie polecenie publikacji WRO nie jest zgodą na wdrożenie lub push POZ.

## 2. Potwierdzony punkt wyjścia po WRO

| Obszar | Stan zastany i znaczenie dla POZ |
| --- | --- |
| Rejestr | `data/search-airports.json` zawiera sześć endpointów i jedyny wyjątek GDN/5B/KRK. POZ brak. |
| Allowlisty | Wszystkie dziewięć `*transfer-airports.json` ma scope identyczne z rejestrem sześciu. Samo scope nie dopisuje tras. |
| Wizz POZ | W `data/wizz-route-schedules.json` brak par zawierających POZ. Numerów i czasów nie wolno kopiować z WRO. |
| 1A/1B | `collect_step1.collect_low_cost_legs()` sprawdza wszystkie huby × wszystkie polskie endpointy × oba kierunki × obie linie. `eligibility_evidence` jest dowodem siatki, nie filtrem tej macierzy. |
| 1C–1F | Zapytania low-cost wynikają z konkretnych `polish_routes` i `airlines`. 1D–1F współdzielą wykonawcę z 1C. |
| Krok 2 | 24 skierowane pary na linię, 48 kombinacji trasa–linia; pełna macierz sześciu polskich i dwóch teneryfskich lotnisk. |
| Kroki 3–5 | Zapytania wynikają z `polish_airports` konkretnych hubów i wariantów. A i B muszą być sprawdzone oddzielnie. |
| Techniczne dane Wizz | Wspólny `scripts.wizz_schedules`; obsługiwane wyjątki godziny, dnia tygodnia i konkretnej daty. Pierwszeństwo: data → dzień tygodnia → godzina → baza. |
| Weryfikator Wizz | `verify_wizz_expansion_schedules.py` ma już `--endpoint`; wybór pochodzi z aktualnego rejestru. POZ zadziała dopiero po jego rozszerzeniu i uruchomieniu nowego procesu. |
| Generator konfiguracji | `build_gdn_config_patch.py`, pomimo historycznej nazwy, ma `--endpoint`, kopie baseline i wyjście do przeglądu. Ma ograniczenia opisane w sekcji 7. |
| Audyt sieci | `audit_airport_expansion.py` zapisuje siatki, ale końcowy wydruk nadal wskazuje GDN, a Binter badany jest tylko dla istniejących hubów. Nie poświadcza pełnego audytu nowych hubów POZ. |
| Runner | `collect_five_steps.py` nadaje świeży cache Ryanaira według run ID, kontroluje daty/hash konfiguracji i promuje 20 plików z backupem/rollbackiem. Tego nie trzeba wdrażać ponownie. |
| Raport endpointów | Runner ma już `endpoint_directions` i `endpoint_variants` dla całego rejestru. POZ powinien pojawić się automatycznie; zachować pola GDN i licznik GDN jako transferu. |
| UI | Selektory powstają z wyników; nazwa miasta jest w `app.js.airportLabels`, lista informacyjna w `index.html`. |
| Automatyzacja | Brak `.github/workflows` w zastanym repozytorium. Nowy workflow nie jest częścią dodania POZ. |

Obecny kompletny batch ma okno **2026-10-23–2026-11-22** i run ID
`efa7d3ee-f865-4353-84a7-90b73f3eb21e`. Potwierdzono zgodność dziesięciu
sidecarów i osadzonych raportów, łącznie **14 150 propozycji**. POZ nie
występuje jako endpoint. To baseline, nie prognoza liczby wyników po zmianie.

| Feed | Wyniki baseline | Bazowy plan route/day | Pokrycie zapisane w feedzie |
| --- | ---: | ---: | ---: |
| 1A | 2811 | 5208 | 5208 |
| 1B | 2209 | 868 | 868 |
| 1C | 2623 | 3038 | 3038 |
| 1D | 868 | 744 | 744 |
| 1E | 8 | 248 | 248 |
| 1F | 222 | 434 | 558 |
| 2 | 208 | 1488 | 1488 |
| 3 | 4290 | 9610 | 9610 |
| 4 | 204 | 1302 | 1302 |
| 5 | 707 | 5084 | 5084 |

1F dodaje 124 wymagane sprawdzenia szczegółów dostępnych dni Canaryfly;
nie jest to brak lub nadmiar zapytań. Liczniki pokrycia nie są liczbą
rzeczywistych requestów HTTP: Wizz pyta okresowo, Ryanair współdzieli cache.

## 3. Etap 0 — zabezpieczyć stan sześciu lotnisk

1. Odczytać bieżący `AGENTS.md` i oba kanoniczne dokumenty kolekcji.
   Sprawdzić `git status`, HEAD, gałąź i niezwiązane zmiany użytkownika.
2. Dopiero przy poleceniu wdrożenia pracować lokalnie, np. na
   `codex/add-poznan-poz`. Nie robić pull/reset lub nadpisania brudnych plików
   w celu dopasowania do historycznego hasha z niniejszego planu.
3. **Przed zmianą rejestru** zabezpieczyć sześć endpointów: kod, konfigurację,
   wspólny i lokalne rozkłady Wizz, dziesięć feedów i dziesięć sidecarów.
   Zapisać obecność/brak każdego pliku. Nie dorabiać raportów do starych cen.
4. Użyć osobnego katalogu `tmp/poz-expansion/`; nie wznawiać katalogów GDN/WRO.
   Zachować baseline, snapshoty, materiał techniczny, logi, raport decyzji
   i podsumowanie konfiguracji. Bez tokenów lub danych sesji.
5. Zapisać liczby wyników per endpoint/kierunek/wariant oraz osobno GDN jako
   transfer. Zrobić porównywalne, niezmienne fixture wejściowe dla regresji.
6. Uruchomić bazowe testy offline i sprawdzić, że zastana baza przechodzi
   walidację dla jej dat oraz konfiguracji. Przy późniejszej dacie nie
   poprawiać historycznego `generated_at`, by ominąć kontrolę świeżości.

Odbiór etapu: istnieje odtwarzalny baseline i wiadomo, co należy do migracji.

## 4. Etap 1 — rejestr siedmiu i polityka polskich transferów

1. Dopisać POZ po WRO w `data/search-airports.json.polish_airports`.
   Nie tworzyć alternatywnej listy siedmiu lotnisk w kolektorach.
2. Pozostawić TFN/TFS i `endpoint_transfer_exceptions` bez zmian.
3. Doprowadzić `scope.polish_airports` wszystkich dziewięciu allowlist do
   zgodności z rejestrem, nawet jeżeli dany wariant nie zyska trasy POZ.
4. Uaktualnić bieżące instrukcje projektu do siedmiu endpointów. Historyczne
   raporty i plany GDN/WRO zachować jako historię, nie przepisywać ich liczb.
5. Uruchomić nowe procesy. `scripts.search_airports` oraz część rejestrów
   Wizz ładuje dane przy imporcie; stary proces nie zobaczy nowego pliku.
6. Sprawdzić, że `validate_polish_transfer` i detektor odrzucają POZ jako
   niezatwierdzony hub, POZ–POZ i POZ przez GDN/WRO. Dodatni test starego
   KRK ↔ GDN ↔ TFS pozostaje obowiązkowy.
7. Zaktualizować `selection_method.excluded_endpoints` zgodnie z polityką
   wariantu; w mieszanym kroku zachować precyzyjny wyjątek GDN. Nie traktować
   lotu krajowego z POZ jako automatycznej zgody na nową rolę transferową.

Odbiór etapu: kolektory, detektor i planner pokrycia widzą ten sam rejestr
siedmiu, bez niezamierzonego rozszerzenia ról obecnych endpointów.

## 5. Etap 2 — pełny audyt siatki POZ, przede wszystkim przesiadek

To jednorazowe rozszerzanie konfiguracji, nie zwykłe odświeżenie cen.
Nie kopiować tras WRO lub GDN. Nie zakładać, że każda linia lata przez te
same lotniska, ani że brak dzisiejszego lotu oznacza brak trasy sezonowej.

1. Zebrać aktualne **oficjalne** siatki Ryanaira i Wizz do/z POZ, wraz z
   dokładnymi IATA, źródłem i datą. Oficjalna siatka Ryanaira jest właściwym
   źródłem tras, mimo że jego ceny pobiera Google. Nie utożsamiać np. różnych
   lotnisk Mediolanu, Londynu lub Bukaresztu.
2. Sprawdzić POZ ↔ TFN i POZ ↔ TFS dla obu linii; produkcyjna macierz kroku
   2 ma pytać te kombinacje także przy braku publikowanego rynku.
3. Przeciąć siatkę POZ z bezpośrednimi trasami z/do obu lotnisk Teneryfy.
   Audyt obejmuje **istniejące huby, całkiem nowe huby i dawne wykluczenia
   wynikające jedynie z braku dalszego odcinka do Polski**.
4. Dla 1B–1F zrobić osobny przegląd właściwych przewoźników. Detektor
   obsługuje 1A i 3–5; nie potwierdza Iberii, Vuelinga, Air Europy,
   Volotei ani Canaryfly.
5. Oddzielić potwierdzoną trasę, sezonową/przyszłą, poprawnie stwierdzony
   brak rynku, brak technicznych danych Wizz i awarię źródła. Nie zamieniać
   błędu GraphQL/HTTP w pustą listę, również podczas discovery.
6. Gdy zbiorcze źródło Bintera zawiedzie, zachować sukcesy Ryanair/Wizz i
   raport awarii, ale nie przedstawiać `routes.binter=[]` jako dowodu braku
   połączeń. Nowe huby weryfikować oficjalnymi źródłami tras Bintera;
   istniejąca allowlista nie dowodzi pełnego przeglądu nowej siatki POZ.
7. Ponownie zbadać OVD/GRX dla Vuelinga, OVD i pozostałą siatkę Volotei oraz
   ACE/SPC/VDE i pozostałe bezpośrednie trasy Canaryfly. To kandydaci do
   weryfikacji, **nie trasy Poznania zatwierdzone w tym dokumencie**.
8. Zachować wykluczenia merytoryczne: np. FNC nie spełnia reguły kanaryjskiej
   bonifikaty 1A. Oferta partnera na stronie przewoźnika nie jest dowodem
   bezpośredniego rejsu tej linii.

### Macierz decyzji dla każdego wariantu

| Wariant | Warunek dodania POZ |
| --- | --- |
| 1A | Bezpośredni kwalifikujący się Binter TFN/TFS ↔ hub oraz Ryanair lub Wizz hub ↔ POZ. |
| 1B | Bezpośrednia kwalifikująca się Iberia/Express TFN/TFS ↔ hub oraz właściwe low-cost do POZ. |
| 1C | Potwierdzony na stronie tras Vuelinga odcinek Teneryfa ↔ hub oraz konkretna linia hub ↔ POZ. Aena tylko pomocniczo. |
| 1D | Oficjalna trasa Air Europa Teneryfa ↔ hub oraz low-cost do POZ; nie zmieniać źródła cen z Google. |
| 1E | Oficjalna bezpośrednia Volotea Teneryfa ↔ hub i low-cost do POZ. Sprawdzić stronę tras i MinPrice. |
| 1F | Oficjalny bezpośredni Canaryfly TFN ↔ hub i low-cost do POZ; nie dopuszczać dodatkowej przesiadki wewnętrznej Canaryfly. |
| 3 | Ryanair Teneryfa ↔ hub i Ryanair hub ↔ POZ. |
| 4 | Wizz Teneryfa ↔ hub i Wizz hub ↔ POZ, z kompletem technicznych danych obu odcinków. |
| 5A | **Ryanair na odcinku Teneryfy, Wizz na odcinku POZ.** |
| 5B | **Wizz na odcinku Teneryfy, Ryanair na odcinku POZ.** |

Przy odwróceniu podróży linie pozostają przypisane do tych samych
geograficznych odcinków. Audyt A nie zastępuje B. Dla każdego kandydata
zapisać krok/variant, hub, właściwe TFN/TFS, obie linie, kierunki, dowody,
status i uzasadnienie. Oddzielić dodatki POZ od niezwiązanych propozycji
dla obecnej szóstki; nie aktywować całego discovery bez przeglądu.

`edge_exists()` uznaje obecność jednego kierunku za dowód siatki. To nie
tworzy rejsu powrotnego: ceny i kalendarze obu kierunków pobiera się osobno.

## 6. Etap 3 — numery, czasy i wyjątki Wizz dla nowych par

1. Użyć istniejącego `scripts/verify_wizz_expansion_schedules.py` z jawnym
   `--endpoint POZ`. Po rozszerzeniu rejestru parametr jest już obsługiwany;
   nie zmieniać domyślnego GDN w kodzie na POZ i nie tworzyć drugiego loadera.
2. Utworzyć odrębny materiał `tmp/poz-expansion/verified-wizz-schedules.json`.
   Sprawdzić tożsamość endpointu, snapshotu i okna. Nie wznawiać pliku WRO
   przez zmianę nazwy. Generator patcha kontroluje endpoint/datę snapshotu,
   więc zgodność pełnego okna trzeba również jawnie skontrolować.
3. Zweryfikować oba kierunki każdej potrzebnej pary POZ–hub, aktywne godziny,
   numery i czasy blokowe. Uwzględnić aktywne POZ–TFN/TFS, gdy wystąpią.
   Dla nowych hubów w 4/5B sprawdzić także oba kierunki **hub–Teneryfa**.
4. Porównać listę `required_routes()` z całą zatwierdzaną konfiguracją,
   również macierzą 1A/1B. Nie uznawać samego ukończenia helpera za dowód,
   że każdy potrzebny odcinek i port Teneryfy został uwzględniony.
5. Dane techniczne brać z ofert Wizz w Google Flights HTTP, bez realnej
   przeglądarki i bez przenoszenia cen do feedu Wizz. Oficjalne `timetableV2`
   pozostaje źródłem bieżących dat/odlotów i regular/WDC; jego wersję API
   nadal rozwiązuje `scripts.wizz_api`.
6. Weryfikator może wybrać dni na podstawie kalendarza **tej samej linii**.
   Brak wyprzedanej oferty Google może wymagać technicznego dowodu w innej
   dacie. Nie pożyczać ceny i nie traktować sąsiedniego dnia jako dowodu
   identycznego czasu w każdy dzień bez sprawdzenia reguły obowiązywania.
7. Dla potwierdzonych tras sezonowych można użyć jawnego
   `--inactive-probe-date YYYY-MM-DD`. Dowód z przyszłości dotyczy numeru
   i czasu, nie dostępności lub ceny w bieżących 31 dniach. Zachować osobno
   status bieżącego rynku i przyszły dowód.
8. Uzupełnić wspólny `data/wizz-route-schedules.json`, a dla potrzeb 1A/1B
   także ich lokalne `wizz_route_schedules` i odpowiadające wyjątki.
9. Rozwiązywać różnice tej samej godziny przez istniejące pola:
   `flight_number_overrides_by_departure_time`,
   `flight_number_overrides_by_departure_weekday_and_time` (ISO 1–7),
   `flight_number_overrides_by_departure_date_and_time`. Nie zastępować
   konfliktu wyborem pierwszego lub najczęstszego czasu bez reguły/dowodów.
   Każda obserwacja ma odtwarzać się dokładnie przez `resolve_schedule()`.
10. Zachować WRO–LPA: potwierdzone 13:45 z innym czasem blokowym w poniedziałki
    niż w środy/piątki. To regresja, a nie wzorzec godzin dla Poznania.
11. Nowy aktywny odcinek bez numeru/czasu nadal ma blokować zapis.
    Poprawny Wizz `InvalidMarket` nie jest tym samym co 503, timeout lub
    wyczerpane retry. Nie usuwać wymaganej trasy dla obejścia awarii.

Przykład do uruchomienia **dopiero przy wdrażaniu**, po przygotowaniu
snapshotu i rejestru POZ (znaczniki zastąpić rzeczywistymi danymi):

```text
.venv/bin/python scripts/verify_wizz_expansion_schedules.py --endpoint POZ --snapshot tmp/poz-expansion/network-snapshot.json --from-date YYYY-MM-DD --days 30 --output tmp/poz-expansion/verified-wizz-schedules.json
```

## 7. Etap 4 — selektywna konfiguracja wszystkich dziewięciu allowlist

### Zastane huby, nie deklarowana lista połączeń POZ

| Plik w `data/` | Zastane huby | Co uzupełnić po weryfikacji |
| --- | --- | --- |
| `binter-transfer-airports.json` | FUE, LPA, MAD, PMI, SVQ, VLC | Scope, dowody `eligibility_evidence`, właściwe lokalne Wizz dane. Pełna macierz low-cost nadal niezależna od evidence. |
| `iberia-transfer-airports.json` | MAD | Scope, evidence i lokalne Wizz dane; nowy hub tylko po osobnym oficjalnym potwierdzeniu. |
| `vueling-transfer-airports.json` | ALC, BCN, BIO, AGP, SCQ, SVQ, VLC | Konkretne POZ w `polish_routes` z właściwą listą `airlines`, strefa i trasa Teneryfy. |
| `air-europa-transfer-airports.json` | MAD, BIO | Jak wyżej; zachować accepted airline codes i wyłączne Google źródło rejsów/cen. |
| `volotea-transfer-airports.json` | BIO | Potwierdzone POZ/linia, możliwe nowe huby; sezonowe WRO–BIO i stare trasy bez zmian. |
| `canaryfly-transfer-airports.json` | FUE, LPA | Potwierdzone POZ/linia i nowe huby tylko dla bezpośredniego Canaryfly; końcowe imports/DC bez zmian. |
| `ryanair-transfer-airports.json` | 34 huby | POZ w `airports[].polish_airports` właściwych hubów; ewentualne nowe huby, strefy i uprawnienia. |
| `wizzair-transfer-airports.json` | BBU, BUD, FCO, MXP, OTP, SCQ | Potwierdzone POZ i techniczne dane obu odcinków; stare pozycje sezonowe zachować. |
| `mixed-transfer-airports.json` | A: 19 hubów; B: 6; 22 różne | Osobne dozwolone pary A/B, strefy, rabaty i liczniki. GDN w B nadal tylko KRK. |

Nowy hub wymaga kompletu: IATA, nazwy, IANA timezone, właściwych TFN/TFS,
konkretnych polskich endpointów i linii, uprawnienia/mnożnika rezydenta,
dowodów i ewentualnej reguły opłat. Nie dopisywać go do wszystkich wariantów.
Brak kwalifikującego się POZ w jednym z wariantów jest dopuszczalny, ale
musi być uzasadniony audytem, nie pominięciem tej części zadania.

### Wykorzystanie obecnych narzędzi i ich ograniczenia

1. `discover_transfer_routes.py` uruchamiać najpierw bez `--apply`.
   Snapshot z pełnego audytu musi być zachowany jako odrębny plik; sam
   `--report` zapisuje raport decyzji, nie zastępuje snapshotu sieci.
2. `audit_airport_expansion.py` wymaga przynajmniej poprawienia wydruku
   endpointu i rozszerzenia przeglądu Bintera poza dotychczasowe huby, jeśli
   ma poświadczać nową siatkę. Można użyć jego funkcji do audytu, ale nie
   prezentować starego zakresu jako pełnej kontroli POZ. Błąd źródła musi
   zostać jawny; częściowy snapshot nie może udawać kompletnego.
3. `build_gdn_config_patch.py --endpoint POZ` można wykorzystać już teraz
   po rozszerzeniu rejestru. `--baseline-directory` wskazuje zabezpieczoną
   konfigurację szóstki; `--output-directory` zapisuje kopie do przeglądu
   poza `data/`. Nie podawać w nim katalogu z publicznymi feedami jako wyjścia.
4. Helper 1A–1F obecnie **iteruje tylko po istniejących `airports`**.
   Sam nie doda nowego huba Iberii/Vuelinga/Air Europy/Volotei/Canaryfly
   ani nowego huba Bintera do tej części konfiguracji. Takie rekordy trzeba
   przygotować osobno na podstawie audytu i sprawdzić validatorami.
5. Przy istniejącym hubie porównać również pełne `tenerife_airports`:
   dopisanie POZ bez nowo zweryfikowanego TFN lub TFS może nadal zgubić
   trasę. Obecny helper 3–5 przy znalezionym hubie dopisuje polskie lotnisko,
   nie scala automatycznie wszystkich pól kandydata.
6. Nowy odcinek Teneryfy we wspólnym hubie może poszerzyć także trasy starej
   szóstki. Nie robić tego milcząco. Jeżeli ograniczenie ma być per endpoint,
   trzeba jawnie opisać i przetestować odpowiednie mapowanie w danych;
   nie tworzyć duplikatów tego samego IATA ignorowanych przez wykonawcę.
   Niezwiązane rozszerzenia starej szóstki wypisać osobno do decyzji.
7. Usunąć z helpera założenia tekstowe „pięć → sześć”. Wyrażenie do list
   kodów i opisy muszą obsłużyć POZ oraz aktualny rejestr bez zostawienia
   napisów o sześciu lotniskach lub podwojenia POZ po ponownym uruchomieniu.
8. Zachować historyczne źródła/daty. Dopisać rzeczywisty audyt POZ, a nie
   przedstawiać wszystkich dawnych pozycji jako sprawdzonych ponownie.
   `verified_on` całego pliku nie zastępuje dowodów konkretnej nowej pary.
9. Stosować patch przez `apply_patch` po przeglądzie wygenerowanych kopii.
   Zachować całoplikowe/jednoznaczne konteksty JSON: przy WRO krótkie
   powtarzalne fragmenty dopisały lotnisko do niewłaściwego huba. Sprawdzić
   **dokładne zbiory** POZ/variant/hub/linia po zastosowaniu, nie tylko JSON syntax.
10. Przeliczyć liczniki hubów, listy kwalifikujące/niekwalifikujące do zniżki,
    `airport_timezones`, opisy i scope. Ponowny helper nie może powielać wpisów
    ani usuwać sezonowych WRO/GDN lub wyjątków rozkładu.

Szablony do późniejszego użycia:

```text
.venv/bin/python scripts/discover_transfer_routes.py --snapshot tmp/poz-expansion/network-snapshot.json --report tmp/poz-expansion/discovery-report.json

.venv/bin/python scripts/build_gdn_config_patch.py --endpoint POZ --snapshot tmp/poz-expansion/network-snapshot.json --schedules tmp/poz-expansion/verified-wizz-schedules.json --from-date YYYY-MM-DD --days 30 --baseline-directory tmp/poz-expansion/baseline/data --output-directory tmp/poz-expansion/configuration-review
```

Przygotowanie kopii przez helper nie oznacza akceptacji całości discovery.
Nie używać bez przeglądu `--apply`, które obejmuje wszystkich gotowych
kandydatów, nie tylko Poznań. Zachować dotychczasowe rekordy szóstki.

## 8. Etap 5 — rzeczywiste macierze kolektorów i plan pokrycia

| Kolektor | Wymagany zakres po dodaniu POZ |
| --- | --- |
| 1A `collect_step1.py` | Każdy hub × 7 endpointów × 2 kierunki × Ryanair/Wizz, nawet przy pustym rynku. Oddzielnie każdy dzień Bintera i końcowe imports wybranych taryf. |
| 1B `collect_step1b.py` | Taka sama niezależna macierz low-cost z lokalnymi danymi Wizz; osobno pełne dni Iberii/Express. |
| 1C `collect_step1c.py` | Wszystkie zapisane `polish_routes` z właściwymi liniami, w tym POZ; niezależny pełny Vueling. |
| 1D `collect_step1d.py` | Własna allowlista przekazana do współdzielonego wykonawcy z 1C; pełne indywidualne oferty Air Europa. |
| 1E `collect_step1e.py` | Własne zapisane low-cost i każdy dzień Volotei na każdej trasie, oba kierunki. |
| 1F `collect_step1f.py` | Własne low-cost; pełne miesięczne kalendarze Canaryfly, szczegóły wszystkich dostępnych dni i końcowe kwoty. |
| 2 `collect_step2.py` | 28 skierowanych par na linię, **56 kombinacji trasa–linia**, w tym wszystkie cztery skierowane pary POZ/TFN/TFS dla obu linii. |
| 3 `collect_step3.py` | Wszystkie zatwierdzone Ryanair POZ–hub i hub–Teneryfa w obu kierunkach, wszystkie daty, FR/RK. |
| 4 `collect_step4.py` | Wszystkie zatwierdzone Wizz na obu odcinkach, regular/WDC i kompletny resolver rozkładu. |
| 5 `collect_step5.py` | Osobne A i B, linie przypisane geograficznie, pełne kalendarze przed dopasowaniem. |

Przy niezmienionych obecnych hubach i 31 datach:

| Zakres | Przed POZ | Po POZ |
| --- | ---: | ---: |
| Krok 2: kombinacje trasa–linia | 48 | 56 |
| Krok 2: pozycje pokrycia | 1488 | 1736 |
| 1A low-cost: kombinacje trasa–linia | 144 | 168 |
| 1A: całe pokrycie z Binterem | 5208 | 5952 |
| 1B low-cost: kombinacje trasa–linia | 24 | 28 |
| 1B: całe pokrycie z Iberią | 868 | 992 |

To wzrost macierzy kroku 2 o **16,7%**, nie prognoza wzrostu wszystkich
wyników, czasu lub liczby requestów. Nowe huby, linie, porty Teneryfy i
liczba dopasowań zmieniają koszt niezależnie. Po ostatecznej konfiguracji
przeliczyć wszystkie dziesięć planów przez
`scripts.collection_coverage.expected_queries()`, przed pobieraniem.

Pusty poprawnie sprawdzony dzień POZ musi mieć wpis `checked` z zerem,
nie brak sprawdzenia. Oczekiwania nie mogą powstać z listy znalezionych
lotów. Canaryfly dokłada obowiązek szczegółów po kompletnym kalendarzu.

## 9. Źródła, opłaty rezydenckie, waluty i linki

Nie zmieniać polityki cen podczas rozszerzania endpointu:

| Linia | Dane bieżących rejsów/cen | Rezydent |
| --- | --- | --- |
| Ryanair/Ryanair UK | Google Flights HTTP, własna najniższa oferta każdego FR/RK, wszystkie rozpoznane grupy. | Tylko kwalifikujący się hiszpański odcinek w 3/5, wspólna reguła opłat. Bez bonifikaty na bezpośrednim POZ–Teneryfa. |
| Wizz | Oficjalne timetableV2 regular/WDC; numery/czasy z zatwierdzonych rejestrów. | Kwalifikujący się odcinek w 4/5 według konfiguracji; WDC osobno. |
| Binter | Oficjalne booking_search do wyboru EUR cash fare, potem booking_getImports konkretnej taryfy. | Oficjalna końcowa kwota RC dla jednego dorosłego. PTS pomijać bez odrzucenia prawidłowych taryf EUR. |
| Iberia/Express | Google Flights HTTP. | Jawny szacunek ze wspólną regułą opłat. |
| Vueling | Google Flights HTTP; oficjalna strona Vuelinga pozostaje podstawą siatki. | Jawny szacunek ze wspólną regułą opłat. |
| Air Europa | Wyłącznie Google Flights HTTP: pełne UX, daty/godziny i własna cena każdego rejsu; bez branded minimum i szablonów. | Jawny szacunek z opłatami, nie oficjalna kwota. |
| Volotea | Oficjalny MinPrice route/day, cena PriceWithFee. Bez Google. | Szacunek; własne podatki/opłaty Volotei muszą zgadzać się z tabelą. |
| Canaryfly | Oficjalne booking_calendar → booking_search → booking_getImports. Bez Google. | Oficjalna końcowa kwota DC dla jednego dorosłego. |

1. Dla Bintera/Canaryfly sumować `mainAmount` dla regularnej i `totalAmount`
   dla rezydenta przez taryfę, podatki, dopłaty, service fee i management fee.
   Brak składnika, błędna waluta lub brak potwierdzenia rezydenta blokuje
   publikację. Opaque token tylko w pamięci.
2. Dla szacunków używać wyłącznie `scripts.spanish_resident_fees` i
   `data/spanish-resident-fees.json`:
   `opłata_PLN + mnożnik × (cena_regularna_PLN − opłata_PLN)`.
   Nigdy cała regularna cena × 0.25. Polski odcinek ma pełną cenę.
3. Sam POZ nie wymaga opłaty Aena. Nowy kwalifikujący się hiszpański hub
   wymaga reguł obu kierunków i dowodów. Nie przypisywać automatycznie
   wyspie opłaty modelu półwyspowego.
4. Zastany rejestr opłat obejmuje odloty **2026-03-01–2026-12-31**.
   Przy późniejszym wdrożeniu sprawdzić całe okno. Brak lub wygaśnięcie
   opłaty blokuje publikację, a nie uzasadnia zera lub zgadniętej kwoty.
5. `NBP_SHARED_CURRENCIES` jest w `collect_step1.py`, nie w nowym module.
   Zestawić go z `SOURCE_CURRENCIES` kroków i walutami nowo dodanych rynków.
   Zachować wspólny cache `tmp/nbp-rates/YYYY-MM-DD.json`; nie pytać NBP od
   nowa w każdym kroku. Nowa polska destynacja sama nie wymaga nowej waluty.
6. Linki generować przez `scripts.booking_urls`: wizz_booking_url,
   ryanair_booking_url, iberia_booking_url, vueling_booking_url,
   air_europa_booking_url, volotea_booking_url, canaryfly_booking_url.
   Zachować obecny poprawny generator/link Bintera. Każdy odcinek kupowany
   osobno ma własny adres z właściwą trasą, datą i pasażerami.
7. Air Europa zachowuje `residentType=SPANISH_RESIDENT_RC` na kwalifikującej
   się trasie i usuwa go po wyłączeniu rezydenta. Link nadal wybiera trasę
   i dzień, nie konkretny numer UX. Podobnie nie obiecywać preselektora
   konkretnego rejsu Wizz/Ryanair, gdy danego dnia jest ich kilka.
8. Nie dodawać POZ do kanaryjskich slugów Canaryfly: POZ jest odcinkiem
   low-cost, a nie nowym lotniskiem tej linii. Volotea/Canaryfly wybierają
   rezydenta w swoim interfejsie, bez wymyślonych parametrów URL.
9. `reprice_*` nie dodają siatki POZ i nie zastępują nowej pełnej kolekcji.

## 10. Etap 6 — interfejs i dokumentacja operacyjna

1. W `app.js.airportLabels` dodać `POZ: "Poznań (POZ)"`. W `index.html`
   dopisać Poznań do informacji o zakresie. Nie zmieniać wyglądu przy okazji.
2. Zachować dynamiczne selektory zależne od kierunku. Kolejność IATA przy
   obecnym sortowaniu, jeśli wszystkie endpointy mają wyniki, to
   `all, GDN, KRK, KTW, POZ, WAW, WMI, WRO`.
3. Przy pełnym skanie bez żadnej oferty POZ nie wymuszać pustej opcji ani
   fikcyjnych lotów; wskazać przyczynę w raporcie. Nie mylić braku wyników
   przy filtrze 1000 zł/6 h z brakiem zebrania danych.
4. Przetestować kalendarz i wykres wskazujące tę samą najtańszą kartę POZ,
   wszystkie resident/WDC, osiem sortowań na całym zbiorze, dogrywanie kart,
   zaznaczenie/zakotwiczenie lotu i cache kart. Wąski ekran też w zakresie.
5. X przy filtrze POZ ma przywracać wszystkie lotniska, X zakresu dat pełne
   daty bazy; reset przywracać stare domyślne ustawienia. Direct nadal
   wyszarza czas oczekiwania i drugą linię oraz zeruje tę nieaktywną linię.
6. Sprawdzić `+1` przy przylocie następnego dnia i udostępnione loty POZ
   obu kierunków, również powyżej 1000 zł. Link nie może gubić ustawień
   rabatów, a domyślny kierunek nie może nadpisać kierunku z linku.
7. Nowe pobranie może usunąć wygasły lot z linku starej bazy; obsłużyć to
   dotychczasowym komunikatem. Nie zmieniać algorytmu ID dla samego POZ.
8. Podnieść wersję `app.js` w HTML. CSS zmieniać tylko, jeśli rzeczywisty
   problem układu wymaga poprawki, nie dla nowej nazwy w selektorze.
9. Uaktualnić aktywne listy/macierze w `AGENTS.md`, kanonicznej instrukcji,
   README i opisach allowlist. Uważać na tekst „sześć wariantów kroku 1”:
   nadal jest poprawny — nie zamieniać każdego „sześć” na „siedem”.
10. Utworzyć podczas wdrożenia `docs/WDROZENIE_POZNANIA_POZ.md` z faktycznymi
    dowodami, wynikami i ograniczeniami; niniejszy plan nie jest raportem sukcesu.

## 11. Etap 7 — testy rozszerzenia i regresji całej szóstki

Zachować istniejące testy GDN **oraz WRO**. Dodać np.
`tests/test_poz_expansion.py` i rozszerzyć testy integracyjne JS.
Nie podnosić mechanicznie wszystkich liczników: część dotyczy fixture,
liczby dat lub rzeczywistych dopuszczonych tras, a nie liczby endpointów.

### Konkretne miejsca obecnego kodu testów

- `test_airport_expansion.py` i `test_wro_expansion.py` mają jawne sześć kodów;
  trzeba wymagać siedmiu, ale zachować sprawdzanie własności WRO i GDN.
- `test_step2_collector.py`: 24 skierowane pary zmieniają się na 28.
  `test_source_completeness.py`: 48 sprawdzeń jednego dnia zmienia się na 56.
  Test pokrycia w `test_wro_expansion.py` ma obecnie `48 * 31`.
- Dwuhubowy test macierzy 1A/1B ma 24 wywołania na linię; po POZ to 28.
  Jawnie sprawdzić POZ w obie strony, również przy pustych odpowiedziach.
- W teście regresji `POLISH_AIRPORTS[:-1]` obecnie usuwa WRO, a po dodaniu
  POZ będzie usuwać POZ. Zestawienie tego z filtrem wykluczającym WRO da
  błędny test. Zdefiniować jawny baseline sześciu i osobny stary baseline
  GDN, bez polegania na „ostatnim elemencie”. Porównać te same wejścia
  przed/po migracji, filtrując wyłącznie nowy endpoint.
- W `test_airport_ui.mjs` lista selektora zawiera sześć endpointów. Dodać
  POZ w porządku IATA i przypadki Poznania, nie zastępować nimi WRO/GDN.
- Testy 1E/1F mają oczekiwania konkretnych `polish_routes`. Aktualizować je
  tylko zgodnie z zatwierdzoną siatką, nie zakładać automatycznego POZ–BIO/LPA.
- Zachować dokładne WRO zbiory hubów w testach i jego weekday override;
  nie zmieniać ich wyłącznie dlatego, że dodano inny endpoint.

### Wymagana macierz odbioru

| Obszar | Dodatkowe przypadki POZ |
| --- | --- |
| Rejestr/metadane | Dokładna siódemka, Europe/Warsaw, dziewięć zgodnych scope, brak duplikatów; wszystkie nowe huby mają timezone. |
| Detektor | POZ poszerza istniejący hub i otwiera nowy; nowy TFN/TFS; pending przy braku Wizz; selektywne/idempotentne zastosowanie, bez usuwania sezonowych tras szóstki. |
| Helper | Jawny endpoint POZ, odrzucenie dowodów WRO/innego okna, poprawne opisy siedmiu, poprawny hub po patchu; nowy hub 1B–1F nie może zostać zgubiony. |
| Wizz | Oba kierunki, różne godziny tego samego dnia, numery/czasy, wyjątki clock/weekday/date i ich pierwszeństwo; zgodność wspólnego i lokalnych rejestrów. |
| 1A–1F | Budowanie POZ w obie strony oraz rzeczywiste planowanie/pobieranie właściwych tras, nie tylko syntetyczne build_connections; pełne niezależne kalendarze. |
| 2 | 56 × 31 pozycji, w tym POZ/TFN/TFS obie linie i oba kierunki; poprawnie sprawdzone zero. |
| 3/4/5 | Właściwa linia na każdym geograficznym odcinku i właściwy rabat, osobno A/B; test syntetyczny może badać mechanikę B bez fałszywej deklaracji żywej trasy. |
| Ceny | FR/RK, indywidualna cena każdego rejsu, wszystkie znane grupy Google; official imports RC/DC; opłaty obu kierunków, brak/wygasła stawka fail closed. |
| Coverage | Plan sprzed zapytań, dzień jednej linii bez drugiej, puste dni versus błędy; stary raport sześciu nie certyfikuje siedmiu. |
| Batch/cache | Jeden run, nowe ID = świeży cache; resume = te same daty/config; zmiana konfiguracji odrzucana; Google max 2 również retry; jeden NBP. |
| Promocja | 20 plików i backup/rollback, również test wcześniejszego braku sidecara. Awaria nie miesza starej i nowej bazy. |
| Granice czasu | 119/120 i 1440/1441 minut; północ, zmiana czasu, granice okna. Czas rzeczywisty liczyć na znacznikach z poprawnymi strefami/UTC. |
| UI/linki | POZ w obu kierunkach i czterech trybach rabatów; kalendarz/słupek → ta sama karta; X/reset/direct/+1, udostępnianie, zakup obu odcinków. |
| Regresja | WAW/WMI/KTW/KRK/GDN/WRO na zamrożonych wejściach: identyczne stare ID/ceny/dopasowania; GDN/5B/KRK działa, GDN/POZ i WRO/POZ niedozwolone. |

Przed kolekcją uruchomić testy offline. Testy JS na realnych nowych wynikach
POZ uruchomić dopiero po ukończeniu dziesięciu nowych feedów w stagingu.
Jeśli dany wariant nie ma realnej trasy lub żadnej oferty, nie wymuszać
dodatniej liczby lotów. Syntetyczna fixture ma potwierdzić mechanikę,
a kompletny raport pokrycia rzeczywiste wykonanie skanu.

```text
.venv/bin/python -m unittest discover -s tests
node --check app.js
node --test tests/test_airport_ui.mjs
git diff --check
```

## 12. Etap 8 — nowa pełna baza siedmiu, wyłącznie do stagingu

1. Zamknąć audyt i wszystkie zmiany konfiguracji **przed** rozpoczęciem
   produkcyjnego runu. Nie zmieniać rejestru/allowlist/rozkładów/opłat w tle.
2. Ustalić jeden dzień w `Atlantic/Canary` i jawnie przekazać `--from-date`.
   Nowy katalog np. `tmp/poz-expansion/batch-YYYY-MM-DD-RUN`, nowe run ID,
   `--days 30`. Nie używać run ID ani cache WRO jako dzisiejszego POZ.
3. Runner ma już przydział cache per run i przekazuje go wszystkim dziesięciu
   procesom przez `RESIFLY_RYANAIR_GOOGLE_CACHE`. Zachować tę funkcję;
   metadane pliku cache sprawdzają daty i hash konfiguracji przy wznowieniu.
4. Uruchomić pełną kolejność **1A, 1B, 1C, 1D, 1E, 1F, 2, 3, 4, 5**.
   Odświeżyć całą siódemkę, nie dopisywać nowych lotów POZ do starej bazy
   szóstki. Nie nadawać starym cenom nowego run ID lub raportu pokrycia.
5. Współdzielić dzienny NBP. Nie uruchamiać obok innych kolektorów,
   weryfikatorów lub prób Google: semafor 2 jest procesowy, nie globalny
   pomiędzy osobnymi procesami. `--workers 4` nie zwiększa limitu Google.
6. Po awarii zachować log, failed sidecar i stan cache. Runner nadpisuje log
   danego kroku przy kolejnej próbie, więc poprzedni log/raport najpierw
   skopiować do własnego pliku diagnostycznego. Nie obchodzić parsera.
7. Wznowić **nieudany i wszystkie niewykonane kroki** z pierwotnym run ID,
   datami i konfiguracją. Ukończonych feedów tego runu nie pobierać ponownie
   bez potrzeby. Przy WRO dwa przejściowe błędy Google ustąpiły po takim
   wznowieniu; nie uznano błędnych odpowiedzi za puste dni.
8. Jeśli zmienia się konfiguracja albo minął dzień kanaryjski, zacząć nowy
   pełny run. Walidator wymaga bieżącej daty `generated_at`; nie poprawiać
   jej ręcznie. Nie mieszać różnych kursów i dni w jednej publikacji.

Szablony, których **nie uruchamia się podczas przygotowania planu**:

```text
.venv/bin/python scripts/collect_five_steps.py --from-date YYYY-MM-DD --days 30 --stage-directory tmp/poz-expansion/batch-YYYY-MM-DD-RUN --workers 4

.venv/bin/python scripts/collect_five_steps.py --from-date YYYY-MM-DD --days 30 --stage-directory tmp/poz-expansion/batch-YYYY-MM-DD-RUN --run-id RUN_ID_Z_RAPORTU --refresh-steps 3 4 5

.venv/bin/python scripts/collect_five_steps.py --from-date YYYY-MM-DD --days 30 --stage-directory tmp/poz-expansion/batch-YYYY-MM-DD-RUN --validate-only

RESIFLY_TEST_DATA_DIRECTORY=tmp/poz-expansion/batch-YYYY-MM-DD-RUN node --test tests/test_airport_ui.mjs
```

Kroki `3 4 5` są przykładem wznowienia, nie stałą procedurą. Przy awarii 1C
lista obejmuje 1c 1d 1e 1f 2 3 4 5. Nie podnosić równoległości ani nie
skracać okna tylko po to, by zmieścić pełną nową siatkę w krótszym czasie.

## 13. Etap 9 — odbiór, lokalna podmiana i odzyskiwanie

Przed promocją potwierdzić:

1. Wszystkie dziesięć feedów schema 2 i sidecary mają jeden run, wspólne
   okno, poprawne dzienne kursy, właściwe źródła i bieżące daty kolekcji.
2. Wszystkie raporty: `complete`, zero `missing_queries` i zero
   `unexpected_queries`, zgodny aktualny plan **siedmiu** endpointów.
   Wszystkie wymagane dni POZ sprawdzone, także z zerem ofert.
3. Każda zatwierdzona para/hub/linia ma dowód i rzeczywisty plan zapytań.
   Nie ogłaszać pełnej nowej siatki, gdy wymagany kandydat został zgubiony
   w helperze albo nierozstrzygnięty błąd źródła udaje brak trasy.
4. Unikalne ID globalnie; chronologia, strefy, endpointy, brak samoprzesiadek,
   właściwe rabaty/opłaty, sumy, pełne numery, booking_url i brak tokenów.
5. Raport wyników POZ per kierunek/krok/variant/hub/linia; osobno stara
   szóstka i GDN transfer. Liczba propozycji nie zastępuje pokrycia.
6. Testy offline i integracyjne JS na stagingu przechodzą. Do podglądu
   wizualnego użyć lokalnej kopii strony w `tmp/` z kompletnym nowym stagingiem;
   nie trzeba wcześniej podmieniać publicznego `data/`.
7. Rzeczywista kontrola przeglądarki: POZ jako wylot/przylot, karta po kliknięciu
   kalendarza/słupka, zakup, share, filtry, reset, +1, stara szóstka, wąski
   i szeroki ekran. Ocenić czas przygotowania, pamięć i płynność większej bazy.
8. Brak dostępu do sterowania przeglądarką jawnie opisać i pozostawić odbiór
   wizualny otwarty. Testy JS z dublerem DOM i sam HTTP 200 nie są jego
   zamiennikiem. Nie przenosić automatycznie wyjątku odbioru WRO na POZ.

Po odbiorze, zgodnie z poleceniem wdrożenia, wykonać lokalną promocję:

```text
.venv/bin/python scripts/collect_five_steps.py --from-date YYYY-MM-DD --days 30 --stage-directory tmp/poz-expansion/batch-YYYY-MM-DD-RUN --validate-only --promote
```

Promocja obejmuje **20 plików**, a nie same feedy. Obecny backup zachowuje
pierwszy stan i manifest obecności sidecarów; rollback odtwarza obsłużoną
awarię. To nie jest pojedyncza transakcja odporna na nagłą utratę zasilania.
Nie przebudowywać całej publikacji bez potrzeby, ale nie składać fałszywej
gwarancji atomowości zestawu.

Po promocji ponownie zwalidować `data/`, porównać bajtowo wszystkie 20 plików
ze stagingiem, uruchomić JS na publicznych danych i odczytać nowe feedy przez
lokalny HTTP. Wrócić do właściwego URL głównej strony, nie pozostawiać
użytkownikowi wyłącznie roboczego podglądu stagingu.

Raport `docs/WDROZENIE_POZNANIA_POZ.md` ma zawierać faktyczne trasy i dowody,
statusy sezonowe/pending, okno, daty, run ID, kursy, cache, pokrycie, wyniki
POZ i starej szóstki, GDN transfer, testy, odbiór przeglądarki oraz backup.
Nie opisywać świeżych cen jako gwarantowanych w chwili późniejszego zakupu.

W razie wycofania odtworzyć spójny **kod + rejestr/allowlisty/rozkłady +
wszystkie feedy i sidecary** poprzedniej szóstki. Same stare JSON-y przy
nowym planie siedmiu nie przejdą walidacji. Nie resetować destrukcyjnie
repozytorium i nie usuwać niezwiązanych zmian użytkownika.

## 14. Publikacja i przyszły GitHub Actions

Publikować dopiero na osobne polecenie użytkownika dotyczące wdrożenia POZ.
Nie traktować niniejszego planu ani wcześniejszego push WRO jako takiej zgody.
Pakiet obejmuje kod, konfigurację, testy, dokumentację, dziesięć nowych
feedów i sidecary. Robocze cache, kopie i surowe odpowiedzi `tmp/` nie są
automatycznie publicznym artefaktem. Przed push ponownie sprawdzić status
i zdalną gałąź; po nim potwierdzić commit i faktyczny stan wdrożonej strony.

Tworzenie workflow pozostaje poza zakresem, chyba że użytkownik zdecyduje
inaczej. Późniejszy Actions powinien:

- Instalować `scripts/requirements-flight-collector.txt` i wykonywać testy.
- Wyznaczyć jeden dzień `Atlantic/Canary`, uruchomić dziesięć kolektorów
  sekwencyjnie w jednym jobie z tym samym run ID i dziennym snapshotem NBP.
- Nie współdzielić starego cache cen między nowymi runami. Wznowienie tego
  samego runu jest wyjątkiem wymagającym zgodnych dat i konfiguracji.
- Zachować łączny limit Google 2. Osobne równoległe joby nie współdzielą
  semafora i nie powinny każdemu dostać własnego niezależnego limitu 2.
- Zachować logi i raporty błędu jako artefakty; publikować wyłącznie komplet
  po walidacji. Audyt sieci uruchamiać osobno, nie przy każdym odświeżeniu cen.
- Dopasować czas joba do zmierzonego kosztu siedmiu endpointów. Nie obniżać
  zakresu, nie zmieniać źródeł i nie ukrywać błędów, by uzyskać zielony job.

## 15. Checklista odbioru przyszłego wdrożenia POZ

- [x] Zabezpieczony baseline kodu/konfiguracji i 20 plików starej szóstki.
- [x] Rejestr i dziewięć scope: dokładnie WAW/WMI/KTW/KRK/GDN/WRO/POZ.
- [x] POZ ma Europe/Warsaw; wszystkie procesy czytają nowy rejestr.
- [x] Audyt obecnych i nowych hubów, także dawnych wykluczeń; ograniczenia źródeł jawnie zapisane w raporcie.
- [x] Osobny audyt 1B–1F i obu mieszanych wariantów; żadnej skopiowanej w ciemno trasy WRO/GDN.
- [x] Każda aktywowana para ma właściwy dowód; awarie nie udają braku trasy.
- [x] Wizz: oba kierunki obu potrzebnych odcinków, numery/czasy i wszystkie override, zgodne rejestry lokalne/wspólny.
- [x] Audyt nie wymagał nowych hubów/TFN/TFS; generator jest idempotentny i odrzuca nieprzejrzany nowy port Teneryfy zamiast go pominąć.
- [x] Zachowane trasy szóstki, WRO–LPA weekday override i GDN/5B/KRK; brak rozszerzenia GDN/WRO do POZ jako hubów.
- [x] Krok 2 planuje 28 par na linię, 56 kombinacji i 1736 pozycji dla 31 dat.
- [x] Pozostałe kroki planują i pobierają pełne niezależne kalendarze zatwierdzonych par POZ.
- [x] FR/RK i indywidualne oferty Google; final imports Binter/Canaryfly RC/DC; wspólna ważna tabela opłat dla szacunków.
- [x] Jeden dzienny NBP, Google max 2 łącznie, nowy cache per run, bez użycia cache WRO jako nowej kolekcji POZ.
- [x] Testy POZ oraz regresja GDN/WRO i całej szóstki przechodzą; naprawione założenie `POLISH_AIRPORTS[:-1]`.
- [x] Logika UI/kalendarza/wykresu, rabaty, sortowania, X/reset/direct/+1/share i linki potwierdzone testami JS obu kierunków na prawdziwych danych.
- [ ] Rzeczywisty odbiór wizualny i natywnego schowka — otwarty; narzędzie zwróciło `Local browser use is disabled in Work settings`.
- [x] Dziesięć nowych feedów i sidecary mają zgodny kompletny plan siedmiu i jeden run ID.
- [x] Staging oceniony funkcjonalnie; ograniczenie odbioru wizualnego jawnie zapisane, bez fałszywej deklaracji testu.
- [x] Po promocji 20 plików jest zgodne ze stagingiem; działa lokalny HTTP, backup i testy rollbacku.
- [x] Raport wdrożenia wyjaśnia brak wyników, sezonowość i nierozstrzygnięty punkt; nie obiecuje fikcyjnej kompletności.
- [x] Pierwszy odbiór bez commita/push/Actions, zgodnie z poleceniem lokalnej realizacji; późniejsza publikacja POZ autoryzowana osobnym poleceniem użytkownika.

## 16. Co wykonano przy przygotowaniu tego planu

- Odczytano bieżące instrukcje, plany i raport WRO, kanoniczne dokumenty,
  rejestr, dziewięć allowlist, helpery audytu/konfiguracji, resolver Wizz,
  planner pokrycia, runner, istotne funkcje kolektorów, testy i UI.
- Sprawdzono zakresy, metadane i liczby dziesięciu obecnych feedów, zgodność
  sidecarów oraz bieżącego planu pokrycia. Nie wykonano nowych requestów cen.
- Ponownie uruchomiono **165 testów Python — OK** i **14 testów JS — OK**.
  To dowód poprawności baseline sześciu, **nie wdrożenia Poznania**.
- Zapisano ten dokument i odnośnik w README. Nie zmieniono rejestru,
  allowlist, kolektorów, aplikacji ani plików wynikowych. Nie uruchamiano
  live discovery, kolekcji cen, repricingu, promocji ani GitHub Actions.
- Nie wykonano commita ani push. Plan jest gotowy do późniejszej realizacji
  po poleceniu użytkownika, z aktualną ponowną kontrolą stanu repozytorium.
