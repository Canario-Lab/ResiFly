# Lokalne wdrożenie Rzeszowa (RZE) — 23.10.2026

Status: **kod, konfiguracja i nowa baza odebrane lokalnie; publikacja
GitHub następnie osobno autoryzowana przez użytkownika 23.10.2026**.
Pełna kolekcja dziewięciu endpointów i walidacja zakończone; lokalna strona
korzysta z nowego kompletu 20 plików. Odbiór wizualny oraz test systemowego
schowka pozostają otwarte: sterowanie lokalną przeglądarką jest wyłączone
w ustawieniach Work. Pierwszy odbiór odbył się bez commita i push;
nie zmieniano GitHub Actions.

## Baseline

HEAD `b2c5f2b7c1612cb507de958720f8d0aebb5e59de`, checkout
`codex/add-lodz-lcj`. Zastano lokalny plan RZE i odnośnik w README; zachowano.
Przed zmianą konfiguracji stara baza ośmiu endpointów przeszła walidację:
15 030 propozycji, run `a6f8a0e8-f295-4f20-984e-74607fc6cb08`, okno
2026-10-23–2026-11-22. Kopia konfiguracji, kodu, testów, dokumentacji
i 20 publicznych plików: `tmp/rze-expansion/baseline/`.
Manifest SHA-256: `tmp/rze-expansion/baseline-manifest.json`.

## Audyt pełnych siatek

Oficjalne siatki pobrano dla całej sieci, bez ograniczenia do istniejących
hubów. Snapshot: `tmp/rze-expansion/network-snapshot.json`.
Ryanair RZE: ALC, BRS, DUB, EDI, LTN, MAN, MLA, MXP, STN, ZAD.
Wizz RZE: FCO, TGD. Jedyny hiszpański sąsiad low-cost RZE to ALC.
Przecięcia przejrzano także pod kątem całkowicie nowych hubów; żadnego
nie znaleziono. Nie oznacza to pominięcia tego sprawdzenia.

| Wariant | Nowe uprawnienia RZE |
| --- | --- |
| 1A Binter | Brak; pełna macierz sześciu zapisanych hubów nadal obejmuje RZE/obie linie. |
| 1B Iberia/Express | Brak; pełna macierz RZE/MAD nadal jest pobierana. |
| 1C Vueling | Ryanair przez ALC do/z TFN. |
| 1D Air Europa | Brak. |
| 1E Volotea | Brak. |
| 1F Canaryfly | Brak. |
| 2 bezpośrednie | Cała macierz RZE/TFN/TFS, obu linii i kierunków; pełne 248 pozycji pokrycia, zero bezpośrednich ofert w oknie. |
| 3 Ryanair/Ryanair | BRS, DUB, EDI, LTN, MAN, MXP, STN. |
| 4 Wizz/Wizz | FCO. |
| 5A Ryanair na Teneryfie / Wizz na Polsce | FCO. |
| 5B Wizz na Teneryfie / Ryanair na Polsce | MXP. |

Osobny przegląd źródeł rezydenckich:

