# Krok 6 easyJet — realizacja lokalna, 24.10.2026

## Aktualizacja po pierwszym pełnym odbiorze

Pełny odbiór opisany niżej dotyczy pierwotnego runu `c86f6042`.
Następnie KRK↔NCE zweryfikowano w oficjalnym rozkładzie Kraków Airport
i uzupełniono częściowo z Wizza: 19 rejsów oraz 4 nowe propozycje
TFS→NCE→KRK. Krok 6 ma obecnie 2188 propozycji, całość 18 201.
Pozostałe loty i ceny zachowano wraz z pochodzeniem; nie pobierano ich od nowa.
Pending pozostają tylko BSL↔WAW i NCE↔GDN. Szczegóły aktualizacji i dowody:
[`PARTIAL_FLIGHT_UPDATES.md`](PARTIAL_FLIGHT_UPDATES.md).

## Historia pierwszego odbioru lokalnego

Status: **wdrożone i zweryfikowane lokalnie; bez commita i wysyłania na GitHub**.
Użytkownik polecił realizację planu `PLAN_WDROZENIA_KROKU_6_EASYJET.md`.
Nie oznacza to wdrożenia na publicznej stronie produkcyjnej.

## Odbiór końcowy lokalny

- Pełna świeża kolekcja zakończona, run
  `c86f6042-3364-4a5a-b480-802960801080`, okres 24.10–23.11.2026.
  Wszystkie 35 526 planowanych obserwacji źródeł ukończone; brakujących 0.
- Zwalidowano i podmieniono lokalny komplet **11 feedów + 11 raportów**.
  Łącznie 18 197 propozycji, w tym **2184 w kroku 6**: 1014 Polska→Teneryfa
  i 1170 w drugą stronę. Nie użyto starych cen ani danych testowych.
- Zbadano 14 zapisanych hubów w pełnych kalendarzach obu kierunków;
  dopasowane połączenia powstały przez 13. NCE nie dało dopasowań w tym runie.
  Trzy niezweryfikowane pary Wizz (BSL–WAW, NCE–GDN, NCE–KRK) pozostają
  jawnie pending, bez udawania kompletnego pokrycia tych kandydatów.
- Domyślne filtry Polska→Teneryfa, do 1000 PLN, przesiadka do 6 h dają
  173 propozycje easyJet. Przykład z rzeczywistej bazy: 21.11,
  WRO–LPL FR9298 za 74 PLN + LPL–TFS U23365 za 163 PLN = 237 PLN,
  przesiadka 2 h 45 min. Obie nogi bez zniżki rezydenta.
- **285 testów Python i 47 testów JS przeszło**; dodatkowo budowa wszystkich
  feedów bez sieci, kompletna walidacja i rollback awarii ostatniego z 22 plików.
  Testy JS powtórzono także na finalnej lokalnej bazie i finalnym app.js.
- Lokalny serwer zwrócił 27/27 zasobów HTTP200 z treścią identyczną z plikami.
  Przeglądarka potwierdziła filtr easyJet, szczegóły obu cen i modal z osobnymi
  deterministycznymi linkami zakupu. Link easyJet otwiera trasę/datę dla jednego
  dorosłego, nie gwarantuje automatycznego wyboru konkretnego numeru lotu.
  Kierunek powrotny przy tych samych limitach dał 76 propozycji easyJet,
  z prawidłowymi oznaczeniami +1. Link udostępnienia odnalazł dokładny ID
  przykładu za 237 PLN, rozwinął szczegóły i wyróżnił jego kartę.
- Google osiągnął maksymalnie 3 równoległe próby, pozostałe źródła po 2.
  Właściwe pobieranie źródeł trwało 42 min 01 s (bez budowy i testów).
  To większy zakres niż wcześniejszy batch; nie jest dowodem przyspieszenia.
- Poprzedni zestaw 20 plików zachowano w stagingowym `previous-public-feeds`
  i niezależnym `baseline-public`. Nie wykonano operacji Git ani zmian Actions.

