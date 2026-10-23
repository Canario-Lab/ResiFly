# Lokalne wdrożenie Łodzi (LCJ) — 23.10.2026

Status: **wdrożone lokalnie**. Konfiguracja, kod i dziesięć nowych feedów
obsługują osiem endpointów. Zebrano **15 030 propozycji**, w tym **212 LCJ**,
dla 2026-10-23–2026-11-22; komplet 32 178 pozycji pokrycia, zero braków
i nadmiarów. Zweryfikowano lokalną podmianę bazy, testy i HTTP.
Pierwszy odbiór odbył się **bez commita i push**. Następnie 23.10.2026
użytkownik osobno autoryzował wysłanie całego pakietu LCJ na GitHub.
Nie dodano GitHub Actions. Odbiór wizualny i natywnego schowka pozostaje
jawnie otwarty z powodu wyłączonego sterowania przeglądarką.

## Baseline i zabezpieczenie

Punkt wyjścia: `e6ff8b91b969e9ce2155cecfdacf8163fc61a9ad`, siedem endpointów,
14 933 propozycje i kompletny run `3f11be44-c429-4c52-82e5-4ae9b41d6a61`.
Przed zmianą rejestru zabezpieczono 101 plików kodu, konfiguracji, testów,
dokumentacji oraz feedów/sidecarów w `tmp/lcj-expansion/baseline/`.
Manifest SHA256 i podsumowanie poprzedniej bazy:
`tmp/lcj-expansion/baseline-manifest.json`.
Gałąź lokalna: `codex/add-lodz-lcj`.

## Audyt siatki i granice dowodu

Oficjalne siatki Ryanaira i Wizz pobrano 23.10.2026. Snapshot:
`tmp/lcj-expansion/network-snapshot.json`. Ryanair LCJ: **AGP, ALC, BGY,
BHX, CRL, DUB, STN**. Wizz: brak opublikowanego odcinka LCJ.
Kandydatów wyznaczono z przecięcia siatek, **bez ograniczenia do starych
hubów**. Porównanie z unią wszystkich dziewięciu allowlist baseline nie
wykazało zupełnie nowego huba ani nowego TFN/TFS w znanym hubie.

| Wariant | Dodane uprawnienia LCJ | Uzasadnienie |
| --- | --- | --- |
| 1A Binter | Brak | AGP/ALC nie występują w przejrzanym oficjalnym katalogu destynacji Bintera. Pełna macierz 1A mimo to sprawdza wszystkie zapisane huby z LCJ dla obu linii. |
| 1B Iberia/Express | Brak | Bezpośrednie MAD nie ma low-cost do LCJ. Pełna macierz 1B mimo to sprawdza LCJ/MAD dla obu linii. |
| 1C Vueling | Ryanair przez **ALC i AGP** | Własna strona Vuelinga z Teneryfy potwierdza TFN–ALC i TFN–AGP, a oba huby mają Ryanair do LCJ. |
| 1D Air Europa | Brak | Bezpośrednie MAD/BIO nie mają LCJ; promocyjna oferta TFN–ALC nie jest dowodem bezpośredniego rejsu. |
| 1E Volotea | Brak | BIO/OVD nie mają odcinka low-cost do LCJ. Strona ogólna Volotei jest dynamiczna; użyto również jej strony Asturias i pomocniczo operatora lotniska. |
| 1F Canaryfly | Brak | Żaden port kanaryjski, także ACE/SPC/VDE, nie jest sąsiadem LCJ w siatkach low-cost. |
| 2 | Całe LCJ/TFN/TFS × oba kierunki × obie linie | Brak publikowanego rynku nie jest powodem pominięcia zapytań. |
| 3 Ryanair + Ryanair | **AGP, BGY, BHX, CRL, DUB, STN** | Wspólne kierunki oficjalnych siatek LCJ i TFS. |
| 4 Wizz + Wizz | Brak | Brak odpowiedniego przecięcia siatek. |
| 5A/5B | Brak | Sprawdzono oba przypisania linii do geograficznych odcinków; brak pasującej pary. |

Źródła osobnego przeglądu przewoźników:

- [Binter — wszystkie destynacje](https://www.bintercanarias.com/es/destinos).
  Zbiorczy `timetable_get` zwrócił GraphQL E01000. Snapshot zachowuje `failed`;
  pusta lista Bintera **nie** poświadcza braku tras. Brak przecięcia AGP/ALC
  wyznaczono z odrębnego przeglądu oficjalnych destynacji, nie z błędu API.
- [Iberia Teneryfa–Madryt](https://www.iberia.com/es/vuelos-baratos/Tenerife-Madrid/),
  [Aena TFN/Iberia](https://www.aena.es/es/tenerife-norte-ciudad-de-la-laguna/aerolineas/iberia.html)
  i [Aena TFS/Iberia](https://www.aena.es/es/tenerife-sur/aerolineas/iberia.html).
- [Własna strona kierunków Vuelinga](https://www.vueling.com/es/vuelos-baratos-desde-tenerife):
  także GRX/OVD/MAD, które nie mają odcinka low-cost do LCJ.
- [Air Europa z Teneryfy](https://www.aireuropa.com/es-es/ofertas-de-vuelos-desde-tenerife),
  [promocyjna strona ALC](https://www.aireuropa.com/es-es/ofertas-de-vuelos-desde-tenerife-a-alicante)
  i kontrola bezpośrednich tras przez
  [Aena](https://www.aena.es/es/tenerife-norte-ciudad-de-la-laguna/aerolineas/air-europa.html).
  Nie przekształcono promocyjnej pary miast w fikcyjny bezpośredni rejs.
- [Volotea — Tenerife South](https://www.volotea.com/en/flight-offers/from-tenerife-south/),
  [własna strona Asturias](https://www.volotea.com/en/flight-offers/tenerife-south/to-asturias/)
  oraz pomocniczo [Aena](https://www.aena.es/es/tenerife-sur/aerolineas/volotea.html).
  Ograniczenie odczytu dynamicznej strony ogólnej pozostaje jawne.
- [Canaryfly](https://www.canaryfly.es/en/cheap-flights): siatka międzywyspowa
  nie przecina siedmiu sąsiadów LCJ.

Decyzje, źródła i plan zapytań zapisano w
`tmp/lcj-expansion/route-decisions.json`; oddzielnie raport discovery z jawnym
statusem Bintera: `tmp/lcj-expansion/discovery-reviewed-report.json`.
Nie aktywowano niezwiązanych kandydatów starych endpointów.

## Konfiguracja i techniczne dane Wizz

Rejestr i dziewięć scope: WAW/WMI/KTW/KRK/GDN/WRO/POZ/LCJ;
LCJ ma `Europe/Warsaw`. Wyjątek GDN/5B/KRK bez zmian.
`review_routes.py` potwierdził semantyczną niezmienność całych starych
uprawnień oraz wszystkich wspólnych/lokalnych rozkładów i stref hubów.

Wizz sprawdzono dla LCJ/TFN/TFS w obu kierunkach w pełnym oknie:
cztery poprawne nieaktywne rynki, zero obserwacji technicznych, zero pending.
Nie dodano wymyślonych numerów/czasów; nie zmieniono wspólnego pliku Wizz.
Dowody: `tmp/lcj-expansion/verified-wizz-schedules.json`.

Generator konfiguracji ma poprawkę idempotentnych list endpointów (bez
`/LCJ/LCJ`) i notatkę źródłową odzwierciedlającą faktyczną liczbę obserwacji
Wizz zamiast stałej deklaracji udanej weryfikacji. Dwa przebiegi dały
semantycznie identyczne wszystkie dziesięć kopii konfiguracji.
Nowych hubów 1A–1F nie było do dodania; ograniczenie generatora do istniejących
rekordów tej rodziny nie zostało przedstawione jako pełny audyt nowych hubów.

## Ukończona kolekcja

Staging: `tmp/lcj-expansion/batch-2026-10-23`.
Run ID: `a6f8a0e8-f295-4f20-984e-74607fc6cb08`.
Okno: 2026-10-23–2026-11-22, 31 dat włącznie.
Hash konfiguracji: `5b5f69d1253a4bf6127049e43aadc4b90874fcd469b0d6170d7249ef05629b8f`.
Nowy cache Ryanaira: `ryanair-google-00c45dd54fb015b22d54.jsonl`.
Jeden dzienny NBP EUR/PLN: 4.3917. Kolektory sekwencyjne, Google max 2.

Wszystkie dziesięć feedów ma schema 2, ten sam run i okno, raport `complete`
oraz identyczny sidecar. Sprawdzono zgodność z bieżącym kanonicznym planem
ośmiu endpointów, nie tylko liczbę odpowiedzi. Google Ryanaira: **15 500
unikalnych tras/dni**, wszystkie zapisane w nowym cache tego runu.

| Feed | Propozycje | LCJ | Ukończone / wymagane pozycje pokrycia |
| --- | ---: | ---: | ---: |
| 1A Binter | 2804 | 0 | 6696 / 6696 |
| 1B Iberia/Express | 2179 | 0 | 1116 / 1116 |
| 1C Vueling | 2852 | 43 | 3410 / 3410 |
| 1D Air Europa | 853 | 0 | 744 / 744 |
| 1E Volotea | 8 | 0 | 248 / 248 |
| 1F Canaryfly | 220 | 0 | 558 / 558 |
| 2 bezpośrednie | 205 | 0 | 1984 / 1984 |
| 3 Ryanair + Ryanair | 5011 | 169 | 10 974 / 10 974 |
| 4 Wizz + Wizz | 199 | 0 | 1302 / 1302 |
| 5 mieszane | 699 | 0 | 5146 / 5146 |
| **Razem** | **15 030** | **212** | **32 178 / 32 178** |

1F obejmuje 434 bazowe pozycje oraz 124 szczegóły dostępnych dni; pobrano
komplet kalendarzy miesięcznych przed szczegółami. Krok 2 ma 64 kombinacje
tras/linii × 31 dat; dla LCJ ukończono wszystkie 248 pozycji, bez ofert
bezpośrednich. Zero wyników nie oznacza pominięcia zapytań.

Źródła i ceny bez zmiany zasad: Ryanair FR/RK oraz Air Europa wyłącznie
indywidualne oferty Google HTTP, Wizz oficjalny kalendarz i zweryfikowane
metadane techniczne, Binter/Canaryfly oficjalne końcowe imports RC/DC.
Pozostałe szacunki rezydenta zachowują pełne kierunkowe opłaty ze wspólnego
rejestru; nie przemnożono pełnej ceny przez 0.25. Nie filtrowano cen przy
kolekcji. Nie wykorzystano starych cen ani wcześniejszego cache POZ.

Pierwsze podejście ukończyło 1A–1F. Krok 2 zatrzymała nieznana struktura
odpowiedzi Google dla GDN–TFN, 2026-11-01, po wyczerpaniu retry. Nie uznano
jej za pusty dzień i nie zmieniono parsera. Zachowano log, failed sidecar
i raport jako `step2-attempt1-failed.*` oraz `validation-attempt1-failed.json`.
Wznowiono tylko 2/3/4/5 z tym samym ID/cache; ukończonych sześciu wariantów
nie pobierano ponownie. Publiczna baza nie została podmieniona po błędzie.
Wznowienie poprawnie pobrało również wcześniejszy błędny dzień. Pozostałe
kroki oraz walidacja całej kolekcji zakończyły się sukcesem.

## Wyniki Łodzi i zachowanie pozostałych endpointów

LCJ: **96 Polska → Teneryfa**, **116 Teneryfa → Polska**. W 1C:
ALC 11 (4 wyloty z LCJ, 7 powrotów), AGP 32 (15 wylotów, 17 powrotów).
W kroku 3: STN 118, BGY 10, BHX 18, DUB 23 — razem 169.
Sprawdzono także pełne kalendarze AGP i CRL: Ryanair nie zwrócił w tym
oknie TFS–AGP/AGP–TFS ani LCJ–CRL/CRL–LCJ. Dlatego te zapisane uprawnienia
nie dały połączeń, ale pozostają w konfiguracji jako potencjalnie sezonowe.
Każdy z 24 kierunkowych odcinków sześciu hubów LCJ/3 ma 31 sprawdzonych dat.

| Endpoint | Wszystkie propozycje | Polska → Teneryfa | Teneryfa → Polska |
| --- | ---: | ---: | ---: |
| WAW | 1993 | 1030 | 963 |
| WMI | 1908 | 954 | 954 |
| KTW | 785 | 431 | 354 |
| KRK | 5092 | 2523 | 2569 |
| GDN | 1974 | 1003 | 971 |
| WRO | 2251 | 1138 | 1113 |
| POZ | 815 | 431 | 384 |
| LCJ | 212 | 96 | 116 |

Stara siódemka ma 14 818 aktualnych propozycji. Zmiana liczby względem
baseline 14 933 wynika z nowego pobrania; nie usunięto starych uprawnień.
Zachowano siedem wyników z GDN jako transferem wyłącznie wariantu 5B do KRK.
Przy domyślnych 1000 zł / 6 h / rezydent bez WDC dla LCJ dostępne jest
8 propozycji w każdym kierunku. Pełne 212 wymaga rozszerzenia filtrów.

## Testy i lokalna promocja

196 testów Python przeszło po konfiguracji LCJ. Zachowano regresje GDN/WRO/POZ,
naprawiono historyczne fixture POZ zależne od ostatniego elementu rejestru.
Nowe testy LCJ obejmują pełne macierze, nowe huby aż do planu zapytań,
budowanie obu kierunków, wszystkie warianty i zakaz polskich transferów.

**18 testów JS przeszło na stagingu i ponownie na publicznym lokalnym
`data/`**: osiem endpointów, oba kierunki LCJ, rabaty, minima kalendarza
i wykresu, sortowania, chipy, share i linki zakupu, reset dat, +1 i limit
1000 zł bez odrzucania droższych lotów z bazy. Nowy test początkowo miał
błędną domenę Vuelinga `www.vueling.com`; dopasowano asercję do istniejącego
kanonicznego generatora `tickets.vueling.com`, bez zmiany linków w danych.
`node --check`, `compileall` i `git diff --check` również przeszły.

Audyt akceptacyjny sprawdził globalnie unikalne ID, chronologię i czasy
przesiadek 120–1440 min, połączone odcinki, sumy cen regularnych, numery lotów,
okno, endpointy, wyjątek GDN oraz deterministyczne oficjalne linki bez sekretów.
Raport: `tmp/lcj-expansion/batch-2026-10-23/acceptance-report.json`.

Przed promocją potwierdzono SHA256 wszystkich 20 starych publicznych plików
z baseline. Następnie `collect_five_steps.py --validate-only --promote`
podmienił lokalnie dziesięć feedów i dziesięć sidecarów. Backup:
`tmp/lcj-expansion/batch-2026-10-23/previous-public-feeds/`, manifest 20 plików;
każdy zgodny bajtowo z poprzednim baseline. Ponowna walidacja publicznej
bazy oraz porównanie wszystkich 20 plików ze stagingiem przeszły.
Rollback wymaga spójnego odtworzenia poprzedniego kodu/konfiguracji i feedów;
promocja nie jest transakcją odporną na utratę zasilania.

HTTP 127.0.0.1:8000 zwraca nowe `index.html`, `app.js` i wszystkie 20 plików
danych zgodne bajtowo z lokalnym dyskiem; kod zawiera LCJ i wersję
`20261023-lcj-1`. Podgląd: `http://127.0.0.1:8000/?build=lcj-local-20261023`.

## Otwarty odbiór wizualny

Próba sterowania lokalną przeglądarką w trakcie tego wdrożenia ponownie
zwróciła `Local browser use is disabled in Work settings`; nie obchodzono
wyłączenia. Testy logiki JS na rzeczywistych feedach oraz HTTP nie zastępują
renderowania, weryfikacji szerokiego/wąskiego ekranu, płynności i natywnego
schowka. Te czynności pozostają użytkownikowi do sprawdzenia lokalnie.
Pierwszy odbiór nie obejmował commita ani push. Późniejsze polecenie
użytkownika z 23.10.2026 autoryzuje publikację całego pakietu LCJ i nowej
bazy na GitHub; nie rozszerza zakresu o tworzenie workflow.
