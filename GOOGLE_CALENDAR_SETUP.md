# Инструкция по настройке Google Calendar для giga-agent

## Обзор

В giga-agent реализована простая авторизация Google Calendar через Service Account (по образцу проекта sterligov/main). Это позволяет работать с календарем без сложной OAuth авторизации пользователей.

## Шаг 1: Создание проекта в Google Cloud Console

1. Перейдите в [Google Cloud Console](https://console.cloud.google.com/)
2. Войдите в свой Google аккаунт
3. Создайте новый проект или выберите существующий:
   - Нажмите на выпадающий список проектов в верхней части
   - Нажмите "Новый проект"
   - Введите название проекта (например, "giga-agent-calendar")
   - Нажмите "Создать"

## Шаг 2: Включение Google Calendar API

1. В Google Cloud Console выберите ваш проект
2. Перейдите в раздел "APIs & Services" > "Library"
3. Найдите "Google Calendar API"
4. Нажмите на API и затем "Enable" (Включить)

## Шаг 3: Создание Service Account

1. Перейдите в "APIs & Services" > "Credentials"
2. Нажмите "Create Credentials" > "Service Account"
3. Заполните форму:
   - **Service account name**: `giga-agent-calendar-service`
   - **Service account ID**: автоматически сгенерируется
   - **Description**: `Service account for giga-agent calendar integration`
4. Нажмите "Create and Continue"
5. В разделе "Grant this service account access to project":
   - Роль: "Editor" или "Calendar Admin"
6. Нажмите "Continue" и затем "Done"

## Шаг 4: Создание ключей Service Account

1. В списке Service Accounts найдите созданный аккаунт
2. Нажмите на email Service Account
3. Перейдите на вкладку "Keys"
4. Нажмите "Add Key" > "Create new key"
5. Выберите тип "JSON"
6. Нажмите "Create"
7. Файл автоматически скачается (например, `giga-agent-calendar-xxxxx.json`)

## Шаг 5: Настройка календаря

### Вариант A: Использование основного календаря
1. Откройте [Google Calendar](https://calendar.google.com/)
2. В настройках календаря найдите "Calendar ID" основного календаря
3. Обычно это ваш email адрес

### Вариант B: Создание отдельного календаря
1. В Google Calendar нажмите "+" рядом с "Other calendars"
2. Выберите "Create new calendar"
3. Заполните название (например, "Giga Agent Calendar")
4. Нажмите "Create calendar"
5. В настройках календаря найдите "Calendar ID"

## Шаг 6: Предоставление доступа Service Account к календарю

**⚠️ ВАЖНО: Этот шаг критически важен для работы с вашим личным календарем!**

### Для доступа к личному календарю (например, your-email@gmail.com):

1. Откройте [Google Calendar](https://calendar.google.com/)
2. В левой панели найдите ваш основной календарь (обычно с вашим email)
3. Нажмите на три точки рядом с названием календаря
4. Выберите "Settings and sharing"
5. Прокрутите вниз до раздела "Share with specific people"
6. Нажмите "Add people"
7. Введите email Service Account (найден в JSON файле, поле `client_email`)
   - Пример: `giga-agent-calendar-xxxxx@giga-agent-calendar.iam.gserviceaccount.com`
8. Установите права доступа: **"Make changes to events"** (Редактировать события)
9. Нажмите "Send"

### Для доступа к отдельному календарю:

1. Создайте новый календарь или выберите существующий
2. Повторите шаги 3-9 выше

### Проверка доступа:

После предоставления доступа Service Account должен получить права на:
- ✅ Создание событий
- ✅ Чтение событий  
- ✅ Редактирование событий
- ✅ Удаление событий

**Примечание:** Изменения могут занять несколько минут для применения.

## Шаг 7: Настройка переменных окружения

**⚠️ ВАЖНО: Убедитесь, что CALENDAR_ID указывает на ваш личный календарь!**

Создайте файл `.env` в корне проекта giga-agent или добавьте в существующий:

```env
# Google Calendar Service Account
GOOGLE_CALENDAR_CREDENTIALS=path/to/your/service-account-file.json
CALENDAR_ID=your-calendar-id@group.calendar.google.com

# Примеры:
# Для личного календаря:
# GOOGLE_CALENDAR_CREDENTIALS=./credentials/giga-agent-calendar-xxxxx.json
# CALENDAR_ID=your-email@gmail.com

# Для отдельного календаря:
# GOOGLE_CALENDAR_CREDENTIALS=./credentials/giga-agent-calendar-xxxxx.json
# CALENDAR_ID=your-calendar-name@group.calendar.google.com
```

**Примечание:** Если вы хотите использовать свой личный календарь (например, alxstud@gmail.com), обязательно:
1. Предоставьте доступ Service Account к календарю (Шаг 6)
2. Установите `CALENDAR_ID=your-email@gmail.com` (не `primary`)

## Шаг 8: Размещение файла ключей

1. Создайте папку `credentials` в корне проекта
2. Поместите скачанный JSON файл в эту папку
3. Убедитесь, что файл добавлен в `.gitignore`:

```gitignore
# Google Calendar credentials
credentials/
*.json
.env
```

## Шаг 9: Установка зависимостей

Убедитесь, что установлены необходимые пакеты:

```bash
pip install google-api-python-client google-auth-oauthlib google-auth-httplib2
```

## Шаг 10: Тестирование

После настройки вы можете протестировать интеграцию:

1. Запустите giga-agent
2. Используйте команды:
   - "проверить статус календаря" - проверить подключение
   - "показать события" - показать список событий
   - "показать свободные слоты на 2025-01-20" - показать доступное время
   - "создать событие" - создать новое событие

## Примеры использования

### Проверка статуса
```
Пользователь: "проверить статус календаря"
Агент: ✅ Google Calendar подключен
```

### Создание события
```
Пользователь: "создай встречу 'Совещание' на 20.01.2025 15:00-16:00"
Агент: ✅ Событие создано успешно!
```

### Просмотр событий
```
Пользователь: "покажи мои события"
Агент: 📅 События в календаре (3):
1. Совещание
   ⏰ 20.01.2025 15:00 - 16:00
```

## Устранение неполадок

### Ошибка "Service account не найден"
- Проверьте путь к файлу в `GOOGLE_CALENDAR_CREDENTIALS`
- Убедитесь, что файл существует и доступен для чтения

### Ошибка "Calendar not found"
- Проверьте `CALENDAR_ID` в переменных окружения
- Убедитесь, что Service Account имеет доступ к календарю

### Ошибка "Insufficient permissions"
- Проверьте, что Service Account добавлен в календарь с правами "Make changes to events"
- Убедитесь, что Google Calendar API включен в проекте

### Ошибка "Authentication failed"
- Проверьте содержимое JSON файла
- Убедитесь, что ключи не истекли
- Пересоздайте ключи если необходимо

### События создаются в календаре Service Account, а не в личном календаре

**Проблема:** События появляются в календаре Service Account, но не видны в вашем личном календаре.

**Решение:**
1. **Проверьте настройки доступа:**
   - Убедитесь, что Service Account добавлен в ваш личный календарь
   - Проверьте, что установлены права "Make changes to events"

2. **Проверьте переменные окружения:**
   ```bash
   # Убедитесь, что CALENDAR_ID указывает на ваш календарь
   echo $CALENDAR_ID
   # Должно быть: your-email@gmail.com (не primary)
   ```

3. **Перезапустите контейнеры:**
   ```bash
   docker-compose down
   docker-compose up -d
   ```

4. **Проверьте настройки в Google Calendar:**
   - Откройте ваш календарь alxstud@gmail.com
   - В настройках календаря найдите раздел "Share with specific people"
   - Убедитесь, что Service Account указан с правами "Make changes to events"

**Диагностика:**
```bash
# Проверьте, какой календарь используется
docker-compose exec langgraph-api python -c "
import os
print('CALENDAR_ID:', os.getenv('CALENDAR_ID'))
"
```

## Безопасность

⚠️ **Важные моменты безопасности:**

1. **Никогда не коммитьте JSON файлы с ключами в Git**
2. **Используйте переменные окружения для конфиденциальных данных**
3. **Ограничьте права Service Account только необходимыми**
4. **Регулярно ротируйте ключи**
5. **Мониторьте использование API в Google Cloud Console**

## Дополнительные настройки

### Ограничения API
- Google Calendar API имеет лимиты запросов
- По умолчанию: 1,000,000 запросов в день
- Для продакшена рассмотрите увеличение лимитов

### Мониторинг
- В Google Cloud Console можно отслеживать использование API
- Настройте алерты при превышении лимитов

## Поддержка

При возникновении проблем:
1. Проверьте логи giga-agent
2. Убедитесь в правильности настройки переменных окружения
3. Проверьте права доступа в Google Cloud Console
4. Обратитесь к документации Google Calendar API

---

**Готово!** Теперь giga-agent может работать с Google Calendar через простую авторизацию Service Account.
