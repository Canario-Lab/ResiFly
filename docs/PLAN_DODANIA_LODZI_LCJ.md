# Plan dodania Łodzi (LCJ) jako ósmego polskiego lotniska ResiFly

Dokument wykonawczy do późniejszej realizacji przez Codexa. Przygotowany
**23 października 2026 r.** na podstawie repozytorium w stanie
`e6ff8b91b969e9ce2155cecfdacf8163fc61a9ad`, po wdrożeniu Poznania.

**Status: wdrożone lokalnie 23.10.2026 na osobne polecenie użytkownika.
Po odbiorze użytkownik osobno autoryzował wysłanie całego pakietu LCJ na GitHub.
Odbiór wizualny/schowka pozostaje otwarty.** Wynik i dowody:
[`WDROZENIE_LODZI_LCJ.md`](WDROZENIE_LODZI_LCJ.md).
Poniższy punkt wyjścia dokumentuje etap przygotowania planu. Wtedy
nie uruchamiano audytu siatki LCJ na żywo, wyszukiwań cen, repricingu ani
promocji. Nie ma tutaj zatwierdzonych tras Łodzi. Nazwy obecnych hubów są
punktem wyjścia do audytu, a nie deklaracją połączeń z LCJ.

Wiążące pozostają `AGENTS.md`, `docs/FIVE_STEP_FLIGHT_SEARCH.md` oraz
`docs/COLLECTION_RELIABILITY.md`. Historycznych planów i raportów GDN/WRO/POZ
nie przepisywać na osiem lotnisk. Niniejszy plan nie upoważnia do wdrożenia,
commita, push ani utworzenia GitHub Actions. Wcześniejsze polecenie publikacji
POZ nie obejmuje LCJ.

## 1. Cel i niezmienne zasady

Docelowy rejestr, z zachowaniem kolejności obecnej siódemki:
**WAW, WMI, KTW, KRK, GDN, WRO, POZ, LCJ**. Nowy wpis:

```json
{ "iata": "LCJ", "name_pl": "Łódź", "timezone": "Europe/Warsaw" }
```

Obsłużyć LCJ → TFN/TFS oraz TFN/TFS → LCJ: bezpośrednio albo z jedną
przesiadką, dla każdej kombinacji przewoźników dopuszczonej w pięciu krokach.
Nie dodawać automatycznie Łodzi do wszystkich istniejących hubów i nie
ograniczać discovery do hubów, które już występują w plikach.

Zachować bez zmian:

- **Pięć głównych kroków**, sześć wariantów 1A–1F, dziesięć feedów.
- Pełne niezależne kalendarze każdego zapisanego odcinka, każdego przewoźnika
  i obu kierunków. Dopasowanie dopiero po zebraniu obu linii; dat zapytań
  jednej linii nie wolno wyznaczać z rozkładu drugiej.
- `--days 30` oznacza dzień startu i 30 kolejnych dni: **31 dat włącznie**.
  Nie zmieniać tej semantyki. Daty odlotów obu odcinków muszą być w oknie.
- Przesiadka na **tym samym lotnisku IATA**, 120–1440 minut włącznie,
  poprawna chronologia i lokalne strefy czasowe. Żadnej zmiany lotniska
  w obrębie miasta, dodatkowego lotu ani dojazdu między polskimi miastami.
- Wyjątek **GDN jako transfer 5B wyłącznie do KRK**. Nie rozszerzać go na LCJ.
  LCJ nie staje się hubem dla pozostałych endpointów. Bez LCJ–LCJ.
- Wszystkie ceny w danych, bez limitu w kolektorach. Na stronie pozostają
  domyślne Polska → Teneryfa, 1000 zł, 6 godzin i najbliższy termin.
- Osobne ceny regularne, rezydenckie oraz WIZZ Discount Club; bez zmiany
  algorytmu ID i reguł udostępniania lotu.
- Jeden dzienny zestaw NBP; Google Flights HTTP maksymalnie **dwa zapytania
  jednocześnie**, także retry i techniczne sprawdzanie rozkładów Wizz.
- Ryanair/Ryanair UK: wyłącznie indywidualne oferty Google HTTP z FR/RK.
  Air Europa: także wyłącznie indywidualne oferty Google HTTP. Bez minimum
  dnia kopiowanego na wszystkie rejsy, Fare Finder i branded feedu Air Europa.
- Binter/Canaryfly: oficjalne końcowe rozliczenia, nie ceny z listy taryf.
  Pozostałe uprawnione odcinki: jawny szacunek ze wspólną tabelą opłat.
- Trwały link zakupu na każdym odcinku, bez cookies, tokenów i sesji.
- Istniejące uprawnienia tras, sezonowość i rozkłady starej siódemki.
  Na zamrożonych tych samych wejściach stare wyniki/ID/ceny muszą być takie
  same. Nowe pobranie może naturalnie zmienić dostępność i ceny.

## 2. Potwierdzony punkt wyjścia po POZ

Przy przygotowaniu planu sprawdzono czyste `main` w powyższym commicie.
Rejestr i scope wszystkich dziewięciu allowlist zawierają dokładnie siedem
endpointów. LCJ nie występuje jako endpoint w feedach ani we wspólnych
technicznych trasach Wizz. Nie sprawdzano jeszcze, czy istnieją żywe trasy LCJ.

Obecna baza przeszła `validate_batch` dla dat **2026-10-23–2026-11-22**,
run ID **`3f11be44-c429-4c52-82e5-4ae9b41d6a61`**. Dziesięć sidecarów
odpowiada osadzonym raportom. Łącznie **14 933 propozycje** i **30 566
ukończonych pozycji pokrycia**. To baseline, nie prognoza wyniku LCJ.

| Feed | Wyniki baseline | Bazowy plan route/day | Zapisane kompletne pokrycie |
| --- | ---: | ---: | ---: |
| 1A (`step1`) | 2817 | 5952 | 5952 |
| 1B | 2196 | 992 | 992 |
| 1C | 2847 | 3286 | 3286 |
| 1D | 857 | 744 | 744 |
| 1E | 8 | 248 | 248 |
| 1F | 224 | 434 | 558 |
| 2 | 207 | 1736 | 1736 |
| 3 | 4870 | 10602 | 10602 |
| 4 | 200 | 1302 | 1302 |
| 5 | 707 | 5146 | 5146 |

1F ma dodatkowe 124 wymagane sprawdzenia szczegółów dni dostępnych według
pełnego kalendarza Canaryfly. Pokrycie to nie liczba requestów HTTP:
Ryanair współdzieli cache, Wizz pyta okresowo, Canaryfly miesięcznie.

Wyniki per obecny endpoint: WAW 2010, WMI 1914, KTW 801, KRK 5138,
GDN 1988, WRO 2260, POZ 822. Raportować też osobno GDN jako transfer;
nie doliczać tej roli do liczby podróży kończących się w Gdańsku.

### Co w kodzie jest już uogólnione

