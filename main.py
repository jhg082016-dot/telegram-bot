import os
import sys
import subprocess
import platform
import psutil
import shutil
import time
import threading
import socket
import getpass
import requests
import json
import random
import string
from datetime import datetime
from telebot import TeleBot, types

# ===== ТОКЕН ИЗ ПЕРЕМЕННОЙ ОКРУЖЕНИЯ =====
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not BOT_TOKEN:
    print("❌ ОШИБКА: TELEGRAM_BOT_TOKEN не задан!")
    print("Установи переменную окружения TELEGRAM_BOT_TOKEN")
    sys.exit(1)

DOWNLOAD_FOLDER = "downloads"
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

bot = TeleBot(BOT_TOKEN)

# ===== ФУНКЦИИ =====

def run_command(cmd, timeout=60):
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
    return result.stdout + result.stderr

def send_long_message(chat_id, text):
    if len(text) <= 4000:
        bot.send_message(chat_id, text)
    else:
        for i in range(0, len(text), 4000):
            bot.send_message(chat_id, text[i:i+4000])

# ===== КОМАНДЫ БОТА =====

@bot.message_handler(commands=['start', 'help'])
def help_cmd(msg):
    bot.reply_to(msg, """
📌 /info — информация о системе
📌 /exec <команда> — выполнить shell-команду
📌 /run <путь> [аргументы] — запустить файл
📌 /download <url> — скачать файл
📌 /upload <путь> — отправить файл с ПК
📌 /screenshot — скриншот
📌 /processes — список процессов
📌 /kill <PID> — убить процесс
📌 /shutdown — выключить
📌 /reboot — перезагрузить
""")

@bot.message_handler(commands=['info'])
def info_cmd(msg):
    info = {}
    info["OS"] = platform.system()
    info["OS_version"] = platform.version()
    info["Machine"] = platform.machine()
    info["Processor"] = platform.processor()
    info["Hostname"] = socket.gethostname()
    try:
        info["IP"] = socket.gethostbyname(socket.gethostname())
    except:
        info["IP"] = "не определен"
    info["CPU_count"] = psutil.cpu_count()
    info["CPU_percent"] = psutil.cpu_percent(interval=0.5)
    info["RAM_total"] = round(psutil.virtual_memory().total / (1024**3), 2)
    info["RAM_used"] = round(psutil.virtual_memory().used / (1024**3), 2)
    info["RAM_percent"] = psutil.virtual_memory().percent
    info["Disk"] = []
    for part in psutil.disk_partitions():
        try:
            usage = psutil.disk_usage(part.mountpoint)
            info["Disk"].append({
                "mount": part.mountpoint,
                "total": round(usage.total / (1024**3), 2),
                "used": round(usage.used / (1024**3), 2),
                "free": round(usage.free / (1024**3), 2),
                "percent": usage.percent
            })
        except:
            pass
    info["Users"] = [u.name for u in psutil.users()]
    
    text = f"🏴‍☠️ SWILL-система\n"
    text += f"ОС: {info['OS']} {info['OS_version']}\n"
    text += f"Хост: {info['Hostname']}\n"
    text += f"IP: {info['IP']}\n"
    text += f"CPU: {info['CPU_count']} ядер, загрузка {info['CPU_percent']}%\n"
    text += f"RAM: {info['RAM_used']} / {info['RAM_total']} ГБ ({info['RAM_percent']}%)\n"
    text += "Диски:\n"
    for d in info["Disk"]:
        text += f"  {d['mount']} — {d['used']}/{d['total']} ГБ ({d['percent']}%)\n"
    text += f"Пользователи: {', '.join(info['Users']) if info['Users'] else 'нет активных'}"
    
    send_long_message(msg.chat.id, text)

@bot.message_handler(commands=['exec'])
def exec_cmd(msg):
    cmd = msg.text.replace('/exec', '', 1).strip()
    if not cmd:
        bot.reply_to(msg, "❌ Укажи команду")
        return
    try:
        out = run_command(cmd)
        if not out.strip():
            out = "(пустой вывод)"
        send_long_message(msg.chat.id, f"📟 Результат:\n{out}")
    except Exception as e:
        bot.reply_to(msg, f"⚠️ Ошибка: {str(e)}")

