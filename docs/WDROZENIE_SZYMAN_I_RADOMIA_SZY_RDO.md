# Lokalne wdrożenie Szyman (SZY) i Radomia (RDO)

Data realizacji: **24.10.2026**. Status: **wdrożone i odebrane lokalnie**.
Użytkownik zatwierdził wdrożenie wyłącznie lokalne. Nie wykonano commita,
push ani zmian workflow GitHub Actions.
Powyższe zdanie opisuje pierwszy odbiór lokalny. Następnie 24.10.2026
użytkownik osobno autoryzował wysłanie całego pakietu SZY/RDO, nowego huba NRN
i wszystkich dziesięciu feedów z sidecarami na GitHub. Bez nowych workflow.

Podgląd: <http://127.0.0.1:8000/?build=szy-rdo-local-20261024>.
Wybierz Szymany i zwiększ limit przesiadki do **24 h**: przy 1000 zł jest
8 ofert Polska → Teneryfa i 18 w przeciwnym kierunku. Domyślnego limitu 6 h
nie zmieniono; obecnie ukrywa on wszystkie propozycje SZY.

Plan: [`PLAN_DODANIA_SZYMAN_I_RADOMIA_SZY_RDO.md`](PLAN_DODANIA_SZYMAN_I_RADOMIA_SZY_RDO.md).
Baseline HEAD `811599d64b93ed65f08563f56ad2e5fb8ac96eb1`, historyczna gałąź
`codex/add-lodz-lcj`. Zastane zmiany to README i nieśledzony plan tego zadania;
zachowano je w baseline. Brak innych zastanych zmian.

## Zakres i konfiguracja

- Rejestr 13: WAW, WMI, KTW, KRK, GDN, WRO, POZ, LCJ, RZE, BZG, LUZ, SZY, RDO.
  Nowe porty `Europe/Warsaw`. Dokładnie 5 kroków, 1A–1F jako warianty,
  10 feedów, 10 sidecarów i 9 allowlist.
- **SZY: krok 3 przez STN i zupełnie nowy NRN**. NRN ma TFS, wyłącznie SZY,
  Niemcy / `Europe/Berlin`, brak zniżki rezydenckiej, mnożnik 1.0.
  Nie rozszerzono NRN na pozostałe polskie endpointy.
- **RDO: brak zatwierdzonej topologii przesiadki** w obecnych rodzinach linii.
  Mimo tego pełne macierze 1A/1B/2 zawierają Radom i każdą wymaganą datę obu
  kierunków obu linii. Wyników zerowych nie wyprowadzono z awarii.
- GDN pozostał wyłącznie 5B/KRK,LUZ. Bez nowych polskich hubów, LOT-u,
  czarterów, dojazdów, zmiany lotniska w mieście i drugiej przesiadki.
- Stara jedenastka zachowała uprawnienia. Wszystkie dawne Wizz schedule,
  override, lokalne kopie 1A/1B i rejestr opłat pozostały niezmienione.
  Dowód: `tmp/szy-rdo-expansion/configuration-acceptance-report.json`.
- Poprawiono helper konfiguracji: techniczne schedule czyta z wybranego
  baseline, nie ukrytego live `data/`, co umożliwia łączenie dwóch rozszerzeń.
  Opisy obsługują również „dwanaście/trzynaście”. Review SZY następnie RDO,
  bez nadpisania nowych uprawnień pierwszego endpointu.
  Oddzielne review RDO→SZY dało równoważne 10 dokumentów (po normalizacji
  nieistotnej kolejności źródeł i listy wykluczeń), bez zmiany live danych.

## Faktyczny audyt siatek

Odczytano pełne oficjalne grafy Ryanaira i Wizza osobno dla obu portów,
nie tylko obecne huby. Wyniki z 24.10.2026:

| Endpoint | Ryanair | Wizz Air | Wspólne IATA low-cost z Teneryfą |
| --- | --- | --- | --- |
| SZY | NRN, STN | DTM | 3: NRN i STN z TFS; inne warianty brak |
| RDO | brak | BOJ, LCA, TIA | brak 3/4/5A/5B |

