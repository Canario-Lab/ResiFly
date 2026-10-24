# Bezpieczne zbieranie i publikowanie cen

Zabezpieczenia działają w lokalnych kolektorach. Nie wymagają GitHub Actions
i nie dodają samodzielnie kroków wyszukiwania. Użytkownik 24.10.2026
zatwierdził osobny krok 6 easyJet + FR/Wizz i Google Flights dla easyJet.
Kanoniczne listy tras, zakres
dat, obydwa kierunki, zniżki i filtrowanie cen na stronie pozostają bez zmian.

Osobna decyzja użytkownika z 24.10.2026 dopuszcza kontrolowaną aktualizację
częściową: [`PARTIAL_FLIGHT_UPDATES.md`](PARTIAL_FLIGHT_UPDATES.md).
To jawny wyjątek od zakazu mieszania runów, nie oznaczenie starych cen jako
nowych. Zwykła cotygodniowa pełna kolekcja nie zmienia zachowania.

## Wspólne źródła i równoległość od 24.10.2026

`collect_five_steps.py` zaczyna od `source_pipeline.py`: niezależny plan z
jedenastu feedów jest deduplikowany według przewoźnika, trasy i dnia. Google
realizuje kolejno rodziny Ryanair (FR/RK), Iberia (IB/I2), Vueling, Air Europa i easyJet,
globalnie do trzech prób HTTP naraz, także podczas ponowień. Nie jest to
oficjalnie gwarantowany limit Google. Blokada procesu w `tmp/locks/` odrzuca
drugiego właściciela Google na tej samej maszynie.

Jednocześnie osobne kolejki Wizz Air, Binter, Canaryfly i Volotea wykonują do
dwóch prób HTTP na źródło. Wizz zapisuje razem regular/WDC po ich poprawnym
pobraniu, Binter/Canaryfly końcowe kwoty imports bez tokenów, Canaryfly osobno
pełny kalendarz oraz szczegóły dostępnych dni. Brak aktywnego lotu nie usuwa
obowiązku odczytu zaplanowanego kalendarza.

Repozytorium JSONL w stagingu identyfikuje run, daty, konfigurację i wersję
adapterów, NBP oraz limit. Zapisy są serializowane; kompletne obserwacje są
niemutowalne. Manifest kompletności zawiera sumy SHA256 plików. Przerwany lub
zmieniony zapis nie poświadcza sukcesu. Wznowienie tego samego runu może użyć
wyłącznie jego poprawnych obserwacji przy identycznej konfiguracji/adapterach.

Dopiero po pełnym źródle jedenaście kolektorów uruchamia się kolejno z
`RESIFLY_SOURCE_MODE=read`. Raporty pokrycia zachowują oryginalne metody
źródeł; brak cache blokuje, nie wywołuje awaryjnej sieci. NBP jest zamrożony
w manifeście źródeł. Wszystkie dwadzieścia dwa pliki przechodzą dotychczasową
bramkę promocji lokalnej. Nie wykonuje ona operacji Git ani GitHub Actions.

`performance.json`, `source-progress.json`, `source-coverage.json` i log batcha
pozwalają oddzielić faktyczne próby HTTP, retry, czasy i limity od logicznego
route/day coverage. Poprawne `InvalidMarket` Wizza (HTTP400) pozostaje pustym
rynkiem, nie błędem kompletności. Nie interpretować surowego licznika 4xx jako
liczby nieudanych kalendarzy.

## Migracja easyJet — 24.10.2026

Zestaw sześciu głównych kroków to 11 feedów i 11 sidecarów. Nowy krok 6
jest wymagany, nie opcjonalny. Pierwsza migracja zachowuje backup starych
20 plików i zapisuje nieistnienie starego Step 6; późne wycofanie usuwa nowo
utworzony Step 6 i przywraca cały poprzedni komplet. Test awarii ostatniej
podmiany obejmuje wszystkie 22 pliki. Oryginalna nazwa runnera jest utrzymana.

easyJet jest wyłącznie kolejną rodziną istniejącej kolejki Google po UX,
bez dodatkowego limitu ani przełączenia na stronę przewoźnika. Surowe
znormalizowane obserwacje ceny/rejsu są współdzielone i niemutowalne;
builder dopisuje trwały link oraz pochodne ceny rezydenta. Obecne trasy są
międzynarodowe, bez tej bonifikaty. Polski Wizz zachowuje osobno regular/WDC.

Bazylea wymaga CHF. Dzienne cache NBP bez tej waluty nie jest kompletnym
snapshotem dla nowej kolekcji. Wszystkie waluty, łącznie z CHF, są pobierane
i zamrażane przed zapytaniami o loty. Nie dopisywać waluty do manifestu już
rozpoczętego runu ani nie zmieniać jego hashy: poprawka wymaga nowego runu.
Szczegóły prób, zatrzymanego pierwszego przebiegu i aktualnego odbioru:
[`WDROZENIE_KROKU_6_EASYJET_STATUS.md`](WDROZENIE_KROKU_6_EASYJET_STATUS.md).

