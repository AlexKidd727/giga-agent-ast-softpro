#!/usr/bin/env python3
"""
Тест Tinkoff агента
"""

import asyncio
import os
import sys
from pathlib import Path

# Добавляем путь к модулям
sys.path.append(str(Path(__file__).parent))

async def test_tinkoff_agent():
    """Тестируем Tinkoff агента"""
    
    print("=== ТЕСТ TINKOFF АГЕНТА ===\n")
    
    # Проверяем переменные окружения
    print("1. Проверка переменных окружения:")
    token = os.getenv("TINKOFF_TOKEN")
    account_id = os.getenv("TINKOFF_ACCOUNT_ID")
    sandbox = os.getenv("TINKOFF_SANDBOX", "true")
    
    print(f"   TINKOFF_TOKEN: {'✅ Установлен' if token else '❌ Не установлен'}")
    print(f"   TINKOFF_ACCOUNT_ID: {'✅ Установлен' if account_id else '❌ Не установлен'}")
    print(f"   TINKOFF_SANDBOX: {sandbox}")
    
    if not token or not account_id:
        print("\n❌ Необходимо установить переменные окружения:")
        print("   TINKOFF_TOKEN - токен API")
        print("   TINKOFF_ACCOUNT_ID - ID счета")
        return False
    
    print("\n2. Тест импорта модулей:")
    try:
        from giga_agent.agents.tinkoff_agent import tinkoff_agent
        print("   ✅ Импорт tinkoff_agent успешен")
    except Exception as e:
        print(f"   ❌ Ошибка импорта tinkoff_agent: {e}")
        return False
    
    try:
        from giga_agent.agents.tinkoff_agent.utils.client import get_tinkoff_client
        print("   ✅ Импорт client успешен")
    except Exception as e:
        print(f"   ❌ Ошибка импорта client: {e}")
        return False
    
    try:
        from giga_agent.agents.tinkoff_agent.utils.tinkoff_client import get_tinkoff_client as get_tinkoff_client_alt
        print("   ✅ Импорт tinkoff_client успешен")
    except Exception as e:
        print(f"   ❌ Ошибка импорта tinkoff_client: {e}")
        return False
    
    print("\n3. Тест подключения к API:")
    try:
        client = get_tinkoff_client()
        if client:
            connection_result = client.check_connection()
            if connection_result.get("success"):
                print("   ✅ Подключение к Tinkoff API успешно")
                print(f"   Sandbox режим: {connection_result.get('sandbox_mode')}")
                print(f"   Найден аккаунт: {connection_result.get('account_found')}")
                print(f"   Количество аккаунтов: {connection_result.get('accounts_count')}")
            else:
                print(f"   ❌ Ошибка подключения: {connection_result.get('error')}")
                return False
        else:
            print("   ❌ Не удалось создать клиент")
            return False
    except Exception as e:
        print(f"   ❌ Ошибка при тестировании подключения: {e}")
        return False
    
    print("\n4. Тест базовых функций агента:")
    try:
        # Тест простого запроса
        result = await tinkoff_agent("покажи портфель", "test_user")
        print("   ✅ Агент отвечает на запросы")
        print(f"   Ответ: {result[:100]}...")
    except Exception as e:
        print(f"   ❌ Ошибка при тестировании агента: {e}")
        return False
    
    print("\n5. Тест поиска инструментов:")
    try:
        from giga_agent.agents.tinkoff_agent.nodes.instruments import search_instrument
        result = await search_instrument("SBER", "shares")
        print("   ✅ Поиск инструментов работает")
        print(f"   Результат: {result[:100]}...")
    except Exception as e:
        print(f"   ❌ Ошибка при поиске инструментов: {e}")
        return False
    
    print("\n✅ ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!")
    return True

async def test_agent_functions():
    """Тестируем отдельные функции агента"""
    
    print("\n=== ТЕСТ ФУНКЦИЙ АГЕНТА ===\n")
    
    try:
        from giga_agent.agents.tinkoff_agent.nodes.portfolio import get_portfolio_summary
        from giga_agent.agents.tinkoff_agent.nodes.instruments import find_figi_by_ticker
        from giga_agent.agents.tinkoff_agent.nodes.operations import get_operations_today
        
        print("1. Тест получения сводки по портфелю:")
        result = await get_portfolio_summary()
        print(f"   Результат: {result[:150]}...")
        
        print("\n2. Тест поиска FIGI:")
        result = await find_figi_by_ticker("SBER")
        print(f"   Результат: {result[:150]}...")
        
        print("\n3. Тест получения операций за сегодня:")
        result = await get_operations_today()
        print(f"   Результат: {result[:150]}...")
        
        print("\n✅ ТЕСТЫ ФУНКЦИЙ ПРОЙДЕНЫ!")
        return True
        
    except Exception as e:
        print(f"\n❌ Ошибка при тестировании функций: {e}")
        return False

if __name__ == "__main__":
    print("Запуск тестов Tinkoff агента...\n")
    
    # Запускаем основные тесты
    success = asyncio.run(test_tinkoff_agent())
    
    if success:
        # Запускаем тесты функций
        asyncio.run(test_agent_functions())
        print("\n🎉 ВСЕ ТЕСТЫ ЗАВЕРШЕНЫ УСПЕШНО!")
    else:
        print("\n💥 ТЕСТЫ ЗАВЕРШЕНЫ С ОШИБКАМИ!")
        sys.exit(1)