| Obszar | Obecny mechanizm i znaczenie dla LCJ |
| --- | --- |
| Rejestr | `scripts.search_airports` ładuje kody/strefy i wyjątek GDN z `data/search-airports.json`. Dane są ładowane przy imporcie. |
| Discovery 1A/3/4/5 | `discover_transfer_routes.candidate_intersection()` porównuje siatki, nie filtruje kandydatów starą allowlistą. 1B–1F wymagają osobnych audytów. |
| Audyt endpointu | `audit_airport_expansion.py` wymaga `--endpoint`; kandydatami Bintera są wszyscy low-cost sąsiedzi endpointu. Zapisuje jawne `complete`/`not_checked`/`failed`. |
| Wizz | `verify_wizz_expansion_schedules.py` ma `--endpoint`, wznowienie z kontrolą tożsamości i osobne dowody sezonowe. Resolver wspólny: `scripts.wizz_schedules`. |
| Konfiguracja | `build_gdn_config_patch.py` ma jawny endpoint, datę/okno, baseline i kopie do przeglądu. Nie jest pełnym generatorem wszystkich nowych hubów; ograniczenia w sekcji 7. |
| 1A/1B | Wykonawca low-cost sprawdza pełną macierz huby × wszystkie polskie endpointy × dwie linie × oba kierunki. Evidence nie jest filtrem pobierania. |
| 1C–1F | Pobieranie low-cost wynika z konkretnych `polish_routes` i `airlines`. 1D–1F współdzielą wykonawcę low-cost z 1C. |
| 2–5 | Macierz 2 wynika z rejestru; 3/4/5 z konkretnych uprawnień w allowlistach. Warianty mieszane są osobne. |
| Pokrycie | `expected_queries()` planuje przed zbieraniem. Runner raportuje `endpoint_directions` i `endpoint_variants` dla całego rejestru. |
| Batch | Nowy run otrzymuje świeży cache Ryanaira i hash konfiguracji; wznowienie wymaga zgodnych dat/konfiguracji. Promocja obejmuje 20 plików i backup. |
| UI | Selektory powstają z wyników; czytelna nazwa w `app.js.airportLabels`, lista informacyjna w `index.html`. |

Nie trzeba implementować tych mechanizmów od nowa. Trzeba dowieść, że
działają dla ósmego endpointu i każdego nowego zatwierdzonego huba.

## 3. Etap 0 — zabezpieczenie i ponowny odczyt instrukcji

1. Odczytać aktualne `AGENTS.md`, oba kanoniczne dokumenty, ten plan oraz
   raporty WRO/POZ. Sprawdzić HEAD, `git status`, gałąź i zmiany użytkownika.
   Historyczny hash nie jest poleceniem resetowania repozytorium.
2. Dopiero po zleceniu wdrożenia użyć lokalnej gałęzi np.
   `codex/add-lodz-lcj`. Nie robić commit/push bez właściwej zgody.
3. **Przed zmianą rejestru** zabezpieczyć kod, konfigurację, opłaty,
   wspólne i lokalne rozkłady Wizz, testy, dokumentację oraz 20 plików
   starej bazy. Zapisać hash i manifest obecności każdego pliku.
4. Użyć odrębnego `tmp/lcj-expansion/`: `baseline/`, snapshoty siatek,
   raport decyzji, materiał Wizz, kopie konfiguracji, staging, logi i odbiór.
   Nie przerabiać cache/snapshotów POZ lub WRO na materiał Łodzi.
5. Zapisać baseline per endpoint, kierunek, krok, wariant i GDN-transfer.
   Zabezpieczyć niezmienne fixture wejściowe do porównania starej siódemki.
6. Uruchomić testy offline. Obecną bazę sprawdzić w jej właściwym kontekście
   dat: późniejsza odmowa `validate_batch` z powodu starego `generated_at`
   nie upoważnia do zmiany timestampu lub osłabienia kontroli świeżości.

Odbiór: baseline jest odtwarzalny, zakres zmian znany, niezwiązane pliki
użytkownika pozostają nietknięte.

## 4. Etap 1 — kanoniczny rejestr ośmiu i scope

1. Dodać LCJ po POZ w `data/search-airports.json.polish_airports`, z nazwą
   `Łódź` i strefą `Europe/Warsaw`. Sprawdzić brak duplikatów i poprawny IATA.
2. Nie zmieniać TFN/TFS ani `endpoint_transfer_exceptions`. Nie tworzyć
   drugiej listy ośmiu w kolektorach, detektorze lub konfiguracji UI.
3. Uzgodnić `scope.polish_airports` wszystkich **dziewięciu** allowlist z
   rejestrem, także wariantów bez potwierdzonej trasy LCJ.
4. Uaktualnić aktywne zakresy w `AGENTS.md`, kanonicznej instrukcji i README.
   „Sześć wariantów kroku 1” i historia siódmego endpointu POZ nadal są poprawne.
5. Ponownie uruchomić procesy/helpery po zmianie rejestru. Dopiero wtedy
   `argparse choices=POLISH_AIRPORTS` zaakceptuje `--endpoint LCJ`.
6. Sprawdzić `validate_polish_transfer` oraz discovery: zabronione LCJ jako
   hub, LCJ przez GDN/WRO/POZ i każdy inny niezatwierdzony polski transfer.
   Dozwolony stary KRK ↔ GDN ↔ Teneryfa w 5B musi pozostać.
7. Uzgodnić `selection_method.excluded_endpoints` z precyzyjną polityką
   danego wariantu. Nie usuwać wyjątku GDN przez szeroką podmianę listy.

Odbiór: każdy proces widzi ten sam rejestr ośmiu; samo scope nie jest
zatwierdzeniem żadnego konkretnego połączenia LCJ.

## 5. Etap 2 — audyt siatki, także zupełnie nowych przesiadek

### Wymagany dowód: stare listy nie ograniczają discovery

1. Pobrać bieżące oficjalne siatki Ryanair i Wizz oraz metadane lotnisk.
   Zestawić wszystkie kierunki z/do LCJ ze wszystkimi bezpośrednimi
   kierunkami z/do TFN i TFS dla właściwych kombinacji linii.
2. **Nie zaczynać od pętli po starej allowliście.** Kandydat ma powstać z
   przecięcia dwóch siatek. Stare listy służą dopiero do klasyfikacji:
   istniejący hub, istniejący w innym wariancie, całkiem nowy hub lub nowy
   port TFN/TFS w znanym hubie. Zbiór „nowy globalnie” porównać z unią
   hubów wszystkich dziewięciu plików sprzed wdrożenia.
3. Zachować pełne wejścia i listy wspólnych kierunków **przed** aplikowaniem
   zmian. Dodać test z LCJ → NEW → TFS, gdzie NEW nie występuje w żadnej
   starej allowliście. Kandydat ma zostać odkryty i przejść ścieżkę konfiguracji.
   Sam test możliwości algorytmu nie zastępuje rzeczywistego audytu siatki.
4. W 3/4/5 nie ograniczać kandydatów do Hiszpanii lub lotnisk rezydenckich.
   Kwalifikacja do zniżki to osobna cecha odcinka. W 1A–1F zachować regułę
   dopuszczania wyłącznie kwalifikujących się tras linii rezydenckiej;
   nie dodawać np. zagranicznej trasy Bintera poza tym zakresem.