## Automatyczne odzyskiwanie źródeł — 24.10.2026

Na polecenie użytkownika odzyskiwanie przejściowych błędów pełnego batcha
nie wymaga ponownego pytania o zgodę. Implementacja: `source_recovery.py`.
Zwykły krótki budżet adaptera pozostaje bez zmian (Google: cztery próby).
Nieudane zadanie jest odkładane, a pozostałe dni/trasy tej kolejki są
sprawdzane dalej. Potem następują najwyżej dwie dodatkowe rundy po 60 i 120 s
od ostatniej nieudanej próby. Czas kończenia zdrowych zadań wlicza się w tę
przerwę — jeżeli już minęła, ponowienie nie dokłada zbędnego oczekiwania.
Retry-After może wydłużyć przerwę w granicach istniejącego budżetu; większe
żądane oczekiwanie nadal blokuje, nie jest ignorowane. Przerwa nie zajmuje
slotu HTTP i jest przerywalna. Nie ma nieograniczonej pętli restartów.

Ryanair jest planowany jako osobne zadania trasa/dzień, z tym samym plikiem
cache runu. Wizz nadal pobiera pełne własne kalendarze regular/WDC,
Canaryfly pełne miesiące przed szczegółami dostępnych dni. Każda kolejka
ponawia tylko nieukończone zadania, nie cudze daty i nie poprzednie ceny.
Po 20 nieudanych zadaniach w rundzie pozostałe niepodjęte zadania tej kolejki
są odraczane do kolejnej rundy — zabezpieczenie na większą awarię źródła.
Zadania aktywne mogą się zakończyć. Niepodjęte zadanie pozostaje brakiem,
nigdy potwierdzonym zerem dostępności. Liczba aktywnych futures jest
ograniczona do workerów, zamiast umieszczać cały plan w executorze naraz.

Po wyczerpaniu rund niezależne źródła i późniejsze rodziny Google kończą
własne kalendarze. W kolejce Google nadal kolejno FR/RK, IB/I2, VY, UX, easyJet,
nigdy różne rodziny równocześnie, najwyżej trzy rzeczywiste próby HTTP.
Oficjalne źródła nadal do dwóch każde. Pełne coverage jest bramką budowania
i promocji; bez niego nie powstaje certyfikat ukończenia. Zachowujemy
dotychczasowy publiczny komplet oraz poprawne obserwacje bieżącego runu.

Błędy integralności repozytorium, lokalnego zapisu, programowania, jawne
błędy bezpieczeństwa konfiguracji i przerwanie operatora nie są automatycznie
odraczane. Preflight nadal musi przejść przed pobieraniem. Dodatkowe rundy
są własnością pełnego `collect_five_steps.py`; samodzielne kolektory nadal
mają dotychczasowy krótki budżet i kończą się błędem po jego wyczerpaniu.

Raport `source-recovery.json` zawiera run/identity, rundy, statusy, liczbę
ukończonych zadań i brakujące identyfikatory tras/dat. Nie zapisuje treści
odpowiedzi, komunikatów wyjątków, tokenów ani danych sesji. Zmiana kodu
odzyskiwania zmienia hash adapterów: nie wolno przepisywać certyfikatów
starego runu, by udawały pobranie nową wersją.

Wdrożenie tej zmiany nie pobiera nowych kalendarzy i nie zmienia publicznych
cen. Testy offline obejmują chwilową niepełną odpowiedź Google (normalne
cztery próby, później sukces bez zmiany parsera), trwałe braki, kontynuację
niezależnych źródeł i rodzin, limit trzech/dwóch także przy recovery,
Retry-After, przerwanie, wyłącznik większej awarii oraz blokadę certyfikacji.

Odbiór tej zmiany: **273 testy Python** (w tym 14 nowych testów odzyskiwania),
**45 testów JS**, bez pominiętych. Python i dodatkowy test wszystkich dziesięciu
builderów wykonano z zablokowanym transportem HTTP. Buildery korzystały wyłącznie
z jawnego, usuwanego fixture offline, bez promocji i bez przypisywania starym
cenom świeżości. Bieżące publiczne 20 plików pozostało bez zmian i ponownie
przeszło walidację dotychczasowego runu. Nie pobierano nowych kalendarzy ani
nie wykonywano commita/push tej zmiany. Logi: `tmp/source-recovery-20261024/`.

## Ryanair

Wspólna funkcja w `scripts/collect_step2.py` jest używana przez kroki 1A–1F,
2, 3 i 5. Od decyzji z 22.10.2026 jedynym bieżącym źródłem numerów, dat,
godzin i indywidualnych cen Ryanaira jest Google Flights HTTP. Każda zapisana
trasa jest pytana osobno o każdy dzień pełnego okna, niezależnie od rozkładu
drugiej linii. Parser zachowuje wszystkie bezpośrednie oferty z kodami `FR`
oraz Ryanair UK `RK`, także kilka godzin tego samego dnia.

