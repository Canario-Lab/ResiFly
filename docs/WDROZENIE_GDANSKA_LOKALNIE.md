# Gdańsk GDN — lokalne wdrożenie, 22 października 2026

Wyłącznie praca lokalna. Nie utworzono gałęzi, commita, PR ani wdrożenia i nie
wykonano push. Punktem odniesienia jest HEAD
`52d504872547341e857ab6b30cb5ad2ea928d00a`.

## Zakres konfiguracji

Polskie endpointy: WAW, WMI, KTW, KRK, GDN. Wspólny rejestr
`data/search-airports.json` jest czytany przez kolektory i detektor; wszystkie
dziewięć allowlist ma zgodny scope. GDN ma strefę `Europe/Warsaw`.
Nadal jest dokładnie pięć kroków głównych oraz warianty 1A–1F, łącznie 10 feedów.
Nie utworzono osobnego feedu Gdańska.

| Wariant | Potwierdzony zakres dodatków GDN |
| --- | --- |
| 1A Binter | MAD, PMI; Ryanair i Wizz Air na odcinku do/z GDN |
| 1B Iberia/Express | MAD; Ryanair i Wizz Air |
| 1C Vueling | AGP, ALC, BCN; Ryanair i Wizz Air |
| 1D Air Europa | MAD; Ryanair i Wizz Air |
| 1E Volotea | Brak kwalifikującego się nowego odcinka GDN; BIO/WAW/KRK pozostaje bez zmian |
| 1F Canaryfly | Brak kwalifikującego się nowego odcinka GDN; dotychczasowe FUE/LPA bez zmian |
| 2 bezpośrednie | Pełna macierz 20 kierunkowych par na linię, 40 kombinacji para/linia; GDN ↔ TFN/TFS, Ryanair i Wizz |
| 3 Ryanair/Ryanair | AGA, AGP, BGY, BRS, BUD, BVA, DUB, EDI, EMA, FCO, LBA, LPL, MAN, MXP, NAP, NCL, OPO, PSA, STN, TSF |
| 4 Wizz/Wizz | BUD, FCO, MXP |
| 5A Ryanair na Teneryfie / Wizz w Polsce | AGA, AGP, BUD, EIN, FCO, LTN, MXP |
| 5B Wizz na Teneryfie / Ryanair w Polsce | BUD, FCO, MXP, OTP |

OTP jest nowym hubem **wariantu 5B**. Przewoźnik odcinka TFS–OTP to Wizz,
a OTP–GDN to Ryanair. Nie oznacza to aktywacji Wizz GDN–OTP w kroku 4.

Zachowano starą przesiadkę KRK ↔ GDN ↔ TFS w wariancie 5B. Wyjątek GDN/KRK
jest jawny w rejestrze endpointów. Macierze, detektor i walidatory odrzucają
self-route GDN–GDN. Nie rozszerzono innych ról polskich endpointów jako hubów.
Porównanie konfiguracji z HEAD nie wykazało usuniętych par ani dodatków
niezwiązanych z nowym endpointem GDN.

## Źródła i techniczne rozkłady Wizz

Oficjalne siatki Ryanair/Wizz zapisano w lokalnym
`tmp/gdn-expansion/network-snapshot.json`. Nadrzędne źródła linii rezydenckich
pozostają te same; nie dodano niekwalifikujących się hubów.

- Binter: https://www.bintercanarias.com/es/destinos — przecięcie pełnej listy
  kierunków z GDN nie dało dodatkowego kwalifikującego się huba poza MAD/PMI.
- Vueling: https://www.vueling.com/es/vuelos-baratos-desde-tenerife — także
  ponowny przegląd OVD/GRX; GDN nie ma wymaganego odcinka Ryanair/Wizz.
- Air Europa: oficjalne strony MAD/BIO i branded fare feed.
- Volotea: oficjalne bezpośrednie trasy i MinPrice; brak GDN–BIO/OVD.
- Canaryfly: oficjalne trasy i kalendarze GraphQL; brak odpowiedniego odcinka
  GDN do wysp obsługiwanych przez tę linię, także ACE/SPC/VDE.

