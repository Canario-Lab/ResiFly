# Bezpieczne zbieranie i publikowanie cen

Zabezpieczenia działają w lokalnych kolektorach. Nie wymagają GitHub Actions
i nie wprowadzają szóstego kroku wyszukiwania. Kanoniczne listy tras, zakres
dat, obydwa kierunki, zniżki i filtrowanie cen na stronie pozostają bez zmian.

## Ryanair

Wspólna funkcja w `scripts/collect_step2.py` jest używana przez kroki 1A–1F,
2, 3 i 5. Pobiera własny indeks aktywnych dat przewoźnika i pełną dostępność,
bez ograniczania dat rozkładem drugiej linii. Sprawdza obecność wszystkich
oczekiwanych aktywnych dni w odpowiedzi. Zachowuje wszystkie zwrócone
bezpośrednie loty mające dostępną taryfę, także różne godziny tego samego dnia.

Po błędzie pełnego okna próbuje tych samych pełnych danych z elastycznością
dat ustawioną na zero, osobno dla aktywnych dni tego okna. Nie ponawia już
poprawnie zebranych okien. Po niepowodzeniu przerywa aktualizację i podaje
trasę oraz datę. Nie traktuje HTTP 400/404 indeksu dat jako potwierdzenia
braku połączenia; prawidłowa lista `[]` jest dopuszczalna.

Fare Finder nie jest źródłem zastępczym do publikacji: minimum miesięczne
pomija dni, a minimum dzienne może pomijać inne godziny. Dawne wejście
`collect_ryanair_farefinder_dates` zawsze zgłasza blokadę, zamiast wysyłać
zapytanie i poświadczać niekompletny wynik.

To zabezpieczenie nie omija odmowy przewoźnika ani nie gwarantuje dostępności
API. Jeżeli pełne źródło odrzuca również zapytanie dzienne, aktualizacja
pozostaje zablokowana. Inne źródło zastępcze wymaga osobnej weryfikacji
kompletności godzin i cen, nie tylko znalezienia jednej oferty.

## Binter

Istniejące ograniczone ponowienia HTTP zostają. Po ich wyczerpaniu błąd
propaguje się z trasą i datą; nie jest zamieniany na pustą listę. Walidowane
są błędy GraphQL, `booking_search`, struktura dostępności, trasa i data.
HTTP 200 z `errors`, brakującą dostępnością lub komunikatem typu ERROR/FATAL
nie jest poprawnym pustym dniem.

Poprawna pusta dostępność i wyprzedane taryfy (`seats=0`) są dozwolone.
Punkty lojalnościowe `PTS` są celowo pomijane, a taryfy pieniężne EUR są
przetwarzane niezależnie. Nieprawidłowa taryfa gotówkowa blokuje wynik.

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
