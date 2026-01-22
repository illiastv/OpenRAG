# Швидкий деплой OpenRAG

## 1. Підготовка

Створіть файл `.env` в корені проекту:
```bash
OPENAI_API_KEY=your_openai_key_here
```

## 2. Деплой

```bash
docker-compose up -d --build
```

## 3. Перевірка

Відкрийте браузер: `d`

## 4. Зупинка

```bash
docker-compose down
```

## 5. Перезапуск

```bash
docker-compose restart
```

## 6. Логи

```bash
# Всі логи
docker-compose logs

# Логи бекенду
docker-compose logs backend

# Логи фронтенду
docker-compose logs frontend

# Слідкування за логами
docker-compose logs -f
```

## 7. Оновлення

```bash
# Зупинити
docker-compose down

# Перебілдити і запустити
docker-compose up -d --build
```

## Порти

- **5555** - зовнішній порт для доступу до додатку
- **8000** - внутрішній порт бекенду (не відкритий ззовні)

## Troubleshooting

Якщо не працює:
1. Перевірте `.env` файл з OPENAI_API_KEY
2. Перевірте логи: `docker-compose logs`
3. Перевірте чи порт 5555 не зайнятий: `netstat -tulpn | grep 5555`
4. Перевірте firewall: `sudo ufw allow 5555`
