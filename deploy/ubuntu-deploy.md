# Wdrożenie na Ubuntu (Apache) — pismo.iit.sggw.pl

Katalog aplikacji: `/home/a304500/public_html/pismo`

## 1. Pakiety systemowe (jako root / sudo)

```bash
sudo apt update
sudo apt install -y apache2 python3 python3-venv python3-pip git curl

# Node 20 (NodeSource) — do buildu frontendu
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs

sudo a2enmod proxy proxy_http headers remoteip
sudo systemctl reload apache2
```

Jeśli nie masz sudo do NodeSource — użyj **nvm** w userze `a304500` (patrz README) albo zbuduj `frontend/dist` lokalnie i wgraj na serwer.

## 2. Kod

```bash
cd /home/a304500/public_html
git clone https://github.com/klipka78/analiza-dynamiki-pisania.git pismo
cd pismo
cp .env.example .env
nano .env
```

Przykład `.env`:

```env
DOMAIN=pismo.iit.sggw.pl
PUBLIC_URL=https://pismo.iit.sggw.pl
ADMIN_TOKEN=zmien-na-silne-haslo
APP_ENV=production
HOST_PORT=80
DATABASE_URL=sqlite:////home/a304500/public_html/pismo/data/keystroke.db
```

```bash
mkdir -p /home/a304500/public_html/pismo/data
```

## 3. Frontend

```bash
cd /home/a304500/public_html/pismo/frontend
npm ci
npm run build
# powstaje: frontend/dist
```

## 4. Backend

```bash
cd /home/a304500/public_html/pismo/backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Test ręczny:

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000
# curl http://127.0.0.1:8000/api/health
# Ctrl+C
```

## 5. systemd (API zawsze włączone)

```bash
sudo cp /home/a304500/public_html/pismo/deploy/pismo-api.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now pismo-api
sudo systemctl status pismo-api
```

## 6. Apache vhost

```bash
sudo cp /home/a304500/public_html/pismo/deploy/apache-pismo.iit.sggw.pl.conf \
  /etc/apache2/sites-available/pismo.iit.sggw.pl.conf
sudo a2ensite pismo.iit.sggw.pl.conf
sudo apache2ctl configtest
sudo systemctl reload apache2
```

HTTPS: rekord DNS `pismo.iit.sggw.pl` → IP serwera + Wasz reverse proxy / certbot przed Apache.

## 7. Sprawdzenie

- https://pismo.iit.sggw.pl/
- https://pismo.iit.sggw.pl/api/health
- https://pismo.iit.sggw.pl/admin  (token z `.env`)

## Aktualizacja później

```bash
cd /home/a304500/public_html/pismo
git pull
cd frontend && npm ci && npm run build
cd ../backend && source .venv/bin/activate && pip install -r requirements.txt
sudo systemctl restart pismo-api
```
