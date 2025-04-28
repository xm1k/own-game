### frontend/Dockerfile
FROM node:16-alpine

# Рабочая директория
WORKDIR /app

# Копируем package.json и package-lock.json (если есть)
COPY package*.json ./

# Устанавливаем зависимости
RUN npm install

# Копируем весь фронтенд-код
COPY . .

# Открываем порт разработки
EXPOSE 8080

# Запуск dev-сервера Vue
CMD ["npm", "run", "serve"]
