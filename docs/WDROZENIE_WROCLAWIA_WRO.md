# Wrocław (WRO) — lokalne wdrożenie

Data rozpoczęcia: **2026-10-23**, strefa `Atlantic/Canary`.
Punkt odniesienia: `ac15154cfb6a55c3b54f0d51528e55864cfd4737`.
Gałąź przygotowania: `codex/add-wroclaw-wro`. Etap lokalny przeprowadzono bez
commitów i bez push, zgodnie z pierwotnym poleceniem. Następnie 2026-10-23
użytkownik zlecił wysłanie całego pakietu na GitHub; docelowa gałąź to `main`.

## Status

WRO wdrożono lokalnie, z nowym kompletem dziesięciu feedów po pełnej kolekcji
i walidacji. Strona korzysta z bazy 2026-10-23–2026-11-22, zawierającej
**14 150 propozycji, w tym 2257 dla WRO**. Publikacja repozytorium została
następnie autoryzowana przez użytkownika; obejmuje kod, konfigurację,
dokumentację, testy i wszystkie dziesięć feedów wraz z sidecarami. Lokalne
cache, kopie bezpieczeństwa i surowe pliki robocze `tmp/` nie należą do pakietu.
Testy kodu i logiki interfejsu przeszły. Końcowego wizualnego odbioru nowej
bazy w przeglądarce nie wykonano: sterowanie lokalną przeglądarką zostało
wyłączone w ustawieniach Work. Nie jest on zastępowany deklaracją sukcesu
testu wizualnego. Lokalny serwer odpowiada pod `http://127.0.0.1:8000/`.

## Zakres konfiguracji

Kanoniczny rejestr zawiera WAW, WMI, KTW, KRK, GDN, WRO. Strefa WRO:
`Europe/Warsaw`. Zsynchronizowano dziewięć scope; zachowano pięć kroków
głównych i dziesięć feedów. Nie ma odrębnego feedu Wrocławia.

| Wariant | Zatwierdzony dodatek WRO |
| --- | --- |
| 1A Binter | LPA przez Wizz; MAD, PMI, SVQ, VLC przez Ryanair. Wykonawca nadal sprawdza pełną macierz wszystkich hubów i obu linii. |
| 1B Iberia/Express | MAD przez Ryanair; wykonawca low-cost nadal sprawdza obie linie i pełny zakres. |
| 1C Vueling | ALC, SVQ, VLC przez Ryanair; BCN i BIO przez Wizz; AGP przez obie linie. |
| 1D Air Europa | MAD przez Ryanair i BIO przez Wizz. |
| 1E Volotea | BIO przez Wizz; drugi odcinek jest sezonowy, bez lotów w bieżącym oknie. |
| 1F Canaryfly | LPA przez Wizz. |
| 2 bezpośrednie | WRO ↔ TFN/TFS dla obu linii: pełna macierz, bez założenia dostępności lotu. |
| 3 Ryanair/Ryanair | AGA, AGP, BGY, BHX, BLQ, BOH, BRS, BVA, CRL, DUB, EDI, EMA, LBA, LPL, LTN, MAN, MRS, NAP, NCL, OPO, PSA, RAK, SNN, STN, SVQ, TSF, VLC. |
| 4 Wizz/Wizz | BUD. |
| 5A Ryanair na Teneryfie / Wizz w Polsce | AGP, BUD, EIN, LTN. |
| 5B Wizz na Teneryfie / Ryanair w Polsce | Brak kwalifikującej się nowej pary WRO w sprawdzonej siatce; nie tworzono sztucznego wariantu. |

Zachowano wszystkie poprzednie rekordy tras istniejących pięciu endpointów
oraz ich numery/czasy/override Wizz. Porównanie maszynowe po odjęciu dopisków
WRO wykazało równość tych rekordów z baseline. Wyjątek transferowy
GDN/5B/KRK pozostał bez zmiany; GDN jako transfer do WRO jest niedozwolone.

## Dowody siatki i rozkładów

Aktualne oficjalne siatki Ryanaira i Wizz zapisano w
`tmp/wro-expansion/low-cost-snapshot.json`. Pełny materiał audytu znajduje się
w `network-snapshot.json`, `configuration-audit.json` oraz raportach discovery
w tym samym katalogu. Nadrzędne strony tras przewoźników rezydenckich
sprawdzono oddzielnie; nie zastępowano ich siatką Aeny.
Snapshot WRO zawiera 56 różnych sąsiadów Ryanaira i 27 Wizz Aira;
dozwolone przesiadki wyprowadzono z tych siatek, a nie z ręcznej listy
kilku spodziewanych kierunków.