Zweryfikowano przez Google Flights HTTP numery, lokalne godziny i czasy
blokowe Wizz dla 24 skierowanych par: GDN w obu kierunkach z AGA, AGP, ALC,
BCN, BUD, EIN, FCO, LTN, MAD, MXP, PMI i TFS. Dowody:
`tmp/gdn-expansion/verified-wizz-schedules.json`.
Rejestr obejmuje warianty numerów **i czasów blokowych** zależne od godziny.
Potrzebne wpisy MAD/PMI są również w lokalnych danych 1A/1B.

GDN–TFS: W61709, 355 minut; TFS–GDN: W61710, 335 minut. To świadoma
aktualizacja poprzednich zapisanych 365/330 minut według bieżącego rozkładu.
Dotychczasowe cztery wpisy WAW/KTW ↔ TFS przeniesiono bez zmiany wartości
z kodu kroku 2 do wspólnego rejestru.

Nieaktywowane: Wizz GDN ↔ BBU i GDN ↔ OTP. Oficjalna mapa je wymienia, ale
pełny kalendarz 22.10–21.11.2026 nie zwrócił lotów w żadnym kierunku.
Nie wymyślano dla nich numerów ani czasów; detektor pozostawia je w pending.
Przy ich późniejszej aktywacji trzeba zweryfikować oba rozkłady i rozszerzyć
allowlistę. To ograniczenie należy odróżniać od potwierdzonego wariantu 5B OTP.

## Poprawki kompletności i bezpieczeństwa

- 1A/1B odpytuje Wizz przed oceną brakujących danych technicznych. Aktywny
  nieznany rozkład kończy się błędem, nie cichym pustym wynikiem.
- Wizz `400 InvalidMarket` oznacza brak rynku; błędy źródła są ponawiane i
  propagowane, nie publikowane jako brak dostępności.
- Usunięto starszy problem wspólnego helpera Ryanaira 1A–1F: Fare Finder
  zwracał najtańszą ofertę całego zakresu, nie pełny kalendarz. Warianty te
  korzystają teraz z tego samego wykonawcy co krok 2: active-dates,
  availability. Pierwsze odświeżenie dopuszczało awaryjny Fare Finder
  osobno dla każdego aktywnego dnia. Późniejsze uszczelnienie opisane w
  `docs/COLLECTION_RELIABILITY.md` zabrania również tego dziennego minimum:
  wymaga pełnej dostępności lub blokuje publikację. Zapisanych poniżej
  wcześniejszych wyników nie wyposażono w nowe raporty kompletności.
- Wersja klienta Ryanair jest ustalana raz na proces 1A–1F, z blokadą dla
  wątków. Nie wpisano numeru na stałe. Dynamiczna obsługa wersji Wizz pozostaje.
- Google Flights nadal ma limit 2 równoległych zapytań; każdy wariant
  rezydencki skanuje pełne niezależne kalendarze przed dopasowaniem low-cost.
- Wszystkie kroki korzystają z jednego dziennego snapshotu NBP
  `tmp/nbp-rates/2026-10-22.json`. Zniżki i ceny WDC pozostają osobnymi polami.
- Brak cenowego odrzucania ofert w kolektorach. Limit ceny stosuje strona.
- Deterministyczne booking URL pozostają na odcinkach; nie zapisano tokenów
  ani cookies. Nie zmieniono dopuszczalnego czasu przesiadki 120–1440 minut.

## Kolekcja i wycofanie

Wspólne okno: **2026-10-22–2026-11-21**, domknięte, 31 dat zgodnie z
dotychczasowym `--days 30`. Staging: `tmp/gdn-expansion/staging`.

`scripts/collect_five_steps.py` waliduje wszystkie 10 feedów: schema i krok,
okno, datę wygenerowania, wspólne kursy, globalną unikalność ID, endpointy,
ciągłość i chronologię odcinków, ceny, linki oraz przesiadki. Opcja
`--refresh-steps` może przeliczyć wybrane warianty, ale końcowa walidacja
zawsze obejmuje cały zestaw. Nie ogranicza ona kalendarza żadnej trasy.

