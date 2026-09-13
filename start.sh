#!/bin/bash

echo "=== [START] Автозапуск ==="

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

# Убиваем старые процессы
pkill -9 -f ai_bot.py 2>/dev/null
pkill -9 -f backup_and_notify.py 2>/dev/null
pkill -9 -f main.py 2>/dev/null
sleep 2

# Запускаем backup в фоне (он спит и раз в сутки делает бэкап)
nohup python3 -u /app/backup_and_notify.py > /app/backup.log 2>&1 &
echo "✅ backup_and_notify.py запущен"

# Запускаем main.py в фоне (SWILL-бот для группы)
nohup python3 -u /app/main.py > /app/main.log 2>&1 &
echo "✅ main.py запущен"

# Запускаем AI-бота НАПРЯМУЮ — все логи идут в Railway
echo "--- ЗАПУСК AI_BOT ---"
python3 -u /app/ai_bot.py
