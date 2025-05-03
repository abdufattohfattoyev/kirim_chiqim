FROM python:3.11-slim

WORKDIR /app

# Tizim qaramliklarini o‘rnatish (gcc va boshqa zarur vositalar)
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Python qaramliklarini nusxalash va o‘rnatish
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Ilova kodini nusxalash
COPY . .

# Static fayllarni yig‘ish
RUN python manage.py collectstatic --noinput --clear

# Gunicorn bilan ishga tushirish
CMD ["gunicorn", "--bind", "0.0.0.0:8001", "config.wsgi:application"]