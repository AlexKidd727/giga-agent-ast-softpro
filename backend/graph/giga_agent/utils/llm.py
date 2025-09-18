import os
import json
import logging
from typing import Dict, Optional, Any
from openai import OpenAI
from langchain.chat_models import init_chat_model
from langchain.embeddings import init_embeddings
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

logger = logging.getLogger(__name__)

from giga_agent.utils.env import load_project_env
from giga_agent.utils.gigachat_modes import get_gigachat_mode_manager

GIGACHAT_PROVIDER = "gigachat:"

load_project_env()


def get_agent_env(tag: str = None):
    if tag is None:
        return "GIGA_AGENT_LLM"
    else:
        return f"GIGA_AGENT_LLM_{tag.upper()}"


class OpenAIGigaChatWrapper:
    """Обертка для OpenAI клиента, имитирующая интерфейс LangChain"""
    
    def __init__(self, model: str, api_key: str, base_url: str, **kwargs):
        self.model = model
        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url
        )
        self._model_name = f"GigaChat/{model}"
        self._bound_kwargs = {}
        self._config = {}
    
    def invoke(self, messages, **kwargs):
        """Имитирует метод invoke из LangChain"""
        # Конвертируем сообщения в формат OpenAI
        openai_messages = self._convert_messages_to_openai(messages)
        
        # Объединяем kwargs с привязанными параметрами
        final_kwargs = {**self._bound_kwargs, **kwargs}
        
        # Добавляем инструменты если они привязаны
        if hasattr(self, '_tools') and self._tools:
            # Конвертируем инструменты в формат OpenAI
            tools = []
            for tool in self._tools:
                # Если это уже словарь (из tool_client.get_tools())
                if isinstance(tool, dict):
                    tool_def = {
                        "type": "function",
                        "function": tool
                    }
                    tools.append(tool_def)
                # Если это объект с атрибутами
                elif hasattr(tool, 'name') and hasattr(tool, 'description'):
                    tool_def = {
                        "type": "function",
                        "function": {
                            "name": tool.name,
                            "description": tool.description,
                        }
                    }
                    # Добавляем параметры если есть
                    if hasattr(tool, 'args_schema'):
                        tool_def["function"]["parameters"] = tool.args_schema.model_json_schema()
                    tools.append(tool_def)
            
            if tools:
                final_kwargs["tools"] = tools
                final_kwargs["tool_choice"] = "auto"
        
        # Логируем запрос для отладки
        print(f"🔍 OpenAI API запрос:")
        print(f"  Модель: {self._model_name}")
        print(f"  Сообщения: {len(openai_messages)}")
        print(f"  Инструменты: {len(final_kwargs.get('tools', []))}")
        if 'tools' in final_kwargs:
            for i, tool in enumerate(final_kwargs['tools']):
                print(f"    {i+1}. {tool.get('function', {}).get('name', 'unknown')}")
        
        response = self.client.chat.completions.create(
            model=self._model_name,
            messages=openai_messages,
            **final_kwargs
        )
        
        # Конвертируем ответ в формат LangChain если нужно
        return self._convert_response_to_langchain(response)
    
    def _convert_messages_to_openai(self, messages):
        """Конвертирует LangChain сообщения в формат OpenAI"""
        openai_messages = []
        system_messages = []
        
        # Если это строка
        if isinstance(messages, str):
            return [{"role": "user", "content": messages}]
        
        # Если это одно сообщение
        if not isinstance(messages, (list, tuple)):
            messages = [messages]
        
        for message in messages:
            # Если это уже словарь OpenAI
            if isinstance(message, dict):
                if message.get("role") == "system":
                    system_messages.append(message)
                else:
                    openai_messages.append(message)
                continue
            
            # Если это LangChain сообщение
            if hasattr(message, 'content'):
                role = "user"  # По умолчанию
                
                # Определяем роль по типу сообщения
                message_type = type(message).__name__.lower()
                if "system" in message_type:
                    role = "system"
                elif "assistant" in message_type:
                    role = "assistant"
                elif "human" in message_type:
                    role = "user"
                elif "ai" in message_type:
                    role = "assistant"
                
                # Создаем сообщение OpenAI
                openai_message = {
                    "role": role,
                    "content": message.content
                }
                
                # Добавляем tool_calls если есть
                if hasattr(message, 'tool_calls') and message.tool_calls:
                    openai_message["tool_calls"] = message.tool_calls
                
                # Добавляем tool_call_id если есть
                if hasattr(message, 'tool_call_id') and message.tool_call_id:
                    openai_message["tool_call_id"] = message.tool_call_id
                
                # Разделяем system и обычные сообщения
                if role == "system":
                    system_messages.append(openai_message)
                else:
                    openai_messages.append(openai_message)
            else:
                # Если не можем определить тип, пробуем как строку
                openai_messages.append({
                    "role": "user",
                    "content": str(message)
                })
        
        # System сообщения должны быть первыми
        return system_messages + openai_messages
    
    def _convert_response_to_langchain(self, response):
        """Конвертирует ответ OpenAI в формат LangChain"""
        # Если это не ответ OpenAI, возвращаем как есть
        if not hasattr(response, 'choices') or not response.choices:
            return response
        
        message = response.choices[0].message
        
        # Создаем настоящий AIMessage из LangChain
        if hasattr(message, 'tool_calls') and message.tool_calls:
            # Конвертируем tool_calls в формат LangChain
            tool_calls = []
            for tool_call in message.tool_calls:
                try:
                    # Парсим аргументы
                    args = json.loads(tool_call.function.arguments) if tool_call.function.arguments else {}
                except (json.JSONDecodeError, AttributeError):
                    args = {}
                
                tool_calls.append({
                    "name": tool_call.function.name,
                    "args": args,
                    "id": tool_call.id
                })
            
            return AIMessage(
                content=message.content or "",
                tool_calls=tool_calls
            )
        else:
            return AIMessage(
                content=message.content or ""
            )
    
    def _safe_serialize(self, obj: Any) -> Any:
        """Безопасная сериализация объектов для JSON"""
        try:
            # Пробуем сериализовать
            json.dumps(obj)
            return obj
        except (TypeError, ValueError):
            # Если не получается, конвертируем в строку
            if hasattr(obj, 'content'):
                return obj.content
            elif hasattr(obj, '__dict__'):
                return str(obj)
            else:
                return str(obj)
    
    def __call__(self, messages, **kwargs):
        """Поддерживает вызов как функции"""
        response = self.invoke(messages, **kwargs)
        # Возвращаем LangChain сообщение
        return response
    
    def bind(self, **kwargs):
        """Имитирует метод bind из LangChain - привязывает параметры"""
        # Создаем новую обертку с привязанными параметрами
        new_wrapper = OpenAIGigaChatWrapper(
            model=self.model,
            api_key=self.client.api_key,
            base_url=self.client.base_url
        )
        new_wrapper._bound_kwargs = {**self._bound_kwargs, **kwargs}
        new_wrapper._config = self._config.copy()
        
        # Копируем инструменты если есть
        if hasattr(self, '_tools'):
            new_wrapper._tools = self._tools
        if hasattr(self, '_parallel_tool_calls'):
            new_wrapper._parallel_tool_calls = self._parallel_tool_calls
        if hasattr(self, '_tool_kwargs'):
            new_wrapper._tool_kwargs = self._tool_kwargs.copy()
        
        return new_wrapper
    
    def with_config(self, tags=None, **config):
        """Имитирует метод with_config из LangChain"""
        # Создаем новую обертку с конфигурацией
        new_wrapper = OpenAIGigaChatWrapper(
            model=self.model,
            api_key=self.client.api_key,
            base_url=self.client.base_url
        )
        new_wrapper._bound_kwargs = self._bound_kwargs.copy()
        new_wrapper._config = {**self._config, **config}
        if tags:
            new_wrapper._config['tags'] = tags
        
        # Копируем инструменты если есть
        if hasattr(self, '_tools'):
            new_wrapper._tools = self._tools
        if hasattr(self, '_parallel_tool_calls'):
            new_wrapper._parallel_tool_calls = self._parallel_tool_calls
        if hasattr(self, '_tool_kwargs'):
            new_wrapper._tool_kwargs = self._tool_kwargs.copy()
        
        return new_wrapper
    
    def bind_tools(self, tools, parallel_tool_calls=False, **kwargs):
        """Имитирует метод bind_tools из LangChain"""
        # Создаем новую обертку с привязанными инструментами
        new_wrapper = OpenAIGigaChatWrapper(
            model=self.model,
            api_key=self.client.api_key,
            base_url=self.client.base_url
        )
        new_wrapper._bound_kwargs = self._bound_kwargs.copy()
        new_wrapper._config = self._config.copy()
        
        # Сохраняем инструменты и настройки
        new_wrapper._tools = tools
        new_wrapper._parallel_tool_calls = parallel_tool_calls
        new_wrapper._tool_kwargs = kwargs
        
        return new_wrapper


