import copy
import json
import os
import re
import traceback
from datetime import datetime
from typing import Literal
from uuid import uuid4

from genson import SchemaBuilder

# Применяем HTTP патчер для перехвата запросов к GigaChat API
import logging
logger = logging.getLogger(__name__)
logger.info("🔧 TOOL_GRAPH: Импорт HTTP патчера...")
from giga_agent.utils.http_patcher import patch_httpx
logger.info("🔧 TOOL_GRAPH: Применение HTTP патчера...")
patch_httpx()
logger.info("🔧 TOOL_GRAPH: HTTP патчер применен!")

from langchain_core.messages import (
    AIMessage,
    ToolMessage,
)
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langgraph.graph import StateGraph
from langgraph.prebuilt.tool_node import _handle_tool_error, ToolNode
import gigachat.exceptions
from langgraph.store.base import BaseStore
from langgraph.types import interrupt

from giga_agent.config import (
    AgentState,
    REPL_TOOLS,
    SERVICE_TOOLS,
    AGENT_MAP,
    load_llm,
)
from giga_agent.prompts.few_shots import FEW_SHOTS_ORIGINAL, FEW_SHOTS_UPDATED
from giga_agent.prompts.main_prompt import SYSTEM_PROMPT
from giga_agent.repl_tools.utils import describe_repl_tool
from giga_agent.tool_server.tool_client import ToolClient
from giga_agent.utils.env import load_project_env
from giga_agent.utils.jupyter import JupyterClient
import re


