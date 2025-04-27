FROM python:3.10-slim
WORKDIR /app

# psql-клиент (для pg_isready)
RUN apt-get update \
    && apt-get install -y postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Python-зависимости
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Приложение
COPY . .
EXPOSE 5000

# Ждём доступности БД, затем запускаем Flask
CMD ["sh", "-c", "until pg_isready -h db -U postgres -d ssi; do echo 'Waiting for database…'; sleep 2; done; python app.py"]
