# ResiFly — pięć kroków zbierania danych o lotach

To jest kanoniczna, trwała instrukcja cotygodniowego wyszukiwania. Nie należy
dodawać innych rodzajów wyszukiwania ani pomijać żadnego z pięciu kroków bez
wyraźnej decyzji użytkownika.

## Harmonogram

- Uruchomienie: każdy wtorek o 09:00 czasu Wysp Kanaryjskich.
- Każde uruchomienie zaczyna się od zera i pobiera aktualne rozkłady oraz ceny.
- Nie wolno używać cen z poprzedniego uruchomienia.

## Wspólne zasady dla wszystkich kroków

- Okno wyszukiwania: od dnia uruchomienia do 30 dni naprzód.
- Polskie lotniska: Warszawa Chopina (WAW), Warszawa Modlin (WMI), Kraków
  (KRK) i Katowice (KTW).
- Teneryfa: Tenerife Sur (TFS) lub Tenerife Norte (TFN).
- Kierunki `Polska → Teneryfa` i `Teneryfa → Polska` analizować i pokazywać
  oddzielnie. Nie łączyć ich w podróż w obie strony i nie dobierać długości
  pobytu.
- Dopuszczać lot bezpośredni albo maksymalnie jedną przesiadkę, zgodnie z
  zasadami danego kroku.
- Przy przesiadce wymagać od 2 do 24 godzin między planowanym przylotem
  pierwszego odcinka a odlotem drugiego. Odcinki muszą być chronologicznie
  wykonalne.
- Nie odrzucać połączeń ze względu na cenę. Kolektory zapisują wszystkie wyniki
  spełniające zasady tras, dat, przewoźników i przesiadek, a maksymalną cenę
  wybiera użytkownik dopiero na stronie.
- Bagaż nie ma znaczenia — używać najtańszej dostępnej taryfy.
- Ceny walutowe przeliczać na PLN według aktualnego kursu NBP z dnia
  uruchomienia i podawać zastosowany kurs.
- Jeśli odcinki są kupowane osobno, oznaczać je jako
  `self-transfer / osobne bilety`.
- Dla każdego wyniku podawać:
  - datę i lokalną godzinę każdego odcinka,
  - pełną trasę,
  - lotnisko przesiadkowe,
  - przewoźnika każdego odcinka,
  - czas przesiadki,
  - zwykłą cenę odcinka z/do TFS lub TFN,
  - cenę tego odcinka po pomnożeniu przez 25%,
  - cenę pozostałego odcinka,
  - cenę całkowitą w PLN.
- Jeśli krok nie zwróci wyników, zapisać informację, co sprawdzono i że nie
  znaleziono połączeń spełniających warunki.

## Krok 1 — przewoźnik ze zniżką rezydencką + Ryanair lub Wizz Air

Krok 1 ma dwa niezależne warianty. Oba są częścią tego samego kroku, więc
cała procedura nadal zawiera dokładnie pięć głównych kroków.

### Krok 1A — Binter + Ryanair lub Wizz Air

- Używać wyłącznie lotnisk z kanonicznej listy
  `data/binter-transfer-airports.json`. Aktualnie są to: Fuerteventura (FUE),
  Gran Canaria (LPA), Madryt (MAD), Palma de Mallorca (PMI), Sewilla (SVQ) i
  Walencja (VLC).
- Podczas cotygodniowego uruchomienia nie wyszukiwać ponownie możliwych lotnisk
  przesiadkowych, nie rozszerzać listy i nie usuwać z niej pozycji. Sprawdzać
  tylko bieżące rozkłady oraz ceny dla pozycji zapisanych w pliku.
- Listę zmieniać wyłącznie na wyraźne polecenie użytkownika. Lotnisko obecne na
  liście może nie mieć połączenia w danym 30-dniowym oknie, np. z powodu
  sezonowości.
- Kod lotniska, jego strefę czasową, uprawnienie do zniżki na odcinku Bintera
  oraz zweryfikowane dane tras Wizz Air przechowywać w
  `data/binter-transfer-airports.json`. Dodanie lotniska nie może wymagać
  dopisywania jego danych bezpośrednio w kodzie kolektora.
- Nie sprawdzać lotnisk zapisanych w `excluded_airports`, w tym Funchal (FNC)
  na Maderze, ponieważ na połączenia z Maderą nie obowiązuje kanaryjska zniżka
  rezydencka 75%.
- Dla każdego lotniska z listy sprawdzić oba kierunki:
  1. WAW/WMI/KRK/KTW → lotnisko przesiadkowe linią Ryanair albo Wizz Air →
     TFS/TFN linią Binter.
  2. TFS/TFN → lotnisko przesiadkowe linią Binter → WAW/WMI/KRK/KTW linią
     Ryanair albo Wizz Air.
- Zwykłą cenę wyłącznie odcinka Bintera pomnożyć przez 25%. Drugi odcinek
  policzyć w pełnej cenie.
- W wynikach kroku umieścić krótką listę użytych lotnisk przesiadkowych oraz
  wszystkie znalezione połączenia.

### Krok 1B — Iberia/Iberia Express + Ryanair lub Wizz Air