def parse_function_calls_from_text(message):
    """Парсит вызовы функций из текста ответа LLM - ТОЛЬКО JSON формат"""
    content = message.content
    
    # Логируем в файл для отладки (Windows-совместимый путь)
    import tempfile
    import os
    log_dir = tempfile.gettempdir()
    log_file = os.path.join(log_dir, "parsing_debug.log")
    
    try:
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"🔍 ПАРСИНГ: Анализирую контент: {content[:200]}...\n")
    except Exception as e:
        print(f"Ошибка записи в лог: {e}")
    
    print(f"🔍 ПАРСИНГ: Анализирую контент: {content[:200]}...")
    
    # Проверяем, не является ли это результатом выполнения агента
    # Если в контенте есть признаки результата, не парсим
    result_indicators = [
        # Tinkoff агент результаты
        "Общая стоимость портфеля",
        "ПОЗИЦИИ В ПОРТФЕЛЕ",
        "FIGI:",
        "Доходность:",
        "Текущая цена:",
        "Итоговая стоимость:",
        "Ваш текущий портфель",
        "СВОДКА ПО ПОРТФЕЛЮ",
        "Действие: tinkoff_agent",
        
        # Calendar агент результаты
        "событие добавлено",
        "напоминание создано",
        "календарь обновлен",
        "Действие: calendar_agent",
        
        # Weather результаты
        "текущая погода",
        "температура",
        "влажность",
        "Действие: weather",
        
        # Общие индикаторы результатов
        "Результат выполнения инструмента",
        "Действие:",
        "✅",
        "❌",
        "⚠️"
    ]
    
    if any(indicator in content for indicator in result_indicators):
        print("🔍 ПАРСИНГ: Обнаружен результат выполнения агента, пропускаю парсинг")
        try:
            with open(log_file, "a", encoding="utf-8") as f:
                f.write("🔍 ПАРСИНГ: Обнаружен результат выполнения агента, пропускаю парсинг\n")
        except Exception as e:
            print(f"Ошибка записи в лог: {e}")
        return message
    
    # ТОЛЬКО JSON формат для вызова агентов
    # Ищем полный JSON объект с name и args
    json_patterns = [
        r'\{"name":\s*"(\w+_agent)",\s*"args":\s*\{[^}]*"user_request":\s*"([^"]+)"[^}]*"user_id":\s*"([^"]+)"[^}]*\}\}',
        r'\{"name":\s*"(\w+_agent)",\s*"args":\s*\{[^}]*"user_request":\s*"([^"]+)"[^}]*\}\}',
    ]
    
    tool_calls = []
    
    # Ищем JSON формат
    seen_calls = set()  # Для дедупликации
    
    for pattern in json_patterns:
        matches = re.findall(pattern, content)
        print(f"🔍 ПАРСИНГ: JSON паттерн найден {len(matches)} совпадений")
        for match in matches:
            if len(match) == 3:
                agent_name, user_request, user_id = match
                # Создаем ключ для дедупликации
                call_key = f"{agent_name}:{user_request}:{user_id}"
                if call_key not in seen_calls:
                    seen_calls.add(call_key)
                    tool_calls.append({
                        "name": agent_name,
                        "args": {
                            "user_request": user_request,
                            "user_id": user_id
                        },
                        "id": f"call_{len(tool_calls) + 1}"
                    })
                    print(f"🔍 ПАРСИНГ: Найден JSON вызов {agent_name} с user_request='{user_request}', user_id='{user_id}'")
                else:
                    print(f"🔍 ПАРСИНГ: Пропущен дублированный вызов {agent_name} с user_request='{user_request}'")
            elif len(match) == 2:
                agent_name, user_request = match
                # Создаем ключ для дедупликации
                call_key = f"{agent_name}:{user_request}:default_user"
                if call_key not in seen_calls:
                    seen_calls.add(call_key)
                    tool_calls.append({
                        "name": agent_name,
                        "args": {
                            "user_request": user_request,
                            "user_id": "default_user"
                        },
                        "id": f"call_{len(tool_calls) + 1}"
                    })
                    print(f"🔍 ПАРСИНГ: Найден JSON вызов {agent_name} с user_request='{user_request}'")
                else:
                    print(f"🔍 ПАРСИНГ: Пропущен дублированный вызов {agent_name} с user_request='{user_request}'")
    
    # Если не найдено в JSON формате, пытаемся извлечь из контекста
    if not tool_calls:
        print("🔍 ПАРСИНГ: JSON вызовы не найдены, анализирую контекст")
        
        # Ищем ключевые слова для определения агента и извлекаем запрос
        content_lower = content.lower()
        
        # Определяем агента по контексту
        agent_name = None
        if any(word in content_lower for word in ["tinkoff", "портфель", "акции", "операции", "купи", "продай", "график", "мечел", "sber", "газпром", "инвестиционный счет", "сбербанк"]):
            agent_name = "tinkoff_agent"
        elif any(word in content_lower for word in ["calendar", "календарь", "напоминание", "событие", "встреча"]):
            agent_name = "calendar_agent"
        elif any(word in content_lower for word in ["погода", "weather"]):
            agent_name = "weather"
        elif any(word in content_lower for word in ["поиск", "search", "найди"]):
            agent_name = "search"
        
        if agent_name:
            # Извлекаем основной запрос пользователя из контекста
            context_patterns = [
                r'Передать запрос агенту\s+\w+\s+для\s+(.+?)(?:\.|$)',
                r'вызвать\s+\w+\s+для\s+(.+?)(?:\.|$)',
                r'использовать\s+\w+\s+для\s+(.+?)(?:\.|$)',
                r'обратиться к\s+\w+\s+с\s+(.+?)(?:\.|$)',
                r'Передать запрос агенту\s+\w+\s+(.+?)(?:\.|$)',
                r'вызвать\s+\w+\s+(.+?)(?:\.|$)',
                r'использовать\s+\w+\s+(.+?)(?:\.|$)',
            ]
            
            user_request = None
            for pattern in context_patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                if matches:
                    user_request = matches[0].strip()
                    break
            
            # Если не нашли через паттерны, ищем в JSON-подобных структурах
            if not user_request:
                json_like_patterns = [
                    r'"user_request":\s*"([^"]+)"',
                    r"'user_request':\s*'([^']+)'",
                    r'user_request:\s*"([^"]+)"',
                    r'user_request:\s*\'([^\']+)\'',
                ]
                
                for pattern in json_like_patterns:
                    matches = re.findall(pattern, content)
                    if matches:
                        user_request = matches[0].strip()
                        break
            
            # Если все еще не нашли, берем весь контент как запрос
            if not user_request:
                clean_content = re.sub(r'(План:|Начинаю выполнение плана\.|Ожидаю подтверждение.*)', '', content, flags=re.IGNORECASE)
                clean_content = re.sub(r'<[^>]+>', '', clean_content)  # Убираем HTML теги
                clean_content = re.sub(r'\{[^}]*\}', '', clean_content)  # Убираем JSON-подобные структуры
                user_request = clean_content.strip()
            
            if user_request and len(user_request) > 5:  # Минимальная длина запроса
                # Создаем ключ для дедупликации
                call_key = f"{agent_name}:{user_request}:default_user"
                if call_key not in seen_calls:
                    seen_calls.add(call_key)
                    tool_calls.append({
                        "name": agent_name,
                        "args": {
                            "user_request": user_request,
                            "user_id": "default_user"
                        },
                        "id": f"call_{len(tool_calls) + 1}"
                    })
                    print(f"🔍 ПАРСИНГ: Найден контекстный вызов {agent_name} с user_request='{user_request}'")
                else:
                    print(f"🔍 ПАРСИНГ: Пропущен дублированный контекстный вызов {agent_name} с user_request='{user_request}'")
    
    # Если найдены вызовы функций, создаем новое сообщение с tool_calls
    if tool_calls:
        print(f"🔍 ПАРСИНГ: Найдено {len(tool_calls)} вызовов функций, создаю AIMessage с tool_calls")
        
        # Логируем найденные вызовы
        try:
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(f"🔍 ПАРСИНГ: Найдено {len(tool_calls)} вызовов функций\n")
                for i, call in enumerate(tool_calls):
                    f.write(f"  {i+1}. {call['name']}({call['args']})\n")
        except Exception as e:
            print(f"Ошибка записи в лог: {e}")
        
        # Удаляем JSON вызовы из контента
        clean_content = content
        for pattern in json_patterns:
            clean_content = re.sub(pattern, '', clean_content)
        clean_content = clean_content.strip()
        
        # Создаем новое сообщение с tool_calls
        from langchain_core.messages import AIMessage
        result_message = AIMessage(
            content=clean_content,
            tool_calls=tool_calls
        )
        
        # Логируем результат
        try:
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(f"🔍 ПАРСИНГ: Создано AIMessage с {len(tool_calls)} tool_calls\n")
        except Exception as e:
            print(f"Ошибка записи в лог: {e}")
            
        return result_message
    
    # Если вызовов функций не найдено, возвращаем оригинальное сообщение
    print("🔍 ПАРСИНГ: Вызовы функций не найдены, возвращаю оригинальное сообщение")
    try:
        with open(log_file, "a", encoding="utf-8") as f:
            f.write("🔍 ПАРСИНГ: Вызовы функций не найдены, возвращаю оригинальное сообщение\n")
    except Exception as e:
        print(f"Ошибка записи в лог: {e}")
    
    return message


