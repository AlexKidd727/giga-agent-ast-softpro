# Google Calendar Credentials

Эта папка предназначена для хранения файлов авторизации Google Calendar.

## Настройка

1. Создайте Service Account в Google Cloud Console
2. Скачайте JSON файл с ключами
3. Поместите файл в эту папку (например, `service-account.json`)
4. Установите переменную окружения:
   ```env
   GOOGLE_CALENDAR_CREDENTIALS=./credentials/service-account.json
   ```

## Безопасность

⚠️ **Важно:** 
- Никогда не коммитьте файлы с ключами в Git
- Файлы *.json автоматически игнорируются
- Используйте переменные окружения для путей к файлам

## Структура файла

Пример структуры JSON файла Service Account:
```json
{
  "type": "service_account",
  "project_id": "your-project",
  "private_key_id": "...",
  "private_key": "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n",
  "client_email": "your-service@your-project.iam.gserviceaccount.com",
  "client_id": "...",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token"
}
```

Подробная инструкция по настройке: [GOOGLE_CALENDAR_SETUP.md](../GOOGLE_CALENDAR_SETUP.md)