- Używać wyłącznie lotnisk z kanonicznej listy
  `data/iberia-transfer-airports.json`. Po sprawdzeniu siatki Iberii z TFN i
  TFS jedynym kwalifikującym się lotniskiem jest Madryt (MAD).
- Nie dodawać tras bez kanaryjskiej zniżki rezydenckiej. Cotygodniowy kolektor
  nie odkrywa ponownie lotnisk i nie modyfikuje listy.
- Sprawdzić oba kierunki oddzielnie:
  1. WAW/WMI/KRK/KTW → MAD linią Ryanair albo Wizz Air → TFS/TFN linią
     Iberia lub Iberia Express.
  2. TFS/TFN → MAD linią Iberia lub Iberia Express → WAW/WMI/KRK/KTW linią
     Ryanair albo Wizz Air.
- Pobierać regularną cenę Iberii/Iberii Express w PLN z Google Flights zwykłym
  zapytaniem HTTP, bez uruchamiania prawdziwej przeglądarki. Cenę rezydenta
  zapisać jako orientacyjną wartość równą 25% tej ceny regularnej i wyraźnie
  oznaczyć sposób wyliczenia w odcinku.
- Jeśli Google Flights nie zwróci użytecznych danych Iberii, przerwać wykonanie
  bez nadpisywania poprzedniego pliku wynikowego. Nie tworzyć cen zastępczych.
- Odcinek Wizz Air lub Ryanair liczyć w pełnej cenie. Nie filtrować wyników
  cenowo w kolektorze.
- Generować wariant poleceniem `scripts/collect_step1b.py`, a publiczny wynik
  zapisywać w `data/step1b-results.json`.
- Każdy odcinek Iberii otrzymuje trwały `booking_url` z trasą, datą, liczbą
  pasażerów i kodem rezydenta, bez cookies ani tokenów sesji.

## Krok 2 — loty bezpośrednie

- Sprawdzić wyłącznie bezpośrednie loty Ryanair i Wizz Air między WAW, WMI,
  KRK lub KTW a TFS lub TFN.
- Sprawdzić oba kierunki oddzielnie.
- Używać pełnej aktualnej ceny lotu; nie stosować mnożnika 25%.
- Zapisać wszystkie znalezione loty bezpośrednie niezależnie od ceny.

## Krok 3 — Ryanair + Ryanair

- Używać wyłącznie lotnisk i odpowiadających im polskich lotnisk zapisanych w
  kanonicznej liście `data/ryanair-transfer-airports.json`.
- Podczas cotygodniowego uruchomienia nie odkrywać ponownie możliwych lotnisk
  przesiadkowych, nie rozszerzać listy i nie usuwać z niej pozycji. Sprawdzać
  tylko bieżące rozkłady oraz ceny dla kombinacji zapisanych w pliku.
- Listę zmieniać wyłącznie na wyraźne polecenie użytkownika. Lotnisko obecne na
  liście może nie mieć połączenia w danym 30-dniowym oknie, np. z powodu
  sezonowości lub czasowego zawieszenia trasy.
- Strefy czasowe lotnisk przesiadkowych przechowywać w `airport_timezones` w
  tym samym pliku listy, a nie w kodzie kolektora.
- Sprawdzić wszystkie chronologicznie wykonalne połączenia przez każde lotnisko
  z listy, w obu kierunkach.
- Uprawnienie do zniżki odczytywać z pola
  `resident_discount_on_tenerife_leg` w pliku listy. Mnożnik `0.25` stosować
  wyłącznie do odcinka TFS/TFN ↔ przesiadka, gdy lotnisko przesiadkowe znajduje
  się w `eligible_transfer_airports`. Dla pozostałych lotnisk stosować pełną
  cenę (`1.0`). Odcinek między Polską a lotniskiem przesiadkowym zawsze liczyć
  w pełnej cenie.
- W wynikach kroku najpierw podać aktualną listę lotnisk przesiadkowych i
  odpowiadające im polskie lotniska, a następnie wszystkie połączenia.

## Krok 4 — Wizz Air + Wizz Air

- Używać wyłącznie lotnisk i odpowiadających im polskich lotnisk zapisanych w
  kanonicznej liście `data/wizzair-transfer-airports.json`.
- Podczas cotygodniowego uruchomienia nie odkrywać ponownie możliwych lotnisk
  przesiadkowych, nie rozszerzać listy i nie usuwać z niej pozycji. Sprawdzać
  tylko bieżące rozkłady oraz ceny dla kombinacji zapisanych w pliku.
- Listę zmieniać wyłącznie na wyraźne polecenie użytkownika. Lotnisko obecne na
  liście może nie mieć połączenia w danym 30-dniowym oknie, np. z powodu
  sezonowości, przyszłej daty uruchomienia albo czasowego zawieszenia trasy.
- Strefy czasowe lotnisk przechowywać w `airport_timezones` w tym samym pliku
  listy. Zweryfikowane numery lotów, czasy blokowe i wyjątki godzinowe Wizz Air
  przechowywać w `data/wizz-route-schedules.json`, nie w kodzie kolektora.
