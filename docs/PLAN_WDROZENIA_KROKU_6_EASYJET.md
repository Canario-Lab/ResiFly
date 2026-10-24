# Plan wdrożenia kroku 6 — easyJet + Ryanair / Wizz Air

Data: **24.10.2026**. Plan na podstawie aktualnego kodu ResiFly, oficjalnych
stron przewoźnika oraz wcześniejszego pełnego snapshotu siatek FR/Wizz z tego
samego dnia. To dokument wykonawczy, **nie gotowy kolektor**.

**Realizacja ukończona lokalnie po osobnym poleceniu użytkownika.** Pierwsza
bramka direct HTTP zwróciła 403; następnie użytkownik zatwierdził Google
Flights. Zbudowano i lokalnie podmieniono komplet 11 feedów; krok 6 zawiera
2184 propozycje. Stan końcowy i dowody odbioru:
[`WDROZENIE_KROKU_6_EASYJET_STATUS.md`](WDROZENIE_KROKU_6_EASYJET_STATUS.md).
Poniższe opisy etapu planowania pozostają historycznym punktem wyjścia.

## 1. Decyzja użytkownika i granice bieżącego zadania

Użytkownik wyraźnie zatwierdził nowy **główny krok 6**, nie wariant 1G:

- Polska → Ryanair/Wizz Air → wspólny port → easyJet → TFS/TFN.
- TFS/TFN → easyJet → wspólny port → Ryanair/Wizz Air → Polska.

easyJet obsługuje zawsze geograficzną nogę teneryfską, również po odwróceniu
kierunku. Nie dodajemy easyJet na polskiej nodze ani easyJet + easyJet.

Obowiązują wszystkie 15 polskich endpointów z `data/search-airports.json`,
odczytywane przez `scripts.search_airports`, bez nowej listy w kodzie:
WAW, WMI, KTW, KRK, GDN, WRO, POZ, LCJ, RZE, BZG, LUZ, SZY, RDO, SZZ, IEG.
Badamy obydwa lotniska Teneryfy oddzielnie. Zgoda na krajowe przesiadki nadal
obowiązuje, ale hub nie może być końcem własnej trasy. Nie dodajemy LOT-u,
Norwegian, czarterów, zmiany lotniska ani drugiej przesiadki.

**Teraz: tylko plan i odczyty dowodów.** Nie uruchamiać całej kolekcji,
nie zmieniać aplikacji/kolektorów/list tras/obecnej bazy, nie robić commita/push,
nie zakładać kont ani nie wykupywać integracji. Realizacja wymaga osobnego
polecenia. Wybór płatnego lub wymagającego umowy dostępu jest osobną decyzją.

## 2. Stan zastany, który trzeba zachować

- HEAD: `789abe5abe876279a728d997a83d107e3bcd53d1`; gałąź ma historyczną nazwę
  `codex/add-lodz-lcj`, która nie określa zakresu nowego kroku.
- W chwili planowania lokalnie istnieją **niezacommitowane poprawki
  automatycznego odzyskiwania**: `source_recovery.py`, podłączenia do źródeł,
  testy i dokumentacja. Zachować je, nie wracać do wersji z samego HEAD.
- Obecnie runtime nadal ma pięć głównych kroków, 10 feedów, 10 sidecarów
  i dziewięć allowlist. Uzgodnienie kroku 6 nie zmieniło jeszcze runtime.
  Docelowo: sześć głównych kroków, 11 feedów, 11 sidecarów i dziesięć allowlist.
- Obecna publiczna baza: 2026-10-24–2026-11-23, run
  `3a5a1329-a7e2-4b95-a2e5-6b10546a544d`, 16 087 propozycji.
- Udokumentowany ostatni odbiór kodu z recovery: 273 testy Python i 45 JS.
  To baseline, nie wynik przyszłego easyJet.
- Google globalnie max 3 rzeczywiste próby HTTP, w tym retry, jedna rodzina
  naraz. Wizz/Binter/Canaryfly/Volotea niezależnie do dwóch na źródło.
- Pełny runner zbiera raz unikalne obserwacje, potem buduje feedy kolejno,
  bez sieci, z jednego runu, konfiguracji, adapterów i NBP.
- Recovery bez pytania: zwykły budżet adaptera + najwyżej dwie odroczone rundy
  60/120 s; poprawnych zadań nie powtarzać. Brak danych nigdy nie jest zerem.

## 3. Najważniejsze ustalenie: źródło easyJet nie jest jeszcze rozstrzygnięte

### 3.1. Co potwierdzono