async def get_gigachat_token_info() -> str:
    """Получение информации о токенах GigaChat"""
    try:
        import aiohttp
        import os
        
        # Получаем токен из переменных окружения (пробуем разные варианты)
        credentials = os.getenv("MAIN_GIGACHAT_CREDENTIALS") or os.getenv("GIGACHAT_CREDENTIALS")
        if not credentials:
            return "❌ Токен GigaChat не найден в переменных окружения. Проверьте переменные MAIN_GIGACHAT_CREDENTIALS или GIGACHAT_CREDENTIALS."
        
        # Декодируем credentials (base64)
        import base64
        try:
            decoded_credentials = base64.b64decode(credentials).decode('utf-8')
            client_id, client_secret = decoded_credentials.split(':')
        except Exception as decode_error:
            return f"❌ Ошибка декодирования токена: {str(decode_error)}"
        
        # Получаем access token
        auth_url = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
        auth_data = {
            "scope": "GIGACHAT_API_PERS"
        }
        auth_headers = {
            "Authorization": f"Basic {credentials}",
            "Content-Type": "application/x-www-form-urlencoded"
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(auth_url, data=auth_data, headers=auth_headers) as resp:
                if resp.status == 200:
                    auth_response = await resp.json()
                    access_token = auth_response.get("access_token")
                    
                    if access_token:
                        # Запрашиваем информацию о токенах
                        token_url = "https://gigachat.devices.sberbank.ru/api/v1/token"
                        token_headers = {
                            "Authorization": f"Bearer {access_token}"
                        }
                        
                        async with session.get(token_url, headers=token_headers) as token_resp:
                            if token_resp.status == 200:
                                token_data = await token_resp.json()
                                return f"📊 **Информация о токенах:**\n" \
                                       f"• Лимит токенов: {token_data.get('token_limit', 'N/A')}\n" \
                                       f"• Использовано: {token_data.get('used_tokens', 'N/A')}\n" \
                                       f"• Остаток: {token_data.get('remaining_tokens', 'N/A')}"
                            else:
                                token_error_text = await token_resp.text()
                                return f"❌ Ошибка получения информации о токенах: {token_resp.status} - {token_error_text}"
                    else:
                        return "❌ Не удалось получить access token из ответа авторизации"
                else:
                    auth_error_text = await resp.text()
                    return f"❌ Ошибка авторизации: {resp.status} - {auth_error_text}"
    except Exception as e:
        return f"❌ Ошибка при получении информации о токенах: {str(e)}"


async def handle_gigachat_error_async(e: Exception, flag: bool = False) -> str:
    """Асинхронная обработка ошибок GigaChat с информацией о токенах"""
    if isinstance(e, gigachat.exceptions.ResponseError):
        error_msg = str(e)
        
        # Получаем актуальную информацию о токенах
        token_info = await get_gigachat_token_info()
        
        # Добавляем дополнительную информацию в зависимости от типа ошибки
        additional_info = ""
        if "402" in error_msg or "payment required" in error_msg.lower():
            additional_info = "\n\n💡 **Рекомендация:** У вас закончились токены или превышен лимит оплаты. Пополните баланс в личном кабинете GigaChat."
        elif "quota" in error_msg.lower() or "limit" in error_msg.lower():
            additional_info = "\n\n💡 **Рекомендация:** Возможно, превышен лимит токенов."
        elif "unauthorized" in error_msg.lower() or "401" in error_msg:
            additional_info = "\n\n💡 **Рекомендация:** Проблема с авторизацией. Проверьте правильность токенов в переменных окружения."
        elif "422" in error_msg or "properties.state.properties" in error_msg:
            additional_info = "\n\n💡 **Рекомендация:** Ошибка формата запроса. Возможно, проблема с версией API или конфигурацией."
        
        # Формируем основное сообщение с рекомендацией на первом месте
        main_message = f"❌ **Ошибка GigaChat API**\n\n{additional_info}"
        
        # Создаем детальную информацию в раскрывающемся блоке
        details = f"**Детали ошибки:**\n{error_msg}\n\n{token_info}"
        
        return f"{main_message}\n\n<details>\n<summary>🔍 Показать детали ошибки</summary>\n\n{details}\n</details>"
    else:
        # Для других ошибок используем стандартную обработку
        return _handle_tool_error(e, flag=flag)


def handle_gigachat_error(e: Exception, flag: bool = False) -> str:
    """Синхронная обработка ошибок GigaChat (для совместимости)"""
    if isinstance(e, gigachat.exceptions.ResponseError):
        error_msg = str(e)
        
        # Извлекаем информацию о токенах из ошибки
        token_info = ""
        if "402" in error_msg or "payment required" in error_msg.lower():
            token_info = "\n\n💡 **Информация о токенах:** У вас закончились токены или превышен лимит оплаты. Пополните баланс в личном кабинете GigaChat."
        elif "quota" in error_msg.lower() or "limit" in error_msg.lower():
            token_info = "\n\n💡 **Информация о токенах:** Возможно, превышен лимит токенов. Проверьте остаток токенов в личном кабинете GigaChat."
        elif "unauthorized" in error_msg.lower() or "401" in error_msg:
            token_info = "\n\n💡 **Информация о токенах:** Проблема с авторизацией. Проверьте правильность токенов в переменных окружения."
        elif "422" in error_msg or "properties.state.properties" in error_msg:
            token_info = "\n\n💡 **Информация о токенах:** Ошибка формата запроса. Возможно, проблема с версией API или конфигурацией."
        
        # Формируем основное сообщение с рекомендацией на первом месте
        main_message = f"❌ **Ошибка GigaChat API**\n\n{token_info}"
        
        # Создаем детальную информацию в раскрывающемся блоке
        details = f"**Детали ошибки:**\n{error_msg}"
        
        return f"{main_message}\n\n<details>\n<summary>🔍 Показать детали ошибки</summary>\n\n{details}\n</details>"
    else:
        # Для других ошибок используем стандартную обработку
        return _handle_tool_error(e, flag=flag)
from giga_agent.utils.lang import LANG
from giga_agent.utils.python import prepend_code

load_project_env()

llm = load_llm(is_main=True)


def generate_repl_tools_description():
    repl_tools = []
    for repl_tool in REPL_TOOLS:
        repl_tools.append(describe_repl_tool(repl_tool))
    service_tools = [tool.name for tool in SERVICE_TOOLS]
    repl_tools = "\n".join(repl_tools)
    return f"""В коде есть дополнительные функции:
```
{repl_tools}
```
Также ты можешь вызвать из кода следующие функции: {service_tools}. Аргументы и описания этих функций описаны в твоих функциях!
Вызывай эти методы, только через именованные агрументы"""


prompt = ChatPromptTemplate.from_messages(
    [
        ("system", SYSTEM_PROMPT),
    ]
    + (
        FEW_SHOTS_ORIGINAL
        if os.getenv("REPL_FROM_MESSAGE", "1") == "1"
        else FEW_SHOTS_UPDATED
    )
    + [MessagesPlaceholder("messages", optional=True)]
).partial(repl_inner_tools=generate_repl_tools_description(), language=LANG)


def generate_user_info(state: AgentState):
    lang = ""
    if not LANG.startswith("ru"):
        lang = f"\nВыбранный язык пользователя: {LANG}\n"
    return f"<user_info>\nТекущая дата: {datetime.today().strftime('%d.%m.%Y %H:%M')}{lang}</user_info>"


def get_code_arg(message):
    regex = r"```python(.+?)```"
    matches = re.findall(regex, message, re.DOTALL)
    if matches:
        return "\n".join(matches).strip()


client = JupyterClient(
    base_url=os.getenv("JUPYTER_CLIENT_API", "http://127.0.0.1:9090")
)


async def agent(state: AgentState):
    # Логируем вызов функции agent (Windows-совместимый путь)
    import tempfile
    import os
    log_dir = tempfile.gettempdir()
    log_file = os.path.join(log_dir, "agent_debug.log")
    
    try:
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"🔍 AGENT: Функция agent вызвана\n")
    except Exception as e:
        print(f"Ошибка записи в лог агента: {e}")
    
    tool_client = ToolClient(
        base_url=os.getenv("TOOL_CLIENT_API", "http://127.0.0.1:9091")
    )
    kernel_id = state.get("kernel_id")
    tools = state.get("tools")
    file_ids = []
    if not kernel_id:
        kernel_id = (await client.start_kernel())["id"]
        await client.execute(kernel_id, "function_results = []")
    if not tools:
        tools = await tool_client.get_tools()
    ch = (prompt | llm.bind_tools(tools, parallel_tool_calls=False)).with_retry()
    if state["messages"][-1].type == "human":
        user_input = state["messages"][-1].content
        # Безопасная проверка additional_kwargs
        if hasattr(state["messages"][-1], 'additional_kwargs'):
            files = state["messages"][-1].additional_kwargs.get("files", [])
        else:
            files = []
        file_prompt = []
        for idx, file in enumerate(files):
            file_prompt.append(
                f"""Файл ![](graph:{idx})\nЗагружен по пути: '{file['path']}'"""
            )
            if "file_id" in file:
                file_prompt[
                    -1
                ] += f"\nФайл является изображением его id: '{file['file_id']}'"
                file_ids.append(file["file_id"])
        file_prompt = (
            "<files_data>" + "\n----\n".join(file_prompt) + "</files_data>"
            if len(file_prompt)
            else ""
        )
        # Безопасная проверка additional_kwargs для selected
        if hasattr(state["messages"][-1], 'additional_kwargs'):
            selected = state["messages"][-1].additional_kwargs.get("selected", {})
        else:
            selected = {}
        selected_items = []
        for key, value in selected.items():
            selected_items.append(f"""![{value}](graph:{key})""")
        selected_prompt = ""
        if selected_items:
            selected_items = "\n".join(selected_items)
            selected_prompt = (
                f"Пользователь указал на следующие вложения: \n{selected_items}"
            )
        state["messages"][
            -1
        ].content = f"<task>{user_input}</task> Активно планируй и следуй своему плану! Действуй по простым шагам!{generate_user_info(state)}\n{file_prompt}\n{selected_prompt}\nСледующий шаг: "
    
    try:
        message = await ch.ainvoke({"messages": state["messages"]})
        
        # Логируем получение ответа от LLM
        try:
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(f"🔍 AGENT: Получен ответ от LLM: {message.content[:200]}...\n")
        except Exception as e:
            print(f"Ошибка записи в лог агента: {e}")
        
        # Парсим ответ LLM и извлекаем вызовы функций
        parsed_message = parse_function_calls_from_text(message)
        
        # Логируем результат парсинга
        try:
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(f"🔍 AGENT: Результат парсинга - has tool_calls: {hasattr(parsed_message, 'tool_calls') and bool(parsed_message.tool_calls)}\n")
                if hasattr(parsed_message, 'tool_calls') and parsed_message.tool_calls:
                    f.write(f"🔍 AGENT: Количество tool_calls: {len(parsed_message.tool_calls)}\n")
        except Exception as e:
            print(f"Ошибка записи в лог агента: {e}")
        
        # Безопасная работа с additional_kwargs
        if hasattr(parsed_message, 'additional_kwargs'):
            parsed_message.additional_kwargs.pop("function_call", None)
            parsed_message.additional_kwargs["rendered"] = True
        return {
            "messages": [state["messages"][-1], parsed_message],
            "kernel_id": kernel_id,
            "tools": tools,
            "file_ids": file_ids,
        }
    except Exception as e:
        # Обработка ошибок основного агента (например, ошибки GigaChat API)
        error_content = await handle_gigachat_error_async(e, flag=True)
        error_message = AIMessage(content=error_content)
        return {
            "messages": [state["messages"][-1], error_message],
            "kernel_id": kernel_id,
            "tools": tools,
            "file_ids": file_ids,
        }


