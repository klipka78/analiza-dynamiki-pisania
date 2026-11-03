# Analiza dynamiki pisania (keystroke dynamics)

Aplikacja WEB do rejestracji dynamiki klawiatury (`keydown`/`keyup`) + makro Word (`word-macro/`).

**Domena:** `pismo.iit.sggw.pl`  
**Repo:** https://github.com/klipka78/analiza-dynamiki-pisania

## Uruchomienie na serwerze (Docker) — zalecane

Pełna instrukcja: [`deploy/SERVER.md`](deploy/SERVER.md)

```bash
cd /home/a304500/public_html
git clone https://github.com/klipka78/analiza-dynamiki-pisania.git pismo
cd pismo
cp .env.example .env
nano .env                    # ustaw ADMIN_TOKEN
docker compose up -d --build
```

Aplikacja nasłuchuje na `127.0.0.1:8080`. Apache proxuje domenę:

```bash
sudo cp deploy/apache-docker-vhost.conf /etc/apache2/sites-available/pismo.iit.sggw.pl.conf
sudo a2enmod proxy proxy_http headers remoteip
sudo a2ensite pismo.iit.sggw.pl.conf
sudo systemctl reload apache2
```

- Uczestnicy: https://pismo.iit.sggw.pl/
- Badacz: https://pismo.iit.sggw.pl/admin (`ADMIN_TOKEN` z `.env`)
- Health: https://pismo.iit.sggw.pl/api/health

## Stack

| Warstwa | Technologia |
|---------|-------------|
| Frontend | React + Vite → nginx |
| Backend | FastAPI + SQLite |
| Deploy | Docker Compose |

## `.env` (ważne)

| Zmienna | Opis |
|---------|------|
| `DOMAIN` | `pismo.iit.sggw.pl` |
| `PUBLIC_URL` | `https://pismo.iit.sggw.pl` |
| `ADMIN_TOKEN` | hasło panelu badacza |
| `HOST_PORT` | `8080` (Apache → ten port) |
| `HOST_BIND` | `127.0.0.1` |

## Lokalnie (dev)

```bash
docker compose up -d --build
# albo osobno: backend uvicorn + frontend npm run dev
```

## Dokumentacja systemu

Pełny opis (cel, technologie, składowanie danych, SQLite vs PostgreSQL, analiza ML / rozpoznawanie autora):  
**[`docs/SYSTEM.md`](docs/SYSTEM.md)**

## Makro Word

Folder `word-macro/` — zobacz `word-macro/README.md`.