5. Sprawdzić także dawne wykluczenia wynikające jedynie z braku dalszego
   low-cost do Polski. Nie uchylać wykluczeń merytorycznych, np. FNC w 1A.
6. Sprawdzić LCJ ↔ TFN i LCJ ↔ TFS dla obu linii. Brak rynku na mapie
   nie usuwa obowiązku pełnej macierzy kroku 2 w kolekcji cen.

Nie utożsamiać miasta i lotniska: BVA/ORY/CDG, STN/LTN, BGY/MXP,
BBU/OTP to różne węzły. Każdy odcinek przesiadki musi spotkać się na tym
samym IATA. Trasa partnera lub oferta z dodatkową przesiadką nie dowodzi
bezpośredniego lotu danego przewoźnika.

### Osobny audyt sześciu przewoźników rezydenckich

Detektor obsługuje 1A/3/4/5; nie poświadcza pełnego audytu 1B–1F.
Dla każdego wariantu przejrzeć również kierunki spoza zastanej allowlisty:

| Wariant | Warunek zatwierdzenia LCJ i właściwe źródło siatki |
| --- | --- |
| 1A | Bezpośredni kwalifikujący się Binter TFN/TFS ↔ hub i Ryanair/Wizz hub ↔ LCJ. Oficjalne destynacje/rozkład Bintera, nie wyłącznie stara lista sześciu hubów. |
| 1B | Kwalifikujący się bezpośredni Iberia/Express TFN/TFS ↔ hub oraz low-cost do LCJ. Oficjalna siatka przewoźnika; nie zakładać z góry, że MAD zamyka audyt. |
| 1C | Vueling Teneryfa ↔ hub potwierdzony na własnej stronie tras Vuelinga i konkretny low-cost do LCJ. Aena tylko pomocniczo. |
| 1D | Oficjalnie potwierdzony bezpośredni Air Europa Teneryfa ↔ hub i low-cost do LCJ; cena/numery/godziny później wyłącznie z Google HTTP. |
| 1E | Oficjalna siatka Volotei i publiczny MinPrice potwierdzają bezpośredni kwalifikujący się odcinek; low-cost tego samego huba do LCJ. |
| 1F | Bezpośredni Canaryfly TFN ↔ hub i low-cost do LCJ; własne strony tras i GraphQL. Nie dopuszczać wewnętrznej przesiadki Canaryfly. |
| 3 | Ryanair Teneryfa ↔ hub i Ryanair hub ↔ LCJ. |
| 4 | Wizz Teneryfa ↔ hub i Wizz hub ↔ LCJ, oba odcinki mają zweryfikowaną technikę. |
| 5A | Ryanair na odcinku Teneryfy, Wizz na odcinku LCJ. |
| 5B | Wizz na odcinku Teneryfy, Ryanair na odcinku LCJ. |

Odwrócenie kierunku podróży nie zamienia linii przypisanej do geograficznego
odcinka. Audytować A i B niezależnie. Nawet gdy Wizz nie ma aktywnego rynku
LCJ, wariant 5B może nadal korzystać z Wizz na odcinku Teneryfy.

OVD/GRX dla Vuelinga, OVD i inne kierunki Volotei oraz ACE/SPC/VDE i reszta
bezpośredniej siatki Canaryfly są przykładami do ponownej kontroli, nie
potwierdzonymi połączeniami Łodzi. Nie ograniczać osobnych przeglądów do
tych przykładów.

### Awaria źródła i obowiązkowy rejestr decyzji

Przy WRO endpoint Binter `timetable_get` zawodził, a przy POZ użyto jawnego
`--low-cost-only` i osobnego przeglądu destynacji. Nie przenosić dawnych
wyników na LCJ i nie przedstawiać `routes.binter=[]` jako braku tras.

Jeśli audyt Bintera zawiedzie, zachować low-cost snapshot i błąd. Oddzielny
przegląd oficjalnych kierunków musi udokumentować każdy istotny kandydat,
także nowy, oraz bezpośredniość połączenia z Teneryfą. Nierozstrzygnięte
pozycje oznaczyć `pending`; brak dostępu nie jest negatywnym wynikiem.
Nie ogłaszać całego audytu zakończonym, gdy istotne kandydatury są nieustalone.

Zapisać `tmp/lcj-expansion/route-decisions.json` (lub równoważny raport) z:

- krokiem/wariantem, hubem IATA, właściwym TFN/TFS, liniami obu odcinków;
- kierunkami, źródłami, datą odczytu i dowodem bezpośredniej trasy;
- klasyfikacją względem baseline: stary / nowy dla wariantu / zupełnie nowy;
- uprawnieniem do zniżki, wymaganymi danymi Wizz/opłatami;
- statusem: potwierdzony, sezonowy/przyszły, brak rynku, brak danych lub awaria;
- decyzją zastosowania i jej uzasadnieniem; osobno nowy port Teneryfy.

Gdy wynik „zero całkiem nowych hubów” jest prawdziwy, wykazać to zapisanym
porównaniem pełnych zbiorów. Nie wywodzić z tego, że przeszukano tylko stare.
Potwierdzona siatka nie gwarantuje dopasowania przesiadki w bieżących 31 dniach.

Przykłady poleceń **dopiero podczas wdrożenia**, po dodaniu rejestru LCJ:

```text
.venv/bin/python scripts/audit_airport_expansion.py --endpoint LCJ --as-of YYYY-MM-DD --output-directory tmp/lcj-expansion
.venv/bin/python scripts/discover_transfer_routes.py --snapshot tmp/lcj-expansion/network-snapshot.json --report tmp/lcj-expansion/discovery-report.json
```

`--low-cost-only` jest jawnym trybem częściowym, nie poświadczeniem Bintera.
Nie używać globalnego `--apply` bez przeglądu: raport obejmuje także stare
endpointy i może zawierać niezwiązane propozycje wymagające osobnej decyzji.

## 6. Etap 3 — techniczne dane wszystkich potrzebnych tras Wizz

1. Uruchomić `verify_wizz_expansion_schedules.py --endpoint LCJ` na nowym
   snapshotcie i własnym pliku dowodów z właściwym oknem. Nie zmieniać domyślnego
   GDN w helperze na LCJ; nie używać materiału POZ przez podmianę nazwy.
2. Porównać `required_routes()` z pełnym raportem decyzji i projektowaną
   konfiguracją. Potrzebne są oba kierunki LCJ–hub, ewentualne LCJ–TFN/TFS,
   a przy nowym hubie w 4/5B także oba kierunki hub–Teneryfa. Uwzględnić pełne
   macierze 1A/1B i lokalne metadane, nie tylko dopasowane przesiadki.
3. Bieżące daty, odloty i regular/WDC nadal z oficjalnego `timetableV2`,
   numer wersji przez `scripts.wizz_api`. Numery i czasy techniczne z
   wiarygodnych obserwacji Wizz w Google HTTP. Nie kopiować czasów POZ/WRO.
4. Zweryfikować wszystkie aktywne godziny i różnice dat/dni tygodnia.
   Utrwalić pełne numery, czasy blokowe i poprawne lokalne strefy obu końców.
   Dowód z sąsiedniego dnia nie gwarantuje identycznego czasu w każdy dzień.