Wszystkie zapytania Ryanaira są ograniczone do trzech równoległych wywołań.
Znormalizowane poprawne odpowiedzi trasa/dzień trafiają do trwałego cache i są
ponownie używane przez dziesięć kolektorów tego samego batcha. Brak ceny
konkretnego rejsu, nieznana struktura albo wyczerpanie ponowień blokuje
publikację; poprawny pusty dzień jest dozwolony. Minimum dnia i Fare Finder
nie są źródłami zastępczymi i nie mogą poświadczyć kompletnego kalendarza.

## Binter

Istniejące ograniczone ponowienia HTTP zostają. Po ich wyczerpaniu błąd
propaguje się z trasą i datą; nie jest zamieniany na pustą listę. Walidowane
są błędy GraphQL, `booking_search`, struktura dostępności, trasa i data.
HTTP 200 z `errors`, brakującą dostępnością lub komunikatem typu ERROR/FATAL
nie jest poprawnym pustym dniem.

Poprawna pusta dostępność i wyprzedane taryfy (`seats=0`) są dozwolone.
Punkty lojalnościowe `PTS` są celowo pomijane, a taryfy pieniężne EUR są
przetwarzane niezależnie. Nieprawidłowa taryfa gotówkowa blokuje wynik.

`booking_search` zwraca kwotę samej taryfy, a nie zawsze końcową cenę płatną.
Po wybraniu najtańszej taryfy EUR kolektor przekazuje jej nieutrwalany token do
`booking_getImports` dla jednego dorosłego (`RC` na trasie ze zniżką). Cena
regularna jest sumą wartości bazowych `mainAmount`, a cena rezydenta sumą
końcowych `totalAmount` dla taryfy, podatków, dopłat, opłaty serwisowej i
opłaty za obsługę. Dzięki temu np. 375,00/93,75 EUR z listy taryf staje się
395,91/105,66 EUR do zapłaty. Błąd, brak składnika, inna waluta lub brak
potwierdzenia statusu rezydenta blokuje publikację.

Jednorazowa naprawa istniejącego feedu jest wykonywana przez
`scripts/reprice_binter_final_prices.py --apply`. Skrypt nie zbiera ponownie
innych przewoźników ani nie dodaje nowych połączeń: odświeża końcowe ceny
wyłącznie lotów Bintera już zapisanych w `step1-results.json`, wymaga dokładnego
dopasowania każdego nadal dostępnego numeru i godzin, przelicza zależne sumy
oraz dopiero po kompletnym sukcesie atomowo podmienia feed. Jeśli oficjalna
odpowiedź dla poprawnie sprawdzonej trasy i dnia nie zawiera już zapisanego
lotu, skrypt usuwa wyłącznie połączenia oparte na tym niedostępnym odcinku i
zapisuje je w raporcie. Kopia przed zmianą, staging i raport pozostają w
`tmp/binter-price-repair/`.

## Szacunki cen rezydenta i opłaty Aeny

Wspólny rejestr `data/spanish-resident-fees.json` zawiera kierunkowe opłaty
niedyskontowane i jawny okres ich ważności. `scripts.spanish_resident_fees`
stosuje wzór `opłaty + 0.25 × (cena regularna − opłaty)` do Iberii/Iberii
Express, Vuelinga, Air Europy, Volotei oraz kwalifikujących się hiszpańskich
odcinków Ryanaira i Wizz Aira w krokach 3–5. Wszystkie opłaty są przeliczane
jednym kursem EUR/PLN batcha. Brak stawki lub wyjście poza okres ważności
rejestru blokuje publikację.

Binter i Canaryfly są wyłączone ze wspólnego estymatora: ich źródła zwracają
oficjalne ceny rezydenta dla konkretnych rejsów. Skrypt
`scripts/reprice_spanish_resident_estimates.py` służy wyłącznie do poprawienia
pól pochodnych w już zebranych feedach i nie wykonuje zapytań sieciowych.
Zachowuje rozkłady, ceny regularne, linki, daty kolekcji, raporty pokrycia i
`run_id`.

W Canaryfly kwoty z `booking_search` są wartościami listy taryf i nie są
końcową ceną płatną. Kolektor przekazuje nieutrwalany token wybranej taryfy do
`booking_getImports` dla jednego dorosłego z kodem rezydenta `DC`. Tak jak w
Binterze, cena regularna jest sumą `mainAmount`, a rezydencka sumą
`totalAmount` dla taryfy, podatków, dopłat, opłaty serwisowej i opłaty za
obsługę. Brak któregokolwiek składnika lub brak potwierdzenia rezydenta blokuje
publikację. Opłaty międzywyspowe pochodzą z końcowego rozliczenia przewoźnika,
nie z tabeli opłat dla tras Teneryfa–Półwysep.

