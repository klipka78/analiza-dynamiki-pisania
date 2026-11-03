# Analiza — rozpoznawanie użytkownika

Skrypt buduje cechy z eksportu CSV systemu **pismo** i uczy klasyfikator (Random Forest / SVM / k-NN).

## 1. Pobierz dane z systemu

1. Wejdź na https://pismo.iit.sggw.pl/admin  
2. Podaj `ADMIN_TOKEN`  
3. **Eksport wszystkich zdarzeń** → zapisz jako `all_events.csv`

Albo:

```bash
curl -fsS -H "X-Admin-Token: TWOJ_TOKEN" \
  https://pismo.iit.sggw.pl/api/export/all.csv \
  -o all_events.csv
```

Wymagane kolumny: `session_uid, participant_id, task_id, seq, elapsed_ms, event_type, code, key, ...`

## 2. Instalacja

```bash
cd analysis
python -m venv .venv
# Windows: .venv\Scripts\activate
source .venv/bin/activate
pip install -r requirements.txt
```

## 3. Uruchomienie

```bash
# dane rzeczywiste
python recognize_user.py --csv all_events.csv --model all --out-dir results

# smoke test bez serwera
python recognize_user.py --demo --model all --out-dir results
```

Wyniki w `results/`:

- `confusion_rf.png` / `svm` / `knn` — macierz pomyłek  
- `metrics_*.json` — accuracy, F1  
- `report_*.txt` — classification report  
- `session_features.csv` — wektory cech per sesja  

## 4. Co liczy skrypt

| Cecha | Opis |
|-------|------|
| hold_* | średni czas przytrzymania klawisza |
| dig_* / flight_* | latencje digrafów (kolejne down) |
| wpm | tempo pisania |
| backspace_pct | udział Backspace |

Split **po sesjach** (`GroupShuffleSplit`) — ta sama sesja nie jest w train i test naraz.  
Etykieta = `participant_id`.

## 5. Zalecenia badawcze

- ≥ 5–10 sesji na osobę (teksty A/B/C)  
- stałe ID uczestnika  
- `--min-sessions-per-user 2` (domyślnie) — podnieś przy większych danych  