5. Trasy sezonowe można technicznie sprawdzić jawnym
   `--inactive-probe-date YYYY-MM-DD`. Oddzielić taki dowód od dostępności
   i cen w aktualnym oknie. Nie publikować przyszłej ceny jako dzisiejszej.
6. Rozwiązać konflikty przez clock/weekday/date overrides; pierwszeństwo
   data → dzień ISO tygodnia → godzina → baza. Nie wybierać arbitralnie
   pierwszej/najczęstszej sprzecznej obserwacji. Każdy zapisany dowód musi
   odtwarzać się przez `resolve_schedule()` z właściwą datą.
7. Przygotować `data/wizz-route-schedules.json` i odpowiednie lokalne
   `wizz_route_schedules` oraz override 1A/1B. Zachować ich zgodność.
   W kolejnym etapie zweryfikowany materiał wykorzysta generator konfiguracji.
8. Nie usuwać sezonowych tras starej siódemki, WRO–LPA z poniedziałkowym
   wyjątkiem ani POZ–LTN i jego zweryfikowanych różnic daty/czasu.
9. Brak aktywnego rynku Wizz LCJ może być prawidłowym wynikiem, ale błąd
   HTTP/GraphQL/503/retry nim nie jest. Aktywna wymagana trasa bez numeru
   lub czasu blokuje wdrożenie tej pozycji; nie wolno dopisać szablonu.

```text
.venv/bin/python scripts/verify_wizz_expansion_schedules.py --endpoint LCJ --snapshot tmp/lcj-expansion/network-snapshot.json --from-date YYYY-MM-DD --days 30 --output tmp/lcj-expansion/verified-wizz-schedules.json
```

Weryfikacja techniczna nie zastępuje pełnych niezależnych kalendarzy cen.
Brak ofert Google dla wyprzedanego dnia nie uzasadnia wynalezienia danych.

## 7. Etap 4 — wszystkie allowlisty i ograniczenia generatora

### Pliki do przejrzenia, nie lista tras zatwierdzonych dla LCJ

| Plik w `data/` | Zastane huby | Wymagana praca po audycie |
| --- | --- | --- |
| `binter-transfer-airports.json` | FUE, LPA, MAD, PMI, SVQ, VLC | Scope, evidence low-cost i lokalne Wizz; także kompletny rekord każdego nowego kwalifikującego się huba. |
| `iberia-transfer-airports.json` | MAD | Scope, evidence, lokalne Wizz i nowe huby tylko z niezależnym dowodem. |
| `vueling-transfer-airports.json` | ALC, BCN, BIO, AGP, SCQ, SVQ, VLC | LCJ w odpowiednich `polish_routes` z dokładnymi `airlines`; ewentualne nowe rekordy. |
| `air-europa-transfer-airports.json` | MAD, BIO | Jak wyżej, zachować accepted airline codes i źródło Google HTTP. |
| `volotea-transfer-airports.json` | BIO | Potwierdzone pary LCJ i nowe huby, bez usuwania sezonowego WRO–BIO. |
| `canaryfly-transfer-airports.json` | FUE, LPA | Potwierdzone bezpośrednie pary, DC/final imports, brak automatycznej trasy LCJ–wyspy. |
| `ryanair-transfer-airports.json` | 34 huby | LCJ w uprawnieniach potwierdzonych hubów; nowe rekordy, strefy, rabaty, liczniki. |
| `wizzair-transfer-airports.json` | BBU, BUD, FCO, MXP, OTP, SCQ | Dokładne uprawnienia LCJ i komplet techniki Wizz, nie kopia POZ/WRO. |
| `mixed-transfer-airports.json` | A: 19, B: 6, 22 różne | Osobne uprawnienia A/B, strefy, rabaty i liczniki; GDN/5B tylko KRK. |

Nowy rekord potrzebuje IATA, nazwy, IANA timezone, właściwych TFN/TFS,
konkretnych endpointów/linii, kwalifikacji rezydenckiej i mnożnika, dowodów
oraz ewentualnych reguł opłat. Wiedza ma trafić do danych, nie hard-code
kolektora. Dla kroków 3–5 uzupełnić `airport_timezones`.

### Obecne pułapki wymagające jawnego rozwiązania

1. `build_gdn_config_patch.py`, mimo historycznej nazwy, obsługuje endpoint
   z rejestru i sprawdza datę snapshotu oraz pełne okno. Użyć `--endpoint LCJ`,
   `--from-date`, `--days`, kopii baseline i osobnego wyjścia do przeglądu.
2. W części 1A–1F generator **iteruje tylko po istniejących `airports`**.
   Nie utworzy sam nowego huba Bintera/Iberii/Vuelinga/Air Europy/Volotei/
   Canaryfly. Każdy nowy hub z raportu decyzji trzeba obsłużyć osobno albo
   rozszerzyć generator z testem; wygenerowany patch nie dowodzi kompletności.
3. Przy istniejącym hubie 3–5 generator odrzuca nowy TFN/TFS komunikatem
   `Review new Tenerife airports explicitly`. To zabezpieczenie zachować.
   Nie usuwać nowego portu z dowodów, żeby obejść błąd.
4. Poszerzenie `tenerife_airports` wspólnego huba może rozszerzyć również
   stare siedem endpointów. Jawnie ustalić wpływ i przetestować. Jeśli
   potrzebna jest relacja per endpoint, opisać ją w danych i wykonawcy;
   nie tworzyć powtarzających się rekordów IATA ignorowanych przez loader.
   Zmiany niezwiązane z LCJ przedstawić do osobnej decyzji.
5. Tekstowy regex generatora kończy się obecnie na opcjonalnym `/POZ`.
   Po rozszerzeniu rejestru ponowny przebieg może dopisać **`/LCJ/LCJ`**.
   Uogólnić aktualizację listy kodów i opisów, dodać test dwóch przebiegów
   LCJ. Regex liczebników także nie obejmuje jeszcze „osiem”.
6. Generator dopisuje ogólną notatkę źródłową o weryfikacji Wizz. Dostosować
   ją do faktycznie wykonanego zakresu: pusta siatka, sezonowe dowody lub
   `pending` nie mogą stać się deklaracją pełnej udanej weryfikacji.
   Nie odświeżać historycznych źródeł/dowodów samą zmianą `verified_on`.
7. Porównać nowe rekordy z dotychczasową zawartością wspólnego/lokalnych
   rozkładów. Generator nie może zastąpić istniejącego poprawnego rozkładu
   przypadkową pojedynczą obserwacją z audytu LCJ.
8. Przeliczyć wszystkie liczniki, listy rabatowe, scope, strefy i wykluczenia.
   Sprawdzić dokładny zbiór LCJ/hub/wariant/linia z raportem decyzji oraz
   semantyczną niezmienność starej siódemki, nie tylko poprawność JSON.
9. Patch nakładać przez `apply_patch`, z jednoznacznym kontekstem huba.
   Krótkie powtarzalne fragmenty JSON grożą dopisaniem LCJ do złego lotniska.

