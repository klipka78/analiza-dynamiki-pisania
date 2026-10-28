# Analiza dynamiki pisania (keystroke dynamics)

Aplikacja WEB do rejestracji i analizy charakteru wprowadzania tekstu na klawiaturze (mikroczasy `keydown`/`keyup`, digrafy, tempo).  
Zawiera też pakiet makra Word (`word-macro/`).

Domena docelowa (konfigurujesz w `.env`): **pismo.iit.sggw.pl**

## Stack

- **Frontend:** React + Vite (TypeScript)
- **Backend:** FastAPI + SQLAlchemy + SQLite
- **Deploy:** Docker Compose na Ubuntu (nginx → API)

## Szybki start lokalnie (Docker)

```bash
cp .env.example .env
# edytuj DOMAIN, PUBLIC_URL, ADMIN_TOKEN

docker compose up -d --build
```

Wejdź na `http://localhost` (lub port z `HOST_PORT`).

- Sesja uczestnika: `/`
- Panel badacza: `/admin` (token = `ADMIN_TOKEN`)

## Ubuntu (serwer)

```bash
sudo bash deploy/ubuntu-setup.sh
sudo mkdir -p /opt/pismo && cd /opt/pismo
git clone <URL-repo> .
cp .env.example .env
nano .env   # DOMAIN=pismo.iit.sggw.pl itd.
docker compose up -d --build
```

### DNS / reverse proxy

1. Ustaw rekord **A/AAAA** dla `pismo.iit.sggw.pl` na IP serwera.
2. Na hoście wystaw port `HOST_PORT` (domyślnie 80) albo postaw zewnętrzny nginx/Caddy z TLS:

Przykład Caddy (osobno na hoście):

```
pismo.iit.sggw.pl {
  reverse_proxy localhost:80
}
```

Albo certbot + nginx proxy na kontener `web`.

## API (skrót)

| Metoda | Ścieżka | Opis |
|--------|---------|------|
| GET | `/api/health` | status |
| GET | `/api/tasks` | teksty A/B/C |
| POST | `/api/sessions` | zapis sesji + eventów |
| GET | `/api/sessions` | lista (header `X-Admin-Token`) |
| GET | `/api/sessions/{uid}/export.csv` | CSV sesji |
| GET | `/api/export/all.csv` | wszystkie zdarzenia |

Format CSV jest zgodny koncepcyjnie z eksportem makra Word.

## Zmienne `.env`

| Zmienna | Przykład |
|---------|----------|
| `DOMAIN` | `pismo.iit.sggw.pl` |
| `PUBLIC_URL` | `https://pismo.iit.sggw.pl` |
| `ADMIN_TOKEN` | silne hasło |
| `HOST_PORT` | `80` |
| `DATABASE_URL` | `sqlite:////data/keystroke.db` |

## Dev bez Dockera

```bash
# terminal 1
cd backend
python -m venv .venv && source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
# DATABASE_URL=sqlite:///./keystroke.db
uvicorn app.main:app --reload --port 8000

# terminal 2
cd frontend
npm install
npm run dev
```

## Makro Word

Folder `word-macro/` — UserForm + eksport CSV. Instrukcja w `word-macro/README.md`.

## RODO / etyka badania

Nie zbieraj haseł ani treści wrażliwych. Uczestnicy dostają anonimowe ID.  
Teksty zadań są kontrolne (copy-task).
