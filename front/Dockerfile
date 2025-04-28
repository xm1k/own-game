# front/Dockerfile
FROM node:18-alpine

WORKDIR /app

# 1) копируем манифесты и ставим все deps
COPY package*.json ./
RUN npm ci

# 2) копируем код
COPY . .

EXPOSE 8080

CMD ["npm", "run", "serve"]