Jednorazowa naprawa istniejącego Step 1F jest wykonywana przez
`scripts/reprice_canaryfly_final_prices.py --apply`. Skrypt nie pobiera
ponownie miesięcznych kalendarzy ani pozostałych linii: sprawdza tylko trasy i
dni lotów Canaryfly zapisanych już w feedzie, pobiera ich końcowe ceny,
przelicza zależne sumy i podmienia plik atomowo po pełnym sukcesie. Jeśli
poprawnie sprawdzona trasa i dzień nie zawierają już starego lotu, usuwane są
wyłącznie połączenia zależne od tego niedostępnego odcinka. Kopia wejścia,
staging i raport pozostają w `tmp/canaryfly-price-repair/`.

## Air Europa — wyłącznie Google Flights od 22.10.2026

Krok 1D pobiera numery rejsów, pełne daty/godziny i regularne ceny w PLN
wyłącznie z indywidualnych ofert Google Flights HTTP. Dla każdego rejsu
zachowuje jego własną najniższą zwróconą taryfę. Nie wolno zastępować ceny
konkretnego lotu promocyjnym minimum trasy/dnia ani rozkładem z szablonu.
Usunięto dotychczasowy klient branded feedu i aktywne szablony z allowlisty.

Obowiązuje wspólny limit trzech równoległych zapytań, także gdy `--workers`
jest większy. W pełnym batchu chwilowe błędy przechodzą opisane wyżej
ograniczone odzyskiwanie. Samodzielny kolektor po błędzie źródła zatrzymuje
dalsze zapytania; aktywny wątek może dokończyć swoją próbę. Pusty, poprawnie sprawdzony dzień jest
dozwolony. Brak ceny, pełnego numeru lub godzin zwróconego rejsu blokuje zapis.
Raport pokrycia dopuszcza tylko metodę `google_flights_http` dla Air Europa,
więc stary raport minimum dnia nie może poświadczyć nowego pobrania.

Cena rezydenta pozostaje jawnie oznaczonym szacunkiem, nie oficjalną wyceną
przewoźnika. Kolektor odejmuje kierunkowe stałe opłaty zapisane we wspólnym
`data/spanish-resident-fees.json`,
stosuje `0.25` wyłącznie do części taryfowej i dodaje opłaty z powrotem,
przeliczając EUR jednym kursem NBP batcha. Brak reguły opłat blokuje zapis;
nie wolno mnożyć całej regularnej ceny przez `0.25`. Trwały link zakupu nadal prowadzi do Air Europa,
z trasą/datą/pasażerami i parametrem `residentType=SPANISH_RESIDENT_RC`,
usuwanym przez stronę po wyłączeniu rezydenta. Obecny format jest wyszukiwaniem
trasy/dnia, nie potwierdzonym automatycznym wyborem numeru rejsu. Nie wolno
dodawać niezweryfikowanych parametrów wyboru lotu lub utrwalać linków sesyjnych.

## Raport pokrycia

`scripts/collection_coverage.py` tworzy plan wszystkich tras/dni z zapisanych
macierzy i allowlist przed zapytaniami. Nie buduje planu z znalezionych
lotów. Wątki rejestrują sukces dopiero po zakończeniu pobrania i parsowania;
wyjątek nie jest sukcesem. Raport rozróżnia sprawdzone dni bez lotów od
brakujących sprawdzeń. W Canaryfly pełny kalendarz dodatkowo wyznacza
wymagane sprawdzenia szczegółów dni oznaczonych jako dostępne.

Każdy feed zawiera `collection_coverage`, a obok powstaje plik
`step*-results.collection-report.json` z identycznym raportem. Raport
obejmuje przewoźnika, trasę, daty, metodę, liczbę lotów i wspólny identyfikator
uruchomienia. Błąd zostawia poprzedni feed bez zmian, ale aktualizuje sidecar
do statusu `failed` z brakami i przyczyną. Nie wolno takiego zestawu promować.

Pokrycie dowodzi ukończenia zaplanowanych zapytań oraz przejścia walidacji
znanego formatu. Nie stanowi niezależnej gwarancji, że zewnętrzny serwer
nigdy nie zwróci poprawnie wyglądających, lecz niepełnych danych.

## Zapis i cały batch

- Pojedynczy kolektor publikuje dopiero po pełnym pokryciu. JSON jest
  przygotowywany w pliku tymczasowym i zastępuje poprzedni po udanej
  serializacji; błąd nie obcina starego pliku.
- Całą bazę zbierać przez `scripts/collect_five_steps.py` do stagingu.
  Wszystkie jedenaście feedów otrzymuje to samo `RESIFLY_COLLECTION_RUN_ID`.
  Runner przydziela im świeży plik cache Ryanaira dla konkretnego runu
  i przekazuje go jako `RESIFLY_RYANAIR_GOOGLE_CACHE`. Wznowienie zachowuje
  ten sam cache; inne daty lub konfiguracja tras dla tego samego ID są odrzucane.
