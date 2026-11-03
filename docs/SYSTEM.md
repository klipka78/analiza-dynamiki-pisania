# Dokumentacja systemu — analiza dynamiki pisania

**Domena produkcyjna:** https://pismo.iit.sggw.pl  
**Repozytorium:** https://github.com/klipka78/analiza-dynamiki-pisania

---

## 1. Cel systemu

System zbiera **dynamikę wprowadzania tekstu z klawiatury** (keystroke dynamics), a nie wygląd liter.  
Na podstawie mikroczasów naciskania i zwalniania klawiszy, odstępów między znakami oraz wzorców poprawek bada się, czy da się **rozpoznać autora** (uczestnika) wprowadzanego tekstu.

Typowy przebieg badania:

1. Uczestnik dostaje identyfikator (np. `P017`).
2. Przepisuje jeden z tekstów kontrolnych (A / B / C) naturalnym tempem.
3. Przeglądarka rejestruje każde `keydown` / `keyup` z czasem względnym.
4. Sesja trafia do bazy; badacz eksportuje CSV i buduje model rozpoznawania.

Dodatkowo w repozytorium jest wariant offline: **makro Microsoft Word** (`word-macro/`) z tym samym pomysłem pomiaru.

---

## 2. Co system robi (funkcje)

| Obszar | Funkcja |
|--------|---------|
| Sesja uczestnika (`/`) | Start/Stop rejestracji, teksty A/B/C, wysłanie sesji |
| Panel badacza (`/admin`) | Lista sesji, eksport CSV (sesja / wszystkie), token `ADMIN_TOKEN` |
| API | Zapis sesji, health, zadania, eksport |
| Makro Word | Rejestracja w UserForm + lokalny CSV (porównanie środowisk) |

**Nie jest to keylogger ogólnego użytku** — rejestracja działa tylko w polu zadania, na tekstach kontrolnych, za zgodą uczestnika badania.

---

## 3. Architektura

```text
[Uczestnik / przeglądarka]
        │  HTTPS
        ▼
[Reverse proxy SGGW] ──► [Apache :80]
                              │  ProxyPass
                              ▼
                     [Docker: nginx web :8080]
                         │            │
                    pliki SPA    /api/* ──► [Docker: FastAPI :8000]
                                                  │
                                                  ▼
                                         [wolumen SQLite]
```

| Warstwa | Technologia | Rola |
|---------|-------------|------|
| Frontend | React 18, TypeScript, Vite | UI sesji i panelu |
| Serwowanie SPA | nginx (kontener `web`) | Pliki statyczne + proxy `/api` |
| Backend | FastAPI, Uvicorn, Pydantic, SQLAlchemy 2 | API REST, walidacja, ORM |
| Baza | SQLite (plik w wolumenie Dockera) | Sesje + zdarzenia klawiszy |
| Orkiestracja | Docker Compose | `api` + `web` |
| Edge | Apache 2 + ProxyPass | Domena `pismo.iit.sggw.pl` → `:8080` |
| Offline | VBA / Word UserForm | Alternatywne zbieranie CSV |

---

## 4. Gdzie są składowane dane

### 4.1. Lokalizacja na serwerze (Docker)

Baza to **SQLite** w nazwanym wolumenie Dockera:

| Element | Wartość |
|---------|---------|
| Zmienna | `DATABASE_URL=sqlite:////data/keystroke.db` |
| Ścieżka w kontenerze `api` | `/data/keystroke.db` |
| Wolumen Compose | `pismo_keystroke_data` |
| Host (typowo) | `/var/lib/docker/volumes/pismo_keystroke_data/_data/keystroke.db` |

Podgląd:

```bash
docker compose exec api ls -la /data
docker volume inspect pismo_keystroke_data
```

Eksport bez wchodzenia w plik DB — panel `/admin` lub:

- `GET /api/sessions/{uid}/export.csv`
- `GET /api/export/all.csv`  
(header: `X-Admin-Token`)

### 4.2. Tabele

**`sessions`** — jedna próba przepisania tekstu  