- [Oficjalny katalog Bintera](https://www.bintercanarias.com/es/destinos)
  nie zawiera ALC. Zbiorczy `timetable_get` zwrócił GraphQL E01000;
  snapshot zachowuje `failed`. Nie wywnioskowano braku tras z błędu API.
- [Iberia](https://www.iberia.com/es/vuelos-baratos/Tenerife-Madrid/) i
  [Iberia Express](https://www.iberiaexpress.com/informacion-general/iberia-express/destinos),
  pomocniczo listy operatora [TFN](https://www.aena.es/es/tenerife-norte-ciudad-de-la-laguna/aerolineas/iberia.html)
  i [TFS](https://www.aena.es/es/tenerife-sur/aerolineas/iberia.html):
  bezpośredni MAD bez low-cost do RZE; nie potwierdzono własnej trasy ALC.
- [Własna strona Vuelinga](https://www.vueling.com/es/vuelos-baratos-desde-tenerife)
  potwierdza TFN/ALC. Przejrzano także pozostałe hiszpańskie kierunki,
  w tym GRX/OVD/MAD, bez przecięcia z RZE.
- [Air Europa](https://www.aireuropa.com/es-es/ofertas-de-vuelos-desde-tenerife)
  reklamuje również ALC, lecz para miast nie dowodzi bezpośredniego rejsu;
  [operator TFN](https://www.aena.es/es/tenerife-norte-ciudad-de-la-laguna/aerolineas/air-europa.html)
  wskazuje bezpośrednie BIO/MAD, bez odcinka low-cost RZE.
- [Oferty Volotei](https://www.volotea.com/es/ofertas-vuelos/tenerife/)
  zawierają TFS/BIO i listę rynków ALC bez Teneryfy;
  [operator TFS](https://www.aena.es/es/tenerife-sur/aerolineas/volotea.html)
  potwierdza BIO/OVD, bez RZE. Ogólna strona przewoźnika jest dynamiczna;
  nie potraktowano pustej sekcji jako dowodu nieistnienia trasy.
- [Canaryfly](https://www.canaryfly.es/en/cheap-flights): sieć międzywyspowa
  nie przecina pełnego zestawu sąsiadów low-cost RZE.

Decyzje i bazowy plan zapytań: `tmp/rze-expansion/route-decisions.json`.
Raport discovery z jawnymi ograniczeniami:
`tmp/rze-expansion/discovery-reviewed-report.json`.
Nie aktywowano kandydatów niezwiązanych z RZE ani nowych polskich transferów.

## Konfiguracja, Wizz i testy wstępne

RZE ma strefę Europe/Warsaw; dziewięć scope zgodne z rejestrem.
Wyjątek GDN/5B wyłącznie do KRK bez zmian. `review_routes.py` potwierdził
semantyczną niezmienność uprawnień, stref i rozkładów starej ósemki.

Wizz RZE–FCO: W46068, 140 min przy 08:35 oraz 130 min przy 10:45/22:45;
FCO–RZE: W46067, 135 min. Wszystkie 16 obserwacji Google HTTP odtwarza
loader wspólnego rejestru. Osobne porównanie z oficjalnym timetable
potwierdziło pokrycie wszystkich 9 aktywnych odlotów RZE–FCO i 7 FCO–RZE,
bez brakujących dat/godzin (`wizz-active-departure-check.json`).
Sprawdzono również cztery bezpośrednie rynki
Wizz RZE/TFN/TFS: nieaktywne w oknie; zero pending.
Dowody: `tmp/rze-expansion/verified-wizz-schedules.json`.
Pozostałe wspólne i lokalne rozkłady, m.in. WRO–LPA i POZ–LTN, niezmienione.

Ponowny przegląd wykazał, że kontrola nowych odcinków Wizz Teneryfa–hub
w 4/5B już była w kodzie i testach LCJ, mimo zbyt ostrożnego opisu planu.
Nie implementowano jej ponownie; zachowano i rozszerzono test dla RZE.
Nie wystąpił nowy hub 1A–1F wymagający ręcznej budowy pełnego rekordu;
ograniczenia helpera nie zostały uznane za zastępstwo audytu siatek.

208 testów Python przeszło, również ponownie po zakończeniu kolekcji.
JS na starych feedach: 29 poprawnych i jeden świadomie pominięty do czasu
nowego stagingu RZE. Następnie na nowym stagingu i ponownie po promocji:
**30/30 poprawnych, zero pominiętych**. Dodano testy syntetyczne dziewiątego
checkboxa, OR, chipów, kierunków i braku ofert oraz test rzeczywistego
kalendarza/wykresu/share RZE. Zachowano multiselect i warstwy menu nad
kalendarzem; nie zastąpiono checkboxów pojedynczym selectem.

## Nowa kolekcja — zakończona

Staging: `tmp/rze-expansion/batch-2026-10-23`.
Run ID: `e1d13844-5567-46d6-980d-f819f4fa1752`.
Okno 2026-10-23–2026-11-22; 31 dat włącznie.
Hash konfiguracji: `d4eddf522cc0045f0c11f00d166436fc563512e344e41cd4a4f09c35baed3cdc`.
Nowy cache Ryanaira: `ryanair-google-b2b0aa887e182f40a489.jsonl`, bez użycia
cen/cache poprzedniej kolekcji. Runner sekwencyjny, Google max 2, jeden
dzienny zestaw NBP (EUR/PLN 4.3917).
Pełne niezależne kalendarze każdej zapisanej linii w obu kierunkach;
ten sam mechanizm końcowych imports Binter/Canaryfly i estymat z opłatami.

Kolekcja zakończyła wszystkie dziesięć feedów bez wznowienia lub osłabienia
walidacji. Raport ukończenia zachowano jako `collection-complete-report.json`;
`validation-report.json` potwierdza również późniejszą lokalną promocję.

| Feed | Wszystkie wyniki | Polska → Teneryfa | Teneryfa → Polska | Wyniki RZE | Complete coverage |
| --- | ---: | ---: | ---: | ---: | ---: |
| 1A | 2797 | 1417 | 1380 | 0 | 7440/7440 |
| 1B | 2171 | 1091 | 1080 | 0 | 1240/1240 |
| 1C | 2853 | 1503 | 1350 | 16 | 3472/3472 |
| 1D | 853 | 435 | 418 | 0 | 744/744 |
| 1E | 8 | 8 | 0 | 0 | 248/248 |
| 1F | 221 | 108 | 113 | 0 | 558/558 |
| 2 | 205 | 97 | 108 | 0 | 2232/2232 |
| 3 | 5241 | 2630 | 2611 | 242 | 11408/11408 |
| 4 | 210 | 116 | 94 | 11 | 1364/1364 |
| 5 | 709 | 342 | 367 | 10 | 5270/5270 |

Łącznie **15 268 propozycji, 33 976 ukończonych pozycji pokrycia**, zero
braków i nadmiarów, wspólny run ID. W 1F dodatkowe 124 pozycje to szczegóły
dni dostępnych po kompletnym skanie kalendarzy; bazowy plan ma 434 pozycje.
Świeży cache zawiera dokładnie **16 492** unikalne zaplanowane route/day
Ryanaira, wszystkie `status=ok`, `source=google_flights_http`.

RZE: **279 propozycji: 137 Polska → Teneryfa i 142 Teneryfa → Polska**.

- 1C: 16 przez ALC, po 8 w każdym kierunku.
- 3: 242 (116/126) przez BRS (8), DUB (29), EDI (20), MAN (38), STN (147).
- 4: 11 (9/2) przez FCO.
- 5: 10 (4/6), wszystkie wariant A przez FCO.

Zero wyników przez LTN/MXP nie oznacza pominięcia tych tras. Każda para
RZE–hub ma 62 poprawnie sprawdzone dni/kierunki. RZE/LTN zwrócił zero rejsów,
RZE/MXP dwa rejsy, ale nie powstała poprawna przesiadka 120–1440 min ani
w 3, ani w 5B. RZE w 1A/1B zostało uwzględnione w pełnych macierzach;
brak innych uprawnień 1A–1F wynika z opisanego audytu, nie z błędu źródła.

Przy domyślnych filtrach (do 1000 zł, do 6 h, rezydent, bez WDC) RZE ma
22 propozycje w stronę Teneryfy i 4 z powrotem. Wyższe ceny i dłuższe
przesiadki pozostały w feedach. Pozostałe osiem endpointów ma wyniki w obu
kierunkach; zmiany dostępności/cen względem baseline wynikają z nowego
pobrania, a nie z doklejania starych cen.

## Odbiór i lokalna promocja

`tmp/rze-expansion/accept_batch.py` zwalidował cały staging, a po promocji
ponownie publiczną kopię: bieżący plan dziewięciu, identyczne sidecary,
wspólny run, chronologię/strefy i granice przesiadek, unikalne ID,
numery lotów, sumy cen regularnych, deterministyczne linki odcinków
Ryanair/Wizz oraz domeny i brak tokenów w linkach wszystkich linii.
Zachowany wyłącznie wyjątek GDN/5B→KRK: 7 wyników; brak nowych polskich hubów.
Raport: `tmp/rze-expansion/batch-2026-10-23/acceptance-report.json`.

Próbki obecnej bazy, nie nowe zapytania cenowe:

- `step3-4bf902b99aadb2ee`: RZE–BRS–TFS, FR8225 + FR4753,
  20–21.11.2026, 90 + 132 = 222 zł, przesiadka 355 min, przylot następnego
  dnia o 01:25. Oba odcinki zagraniczne — bez zniżki rezydenta.
- `step5-116fe0462206fb86`: TFS–FCO–RZE, FR245 + W46067, 20.11.2026,
  260 + 158,06 = 418,06 zł; z WDC na odcinku Wizz 374,14 zł łącznie,
  przesiadka 355 min. Linki wskazują właściwe trasy/datę, bez obietnicy
  automatycznego wyboru numeru rejsu na stronie przewoźnika.

Testy UI w Node na rzeczywistych feedach obejmują oba kierunki RZE,
cztery kombinacje rezydent/WDC, osiem sortowań, minima dnia, wspólny cel
kalendarza/wykresu/karty, przywrócenie share oraz share powyżej 1000 zł.
Syntetyczne testy obejmują `+1`, brak ofert i tylko jeden kierunek.
`node --check app.js`, `compileall` oraz `git diff --check` przeszły.
Testy nie są deklaracją wizualnego odbioru w przeglądarce.

Przed promocją wszystkie 20 starych plików nadal odpowiadało bajtowo
baseline. Użyto istniejącego runnera z `--validate-only --promote`, bez
ponownego pobierania. Backup promocji:
`tmp/rze-expansion/batch-2026-10-23/previous-public-feeds/manifest.json`.
Wszystkie 20 kopii backupu odpowiada baseline, a wszystkie 20 publicznych
plików odpowiada nowemu stagingowi (`all_public_files_match_stage=true`).
Nie zmieniano ręcznie wygenerowanych JSON-ów.

`tmp/rze-expansion/verify_local_http.py` sprawdził po HTTP status 200 i
identyczność bajtową `index.html`, `app.js` i wszystkich 20 plików danych;
wszystkie raporty są complete i mają nowy run ID. Lokalny adres:
`http://127.0.0.1:8000/?build=rze-local-20261023`.

### Otwarty odbiór wizualny

Po promocji próba odświeżenia testowej karty zwróciła „Local browser use is
disabled in Work settings”. Nie obchodzono blokady inną automatyzacją.
Nie potwierdzono wizualnie menu, układu desktop/320 px, scrollowania do karty
ani działania systemowego schowka. Te punkty wymagają ręcznego sprawdzenia
lub późniejszego włączenia sterowania przeglądarką. Automatyczne sprawdzenie
logiki filtrów, kalendarza, wykresu, share i serwowanych plików zakończyło się
sukcesem, ale nie zastępuje tego odbioru.

## Wycofanie i granice publikacji

Przy ewentualnym wycofaniu należy przywrócić spójnie kod, konfigurację
i 20 plików z `tmp/rze-expansion/baseline/`, zachowując niezwiązane zmiany.
Samo przywrócenie starej bazy ośmiu pod konfigurację dziewięciu nie jest
poprawnym rollbackiem. Istniejąca promocja chroni przed obsłużonym błędem
podmiany, ale nie stanowi jednej transakcji odpornej na utratę zasilania.

Przy pierwszym lokalnym odbiorze HEAD pozostał
`b2c5f2b7c1612cb507de958720f8d0aebb5e59de`, ta sama gałąź; nie wykonywano
stagingu Git, commita, push, PR ani zmian workflow Actions.
Następnie użytkownik polecił „dawaj na github”. Przed publikacją ponownie
przeszły walidacja całego batcha, 208 testów Python, 30 JS i kontrola diff.
Pobrany `origin/main` wskazywał ten sam baseline, bez rozbieżnej historii.
Zakres autoryzacji obejmuje kod, konfigurację, testy, dokumentację i komplet
20 publicznych plików. `tmp/` z cache, logami i backupami pozostaje lokalne
i ignorowane przez Git; nie dodano workflow zbierania cen ani PR.