async def tool_call(
    state: AgentState,
    store: BaseStore,
):
    tool_client = ToolClient(
        base_url=os.getenv("TOOL_CLIENT_API", "http://127.0.0.1:9091")
    )
    # Безопасная проверка tool_calls
    last_message = state["messages"][-1]
    if not hasattr(last_message, 'tool_calls') or not last_message.tool_calls:
        raise ValueError("No tool_calls found in the last message")
    action = copy.deepcopy(last_message.tool_calls[0])
    value = interrupt({"type": "approve"})
    if value.get("type") == "comment":
        return {
            "messages": ToolMessage(
                tool_call_id=action.get("id", str(uuid4())),
                content=json.dumps(
                    {
                        "message": f'Пользователь отменил выполнение инструмента. Комментарий: "{value.get("message")}"'
                    },
                    ensure_ascii=False,
                ),
            )
        }
    
    # Если пользователь не отменил, продолжаем выполнение
    tool_call_index = state.get("tool_call_index", -1)
    if action.get("name") == "python":
        if os.getenv("REPL_FROM_MESSAGE", "1") == "1":
            action["args"]["code"] = get_code_arg(state["messages"][-1].content)
        else:
            # На случай если гига отправить в аргумент ```python(.+)``` строку
            code_arg = get_code_arg(action["args"].get("code"))
            if code_arg:
                action["args"]["code"] = code_arg
        if "code" not in action["args"] or not action["args"]["code"]:
            return {
                "messages": ToolMessage(
                    tool_call_id=action.get("id", str(uuid4())),
                    content=json.dumps(
                        {"message": "Напиши код в своем сообщении!"},
                        ensure_ascii=False,
                    ),
                )
            }
        action["args"]["code"] = prepend_code(action["args"]["code"], state)
    file_ids = []
    try:
        state_ = copy.deepcopy(state)
        state_.pop("messages")
        tool_client.set_state(state_)
        if action.get("name") not in AGENT_MAP:
            result = await tool_client.aexecute(action.get("name"), action.get("args"))
        else:
            tool_node = ToolNode(tools=list(AGENT_MAP.values()))
            injected_args = tool_node.inject_tool_args(
                {"name": action.get("name"), "args": action.get("args"), "id": "123"},
                state,
                None,
            )["args"]
            result = await AGENT_MAP[action.get("name")].ainvoke(injected_args)
        tool_call_index += 1
        try:
            result = json.loads(result)
        except Exception as e:
            pass
        if result:
            add_data = {
                "data": result,
                "message": f"Результат функции сохранен в переменную `function_results[{tool_call_index}]['data']` ",
            }
            await client.execute(
                state.get("kernel_id"), f"function_results.append({repr(add_data)})"
            )
            if (
                len(json.dumps(result, ensure_ascii=False)) > 10000 * 4
                and action.get("name") not in AGENT_MAP
            ):
                schema = SchemaBuilder()
                schema.add_object(obj=add_data.pop("data"))
                add_data[
                    "message"
                ] += f"Результат функции вышел слишком длинным изучи результат функции в переменной с помощью python. Схема данных:\n"
                add_data["schema"] = schema.to_schema()
            if action.get("name") == "get_urls":
                add_data["message"] += result.pop("attention")
            elif action.get("name") == "search":
                # Улучшаем обработку результатов поиска для лучшего понимания модели
                try:
                    if "data" in result and len(result["data"]) > 0:
                        search_data = result["data"][0]
                        if "results" in search_data and len(search_data["results"]) > 0:
                            # Извлекаем основную информацию из результатов поиска
                            main_result = search_data["results"][0]
                            summary = f"Найдена информация: {main_result.get('title', 'Без названия')}\n"
                            summary += f"Содержание: {main_result.get('content', 'Нет описания')}\n"
                            if len(search_data["results"]) > 1:
                                summary += f"Найдено {len(search_data['results'])} результатов поиска.\n"
                            add_data["message"] += f"\n\nКраткое изложение результатов поиска:\n{summary}"
                        else:
                            add_data["message"] += "\n\nРезультаты поиска не найдены."
                    else:
                        add_data["message"] += "\n\nДанные поиска недоступны."
                except Exception as search_error:
                    add_data["message"] += f"\n\nОшибка обработки результатов поиска: {str(search_error)}"
            elif action.get("name") == "python":
                # Для python инструмента используем результат как есть
                add_data = result
        else:
            add_data = result
        tool_attachments = []
        if "giga_attachments" in result:
            add_data = result
            attachments = result.pop("giga_attachments")
            file_ids = [attachment["file_id"] for attachment in attachments]
            for attachment in attachments:
                if attachment["type"] == "text/html":
                    await store.aput(
                        ("html",),
                        attachment["file_id"],
                        attachment,
                        ttl=None,
                    )
                elif attachment["type"] == "audio/mp3":
                    await store.aput(
                        ("audio",),
                        attachment["file_id"],
                        attachment,
                        ttl=None,
                    )
                else:
                    await store.aput(
                        ("attachments",),
                        attachment["file_id"],
                        attachment,
                        ttl=None,
                    )

                tool_attachments.append(
                    {
                        "type": attachment["type"],
                        "file_id": attachment["file_id"],
                    }
                )
        message = ToolMessage(
            tool_call_id=action.get("id", str(uuid4())),
            content=json.dumps(add_data, ensure_ascii=False),
            additional_kwargs={"tool_attachments": tool_attachments},
        )
    except Exception as e:
        traceback.print_exc()
        error_content = await handle_gigachat_error_async(e, flag=True)
        message = ToolMessage(
            tool_call_id=action.get("id", str(uuid4())),
            content=error_content,
        )
        tool_call_index = action.get("index", 0)

    return {
        "messages": [message],
        "tool_call_index": tool_call_index,
        "file_ids": file_ids,
    }


def router(state: AgentState) -> Literal["tool_call", "__end__"]:
    # Безопасная проверка tool_calls
    last_message = state["messages"][-1]
    if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
        return "tool_call"
    else:
        return "__end__"


workflow = StateGraph(AgentState)
workflow.add_node(agent)
workflow.add_node(tool_call)
workflow.add_edge("__start__", "agent")
workflow.add_conditional_edges("agent", router)
workflow.add_edge("tool_call", "agent")


graph = workflow.compile()