- `session_uid`, `participant_id`, `task_id` (A/B/C)  
- `reference_text`, `typed_text`  
- `user_agent`, `language`, `event_count`, `created_at`

**`events`** — pojedyncze zdarzenia klawiszy  

- `seq`, `elapsed_ms` (od Start), `event_type` (`down`/`up`)  
- `code`, `key`, `key_code`, `shift`, `ctrl`, `alt`

### 4.3. Format CSV (do analizy)

```csv
seq,elapsed_ms,event_type,code,key,key_code,shift,ctrl,alt
1,12.450,down,KeyT,t,84,0,0,0
2,95.120,up,KeyT,t,84,0,0,0
...
```

Etykieta autora = pole **`participant_id`** w sesji (lub kolumna w eksporcie zbiorczym).

---

## 5. Czy warto przejść na PostgreSQL?

**Na etapie pracy dyplomowej / pilotażu: SQLite wystarczy.**

| Kryterium | SQLite (teraz) | PostgreSQL |
|-----------|----------------|------------|
| Liczba uczestników (dziesiątki–niskie setki) | OK | OK |
| Równoległe zapisy | Ograniczone | Lepsze |
| Backup | Skopiować plik / wolumen | `pg_dump` |
| Złożone zapytania analityczne | Wystarczające | Wygodniejsze |
| Operacja / utrzymanie | Minimalne | Więcej (kontener, hasła, migracje) |

**Kiedy warto Postgres:**

- wielu uczestników pisze **jednocześnie**,
- baza urośnie do milionów eventów i wolne będą zapytania/eksporty,
- chcesz osobny serwer analityczny / BI podłączony na stałe.

Migracja jest prosta architektonicznie (SQLAlchemy już jest): dodać usługę `db` w Compose i zmienić `DATABASE_URL`.  
**Nie jest to konieczne, żeby zacząć zbierać próby i trenować modele.**

---

## 6. Jak analizować dane i rozpoznawać użytkownika

### 6.1. Protokół zbierania (rekomendacja badawcza)

| Parametr | Sugestia startowa |
|----------|-------------------|
| Liczba osób | ≥ 10–20 (im więcej, tym lepsza ocena) |
| Sesje na osobę | ≥ 5–10 (różne dni / warunki) |
| Teksty | A, B, C — te same dla wszystkich |
| Etykieta | stałe `participant_id` (P001, P002…) |
| Instrukcja | naturalne tempo, poprawki dozwolone |

Podział: część sesji → **trening**, część → **test** (osoba nie może „wyciec” tylko jedną sesją w obie strony — trzymaj split po sesjach).

### 6.2. Cechy (feature engineering) z eventów

Z par `down`/`up` i kolejnych `down`:

1. **Hold time (dwell)** — czas przytrzymania klawisza: `up.t − down.t` (per `code`).
2. **Flight time / digraph latency** — odstęp między kolejnymi naciśnięciami (np. `T→E`).
3. **Trigraph** — latencje dla trójek znaków (opcjonalnie).
4. **Tempo** — znaki/min (WPM) na sesję.
5. **Poprawki** — udział `Backspace` / `Delete`.
6. **Statystyki** — średnia, mediana, odchylenie, percentyle hold/flight (globalnie i dla najczęstszych digrafów).
7. **Wektor stałej długości** — np. średnie hold dla zbioru klawiszy + średnie flight dla top-N digrafów + WPM + % Backspace.

Każda **sesja** → jeden wektor cech + etykieta `participant_id`.

### 6.3. Modele (od prostych do trudniejszych)

| Poziom | Metoda | Uwagi |
|--------|--------|------|
| Baseline | k-NN / Distance (manhattan na wektorach) | Klasyczny w literaturze KD |
| Klasyczny ML | Random Forest, SVM (RBF), Logistic Regression | Dobry start do pracy |
| Zaawansowane | LSTM / Transformer na sekwencji hold/flight | Wymaga więcej danych |

Metryki: **accuracy**, **balanced accuracy**, macierz pomyłek, EER (jeśli scenariusz weryfikacji 1:1).

Scenariusze:

- **Identyfikacja (1:N)** — „który to uczestnik?” (klasyfikacja wieloklasowa).
- **Weryfikacja (1:1)** — „czy to nadal P017?” (binary / distance threshold).

### 6.4. Przykładowy pipeline analizy (offline)

```text
Eksport CSV (admin)
    → pandas: sesje + eventy
    → wyliczenie hold / digraph
    → macierz cech X, etykiety y
    → train/test split (po session_uid)
    → sklearn (RF/SVM)
    → raport: accuracy, confusion matrix
```

Szkic w Pythonie (lokalnie / notebook):

```python
# 1) wczytaj all_events.csv + zmapuj session → participant_id
# 2) dla każdej sesji policz wektor cech
# 3) clf = RandomForestClassifier(...)
# 4) cross_val_score / test set
```

Narzędzia: **Python, pandas, scikit-learn, matplotlib/seaborn**; opcjonalnie Jupyter na stacji badacza (nie musi być na serwerze WWW).

### 6.5. Ograniczenia i szum

- inna klawiatura / laptop vs zewnętrzna,
- układ PL vs EN, zmęczenie, pośpiech,
- mała liczba sesji → przeuczenie,
- ten sam tekst ułatwia porównanie, ale wyniki nie przenoszą się automatycznie na dowolny tekst swobodny.

W pracy dyplomowej warto opisać te czynniki i trzymać warunki możliwie stałe.

---

## 7. Endpointy API (skrót)

| Metoda | Ścieżka | Auth | Opis |
|--------|---------|------|------|
| GET | `/api/health` | — | Status |
| GET | `/api/tasks` | — | Teksty A/B/C |
| POST | `/api/sessions` | — | Zapis sesji + eventów |
| GET | `/api/sessions` | `X-Admin-Token` | Lista |
| GET | `/api/sessions/{uid}/export.csv` | token | CSV sesji |
| GET | `/api/export/all.csv` | token | Wszystkie eventy |

---

## 8. Operacje na produkcji

```bash
cd /home/a304500/public_html/pismo   # lub właściwa ścieżka usera

# status
docker compose ps
curl -fsS http://127.0.0.1:8080/api/health

# po zmianie .env (np. ADMIN_TOKEN)
docker compose up -d --force-recreate

# aktualizacja kodu
git pull
docker compose up -d --build

# backup bazy
docker run --rm -v pismo_keystroke_data:/data -v "$PWD":/backup alpine \
  cp /data/keystroke.db /backup/keystroke-$(date +%F).db
```

---

## 9. Bezpieczeństwo i etyka

- Zbierane są czasy i kody klawiszy w **kontrolowanym zadaniu**, nie treść haseł z innych stron.
- `participant_id` powinien być anonimowy (kod, nie nazwisko w ID).
- `ADMIN_TOKEN` trzymaj wyłącznie w `.env` (nie w git).
- API admina tylko z tokenem; kontener nasłuchuje na `127.0.0.1:8080`.
- Uczestników informuj o celu badania i zakresie danych (RODO / zgoda).

---

## 10. Struktura repozytorium

```text
backend/          FastAPI + SQLAlchemy
frontend/         React + Vite
deploy/           Apache vhost, instrukcja serwera
word-macro/       VBA / Word
docs/SYSTEM.md    ta dokumentacja
docker-compose.yml
.env.example
```

---

## 11. Podsumowanie

| Pytanie | Odpowiedź |
|---------|-----------|
| Gdzie dane? | SQLite w wolumenie Dockera `pismo_keystroke_data` (`/data/keystroke.db`) |
| Postgres już teraz? | Nie wymagany; SQLite OK do zbierania i analizy offline |
| Jak rozpoznać użytkownika? | Wiele sesji na ID → cechy hold/digraph → klasyfikator (RF/SVM/k-NN) |
| Skąd brać dane do ML? | Panel `/admin` → eksport CSV |

Kolejny sensowny krok rozwojowy: skrypt `analysis/` (notebook + `requirements-ml.txt`) liczący cechy i baseline accuracy — na żądanie można go dodać do repozytorium.