- `validate_batch` wymaga zgodności raportu w feedzie i sidecarze, bieżącego
  planu tras/dni oraz wspólnego `run_id`, oprócz walidacji okna, kursów,
  odcinków i wyników. Brak raportu lub pomieszanie uruchomień blokuje zapis.
- `promote_batch` sam ponownie waliduje zestaw przed pierwszą zmianą plików.
  Przy obsłużonym błędzie podmiany przywraca poprzednie pliki. Promocja obejmuje jedenaście feedów i ich jedenaście sidecarów,
  z backupem poprzednich plików i informacją o wcześniej brakujących raportach.
  Jak wcześniej, dwadzieścia dwie podmiany nie są pojedynczą transakcją systemu plików odporną na
  nagłe zabicie procesu lub utratę zasilania.
- Po błędzie batch zapisuje `validation-report.json` ze statusem `failed`,
  identyfikatorem i krokiem, a nie pozostawia pozornego raportu sukcesu.

Nowa pełna kolekcja:

```bash
.venv/bin/python scripts/collect_five_steps.py --from-date YYYY-MM-DD --days 30 --stage-directory tmp/flight-batch --workers 4
```

Jeżeli trzeba wznowić przerwany batch, użyć tych samych dat i `run_id`
z `validation-report.json`. Powtórzyć nieudany i wszystkie niewykonane kroki:

```bash
.venv/bin/python scripts/collect_five_steps.py --from-date YYYY-MM-DD --days 30 --stage-directory tmp/flight-batch --run-id IDENTYFIKATOR --refresh-steps 3 4 5
```

Nie kopiować cen z poprzedniego uruchomienia. Dopiero po pełnym sukcesie:

```bash
.venv/bin/python scripts/collect_five_steps.py --from-date YYYY-MM-DD --days 30 --stage-directory tmp/flight-batch --validate-only --promote
```

## Stan wdrożenia 2026-10-22

Poniższe raporty wcześniejszych wdrożeń są historyczne: ich liczby feedów
nie opisują migracji easyJet. Aktualny zestaw wynika z `scripts.search_steps`.

Obecnych publicznych JSON-ów nie zmieniono ani nie dopisano im poświadczeń.
Starszy staging GDN nie ma nowych raportów i wymaga nowego pełnego pobrania
przed kolejną promocją. Testy obejmują awarie źródeł, brak dnia, różne loty
jednego dnia i zachowanie poprzednich plików. Mały test żywych źródeł zwrócił
cztery loty Bintera TFN–MAD; Ryanair WMI–TFS odrzucił pełną dostępność także
przy próbie dziennej, co prawidłowo zablokowało wynik. Pełnej bazy ponownie
nie zbierano i nie wykonywano operacji Git.

## Lokalna kolekcja sześciu endpointów 2026-10-23

Przy wdrożeniu WRO wykonano nową pełną kolekcję dziesięciu feedów dla
2026-10-23–2026-11-22. Wszystkie mają run ID
`efa7d3ee-f865-4353-84a7-90b73f3eb21e`, kompletne osadzone raporty i zgodne
sidecary. Lokalna promocja objęła dwadzieścia plików i zachowała backup
poprzedniej bazy. Nie użyto starszego stagingu GDN ani starych cen.
Przejściowe nieprawidłowe odpowiedzi Google w 1C i 3 blokowały publikację;
wznowienia z tym samym cache zakończyły brakujące zapytania bez osłabiania
walidacji. Zakres, wyniki, testy i ograniczenie odbioru wizualnego opisuje
[`WDROZENIE_WROCLAWIA_WRO.md`](WDROZENIE_WROCLAWIA_WRO.md). Pierwszy odbiór
odbył się bez commita i push. Następnie 2026-10-23 użytkownik autoryzował
publikację całego pakietu WRO i nowej bazy na GitHub.

## Lokalna kolekcja siedmiu endpointów 2026-10-23

Przy dodaniu POZ zebrano od nowa komplet dziesięciu feedów dla
2026-10-23–2026-11-22, run ID `3f11be44-c429-4c52-82e5-4ae9b41d6a61`.
Wspólny nowy cache Ryanaira ma 14 570 ukończonych tras/dni; nie użyto cen
ani cache WRO. Jeden dzienny NBP, Google max 2, niezmienione źródła i reguły
końcowych cen Binter/Canaryfly oraz szacunków pozostałych linii.

