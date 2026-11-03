# Analiza lokalna (PC z GPU)

Serwer **pismo** tylko zbiera dane. Trening i rozpoznawanie uruchamiasz **na swoim komputerze** (RTX / CUDA).

## Workflow

```text
[pismo.iit.sggw.pl]  →  all_events.csv  →  [Twój PC + GPU]
     zbieranie              eksport           analysis/recognize_user.py
```

### 1. Pobierz CSV z serwera

Panel: https://pismo.iit.sggw.pl/admin → **Eksport wszystkich zdarzeń**

albo:

```bash
curl -fsS -H "X-Admin-Token: TWOJ_TOKEN" \
  https://pismo.iit.sggw.pl/api/export/all.csv \
  -o all_events.csv
```

### 2. Środowisko na PC

```bash
cd analysis
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
```

Sprawdź GPU:

```bash
python -c "import torch; print(torch.__version__, torch.cuda.is_available(), torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU')"
```

U Ciebie powinno być: `True` + `NVIDIA GeForce RTX …`

### 3. Uruchomienie

```bash
# GPU — sieć MLP (PyTorch + CUDA)
python recognize_user.py --csv all_events.csv --model mlp --device cuda

# porównanie: sklearn (CPU) + MLP (GPU)
python recognize_user.py --csv all_events.csv --model all --device auto

# smoke test bez serwera
python recognize_user.py --demo --model mlp --device cuda
```

| Model | Gdzie liczy |
|-------|-------------|
| `rf`, `svm`, `knn` | CPU (scikit-learn) |
| `mlp` | **GPU** (PyTorch CUDA), fallback CPU |

Wyniki: `results/confusion_*.png`, `metrics_*.json`, `session_features.csv`

## Uwagi

- Przy małej liczbie sesji RF na CPU często wystarcza; GPU przyda się przy większym zbiorze / MLP / przyszłym LSTM na sekwencjach.
- Split zawsze **po sesjach** — ta sama sesja nie jest w train i test.
- Etykieta = `participant_id` z systemu.