def load_gigachat(tag: str = None, is_main: bool = False):
    """Загружает GigaChat через OpenAI клиент"""
    llm_str = os.getenv(get_agent_env(tag))
    
    # Получаем настройки
    if is_main:
        api_key = os.getenv("MAIN_GIGACHAT_CREDENTIALS")
        base_url = os.getenv("MAIN_GIGACHAT_BASE_URL", "https://foundation-models.api.cloud.ru/v1")
    else:
        api_key = os.getenv("GIGACHAT_CREDENTIALS")
        base_url = os.getenv("GIGACHAT_BASE_URL", "https://foundation-models.api.cloud.ru/v1")
    
    # Получаем модель из переменной окружения
    original_model = llm_str[len(GIGACHAT_PROVIDER):]
    
    # Получаем менеджер режимов
    mode_manager = get_gigachat_mode_manager()
    
    # Определяем финальную модель в зависимости от режима
    model_name = mode_manager.get_model_name(original_model)
    
    # Создаем обертку OpenAI клиента
    return OpenAIGigaChatWrapper(
        model=model_name,
        api_key=api_key,
        base_url=base_url
    )


def load_gigachat_embeddings():
    """Заглушка для embeddings - пока не реализовано"""
    # TODO: Реализовать embeddings через OpenAI API если нужно
    raise NotImplementedError("Embeddings через OpenAI API пока не реализованы")


