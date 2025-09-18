#!/usr/bin/env python3
"""
Скрипт для тестирования режимов GigaChat
"""
import os
import sys
sys.path.append('.')

from giga_agent.utils.gigachat_modes import get_gigachat_mode_manager, GigaChatMode
from giga_agent.utils.llm import load_gigachat


def test_modes():
    """Тестирует различные режимы GigaChat"""
    print("=== Тестирование режимов GigaChat ===\n")
    
    # Тест 1: Обычный режим
    print("1. Тестирование обычного режима:")
    os.environ["GIGACHAT_MODE"] = "normal"
    mode_manager = get_gigachat_mode_manager()
    print(f"   Режим: {mode_manager.get_mode().value}")
    print(f"   Модель: {mode_manager.get_model_name('GigaChat-2-Pro')}")
    print(f"   Это обычный режим: {mode_manager.is_normal_mode()}")
    print()
    
    # Тест 2: Мини режим
    print("2. Тестирование мини режима:")
    os.environ["GIGACHAT_MODE"] = "mini"
    mode_manager = get_gigachat_mode_manager()
    print(f"   Режим: {mode_manager.get_mode().value}")
    print(f"   Модель для LLM: {mode_manager.get_model_name('GigaChat-2-Pro')}")
    print(f"   Модель для API: mini")
    print(f"   Это мини режим: {mode_manager.is_mini_mode()}")
    print()
    
    # Тест 3: Быстрый режим
    print("3. Тестирование быстрого режима:")
    os.environ["GIGACHAT_MODE"] = "fast"
    mode_manager = get_gigachat_mode_manager()
    print(f"   Режим: {mode_manager.get_mode().value}")
    print(f"   Модель для LLM: {mode_manager.get_model_name('GigaChat-2-Pro')}")
    print(f"   Модель для API: lite")
    print(f"   Это быстрый режим: {mode_manager.is_fast_mode()}")
    print()
    
    # Тест 4: Модификация данных запроса
    print("4. Тестирование модификации данных запроса:")
    test_data = {
        "messages": [
            {"role": "system", "content": "Вы ассистент."},
            {"role": "user", "content": "Привет!"}
        ],
        "model": "GigaChat-2-Pro",
        "temperature": 1.0
    }
    
    for mode in ["normal", "mini", "fast"]:
        os.environ["GIGACHAT_MODE"] = mode
        mode_manager = get_gigachat_mode_manager()
        modified_data = mode_manager.modify_request_data(test_data.copy())
        print(f"   {mode.capitalize()} режим:")
        print(f"     Модель: {modified_data['model']}")
        print(f"     Температура: {modified_data.get('temperature', 'не задана')}")
        print(f"     Макс токены: {modified_data.get('max_tokens', 'не заданы')}")
        print()
    
    # Тест 5: Кастомные модификации
    print("5. Тестирование кастомных модификаций:")
    os.environ["GIGACHAT_MODE"] = "normal"
    os.environ["GIGACHAT_CUSTOM_MODEL"] = "GigaChat-2-Mini"
    os.environ["GIGACHAT_TEMPERATURE"] = "0.8"
    os.environ["GIGACHAT_MAX_TOKENS"] = "1500"
    
    mode_manager = get_gigachat_mode_manager()
    modified_data = mode_manager.modify_request_data(test_data.copy())
    print(f"   Кастомная модель: {modified_data['model']}")
    print(f"   Кастомная температура: {modified_data.get('temperature')}")
    print(f"   Кастомные макс токены: {modified_data.get('max_tokens')}")
    print()
    
    print("=== Тестирование завершено ===")


if __name__ == "__main__":
    test_modes()
