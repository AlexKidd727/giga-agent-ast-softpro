# Makefile для giga-agent

.PHONY: help test test-calendar test-unit test-integration install-test-deps clean

# Помощь
help:
	@echo "Доступные команды:"
	@echo "  make test              - Запустить все тесты"
	@echo "  make test-calendar     - Запустить тесты Google Calendar"
	@echo "  make test-unit         - Запустить unit тесты"
	@echo "  make test-integration  - Запустить интеграционные тесты"
	@echo "  make test-simple       - Запустить простой тест календаря"
	@echo "  make install-test-deps - Установить зависимости для тестов"
	@echo "  make clean             - Очистить временные файлы"

# Установка зависимостей для тестов
install-test-deps:
	pip install -r tests/requirements.txt

# Все тесты
test:
	pytest tests/ -v

# Тесты Google Calendar
test-calendar:
	pytest tests/test_calendar_events.py -v -m calendar

# Unit тесты
test-unit:
	pytest tests/ -v -m unit

# Интеграционные тесты
test-integration:
	pytest tests/ -v -m integration

# Простой тест календаря
test-simple:
	python test_calendar_simple.py

# Тесты с покрытием
test-coverage:
	pytest tests/ --cov=giga_agent --cov-report=html --cov-report=term-missing

# Очистка
clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf .pytest_cache/
	rm -rf htmlcov/
	rm -rf .coverage

# Запуск с Docker
test-docker:
	docker-compose exec langgraph-api pytest tests/ -v

# Тест календаря в Docker
test-calendar-docker:
	docker-compose exec langgraph-api python test_calendar_simple.py