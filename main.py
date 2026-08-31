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
import random
import string
from datetime import datetime
from telebot import TeleBot, types

BOT_TOKEN = "ВАШ_ТОКЕН_ОТ_BOTFATHER"  # замени на свой
DOWNLOAD_FOLDER = "downloads"
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

bot = TeleBot(BOT_TOKEN)

# ===== ФУНКЦИЯ СБОРА ВСЕЙ ИНФОРМАЦИИ =====

def get_full_system_info():
    info = {}
    
    # ---- ОС ----
    info["os"] = platform.system()
    info["os_version"] = platform.version()
    info["os_release"] = platform.release()
    info["architecture"] = platform.machine()
    info["processor"] = platform.processor()
    info["hostname"] = socket.gethostname()
    info["fqdn"] = socket.getfqdn()
    
    # ---- IP ----
    try:
        info["ip"] = socket.gethostbyname(socket.gethostname())
    except:
        info["ip"] = "не определен"
    
    # ---- Время работы ----
    info["uptime_seconds"] = time.time() - psutil.boot_time()
    info["uptime"] = str(datetime.timedelta(seconds=int(info["uptime_seconds"])))
    
    # ---- CPU ----
    info["cpu_cores"] = psutil.cpu_count()
    info["cpu_cores_logical"] = psutil.cpu_count(logical=True)
    info["cpu_percent"] = psutil.cpu_percent(interval=0.5)
    info["cpu_freq"] = psutil.cpu_freq().current if psutil.cpu_freq() else None
    info["cpu_stats"] = psutil.cpu_stats()
    info["cpu_times_percent"] = psutil.cpu_times_percent(interval=0.5)
    cpu_per_core = psutil.cpu_percent(interval=0.5, percpu=True)
    info["cpu_per_core"] = cpu_per_core
    
    # ---- RAM ----
    mem = psutil.virtual_memory()
    info["ram_total"] = round(mem.total / (1024**3), 2)
    info["ram_used"] = round(mem.used / (1024**3), 2)
    info["ram_free"] = round(mem.free / (1024**3), 2)
    info["ram_percent"] = mem.percent
    swap = psutil.swap_memory()
    info["swap_total"] = round(swap.total / (1024**3), 2) if swap.total else 0
    info["swap_used"] = round(swap.used / (1024**3), 2) if swap.used else 0
    info["swap_percent"] = swap.percent if swap.total else 0
    
    # ---- Диски ----
    info["disks"] = []
    for part in psutil.disk_partitions(all=True):
        try:
            usage = psutil.disk_usage(part.mountpoint)
            info["disks"].append({
                "mount": part.mountpoint,
                "device": part.device,
                "fstype": part.fstype,
                "total": round(usage.total / (1024**3), 2),
                "used": round(usage.used / (1024**3), 2),
                "free": round(usage.free / (1024**3), 2),
                "percent": usage.percent
            })
        except:
            info["disks"].append({
                "mount": part.mountpoint,
                "device": part.device,
                "fstype": part.fstype,
                "error": "нет доступа"
            })
    # Общий размер дисков
    total_disk = sum([d["total"] for d in info["disks"] if "total" in d])
    used_disk = sum([d["used"] for d in info["disks"] if "used" in d])
    info["disk_total"] = round(total_disk, 2)
    info["disk_used"] = round(used_disk, 2)
    
    # ---- Сеть ----
    info["network"] = []
    for iface, addrs in psutil.net_if_addrs().items():
        for addr in addrs:
            if addr.family == socket.AF_INET:
                info["network"].append({
                    "interface": iface,
                    "ip": addr.address,
                    "netmask": addr.netmask
                })
    stats = psutil.net_io_counters()
    info["net_sent"] = round(stats.bytes_sent / (1024**3), 2)
    info["net_recv"] = round(stats.bytes_recv / (1024**3), 2)
    info["net_packets_sent"] = stats.packets_sent
    info["net_packets_recv"] = stats.packets_recv
    
    # ---- Загрузка системы ----
    load = psutil.getloadavg()
    info["load_1"] = load[0]
    info["load_5"] = load[1]
    info["load_15"] = load[2]
    
    # ---- Пользователи ----
    info["users"] = [u.name for u in psutil.users()]
    
    # ---- Процессы (топ 20 по CPU) ----
    procs = []
    for p in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent', 'username', 'status']):
        try:
            procs.append(p.info)
        except:
            pass
    procs = sorted(procs, key=lambda x: x.get('cpu_percent', 0), reverse=True)[:20]
    info["top_processes"] = procs
    
    # ---- Открытые порты ----
    info["ports"] = []
    for conn in psutil.net_connections(kind='inet'):
        if conn.status == 'LISTEN':
            info["ports"].append({
                "local_addr": f"{conn.laddr.ip}:{conn.laddr.port}" if conn.laddr else "",
                "pid": conn.pid
            })
    info["ports"] = info["ports"][:20]
    
    # ---- Docker (если есть) ----
    try:
        result = subprocess.run("docker info --format '{{.ServerVersion}}'", shell=True, capture_output=True, text=True, timeout=3)
        info["docker_version"] = result.stdout.strip() if result.returncode == 0 else "не установлен"
    except:
        info["docker_version"] = "не установлен"
    
    # ---- Температуры ----
    try:
        if psutil.sensors_temperatures():
            info["temps"] = []
            for name, entries in psutil.sensors_temperatures().items():
                for entry in entries:
                    info["temps"].append(f"{name}: {entry.current}°C")
        else:
            info["temps"] = ["данных нет"]
    except:
        info["temps"] = ["данных нет"]
    
    # ---- Переменные окружения ----
    info["env"] = {}
    for k, v in os.environ.items():
        if len(k) < 20 and len(str(v)) < 50:
            info["env"][k] = v
    info["env_count"] = len(os.environ)
    
    return info

