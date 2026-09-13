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

echo "--- СПИСОК ФАЙЛОВ В /app ---"
ls -la /app/
echo "--- КОНЕЦ СПИСКА ---"

echo "--- ПРОВЕРКА СИНТАКСИСА ---"
python3 -m py_compile /app/ai_bot.py && echo "ai_bot.py OK" || echo "ai_bot.py СЛОМАН"
python3 -m py_compile /app/auto_features.py && echo "auto_features.py OK" || echo "auto_features.py СЛОМАН"
echo "--- КОНЕЦ ПРОВЕРКИ ---"

echo "--- ПРОВЕРКА ИМПОРТОВ ---"
python3 -c "import telebot; print('telebot OK')" 2>&1
python3 -c "import matplotlib; print('matplotlib OK')" 2>&1
python3 -c "import pypdf; print('pypdf OK')" 2>&1
python3 -c "import pdf2image; print('pdf2image OK')" 2>&1
python3 -c "import docx; print('docx OK')" 2>&1
python3 -c "import img2pdf; print('img2pdf OK')" 2>&1
python3 -c "import yt_dlp; print('yt_dlp OK')" 2>&1
python3 -c "import pyflakes; print('pyflakes OK')" 2>&1
echo "--- КОНЕЦ ПРОВЕРКИ ---"

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

sleep 5

echo "--- ЖИВЫЕ ПРОЦЕССЫ ---"
ps aux | grep python3 | grep -v grep
echo "--- КОНЕЦ ПРОЦЕССОВ ---"

echo "--- ЛОГ AI_BOT (последние 20 строк) ---"
tail -20 /app/ai_bot.log
echo "--- КОНЕЦ ЛОГА AI_BOT ---"

echo "--- ЛОГ MAIN (последние 20 строк) ---"
tail -20 /app/main.log
echo "--- КОНЕЦ ЛОГА MAIN ---"

echo "--- ЛОГ BACKUP (последние 20 строк) ---"
tail -20 /app/backup.log
echo "--- КОНЕЦ ЛОГА BACKUP ---"

echo "=== [START] Готово ==="
