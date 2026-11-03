# Uruchomienie na Ubuntu (Docker) — pismo.iit.sggw.pl

## Na serwerze (raz)

```bash
# Docker
sudo apt update
sudo apt install -y git curl ca-certificates
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker "$USER"
# wyloguj i zaloguj ponownie, albo:
newgrp docker

# Apache (jeśli macie vhost + reverse proxy HTTPS przed serwerem)
sudo apt install -y apache2
sudo a2enmod proxy proxy_http headers remoteip
```

## Pobranie i start

```bash
cd /home/a304500/public_html
git clone https://github.com/klipka78/analiza-dynamiki-pisania.git pismo
cd pismo

cp .env.example .env
nano .env
# ustaw ADMIN_TOKEN (resztę możesz zostawić)

docker compose up -d --build
docker compose ps
curl -fsS http://127.0.0.1:8080/api/health
```

## Apache vhost

```bash
sudo cp deploy/apache-docker-vhost.conf /etc/apache2/sites-available/pismo.iit.sggw.pl.conf
sudo a2ensite pismo.iit.sggw.pl.conf
sudo apache2ctl configtest
sudo systemctl reload apache2
```

DNS: `pismo.iit.sggw.pl` → IP serwera. HTTPS na Waszym zewnętrznym reverse proxy.

## Aktualizacja

```bash
cd /home/a304500/public_html/pismo
git pull
docker compose up -d --build
```

## Logi / stop

```bash
docker compose logs -f
docker compose down
```