Każdy sąsiad nowych portów w pełnych grafach leży poza Hiszpanią. Przejrzano
oficjalne materiały sześciu przewoźników resident: [Binter](https://www.bintercanarias.com/es/destinos),
[Iberia](https://www.iberia.com/es/vuelos-baratos/Tenerife-Madrid/),
[Vueling](https://www.vueling.com/es/vuelos-baratos-desde-tenerife),
[Air Europa](https://www.aireuropa.com/es-es/ofertas-de-vuelos-desde-tenerife),
[Volotea](https://www.volotea.com/es/ofertas-vuelos/tenerife/) i
[Canaryfly](https://www.canaryfly.es/en/cheap-flights).
Brak polskiej nogi do kwalifikującego się hiszpańskiego/kanaryjskiego huba
wyklucza nowe uprawnienia w 1A–1F, niezależnie od ofert zagranicznych linii.
Nie ograniczono sprawdzenia do starych list ani nie dopisano fikcyjnej relacji.

Binter `timetable_get` ponownie zwrócił GraphQL **E01000** w obu audytach.
Oryginalny failed/source error zachowano, nie zamieniono go w complete lub
pustą dostępność. Odrębny oficjalny katalog i pełna topologia polskiej nogi
zamykają decyzję kwalifikacji. Niezależna kolekcja cen Bintera przez
`booking_search` oraz końcowe `booking_getImports` zakończyła się kompletnie
i przeszła własną walidację. Nie jest to naprawienie błędu discovery.
Ograniczenia dynamicznych stron ofertowych nie są dowodem pustego kalendarza.

Techniczny skan Wizza sprawdził wymagane bezpośrednie SZY/RDO↔TFN/TFS
przez pełne 31 dat i zwrócił poprawne zera wszystkich ośmiu tras. Nie było
nowych kwalifikujących się przesiadkowych nóg Wizza, więc nie dopisywano
numerów/bloków DTM/BOJ/LCA/TIA tylko dla istnienia wpisu. Każdy endpoint ma
własny plik dowodowy z zerem obserwacji, bez pending i bez skopiowanych danych LUZ.

Dowody lokalne: `tmp/szy-rdo-expansion/audit-SZY/`, `audit-RDO/`,
`route-decisions.json`, `verified-wizz-SZY.json`, `verified-wizz-RDO.json`,
`review-SZY/` i `review-SZY-RDO/`. Raw intersections zapisano przed interpretacją.

## Baza i bramki odbioru — ukończone

Poprzednia baza: 16 017 propozycji / komplet 11 endpointów,
run `f9323dee-9fdc-4e2f-8075-a39d53838115`. Kopia i manifest SHA-256 w
`tmp/szy-rdo-expansion/baseline/` i `baseline-manifest.json`.

Nowy batch:

- Okno **2026-10-24–2026-11-23** (31 dat).
- Run **`d98ec327-3fa9-40bd-9a9a-6da358c35bfa`**.
- Konfiguracja SHA-256 **`d1589d0bcd828adc06e799423e4bf7bec7b113a174b5fbe88d96cdaf086f4d49`**.
- Staging `tmp/szy-rdo-expansion/batch-2026-10-24`.
- Świeży współdzielony cache Ryanaira: dokładnie **19 282 unikalnych route/day**,
  wszystkie poprawne, wyłącznie `google_flights_http`, zbiór kluczy równy planowi.
  Bez starych cen/cache LUZ. Google max 2, kolektory sekwencyjnie, workers 2.
- Jeden zestaw NBP dla D, **EUR/PLN 4.3917**. Źródła cen, końcowe imports i estymaty z opłatami
  pozostają bez zmian, żadnego limitu cen w danych.
- Cały batch zakończył się przy pierwszym uruchomieniu, bez wznowienia.
  Dziesięć raportów osadzonych i dziesięć sidecarów jest zgodnych, kompletnych,
  ma jeden run ID i aktualny hash konfiguracji. Łącznie **39 308 pozycji pokrycia**,
  zero braków i nieoczekiwanych zapytań; **15 954 propozycje**.

| Feed | Kompletne pokrycie | Polska → Teneryfa | Teneryfa → Polska | Razem |
| --- | ---: | ---: | ---: | ---: |
| 1A | 10416 | 1460 | 1436 | 2896 |
| 1B | 1736 | 1139 | 1104 | 2243 |
| 1C | 3534 | 1501 | 1393 | 2894 |
| 1D | 744 | 450 | 433 | 883 |
| 1E | 248 | 8 | 0 | 8 |
| 1F | 558 | 110 | 115 | 225 |
| 2 | 3224 | 101 | 112 | 213 |
| 3 | 12090 | 2812 | 2833 | 5645 |
| 4 | 1364 | 121 | 95 | 216 |
| 5 | 5394 | 350 | 381 | 731 |

W 1F pokrycie to bazowe 434 zapytania i 124 zapytania szczegółów dostępnych
dni. Warianty kroku 5: A 553, B 178. Siedem propozycji z GDN jako hubem
dotyczy wyłącznie dozwolonego KRK/5B.

| Endpoint | Polska → Teneryfa | Teneryfa → Polska | Razem |
| --- | ---: | ---: | ---: |
| WAW | 1054 | 988 | 2042 |
| WMI | 973 | 968 | 1941 |
| KTW | 436 | 365 | 801 |
| KRK | 2584 | 2621 | 5205 |
| GDN | 1038 | 991 | 2029 |
| WRO | 1161 | 1166 | 2327 |
| POZ | 440 | 394 | 834 |
| LCJ | 98 | 121 | 219 |
| RZE | 140 | 143 | 283 |
| BZG | 96 | 96 | 192 |
| LUZ | 23 | 23 | 46 |
| SZY | 9 | 26 | 35 |
| RDO | 0 | 0 | 0 |

Wszystkie **35 propozycji SZY** pochodzą z kroku 3 przez STN. Pełne kalendarze
SZY↔STN zwróciły po 9 rejsów w każdym kierunku. Przesiadki mają 460–1215 min
(7 h 40 min–20 h 15 min); w kierunku z Polski minimum wynosi 17 h 30 min.
Ceny całych propozycji SZY: 165–1833 zł. Przy 1000 zł i 24 h pozostaje
8 propozycji z Polski i 18 do Polski; przy 6 h w obu kierunkach jest zero.

**NRN został wdrożony, ale nie dał teraz połączeń SZY.** Wszystkie cztery
kierunkowe kalendarze mają po 31 poprawnie sprawdzonych dni: SZY→NRN 0 rejsów,
NRN→SZY 0, NRN→TFS 22, TFS→NRN 22. Topologia nie gwarantuje dostępności
w danym oknie. Nie usunięto huba na przyszłość i nie wymyślono polskiej nogi.

**RDO jest pełnoprawnym trzynastym endpointem konfiguracji**, ale obecne
rodziny przewoźników nie dają kwalifikującej się przesiadki ani bezpośredniego
rejsu na Teneryfę. Wymagane pełne macierze zwróciły poprawne zera. Brak wyników
nie jest zastępstwem błędu żądania. Kompletność dotyczy poprawnego wykonania
kanonicznego planu i odpowiedzi źródeł, nie gwarantuje nieomylności zewnętrznej
wyszukiwarki ani wiecznej nieobecności trasy.

## Testy i UI

Końcowy zestaw: **246 testów Python i 42 JS**, bez pominiętych testów.
JS wykonano na kompletnym stagingu i ponownie po podmianie lokalnej publicznej
bazy. Test rzeczywistego batcha trzynastu przeszedł; nie został pozostawiony
jako skip na starej bazie. Testy strony obejmują pełne syntetyczne 13 opcji,
SZY/RDO osobno/OR, zero/jeden kierunek, kwoty/minima/karta, cztery zniżki,
osiem sortów, share i +1.

Testy nowych portów obejmują faktyczny nowy NRN end-to-end, pełne executory
przy pustych kalendarzach, odrzucanie coverage 11/12, granice 120–1440,
inne IATA, brak nowej zgody GDN, helper chain i zamrożone ELEVEN we wszystkich
dziesięciu builderach. Dawne historyczne SIX–TEN zachowano.

UI: etykiety Szymany / Olsztyn–Mazury (SZY), Radom (RDO), Weeze (NRN),
opis 13 portów i JS `20261024-szy-rdo-1`. Bez zmian CSS i domyślnych limitów;
domyślne Polska → Teneryfa / 1000 zł / 6 h / najbliższy termin pozostają.
Opcje multiselect pochodzą z rzeczywistych ofert obu kierunków: RDO=0 nie
tworzy fikcyjnego checkboxa. Na tej bazie jest **12 rzeczywistych opcji**,
w tym SZY; jeśli pojawią się oferty RDO, opcja powstanie automatycznie.

Odbiór prawdziwej lokalnej strony:

- Desktop 1280 px i rzeczywisty wąski panel około 319 px: długa etykieta SZY
  zawija się, menu ma przewijanie i dostępne ostatnie wiersze/przycisk Gotowe.
  Żądane wymuszenie dokładnie 320 px nie zadziałało w narzędziu IAB, więc nie
  zgłaszamy takiej emulacji jako wykonanej. Przy szerokości panelu 319 px
  pozostaje istniejące minimum strony 320 px; nie zmieniano globalnego CSS.
- OR SZY+LUZ, powrót do SZY, zachowanie wyboru po zmianie kierunku,
  8 wyników z Polski i 18 w przeciwnym kierunku przy 1000 zł / 24 h.
- Data kalendarza i odpowiadający jej słupek wskazują tę samą rozwiniętą
  kartę `step3-b738cabb00e80ed2`. Widoczne prawidłowe ceny i indeksy +1.
- Dwa osobne bilety: FR229 SZY–STN 30.10 i FR582 STN–TFS 31.10, razem
  746 zł (273 + 473), przesiadka 17 h 30 min. Odcinki mają własne daty linków.
  Zweryfikowano linki w modalu, bez zakupu ani rezerwacji.
- Przycisk kopiowania pokazał sukces. Odczyt schowka przez API narzędzia
  zwrócił pusty tekst, dlatego zweryfikowano rzeczywiste Cmd+V do lokalnego
  pustego pola testowego: wklejony URL był dokładnie linkiem do tej karty.
  Otwarcie tego faktycznie skopiowanego URL ponownie rozwinęło właściwą kartę
  i automatycznie ustawiło potrzebne 24 h. Nie odczytywano ani nie wypisywano
  obcej zawartości schowka. Końcowe logi konsoli: brak błędów.

## Lokalna promocja, dowody i rollback

Po pełnej walidacji promowano razem **wszystkie 20 plików** do lokalnego
`data/`, bez publikacji w internecie. Porównania bajtowe potwierdziły:
przed promocją publiczne=baseline, po promocji publiczne=staging,
wszystkie 20 backupów=baseline. Ponowny odbiór batcha przeszedł.
HTTP podaje aktualne bajty **22 plików**: index, app i 20 plików danych.
Lokalny serwer pozostawiono uruchomiony na 127.0.0.1:8000.

Dowody w `tmp/szy-rdo-expansion/batch-2026-10-24/`:

- `collection-complete-report.json` — oryginalny raport ukończonej kolekcji,
  zachowany przed osobnym `--validate-only --promote`;
- `pre-promotion-acceptance-report.json` — pełny odbiór przed podmianą;
- `acceptance-report.json` — ponowny odbiór, publiczne=staging,
  backup=baseline i dokładny zbiór route/day cache;
- `http-acceptance-report.json` — 22 odpowiedzi HTTP zgodne bajtowo;
- `previous-public-feeds/manifest.json` i 20 kopii starej bazy;
- świeży cache route/day oraz jego metadata — wyłącznie lokalne artefakty,
  nie do dodawania do Git.

Zapisany podgląd rzeczywistej karty: `tmp/szy-rdo-expansion/podglad-szy.jpg`.
Po uzupełnieniu raportu ponownie przeszły wszystkie 246 testów Python,
42 JS na lokalnej publicznej bazie, odbiór batcha, `node --check app.js`
i `git diff --check`. Testy kolektorów używały mocków, bez ponownej kolekcji cen.

Promocja ma backup i rollback obsłużonych błędów; 20 podmian nie jest jedną
transakcją odporną na nagłe zabicie procesu. Pełny rollback wymaga spójnego
powrotu kodu/rejestrów/konfiguracji i 20 plików do jedenastu, nie samych cen.
Zachować zastane zmiany i kopie; bez globalnego resetowania/odrzucania.

Przy pierwszym odbiorze lokalnym HEAD pozostał
`811599d64b93ed65f08563f56ad2e5fb8ac96eb1`, niczego nie dodano do indeksu
i nie wykonano commita/push. Późniejsze polecenie publikacji opisano na początku
raportu; nie upoważnia ono do dodania kolejnych endpointów lub tras.
Nie zmieniano workflow, parserów cen, kolektorów, limitów Google,
harmonogramów Wizza ani zasad wyceny rezydenta.