Lokalna podmiana `--validate-only --promote` jest możliwa dopiero po poprawnej
walidacji. Najpierw przygotowuje wszystkie nowe pliki i zachowuje poprzednie
w `tmp/gdn-expansion/staging/previous-public-feeds`. Błąd podmiany przywraca
poprzedni stan. Nie jest to jedna atomowa operacja na 10 plikach.
Pierwsza kopia zapasowa nie jest nadpisywana przy kolejnej podmianie.
Nie poprawiano ręcznie wygenerowanych wyników JSON.

W pierwszym przebiegu krok 5 napotkał HTTP 403 Ryanaira; cały feed pozostał
niepodmieniony. Po potwierdzeniu przywróconej dostępności pełny krok 5
zakończył się poprawnie z dwoma workerami. Nie obchodzono zabezpieczeń linii.
Warianty 1A–1F przeliczono ponownie po poprawieniu pełnego kalendarza Ryanaira.

## Testy i kontrola strony

- Python: **104 testy, OK**, w tym GDN w obu kierunkach, oba warianty 5,
  stare połączenie przez GDN, zachowanie ID/kwot starej czwórki na tych samych
  wejściach, kompletność zakresu wywołań, błędy źródeł, granice 119/120 i
  1440/1441 minut, północ, zmiana czasu i wycofanie nieudanej podmiany.
- JavaScript: **8 testów, OK**, produkcyjna logika `app.js` z rzeczywistymi
  feedami. Filtry GDN, osiem sortowań, minima dat dla czterech kombinacji
  resident/WDC, oba zestawy chipów X, wspólny cel kalendarza i wykresu,
  link do konkretnego lotu, `+1` i wyłączenie drugiej linii dla lotów direct.
- Sprawdzono źródła Python przez compileall oraz `git diff --check`.
- W zewnętrznym Chrome sprawdzono GDN jako przylot i wylot, X → wszystkie,
  ponowny wybór GDN, kalendarz → właściwa karta oraz słupek → ta sama oferta.
  Kopiowanie linku i jego otwarcie po przeładowaniu odtworzyło właściwą kartę.
- Okno zakupu pokazało trwałe linki TFN–AGP Vueling i AGP–GDN Wizz z prawidłową
  datą. Nie wykonywano rezerwacji ani zakupu.
- Dla GDN → Teneryfa, 23.10, przy limicie przesiadki 6 h, porównano ceny
  w danych i Chrome: regularna 956,88 zł, rezydent 755,97 zł, WDC 910,88 zł,
  obie zniżki 709,97 zł (stan ofert podczas pierwszej kontroli).
- Sortowanie po czasie ustawiło na początku pięć bezpośrednich lotów
  po 5 h 55 min, dalej 8 h 20 min, 8 h 50 min, 9 h itd.; nie tylko przewinęło
  do jednej karty. Domyślny najbliższy termin pozostał bez zmian.
- Sprawdzono układ w węższym oknie Chrome: filtry i karta przechodzą do
  układu jednokolumnowego. To kontrola responsywności, nie test na telefonie.
  Nie zmieniano CSS, `app.js`, rozmiaru batcha ani limitów cache kart.

Zrzuty lokalne: `tmp/gdn-expansion/chrome-gdn-card.png` oraz
`tmp/gdn-expansion/chrome-gdn-narrow.png`. Końcowy podgląd po ponownej
kolekcji: `tmp/gdn-expansion/chrome-gdn-final.png`. Finalna baza w Chrome
pokazała 812 propozycji przy ustawieniach domyślnych oraz 83 po wybraniu
przylotu GDN (rezydent, limit przesiadki 6 h). Kliknięcie 23.10 ponownie
otworzyło właściwy lot za 634,83 zł. Liczby te są po filtrach, nie oznaczają
liczebności całej bazy.

## Końcowy raport danych

**Zakończono lokalnie.** Całe 10 feedów przeszło walidację i zostało
podmienione razem po ponownej kolekcji 1A–1F z pełnym Ryanairem.
Ich zawartość jest identyczna ze stagingiem. Wszystkie 10 kopii poprzednich
feedów jest identycznych z bazowym HEAD, co sprawdzono porównaniem bajtów.

