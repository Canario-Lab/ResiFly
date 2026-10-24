# Ręczna aktualizacja częściowa tras

Decyzja użytkownika 24.10.2026. Osobny tryb utrzymania tej samej sześciokrokowej
bazy, bez commita, push ani zmian Actions. Pełny batch nadal pobiera wszystko od zera.

## Przebieg

1. Sprawdza kompletny batch rodzica: źródła, certyfikat i hashe, feedy,
   coverage, okres, identyfikator i zapisaną konfigurację.
2. Planuje wyłącznie wskazane pary przewoźnik/lotniska: zawsze oba kierunki
   i każdy dzień okna rodzica, niezależnie od kalendarza innej linii.
3. Tworzy nowy staging i ID. Kopiuje pozostałe obserwacje z ich prawdziwym
   pochodzeniem, bez zmiany manifestu, danych i certyfikatu rodzica.
4. Pobiera tylko wybrane kalendarze dotychczasowymi adapterami. Google ma
   współdzielone 3 próby HTTP, rodziny kolejno; oficjalne źródła do 2.
   Zachowuje dotychczasowe retry i automatyczne odzyskiwanie.
5. Buduje wszystkie 11 feedów bez sieci. To przeliczenie konsumentów, nie
   ponowne pobieranie linii. Usunięty lot znika ze wszystkich zależnych
   propozycji; zmieniona cena trafia do wszystkich właściwych kroków.
6. Waliduje 22 pliki. Jawna promocja ma blokadę jednego publikującego,
   porównanie publicznej bazy z rodzicem i rollback po błędzie podmiany.

## Domyślny podgląd — bez HTTP i podmiany bazy

```bash
.venv/bin/python scripts/incremental_update.py \
  --base-batch tmp/easyjet-expansion/batch-20261024-v2 \
  --base-ref 23b993f --route 'Wizz Air:WAW:NCE'
```

Ta istniejąca trasa daje 62 logiczne obserwacje (31 dni, oba kierunki),
35 464 zachowane z rodzica. Nie jest to 62 gwarantowanych żądań HTTP:
Wizz ma zakresy regular/WDC, inne źródła własne operacje i retry.

Rzeczywiste pobranie **wyłącznie wybranych tras**, bez publikacji:

```bash
.venv/bin/python scripts/incremental_update.py \
  --base-batch tmp/easyjet-expansion/batch-20261024-v2 \
  --base-ref 23b993f --route 'Wizz Air:WAW:NCE' \
  --stage-directory tmp/partial-waw-nce --collect
```

Po zgodzie na podmianę lokalnej bazy można dodać `--promote` albo promować
zwalidowany staging przez istniejący runner `collect_five_steps.py`
z `--validate-only --promote` i dokładnym okresem rodzica. Bez commita/push.
Każda nowa próba wymaga pustego stagingu, nie nadpisuje rodzica.

`--route` można powtarzać. Obsługiwane nazwy: Ryanair, Wizz Air, Binter,
Canaryfly, Iberia, Vueling, Air Europa, Volotea, easyJet. Nie zmienia się
zatwierdzonego źródła cen. Wizz zachowuje regular/WDC, Binter i Canaryfly
końcowe ceny oficjalne, pozostałe uprawnione linie dotychczasowe szacunki.

## Pochodzenie i wiek

- `sources/provenance.json` mapuje każdą obserwację, także poprawne zero,
  na pierwotne pobranie. Jego hash jest w certyfikacie razem z hashami JSONL.
- Publiczne `data_lineage` jest jednakowe we wszystkich feedach i sidecarach:
  rodzic, rewizja, data częściowej aktualizacji i pełnej bazy, zakresy czasów
  źródeł oraz pochodzenie kursów. Dzień coverage ma `observation_run_id`,
  odcinek `source_observation_run_id`.
- Dla starszego pełnego batcha przedział obserwacji biegnie od początku
  telemetrii do wygenerowania ostatniego feedu. To przedział, nie wymyślony
  czas każdej odpowiedzi. Kolejne aktualizacje zachowują te pierwotne daty.
- Dziedziczone obserwacje mogą mieć najwyżej 24 godziny, liczone od początku
  przedziału. Starsza baza wymaga pełnego odświeżenia.
