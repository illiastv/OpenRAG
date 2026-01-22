#!/bin/bash

echo "🚀 Деплой OpenRAG..."

# Перевірка .env файлу
if [ ! -f .env ]; then
    echo "❌ Файл .env не знайдено!"
    echo "Створіть .env файл з OPENAI_API_KEY=your_key"
    exit 1
fi

# Зупинка старих контейнерів
echo "🛑 Зупинка старих контейнерів..."
docker-compose down

# Білд і запуск
echo "🔨 Білд і запуск..."
docker-compose up -d --build

# Чекаємо поки контейнери запустяться
echo "⏳ Чекаємо запуск контейнерів..."
sleep 5

# Перевірка статусу
echo "📊 Статус контейнерів:"
docker-compose ps

echo ""
echo "✅ Деплой завершено!"
echo "🌐 Відкрийте: http://your-server-ip:5555"
echo ""
echo "Логи: docker-compose logs -f"
