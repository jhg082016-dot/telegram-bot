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

pkill -9 -f ai_bot.py 2>/dev/null
pkill -9 -f backup_and_notify.py 2>/dev/null
pkill -9 -f main.py 2>/dev/null
sleep 2

# ЗАПУСКАЕМ AI_BOT НЕ В ФОНЕ, А НАПРЯМУЮ — ЧТОБЫ ВИДЕТЬ ОШИБКУ
echo "--- ПРОВЕРКА AI_BOT ---"
python3 /app/ai_bot.py 2>&1 | head -50 &
AI_PID=$!
sleep 10
kill $AI_PID 2>/dev/null
echo "--- КОНЕЦ ПРОВЕРКИ ---"

# Теперь запускаем в фоне как обычно
nohup python3 /app/ai_bot.py > /app/ai_bot.log 2>&1 &
echo "✅ ai_bot.py запущен"

nohup python3 /app/backup_and_notify.py > /app/backup.log 2>&1 &
echo "✅ backup_and_notify.py запущен"

nohup python3 /app/main.py > /app/main.log 2>&1 &
echo "✅ main.py запущен"

echo "=== [START] Готово ==="