def is_llm_gigachat(tag: str = None):
    llm_str = os.getenv(get_agent_env(tag))
    return llm_str.startswith(GIGACHAT_PROVIDER)


# Singletons cache
_LLM_SINGLETONS: Dict[str, object] = {}
_EMBEDDINGS_SINGLETON: Optional[object] = None


def load_llm(tag: str = None, is_main: bool = False):
    env_key = get_agent_env(tag)
    singleton_key = env_key
    if is_main:
        singleton_key = "MAIN_" + singleton_key
    if singleton_key in _LLM_SINGLETONS:
        return _LLM_SINGLETONS[singleton_key]

    llm_str = os.getenv(env_key)
    if llm_str is None:
        raise RuntimeError(f"{env_key} is empty! Fill it with your model")

    if llm_str.startswith(GIGACHAT_PROVIDER):
        # Используем нашу обертку OpenAIGigaChatWrapper для совместимости
        try:
            from langchain_gigachat import ChatGigaChat
            llm = ChatGigaChat(
                model=llm_str[len(GIGACHAT_PROVIDER):],
                credentials=os.getenv("MAIN_GIGACHAT_CREDENTIALS" if is_main else "GIGACHAT_CREDENTIALS"),
                scope="GIGACHAT_API_PERS",
                verify_ssl_certs=False
            )
        except ImportError:
            # Fallback на нашу обертку если langchain_gigachat недоступен
            logger.warning("langchain_gigachat недоступен, используем OpenAIGigaChatWrapper")
            model_name = llm_str[len(GIGACHAT_PROVIDER):]
            api_key = os.getenv("MAIN_GIGACHAT_CREDENTIALS" if is_main else "GIGACHAT_CREDENTIALS")
            base_url = os.getenv("GIGACHAT_BASE_URL", "https://gigachat.devices.sberbank.ru/api/v1")
            llm = OpenAIGigaChatWrapper(
                model=model_name,
                api_key=api_key,
                base_url=base_url
            )
    else:
        llm = init_chat_model(llm_str)

    _LLM_SINGLETONS[singleton_key] = llm
    return llm


def load_embeddings():
    global _EMBEDDINGS_SINGLETON

    if _EMBEDDINGS_SINGLETON is not None:
        return _EMBEDDINGS_SINGLETON

    emb_str = os.getenv("GIGA_AGENT_EMBEDDINGS")
    if emb_str is None:
        raise RuntimeError("GIGA_AGENT_EMBEDDINGS is empty! Fill it with your model")

    if emb_str.startswith(GIGACHAT_PROVIDER):
        embeddings = load_gigachat_embeddings()
    else:
        embeddings = init_embeddings(emb_str)

    _EMBEDDINGS_SINGLETON = embeddings
    return embeddings


def is_llm_image_inline():
    llm_str = os.getenv("GIGA_AGENT_LLM")
    if llm_str is None:
        raise RuntimeError("GIGA_AGENT_LLM is empty! Fill it with your model")
    return llm_str.startswith(GIGACHAT_PROVIDER)