Raporty wszystkich feedów i ich sidecary są kompletne, zgodne z planem
siedmiu endpointów i jednym runem: 30 566 pozycji, zero braków/nadmiarów.
Po 182 testach Python i 16 JS na stagingu wykonano wyłącznie lokalną
promocję z backupem 20 plików, porównaniem bajtowym, ponowną walidacją
publicznej bazy i testami JS. Lokalny HTTP podaje nowy kod i dane.
Odbiór wizualny pozostaje jawnie otwarty (sterowanie lokalną przeglądarką
jest wyłączone w Work). Pierwszy odbiór odbył się bez commita i push.
Następnie 2026-10-23 użytkownik osobno autoryzował publikację całego pakietu
POZ i nowej bazy na GitHub. Dowody i wyniki:
[`WDROZENIE_POZNANIA_POZ.md`](WDROZENIE_POZNANIA_POZ.md).

## Lokalna kolekcja ośmiu endpointów 2026-10-23

Po dodaniu LCJ uruchomiono nowy pełny batch
`a6f8a0e8-f295-4f20-984e-74607fc6cb08` dla 2026-10-23–2026-11-22,
w `tmp/lcj-expansion/batch-2026-10-23`. Własny świeży cache Ryanaira ma
15 500 ukończonych tras/dni; jeden dzienny NBP, Google max 2. Wszystkie
dziesięć feedów i sidecary są kompletne dla bieżącej konfiguracji ośmiu:
32 178 pozycji pokrycia, zero braków/nadmiarów, 15 030 propozycji, w tym
212 LCJ. Nie mieszano starych i nowych cen.

Nieznana odpowiedź Google w kroku 2 zablokowała pierwsze podejście. Wznowiono
tylko 2–5 z tym samym runem/cache, bez zmiany parsera lub traktowania błędu
jako pustego dnia. Po 196 testach Python i 18 JS na stagingu wykonano lokalną
promocję z backupem 20 plików. Publiczna walidacja, bajtowe porównanie ze
stagingiem, ponowne 18 JS i HTTP nowego kodu/20 plików danych przeszły.
Odbiór wizualny/schowka pozostaje otwarty — lokalne sterowanie przeglądarką
wyłączone w Work. Pierwszy odbiór odbył się bez commita i push; następnie
23.10.2026 użytkownik osobno autoryzował publikację całego pakietu LCJ i nowej
bazy na GitHub. Nie dodano workflow Actions. Wyniki i ograniczenia źródeł
discovery: [`WDROZENIE_LODZI_LCJ.md`](WDROZENIE_LODZI_LCJ.md).

## Lokalna kolekcja dziewięciu endpointów 2026-10-23

Po dodaniu RZE zebrano od nowa komplet dziesięciu feedów dla
2026-10-23–2026-11-22, run ID `e1d13844-5567-46d6-980d-f819f4fa1752`.
Świeży cache ma dokładnie 16 492 unikalne poprawne route/day Ryanaira,
nie wykorzystuje starej bazy/cache LCJ. Jeden dzienny zestaw NBP,
Google max 2, pełne niezależne kalendarze i dotychczasowe źródła cen.

Wszystkie dziesięć osadzonych raportów i sidecarów jest kompletnych dla
bieżącej konfiguracji dziewięciu: 33 976 pozycji pokrycia, zero braków
i nadmiarów, 15 268 propozycji, w tym 279 RZE (137/142 w obu kierunkach).
Cała kolekcja zakończyła się bez wznowienia. Wyniki zerowe nie zostały
wyprowadzone z awarii źródła; błąd Binter `timetable_get` podczas discovery
pozostał jawnie błędem, z osobnym przeglądem oficjalnej siatki. Bieżąca
kolekcja cen Binter `booking_search`/`booking_getImports` była kompletna.

Po 208 testach Python i 30 JS na stagingu wykonano lokalną promocję
z backupem 20 plików. Ponowna walidacja i 30 JS na publicznej lokalnej bazie
przeszły, bez pominiętych testów. Backup odpowiada baseline, publiczne pliki
stagingowi, a HTTP nowemu kodowi i wszystkim 20 plikom. Odbiór wizualny
desktop/320 px i systemowego schowka pozostaje otwarty — lokalne sterowanie
przeglądarką jest wyłączone w Work. Pierwszy odbiór był wyłącznie lokalny,
bez commita i push. Następnie 23.10.2026 użytkownik osobno autoryzował
publikację całego pakietu RZE i nowej bazy na GitHub. Bez zmian Actions.
Dowody, ograniczenia i rollback:
[`WDROZENIE_RZESZOWA_RZE.md`](WDROZENIE_RZESZOWA_RZE.md).

## Lokalna kolekcja dziesięciu endpointów 2026-10-23

Po dodaniu BZG zebrano nowy pełny batch dla 2026-10-23–2026-11-22:
`e0322930-e323-4c8c-9f08-459723852a72`, staging
`tmp/bzg-expansion/batch-2026-10-23`. Własny świeży cache Ryanaira ma
dokładnie 17 360 unikalnych poprawnych route/day, zgodnych z pełnym planem;
nie używano cen poprzedniego runu RZE. Jeden dzienny NBP, Google najwyżej 2.

