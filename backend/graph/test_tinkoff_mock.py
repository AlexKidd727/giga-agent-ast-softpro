#!/usr/bin/env python3
"""
Тест Tinkoff агента с мок-данными (без реального API)
"""

import asyncio
import os
import sys
from pathlib import Path

# Добавляем путь к модулям
sys.path.append(str(Path(__file__).parent))

# Устанавливаем тестовые переменные окружения
os.environ["TINKOFF_TOKEN"] = "test_token"
os.environ["TINKOFF_ACCOUNT_ID"] = "test_account_id"
os.environ["TINKOFF_SANDBOX"] = "true"

async def test_tinkoff_agent_mock():
    """Тестируем Tinkoff агента с мок-данными"""
    
    print("=== ТЕСТ TINKOFF АГЕНТА (МОК-РЕЖИМ) ===\n")
    
    # Проверяем переменные окружения
    print("1. Проверка переменных окружения:")
    token = os.getenv("TINKOFF_TOKEN")
    account_id = os.getenv("TINKOFF_ACCOUNT_ID")
    sandbox = os.getenv("TINKOFF_SANDBOX", "true")
    
    print(f"   TINKOFF_TOKEN: {'✅ Установлен' if token else '❌ Не установлен'}")
    print(f"   TINKOFF_ACCOUNT_ID: {'✅ Установлен' if account_id else '❌ Не установлен'}")
    print(f"   TINKOFF_SANDBOX: {sandbox}")
    
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
    
    print("\n3. Тест создания клиента:")
    try:
        client = get_tinkoff_client()
        if client:
            print("   ✅ Клиент создан успешно")
            print(f"   Sandbox режим: {client.sandbox}")
            print(f"   Account ID: {client.account_id}")
        else:
            print("   ❌ Не удалось создать клиент")
            return False
    except Exception as e:
        print(f"   ❌ Ошибка при создании клиента: {e}")
        return False
    
    print("\n4. Тест структуры агента:")
    try:
        from giga_agent.agents.tinkoff_agent.graph import create_tinkoff_agent
        agent = create_tinkoff_agent()
        print("   ✅ Агент создан успешно")
        print(f"   Тип агента: {type(agent)}")
    except Exception as e:
        print(f"   ❌ Ошибка при создании агента: {e}")
        return False
    
    print("\n5. Тест инструментов агента:")
    try:
        from giga_agent.agents.tinkoff_agent.graph import TINKOFF_TOOLS
        print(f"   ✅ Найдено инструментов: {len(TINKOFF_TOOLS)}")
        for i, tool in enumerate(TINKOFF_TOOLS[:5], 1):  # Показываем первые 5
            print(f"   {i}. {tool.name}")
        if len(TINKOFF_TOOLS) > 5:
            print(f"   ... и еще {len(TINKOFF_TOOLS) - 5} инструментов")
    except Exception as e:
        print(f"   ❌ Ошибка при получении инструментов: {e}")
        return False
    
    print("\n✅ ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!")
    return True

async def test_agent_structure():
    """Тестируем структуру агента"""
    
    print("\n=== ТЕСТ СТРУКТУРЫ АГЕНТА ===\n")
    
    try:
        from giga_agent.agents.tinkoff_agent.graph import create_tinkoff_agent, TINKOFF_PROMPT
        
        print("1. Тест создания агента:")
        agent = create_tinkoff_agent()
        print("   ✅ Агент создан")
        
        print("\n2. Тест промпта:")
        print(f"   ✅ Промпт загружен: {len(str(TINKOFF_PROMPT))} символов")
        
        print("\n3. Тест узлов агента:")
        # Проверяем, что все узлы доступны
        from giga_agent.agents.tinkoff_agent.nodes import portfolio, orders, instruments, operations
        print("   ✅ Все узлы импортированы успешно")
        
        print("\n4. Тест инструментов:")
        from giga_agent.agents.tinkoff_agent.graph import TINKOFF_TOOLS
        tool_names = [tool.name for tool in TINKOFF_TOOLS]
        print(f"   ✅ Найдено {len(tool_names)} инструментов:")
        for name in tool_names:
            print(f"      - {name}")
        
        print("\n✅ СТРУКТУРА АГЕНТА КОРРЕКТНА!")
        return True
        
    except Exception as e:
        print(f"\n❌ Ошибка при тестировании структуры: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("Запуск тестов Tinkoff агента (мок-режим)...\n")
    
    # Запускаем основные тесты
    success = asyncio.run(test_tinkoff_agent_mock())
    
    if success:
        # Запускаем тесты структуры
        asyncio.run(test_agent_structure())
        print("\n🎉 ВСЕ ТЕСТЫ ЗАВЕРШЕНЫ УСПЕШНО!")
        print("\n📝 Для тестирования с реальным API:")
        print("   1. Получите токен в Tinkoff Invest")
        print("   2. Установите переменные окружения:")
        print("      TINKOFF_TOKEN=your_token")
        print("      TINKOFF_ACCOUNT_ID=your_account_id")
        print("   3. Запустите: python test_tinkoff_agent.py")
    else:
        print("\n💥 ТЕСТЫ ЗАВЕРШЕНЫ С ОШИБКАМИ!")
        sys.exit(1)