```text
.venv/bin/python scripts/build_gdn_config_patch.py --endpoint LCJ --snapshot tmp/lcj-expansion/network-snapshot.json --schedules tmp/lcj-expansion/verified-wizz-schedules.json --from-date YYYY-MM-DD --days 30 --baseline-directory tmp/lcj-expansion/baseline/data --output-directory tmp/lcj-expansion/configuration-review
```

To przygotowanie kopii do oceny, nie zgoda na zastosowanie całości discovery.
Przebieg drugi na wygenerowanych kopiach musi być idempotentny, a test nowego
huba musi potwierdzać jego obecność aż do planu zapytań kolektora.

## 8. Etap 5 — rzeczywiste macierze dziesięciu kolektorów

| Kolektor | Zakres wymagany po dodaniu LCJ |
| --- | --- |
| 1A `collect_step1.py` | Każdy zapisany hub × osiem polskich endpointów × Ryanair/Wizz × oba kierunki i wszystkie dni; niezależnie każdy dzień Bintera oraz końcowe imports. Evidence nie ogranicza macierzy. |
| 1B `collect_step1b.py` | Analogiczna pełna macierz low-cost, także brakujące rynki; niezależnie pełne kalendarze Iberii/Express. |
| 1C `collect_step1c.py` | Każda zapisana para LCJ/hub/linia z `polish_routes`; niezależnie wszystkie dni Vuelinga. |
| 1D `collect_step1d.py` | Własna allowlista dla wspólnego wykonawcy low-cost; indywidualne pełne oferty Air Europa, Google max 2. |
| 1E `collect_step1e.py` | Wszystkie zapisane low-cost i każdy dzień każdej trasy Volotei w obu kierunkach, bez Google. |
| 1F `collect_step1f.py` | Pełne miesięczne Canaryfly obu kierunków, potem wszystkie wymagane szczegóły i imports; niezależne low-cost. |
| 2 `collect_step2.py` | Osiem × TFN/TFS × dwa kierunki × dwie linie = **64 kombinacje**, także LCJ bez wykrytego rynku. |
| 3 `collect_step3.py` | Wszystkie zatwierdzone stare i nowe huby Ryanair; LCJ–hub oraz hub–Teneryfa, oba kierunki, wszystkie dni, FR/RK. |
| 4 `collect_step4.py` | Wszystkie zatwierdzone pary Wizz na obu odcinkach, regular/WDC i zweryfikowany resolver. |
| 5 `collect_step5.py` | A i B osobno, pełne kalendarze właściwych linii obu geograficznych odcinków; nie zamieniać linii w powrocie. |

Przy niezmienionej liczbie obecnych hubów/portów i 31 datach minimalne
rozszerzenia wynikające z samych pełnych macierzy są następujące:

| Zakres | Siedem endpointów | Osiem endpointów |
| --- | ---: | ---: |
| Krok 2: skierowane pary na linię | 28 | 32 |
| Krok 2: kombinacje trasa–linia | 56 | 64 |
| Krok 2: plan route/day | 1736 | 1984 |
| 1A low-cost: kombinacje | 168 | 192 |
| 1A całe pokrycie z obecnym Binterem | 5952 | 6696 |
| 1B low-cost: kombinacje | 28 | 32 |
| 1B całe pokrycie z obecną Iberią | 992 | 1116 |

Macierz kroku 2 rośnie o około 14,3%, niekoniecznie tyle samo wyniki,
czas lub liczba requestów. Nowe huby, porty i uprawnienia tras zmienią pozostałe
plany. Nie przepisywać starych liczników do certyfikatów ośmiu.

Po zamknięciu konfiguracji wyliczyć wszystkie dziesięć planów przez
`scripts.collection_coverage.expected_queries()` **przed zapytaniami**.
Sprawdzić każdą zatwierdzoną parę LCJ/linia/kierunek/dzień i nowe odcinki
Teneryfy. Poprawnie pusty dzień ma wpis `checked` z zerem, nie brak.
Canaryfly po pełnych kalendarzach dodaje obowiązek szczegółów dostępnych dni.

## 9. Etap 6 — źródła, opłaty, NBP i linki

Nie zmieniać polityki cen przy dodawaniu endpointu:

| Linia | Źródło bieżących rejsów/cen | Rezydent |
| --- | --- | --- |
| Ryanair / Ryanair UK | Google Flights HTTP, własna najniższa cena każdego FR/RK, wszystkie rozpoznane grupy ofert. | Tylko uprawniony hiszpański odcinek w 3/5; wspólne opłaty. LCJ–Teneryfa bez bonifikaty. |
| Wizz | Oficjalne `timetableV2` regular/WDC; numer/czas z zatwierdzonego rejestru. | Tylko uprawniony odcinek 4/5; WDC osobno. |
| Binter | `booking_search` wybiera EUR cash fare, `booking_getImports` podaje końcowe składniki. | Oficjalna końcowa kwota dla jednego dorosłego RC; bez estymatora. |
| Iberia / Express | Google Flights HTTP. | Jawny szacunek ze wspólnymi opłatami. |
| Vueling | Google Flights HTTP; własna strona tras jako źródło siatki. | Jawny szacunek ze wspólnymi opłatami. |
| Air Europa | Wyłącznie Google HTTP: pełny numer UX, daty/godziny, osobna cena każdego rejsu. | Jawny szacunek, nie oficjalna wycena przewoźnika. |
| Volotea | Oficjalny MinPrice route/day, kwota z opłatami; bez Google. | Szacunek, z kontrolą zgodności zwróconych opłat ze wspólnym rejestrem. |
| Canaryfly | `booking_calendar` → `booking_search` → `booking_getImports`; bez Google. | Oficjalna końcowa kwota dla jednego dorosłego DC; bez estymatora. |

1. Binter/Canaryfly: regularna = suma `mainAmount`, rezydencka = suma
   `totalAmount` taryfy, taxes, supplements, service fee i management fee.
   PTS nie są EUR. Brak składnika/właściwej waluty/potwierdzenia rezydenta
   blokuje zapis; token tylko w pamięci, nie w feedzie/raporcie/logu.
2. Szacunki wyłącznie przez `scripts.spanish_resident_fees` i
   `data/spanish-resident-fees.json`: opłata PLN + mnożnik × (regularna PLN
   − opłata PLN). Nie mnożyć całej ceny przez 0.25, nie dyskontować opłat.
3. Sam LCJ nie wymaga nowej stawki Aeny. Nowy kwalifikujący się odcinek
   hiszpański wymaga właściwych reguł **obu kierunków** i dowodów.
   Nie zgadywać opłaty ani kopiować modelu półwyspowego na lot międzywyspowy.
4. Obecny okres rejestru opłat to 2026-03-01–2026-12-31. Przy wdrożeniu
   ponownie sprawdzić pełne okno odlotów; brak/wygaśnięcie reguły blokuje zapis.
5. Wszystkie opłaty i taryfy EUR przeliczać jednym dziennym NBP batcha.
   Zachować `tmp/nbp-rates/YYYY-MM-DD.json` i `NBP_SHARED_CURRENCIES`
   z `collect_step1.py`; nowe waluty ewentualnych rynków uzgodnić z
   `SOURCE_CURRENCIES` pozostałych kroków. Nie pytać NBP od nowa co krok.