| Wariant | Wszystkie propozycje | GDN → Teneryfa | Teneryfa → GDN | Poprzednie cztery endpointy |
| --- | ---: | ---: | ---: | ---: |
| 1A | 2000 | 92 | 85 | 1823 |
| 1B | 1870 | 219 | 213 | 1438 |
| 1C | 2011 | 181 | 163 | 1667 |
| 1D | 639 | 66 | 75 | 498 |
| 1E | 6 | 0 | 0 | 6 |
| 1F | 167 | 0 | 0 | 167 |
| 2 | 200 | 5 | 7 | 188 |
| 3 | 1628 | 169 | 171 | 1288 |
| 4 | 174 | 21 | 10 | 143 |
| 5 | 627 | 65 | 72 | 490 |
| **Razem** | **9322** | **818** | **796** | **7708** |

GDN jako endpoint: **1614 propozycji**, w tym **12 bezpośrednich Wizz**
(5 do Teneryfy i 7 do Gdańska). To propozycje połączeń, nie liczba odrębnych
samolotów; ten sam odcinek może wystąpić w różnych dopasowaniach.

Krok 5: wariant A ma 466 propozycji (GDN: 40 do Teneryfy, 32 do Polski),
wariant B ma 161 (GDN: odpowiednio 25 i 40). Dotychczasowy transfer GDN do
KRK dał 7 propozycji: 2 z Polski i 5 do Polski. Baseline zawierał 8; liczba
nie jest stałą, ponieważ pobrano aktualne ceny/rozkłady i zweryfikowano czas
GDN–TFS. Sama rola transferu i jej zatwierdzony zakres zostały zachowane.

Kontrola zakresu wykonania (pary są kierunkowe):

| Wariant | Pełny zakres pobierania |
| --- | --- |
| 1A | 120 par linia/trasa low-cost; 744 trasy/dni Bintera |
| 1B | 20 par linia/trasa low-cost; 124 trasy/dni Iberii |
| 1C | 70 par linia/trasa low-cost; 434 trasy/dni Vuelinga |
| 1D | 16 par linia/trasa low-cost; 124 trasy/dni Air Europa |
| 1E | 4 pary linia/trasa low-cost; 62 trasy/dni Volotei |
| 1F | 8 par linia/trasa low-cost; pełne kalendarze miesięczne, następnie 124 dostępne trasy/dni Canaryfly |
| 2 | 40 kombinacji para/linia |
| 3 | 256 tras Ryanair |
| 4 | 40 tras Wizz |
| 5 | 62 trasy Ryanair i 94 trasy Wizz |

Wariant 1E ma wyniki tylko Polska → Teneryfa, mimo skanu obu kierunków:
nie wymuszano fikcyjnych dopasowań w przeciwnym kierunku. Brak propozycji
GDN w 1E/1F wynika z braku kwalifikującego się drugiego odcinka.

Łącznie **112 testów: 104 Python + 8 JavaScript**, wszystkie poprawne.
Raport maszynowy: `tmp/gdn-expansion/staging/validation-report.json`.
Logi każdego pełnego skanu: `tmp/gdn-expansion/staging/step*.log`.
Wcześniejsze błędy HTTP nie zostały potraktowane jako poprawne puste kalendarze.

Pozostawiono bez zmian zastane nieśledzone obrazy
`assets/poland-tenerife-ticket-v1.png` i `assets/poland-tenerife-ticket-v3.png`.
Nie było zmian JS/CSS produkcyjnej strony ani operacji Git modyfikujących
repozytorium. Zmiany kodu, konfiguracji i danych pozostają niezatwierdzone
lokalnie do przeglądu użytkownika.

Serwer HTTP użyty do testów zakończono po weryfikacji. Chrome pozostawiono
na sprawdzonej stronie. Aby ponownie wczytać podgląd, w katalogu projektu
uruchomić `.venv/bin/python -m http.server 8000 --bind 127.0.0.1` i otworzyć
`http://127.0.0.1:8000/`. Nie wymaga to GitHuba ani publikacji.
