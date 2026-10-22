# Bezpieczne zbieranie i publikowanie cen

Zabezpieczenia działają w lokalnych kolektorach. Nie wymagają GitHub Actions
i nie wprowadzają szóstego kroku wyszukiwania. Kanoniczne listy tras, zakres
dat, obydwa kierunki, zniżki i filtrowanie cen na stronie pozostają bez zmian.

## Ryanair

Wspólna funkcja w `scripts/collect_step2.py` jest używana przez kroki 1A–1F,
2, 3 i 5. Od decyzji z 22.10.2026 jedynym bieżącym źródłem numerów, dat,
godzin i indywidualnych cen Ryanaira jest Google Flights HTTP. Każda zapisana
trasa jest pytana osobno o każdy dzień pełnego okna, niezależnie od rozkładu
drugiej linii. Parser zachowuje wszystkie bezpośrednie oferty z kodami `FR`
oraz Ryanair UK `RK`, także kilka godzin tego samego dnia.

Wszystkie zapytania Ryanaira są ograniczone do dwóch równoległych wywołań.
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

Obowiązuje wspólny limit dwóch równoległych zapytań, także gdy `--workers`
jest większy. Błąd źródła zatrzymuje dalsze zapytania; pozostały aktywny
wątek może dokończyć swoją próbę. Pusty, poprawnie sprawdzony dzień jest
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
  Wszystkie dziesięć feedów otrzymuje to samo `RESIFLY_COLLECTION_RUN_ID`.
- `validate_batch` wymaga zgodności raportu w feedzie i sidecarze, bieżącego
  planu tras/dni oraz wspólnego `run_id`, oprócz walidacji okna, kursów,
  odcinków i wyników. Brak raportu lub pomieszanie uruchomień blokuje zapis.
- `promote_batch` sam ponownie waliduje zestaw przed pierwszą zmianą plików.
  Przy obsłużonym błędzie podmiany przywraca poprzednie pliki. Jak wcześniej,
  dziesięć podmian nie jest pojedynczą transakcją systemu plików odporną na
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

Obecnych publicznych JSON-ów nie zmieniono ani nie dopisano im poświadczeń.
Starszy staging GDN nie ma nowych raportów i wymaga nowego pełnego pobrania
przed kolejną promocją. Testy obejmują awarie źródeł, brak dnia, różne loty
jednego dnia i zachowanie poprzednich plików. Mały test żywych źródeł zwrócił
cztery loty Bintera TFN–MAD; Ryanair WMI–TFS odrzucił pełną dostępność także
przy próbie dziennej, co prawidłowo zablokowało wynik. Pełnej bazy ponownie
nie zbierano i nie wykonywano operacji Git.