Dowody: `tmp/easyjet-expansion/acceptance-report.json`, `http-report.json`,
`batch-20261024-v2/validation-report.json`, `source-coverage.json`,
`performance.json`, `source-recovery.json` oraz raport niezależnego discovery.

## Bieżący etap po zatwierdzeniu Google Flights

Użytkownik osobno zatwierdził Google Flights dla easyJet i stałe read-only
weryfikacje oficjalnych stron przewoźników. Pobieranie cen pozostaje HTTP,
bez prawdziwej przeglądarki. Przeglądarka służyła wyłącznie weryfikacji
próbki, siatki i linku zakupu, bez konta/płatności/rezerwacji.

- Sześć próbnych zapytań TFS↔LTN, TFS↔LGW i BSL↔TFS dostarczyło własne
  ceny, numery i daty/godziny. TFS–LTN 27.10: U22340 18:10–22:35 304 PLN
  oraz U22304 12:55–17:20 355 PLN. Oficjalna strona dla jednego dorosłego
  pokazała te same godziny oraz 68,99/80,49 EUR z obowiązkowymi opłatami.
  Są to obserwacje próbki, nie obietnica aktualnej ceny w całym kalendarzu.
- Oficjalny katalog i selektor easyJet wskazały 22 porty TFS, bez pozytywnego
  dowodu TFN. Świeże pełne grafy FR i Wizz: 14 wspólnych hubów i 73 pary
  sieciowe. Po weryfikacji Wizza 70 par gotowych; BSL–WAW, NCE–GDN i
  NCE–KRK pozostają jawnie pending. Nieaktywnych/przesuniętych godzin nie
  zastąpiono szablonami. Dopisano 18 kierunkowych wpisów Wizz, z dowodami
  i override tam, gdzie obserwacje różniły się zegarem lub dniem tygodnia.
- Wszystkie obecne nogi easyJet są międzynarodowe: brak zniżki rezydenta.
  Ocena źródłowa jest zapisana oddzielnie przy każdym hubie, nie zaszyta
  jako stałe założenie dla przyszłych tras.
- Rzeczywisty `/deeplink` odczytano z linku kalendarza easyJet. Test innej
  daty/odwróconej trasy potwierdził LTN→TFS 01.11, one-way, 1 pasażer.
  Wymaga potwierdzenia liczby pasażerów i otwiera listę daty, nie wybiera
  numeru lotu. Odrzucono stary `/buy/flights?orig=...`, który ignorował trasę.
- Zaimplementowano adapter, kolektor, niezależny audyt sieci, stałą allowlistę,
  wspólny rejestr 11 feedów, Google po UX, coverage i bounded recovery.
- Na wcześniejszym etapie: 283 testy Python offline z zablokowanym transportem HTTP. Dodatkowo
  wszystkie 11 builderów i pełna walidacja przeszły na usuwanym fixture
  offline, bez sieci/promocji; 5 syntetycznych propozycji sprawdziło krok 6.
  Fixture nie był aktualnymi danymi i nie został opublikowany.
- Pierwszy pełny run `89a197d2-7a53-41ce-8472-f69856293630` zatrzymano
  bez promocji: cztery kierunki BSL→Polska wymagały CHF, którego brakowało
  w dotychczasowym wspólnym zestawie NBP. Automatyczne retry nie mogło
  naprawić brakującej konfiguracji waluty. Dopisano CHF i test odrzucenia
  starego cache bez franka. Rzeczywista próba BSL→KRK 25.10: 63,99 CHF
  przy NBP CHF/PLN 4,7681 dała 305,11 PLN (WDC 258,57 PLN). Obecnie
  285 testów Python przechodzi offline. To poprawka konfiguracji, nie
  zmniejszenie zabezpieczeń parsera lub limitu.
- Właściwa kolekcja bieżących cen po poprawce jest oddzielna:
  `tmp/easyjet-expansion/batch-20261024-v2`.
  Nie używała fixture ani starych cen. Po pełnej walidacji cały nowy zestaw
  podmieniono lokalnie. Bez commita/push.

Artefakty lokalne: `tmp/easyjet-expansion/`: `network-snapshot.json`, raporty
discovery, `wizz-technical.json`, `offline-builders-report.json`, baseline
publicznych 20 plików, przygotowany UI i oddzielny staging nowego runu.

