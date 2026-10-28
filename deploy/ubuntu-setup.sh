#!/usr/bin/env bash
# Instalacja na Ubuntu 22.04/24.04 (Docker + compose)
set -euo pipefail

if [[ $EUID -ne 0 ]]; then
  echo "Uruchom jako root: sudo bash deploy/ubuntu-setup.sh"
  exit 1
fi

apt-get update
apt-get install -y ca-certificates curl git

install -m 0755 -d /etc/apt/keyrings
if [[ ! -f /etc/apt/keyrings/docker.asc ]]; then
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
  chmod a+r /etc/apt/keyrings/docker.asc
fi

ARCH=$(dpkg --print-architecture)
CODENAME=$(. /etc/os-release && echo "$VERSION_CODENAME")
echo \
  "deb [arch=${ARCH} signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu ${CODENAME} stable" \
  > /etc/apt/sources.list.d/docker.list

apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

systemctl enable --now docker
echo "Docker OK. Dalej: sklonuj repo, skopiuj .env.example -> .env, ustaw DOMAIN, potem:"
echo "  cd /opt/pismo && docker compose up -d --build"
