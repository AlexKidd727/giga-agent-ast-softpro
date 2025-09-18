#!/usr/bin/env python3
"""
Финальный тест Tinkoff агента с реальным API
"""

import asyncio
import os
import sys
from pathlib import Path

# Добавляем путь к модулям
sys.path.append(str(Path(__file__).parent))

async def test_tinkoff_agent_real():
    """Тестируем Tinkoff агента с реальным API"""
    
    print("=== ФИНАЛЬНЫЙ ТЕСТ TINKOFF АГЕНТА ===\n")
    
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
        print("\n📝 Пример:")
        print("   set TINKOFF_TOKEN=your_token_here")
        print("   set TINKOFF_ACCOUNT_ID=your_account_id_here")
        return False
    
    print("\n2. Тест подключения к API:")
    try:
        from giga_agent.agents.tinkoff_agent.utils.client import get_tinkoff_client
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
    
    print("\n3. Тест поиска инструментов:")
    try:
        from giga_agent.agents.tinkoff_agent.nodes.instruments import search_instrument
        result = await search_instrument.ainvoke({"ticker": "SBER", "instrument_type": "shares"})
        print("   ✅ Поиск инструментов работает")
        print(f"   Результат: {result[:200]}...")
    except Exception as e:
        print(f"   ❌ Ошибка при поиске инструментов: {e}")
        return False
    
    print("\n4. Тест получения портфеля:")
    try:
        from giga_agent.agents.tinkoff_agent.nodes.portfolio import get_portfolio_summary
        result = await get_portfolio_summary.ainvoke({"user_id": "test_user"})
        print("   ✅ Получение портфеля работает")
        print(f"   Результат: {result[:200]}...")
    except Exception as e:
        print(f"   ❌ Ошибка при получении портфеля: {e}")
        return False
    
    print("\n5. Тест агента:")
    try:
        from giga_agent.agents.tinkoff_agent import tinkoff_agent
        result = await tinkoff_agent.ainvoke({"user_request": "покажи портфель", "user_id": "test_user"})
        print("   ✅ Агент работает")
        print(f"   Ответ: {result[:200]}...")
    except Exception as e:
        print(f"   ❌ Ошибка при тестировании агента: {e}")
        return False
    
    print("\n✅ ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!")
    print("\n🎉 TINKOFF АГЕНТ ГОТОВ К ИСПОЛЬЗОВАНИЮ!")
    return True

if __name__ == "__main__":
    print("Запуск финального теста Tinkoff агента...\n")
    
    success = asyncio.run(test_tinkoff_agent_real())
    
    if success:
        print("\n🚀 Агент готов к работе!")
        print("\n📋 Доступные команды:")
        print("   - Показать портфель")
        print("   - Найти инструмент по тикеру")
        print("   - Получить текущую цену")
        print("   - Разместить ордер")
        print("   - Просмотреть операции")
        print("   - И многое другое...")
    else:
        print("\n💥 ТЕСТЫ ЗАВЕРШЕНЫ С ОШИБКАМИ!")
        sys.exit(1)
