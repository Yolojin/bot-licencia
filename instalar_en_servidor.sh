#!/bin/bash
# Instala el bot de la licencia en un servidor Ubuntu que ya existe.
# Uso (dentro del servidor, por SSH):
#   curl -fsSL https://raw.githubusercontent.com/Yolojin/bot-licencia/main/instalar_en_servidor.sh | sudo bash
set -e

echo ""
echo "=== Instalador del bot de la licencia ==="
read -r -p "Tu RUT (sin puntos y con guion, ej: 12345678-9): " RUT </dev/tty
read -r -s -p "Tu clave de la agenda municipal (no se ve al escribir): " CLAVE </dev/tty
echo ""
read -r -p "Token del bot de Telegram (Licencia Iquique): " TOKEN </dev/tty

umask 077
cat > /root/bot.env <<EOF
RUT=$RUT
CLAVE=$CLAVE
TELEGRAM_TOKEN=$TOKEN
TELEGRAM_CHAT_ID=5769383577
EOF

echo ""
echo "Instalando (puede tardar 5 a 15 minutos)..."
curl -fsSL https://raw.githubusercontent.com/Yolojin/bot-licencia/main/instalar_oracle.sh | bash > /var/log/bot-instalacion.log 2>&1
echo ""
echo "Listo. Revisa Telegram: te debería llegar un mensaje del bot."
echo "Registro del bot: /opt/bot/registro.log"
