# Lokalne wdrożenie Poznania (POZ) — 23.10.2026

Status: **wdrożone lokalnie**, komplet nowej bazy po automatycznym odbiorze
funkcjonalnym podmieniony w `data/`. Pierwszy odbiór odbył się bez commita
i push. Następnie 23.10.2026 użytkownik osobno autoryzował publikację całego
pakietu POZ i nowej bazy na GitHub. Nie dodano GitHub Actions.
Odbiór wizualny pozostaje otwarty z powodu wyłączonego sterowania
lokalną przeglądarką w ustawieniach Work; nie oznaczono go jako wykonanego.

## Zakres i zabezpieczenie

Punkt wyjścia: `1d3134ca60152d51aa0eca0c86828ea3d8a2d2e1`, sześć endpointów,
kompletny batch WRO `efa7d3ee-f865-4353-84a7-90b73f3eb21e` z 14 150
propozycjami. Przed zmianą rejestru skopiowano kod, konfigurację, testy,
dokumentację i 20 plików feedów/sidecarów do
`tmp/poz-expansion/baseline/`. Manifest SHA256:
`tmp/poz-expansion/baseline-manifest.json`. Baseline przechodzi własną
walidację dla sześciu endpointów. Gałąź lokalna: `codex/add-poznan-poz`.

Rejestr ma WAW/WMI/KTW/KRK/GDN/WRO/POZ, POZ: `Europe/Warsaw`.
Wszystkie dziewięć scope odpowiada rejestrowi. Dokładnie pięć kroków,
sześć wariantów 1A–1F i dziesięć feedów. GDN pozostaje transferem 5B
wyłącznie do KRK; nie dodano innych polskich transferów ani samotras.

`tmp/poz-expansion/configuration-audit.json` potwierdza niezmienione
uprawnienia tras całej starej szóstki i niezmienione wszystkie dotychczasowe
wspólne/lokalne rozkłady Wizz, w tym WRO–LPA i jego wyjątek poniedziałkowy.
Na zamrożonych wejściach testy porównują stare ID/ceny/dopasowania.

## Audyt tras