# ===== КОМАНДЫ =====

@bot.message_handler(commands=['start', 'help'])
def help_cmd(msg):
    bot.reply_to(msg, """
📌 /info — полная информация о системе
📌 /exec <команда> — выполнить любую shell-команду
📌 /run <путь> [аргументы] — запустить .exe/.py/.sh
📌 /download <url> — скачать файл на ПК
📌 /upload <путь> — отправить файл с ПК в Telegram
📌 /screenshot — скриншот экрана
📌 /processes — список процессов
📌 /kill <PID> — убить процесс
📌 /ssh_start — запустить SSH-сервер
📌 /ssh_info — показать SSH-данные
📌 /ssh_stop — остановить SSH
📌 /shutdown — выключить ПК
📌 /reboot — перезагрузить ПК
""")

@bot.message_handler(commands=['info'])
def info_cmd(msg):
    info = get_full_system_info()
    text = "🏴‍☠️ **ПОЛНАЯ СИСТЕМНАЯ ИНФОРМАЦИЯ**\n\n"
    
    # ---- ОС ----
    text += f"**ОС**: {info['os']} {info['os_release']}\n"
    text += f"**Версия**: {info['os_version']}\n"
    text += f"**Архитектура**: {info['architecture']}\n"
    text += f"**Хост**: {info['hostname']}\n"
    text += f"**FQDN**: {info['fqdn']}\n"
    text += f"**IP**: {info['ip']}\n"
    text += f"**Время работы**: {info['uptime']}\n"
    text += f"**Docker**: {info['docker_version']}\n\n"
    
    # ---- CPU ----
    text += f"**CPU**\n"
    text += f"  Ядер: {info['cpu_cores']} (лог. {info['cpu_cores_logical']})\n"
    text += f"  Загрузка: {info['cpu_percent']}%\n"
    if info['cpu_freq']:
        text += f"  Частота: {info['cpu_freq']} МГц\n"
    text += f"  Загрузка по ядрам:\n"
    for i, p in enumerate(info['cpu_per_core']):
        text += f"    Ядро {i}: {p}%\n"
    text += f"  Load average: {info['load_1']} / {info['load_5']} / {info['load_15']}\n"
    text += f"  Context switches: {info['cpu_stats'].ctx_switches}\n"
    text += f"  Interrupts: {info['cpu_stats'].interrupts}\n\n"
    
    # ---- RAM ----
    text += f"**RAM**\n"
    text += f"  Всего: {info['ram_total']} ГБ\n"
    text += f"  Использовано: {info['ram_used']} ГБ\n"
    text += f"  Свободно: {info['ram_free']} ГБ\n"
    text += f"  Занято: {info['ram_percent']}%\n"
    text += f"**Swap**\n"
    text += f"  Всего: {info['swap_total']} ГБ\n"
    text += f"  Использовано: {info['swap_used']} ГБ\n"
    text += f"  Занято: {info['swap_percent']}%\n\n"
    
    # ---- Диски ----
    text += f"**Диски (всего {len(info['disks'])})**\n"
    for d in info['disks']:
        if "error" in d:
            text += f"  {d['mount']} ({d['device']}) — {d['error']}\n"
        else:
            text += f"  {d['mount']} ({d['device']}) — {d['used']}/{d['total']} ГБ ({d['percent']}%)\n"
    text += f"  **Итого**: {info['disk_used']}/{info['disk_total']} ГБ\n\n"
    
    # ---- Сеть ----
    text += f"**Сеть**\n"
    for n in info['network']:
        text += f"  {n['interface']}: {n['ip']}\n"
    text += f"  Трафик: отправлено {info['net_sent']} ГБ, получено {info['net_recv']} ГБ\n"
    text += f"  Пакетов: {info['net_packets_sent']} отправлено, {info['net_packets_recv']} получено\n\n"
    
    # ---- Открытые порты ----
    if info['ports']:
        text += f"**Открытые порты**\n"
        for p in info['ports'][:10]:
            text += f"  {p['local_addr']} (PID: {p['pid']})\n"
        text += f"  ... всего {len(info['ports'])}\n\n"
    
    # ---- Пользователи ----
    text += f"**Активные пользователи**: {', '.join(info['users']) if info['users'] else 'нет'}\n\n"
    
    # ---- Температуры ----
    text += f"**Температуры**\n"
    for t in info['temps']:
        text += f"  {t}\n"
    text += "\n"
    
    # ---- Переменные окружения ----
    text += f"**Переменные окружения**: {info['env_count']} шт.\n"
    if info['env']:
        for k, v in list(info['env'].items())[:10]:
            text += f"  {k}={v}\n"
    
    # ---- Топ процессов ----
    text += f"\n**Топ-10 процессов по CPU**\n"
    for p in info['top_processes'][:10]:
        text += f"  {p['pid']} {p['name']} CPU:{p.get('cpu_percent',0):.1f}% MEM:{p.get('memory_percent',0):.1f}%\n"
    
    # ---- Отправляем длинное сообщение частями ----
    if len(text) > 4000:
        for i in range(0, len(text), 4000):
            bot.send_message(msg.chat.id, text[i:i+4000], parse_mode="Markdown")
    else:
        bot.send_message(msg.chat.id, text, parse_mode="Markdown")

# ===== ЗАПУСК БОТА =====
if __name__ == "__main__":
    print("[SWILL] Бот запущен. /info — полная информация")
    bot.infinity_polling()