## Historia: niedopuszczone bezpośrednie HTTP

### Wykonana próba direct przed wyborem Google

Z lokalnego środowiska kolektorów wykonano dwa zwykłe, sekwencyjne odczyty
GET przy użyciu zainstalowanego `curl_cffi`, bez impersonation, logowania,
przekazywania sesji, CAPTCHA ani powtarzania prób po odmowie dostępu:

| Publiczny adres | HTTP | Długość odpowiedzi |
| --- | ---: | ---: |
| `https://www.easyjet.com/en/flights-timetables` | 403 | 396 bajtów |
| `https://www.easyjet.com/en/cheap-flights/tenerife-south/london-luton` | 403 | 437 bajtów |

Nie utrwalano surowych odpowiedzi, cookies i tokenów. Raport dotyczy tego
konkretnego klienta/środowiska. Nie dowodzi, że easyJet jest niedostępny
we wszystkich przeglądarkach lub przez autoryzowane API. Nie jest to też
poprzedni problem z zatwierdzeniem narzędzia: teraz żądania zostały wykonane
i rzeczywiście otrzymały HTTP403.

**Nie uzyskano indywidualnych ofert z ceną dla jednego dorosłego.** Nie ma
podstaw do uruchomienia pełnych kalendarzy ani zbudowania kompletnego feedu.
Odmowy nie zamieniono na zero dostępności i nie obchodzono jej innym IP,
tokenem, sesją pracowniczą lub maskowaniem klienta.

## Historia: oficjalne alternatywy przed decyzją o Google

[Distribution Charter easyJet](https://www.easyjet.com/en/business/distribution-charter)
wskazuje umowę Direct API lub zatwierdzony kanał jako ścieżki dostępu do danych
dla resellerów. [Lista partnerów](https://www.easyjet.com/en/business/approved-channels.)
nie jest dowodem dostępu ResiFly do ich API, jego kosztu ani prawa do publikacji
cen. W tym etapie nie uzyskano umowy/klucza i nie akceptowano warunków usługi.

Na tamtym etapie dalsza realizacja wymagała jednego z poniższych:

1. Dozwolony dostęp direct easyJet / zaakceptowany partner, z wymaganym
   kontem, warunkami i zweryfikowaną ceną każdego rejsu.
2. Osobna zgoda na cenowe źródło Google Flights HTTP dla easyJet. Wtedy
   najpierw mała próbka, później ewentualna pełna implementacja z tą samą
   współdzieloną pulą Google max 3, nie dodatkowe trzy połączenia.

Na podstawie wstępnej projekcji 14 hubów: wariant Google dodałby do planu
868 obserwacji easyJet trasa/dzień, a polskie nowe nogi Ryanaira dalsze 248.
Pozostałe wspólne nogi FR nie byłyby pobierane ponownie w tym samym runie.
To projekcja przed weryfikacją kandydatów, nie wynik ukończonej kolekcji.

## Historia: stan zachowany przed zatwierdzeniem Google

Poniższe punkty opisują wyłącznie pierwszą bramkę direct HTTP, nie stan końcowy.

- Bez zmian w aplikacji, kolektorach, konfiguracji, limitach i publicznych
  feedach w ramach tej bramki.
- Zachowano wcześniejsze lokalne poprawki automatycznego odzyskiwania.
- Nadal 10 publicznych feedów i 16 087 wyników, run
  `3a5a1329-a7e2-4b95-a2e5-6b10546a544d`; step6-results nie utworzono.
- Nie dodano pozornego pustego feedu easyJet ani opcjonalnego kroku
  ukrywającego brak źródła. Nie uruchomiono Google dla easyJet.
- Nie pobrano nowych pełnych kalendarzy żadnej linii, nie podmieniono bazy,
  nie wykonano commita, push, PR ani zmian Actions.

Po tej bramce użytkownik zatwierdził Google Flights; próbkę, implementację,
pełne pobieranie i lokalny odbiór wykonano zgodnie z opisem na początku pliku.