Wszystkie dziesięć feedów i sidecarów jest kompletnych dla aktualnej
konfiguracji dziesięciu: 35 464 pozycji pokrycia, zero braków/nadmiarów,
15 407 propozycji, w tym 187 BZG (95/92 w obu kierunkach). Pełna macierz
bezpośrednia 2480/2480 nie daje BZG. Są dopasowania Ryanair/Ryanair przez
BHX/BRS/DUB/STN i Ryanair/Vueling przez ALC. LTN ma pełne kalendarze,
ale brak par w granicach 120–1440 min; nie usunięto sezonowej trasy.

Nieznane odpowiedzi Google zatrzymały 1C (ALC–GDN 2026-11-15), następnie
3 (pierwszy zgłoszony BRS–WMI 2026-11-14). Zachowano failed reports/logi
i poprawne obserwacje. Wznowiono tylko niedokończone feedy z tym samym
runem/cache/hashem, bez zmiany parsera i bez traktowania błędów jako pustych
dni. Krok 5 zatrzymał HTTP 503 Wizza przy WDC WAW–RAK; ponowiono tylko 5
z dwoma workerami. Wszystkie ponowienia ostatecznie zwróciły poprawne dane,
bez zastąpienia WDC ceną regularną, starego feedu lub zmiany źródła ceny.

Po pełnej walidacji i 34 testach JS na stagingu wykonano lokalną promocję
całych 20 plików, z backupem zgodnym z niezależnym baseline. Publiczne
pliki odpowiadają stagingowi; ponowna walidacja, 220 testów Python i 34 JS
przeszły, bez pominiętych testów. HTTP podaje aktualne bajty nowego kodu
i wszystkich 20 plików danych. Odbiór wizualny desktop/320 px i schowka
pozostaje otwarty — sterowanie przeglądarką wyłączone w Work. Pierwszy odbiór
odbył się bez commita i push. Następnie 23.10.2026 użytkownik osobno
autoryzował publikację całego pakietu BZG i nowej bazy na GitHub.
Bez zmian workflow. Audyt źródeł discovery (w tym błąd Binter timetable
i odrębna weryfikacja oficjalnego katalogu), liczby i rollback:
[`WDROZENIE_BYDGOSZCZY_BZG.md`](WDROZENIE_BYDGOSZCZY_BZG.md).

## Lokalna kolekcja jedenastu endpointów 2026-10-24

Po dodaniu LUZ wykonano pełny nowy batch dla 2026-10-24–2026-11-23,
run `f9323dee-9fdc-4e2f-8075-a39d53838115`, staging
`tmp/luz-expansion/batch-2026-10-24`. Wszystkie dziesięć feedów i sidecarów
ma kompletne pokrycie bieżącej konfiguracji jedenastu: 36 890 pozycji,
zero braków/nadmiarów. Świeży cache Ryanaira zawiera dokładnie planowane
18 104 unikalne route/day. Jeden dzienny zestaw NBP, Google max 2;
całość zakończyła się bez wznowienia ani zmiany parserów.

16 017 propozycji, w tym 47 LUZ (23/24 w obu kierunkach). GDN ma trwałą,
precyzyjną zgodę 5B/KRK,LUZ; pełne kalendarze LUZ↔GDN nie zwróciły jednak
aktualnych lotów Ryanaira, więc nie wymyślano połączeń. Błąd Binter timetable
podczas discovery zachowano jako błąd i rozstrzygnięto trasę osobnym
oficjalnym katalogiem; kolekcja cen Bintera była kompletna.

Po walidacji, 234 testach Python i 38 JS bez skipów promowano lokalnie cały
zestaw 20 plików z backupem. Ponowna walidacja i porównania bajtowe przeszły;
HTTP podaje nowy kod i wszystkie 20 plików. Przeglądarka potwierdziła daty,
jedenasty checkbox i 4 domyślne oferty LUZ; pełny odbiór desktop/320 px
i schowka pozostaje otwarty. Po lokalnej promocji użytkownik osobno autoryzował
publikację całego pakietu na GitHub. Bez zmian workflow Actions.
Szczegóły: [`WDROZENIE_LUBLINA_LUZ.md`](WDROZENIE_LUBLINA_LUZ.md).

## Lokalna kolekcja trzynastu endpointów 2026-10-24

Po wspólnym dodaniu SZY i RDO oraz nowego huba NRN zebrano od nowa wszystkie
dziesięć feedów dla 2026-10-24–2026-11-23. Run
`d98ec327-3fa9-40bd-9a9a-6da358c35bfa`, staging
`tmp/szy-rdo-expansion/batch-2026-10-24`. Kompletne niezależne pokrycie
bieżącej konfiguracji trzynastu: **39 308 pozycji**, zero braków/nadmiarów,
zgodne osadzone raporty i sidecary. Świeży cache ma dokładnie planowane
**19 282 unikalne poprawne route/day** Ryanaira, wyłącznie Google Flights HTTP.
Jeden dzienny zestaw NBP (EUR/PLN 4.3917), Google max 2, bez wznowienia,
starych cen, zmiany parsera lub źródeł. Kolekcja cen Bintera była kompletna;
błąd E01000 jego discovery pozostał błędem z odrębną oceną topologii.