6. Każdy odcinek ma własny deterministic `booking_url` do linii, wygenerowany
   przez `scripts.booking_urls`; Binter zachowuje aktualny poprawny mechanizm.
   Zweryfikować trasę, datę, pasażerów i oficjalną domenę. Bez sesji/tokenu.
7. Air Europa zachowuje `residentType=SPANISH_RESIDENT_RC` na uprawnionej
   trasie; strona usuwa parametr po wyłączeniu rezydenta. To wyszukiwanie
   trasy/dnia, nie potwierdzone automatyczne wybranie numeru UX.
   Nie obiecywać dokładnego preselektora również dla Wizz/Ryanair.
8. Canaryfly/Volotea potwierdzają rezydenta we własnym interfejsie; nie
   dopisywać wymyślonych parametrów lub LCJ do kanaryjskich slugów.
9. `reprice_*` nie dodają siatki Łodzi i nie zastępują nowej kolekcji.

## 10. Etap 7 — UI, instrukcje i wersjonowanie

1. `app.js.airportLabels`: dodać `LCJ: "Łódź (LCJ)"`. `index.html`: dopisać
   Łódź do zakresu polskich lotnisk, podnieść wersję `app.js` dla cache.
   Bez przypadkowych zmian stylów, kolorów lub istniejących tekstów.
2. Zachować dynamiczne selektory kierunków. Jeśli wszystkie endpointy mają
   wyniki, obecne sortowanie IATA daje:
   `all, GDN, KRK, KTW, LCJ, POZ, WAW, WMI, WRO`.
3. Brak LCJ po filtrze 1000 zł/6 h nie oznacza braku zebrania. Gdy pełne
   pobranie nie da żadnej oferty LCJ, nie tworzyć fikcyjnej karty ani pustej
   opcji wbrew obecnej logice; przyczynę wykazać w raporcie.
4. Sprawdzić oba kierunki i cztery kombinacje resident/WDC. Kalendarz i
   wykres mają liczyć minimum tą samą funkcją co karty i wskazywać ten sam lot.
5. Sprawdzić osiem sortowań na pełnym zbiorze, dogrywanie kart,
   zakotwiczenie wyniku, cache, puste wyniki oraz czas przygotowania większej bazy.
6. X filtra LCJ przywraca wszystkie lotniska; X dat pełne okno. Reset:
   Polska → Teneryfa, 1000 zł, 6 h, najbliższy termin. Bezpośrednie:
   nieaktywny czas przesiadki i druga linia, jak dotychczas.
7. Sprawdzić +1 przy przylocie następnego dnia, share obu kierunków, także
   lotu powyżej 1000 zł, zachowanie rabatów i dokładnego ID. Domyślny
   kierunek nie może nadpisać kierunku z linku. Zniknięty stary lot nadal
   obsługuje dotychczasowy komunikat, nie sztuczne odtworzenie oferty.
8. Sprawdzić panel zakupu i linki obu odcinków, telefon oraz szeroki ekran.
   Nie zmieniać obsługi pięciu wyróżnianych filtrów przy okazji LCJ.
9. Aktualizować aktywne listy/macierze `AGENTS.md`, instrukcji i README,
   nie historyczne liczby WRO/POZ. Utworzyć podczas wdrożenia
   `docs/WDROZENIE_LODZI_LCJ.md` z rzeczywistymi wynikami i dowodami.

## 11. Etap 8 — testy LCJ i regresja starej siódemki

Dodać `tests/test_lcj_expansion.py`; zachować testy GDN, WRO **i POZ**.
Nie zastępować przypadków Poznania przypadkami Łodzi.

### Konkretne miejsca do dostosowania

- `test_airport_expansion.py`, `test_wro_expansion.py`, `test_poz_expansion.py`:
  jawne oczekiwania siedmiu endpointów zmieniają się na osiem. Zmienić nazwy
  testów opisujących aktualne scope, ale nie historyczne fixture SIX.
- `test_step2_collector.py`: 28 skierowanych par zmienia się na 32.
  `test_source_completeness.py`: jednodniowy plan 56 zmienia się na 64.
  Testy WRO/POZ pełnego pokrycia `56 * 31` zmieniają się na `64 * 31`.
- Dwuhubowe testy low-cost 1A/1B w GDN/POZ: 28 wywołań na linię zmienia się
  na 32. Jawnie sprawdzić LCJ w obie strony również przy pustych odpowiedziach.
- **Pułapka testów POZ:** `test_old_six_direct_and_transfer_results_unchanged_on_frozen_inputs`
  nadal używa `direct[:-1]`, a dane tworzy z aktualnego rejestru. Po dodaniu
  LCJ usunie LCJ zamiast POZ. Inne regresje generują aktualne osiem, usuwają
  tylko POZ i porównują z SIX. Ograniczyć stare fixture jawnie do historycznej
  szóstki/siódemki; nie maskować rozbieżności zmianą wartości oczekiwanych.
- Dla nowej regresji LCJ użyć jawnego baseline
  `SEVEN = ("WAW", "WMI", "KTW", "KRK", "GDN", "WRO", "POZ")`.
  Porównywać te same wejścia/uprawnienia przed i po rozszerzeniu,
  filtrując wszystkie odcinki/wyniki wyłącznie nowego endpointu.
- `test_airport_ui.mjs`: lista selektora z LCJ, odrębne przypadki Łodzi i
  pętle sortowań/filtrów/share obejmujące LCJ. Istniejące GDN/WRO/POZ zachować.
- Testy konkretnych tras/rabatów 1C–1F aktualizować tylko z audytu.
  Brak realnej trasy LCJ nie jest powodem dodania jej dla zielonego testu.

### Macierz odbioru

| Obszar | Wymagane dowody/testy |
| --- | --- |
| Rejestr | Dokładna ósemka i dziewięć zgodnych scope; Europe/Warsaw; zero duplikatów. |
| Nowe huby | LCJ–NEW–TFS odkryte bez NEW w starych listach; zapis nowego huba i obecność w planie zapytań. Osobno dotychczasowy hub i nowy TFN/TFS. |
| Źródła discovery | Jawna awaria/not_checked Bintera; brak zamiany błędu na zero tras; pełne low-cost snapshoty i osobne 1B–1F. |
| Generator | Jawne LCJ/datowanie, odrzucenie materiału POZ/innego okna, brak `/LCJ/LCJ` po dwóch przebiegach, prawidłowy hub, nowe rekordy 1A–1F. |
| Wizz | Oba kierunki, godziny, czasy, pełne numery; date/weekday/clock precedence i zgodność lokalnych/wspólnego rejestru. |
| 1A–1F | LCJ w obu kierunkach; nie tylko `build_connections`, ale właściwy planner i rzeczywisty wykonawca wywołań na mockowanych źródłach. |
| Krok 2 | 64 × 31, w tym osiem kombinacji LCJ/linia/kierunek/TFN/TFS i poprawnie sprawdzone zera. |
| 3/4/5 | Oba kierunki i oba warianty mieszane, właściwy przewoźnik na geograficznym odcinku; bez utraty starego GDN/5B/KRK. |
| Ceny | FR/RK, różne ceny rejsów tego samego dnia, wszystkie grupy ofert; imports RC/DC; opłaty obu kierunków i fail closed dla braków. |
| Czas | 119/120/1440/1441 minut, północ, zmiana czasu, granice okna; czas rzeczywisty liczony z poprawnymi strefami/UTC. |
| Coverage | Siedem nie certyfikuje ośmiu; niezależne dni obu linii, poprawne zera i błędy; brak raportu/mieszane runy blokują promocję. |
| Cache/NBP | Nowy run = świeży cache; wznowienie wymaga identycznych dat/hash; jeden NBP, Google max 2 także retry. |
| Promocja | Backup/rollback 20 plików, również brakującego sidecara; żadnego mieszania poprzedniej i nowej bazy. |
| UI/linki | Oba kierunki LCJ i cztery tryby rabatów; kalendarz/słupek → karta, X/reset/direct/+1, share i zakup obu odcinków. |
| Regresja | Stare siedem: te same ID/ceny/dopasowania na zamrożonych wejściach, zachowane WRO–LPA i POZ–LTN, LCJ nie staje się transferem. |