- [Binter — destynacje](https://www.bintercanarias.com/es/destinos): przecięcie
  kwalifikujących się kierunków z siatką WRO nie dało nowego huba poza obecną listą.
  Zbiorczy `timetable_get` zwrócił GraphQL E01000, a kolejna próba timeout.
  Nie uznano tego za pustą dostępność. Snapshot wyraźnie oznacza podstawę
  tras Bintera jako zapisaną allowlistę i przegląd oficjalnych destynacji.
  Niezależna próba rzeczywistego kolektora cen TFN–MAD, 2026-10-24,
  poprawnie zwróciła cztery rejsy z końcowymi kwotami `booking_getImports`.
- [Iberia — Teneryfa–Madryt](https://www.iberia.com/es/vuelos-baratos/Tenerife-Madrid/),
  [Vueling — loty z Teneryfy](https://www.vueling.com/es/vuelos-baratos-desde-tenerife),
  [Air Europa — MAD](https://www.aireuropa.com/es-es/ofertas-de-vuelos-desde-tenerife-a-madrid)
  i [BIO](https://www.aireuropa.com/es-es/ofertas-de-vuelos-desde-tenerife-a-bilbao),
  [Volotea — TFS](https://www.volotea.com/en/direct-flights/from-tenerife-south/)
  i [Canaryfly — TFN–LPA](https://www.canaryfly.es/en/cheap-flights/tenerife-norte/gran-canaria)
  stanowiły właściwe źródła kontroli tras. Cen promocyjnych z tych stron
  nie przenoszono do bieżącej bazy.
- OVD/GRX i ACE/SPC/VDE ponownie sprawdzono w pełnych siatkach Ryanair/Wizz:
  brak odcinka do któregokolwiek z sześciu polskich endpointów. Nie dodano
  nowego huba jedynie na podstawie zmiany scope.

Numery i czasy techniczne Wizz zweryfikowano przez Google Flights HTTP,
sekwencyjnie, dla pełnego bieżącego okna i dodatkowych jawnie wskazanych
terminów tras sezonowych. Zapisano **171 obserwacji, 14 skierowanych par**
w `tmp/wro-expansion/verified-wizz-schedules.json`. Cały ten materiał
odtwarza się dokładnie przez produkcyjny resolver rozkładów.

Sezonowe WRO ↔ BIO potwierdzono w terminie 2026-12-19 jako W61879/W61880;
to dowód numerów i czasów, a nie cena lub lot dopisany do bieżącego okna.
WRO ↔ BBU, OTP i MAD nie otrzymały brakujących technicznych danych Wizz
z przeprowadzonych prób; nie aktywowano tych par Wizz. Pozostają
nieaktywne w bieżącym oknie, a ich przyszła aktywacja wymaga uzupełnienia
zweryfikowanych danych obu kierunków. Sam Ryanair WRO ↔ MAD jest dozwolony.

## Zmiany wykonawców

- Uogólniono narzędzia weryfikacji i generowania konfiguracji na jawny
  `--endpoint`, z kontrolą zgodności materiału i oddzielnymi kopiami do przeglądu.
- Wizz WRO–LPA o 13:45 ma 330 minut w poniedziałki i 325 minut w środy/piątki.
  Dodano zweryfikowane wyjątki według dnia tygodnia i możliwość wyjątku
  konkretnej daty, z pierwszeństwem data → dzień tygodnia → godzina → baza.
  Rejestr wspólny i lokalny Bintera zawierają zgodne dane.
- Runner nadaje nowemu runowi świeży plik cache Ryanaira, wspólny dla jego
  dziesięciu procesów. Wznowienie wymaga zgodnych dat i konfiguracji.
- Promocja obejmuje dwadzieścia plików: feedy i ich sidecary. Backup zachowuje
  informację o pierwotnym braku raportu; rollback odtwarza również ten stan.
- Raport batcha zawiera kierunki i warianty dla każdego endpointu oraz nadal
  osobno GDN jako transfer. Nie zmieniono sposobu generowania ID.
- W interfejsie dodano etykietę Wrocławia i opis sześciu lotnisk. Zachowano
  domyślne Polska → Teneryfa, 1000 zł, 6 h oraz najbliższy termin.

## Kolekcja i odbiór danych

Nowy run zakończył się w `tmp/wro-expansion/batch-2026-10-23`, dla okna
**2026-10-23–2026-11-22**. Wszystkie źródła pobrano według
bieżącej procedury, bez dopisywania wczorajszych lotów i cen. Google max 2;
snapshot NBP z 2026-10-23, zastosowany EUR/PLN **4.3917**.

Backup przed zmianą: `tmp/wro-expansion/baseline/`. Kopie poprzednich feedów
i manifest pierwotnej obecności sidecarów znajdują się dodatkowo w
`tmp/wro-expansion/batch-2026-10-23/previous-public-feeds/`.

Pierwsza próba 1C została poprawnie zatrzymana po wyczerpaniu retry dla
nieznanego formatu odpowiedzi Google WMI–BCN z 2026-11-13. Nie zmieniano
parsera ani nie uznawano tego dnia za pusty. Późniejsza pojedyncza kontrola
HTTP zwróciła zwykłe oferty z PLN. Wznowiono od 1C z tym samym run ID
`efa7d3ee-f865-4353-84a7-90b73f3eb21e` i cache; nie powtarzano 1A/1B.
Pierwotny log i raport błędu zachowano jako `step1c-first-attempt.*` w stagingu.
Analogicznie zatrzymała się pierwsza próba kroku 3 dla WRO–TSF,
2026-10-29 (`Unknown Google Flights Ryanair payload`). Zapisano
`step3-first-attempt.*` i wznowiono tylko 3/4/5 z tym samym cache, bez
ponawiania ukończonych wariantów kroku 1 i lotów bezpośrednich.

Wspólny run ID wszystkich dziesięciu feedów:
`efa7d3ee-f865-4353-84a7-90b73f3eb21e`.

| Feed | Wszystkie propozycje | WRO → Teneryfa | Teneryfa → WRO | Zakończone sprawdzenia pokrycia |
| --- | ---: | ---: | ---: | ---: |
| 1A | 2811 | 362 | 334 | 5208 |
| 1B | 2209 | 96 | 104 | 868 |
| 1C | 2623 | 202 | 195 | 3038 |
| 1D | 868 | 40 | 34 | 744 |
| 1E | 8 | 0 | 0 | 248 |
| 1F | 222 | 28 | 26 | 558 |
| 2 | 208 | 0 | 0 | 1488 |
| 3 | 4290 | 390 | 382 | 9610 |
| 4 | 204 | 10 | 12 | 1302 |
| 5 | 707 | 13 | 29 | 5084 |
| **Razem** | **14 150** | **1141** | **1116** | **28 148** |

Każdy raport ma `status=complete`, `missing_queries=0`,
`unexpected_queries=0` oraz zgodny sidecar. W Canaryfly 558 pozycji obejmuje
434 bazowe pozycje i 124 szczegółowe sprawdzenia dostępnych dni.
Ryanair ma 13 020 unikalnych sprawdzonych dni tras we wspólnym cache,
wykorzystywanych w kolejnych feedach tego samego runu.

Brak wyniku WRO w 1E wynika z sezonowego WRO–BIO; brak w kroku 2 jest
wynikiem pełnego skanu bezpośredniej macierzy, nie pominięcia WRO. W kroku 5
WRO ma 42 wyniki wariantu A przez EIN/BUD/LTN. Wariant B nie ma
kwalifikującej się nowej pary WRO w zweryfikowanej siatce. Przykładowo
allowlistowany AGP w 5A jest sprawdzony, ale w tym oknie nie dał pasującej
przesiadki. Pozostawiono te uprawnienia na kolejne kolekcje.

Wyniki starych endpointów: WAW 2041, WMI 1913, KTW 799, KRK 5155,
GDN 1985. Zachowano także **7** połączeń z GDN jako transferem do KRK.
Żaden wynik WRO nie używa GDN lub WRO jako transferu.

Lokalna promocja objęła wszystkie 20 plików: dziesięć feedów i dziesięć
raportów. Ponowna walidacja publicznego `data/` oraz porównanie bajtowe
z kompletnym stagingiem potwierdziły zgodność całego zestawu. Przy domyślnych
filtrach rezydenta, 1000 zł i 6 h baza zawiera 153 propozycje WRO → Teneryfa
oraz 174 Teneryfa → WRO. Droższe wyniki pozostają w plikach danych.

## Testy

**165 testów Python — OK**, uruchomionych ponownie po zakończeniu zmian kodu.
**14 testów JS — OK** na rzeczywistych nowych danych zarówno w stagingu,
jak i po lokalnej promocji do `data/`.
Testy Python obejmują nowe trasy, niezależne kalendarze, właściwe przypisanie
linii, stare endpointy, wyjątek GDN, godziny/dni Wizz, izolację cache oraz
podmianę i rollback sidecarów. Kontrola składni i `git diff --check` przeszły.

Testy JS obejmują WRO w obu kierunkach i czterech kombinacjach resident/WDC,
minima kalendarza i wykresu wskazujące tę samą kartę, wszystkie osiem
sortowań, czyszczenie chipów, link udostępniony (również ponad 1000 zł),
domyślne filtry, `+1`, dezaktywację drugiej linii przy lotach bezpośrednich
oraz przełączanie rezydenta w linku Air Europa. To testy produkcyjnego
`app.js` z lekkim dublerem DOM, nie test wizualny prawdziwej przeglądarki.

Sprawdzono linki wszystkich 28 092 wystąpień odcinków; Ryanair/Wizz mają
deterministyczny adres zgodny z trasą i datą, a parametry nie zawierają
tokenów, cookies lub sesji. Wszystkie 171 obserwacji technicznych Wizz
odtwarzają się dokładnie; wcześniejsze trasy i godzinowe wyjątki pozostałych
pięciu endpointów są identyczne z baseline.

HTTP lokalnego serwera: `200 OK`; odczyt wszystkich dziesięciu feedów przez
port 8000 daje dokładnie te same bajty co zwalidowane lokalne pliki i to samo
ID kolekcji. Próba końcowego otwarcia nowej bazy przez
sterowanie przeglądarką zwróciła `Local browser use is disabled in Work
settings`, dlatego wizualna kontrola WRO pozostaje do wykonania ręcznie
lub po ponownym włączeniu tej funkcji. Nie pobierać z tego powodu bazy ponownie.