Oficjalne siatki odczytano 23.10.2026:
[Ryanair routes](https://www.ryanair.com/api/views/locate/3/routes) oraz
mapę Wizz pobraną przez wykrytą z oficjalnej strony wersję API. Pełny
snapshot jest w `tmp/poz-expansion/network-snapshot.json`, raport detektora
w `tmp/poz-expansion/discovery-report.json`. Zastosowanie było selektywne,
wyłącznie dla POZ; nie uruchamiano globalnego `--apply`.

Ryanair — sąsiedzi POZ: AGP, ALC, AMM, ARN, BCN, BGY, BHX, BOJ, BRI, BRS,
BVA, CAG, CFU, CHQ, CIA, CPH, CRL, DBV, DUB, EDI, GRO, LBA, LIS, LPL,
MAN, MLA, OPO, PFO, PMI, PMO, PRG, PUY, SKG, SNN, STN, TGD, TIA, TRF,
TSF, VLC, ZAD. Wizz: BSL, KUT, LTN, MLH, TGD, TIA. Brak opublikowanej
krawędzi nie usuwa obowiązku sprawdzenia pełnej macierzy kroku 2.

| Wariant | Zatwierdzone low-cost POZ / hub | Uzasadnienie |
| --- | --- | --- |
| 1A Binter | Ryanair: PMI, VLC | Przecięcie oficjalnych destynacji Bintera i siatki POZ. Pełny kalendarz Bintera weryfikuje rzeczywiste bezpośrednie odcinki, a końcowe imports cenę. |
| 1B Iberia/Express | Brak nowej zapisanej trasy | MAD nie ma odcinka low-cost do POZ w odczytanych siatkach. Pełna macierz 1B mimo to sprawdza MAD/POZ dla obu linii. |
| 1C Vueling | Ryanair: ALC, BCN, AGP, VLC | Oficjalna strona Vuelinga z Teneryfy oraz oficjalna siatka Ryanaira. |
| 1D Air Europa | Brak | Bezpośrednie kwalifikujące się huby MAD/BIO nie mają low-cost do POZ. Ofert z dodatkową przesiadką nie uznano za bezpośrednie. |
| 1E Volotea | Brak | Hiszpańskie BIO/OVD z oficjalnej strony Volotei nie mają low-cost do POZ. |
| 1F Canaryfly | Brak | Żaden kanaryjski port Canaryfly nie ma krawędzi Ryanair/Wizz do POZ w pobranej siatce. Dotyczy także ACE/SPC/VDE. |
| 2 | Pełne POZ/TFN/TFS × oba kierunki × obie linie | Brak rynku i brak lotów nie są powodem pominięcia zapytań. |
| 3 Ryanair + Ryanair | AGP, BGY, BHX, BRS, BVA, CRL, DUB, EDI, LBA, LPL, MAN, OPO, SNN, STN, TSF, VLC | 16 przecięć oficjalnych siatek, odcinek Teneryfy TFS. |
| 4 Wizz + Wizz | Brak | Żaden hub potrzebnego przecięcia nie łączy się z POZ. |
| 5A Ryanair Teneryfa + Wizz Polska | LTN | Obie oficjalne krawędzie, Wizz zweryfikowany technicznie w obu kierunkach. |
| 5B Wizz Teneryfa + Ryanair Polska | Brak | Brak odpowiedniego przecięcia; bez rozszerzania GDN/KRK. |

Przejrzano także całkiem nowe huby, nie tylko istniejące allowlisty.
Hiszpańscy sąsiedzi POZ to AGP/ALC/BCN/GRO/PMI/VLC. Ich przecięcie z
[pełnymi destynacjami Bintera](https://www.bintercanarias.com/es/destinos)
daje wyłącznie istniejące PMI/VLC. FNC pozostaje niekwalifikujące się.
[Vueling](https://www.vueling.com/es/vuelos-baratos-desde-tenerife) pokazuje
również GRX/OVD/MAD; POZ nie ma do nich wymaganej krawędzi. GRO nie jest
nowym potwierdzonym hubem Vuelinga z Teneryfy. Nie dodano nowego huba ani
nowego portu TFN/TFS we wspólnym hubie; stare trasy sezonowe zachowano.

Źródła pomocnicze/oddzielne:

- Binter [PMI](https://www.bintercanarias.com/es/destinos/palma-de-mallorca)
  i [VLC](https://www.bintercanarias.com/es/destinos/valencia).
- Iberia: zachowany MAD; [oficjalny operator lotniska Aena](https://www.aena.es/es/tenerife-norte-ciudad-de-la-laguna/aerolineas/iberia.html)
  potwierdza MAD. Strona Iberia Express nie była dostępna w narzędziu WWW;
  nie przedstawia się jej nieudanego odczytu jako pustej siatki.
- [Air Europa — własna strona tras z TFN](https://www.aireuropa.com/es-es/ofertas-de-vuelos-desde-tenerife)
  oraz [Aena](https://www.aena.es/es/tenerife-norte-ciudad-de-la-laguna/aerolineas/air-europa.html)
  jako kontrola bezpośrednich MAD/BIO. Samo promowanie dowolnej pary miast
  przez Air Europa nie dowodzi lotu bez przesiadki (np. oferty do PMI).
- [Volotea](https://www.volotea.com/en/flight-offers/from-tenerife-south/):
  BIO/OVD; pozostałe opublikowane kierunki francuskie nie spełniają zniżki.
- [Canaryfly](https://www.canaryfly.es/en/cheap-flights), w tym oficjalny
  [TFN–FUE](https://www.canaryfly.es/en/cheap-flights/tenerife-norte/fuerteventura).

Audyt sieci uruchomiono jawnie z `--low-cost-only`. `routes.binter=[]`
w snapshotcie **nie oznacza braku tras Bintera** i nie certyfikuje jego
globalnego timetable. Zastosowano powyższy osobny przegląd oficjalnych
destynacji i pełną kolekcję zapisanych tras. Helper audytu zapisuje teraz
status `not_checked`/`failed` oddzielnie od poprawnie pustej siatki,
sprawdza kandydatów nowego endpointu zamiast tylko starych hubów i nie
drukuje pustej listy jako wyniku sprawdzenia Bintera.

## Wizz i pomocnicze narzędzia

Materiał `tmp/poz-expansion/verified-wizz-schedules.json` zawiera 36
obserwacji Google Flights HTTP. Każda odtwarza się dokładnie przez resolver.
LTN–POZ: W95389, 125 minut zimą, 130 minut 24.10 o 07:45 (jawny wyjątek
daty); POZ–LTN: W95390, 120 minut 24.10 i 135 minut w zimowym rozkładzie.
Nie kopiowano parametrów WRO. POZ/TFN/TFS sprawdzono Wizz w obu kierunkach:
brak aktywnych lotów w oknie, nie brak wykonania zapytań.

Generator konfiguracji wymaga teraz jawnego początku i pełnego okna,
odrzuca dowody innego endpointu/okna, obsługuje opisy siedmiu endpointów
bez powielania POZ i zatrzymuje się, gdy kandydat wymaga nowego portu
Teneryfy zamiast go milcząco pomijać. Wspólne i lokalne dane pozostałej
szóstki nie zostały przebudowane. Ponowny przebieg generatora na aktualnych
danych dał semantycznie identyczne wszystkie dziesięć plików konfiguracyjnych.
Niezwiązanych oczekujących kandydatów Wizz (m.in. WRO–BBU/OTP) nie aktywowano.

## Nowa kolekcja i pokrycie

Staging: `tmp/poz-expansion/batch-2026-10-23/`.
Run ID: `3f11be44-c429-4c52-82e5-4ae9b41d6a61`.
Okno: 2026-10-23–2026-11-22, 31 dat włącznie. Nowy cache Ryanaira
przydzielony przez runner, bez użycia cache i cen WRO.
Wspólny dzienny EUR/PLN: 4.3917; niezmienione źródła i reguły cen.
Google maksymalnie dwa zapytania, kolektory wykonywane kolejno.

| Feed | Zaplanowane bazowe route/day | Wyniki | POZ |
| --- | ---: | ---: | ---: |
| 1A | 5952 | 2817 | 18 |
| 1B | 992 | 2196 | 0 |
| 1C | 3286 | 2847 | 207 |
| 1D | 744 | 857 | 0 |
| 1E | 248 | 8 | 0 |
| 1F | 434 + 124 szczegóły dostępnych dni | 224 | 0 |
| 2 | 1736 | 207 | 0 |
| 3 | 10602 | 4870 | 594 |
| 4 | 1302 | 200 | 0 |
| 5 | 5146 | 707 | 3 |

Łącznie **14 933 propozycje**, z czego **822 POZ**: 433 Polska → Teneryfa
i 389 Teneryfa → Polska. Przy domyślnych rezydent=tak, WDC=nie, 1000 zł i
6 h dostępnych jest odpowiednio 55 i 40 propozycji POZ. Cała baza zachowuje
także droższe loty i przesiadki do 24 h.

Wszystkie dziesięć raportów ma status `complete`, zgodne sidecary i jeden
run ID; **30 566/30 566 pozycji pokrycia, zero brakujących i zero
nieoczekiwanych**. To nie liczba requestów HTTP: kalendarze Wizz obejmują
okres, a wspólne odcinki Ryanaira wykorzystują cache. Ukończono dokładnie
14 570 unikalnych tras/dni Ryanaira. Nie było ręcznego wznowienia runu.
Hash zamrożonej konfiguracji pozostał zgodny z metadanymi cache:
`1fd6dd1e2c0c4c6ffcb183cc1069809d82c5755ec745a39be72a3f2a592164f4`.

Dla POZ źródła Ryanair/Wizz nie zwróciły w tym oknie lotów bezpośrednich,
mimo pełnego sprawdzenia wszystkich 248 wymaganych pozycji POZ/TFN/TFS.
Nie oznacza to sprawdzenia innych przewoźników czarterowych ani braku lotów
przez cały rok. Dla kroku 3 zatwierdzono 16 hubów, ale dopasowania 2–24 h
w zwróconych kalendarzach powstały przez 12: STN 295, DUB 67, EDI 52,
BGY 52, MAN 35, BHX 28, LPL 26, BRS 14, SNN 12, CRL 7, OPO 5, LBA 1.
AGP/BVA/TSF/VLC pozostają na liście i mają komplet sprawdzeń, mimo braku
pasującej propozycji POZ. W 5A przez LTN są trzy propozycje wyłącznie
Teneryfa → Polska; kierunek odwrotny również w całości sprawdzono.

| Endpoint | Nowe propozycje | Polska → Teneryfa | Teneryfa → Polska |
| --- | ---: | ---: | ---: |
| WAW | 2010 | 1031 | 979 |
| WMI | 1914 | 957 | 957 |
| KTW | 801 | 445 | 356 |
| KRK | 5138 | 2555 | 2583 |
| GDN | 1988 | 1004 | 984 |
| WRO | 2260 | 1141 | 1119 |
| POZ | 822 | 433 | 389 |

GDN jako transfer do KRK: **7 propozycji**, nadal tylko 5B. Zmiany liczby
propozycji starej szóstki względem baseline wynikają z nowego odczytu
dostępności/cen, nie z usunięcia ich uprawnień lub rozkładów. Ich identyczne
wejścia pozostają regresyjnie porównane; nie obiecuje się identycznych cen
w różnym momencie pobrania lub późniejszego zakupu.

Nie zmieniono źródeł cen, sposobu liczenia rezydenta, linków zakupu,
limitów kalendarza ani reguł dopasowania. POZ nie wymaga nowej opłaty Aeny
ani waluty. Estymator używa dotychczasowych stawek do końca 2026;
Binter/Canaryfly zachowują oficjalne końcowe imports, bez mnożenia netto.

## Testy i odbiór

- Baseline: 165 Python i 14 JS — OK.
- Zmiany: pełny zestaw **182 Python — OK**, w tym 17 nowych testów POZ.
- `node --check app.js` i `git diff --check` — OK.
- **16 integracyjnych testów JS — OK** na pełnym stagingu i ponownie na
  nowych publicznych danych lokalnych. Obejmują oba kierunki POZ i cztery
  tryby zniżek, minima kalendarza/wykresu i tę samą docelową kartę,
  osiem sortowań, X filtrów/dat, +1, linki udostępniania także powyżej
  1000 zł, reset i nieaktywne pola przy lotach bezpośrednich. Dubler DOM
  nie jest testem wizualnym ani potwierdzeniem natywnego schowka.
- Dodatkowy audyt całej bazy przeszedł: sumy zwykłych cen, pełne numery,
  daty odlotów w oknie, oficjalne domeny linków i brak tokenów, zgodność
  trasy/daty linków Ryanair/Wizz, polityka polskich transferów i hash
  konfiguracji. Raport: `tmp/poz-expansion/batch-2026-10-23/acceptance-report.json`.
- **Odbiór wizualny pozostaje otwarty:** próba dostępu do lokalnego podglądu
  zwróciła `Local browser use is disabled in Work settings`. Nie obchodzono
  tego ustawienia innym narzędziem.
- Domyślne Polska → Teneryfa, 1000 zł, 6 h i najbliższy termin bez zmian.

## Lokalna promocja i odtworzenie

Po kompletnych testach wykonano `--validate-only --promote`. Wszystkie
**20 plików w `data/` jest bajtowo identycznych ze stagingiem** i przeszły
ponowną walidację całego publicznego batcha. Przed promocją potwierdzono,
że stare 20 plików nadal odpowiadało baseline; backup wraz z manifestem
obecności znajduje się w
`tmp/poz-expansion/batch-2026-10-23/previous-public-feeds/`.
Przy ewentualnym wycofaniu odtworzyć także konfigurację/kod sześciu
endpointów z baseline, nie tylko stare feedy przy nowym rejestrze siedmiu.

Lokalny HTTP `127.0.0.1:8000` zwrócił nowy HTML z POZ, nową wersję
`app.js` oraz wszystkie 20 plików identyczne z lokalnym `data/`.
Podgląd: `http://127.0.0.1:8000/?build=poz-local-20261023`.
Nie przedstawia się tego odczytu HTTP jako testu renderowania w przeglądarce.
Pierwszy odbiór lokalny zakończono bez publikacji, commita, push ani tworzenia
workflow. Późniejsze osobne polecenie użytkownika obejmuje publikację kodu,
konfiguracji, testów, dokumentacji oraz wszystkich dziesięciu feedów i ich
sidecarów. Robocze cache, kopie i surowe odpowiedzi w `tmp/` pozostają lokalne.