@bot.message_handler(commands=['run'])
def run_cmd(msg):
    parts = msg.text.replace('/run', '', 1).strip().split(' ', 1)
    file_path = parts[0] if parts else ""
    args = parts[1] if len(parts) > 1 else ""
    if not file_path:
        bot.reply_to(msg, "❌ Укажи путь к файлу")
        return
    if not os.path.exists(file_path):
        bot.reply_to(msg, f"❌ Файл не найден: {file_path}")
        return
    try:
        cmd = f'"{file_path}" {args}'
        if platform.system() != "Windows":
            os.chmod(file_path, 0o755)
        out = run_command(cmd)
        send_long_message(msg.chat.id, f"✅ Результат:\n{out}")
    except Exception as e:
        bot.reply_to(msg, f"❌ Ошибка: {str(e)}")

@bot.message_handler(commands=['download'])
def download_cmd(msg):
    url = msg.text.replace('/download', '', 1).strip()
    if not url:
        bot.reply_to(msg, "❌ Укажи URL")
        return
    try:
        r = requests.get(url, stream=True)
        filename = url.split('/')[-1].split('?')[0] or "downloaded_file"
        path = os.path.join(DOWNLOAD_FOLDER, filename)
        with open(path, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
        bot.reply_to(msg, f"✅ Скачан: {path}")
    except Exception as e:
        bot.reply_to(msg, f"❌ Ошибка: {str(e)}")

@bot.message_handler(commands=['upload'])
def upload_cmd(msg):
    path = msg.text.replace('/upload', '', 1).strip()
    if not path or not os.path.exists(path):
        bot.reply_to(msg, "❌ Укажи существующий путь")
        return
    try:
        with open(path, 'rb') as f:
            bot.send_document(msg.chat.id, f, caption=f"Файл: {path}")
    except Exception as e:
        bot.reply_to(msg, f"❌ Ошибка: {str(e)}")

@bot.message_handler(commands=['screenshot'])
def screenshot_cmd(msg):
    try:
        import PIL.ImageGrab
        img = PIL.ImageGrab.grab()
        img.save("screenshot.png")
        with open("screenshot.png", "rb") as f:
            bot.send_photo(msg.chat.id, f, caption="🖼️ Скриншот")
        os.remove("screenshot.png")
    except:
        bot.reply_to(msg, "❌ Установи pillow для скриншотов")

@bot.message_handler(commands=['processes'])
def processes_cmd(msg):
    procs = []
    for p in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
        try:
            procs.append(p.info)
        except:
            pass
    procs = sorted(procs, key=lambda x: x.get('cpu_percent', 0), reverse=True)[:30]
    text = "🧠 ТОП-30 процессов:\n"
    for p in procs:
        text += f"{p['pid']} {p['name']} CPU:{p.get('cpu_percent',0):.1f}% MEM:{p.get('memory_percent',0):.1f}%\n"
    send_long_message(msg.chat.id, text)

@bot.message_handler(commands=['kill'])
def kill_cmd(msg):
    pid_str = msg.text.replace('/kill', '', 1).strip()
    if not pid_str.isdigit():
        bot.reply_to(msg, "❌ Укажи PID")
        return
    try:
        p = psutil.Process(int(pid_str))
        p.terminate()
        bot.reply_to(msg, f"✅ Процесс {pid_str} завершён")
    except Exception as e:
        bot.reply_to(msg, f"❌ Ошибка: {str(e)}")

@bot.message_handler(commands=['shutdown'])
def shutdown_cmd(msg):
    bot.reply_to(msg, "🔄 Выключение...")
    if platform.system() == "Windows":
        os.system("shutdown /s /t 5")
    else:
        os.system("shutdown -h now")

@bot.message_handler(commands=['reboot'])
def reboot_cmd(msg):
    bot.reply_to(msg, "🔄 Перезагрузка...")
    if platform.system() == "Windows":
        os.system("shutdown /r /t 5")
    else:
        os.system("reboot")

# ===== ЗАПУСК =====
if __name__ == "__main__":
    print("[SWILL] Бот запущен. /help — список команд.")
    bot.infinity_polling()