- Kursy pozostają zamrożonym snapshotem NBP rodzica, nie nowym kursem.
- Strona pokazuje „Aktualizacja częściowa … · pełna baza …”. Przebudowanie
  plików dziś nie oznacza, że dziś sprawdzono wszystkie ceny.

## Konfiguracja i brakujące trasy

Istniejące zapisane trasy wszystkich obsługiwanych źródeł można odświeżać.
Obsługiwane dodanie nowej trasy jest celowo wąskie: zweryfikowana para
przewoźnik/Polska/hub w **kroku 6**, przy już zatwierdzonym hubie, oraz dane
Wizza wyłącznie dla wybranych kierunków. Najpierw niezależnie potwierdzić
numery, czasy blokowe i wyjątki, potem aktywować parę w allowliście.
Aktualizator sam tego nie odkrywa, nie aktywuje i nie zgaduje.

KRK↔NCE zweryfikowano 24.10.2026 w oficjalnym rozkładzie Kraków Airport:
W62071, 140 minut do Nicei; W62072, 130 minut do Krakowa. Dane obejmują
sobotę 24.10 oraz zimowe rotacje środa/niedziela. Pełny kalendarz i ceny
są nadal pobierane bezpośrednio z Wizza, niezależnie od kalendarza easyJet.

### Pierwsze rzeczywiste uzupełnienie KRK↔NCE — 24.10.2026

- Run `8d963abb-a306-4a75-a4cd-8d89cb06db51`, rodzic
  `c86f6042-3364-4a5a-b480-802960801080`, okno 24.10–23.11.2026.
- Pobrano bezpośrednio z Wizza pełne kalendarze obu kierunków oraz ceny
  regular/WDC: 62 ukończone obserwacje dni, 19 rejsów (9 KRK→NCE,
  10 NCE→KRK). Wszystkie 5 prób HTTP200, błędów 0, równolegle najwyżej 2.
  Google ani inne kalendarze nie były ponownie odpytywane.
- Zachowano 35 526 obserwacji rodzica. Po przebudowie 11 feedów krok 6
  ma 2188 propozycji, o 4 więcej: TFS→NCE→KRK. Łącznie 18 201 propozycji.
  Porównanie po ID potwierdziło niezmienione wszystkie dotychczasowe
  połączenia i ich ceny; nowe propozycje spełniają limit 2–24 h przesiadki.
- Ukończono walidację źródeł i wszystkich 22 plików (brakujących 0),
  a następnie podmieniono lokalną bazę z zachowaniem backupu.
- Wcześniejszy błąd strony rezerwacji Wizza nie jest dowodem awarii API
  kalendarza. Tego widoku nie sprawdzano ponownie podczas uzupełnienia.
  API dostarczyło daty/wyloty/ceny; numery i czasy blokowe potwierdzono
  oddzielnie w oficjalnym rozkładzie Kraków Airport.

Dowody lokalne: `tmp/partial-krk-nce-20261024/` — `performance.json`,
`source-coverage.json`, `validation-report.json`, `sources/provenance.json`
oraz backup poprzedniej publicznej bazy. Dane testowe nie były publikowane.

Inne zmiany endpointów, hubów, źródeł, opłat/zniżek i niezwiązanych rozkładów
są odrzucane. Brak niewybranego kalendarza w rodzicu blokuje plan, bez cichego
rozszerzenia pobierania. Błąd nie staje się zerem. Same publiczne JSON-y bez
kompletnego prywatnego repozytorium nie wystarczają jako rodzic.

Nowe pełne batch'e archiwizują konfigurację. Dla starszych `--base-ref`
odczytuje tylko JSON-y z Gita i wymaga zgodności ich zbiorczego hasha z
oryginalnym manifestem. Nie uruchamia starego kodu i nie przepisuje hashy.

## Ograniczenia

Świadomie zachowane starsze ceny nadal mogą zmienić się u przewoźnika.
22 podmiany z rollbackiem nie są pojedynczą transakcją odporną na odcięcie
zasilania. CLI nie wznawia nieudanego częściowego runu: staging pozostaje
do audytu, następna próba ma nowy katalog i pobiera tylko wskazane trasy.
Zmiana publicznej bazy w międzyczasie blokuje promocję starej rewizji.
