"""
Управление режимами GigaChat
"""
import os
import json
import logging
from typing import Dict, Any, Optional
from enum import Enum

# Настройка логирования
logger = logging.getLogger(__name__)


class GigaChatMode(Enum):
    """Режимы работы GigaChat"""
    NORMAL = "normal"      # Обычный режим (GigaChat-2-Pro)
    MINI = "mini"          # Мини режим (GigaChat-2-Mini)
    FAST = "fast"          # Быстрый режим (GigaChat-2-Lite)


class GigaChatModeManager:
    """Менеджер режимов GigaChat"""
    
    def __init__(self):
        self._mode = self._get_mode_from_env()
        self._custom_modifications = self._get_custom_modifications()
    
    def _get_mode_from_env(self) -> GigaChatMode:
        """Получает режим из переменных окружения"""
        mode_str = os.getenv("GIGACHAT_MODE", "normal").lower()
        
        # Поддержка старых переменных для обратной совместимости
        if os.getenv("FORCE_GIGACHAT_MINI", "false").lower() == "true":
            mode_str = "mini"
        
        try:
            return GigaChatMode(mode_str)
        except ValueError:
            print(f"Неизвестный режим GigaChat: {mode_str}. Используется режим 'normal'")
            return GigaChatMode.NORMAL
    
    def _get_custom_modifications(self) -> Dict[str, Any]:
        """Получает кастомные модификации из переменных окружения"""
        modifications = {}
        
        # Модификации модели
        if os.getenv("GIGACHAT_CUSTOM_MODEL"):
            modifications["model"] = os.getenv("GIGACHAT_CUSTOM_MODEL")
        
        # Модификации параметров генерации
        if os.getenv("GIGACHAT_TEMPERATURE"):
            try:
                modifications["temperature"] = float(os.getenv("GIGACHAT_TEMPERATURE"))
            except ValueError:
                pass
        
        if os.getenv("GIGACHAT_MAX_TOKENS"):
            try:
                modifications["max_tokens"] = int(os.getenv("GIGACHAT_MAX_TOKENS"))
            except ValueError:
                pass
        
        if os.getenv("GIGACHAT_TOP_P"):
            try:
                modifications["top_p"] = float(os.getenv("GIGACHAT_TOP_P"))
            except ValueError:
                pass
        
        return modifications
    
    def get_model_name(self, original_model: str) -> str:
        """Возвращает имя модели в зависимости от режима"""
        if self._mode == GigaChatMode.MINI:
            return "mini"  # Официальное API название
        elif self._mode == GigaChatMode.FAST:
            return "lite"  # Официальное API название
        else:
            return original_model
    
    def modify_request_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Модифицирует данные запроса в зависимости от режима"""
        logger.info("=" * 80)
        logger.info("🔧 МОДИФИКАЦИЯ JSON ДЛЯ GIGACHAT API")
        logger.info("=" * 80)
        
        # Логируем исходные данные
        logger.info(f"📥 ИСХОДНЫЕ ДАННЫЕ:")
        logger.info(f"   Режим: {self._mode.value}")
        logger.info(f"   Исходный JSON: {json.dumps(data, ensure_ascii=False, indent=2)}")
        
        # Создаем копию данных
        modified_data = data.copy()
        
        # Применяем модификации режима
        if self._mode == GigaChatMode.MINI:
            logger.info(f"🔄 ПРИМЕНЕНИЕ MINI РЕЖИМА:")
            logger.info(f"   Исходная модель: {data.get('model', 'не указана')}")
            
            modified_data["model"] = "mini"  # Официальное API название для GigaChat-Mini
            logger.info(f"   Новая модель: {modified_data['model']}")
            
            # Для мини режима можно добавить оптимизации
            original_temp = modified_data.get("temperature")
            original_tokens = modified_data.get("max_tokens")
            
            modified_data.setdefault("temperature", 0.7)
            modified_data.setdefault("max_tokens", 1000)
            
            logger.info(f"   Температура: {original_temp} → {modified_data['temperature']}")
            logger.info(f"   Макс токены: {original_tokens} → {modified_data['max_tokens']}")
        
        elif self._mode == GigaChatMode.FAST:
            logger.info(f"🔄 ПРИМЕНЕНИЕ FAST РЕЖИМА:")
            logger.info(f"   Исходная модель: {data.get('model', 'не указана')}")
            
            modified_data["model"] = "lite"  # Официальное API название
            logger.info(f"   Новая модель: {modified_data['model']}")
            
            # Для быстрого режима можно добавить оптимизации
            original_temp = modified_data.get("temperature")
            original_tokens = modified_data.get("max_tokens")
            
            modified_data.setdefault("temperature", 0.5)
            modified_data.setdefault("max_tokens", 500)
            
            logger.info(f"   Температура: {original_temp} → {modified_data['temperature']}")
            logger.info(f"   Макс токены: {original_tokens} → {modified_data['max_tokens']}")
        
        else:
            logger.info(f"🔄 ОБЫЧНЫЙ РЕЖИМ - модификации не применяются")
        
        # Применяем кастомные модификации
        if self._custom_modifications:
            logger.info(f"🔧 ПРИМЕНЕНИЕ КАСТОМНЫХ МОДИФИКАЦИЙ:")
            logger.info(f"   Кастомные параметры: {json.dumps(self._custom_modifications, ensure_ascii=False, indent=2)}")
            modified_data.update(self._custom_modifications)
        else:
            logger.info(f"🔧 КАСТОМНЫЕ МОДИФИКАЦИИ: отсутствуют")
        
        # Логируем финальный результат
        logger.info(f"📤 ФИНАЛЬНЫЙ JSON:")
        logger.info(f"   {json.dumps(modified_data, ensure_ascii=False, indent=2)}")
        
        # Сравнение изменений
        changes = []
        for key, value in modified_data.items():
            if key not in data or data[key] != value:
                changes.append(f"   {key}: {data.get(key, 'не указано')} → {value}")
        
        if changes:
            logger.info(f"📊 ИЗМЕНЕНИЯ:")
            for change in changes:
                logger.info(change)
        else:
            logger.info(f"📊 ИЗМЕНЕНИЯ: отсутствуют")
        
        logger.info("=" * 80)
        
        return modified_data
    
    def get_mode(self) -> GigaChatMode:
        """Возвращает текущий режим"""
        return self._mode
    
    def set_mode(self, mode: GigaChatMode):
        """Устанавливает режим"""
        self._mode = mode
    
    def is_mini_mode(self) -> bool:
        """Проверяет, активен ли мини режим"""
        return self._mode == GigaChatMode.MINI
    
    def is_fast_mode(self) -> bool:
        """Проверяет, активен ли быстрый режим"""
        return self._mode == GigaChatMode.FAST
    
    def is_normal_mode(self) -> bool:
        """Проверяет, активен ли обычный режим"""
        return self._mode == GigaChatMode.NORMAL


# Глобальный экземпляр менеджера режимов
mode_manager = GigaChatModeManager()


def get_gigachat_mode_manager() -> GigaChatModeManager:
    """Возвращает глобальный менеджер режимов"""
    return mode_manager


def activate_mini_mode():
    """Активирует мини режим"""
    mode_manager.set_mode(GigaChatMode.MINI)


def activate_fast_mode():
    """Активирует быстрый режим"""
    mode_manager.set_mode(GigaChatMode.FAST)


def activate_normal_mode():
    """Активирует обычный режим"""
    mode_manager.set_mode(GigaChatMode.NORMAL)
