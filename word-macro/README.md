# Makro Word — rejestracja dynamiki pisania (UserForm + CSV)

Pakiet VBA do pracy o analizie charakteru pisma komputerowego.  
Uczestnik przepisuje tekst w formularzu; makro zapisuje `keydown` / `keyup` z czasem wysokiej rozdzielczości (`QueryPerformanceCounter`) do CSV.

## Pliki

| Plik | Opis |
|------|------|
| `modKeystroke.bas` | Bufor zdarzeń, timing, eksport CSV, teksty zadań |
| `frmKeystroke_Code.bas` | Kod formularza — **wklej do UserForm**, nie importuj jako moduł |
| `modStartup.bas` | Alias makra startowego |
| `frmKeystroke.frm` | Szkic formularza (bez `.frx` — buduj UI ręcznie) |

## Co zrobić z tymi plikami? (najkrótsza ścieżka)

1. Otwórz `test.docx` (instrukcja).
2. W Wordzie: **Zapisz jako → `test.docm`** (Dokument Word z obsługą makr).
3. Włącz zaufanie VBA:  
   **Plik → Opcje → Centrum zaufania → Ustawienia → Ustawienia makr**  
   zaznacz **Ufaj dostępowi do modelu obiektowego projektu VBA**.
4. `Alt+F11` → **Plik → Importuj plik** → `Installer.bas`.
5. `Alt+F8` → **RunInstaller** → Uruchom (wczyta resztę z folderu `word-macro`).
6. `Alt+F8` → **StartKeystrokeCapture** → Uruchom.

