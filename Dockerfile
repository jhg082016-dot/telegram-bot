# Берем официальный образ Python
FROM python:3.11-slim

# Устанавливаем системные программы, которые нужны твоему боту
# ffmpeg - для youtube_download
# poppler-utils - для pdf2image
# libreoffice - для конвертации в PDF
RUN apt-get update && apt-get install -y \
    ffmpeg \
    poppler-utils \
    libreoffice \
    zip \
    unzip \
    wget \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем и устанавливаем Python-библиотеки из requirements.txt
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Устанавливаем дополнительные библиотеки, которые нужны ai_bot.py
# (их нет в твоем requirements.txt, но они используются в коде)
RUN pip install --no-cache-dir pyTelegramBotAPI requests pypdf pdf2image python-docx img2pdf yt-dlp pyflakes matplotlib

# Копируем ВСЕ остальные файлы проекта (ai_bot.py, start.sh и т.д.)
COPY . .

# Даем права на запуск скрипта
RUN chmod +x start.sh

# Запускаем через наш start.sh
CMD ["bash", "start.sh"]