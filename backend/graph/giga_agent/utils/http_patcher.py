"""
Патчер для перехвата HTTP запросов к GigaChat API
"""
import json
import logging
import httpx
from typing import Any, Dict
from giga_agent.utils.gigachat_modes import get_gigachat_mode_manager

logger = logging.getLogger(__name__)

# Сохраняем оригинальные методы
_original_httpx_post = None
_original_httpx_async_post = None


def patch_httpx():
    """Патчит httpx для перехвата запросов к GigaChat API"""
    global _original_httpx_post, _original_httpx_async_post
    
    if _original_httpx_post is not None:
        logger.info("🔧 HTTP патчер уже применен")
        return
    
    logger.info("🔧 Применение HTTP патчера для GigaChat API")
    
    # Сохраняем оригинальные методы
    _original_httpx_post = httpx.Client.post
    _original_httpx_async_post = httpx.AsyncClient.post
    
    def patched_post(self, url, *args, **kwargs):
        if "gigachat.devices.sberbank.ru" in str(url) or "api.giga.chat" in str(url):
            logger.info("🔍 HTTP ПАТЧЕР: Перехвачен HTTP POST запрос к GigaChat")
            if 'json' in kwargs:
                logger.info(f"📥 Исходный JSON: {json.dumps(kwargs['json'], ensure_ascii=False, indent=2)}")
                kwargs['json'] = modify_gigachat_request(kwargs['json'])
                logger.info(f"📤 Модифицированный JSON: {json.dumps(kwargs['json'], ensure_ascii=False, indent=2)}")
        return _original_httpx_post(self, url, *args, **kwargs)
    
    async def patched_async_post(self, url, *args, **kwargs):
        if "gigachat.devices.sberbank.ru" in str(url) or "api.giga.chat" in str(url):
            logger.info("🔍 HTTP ПАТЧЕР: Перехвачен async HTTP POST запрос к GigaChat")
            if 'json' in kwargs:
                logger.info(f"📥 Исходный JSON: {json.dumps(kwargs['json'], ensure_ascii=False, indent=2)}")
                kwargs['json'] = modify_gigachat_request(kwargs['json'])
                logger.info(f"📤 Модифицированный JSON: {json.dumps(kwargs['json'], ensure_ascii=False, indent=2)}")
        return await _original_httpx_async_post(self, url, *args, **kwargs)
    
    # Применяем патчи
    httpx.Client.post = patched_post
    httpx.AsyncClient.post = patched_async_post
    
    logger.info("✅ HTTP патчер применен успешно")


def modify_gigachat_request(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Модифицирует данные запроса к GigaChat API
    
    Args:
        data: Исходные данные запроса
        
    Returns:
        Модифицированные данные запроса
    """
    logger.info("🚀 HTTP ПАТЧЕР: Начало модификации запроса")
    
    # Получаем менеджер режимов
    mode_manager = get_gigachat_mode_manager()
    logger.info(f"🎯 HTTP ПАТЧЕР: Текущий режим: {mode_manager.get_mode().value}")
    
    # Применяем модификации в зависимости от режима
    modified_data = mode_manager.modify_request_data(data)
    
    logger.info("✅ HTTP ПАТЧЕР: Модификация завершена")
    
    return modified_data


def unpatch_httpx():
    """Убирает патчи httpx"""
    global _original_httpx_post, _original_httpx_async_post
    
    if _original_httpx_post is None:
        return
    
    logger.info("🔧 Удаление HTTP патчера")
    
    # Восстанавливаем оригинальные методы
    httpx.Client.post = _original_httpx_post
    httpx.AsyncClient.post = _original_httpx_async_post
    
    _original_httpx_post = None
    _original_httpx_async_post = None
    
    logger.info("✅ HTTP патчер удален")