CSV trafia do: `Dokumenty\KeystrokeSessions\`

---

## Instalacja ręczna (ok. 10–15 min, bez Installer.bas)

### 1. Włącz makra i kartę Deweloper

1. Word → **Plik → Opcje → Centrum zaufania → Ustawienia Centrum zaufania → Ustawienia makr**
2. Wybierz: *Wyłącz makra z powiadomieniem* (lub włącz dla zaufanych dokumentów).
3. **Opcje → Dostosowywanie Wstążki** → zaznacz **Deweloper**.

### 2. Utwórz szablon makro

1. Nowy pusty dokument.
2. **Plik → Zapisz jako** → typ: **Szablon programu Word z obsługą makr (*.dotm)**  
   np. `KeystrokeCapture.dotm`
3. **Deweloper → Visual Basic** (lub `Alt+F11`).

### 3. Zaimportuj moduły

W oknie VBA, w projekcie szablonu:

1. **Plik → Importuj plik…** → wybierz `modKeystroke.bas`
2. Ponownie → `modStartup.bas`

### 4. Zbuduj UserForm `frmKeystroke`

1. VBA → **Wstaw → UserForm**
2. W oknie Properties ustaw:
   - `(Name)` = `frmKeystroke`
   - `Caption` = `Rejestracja dynamiki pisania`
   - `KeyPreview` = `True`  ← **konieczne**
   - szerokość ok. 480, wysokość ok. 360 (twips: ~9600 × 7200)

3. Dodaj kontrolki (Toolbox) z **dokładnie** tymi nazwami `(Name)`:

| Name | Typ | Właściwości |
|------|-----|-------------|
| `lblId` | Label | Caption: `ID uczestnika` |
| `txtParticipantId` | TextBox | |
| `lblTask` | Label | Caption: `Tekst zadania` |
| `cboTask` | ComboBox | Style: `2 - fmStyleDropDownList` |
| `lblRef` | Label | Caption: `Tekst do przepisania` |
| `txtReference` | TextBox | MultiLine=`True`, EnterKeyBehavior=`True`, ScrollBars=`2`, Locked=`True`, Height większy |
| `lblType` | Label | Caption: `Pole wpisywania` |
| `txtTyped` | TextBox | MultiLine=`True`, EnterKeyBehavior=`True`, ScrollBars=`2`, Height większy |
| `btnStart` | CommandButton | Caption: `Start` |
| `btnStop` | CommandButton | Caption: `Stop` |
| `btnExport` | CommandButton | Caption: `Eksport CSV` |
| `btnClear` | CommandButton | Caption: `Wyczyść` |
| `btnClose` | CommandButton | Caption: `Zamknij` |
| `lblStatus` | Label | Caption: `Status` |
| `lblEvents` | Label | Caption: `Zdarzenia: 0` |
| `lblFolder` | Label | Caption: `Folder CSV:` |

Propozycja układu (od góry):

```
[ID uczestnika: txtParticipantId]  [Tekst: cboTask]
[Tekst do przepisania — txtReference]
[Pole wpisywania — txtTyped]
[Start] [Stop] [Eksport CSV] [Wyczyść] [Zamknij]
[lblStatus]
[lblEvents]   [lblFolder]
```

### 5. Wklej kod formularza

1. Dwuklik na formularzu → otwórzy się okno kodu.
2. Usuń domyślną pustą treść.
3. Otwórz `frmKeystroke_Code.bas`, skopiuj wszystko **od `Option Explicit`** do końca.
4. Wklej do kodu `frmKeystroke`.

### 6. Zapisz i uruchom

1. Zapisz szablon (`Ctrl+S`).
2. W Wordzie: **Deweloper → Makra** → `StartKeystrokeCapture` → **Uruchom**.  
   Albo w VBA: ustaw kursor w `StartKeystrokeCapture` → `F5`.

Opcjonalnie: **Deweloper → Makra → StartKeystrokeCapture → Opcje** → skrót klawiszowy,  
albo dodaj przycisk na pasek Szybki dostęp.

## Przebieg sesji badawczej

1. Uczestnik wpisuje ID (np. `P017`).
2. Wybiera tekst A / B / C.
3. **Start** → przepisuje tekst w dolnym polu naturalnym tempem.
4. **Stop** → **Eksport CSV**.

Pliki trafiają do:

`%USERPROFILE%\Documents\KeystrokeSessions\`

Przykład:

- `20261028_150612_P017_events.csv`
- `20261028_150612_P017_meta.csv`

## Format CSV zdarzeń

```csv
seq,elapsed_ms,event_type,key_code,key_name,shift,ctrl,alt
1,12.450,down,84,T,0,0,0
2,95.120,up,84,T,0,0,0
3,180.300,down,69,E,0,0,0
...
```

- `elapsed_ms` — czas od Start (ms, separator `.`)
- `event_type` — `down` / `up`
- `key_name` — czytelna nazwa (`Space`, `Backspace`, `A`, …)

Plik `*_meta.csv`: ID uczestnika, ID zadania, tekst wzorcowy, wpisany tekst, liczba zdarzeń.

## Cechy do ML (później, z CSV)

Z par `down`/`up` tego samego `key_code`:

- **hold time** = `up.elapsed_ms - down.elapsed_ms`
- **digraph latency** = odstęp między kolejnymi `down`
- tempo (WPM), udział Backspace, wariancja rytmu

## Ograniczenia Word / VBA

- Zdarzenia łapane są na **UserForm** (`KeyPreview=True`), nie w treści dokumentu Word — to zamierzone i stabilniejsze.
- Rozdzielczość czasu zależy od `QueryPerformanceCounter` (zwykle ≤ 1 ms) — dużo lepsza niż `Timer` VBA (~15 ms).
- Układ klawiatury (PL/EN) wpływa na `key_code` znaków diakrytycznych — w meta warto notować layout (do uzupełnienia w WEB).
- Nie używaj tego do logowania haseł / danych wrażliwych.

## Szybki test poprawności

1. Start → wpisz `test` → Stop → Eksport.
2. W CSV powinny być pary down/up dla T,E,S,T.
3. Hold time litery ≈ 50–200 ms; odstępy między literami typowo 80–300 ms.

## Następny krok

Warstwa WEB (React + FastAPI) z tym samym schematem CSV/JSON — wtedy te same skrypty feature extraction zadziałają na danych z Worda i z przeglądarki.