Nowa baza: **15 954 propozycje**, w tym 35 SZY przez STN (9 z Polski,
26 do Polski). RDO ma zero kwalifikujących się wyników. Każdy z czterech
kierunków nowej relacji NRN został sprawdzony przez 31 dat: SZY↔NRN zero,
NRN↔TFS po 22 rejsy. Hub pozostaje w konfiguracji na przyszłe kolekcje;
nie wymyślano brakujących lotów. SZY ma przesiadki dłuższe niż domyślne
6 h; przy 1000 zł i 24 h jest 8 propozycji z Polski i 18 do Polski.

Po walidacji i testach (246 Python, 42 JS, bez skipów) podmieniono lokalnie
całe 20 plików. Backup zgodny z niezależnym baseline, publiczne=staging,
ponowny odbiór batcha i 42 JS na publicznej lokalnej bazie poprawne.
HTTP podaje aktualne bajty index/app i wszystkich 20 plików danych.
Przeglądarka potwierdziła rzeczywiste wyniki, OR portów, oba kierunki,
kalendarz/słupek→ta sama karta, +1, osobne daty booking links oraz faktyczne
kopiowanie, wklejenie i otwarcie linku. Układ sprawdzono przy 1280 px oraz
wąskim panelu około 319 px; wymuszenie dokładnie 320 px w IAB nie zadziałało.
Bez zmian globalnego CSS. Pierwszy odbiór **bez commita/push**. Następnie
24.10.2026 użytkownik osobno autoryzował wysłanie całego pakietu SZY/RDO,
NRN i nowej bazy na GitHub. Bez zmian Actions.
Szczegóły, dowody i rollback:
[`WDROZENIE_SZYMAN_I_RADOMIA_SZY_RDO.md`](WDROZENIE_SZYMAN_I_RADOMIA_SZY_RDO.md).

## Lokalny odbiór SZZ/IEG i źródeł równoległych — 24.10.2026

Pełny batch 15 endpointów dla 2026-10-24–2026-11-23 ma run
`3a5a1329-a7e2-4b95-a2e5-6b10546a544d`, jeden NBP EUR/PLN 4.3917,
33 852 certyfikowane obserwacje źródłowe i 41 974 obserwacje coverage feedów.
Zbudowano 16 087 propozycji, w tym 145 SZZ; IEG ma poprawnie sprawdzone zero.

Pierwsze podejście zatrzymało się bez promocji na niekompletnej odpowiedzi
Google POZ→BRS 17.11.2026 (cztery próby HTTP200). Po wyraźnej zgodzie
użytkownika wznowiono **ten sam run i cache**, bez zmiany parsera, konfiguracji,
adapterów i limitu 3. Zapisane poprawne kalendarze nie były pobierane ponownie.
Problemowy dzień zwrócił później znaną poprawną strukturę z zerem ofert FR/RK,
a wszystkie zaplanowane źródła zostały uzupełnione. Nie nadano certyfikatu
starym publicznym cenom i nie uznano błędu za brak dostępności.

Telemetria potwierdza limit Google 3 (rodziny kolejno FR/RK, IB/I2, VY, UX),
bezpośrednie źródła do 2 i ich rzeczywistą pracę równolegle z Google.
Aktywny czas obu podejść źródeł: 2389,56 s, w tym wznowienie 1044,66 s;
bez przerwy na decyzję, budowania i testów. Nie ma porównawczego pomiaru
Google=2, więc nie wyliczamy procentowego przyspieszenia.

Po kompletnym źródle wszystkie dziesięć builderów pracowało kolejno wyłącznie
z cache. Odbiór: 259 testów Python oraz 45 testów JS na stagingu i po lokalnej
promocji, bez pominiętych. Dodatkowo osobny fixture offline sprawdził wszystkie
dziesięć builderów przy całkowicie zablokowanym transporcie HTTP; nie posłużył
za aktualne dane. Nowe 20 plików odpowiada stagingowi bajtowo, backup starego
kompletu odpowiada niezależnemu baseline, a 23 lokalne zasoby HTTP zwracają
te same bajty. Pierwszy odbiór był bez commita/push ani zmian Actions; następnie
24.10.2026 użytkownik osobno autoryzował wysłanie całego pakietu na GitHub.
Odbiór wizualny
desktop/320 px i realnego schowka pozostaje otwarty: sterowanie przeglądarką
jest wyłączone w Work. Szczegóły i ścieżki dowodów:
[`WDROZENIE_SZCZECINA_I_ZIELONEJ_GORY_SZZ_IEG.md`](WDROZENIE_SZCZECINA_I_ZIELONEJ_GORY_SZZ_IEG.md).
