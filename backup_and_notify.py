import os
import time
import shutil
import sqlite3
import requests
from datetime import datetime

# ===== КОНФИГ =====
BOT_TOKEN = os.getenv("MAIN_BOT_TOKEN")   # основной бот
GROUP_CHAT_ID = "-1004332423937"                            # сюда впишешь ID
DB_PATH = "/app/data/chats.db"
BACKUP_DIR = "/app/backups"
KEYS_FILE = "/app/gemini_keys.json"

# ===== УВЕДОМЛЕНИЕ =====
def notify(text):
    try:
        requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            data={"chat_id": GROUP_CHAT_ID, "text": text},
            timeout=30
        )
    except Exception as e:
        print(f"[notify] error: {e}")

# ===== БЭКАП БД =====
def make_backup():
    if not os.path.exists(DB_PATH):
        print("[backup] DB not found")
        return None
    ts = datetime.now().strftime("%Y-%m-%d_%H-%M")
    dst = os.path.join(BACKUP_DIR, f"chats_{ts}.db")
    shutil.copy2(DB_PATH, dst)
    return dst

def send_backup(path):
    try:
        with open(path, "rb") as f:
            requests.post(
                f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument",
                data={"chat_id": GROUP_CHAT_ID, "caption": f"🗄 Бэкап базы ({os.path.basename(path)})"},
                files={"document": f},
                timeout=120
            )
    except Exception as e:
        print(f"[send_backup] error: {e}")

# ===== ПРОВЕРКА КЛЮЧЕЙ =====
def check_keys():
    if not os.path.exists(KEYS_FILE):
        return None
    import json
    with open(KEYS_FILE) as f:
        data = json.load(f)
    working = 0
    broken = 0
    for key in data.get("keys", []):
        url = f"https://generativelanguage.googleapis.com/v1beta/models?key={key}"
        try:
            r = requests.get(url, timeout=15)
            if r.status_code == 200:
                working += 1
            else:
                broken += 1
        except Exception:
            broken += 1
    if broken > 0:
        notify(f"⚠️ Проблема с ключами Gemini:\n🟢 Работают: {working}\n🔴 Сломаны: {broken}")
    return working, broken

# ===== РОТАЦИЯ СТАРЫХ БЭКАПОВ =====
def cleanup_old(keep=7):
    files = sorted([f for f in os.listdir(BACKUP_DIR) if f.startswith("chats_")])
    if len(files) > keep:
        for f in files[:-keep]:
            os.remove(os.path.join(BACKUP_DIR, f))

# ===== ОСНОВНОЙ ЦИКЛ =====
if __name__ == "__main__":
    print("🚀 backup_and_notify запущен")
    last_backup_day = None
    while True:
        now = datetime.now()
        # бэкап раз в сутки в 03:00
        if now.hour == 3 and now.day != last_backup_day:
            p = make_backup()
            if p:
                send_backup(p)
                cleanup_old(keep=7)
                last_backup_day = now.day
                print(f"[backup] отправлен {p}")
            check_keys()
        time.sleep(600)