Syntetyczny test wariantu bez żywej trasy potwierdza tylko mechanikę, nie
istnienie połączenia. Po kolekcji wykonać JS na rzeczywistych danych LCJ;
jeśli wariant jest pusty, potwierdzić skan i uzasadnić zero, nie wymuszać lotu.

```text
.venv/bin/python -m unittest discover -s tests -p 'test_*.py'
node --check app.js
node --test tests/test_airport_ui.mjs
git diff --check
```

## 12. Etap 9 — nowa kompletna baza ośmiu w stagingu

1. Zakończyć audyt, decyzje, rozkłady, opłaty i testy konfiguracji **przed**
   produkcyjnym runem. Zamrozić hash konfiguracji na czas kolekcji.
2. Wyznaczyć bieżący dzień w `Atlantic/Canary`, jawne `--from-date`,
   `--days 30`, nowe run ID i własny staging np.
   `tmp/lcj-expansion/batch-YYYY-MM-DD-RUN`. Nie używać ID/cache POZ.
3. Uruchomić runner w kolejności **1A, 1B, 1C, 1D, 1E, 1F, 2, 3, 4, 5**.
   Odświeżyć pełną ósemkę. Nie dopisywać cen LCJ do starych cen siedmiu
   ani nie nadawać starej bazie nowych certyfikatów kompletności.
4. Zachować `RESIFLY_COLLECTION_RUN_ID` i wspólny nowy
   `RESIFLY_RYANAIR_GOOGLE_CACHE` nadawane przez runner. Metadane cache
   muszą zgadzać run, daty, okno i hash konfiguracji. Użyć jednego NBP dnia.
5. Kolektory uruchamiać sekwencyjnie. Nie uruchamiać równolegle obok
   weryfikatorów/prób Google: semafor 2 jest procesowy, nie wspólny między
   niezależnymi procesami. `--workers 4` nie podnosi limitu Google.
6. Po awarii zachować log i failed report, nie nadpisywać ich bez kopii przy
   retry. Nie obchodzić parserów i nie uznawać błędu za pusty dzień.
7. Wznawiać nieudany i wszystkie niewykonane kroki z tym samym run ID,
   datami i konfiguracją. Ukończonych feedów **tego samego runu** nie pobierać
   ponownie bez potrzeby. Nie uruchamiać całości od zera przy każdym retry.
8. Zmiana konfiguracji lub przejście na nowy dzień kanaryjski wymaga nowego
   pełnego runu. Nie poprawiać `generated_at` i nie mieszać starych kursów/cen.
9. Na tym etapie nie zmieniać publicznego `data/` i nie wykonywać Git.

Szablony do przyszłego wdrożenia, **nie do uruchamiania przy pisaniu planu**:

```text
.venv/bin/python scripts/collect_five_steps.py --from-date YYYY-MM-DD --days 30 --stage-directory tmp/lcj-expansion/batch-YYYY-MM-DD-RUN --workers 4
.venv/bin/python scripts/collect_five_steps.py --from-date YYYY-MM-DD --days 30 --stage-directory tmp/lcj-expansion/batch-YYYY-MM-DD-RUN --run-id RUN_ID_Z_RAPORTU --refresh-steps 3 4 5
.venv/bin/python scripts/collect_five_steps.py --from-date YYYY-MM-DD --days 30 --stage-directory tmp/lcj-expansion/batch-YYYY-MM-DD-RUN --validate-only
RESIFLY_TEST_DATA_DIRECTORY=tmp/lcj-expansion/batch-YYYY-MM-DD-RUN node --test tests/test_airport_ui.mjs
```

`3 4 5` to przykład wznowienia po awarii kroku 3. Przy awarii 1C lista
obejmuje `1c 1d 1e 1f 2 3 4 5`. Używać rzeczywistych dat/ID, nie placeholderów.

## 13. Etap 10 — odbiór, lokalna podmiana i odzyskiwanie

Przed promocją obowiązkowo potwierdzić:

1. Dziesięć feedów schema 2, jeden nowy run, to samo okno, zgodne dzienne
   kursy i daty zebrania. Sidecary identyczne z raportami wewnętrznymi.
2. Wszystkie raporty `complete`, zero braków/nadmiarów i zgodny bieżący plan
   ośmiu endpointów. Każda wymagana para LCJ i nowy odcinek Teneryfy
   sprawdzone niezależnie, także dni z zerem ofert.
3. Audyt końcowy: **odkryci kandydaci → decyzje → konfiguracja → zaplanowane
   zapytania → ukończone pokrycie**. Żaden zaakceptowany nowy hub lub port
   nie może zniknąć w generatorze. Nierozstrzygnięte źródła pozostają jawne.
4. Unikalne ID globalnie, poprawne endpointy, pełne numery, daty/strefy,
   połączone odcinki, rabaty/opłaty i sumy cen, wszystkie linki bez sekretów.
5. Wyniki LCJ per krok/wariant/kierunek/hub/linia, osobno stara siódemka
   i GDN-transfer. Oddzielić brak rynku, brak dopasowania 2–24 h i brak
   wyniku przy domyślnych 1000 zł/6 h. Zero nie zastępuje raportu pokrycia.
6. Testy offline i JS na stagingu. Do podglądu można użyć lokalnej kopii
   strony z kompletem stagingu; nie trzeba jeszcze podmieniać `data/`.
7. Rzeczywisty odbiór w przeglądarce: LCJ jako wylot/przylot, stare siedem,
   karty, daty/kalendarz/słupki, zakup/share, schowek, filtry, +1, szeroki
   i wąski ekran, płynność większej bazy.
8. Przy WRO/POZ dostęp do sterowania przeglądarką był wyłączony. Sprawdzić
   aktualny stan; nie obchodzić wyłączenia innymi narzędziami. Jeżeli nadal
   brak dostępu, oznaczyć odbiór wizualny/schowka jako otwarty i przekazać
   użytkownikowi do weryfikacji. Test DOM i HTTP 200 nie potwierdzają renderu.

Po odbiorze, w granicach zlecenia wdrożenia, lokalna promocja:

```text
.venv/bin/python scripts/collect_five_steps.py --from-date YYYY-MM-DD --days 30 --stage-directory tmp/lcj-expansion/batch-YYYY-MM-DD-RUN --validate-only --promote
```

Promocja obejmuje **20 plików**: dziesięć feedów i dziesięć sidecarów.
Zachować `previous-public-feeds/` i manifest. Obsłużona awaria uruchamia
rollback, lecz nie jest to jedna transakcja odporna na nagłe zabicie procesu
lub utratę zasilania. Nie składać fałszywej gwarancji atomowości całego zestawu.

Po promocji zwalidować publiczne `data/`, porównać bajtowo 20 plików ze
stagingiem, ponowić JS i odczyt HTTP kodu/danych. Otworzyć główny lokalny
podgląd strony; nie pozostawić wyłącznie kopii roboczej stagingu.

`docs/WDROZENIE_LODZI_LCJ.md` ma zapisać: faktyczne źródła i trasy,
porównanie nowych hubów z baseline, uzasadnione wykluczenia/pending, okno,
run/hash/cache/NBP, pokrycie, wyniki ośmiu, testy, odbiór wizualny i backup.
Nie utożsamiać świeżej bazy z gwarancją ceny w chwili późniejszego zakupu.

Rollback ma odtworzyć spójny **kod + rejestr/allowlisty/rozkłady/opłaty +
20 plików poprzedniej bazy**. Stare feedy siedmiu nie certyfikują nowej
konfiguracji ośmiu. Nie resetować szeroko repo ani usuwać cudzych zmian.

## 14. Publikacja i przyszłe GitHub Actions

Publikować dopiero po osobnym poleceniu dotyczącym LCJ. Przedtem sprawdzić
status, diff i aktualny remote. Jawnie stage'ować właściwe pliki: kod,
konfigurację, testy, dokumentację, dziesięć feedów i dziesięć sidecarów.
Nie wysyłać roboczych cache, raw response, backupów lub tokenów z `tmp/`.
Bez force push. Po push potwierdzić commit zdalny i oddzielnie status
faktycznie wdrożonej strony; sam sukces Git nie jest dowodem wdrożenia hostingu.

Nie dodawać workflow przy okazji LCJ. Późniejsze Actions wymaga osobnego
zlecenia i powinno: instalować `requirements-flight-collector.txt`, uruchamiać
testy, ustalać dzień kanaryjski i jeden NBP, wykonywać dziesięć kolektorów
sekwencyjnie w jednym jobie z nowym runem/cache, zachowywać logi/raporty,
publikować tylko kompletny zwalidowany zestaw. Osobne joby nie współdzielą
procesowego semafora Google. Discovery pozostaje osobnym procesem, nie
częścią rutynowego odświeżania cen. Koszt i czas mierzyć dla ośmiu, nie
ograniczać okna lub list tras dla skrócenia joba.

## 15. Końcowa checklista dla wykonawcy LCJ

- [x] Zgoda na wdrożenie, aktualne instrukcje i odtwarzalny baseline siódemki.
- [x] Dokładna ósemka z LCJ/Europe/Warsaw oraz dziewięć zgodnych scope.
- [x] GDN/5B/KRK zachowane; LCJ i pozostałe endpointy nie dostały nowych ról transferowych.
- [x] Pełne siatki Ryanair/Wizz: przecięcie przed filtrem starych hubów, także zupełnie nowe kierunki.
- [x] Osobne audyty 1A–1F i 5A/5B; brak kopiowania siatki POZ/WRO.
- [x] Raport klasyfikuje stare, nowe dla wariantu i globalnie nowe huby oraz nowe TFN/TFS.
- [x] Awarie i częściowy Binter jawne; żadne `not_checked` nie udaje braku trasy.
- [x] Każda zaakceptowana para ma dowód i przechodzi aż do planu zapytań.
- [x] Przejrzano nowe huby i TFN/TFS: dla LCJ nie było nowych rekordów 1A–1F ani portów Teneryfy do dodania; ograniczenie helpera i źródeł jawne.
- [x] Generator idempotentny dla LCJ, bez duplikacji kodów i fikcyjnej notatki źródłowej.
- [x] Wymagane Wizz obu odcinków/kierunków sprawdzone: cztery nieaktywne rynki LCJ, bez nowych danych technicznych; stare rozkłady/override bez zmian.
- [x] Uprawnienia starej siódemki, WRO–LPA i POZ–LTN zachowane.
- [x] Macierz 2 ma 64 kombinacje i 1984 pozycje dla 31 dat, także poprawnie puste LCJ.
- [x] Pozostałe plany obejmują pełne niezależne kalendarze wszystkich zapisanych odcinków.
- [x] FR/RK i ceny indywidualne; Air Europa Google; Binter/Canaryfly końcowe imports RC/DC.
- [x] Ważne kierunkowe opłaty, jeden NBP, Google max 2 łącznie, nowy cache per run.
- [x] Testy LCJ i stare GDN/WRO/POZ, w tym naprawiona zależność POZ od `direct[:-1]`.
- [x] Dziesięć nowych feedów i sidecary: jeden run, komplet, zero braków/nadmiarów, bieżąca konfiguracja ośmiu.
- [x] Testy logiki UI na nowych feedach: oba kierunki LCJ, rabaty/sortowania, daty, kalendarz/wykres, X/reset/direct/+1/share/zakup.
- [x] Odbiór wizualny i natywnego schowka jawnie pozostawiony otwarty: lokalne sterowanie przeglądarką wyłączone w Work.
- [ ] Rzeczywisty odbiór wizualny szerokiego/wąskiego ekranu, płynności i natywnego schowka przez użytkownika; test DOM/HTTP go nie zastępuje.
- [x] Po lokalnej promocji 20 plików zgodne ze stagingiem, publiczna walidacja/18 JS/HTTP, backup i raport.
- [x] Pierwszy odbiór bez commita i publikacji; osobna zgoda na push LCJ uzyskana 23.10.2026. Nie dodano Actions.

## 16. Co faktycznie zrobiono podczas przygotowania planu

- Odczytano aktualne instrukcje, plan POZ, raporty WRO/POZ, rejestr i scope
  dziewięciu allowlist, planner/runner, helpery audytu, konfiguracji i Wizz,
  miejsca kolektorów, testów oraz UI związane z rozszerzaniem endpointów.
- Potwierdzono HEAD, brak wcześniejszych zmian roboczych, siedem endpointów,
  brak LCJ w wynikach i technicznych trasach Wizz; sprawdzono liczby i pełną
  zgodność dziesięciu obecnych feedów/sidecarów przez `validate_batch`.
- Ponownie uruchomiono **182 testy Python — OK** oraz **16 testów JS — OK**.
  To testy baseline siedmiu, nie dowód wdrożenia lub żywej siatki LCJ.
- Zapisano ten plan i odnośnik w README. Nie zmieniono rejestru, allowlist,
  kolektorów, aplikacji, opłat ani plików wynikowych. Nie uruchamiano live
  discovery LCJ, nowych zapytań cenowych, repricingu ani promocji.
- Nie wykonano commita/push ani zmian GitHub Actions. Realizacja wymaga
  kolejnego polecenia użytkownika i ponownej kontroli bieżącego stanu.
