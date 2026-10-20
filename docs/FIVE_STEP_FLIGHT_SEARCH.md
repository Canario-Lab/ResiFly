# ResiFly — pięć kroków zbierania danych o lotach

To jest kanoniczna, trwała instrukcja cotygodniowego wyszukiwania. Nie należy
dodawać innych rodzajów wyszukiwania ani pomijać żadnego z pięciu kroków bez
wyraźnej decyzji użytkownika.

## Harmonogram

- Uruchomienie: każdy wtorek o 09:00 czasu Wysp Kanaryjskich.
- Każde uruchomienie zaczyna się od zera i pobiera aktualne rozkłady oraz ceny.
- Nie wolno używać cen z poprzedniego raportu.

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
- Do raportu kwalifikować wyłącznie połączenia kosztujące mniej niż 500 PLN za
  całą podróż w jedną stronę po zastosowaniu właściwego przeliczenia 25%.
  Wyników równych 500 PLN ani droższych nie pokazywać.
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
- Każdy krok zakończyć osobnym, czytelnym PDF-em zapisanym w folderze `Loty`
  na Biurku.
- Jeśli krok nie zwróci wyników, mimo to utworzyć PDF z informacją, co
  sprawdzono i że nie znaleziono połączeń spełniających warunki.

## Krok 1 — Binter + Ryanair lub Wizz Air

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
- W PDF-ie najpierw umieścić krótką listę użytych lotnisk
  przesiadkowych, a następnie wszystkie znalezione połączenia poniżej 500 PLN.

## Krok 2 — loty bezpośrednie

- Sprawdzić wyłącznie bezpośrednie loty Ryanair i Wizz Air między WAW, WMI,
  KRK lub KTW a TFS lub TFN.
- Sprawdzić oba kierunki oddzielnie.
- Używać pełnej aktualnej ceny lotu; nie stosować mnożnika 25%.
- Pokazać wyłącznie bezpośrednie loty poniżej 500 PLN.

## Krok 3 — Ryanair + Ryanair

- Na podstawie aktualnej siatki Ryanair ustalić europejskie lotniska, do
  których Ryanair lata bezpośrednio z TFS lub TFN i które mają również
  bezpośrednie połączenie Ryanair z co najmniej jednym z lotnisk WAW, WMI, KRK
  lub KTW.
- Sprawdzić wszystkie chronologicznie wykonalne połączenia przez każde takie
  lotnisko, w obu kierunkach.
- Zwykłą cenę odcinka Ryanair z/do TFS lub TFN pomnożyć przez 25%. Odcinek
  między Polską a lotniskiem przesiadkowym policzyć w pełnej cenie.
- W PDF-ie najpierw podać aktualną listę lotnisk przesiadkowych i odpowiadające
  im polskie lotniska, a następnie wszystkie połączenia poniżej 500 PLN.

## Krok 4 — Wizz Air + Wizz Air

- Na podstawie aktualnej siatki Wizz Air ustalić europejskie lotniska, do
  których Wizz Air lata bezpośrednio z TFS lub TFN i które mają również
  bezpośrednie połączenie Wizz Air z co najmniej jednym z lotnisk WAW, WMI,
  KRK lub KTW.
- Sprawdzić wszystkie chronologicznie wykonalne połączenia przez każde takie
  lotnisko, w obu kierunkach.
- Zwykłą cenę odcinka Wizz Air z/do TFS lub TFN pomnożyć przez 25%. Odcinek
  między Polską a lotniskiem przesiadkowym policzyć w pełnej cenie.
- W PDF-ie najpierw podać aktualną listę lotnisk przesiadkowych i odpowiadające
  im polskie lotniska, a następnie wszystkie połączenia poniżej 500 PLN.

## Krok 5 — połączenia mieszane Ryanair × Wizz Air

- Użyć aktualnych list lotnisk przesiadkowych wyznaczonych w krokach 3 i 4 tego
  samego uruchomienia.
- Wariant A: dla lotnisk, do których Ryanair lata z TFS/TFN, sprawdzić odcinek
  między tym lotniskiem a WAW/WMI/KRK/KTW linią Wizz Air. Połączyć Ryanair na
  odcinku Teneryfa–przesiadka z Wizz Air na odcinku przesiadka–Polska, w obu
  kierunkach.
- Wariant B: dla lotnisk, do których Wizz Air lata z TFS/TFN, sprawdzić odcinek
  między tym lotniskiem a WAW/WMI/KRK/KTW linią Ryanair. Połączyć Wizz Air na
  odcinku Teneryfa–przesiadka z Ryanair na odcinku przesiadka–Polska, w obu
  kierunkach.
- Zwykłą cenę odcinka z/do TFS lub TFN pomnożyć przez 25%, niezależnie od tego,
  czy obsługuje go Ryanair, czy Wizz Air. Odcinek między Polską a lotniskiem
  przesiadkowym policzyć w pełnej cenie.
- W PDF-ie najpierw podać listę lotnisk przesiadkowych dla obu wariantów, a
  następnie wszystkie połączenia poniżej 500 PLN.

## Zakończenie uruchomienia

Po ukończeniu pięciu kroków przygotować krótkie podsumowanie zawierające liczbę
wyników w każdym kroku oraz linki do pięciu utworzonych PDF-ów.

## Ważne rozróżnienie: raport a JSON strony

Próg 500 PLN jest zasadą kwalifikacji wyników do powyższych pięciu raportów.
Obecny testowy JSON strony także został zawężony do cen rezydenckich poniżej
500 PLN, dlatego nie pozwala stronie pokazać droższych połączeń. Jeżeli strona
ma umożliwiać podniesienie limitu ponad 500 PLN, kolektor powinien zapisywać
szerszy zestaw danych, a limit należy stosować dopiero w interfejsie lub podczas
tworzenia raportu. Wygenerowanych JSON-ów nie należy poprawiać ręcznie.