Oficjalny katalog [Flights Timetables](https://www.easyjet.com/en/flights-timetables)
jest źródłem kandydatów sieci, nie dowodem dostępności w każdej dacie.
W odczytanej sekcji TFS wymieniono 22 porty:

`AMS BSL BFS BER BHX BOD BRS EDI GVA GLA LPL LGW LTN SEN LYS MAN LIN MXP NTE NCL NCE CDG`.

Nie znaleziono tam TFN. To **brak pozytywnego dowodu w tym katalogu**, nie
gwarancja, że TFN nie pojawi się w innym sezonie. Podczas właściwego discovery
zweryfikować oba porty, również kierunki powrotne, i zapisać status źródła.
Nie doklejać TFN na podstawie TFS ani odwrotnie.

Publiczne strony tras [TFS–LTN](https://www.easyjet.com/en/cheap-flights/tenerife-south/london-luton)
i [TFS–LGW](https://www.easyjet.com/en/cheap-flights/tenerife-south/london-gatwick)
nie dostarczyły w odczycie tekstowym kompletnej listy ofert. Zawierają elementy
wymagające JavaScript oraz informację, że prezentowane ceny dotyczą jednej
osoby przy dwóch podróżujących w jednej rezerwacji. To nie poświadcza wyceny
jednego dorosłego i indywidualnej ceny każdego rejsu.

**Nie potwierdzono anonimowego endpointu HTTP zapewniającego komplet danych
produkcyjnych. Nie ma jeszcze dowodu, że bezpłatny direct collector zadziała.**
Zaplanowana dodatkowa próba dwóch zwykłych odczytów HTTP z lokalnego środowiska
nie została wykonana: mechanizm zatwierdzania narzędzia odmówił z powodu
limitu użycia. Nie był to HTTP403/429 easyJet i nie wolno tak tego opisywać.
Nie obchodzono tego ograniczenia. Odczyty stron narzędziem WWW są osobnym
materiałem, nie testem przyszłego klienta z naszego środowiska.

### 3.2. Oficjalna droga bez Google

[Distribution Charter](https://www.easyjet.com/en/business/distribution-charter)
opisuje dostęp do danych przez umowę Direct API albo zatwierdzony kanał
dystrybucji; ogranicza też automatyczne wydobywanie danych ze strony przez
resellerów. Nie jest to dowód istnienia otwartego API dla naszej aplikacji.
Przed produkcyjnym użyciem rozstrzygnąć zgodność wybranego sposobu z zakresem
uzyskanego dostępu. Nie traktować dostępnego technicznie JSON-a jako zgody
na cykliczne publikowanie jego danych.

Przewoźnik publikuje [zatwierdzonych partnerów](https://www.easyjet.com/en/business/approved-channels.),
m.in. Duffel, Kyte i Travelfusion, oraz stronę
[Travel trade partners](https://www.easyjet.com/en/business/travel-trade-partners).
To alternatywa dla obciążania Google, ale dostępność konta, koszty, limity,
prawo do przechowywania/wyświetlania i pełność kalendarzy nie zostały tu
sprawdzone. Nie zakładać, że sam fakt umieszczenia partnera na liście daje
nam bezpłatny klucz, pełną siatkę lub uprawnienie do trwałej publikacji cen.

### 3.3. Kolejność wyboru źródła — bramka przed implementacją całości

1. **Preferowane: bezpośredni dozwolony interfejs easyJet**, który przejdzie
   próbkę danych i ma wystarczające warunki dostępu.
2. Jeśli taki dostęp jest umowny: przedstawić wymagania użytkownikowi.
   Nie zakładać konta, nie akceptować umowy i nie płacić bez decyzji.
3. Zatwierdzony partner może odciążyć Google, lecz wymaga osobnej oceny
   pokrycia, dostępu i kosztów; nie włączać go samodzielnie.
4. Dopiero gdy direct nie spełnia wymagań, przedstawić Google Flights HTTP
   jako **jawny wariant rezerwowy do zatwierdzenia**, wraz z kosztem zapytań.
   Nie dodawać go po cichu i nie przełączać w czasie runu.
5. Jeśli nie ma akceptowalnego źródła pełnych cen, zakończyć etap źródła
   raportem. Można mieć discovery i testy offline, ale nie publikować
   pozornie kompletnego kroku 6 z minimum dnia lub cenami innych lotów.

Nie korzystać z logowania pracowniczego/staff travel jako furtki, cudzych
kluczy, omijania CAPTCHA, rotacji IP lub obchodzenia HTTP403. Blokada/wyzwanie
to błąd dostępu, nie brak lotów i nie powód do osłabienia walidacji.

## 4. Próbka dopuszczenia źródła — zanim powstanie pełny skan

Mały, jawnie ograniczony test, po odblokowaniu środowiska i ustaleniu ścieżki
dostępu: maksymalnie kilkanaście kombinacji trasa/dzień, nie całe kalendarze.
Nie ruszać obecnej bazy. Początkowo jedno żądanie naraz.

Przypadki do wyboru z faktycznej oferty:

- TFS↔LTN i TFS↔LGW: obydwa kierunki, dzień z kilkoma rejsami;
- TFS↔MXP lub BSL: inna spółka/format numeru i inna strefa lokalna;
- przylot po północy, dzień bez lotu i dzień wyprzedany;
- daty z obu miesięcy okna i zmiany czasu — bez wymyślania aktywności trasy;
- 1 dorosły, 0 dzieci/niemowląt, one-way, bez płatnych dodatków;
- jeśli zostanie znaleziona kwalifikująca się trasa hiszpańska: resident i
  non-resident dla dokładnie tego samego rejsu i taryfy.

Warunki PASS:

1. Każdy oferowany bezpośredni rejs ma własne IATA, pełne daty/godziny,
   numer, przewoźnika i końcową należną cenę w jawnej walucie.
2. W dzień z kilkoma rejsami wszystkie mają **własne** ceny — nie jedna cena
   „od” skopiowana na rozkład. Nie wystarczy minimum dnia nawet z godzinami.
3. Znana jest liczba pasażerów i wliczenie obowiązkowych opłat. Nie mnożyć
   lub dzielić przypadkowo ceny „per person przy 2 osobach”.
4. Odczyt nie jest ofertą hotel+lot, powrotem, połączeniem chronionym
   `Connections by easyJet` ani podróżą z dodatkową przesiadką.
5. API ma zrozumiałą paginację/zakres i dowód kompletności wszystkich ofert;
   test obejmuje więcej niż pierwszy blok wyników/stronę.
6. Sukces pusty i wyprzedanie są rozróżnialne od błędu, challenge, timeout,
   HTTP429, HTTP200 z błędem lub odpowiedzi „wczytuję wyniki”.
7. Rejs/cena porównane z normalną wyszukiwarką przewoźnika przy takich samych
   parametrach i możliwie bliskim czasie. Zmiana ceny w czasie jest oddzielną
   obserwacją, a nie automatycznym dowodem błędu parsera.
8. Dostęp jest powtarzalny bez ręcznej sesji; ewentualne sekrety pozostają
   wyłącznie w lokalnej konfiguracji/sekretach środowiska, nigdy w Git/feedzie.

Zapisać bezpieczny raport: czas UTC, źródło, trasa/data, status, liczba rejsów,
waluta, typ taryfy, zakres ceny i pasażerów, wynik porównania, typ błędu.
Nie utrwalać surowego HTML z tokenami, cookies, identyfikatorów sesji i
nieanonimizowanych requestów. Brak numeru/godziny/ceny nie jest „do uzupełnienia
szablonem”. Nie rozpoczynać implementacji produkcyjnej bez PASS źródła.

## 5. Wstępne discovery — konkretni kandydaci, jeszcze nie aktywne trasy

Przecięto wymienione 22 kody z **pełnymi** siatkami FR/Wizz zachowanymi przy
poprzednim wdrożeniu, nie tylko z dzisiejszymi allowlistami. Materiał lokalny:
`tmp/szz-ieg-expansion/audit-SZZ/network-snapshot.json`, data 24.10.2026,
5317 kierunkowych krawędzi FR i 2584 Wizz. Podczas wdrożenia odświeżyć grafy;
ten snapshot służy projekcji, nie dowodzi aktualnego kalendarza cen.

| Hub | Polska noga Ryanair — kandydaci | Polska noga Wizz — kandydaci |
| --- | --- | --- |
| BSL | — | WAW, WMI, KRK, WRO, POZ |
| BFS | KRK | — |
| BHX | WMI, KRK, WRO, POZ, LCJ, BZG | — |
| BRS | WMI, KRK, GDN, WRO, POZ, RZE, BZG | — |
| EDI | WMI, KRK, GDN, WRO, POZ, RZE | — |
| GLA | WMI, KRK, WRO | — |
| LPL | WAW, WMI, KRK, GDN, WRO, POZ, SZZ | WAW |
| LGW | — | KRK |
| LTN | KRK, WRO, RZE, BZG, LUZ | WAW, KTW, KRK, GDN, WRO, POZ, LUZ |
| LYS | — | WAW, KRK |
| MAN | WAW, WMI, KTW, KRK, GDN, WRO, POZ, RZE | — |
| MXP | WMI, KRK, GDN, RZE | WAW, KRK, GDN |
| NCL | KRK, GDN, WRO | — |
| NCE | — | WAW, KRK, GDN, WRO |

Wynik wstępny: **14 hubów, 73 pary hub/polski port/przewoźnik**:
50 FR i 23 Wizz. Pozostałe osiem kodów bez wspólnej nogi w tym snapshotcie:
`AMS BER BOD GVA SEN LIN NTE CDG`.

To kandydaci sieciowi. Nie gwarantować żadnej liczby nowych ofert. WMI≠WAW,
LPL≠MAN, LTN≠LGW/STN, GLA≠PIK, MXP≠BGY/LIN, CDG≠ORY/BVA, BSL nie jest
automatycznym aliasem MLH/EAP. W szczególności nie robić sztucznej przesiadki
„Paryż” między dwoma różnymi IATA.

Discovery pierwszego wdrożenia ma:

1. Odczytać pełną aktualną siatkę easyJet TFS i TFN; potwierdzić kierunki,
   sezonowość i kraj/lotnisko, zachować jawne błędy źródeł.
2. Odczytać pełne aktualne siatki FR i Wizz dla wszystkich 15 endpointów.
3. Obliczyć wspólne porty niezależnie dla FR i Wizz. Również te, których
   nie ma dziś w żadnym kroku ResiFly. Nie ograniczać do hubów Bintera.
4. Zweryfikować polskie pary, metadane stref i numery/czasy Wizza.
5. Przedstawić raport dry-run; dopiero kompletne kandydatury zapisać do
   allowlisty. Brak kalendarza nie oznacza braku trasy sezonowej.
6. Zapisać uzasadnienia odrzuconych/pending par. Nie usuwać automatycznie
   istniejących sezonowych wpisów przy kolejnych audytach.

### 5.1. Brakujące techniczne dane Wizza

W obecnym `data/wizz-route-schedules.json` nie ma obu kierunków 12 par:
BSL↔WAW/WMI/KRK/WRO/POZ, LGW↔KRK, LYS↔WAW/KRK,
NCE↔WAW/KRK/GDN/WRO. To **24 wpisy kierunkowe wymagające weryfikacji**,
nie 24 potwierdzone aktywne rejsy. Stare/nieaktualne krawędzie w grafie są
możliwe; zweryfikować je przed aktywacją, szczególnie nietypowe pary.

Publiczny timetable Wizza daje ceny/datę/odlot, ale nie pełną godzinę przylotu
i numer. Nie wymyślać czasu blokowego i nie kopiować numeru z innego portu.
Zebrać niezależne oficjalne dowody obu kierunków; jeśli konieczny będzie
ograniczony audyt techniczny Google, wyraźnie oddzielić go od pełnego źródła
cen i uwzględnić we wspólnym limicie 3. Sprzeczne godziny/numery zapisać
przez istniejące override ISO-weekday/date, z dowodami i datami.
Niepełne pary pozostają pending, nie blokując aktywacji innych kompletnych
kandydatów. Nie udawać, że pending był sprawdzony z zerem cen.

## 6. Pierwsza kontrola zniżki rezydenta

[Oficjalne warunki easyJet](https://www.easyjet.com/en/terms-and-conditions/large-families)
opisują zniżkę dla uprawnionych mieszkańców na bezpośrednie podróże pomiędzy
miejscem zamieszkania a resztą Hiszpanii i wybór statusu podczas rezerwacji.
Istnienie tej polityki **nie dowodzi istnienia kwalifikującej się trasy**
TFS/TFN w naszym zestawie. Wstępne 22 kody prowadzą poza Hiszpanię, więc na
tej liście nie znaleziono kandydata rezydenckiego. To wynik obecnego przeglądu,
nie stałe założenie w kodzie.

W allowliście każda noga easyJet ma jawne eligibility, datę i dowód decyzji.
Dla niekwalifikującej się: false, mnożnik 1.0, cena rezydenta = regularna.
Nie włączać rabatu tylko dlatego, że rejs odlatuje z Wysp Kanaryjskich.

Jeżeli znajdzie się uprawniona trasa:

1. Preferować oficjalną końcową wycenę resident dla **tego samego rejsu**,
   jednego dorosłego i najtańszej odpowiedniej taryfy.
2. Potwierdzić, co jest wliczone i niedyskontowane; zachować osobno official
   i estimate. Nie przenosić sposobu Binter imports na easyJet bez dowodu.
3. Jeśli konieczny szacunek, użyć wspólnej reguły
   `opłaty + 0.25 × (cena regularna − opłaty)`, ale dopiero po weryfikacji
   jej zastosowania i opłat dla tej trasy. Odczyt z
   `data/spanish-resident-fees.json`, jednym NBP batcha.
4. Rejestr obecnie obejmuje Teneryfa–półwysep, nie dowolne lotnisko Hiszpanii.
   Nie zgadywać opłaty dla nowej wyspy/kategorii. Brak sprawdzonej reguły,
   okresu ważności lub finalnej wyceny blokuje taką publikację.
5. Przełączenie filtra resident zmienia wyłącznie kwalifikującą się nogę.
   Noga FR/Wizz do Polski bez rabatu rezydenta; WDC nadal wyłącznie Wizz.

## 7. Docelowe dane i nowe moduły

### 7.1. Stała allowlista

Nowy `data/easyjet-transfer-airports.json`, odczytywany przez nowy loader.
Nie kopiować twardo macierzy z niniejszej tabeli przed aktualnym discovery.
Pola analogiczne do 1C–1F, ale **bez wymogu zniżki rezydenta**:

- schema/version, `verified_on`, purpose, `usage_policy.step=6`;
- scope: 15 endpointów z rejestru, TFS/TFN ze statusem dowodów;
- easyJet tylko na nodze teneryfskiej, FR/Wizz tylko na polskiej;
- każdy hub: IATA, nazwa, IANA timezone, potwierdzone Tenerife airports;
- `polish_routes`: dokładny endpoint i dozwolone linie, nie ogólne „Polska”;
- eligibility/multiplier i sposób liczenia ceny, dowody i data weryfikacji;
- metoda źródła cen i wersja adaptera, cena/osoba/waluta/opłaty;
- źródła odkrycia, wykluczenia oraz pending nieaktywowane w produkcji;
- bez kluczy API, cookies, tokenów, URL-i sesji i sztucznych godzin.

Zweryfikować rodzinę kodów easyJet zamiast wybierać tylko U2. Oficjalna
[strona lotniska Bordeaux](https://www.bordeaux.aeroport.fr/vols-destinations/compagnies-aeriennes/easyjet)
wymienia U2/EZY, EC/EJU i DS/EZS. Zachować marketing/operating od źródła,
nie dopisywać prefiksu U2 do dowolnego gołego numeru bez uzgodnionej reguły.
W UI jedna rodzina `easyJet`, w danych pełny prawdziwy numer danego rejsu.

### 7.2. Adapter i kolektor

Proponowane nowe pliki:

- `scripts/easyjet_source.py`: klient, normalizacja, walidacja odpowiedzi,
  pełność oferty/paginacji, własne ceny rejsów, bez logiki połączeń;
- `scripts/collect_step6.py`: CLI, plan tras/dni, budowanie i walidacja feedu;
- `tests/test_easyjet_source.py`, `tests/test_step6_collector.py`;
- `data/step6-results.json` i `data/step6-results.collection-report.json`
  dopiero wygenerowane po kompletnej kolekcji, nigdy ręcznie pisane.

Każda noga: carrier/full number, IATA, departure_at/arrival_at z timezone,
price_regular_pln oraz oryginalna waluta/kwota, source/method/scope,
resident eligibility/kwota/official-vs-estimate, deterministyczny booking_url.
Kwoty finite >0, waluta/pasażer jawne. Zaokrąglać zgodnie z istniejącą polityką,
nie sumować nieprzeliczonych EUR/GBP/CHF/PLN. Jeden snapshot NBP na cały batch.

## 8. Algorytm kroku 6

1. Załadować zatwierdzoną allowlistę i wspólny rejestr, wykonać preflight.
2. Zaplanować pełne D–D+30 (**31 dat włącznie**) dla każdej zapisanej
   skierowanej nogi easyJet oraz każdej przypisanej pary FR/Wizz.
3. Zebrać niezależnie komplet easyJet w obie strony, bez filtrowania dat
   rozkładem FR/Wizz. Analogicznie zebrać polskie nogi, bez dat z easyJet.
4. Jeśli źródło daje wiarygodny pełny zakres/miesiąc z wszystkimi rejsami
   i cenami, można zmniejszyć liczbę HTTP, ale coverage nadal dotyczy każdej
   daty. Nie stosować tego do min-price calendar.
5. Wspólny source pipeline deduplikuje już planowane nogi bieżącego runu.
   Nie pytać ponownie o to samo z każdego feedu; nie używać cen starego runu.
6. Dopiero po pełnych źródłach zbudować oba kierunki, same-IATA, dokładnie
   dwie nogi, 120–1440 min włącznie. Porównywać chwile w UTC, prezentować
   lokalnie. Nie traktować minusowej różnicy zegarów jako poprawnej przerwy.
7. Zachować wszystkie legalne chronologicznie pary, nie tylko najtańszą
   dzienną. Deduplikować ten sam rejs/ofertę stabilnym kluczem, a nie godziną
   jednego przewoźnika; numery marketingowe i operating nie tworzą dubli.
8. `step=6`, stabilny ID `step6-...`, `self_transfer=true`, jednoznaczny hub,
   własna data każdego lotu, +1/+2 liczone z dat, nie z porównania HH:MM.
9. Zachować regular/resident/WDC i zależne sumy. Nie stosować filtra ceny
   w kolektorze, również powyżej 1000 zł.
10. Ukończone zero wyników jest legalne, jeśli wszystkie zaplanowane
    obserwacje są kompletne. Timeout lub nieznany payload nie jest zerem.

## 9. Równoległość i spodziewany wpływ na czas

Przy direct easyJet dodać **niezależną kolejkę easyJet** obok Google/Wizza/
Bintera/Canaryfly/Volotei. Rozpocząć ostrożnie od 1 HTTP, podnieść najwyżej
do 2 dopiero po dopuszczeniu adaptera/limitu dostawcy. Każdy retry też zajmuje
slot. Mapowanie hostów musi obejmować faktycznie używane domeny — bez
przypadkowego niezliczania API, subdomeny lub partnera. Limiter OS jak inne
direct źródła; w cache-only sieć nadal zakazana.

Wariant Google, jeśli osobno zatwierdzony: easyJet jako następna rodzina
**po UX**, wspólny max 3, bez równoległego FR+easyJet. Nie trzy dla każdego
przewoźnika. Metoda źródła wybrana przed runem, uwzględniona w identity;
bez cichego mieszania direct/Google w połowie kolekcji.

Projekcja **przed weryfikacją kandydatów Wizz**, dla obecnego okna 31 dni:

| Zakres | Logiczne obserwacje trasa/dzień |
| --- | ---: |
| 14 hubów × 2 kierunki easyJet × 31 | 868 |
| 73 polskie pary/linia × 2 kierunki × 31 | 4526 |
| Cały plan kroku 6 | 5394 |
| Polskie obserwacje już w obecnym planie źródeł | 3534 |
| Dodatkowe polskie FR | 248 |
| Dodatkowe polskie Wizz | 744 |

Nowe FR to BFS↔KRK oraz GLA↔WMI/KRK/WRO. **Nawet direct easyJet nie oznacza
zera nowych zapytań Google**: polską nogę FR nadal pobieramy z Google.
Wizz jest własnym źródłem; logiczne route/day nie oznaczają jego liczby HTTP.
Zatwierdzenie/odrzucenie pending par zmieni te liczby, więc przeliczyć je po
ostatecznej allowliście przed pełnym runem.

Przy rozkładzie z poprzedniej kolekcji 248 nowych zapytań Google to rząd
kilkudziesięciu sekund pracy idealnie rozłożonej na trzy sloty, nie gwarancja
czasu. Wariant Google dla easyJet dołożyłby ponadto 868 query/day, o ile
ostateczny zakres pozostanie taki sam. Nie obiecywać skrócenia całej bazy:
dochodzi nowy zakres. Mierzyć czas, retry, parse errors oraz direct overlap.

## 10. Mapa zmian integracyjnych — nie tylko nowy plik z lotami

| Plik / obszar | Wymagana zmiana podczas wdrożenia |
| --- | --- |
| `AGENTS.md` | Wyraźna decyzja: sześć głównych kroków; nowa allowlista, źródło, zniżka, recovery. Usunąć sprzeczne bieżące „exactly five”. |
| `docs/FIVE_STEP_FLIGHT_SEARCH.md` | Zachować stary path jako kompatybilny, zaktualizować tytuł/procedurę do sześciu; nie przepisywać historycznych raportów jako wykonanych sześciokrokowo. |
| `README.md`, `docs/COLLECTION_RELIABILITY.md` | 11 feedów + 11 sidecarów = 22 pliki, dodatkowa kolejka, komendy, warunki dopuszczenia źródła i rollback. |
| `scripts/collection_coverage.py` | `METHODS` easyJet zgodne z faktycznie wybranym źródłem; osobny plan `step == "6"`, komplet obu nóg/obu kierunków, pending nie udaje zera. |
| `scripts/source_pipeline.py` | Dodać 6 do planowania/budowania; union easyJet+FR+Wizz; direct queue albo jedna nowa rodzina Google; preflight opłat i schedule; zamrożone identity. |
| `scripts/source_scheduler.py` | Provider easyJet/partner, właściwe hosty, niezależny limiter i OS slots, retry i telemetria, brak sieci w build. |
| `scripts/source_repository.py` | Obsłużyć nowego carrier/method, tę samą niemutowalność i certyfikat; bez przejęcia cache starego runu. |
| `scripts/source_recovery.py` | Nowe zadania easyJet w istniejącym bounded recovery, te same limity/cooldown/circuit, brak pytań przy przejściowym błędzie. |
| `scripts/collect_five_steps.py` | Dodać 6 do `STEPS`, 11 walidowanych feedów, 22 backups/promotions/rollbacks, raporty i liczby. Zachować CLI jako kompatybilny wrapper albo świadomie udokumentować nową nazwę runnera; nie psuć starych komend. |
| Nowy wspólny rejestr zestawu feedów, np. `scripts/search_steps.py` | Zalecany do usunięcia rozjazdu między `STEPS` w runnerze i source pipeline; aktualizować importy/testy bez pętli zależności. |
| `scripts/discover_transfer_routes.py` lub osobny discovery easyJet | Nowe pełne przecięcie sieci kroku 6, dry-run, pending Wizz i jawne błędy. Nie dodać discovery do zwykłej kolekcji cen. |
| `scripts/verify_wizz_expansion_schedules.py`, `data/wizz-route-schedules.json` | Zweryfikować wskazane nowe Wizz pary, obie strony i override, bez szablonów z domysłu. |
| `scripts/booking_urls.py` | `easyjet_booking_url` dopiero po weryfikacji obsługiwanego trwałego formatu; route/date/1 dorosły, bez sesji. |
| `scripts/refresh_booking_urls.py` | Obsłużyć easyJet w gałęziach carrier; glob plików sam nie tworzy poprawnych linków. |
| `scripts/reprice_spanish_resident_estimates.py` | Dodać 6 tylko jeżeli faktycznie stosuje estimator; nigdy przeliczać oficjalnej ceny resident przez Aena. |
| `scripts/requirements-flight-collector.txt` | Tylko potrzebne wersjonowane zależności; nie instalować przypadkowego wrappera scrapującego jako dowodu stabilności źródła. |
| `app.js` | Źródło step6, rodzina easyJet/logo/fallback, booking, filtry przewoźników, błędy „1–6”, pricing/łączenie wyników. |
| `index.html`, asset logo | Informacja o easyJet i kroku 6, cache-bust JS; bez niezamówionych zmian globalnego stylu i filtrów. |
| Testy ze stałymi `STEPS`/9 allowlist/10 feedów/20 plików | Aktualizacja bieżących oczekiwań i testów fail-closed dla 22 plików; historyczne fixtures pozostają jawnie historyczne. |

Wyszukać wszystkie odwołania przez `rg`: `STEPS`, `step1f-results`,
`step5-results`, `1–5`, `five`, `ten`, `twenty`, „pięć”, „dziesięć”,
„dwadzieścia”, a także serializację carrier i walidatory źródeł. Nie robić
globalnego tekstowego zastąpienia w historycznych raportach wdrożeń.

Po dodaniu dziesiątej allowlisty `configuration_hash()` obejmie ją przez
istniejący glob, ale trzeba to przetestować. `adapter_hash()` obejmuje nowe
moduły. Zmiana wybranej metody źródła, wersji API lub taryfy/pasażerów również
musi zmieniać jawne identity; sam hash kodu nie opisuje zewnętrznej wersji
dostępu. Sekrety nie są częścią manifestu i nie wolno ich do niego kopiować.

## 11. Link zakupu i UI

Trzeba zweryfikować prawdziwy trwały link easyJet: właściwy kierunek, własna
data nogi, jeden dorosły, bez return i dodatków. Nie wymyślać parametrów
wybierających numer lotu. Jeśli format otwiera wyszukiwanie trasy/daty,
oznaczyć `booking_url_scope=route_date_search`, bez obietnicy preselekcji rejsu.
Jeżeli data nie może być przekazana stabilnie, to jawny brak przed odbiorem,
nie „gotowy link do lotu” podmieniony na ogólną stronę.

Resident w linku tylko jeśli istnieje wspierany parametr i został sprawdzony.
W przeciwnym razie użytkownik wybiera status u przewoźnika, z jasną informacją
w zakupie. Nie utrwalać linku Google/partnera zawierającego sesję jako linku
easyJet. Dwa osobne przyciski zakupu odpowiadają dwóm osobnym biletom.

W UI zachować: Polska→Teneryfa, 1000 zł, 6 h, sortowanie najbliższy termin,
wielokrotny wybór polskich lotnisk, wszystkie obecne zniżki, kalendarz,
wykres i kopię linku do konkretnej karty. easyJet ma pojawiać się na nodze
zgodnej z kierunkiem; filtry carrier mają działać, nie być tylko nową etykietą.
WDC nie obniża easyJet. Wyceny bez eligibility nie zmieniają się od resident.

Nowy feed po właściwej migracji jest wymagany. Nie dodawać bezterminowo
`optional:true`, które ukryje awarię kroku 6 i pokaże „pełną” bazę bez niego.
Kod i 22 pliki wypuszczać razem po odbiorze. Nie zmieniać przy tej okazji
globalnej obsługi starszych opcjonalnych feedów bez osobnego uzasadnienia.

## 12. Testy wymagane przed pierwszą pełną kolekcją

### Adapter źródła

- Kilka rejsów tego samego dnia, różne ceny; wszystkie grupy i paginacja.
- Najniższa własna taryfa rejsu bez przypisania cudzej ceny lub minimum dnia.
- Price scope, 1 vs 2 osoby, waluta, obowiązkowe opłaty, wyprzedanie.
- U2/EC/DS i operating carrier, goły numer bez dowodu odrzucony.
- Godziny/data/timezone/DST i przylot kolejnego dnia, brak pola blokuje.
- HTTP200 error/loading, 403/challenge, 429/Retry-After, timeout i malformed;
  żaden przypadek nie może być pustą dostępnością.
- Brak tokenów/sekretów i danych sesji w outputach/reportach.

### Reguły kroku 6

- Obie kolejności nóg; zawsze easyJet na TFS/TFN↔hub, FR/Wizz hub↔Polska.
- Wszystkie 15 endpointów oraz legalne zero/tylko jeden kierunek.
- Te same IATA; odrzucenie par typu LGW/LTN, MXP/BGY, CDG/BVA.
- 119 i 1441 minut odrzucone, 120 i 1440 przyjęte; chronologia UTC.
- Obie linie mają pełne niezależne okna, także dni bez partnera na drugiej
  nodze. Nie przemycić filtrowania dat przez discovery/schedule.
- Cena powyżej limitu UI jest zachowana; regular/resident/WDC poprawne sumy.
- Brak schedule Wizz = pending przy discovery / błąd aktywnej trasy,
  nigdy zgadnięty przylot.
- Eligibility false bez rabatu; official resident nienaruszony; estimator
  oddzielony z opłatami i okresem ważności tylko dla zweryfikowanych tras.

### Pipeline, awarie i UI

- Ta sama noga z 1–5 i 6 pobrana raz w bieżącym runie; stary cache odrzucony.
- Próby/recovery easyJet nie zwiększają Google, chyba że wybrano jawnie
  wariant Google; wtedy wspólny limit 3 i jedna rodzina naraz.
- Direct easyJet działa równolegle z Google, przy własnym limiterze.
- Brak jednej obserwacji/ceny odrzuca cały 22-plikowy batch; nie tworzy
  certyfikatu sukcesu ani nie miesza cen. Poprzedni komplet zachowany.
- Recovery chwilowej awarii, trwała awaria, circuit, bez restartu całości
  i bez pytania przy bezpiecznym ponowieniu tego samego zadania.
- Wszystkie 11 builderów przy całkowicie zablokowanym HTTP, potem walidacja.
- Backup/rollback obejmuje 22 pliki, także pierwsze wdrożenie, gdy stary
  step6 jeszcze nie istniał. Test awarii w środku podmiany i recovery.
- UI: easyJet w filtrach obu nóg zależnie od kierunku; multiselect OR;
  kalendarz/słupek prowadzą do tej samej najtańszej karty i kwoty; osiem
  sortowań, +1, share, toggle resident/WDC i obydwa booking links.
- Regresje dotychczasowych dziesięciu feedów na zamrożonym fixture; dodanie
  kroku 6 nie może zmieniać ich reguł. Nowe rzeczywiste ceny mogą się zmienić.
- Wizualny desktop i ~320 px, prawdziwy schowek i link zakupu. Jeżeli
  sterowanie przeglądarką pozostaje wyłączone, jawnie pozostawić ten odbiór
  niewykonany. Testy logiki nie są dowodem wyglądu ani działania schowka.

## 13. Kolejność wdrożenia dla wykonującego agenta

1. **Baseline i ochrona recovery**: status/diff, kopia config/feedów/raportów,
   hashe i HEAD. Nie usuwać lokalnych poprawek recovery ani nie publikować ich
   przy okazji bez upoważnienia. Przeczytać aktualne AGENTS i kanoniczne docs.
2. **Bramka źródła**: ustalić dozwolony dostęp direct, wykonać małą próbkę
   zgodnie z rozdz. 4. Jeśli nie ma PASS — raport i wybór źródła, nie masowy
   skan Google w zastępstwie. Nie trzeba implementować całej aplikacji, aby
   odkryć, że źródło daje tylko cenę dnia.
3. **Aktualne discovery** pełnych sieci, oddzielnie TFS/TFN, wszystkie 15
   polskich portów. Raport kandydatów i zniżek, dozwolone polskie huby.
4. **Wizz pending**: zweryfikować brakujące numery/czasy obu kierunków,
   aktualne i sezonowe wyjątki; nieaktywnych nie zgadywać.
5. **Kontrakt danych**: nowa allowlista, metody źródeł, preflight, strefy,
   linki i reguły ceny, testy adaptera i buildera. Ustalić jedną metodę na run.
6. **Integracja sześciu kroków**: rejestr kroków, coverage, kolejki, cache,
   recovery, 11 builderów, 22-plikowa bramka i backup; aktualizacja dokumentacji.
7. **UI i regresje offline**: easyJet, źródło, filtry, ceny, kalendarz/wykres,
   +1/share/zakup. Dotychczasowa publiczna baza nadal nietknięta.
8. **Zamrożenie konfiguracji/adapterów**: dopiero teraz jeden nowy run/NBP,
   plan źródeł i pomiar przyrostu. Zmiana parsera/config w trakcie wymaga
   nowego runu, a nie przepisania hashy starego.
9. **Jedna pełna kolekcja lokalna** wszystkich sześciu kroków w stagingu,
   independent full calendars; bez osobnego zbędnego pełnego benchmarku.
   Recovery automatyczne; nie ponawiać gotowych danych i nie mieszać runów.
10. **Odbiór**: komplet źródeł i coverage, wszystkie 11 feedów i sidecary,
    schema/method/identyczne daty/NBP/run, porównanie cen/parametrów próbki,
    testy na świeżej bazie i raport wydajności.
11. **Lokalna promocja tylko po PASS**: backup 22 plików / stan nieistnienia
    step6, porównanie bajtów i HTTP, ponowne testy UI, prawdziwy widok i linki.
    Uczciwie opisać porty bez dopasowań i te ukryte filtrem 6 h/1000 zł.
12. **GitHub osobno na polecenie**. Nie dodawać automatyzacji/Actions ani
    płatnych kont przy okazji. Przyszły job wymaga tych samych bramek, sekretów
    poza Git i dostępu do zaakceptowanego źródła; lokalny PASS nie jest testem
    dostępu z adresów IP GitHub runnera.

## 14. Kryterium zakończenia i decyzja źródłowa

Krok 6 można uznać za wdrożony, kiedy realne źródło dostarcza kompletne ceny
każdego rejsu i wszystkie wyżej opisane bramki przechodzą — nie kiedy sam
katalog tras da się odczytać lub pojawi się logo easyJet.

**Rekomendacja:** najpierw krótki etap dopuszczenia direct easyJet.
Potwierdzona oficjalna droga API wymaga umowy lub partnera; anonimowego,
pełnego i stabilnego źródła nie potwierdzono. Dopiero wynik tej bramki
powinien rozstrzygnąć direct / zatwierdzony partner / osobno zaakceptowany
Google. Niniejszy plan nie upoważnia do cichego wybrania trzeciego wariantu.
