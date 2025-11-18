FROM python:3.11-slim

# نثبّت الأدوات اللي تحتاجها بعض المكتبات
RUN apt-get update && apt-get install -y \
    build-essential \
    poppler-utils \
    libpq-dev \
    libmagic1 \
    tesseract-ocr \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*


# نضع المشروع في الجذر مباشرة
WORKDIR /

# نضبط pip timeout لتجنب read timeout
RUN pip config set global.timeout 200

# ننسخ متطلبات المشروع
COPY requirements.txt /requirements.txt

# نثبّت pip والـ setuptools قبل البدء
RUN pip install --upgrade pip setuptools

# نثبّت كل المكتبات (مع رفع المهلة)
RUN pip install --default-timeout=200 --no-cache-dir -r /requirements.txt

# ننسخ مجلدات المشروع الأساسية
COPY backend /backend
COPY ai_engine /ai_engine
COPY web_app /web_app

# ندخل web_app لأنها تحتوي app.py
WORKDIR /web_app

EXPOSE 8000

CMD ["python", "app.py"]
