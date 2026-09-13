import os
import json
import time
import shutil
import tarfile
import requests
from datetime import datetime, timedelta

# ===== КОНФИГ =====
BOT_TOKEN = os.getenv("MAIN_BOT_TOKEN")
CHAT_ID = "1430065211"

STATE_FILE = "/app/data/timer_state.json"
BACKUP_DIR = "/app/data/timer_backups"
APP_DIR = "/app"

# 400 часов
TRIGGER_HOURS = 400

# ===== УТИЛИТЫ =====
def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                return json.load(f)
        except:
            pass
    return None

def save_state(state):
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)

def send_msg(text):
    try:
        requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            data={"chat_id": CHAT_ID, "text": text},
            timeout=30
        )
    except Exception as e:
        print(f"[send_msg] error: {e}")

def send_doc(path, caption=""):
    try:
        with open(path, "rb") as f:
            requests.post(
                f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument",
                data={"chat_id": CHAT_ID, "caption": caption},
                files={"document": f},
                timeout=300
            )
    except Exception as e:
        print(f"[send_doc] error: {e}")

# ===== СОЗДАНИЕ БЭКАПА =====
def make_full_backup():
    os.makedirs(BACKUP_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    tmp_dir = f"/tmp/full_backup_{ts}"
    os.makedirs(tmp_dir, exist_ok=True)

    # Копируем файлы кода
    for f in os.listdir(APP_DIR):
        full = os.path.join(APP_DIR, f)
        if os.path.isfile(full) and not f.endswith(".tar.gz"):
            try:
                shutil.copy2(full, tmp_dir)
            except:
                pass

    # Копируем папки
    for folder in ["backups", "exports", "imports"]:
        src = os.path.join(APP_DIR, folder)
        if os.path.isdir(src):
            shutil.copytree(src, os.path.join(tmp_dir, folder), dirs_exist_ok=True)

    # Список переменных
    with open(os.path.join(tmp_dir, "env_names.txt"), "w") as f:
        for k, v in os.environ.items():
            if any(x in k for x in ["TELEGRAM", "AI_BOT", "GEMINI", "EXA", "MAIN"]):
                f.write(f"{k}=***\n")

    # Структура
    with open(os.path.join(tmp_dir, "structure.txt"), "w") as f:
        for root, dirs, files in os.walk(APP_DIR):
            f.write(f"{root}\n")
            for file in files:
                f.write(f"  {file}\n")

    # Архив
    archive = f"{BACKUP_DIR}/full_backup_{ts}.tar.gz"
    with tarfile.open(archive, "w:gz") as tar:
        tar.add(tmp_dir, arcname=f"full_backup_{ts}")

    shutil.rmtree(tmp_dir, ignore_errors=True)

    size_mb = round(os.path.getsize(archive) / (1024 * 1024), 2)
    return archive, size_mb

# ===== ОСНОВНАЯ ЛОГИКА =====
if __name__ == "__main__":
    print("[timer] Запуск таймера бэкапа")
    send_msg("⏱ Таймер бэкапа запущен.\nПроверяю состояние...")

    state = load_state()

    if state is None:
        # Первый запуск — создаём состояние
        state = {
            "start_time": datetime.now().isoformat(),
            "backup_done": False
        }
        save_state(state)
        send_msg(
            f"✅ Таймер создан.\n"
            f"📅 Старт: {state['start_time']}\n"
            f"⏰ Бэкап через 400 часов ({TRIGGER_HOURS} ч)."
        )
        print(f"[timer] Первый запуск. Старт: {state['start_time']}")
    else:
        start = datetime.fromisoformat(state["start_time"])
        now = datetime.now()
        elapsed = now - start
        elapsed_hours = elapsed.total_seconds() / 3600
        remaining = TRIGGER_HOURS - elapsed_hours

        print(f"[timer] Прошло: {elapsed_hours:.1f} ч. Осталось: {remaining:.1f} ч.")

        if state.get("backup_done"):
            send_msg("ℹ️ Бэкап уже был сделан ранее. Ничего не делаю.")
            print("[timer] Бэкап уже сделан.")
            exit(0)

        if elapsed_hours >= TRIGGER_HOURS:
            # Делаем бэкап
            send_msg(
                f"🚨 Прошло {elapsed_hours:.0f} часов!\n"
                f"Делаю ПОЛНЫЙ бэкап..."
            )
            try:
                archive, size = make_full_backup()
                send_doc(archive, f"🗄 ПОЛНЫЙ БЭКАП\nРазмер: {size} MB\nДата: {datetime.now()}")

                # Дополнительно присылаем ключи и БД
                for extra in ["chats.db", "gemini_keys.json", "exa_key.txt"]:
                    p = os.path.join(APP_DIR, extra)
                    if os.path.exists(p):
                        send_doc(p, f"📎 {extra}")

                state["backup_done"] = True
                state["backup_time"] = datetime.now().isoformat()
                save_state(state)
                send_msg("✅ Бэкап успешно завершён!")
            except Exception as e:
                send_msg(f"❌ Ошибка при бэкапе: {e}")
        else:
            # Ещё рано — сообщаем сколько осталось
            # Сообщение отправляем только раз в 24 часа
            last_notify = state.get("last_notify")
            if not last_notify or (now - datetime.fromisoformat(last_notify)).total_seconds() > 86400:
                send_msg(
                    f"⏱ Таймер работает.\n"
                    f"Прошло: {elapsed_hours:.1f} ч.\n"
                    f"Осталось: {remaining:.1f} ч."
                )
                state["last_notify"] = now.isoformat()
                save_state(state)
            else:
                print("[timer] Пропускаю уведомление (< 24 ч с прошлого).")