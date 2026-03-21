# Базовый образ
FROM python:3.12-slim

# Системные зависимости (минимум)
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Рабочая директория
WORKDIR /app

# Кэширование зависимостей
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# Копируем проект
COPY . .

# Открываем порт
EXPOSE 10000

# Запуск
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "10000"]