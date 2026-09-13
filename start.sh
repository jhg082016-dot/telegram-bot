#!/bin/bash

echo "=== [START] Автозапуск ==="

apt update -y
apt install -y python3 python3-pip ffmpeg poppler-utils libreoffice zip unzip wget curl

pip3 install --break-system-packages pyTelegramBotAPI requests pypdf pdf2image python-docx img2pdf yt-dlp pyflakes matplotlib

mkdir -p /app/exports /app/imports /app/tmp_files /app/backups

cat > /app/gemini_keys.json << EOF
{
  "keys": [
    "${GEMINI_KEY_1}",
    "${GEMINI_KEY_2}"
  ],
  "current": 0
}
EOF

echo "${EXA_KEY}" > /app/exa_key.txt

pkill -9 -f ai_bot.py 2>/dev/null
pkill -9 -f backup_and_notify.py 2>/dev/null
pkill -9 -f main.py 2>/dev/null
sleep 2

nohup python3 /app/ai_bot.py > /app/ai_bot.log 2>&1 &
echo "✅ ai_bot.py запущен"

nohup python3 /app/backup_and_notify.py > /app/backup.log 2>&1 &
echo "✅ backup_and_notify.py запущен"

nohup python3 /app/main.py > /app/main.log 2>&1 &
echo "✅ main.py запущен"

echo "=== [START] Готово ==="

sleep 20

CHAT_ID="1430065211"

# Проверка Telegram API (главный бот)
GETME_MAIN=$(curl -s "https://api.telegram.org/bot${MAIN_BOT_TOKEN}/getMe")
GETME_AI=$(curl -s "https://api.telegram.org/bot${AI_BOT_TOKEN}/getMe")

# Список процессов
PROCS=$(ps aux 2>/dev/null | grep -E "ai_bot|main.py|backup_and_notify" | grep -v grep)

# Логи
AI_LOG=$(tail -40 /app/ai_bot.log 2>/dev/null || echo "лог пуст")
MAIN_LOG=$(tail -40 /app/main.log 2>/dev/null || echo "лог пуст")
BACKUP_LOG=$(tail -40 /app/backup.log 2>/dev/null || echo "лог пуст")

curl -s -X POST "https://api.telegram.org/bot${MAIN_BOT_TOKEN}/sendMessage" \
  -d chat_id="${CHAT_ID}" \
  -d text="=== GET_ME MAIN ===
${GETME_MAIN}

=== GET_ME AI ===
${GETME_AI}

=== ПРОЦЕССЫ ===
${PROCS}"

curl -s -X POST "https://api.telegram.org/bot${MAIN_BOT_TOKEN}/sendMessage" \
  -d chat_id="${CHAT_ID}" \
  -d text="=== AI_BOT.LOG ===
${AI_LOG}

=== MAIN.LOG ===
${MAIN_LOG}

=== BACKUP.LOG ===
${BACKUP_LOG}"
