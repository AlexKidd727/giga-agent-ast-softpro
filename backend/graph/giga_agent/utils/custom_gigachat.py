"""
Кастомный GigaChat с возможностью модификации JSON перед отправкой
"""
import json
import os
import logging
from typing import Any, Dict, List, Optional, Union
from langchain_gigachat import GigaChat
from langchain_core.messages import BaseMessage
from langchain_core.outputs import LLMResult
from langchain_core.callbacks import CallbackManagerForLLMRun
from giga_agent.utils.gigachat_modes import get_gigachat_mode_manager
import httpx
from unittest.mock import patch

# Настройка логирования
logger = logging.getLogger(__name__)


class CustomGigaChat(GigaChat):
    """Кастомный GigaChat с возможностью модификации JSON перед отправкой"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Патчим HTTP клиент для перехвата запросов
        self._patch_http_client()
    
    def _patch_http_client(self):
        """Патчит HTTP клиент для перехвата запросов к GigaChat API"""
        original_post = httpx.Client.post
        original_async_post = httpx.AsyncClient.post
        
        def patched_post(self, url, *args, **kwargs):
            if "gigachat.devices.sberbank.ru" in str(url) or "api.giga.chat" in str(url):
                logger.info("🔍 CUSTOM GIGACHAT: Перехвачен HTTP POST запрос")
                if 'json' in kwargs:
                    logger.info(f"📥 Исходный JSON: {json.dumps(kwargs['json'], ensure_ascii=False, indent=2)}")
                    kwargs['json'] = self._modify_request_data(kwargs['json'])
                    logger.info(f"📤 Модифицированный JSON: {json.dumps(kwargs['json'], ensure_ascii=False, indent=2)}")
            return original_post(self, url, *args, **kwargs)
        
        async def patched_async_post(self, url, *args, **kwargs):
            if "gigachat.devices.sberbank.ru" in str(url) or "api.giga.chat" in str(url):
                logger.info("🔍 CUSTOM GIGACHAT: Перехвачен async HTTP POST запрос")
                if 'json' in kwargs:
                    logger.info(f"📥 Исходный JSON: {json.dumps(kwargs['json'], ensure_ascii=False, indent=2)}")
                    kwargs['json'] = self._modify_request_data(kwargs['json'])
                    logger.info(f"📤 Модифицированный JSON: {json.dumps(kwargs['json'], ensure_ascii=False, indent=2)}")
            return await original_async_post(self, url, *args, **kwargs)
        
        # Применяем патчи
        httpx.Client.post = patched_post
        httpx.AsyncClient.post = patched_async_post
    
    def _modify_request_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Модифицирует данные запроса перед отправкой к API
        
        Args:
            data: Исходные данные запроса
            
        Returns:
            Модифицированные данные запроса
        """
        logger.info("🚀 CUSTOM GIGACHAT: Начало модификации запроса")
        
        # Получаем менеджер режимов
        mode_manager = get_gigachat_mode_manager()
        logger.info(f"🎯 CUSTOM GIGACHAT: Текущий режим: {mode_manager.get_mode().value}")
        
        # Применяем модификации в зависимости от режима
        modified_data = mode_manager.modify_request_data(data)
        
        logger.info("✅ CUSTOM GIGACHAT: Модификация завершена")
        
        return modified_data
    
    def _call(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> str:
        """Переопределяем _call для модификации запроса"""
        # Вызываем родительский метод, но с модификацией
        return super()._call(messages, stop, run_manager, **kwargs)
    
    async def _acall(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> str:
        """Переопределяем _acall для модификации запроса"""
        # Вызываем родительский метод, но с модификацией
        return await super()._acall(messages, stop, run_manager, **kwargs)
    
    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> LLMResult:
        """Переопределяем _generate для модификации запроса"""
        # Вызываем родительский метод
        return super()._generate(messages, stop, run_manager, **kwargs)
    
    async def _agenerate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> LLMResult:
        """Переопределяем _agenerate для модификации запроса"""
        # Вызываем родительский метод
        return await super()._agenerate(messages, stop, run_manager, **kwargs)