- Sprawdzić wszystkie chronologicznie wykonalne połączenia przez każde lotnisko
  z listy, w obu kierunkach.
- Uprawnienie do zniżki odczytywać z pola
  `resident_discount_on_tenerife_leg` w pliku listy. Mnożnik `0.25` stosować
  wyłącznie do odcinka TFS/TFN ↔ przesiadka, gdy lotnisko przesiadkowe znajduje
  się w `eligible_transfer_airports`. Dla pozostałych lotnisk stosować pełną
  cenę (`1.0`). Odcinek między Polską a lotniskiem przesiadkowym zawsze liczyć
  w pełnej cenie.
- W wynikach kroku najpierw podać aktualną listę lotnisk przesiadkowych i
  odpowiadające im polskie lotniska, a następnie wszystkie połączenia.

## Krok 5 — połączenia mieszane Ryanair × Wizz Air

- Używać wyłącznie kombinacji zapisanych w kanonicznej liście
  `data/mixed-transfer-airports.json`.
- Podczas cotygodniowego uruchomienia nie odkrywać ponownie możliwych lotnisk
  przesiadkowych, nie rozszerzać listy i nie usuwać z niej pozycji. Sprawdzać
  tylko bieżące rozkłady oraz ceny dla kombinacji zapisanych w pliku.
- Wariant A: Ryanair obsługuje odcinek TFS/TFN ↔ przesiadka, a Wizz Air odcinek
  przesiadka ↔ WAW/WMI/KRK/KTW. Sprawdzić oba kierunki oddzielnie.
- Wariant B: Wizz Air obsługuje odcinek TFS/TFN ↔ przesiadka, a Ryanair odcinek
  przesiadka ↔ WAW/WMI/KRK/KTW. Sprawdzić oba kierunki oddzielnie.
- Uprawnienie do zniżki odczytywać osobno dla właściwego wariantu z pola
  `resident_discount_on_tenerife_leg`. Mnożnik `0.25` stosować wyłącznie do
  odcinka TFS/TFN ↔ przesiadka, gdy lotnisko znajduje się w odpowiednim
  `eligible_transfer_airports`. Dla pozostałych lotnisk stosować pełną cenę
  (`1.0`). Odcinek między Polską a lotniskiem przesiadkowym zawsze liczyć w
  pełnej cenie.
- Listę zmieniać wyłącznie na wyraźne polecenie użytkownika. Obecność na liście
  nie gwarantuje połączenia w danym 30-dniowym oknie.
- Strefy czasowe lotnisk przechowywać w `airport_timezones` w tym samym pliku
  listy. Odcinki Wizz Air korzystają ze zweryfikowanych danych zapisanych w
  `data/wizz-route-schedules.json`, dzięki czemu nowa trasa nie wymaga zmiany
  kodu kolektora.
- W wynikach kroku najpierw podać listę lotnisk przesiadkowych dla obu
  wariantów, a następnie wszystkie połączenia.

## Zakończenie uruchomienia

Po ukończeniu pięciu kroków przygotować krótkie podsumowanie zawierające liczbę
wyników w każdym kroku.

## Osobny wykrywacz nowych tras

Cotygodniowe kolektory cen korzystają wyłącznie z zapisanych list i nie szukają
nowych lotnisk przesiadkowych. Do okresowej kontroli siatki kroku 1A oraz kroków
3–5 służy osobny skrypt:

```bash
python3 scripts/discover_transfer_routes.py
```

Domyślnie jest to bezpieczny podgląd zmian bez zapisu. Opcja `--apply` dopisuje
wyłącznie kompletne nowe pozycje do list kroków 1A, 3, 4 i 5; nigdy automatycznie
nie usuwa istniejących pozycji. Krok 2 nie ma listy przesiadek, ponieważ jego
kolektor zawsze sprawdza pełną macierz czterech polskich i dwóch teneryfskich
lotnisk.

Lista 1B jest aktualizowana osobno i może zawierać wyłącznie bezpośrednie trasy
Iberii/Iberii Express z TFN lub TFS, na których obowiązuje kanaryjska zniżka
rezydencka oraz istnieje dalszy odcinek Ryanair lub Wizz Air do Polski.

Jeżeli nowa możliwość wykorzystuje Wizz Air, przed aktywacją muszą istnieć
zweryfikowane numery lotów i czasy blokowe obu kierunków w rejestrze rozkładów.
Gdy ich brakuje, wykrywacz pokazuje tę pozycję jako oczekującą i jej nie zapisuje;
kompletne pozycje z pozostałych kroków nadal mogą zostać dopisane. Raport można
zapisać opcją `--report`, co pozwoli później podłączyć ten sam skrypt do GitHub
Actions bez przepisywania mechanizmu.

## Filtrowanie cen

Publiczne JSON-y nie mają limitu cenowego. Cena regularna, cena rezydencka i
Wizz Air Discount Club są zapisywane jako osobne wartości, jeśli dane źródłowe
je udostępniają. Użytkownik wybiera maksymalną cenę dopiero na stronie.
Wygenerowanych JSON-ów nie należy poprawiać ręcznie; trzeba zmienić kolektor i
ponownie wygenerować dane.

