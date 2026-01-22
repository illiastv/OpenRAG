@echo off
echo 🚀 Деплой OpenRAG...

REM Перевірка .env файлу
if not exist .env (
    echo ❌ Файл .env не знайдено!
    echo Створіть .env файл з OPENAI_API_KEY=your_key
    exit /b 1
)

REM Зупинка старих контейнерів
echo 🛑 Зупинка старих контейнерів...
docker-compose down

REM Білд і запуск
echo 🔨 Білд і запуск...
docker-compose up -d --build

REM Чекаємо поки контейнери запустяться
echo ⏳ Чекаємо запуск контейнерів...
timeout /t 5 /nobreak >nul

REM Перевірка статусу
echo 📊 Статус контейнерів:
docker-compose ps

echo.
echo ✅ Деплой завершено!
echo 🌐 Відкрийте: http://your-server-ip:5555
echo.
echo Логи: docker-compose logs -f
