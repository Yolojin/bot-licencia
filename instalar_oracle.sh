#!/bin/bash
# Instala el bot de la licencia en un servidor Ubuntu de Oracle Cloud.
# Lo ejecuta solo el script de inicio (cloud-init) del servidor.
set -e

mkdir -p /opt/bot
if [ -f /root/bot.env ]; then
  mv /root/bot.env /opt/bot/.env
fi
chmod 600 /opt/bot/.env

export DEBIAN_FRONTEND=noninteractive

# Memoria extra: los servidores gratis tienen poca RAM
if [ ! -f /swapfile ]; then
  fallocate -l 2G /swapfile
  chmod 600 /swapfile
  mkswap /swapfile
  swapon /swapfile
  echo '/swapfile none swap sw 0 0' >> /etc/fstab
fi

apt-get update -y
apt-get install -y python3-venv python3-pip curl

python3 -m venv /opt/bot/venv
/opt/bot/venv/bin/pip install --upgrade pip
/opt/bot/venv/bin/pip install playwright requests
PLAYWRIGHT_BROWSERS_PATH=/opt/bot/navegadores /opt/bot/venv/bin/python -m playwright install --with-deps chromium

cat > /opt/bot/correr.sh <<'FIN'
#!/bin/bash
cd /opt/bot
export PLAYWRIGHT_BROWSERS_PATH=/opt/bot/navegadores
# Siempre usa la última versión del bot que está en GitHub
curl -fsSL https://raw.githubusercontent.com/Yolojin/bot-licencia/main/revisar_agenda.py -o revisar_agenda.py.nuevo \
  && mv revisar_agenda.py.nuevo revisar_agenda.py
echo "=== $(date) ==="
/opt/bot/venv/bin/python revisar_agenda.py
FIN
chmod +x /opt/bot/correr.sh

# Revisa cada 30 minutos
echo '*/30 * * * * root /opt/bot/correr.sh >> /opt/bot/registro.log 2>&1' > /etc/cron.d/bot-licencia
chmod 644 /etc/cron.d/bot-licencia

# Prueba inicial: manda un mensaje a Telegram para confirmar que funciona
MODO_PRUEBA=true /opt/bot/correr.sh >> /opt/bot/registro.log 2>&1 || true
