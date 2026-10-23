# Lokalne wdrożenie Bydgoszczy (BZG) — 23.10.2026

Status: **wdrożone i zweryfikowane lokalnie**. Konfiguracja dziesięciu
endpointów, strona i nowa pełna baza są spójne: 15 407 propozycji, w tym
187 BZG. Wszystkie dziesięć feedów i dziesięć sidecarów promowano lokalnie
dopiero po odbiorze kompletnego batcha. Odbiór wizualny/schowka pozostaje
jawnie otwarty z powodu wyłączonego sterowania przeglądarką w Work.
Pierwszy odbiór odbył się bez commita, push, PR i zmian GitHub Actions.
Następnie 23.10.2026 użytkownik osobno zlecił publikację kompletnego pakietu
BZG i tej nowej bazy na GitHub. Nie dodano workflow zbierania cen.

## Baseline i zakres

HEAD `7d4f9bf7b834bd7007cf4b8a4b414123dfe65233`, gałąź `codex/add-lodz-lcj`.
Zastano lokalny plan BZG i jego link w README; zachowano je.
Przed zmianą rejestru ponownie zwalidowano kompletną bazę dziewięciu:
15 268 propozycji, run `e1d13844-5567-46d6-980d-f819f4fa1752`,
2026-10-23–2026-11-22. Pełny backup kodu, konfiguracji, testów, dokumentacji
i 20 plików danych: `tmp/bzg-expansion/baseline/`.
Manifest SHA-256: `tmp/bzg-expansion/baseline-manifest.json`.

Minimum przesiadki nadal 120 min, maksimum 1440; rozmowa o kombinacji
z 1 godz. 55 min nie zmieniła tej reguły. Domyślnie Polska → Teneryfa,
1000 zł i maksymalnie 6 h przesiadki. Brak limitu ceny w kolektorach.

## Pełny audyt siatek

Nowy snapshot całych oficjalnych sieci: `tmp/bzg-expansion/network-snapshot.json`.
Ryanair BZG: **ALC, BHX, BRS, DUB, LTN, STN**; Wizz: **brak krawędzi BZG**.
Jedynym hiszpańskim sąsiadem BZG jest ALC.
Przecięcia wyliczono przed ograniczeniem do starych allowlist, w tym dla
zupełnie nowych globalnych hubów; żadnego nowego huba ani TFN/TFS w starym
hubie nie znaleziono. Nie kopiowano listy RZE.

| Wariant | Decyzja BZG |
| --- | --- |
| 1A Binter | Bez nowego uprawnienia; pełna macierz sześciu zapisanych hubów z BZG, obu linii i kierunków pozostaje pobierana. |
| 1B Iberia/Express | Bez nowego uprawnienia; pełna macierz BZG/MAD obu linii i kierunków nadal pobierana. |
| 1C Vueling | Ryanair przez ALC do/z TFN. |
| 1D Air Europa | Brak potwierdzonej kwalifikującej trasy. |
| 1E Volotea | Brak potwierdzonej kwalifikującej trasy. |
| 1F Canaryfly | Brak połączenia międzywyspowego z sąsiadem low-cost BZG. |
| 2 bezpośrednie | Pełna macierz obu linii i kierunków; wynik po kolekcji. |
| 3 Ryanair/Ryanair | BHX, BRS, DUB, LTN, STN, każdy z TFS. |
| 4 Wizz/Wizz | Brak przecięcia. |
| 5A Ryanair Teneryfa / Wizz Polska | Brak przecięcia. |
| 5B Wizz Teneryfa / Ryanair Polska | Brak przecięcia, mimo osobnego sprawdzenia tego wariantu. |

Źródła i ograniczenia przeglądu rezydenckiego:

- [Binter — oficjalny katalog](https://www.bintercanarias.com/es/destinos):
  ALC nie występuje. `timetable_get` zwrócił GraphQL E01000 mimo HTTP 200;
  snapshot zachowuje `failed`, nie zamienia błędu w brak tras. Niezależny
  katalog rozstrzyga jedynego hiszpańskiego sąsiada BZG; pozostali są zagraniczni.
- [Iberia Tenerife–Madrid](https://www.iberia.com/es/vuelos-baratos/Tenerife-Madrid/)
  i [oficjalna lista Express](https://www.iberiaexpress.com/informacion-general/iberia-express/destinos),
  potwierdzenie operatora [TFN](https://www.aena.es/es/tenerife-norte-ciudad-de-la-laguna/aerolineas/iberia.html)
  i [TFS](https://www.aena.es/es/tenerife-sur/aerolineas/iberia.html): MAD
  bez low-cost BZG; nie potwierdzono własnego bezpośredniego odcinka ALC.
  Bezpośrednie otwarcie strony Express miało pętlę przekierowań; przejrzano
  jej zaindeksowaną oficjalną treść, bez udawania udanego otwarcia.
- [Własna lista Vuelinga z Teneryfy](https://www.vueling.com/es/vuelos-baratos-desde-tenerife):
  TFN/ALC oraz pozostałe hiszpańskie kierunki; pełne przecięcie z BZG daje ALC.
- [Air Europa — własna strona](https://www.aireuropa.com/es-es/ofertas-de-vuelos-desde-tenerife)
  reklamuje ALC, ale marketing pary miast nie jest dowodem lotu direct.
  [Operator TFN](https://www.aena.es/es/tenerife-norte-ciudad-de-la-laguna/aerolineas/air-europa.html)
  podaje BIO/MAD, bez przecięcia z BZG. Bieżące ceny Air Europa nadal tylko Google.
- [Własne oferty Volotei](https://www.volotea.com/es/ofertas-vuelos/tenerife/):
  opublikowane rynki ALC bez Teneryfy;
  [operator TFS](https://www.aena.es/es/tenerife-sur/aerolineas/volotea.html)
  potwierdza BIO/OVD i zagraniczne NTE. Nie ma przecięcia z BZG; dynamiczna
  sekcja strony nie została potraktowana jako dowód nieistnienia trasy.
- [Canaryfly — własna sieć międzywyspowa](https://www.canaryfly.es/en/cheap-flights)
  nie przecina żadnego z pełnego zestawu sześciu sąsiadów BZG.

Decyzje i plan zapytań: `tmp/bzg-expansion/route-decisions.json`.
Przegląd discovery ze statusem źródeł: `discovery-reviewed-report.json`
w tym samym katalogu. Bez globalnego `--apply` i bez aktywowania zmian innych miast.

## Wizz, konfiguracja i testy przed kolekcją

Wszystkie cztery skierowane rynki Wizz BZG/TFN/TFS mają puste oficjalne
kalendarze w oknie; zero pending i zero potrzebnych nowych obserwacji Google.
Dowód: `tmp/bzg-expansion/verified-wizz-schedules.json`.
Niezależny dodatkowy skan oficjalnego Wizz timetable dla wszystkich sześciu
sąsiadów BZG (12 skierowanych tras, pełne okno) również zwrócił wyłącznie
poprawne puste kalendarze: `tmp/bzg-expansion/wizz-neighbour-crosscheck.json`.
Nie wymyślano rozkładu BZG, a wspólny i lokalne rejestry Wizza pozostały
identyczne bajtowo/semantycznie z baseline.

Dziewięć allowlist ma scope dziesięciu; BZG ma Europe/Warsaw. Jedyny polski
transfer nadal GDN/5B→KRK. `review_routes.py` potwierdza niezmienność
wszystkich uprawnień, stref i lokalnych rozkładów starej dziewiątki.
Powtórne generowanie konfiguracji daje te same dziesięć dokumentów review.
Nie wystąpił nowy hub rezydencki ani nowe TFN/TFS wymagające zmian helpera;
nie deklaruje się naprawienia jego innych ogólnych ograniczeń.

**220 testów Python przeszło.** 12 nowych testów obejmuje BZG we wszystkich
builderach obu kierunków, zamrożoną dziewiątkę, pełne rzeczywiste plany,
nowy globalnie hub NEW, Wizz pending, idempotencję, DST i granice przesiadek,
stary raport dziewięciu i brak jednego BZG route/day.
Początkowy błąd nowego testu `len(generator)` poprawiono na `len(list(...))`;
ponowne całe 220 poprawne, bez zmiany implementacji kolektora.

JS na starej bazie: **33 poprawne, 1 pominięty do odbioru nowego stagingu BZG**.
Dodano syntetyczny dziesiąty checkbox, OR BZG+KRK+RZE, oba kierunki i cache,
brak ofert/jeden kierunek, +1 i resety oraz test rzeczywistych cen/minimów/share.
Fixture historycznego dziewiątego checkboxa RZE nie dziedziczy BZG.
Test etykiety pierwszego lotniska nie zakłada już GDN, gdy BZG sortuje się wcześniej.
Nie usunięto historycznych testów; SIX/SEVEN/EIGHT pozostają zamrożone.

`node --check app.js`, `compileall` i `git diff --check` przeszły.
Ponowne uruchomienie pełnego zestawu Python podczas kolekcji: 220/220,
bez błędów (10,785 s); testy źródeł używają mocków, nie dodatkowych zapytań Google.
JS ma nową wersję `20261023-bzg-1`; multiselect, warstwy menu i pozostałe
ustawienia wyglądu bez przebudowy.

## Nowa kolekcja — zakończona i promowana lokalnie

Staging: `tmp/bzg-expansion/batch-2026-10-23`.
Run ID: `e0322930-e323-4c8c-9f08-459723852a72`.
Okno: 2026-10-23–2026-11-22 (31 dat).
Hash konfiguracji: `d8bd510a1ecf3bb917de6bd2a1e67509ba4cd22924adda9c079dd313f184a142`.
Świeży cache: `ryanair-google-7ba9bc1f0efcf467b78b.jsonl`, bez cen/cache runu RZE.
Jeden dzienny NBP, EUR/PLN 4.3917; runner sekwencyjny, Google najwyżej 2.

Zakończone pierwsze warianty: 1A ma 2777 wyników (1362 Teneryfa → Polska,
1415 Polska → Teneryfa); 1B ma 2174 wyniki i complete 1364/1364.
Ich zakończenie nie stanowi zgody na częściową podmianę publicznej bazy.

Pierwsze podejście 1C przerwano na ALC–GDN 2026-11-15:
`Unknown Google Flights Ryanair payload`. Zachowano błąd i failed coverage
w `tmp/bzg-expansion/first-failure-*.json` oraz log
`tmp/bzg-expansion/step1c-first-attempt.log`. Nie zmieniano parsera, nie
uznawano odpowiedzi za pusty dzień i nie podmieniano publicznych danych.
Wznowiono wyłącznie 1C–5 z tym samym run ID, konfiguracją i świeżym cache
(5076 zapisanych poprawnych route/day w momencie przerwania).
1A i 1B nie są pobierane ponownie.
Ponowne pobranie tego route/day zwróciło prawidłowy wynik i pozwoliło
ukończyć niezależny kalendarz low-cost 1C (1578 odcinków); brak ręcznej
ingerencji w ceny, wynik parsera lub raport pokrycia.

Krok 3 zatrzymał się analogicznie na BRS–WMI 2026-11-14, z nieznanym
payloadem Google. Cache zachował 16 952 poprawne route/day. Osiem kalendarzy
pozostało częściowych (BRS–WMI, BUD–WMI, EIN–KRK, STN–POZ, TFS–BHX,
TSF–KTW, TSF–POZ, WRO–BHX), a STN–WMI nie miało poprawnego pierwszego dnia.
Łącznie dziewięć tras i 160 dni do domknięcia przed krokiem 4.
Zachowano log `step3-first-attempt.log` i `second-failure-*.json` poza stagingiem;
wznowiono tylko 3–5 z tym samym runem, hashem i cache, bez zmiany parsera.
To ponowienie ukończyło 378/378 tras kroku 3, zapisując 5408 propozycji,
i cały krok 4. Wszystkie 160 brakujących dni Ryanaira pobrano poprawnie.

W kroku 5 oficjalny Wizz timetable zwrócił HTTP 503 dla taryfy WDC WAW–RAK.
Nie użyto taryfy regularnej zamiast WDC ani poprzednich danych. Log i failed
coverage zachowano jako `step5-first-attempt.log` i `third-failure-*.json`.
Ponowiono wyłącznie krok 5 z `--workers 2`; konfiguracja, run i kompletny
cache Ryanaira 17 360/17 360 pozostały te same. Obniżono równoległość
wykonawcy, nie podniesiono limitu Google ani nie zmieniono źródła ceny.

Ponowienie kroku 5 zakończyło się poprawnie: Wizz 106/106 tras, complete.
Nie pominięto WAW–RAK/WDC ani innego problematycznego dnia.

### Wyniki wszystkich feedów

Każdy z poniższych raportów jest `complete`, z zerem brakujących
i nadmiarowych zapytań. Sidecary są identyczne z raportami osadzonymi
w feedach; wszystkie mają ten sam run ID i aktualny scope dziesięciu.

| Feed | Wyniki | Polska → Teneryfa | Teneryfa → Polska | W tym BZG | Pokrycie ukończone/planowane |
| --- | ---: | ---: | ---: | ---: | ---: |
| 1A Binter | 2777 | 1415 | 1362 | 0 | 8184/8184 |
| 1B Iberia/Express | 2174 | 1093 | 1081 | 0 | 1364/1364 |
| 1C Vueling | 2844 | 1492 | 1352 | 13 | 3534/3534 |
| 1D Air Europa | 853 | 435 | 418 | 0 | 744/744 |
| 1E Volotea | 8 | 8 | 0 | 0 | 248/248 |
| 1F Canaryfly | 221 | 108 | 113 | 0 | 558/558 |
| 2 bezpośrednie | 203 | 97 | 106 | 0 | 2480/2480 |
| 3 Ryanair/Ryanair | 5408 | 2717 | 2691 | 174 | 11718/11718 |
| 4 Wizz/Wizz | 210 | 116 | 94 | 0 | 1364/1364 |
| 5 mieszane | 709 | 342 | 367 | 0 | 5270/5270 |
| **Razem** | **15407** | **7823** | **7584** | **187** | **35464/35464** |

Krok 5: wariant A 541, wariant B 168. Pokrycie 1F obejmuje pełne kalendarze
miesięczne, dni tras low-cost oraz 124 dostępne dni szczegółowych lotów
Canaryfly. Liczby pokrycia nie są liczbą pojedynczych żądań sieciowych ani
liczbą lotów. Cache Ryanaira ma dokładnie 17 360 unikalnych, poprawnych
route/day, równych sumie zbiorów planów wszystkich feedów; wszystkie
ze źródła `google_flights_http`.

| Endpoint | Wszystkie propozycje | Polska → Teneryfa | Teneryfa → Polska |
| --- | ---: | ---: | ---: |
| WAW | 1980 | 1032 | 948 |
| WMI | 1896 | 953 | 943 |
| KTW | 773 | 428 | 345 |
| KRK | 5069 | 2511 | 2558 |
| GDN | 1958 | 998 | 960 |
| WRO | 2241 | 1140 | 1101 |
| POZ | 817 | 433 | 384 |
| LCJ | 209 | 96 | 113 |
| RZE | 277 | 137 | 140 |
| BZG | 187 | 95 | 92 |

Całość pobrano od nowa, nie dopisano 187 wierszy do starej bazy. Dlatego
aktualna dostępność/ceny i liczby starej dziewiątki mogą różnić się od baseline,
mimo zachowania wszystkich jej uprawnień i rozkładów technicznych.

### BZG i wyniki zerowe

Aktywne dopasowania: STN 97, DUB 31, BHX 31, BRS 15 i ALC 13.
Bez limitu ceny i z przesiadką do 24 h jest 95 propozycji z Polski i 92 powrotne.
Przy dotychczasowych ustawieniach strony (rezydent włączony, WDC wyłączony,
do 1000 zł i do 6 h) BZG ma odpowiednio **5 i 18** propozycji. Mniejszy wynik
domyślny jest filtrem strony, nie odrzucaniem droższych lotów w kolektorach.

LTN zachowano na allowliście, lecz nie daje dopasowania. Sprawdzono wszystkie
31 dni każdej skierowanej trasy: BZG–LTN 14 lotów, LTN–BZG 13, LTN–TFS 5,
TFS–LTN 5. W obu kierunkach zero par w przedziale 120–1440 minut; najkrótsze
dodatnie oczekiwanie wynosi odpowiednio 5225 i 1985 minut, czyli ponad 24 h.
Nie usunięto sezonowej trasy ani nie uznano błędu za pusty dzień.

Krok 2 sprawdził całą macierz dziesięciu endpointów/TFN/TFS, obu linii
i kierunków: 2480/2480. Brak bezpośredniego BZG w tym oknie jest wynikiem
pełnej kolekcji. Zera pozostałych wariantów BZG odpowiadają decyzjom siatkowym
opisanym powyżej. Jedyny polski transfer nadal GDN/5B→KRK (7 propozycji).

### Próbki cen, dat i linków

- `step3-22fc6e348e9d41d0`: 19.11 BZG–DUB FR1893, 13:05–14:50,
  następnie DUB–TFS FR5555, 20:30–00:50 **20.11 (+1)**. Przesiadka 340 min,
  149 + 146 = 295 zł. Oba odcinki mają własne linki Ryanaira z właściwą
  trasą i datą; zakup drugiego odcinka nadal na datę wylotu 19.11.
- `step3-56ae587f04be5715`: 11.11 TFS–BRS FR4754, 06:00–10:10,
  BRS–BZG FR9503, 12:50–16:10. Przesiadka 160 min, 75 + 79 = 154 zł.
  Zagraniczna przesiadka bez szacowania zniżki rezydenckiej.
- `step1c-133e64f374cb7ef2`: 27.10 BZG–ALC FR7833, potem 28.10 ALC–TFN
  VY3148. Regularnie 95 + 529 = 624 zł; estymata rezydenta 95 + 169,64 =
  264,64 zł. Vueling ma 11,35 EUR niedyskontowalnych opłat ALC, przeliczonych
  jednym kursem batcha na 49,85 zł: `49,85 + 0,25 × (529 − 49,85)`.
  Przerwa 18 h, więc ta oferta nie przechodzi domyślnego filtra 6 h.

Pełny odbiór sprawdził sumy cen regularnych, dodatnie ceny i chronologię,
okno obu odcinków, ten sam IATA przesiadki i granice 120–1440 min,
unikalne ID, pełne numery lotów, domeny wszystkich linków i brak parametrów
sesyjnych/tokenów. Rejestr opłat ważny do 31.12.2026 obejmuje całe okno;
nie dodawano nowej opłaty ani nowego rozkładu Wizza. Binter/Canaryfly zachowują
oficjalne końcowe imports, nie estymator 25%. Linki zakupu są trwałymi
wyszukiwaniami trasa/data, nie obietnicą automatycznego wyboru numeru rejsu.

## Odbiór, lokalna promocja i rollback

Przed promocją `accept_batch.py` potwierdził, że wszystkie 20 plików
publicznych jest nadal identycznych z baseline. Wynik:
`tmp/bzg-expansion/batch-2026-10-23/pre-promotion-acceptance-report.json`.
Oryginalny kompletny raport runnera (z hashem i ścieżką cache) zachowano jako
`collection-complete-report.json`, przed wywołaniem `--validate-only --promote`.

Promocja zakończyła się poprawnie i objęła całe 20 plików.
`previous-public-feeds/manifest.json` i 20 plików w tym katalogu przechowują
poprzedni publiczny zestaw. Ponowny `acceptance-report.json` potwierdza:

- wszystkie publiczne feedy i sidecary identyczne bajtowo ze stagingiem;
- wszystkie 20 backupów identyczne bajtowo z niezależnym baseline;
- complete coverage aktualnych dziesięciu, jeden run, zero braków/nadmiarów;
- pełną zgodność cache Ryanaira z planem, bez dodatkowych/przestarzałych wpisów.

34/34 testy JS przeszły na stagingu (0 pominiętych) i ponownie na lokalnych
publicznych danych. Po promocji ponownie 220/220 Python, bez błędów.
Sprawdzono wielokrotny wybór lotnisk i cache, oba kierunki, cztery ustawienia
zniżek, wszystkie osiem sortowań, minima kalendarza/wykresu, cel karty,
udostępnianie droższej oferty, +1 i resety. Są to testy logiki, nie wizualna QA.

Lokalny HTTP zwrócił 200 i dokładne aktualne bajty dla 22 plików:
`index.html`, `app.js`, dziesięciu feedów i dziesięciu raportów.
Dowód: `http-acceptance-report.json` w stagingu. JS `20261023-bzg-1`.
Podgląd: <http://127.0.0.1:8000/?build=bzg-local-20261023>.

Podczas pierwszego lokalnego odbioru nie wykonano commita, push, PR ani
zmiany workflow; HEAD i gałąź nadal odpowiadały baseline. Późniejsze osobne
polecenie użytkownika autoryzuje publikację pakietu BZG i wszystkich 20 plików
danych, bez cache/logów/backupów z `tmp/` i bez zmiany workflow.
Rollback wymaga spójnego przywrócenia konfiguracji,
kodu i 20 plików sprzed BZG z `tmp/bzg-expansion/baseline/`, z zachowaniem
zastanych niezwiązanych zmian (w tym początkowego planu/linku README).
Sam backup feedów dziewięciu pod konfigurację dziesięciu nie jest spójnym
wycofaniem. Nie uruchamiano rollbacku, `git reset --hard` ani kasowania plików.
Niezależnego baseline nie należy usuwać po udanej promocji.

## Odbiór przeglądarkowy

Przy wdrożeniu ponownie sprawdzono dostępność narzędzia. Inwentaryzacja
aplikacji działa, ale sterowanie przeglądarką jest wyłączone w ustawieniach
Work. Nie obchodzono blokady przez inne sterowanie przeglądarką.
Wizualny odbiór desktop/320 px oraz test systemowego schowka pozostają otwarte;
testy Node i HTTP nie będą przedstawiane jako zastępstwo wizualnej kontroli.
