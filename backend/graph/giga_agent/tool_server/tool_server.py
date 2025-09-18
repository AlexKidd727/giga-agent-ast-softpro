import traceback
from contextlib import asynccontextmanager

from fastapi import FastAPI, Body
from langchain_gigachat.utils.function_calling import convert_to_gigachat_tool
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt.tool_node import _handle_tool_error, ToolNode
import gigachat.exceptions
from pydantic_core import ValidationError
from fastapi.responses import JSONResponse

from giga_agent.utils.env import load_project_env
from giga_agent.config import MCP_CONFIG, TOOLS, REPL_TOOLS, AGENT_MAP


async def get_gigachat_token_info() -> str:
    """Получение информации о токенах GigaChat"""
    try:
        import aiohttp
        import os
        
        # Получаем токен из переменных окружения
        credentials = os.getenv("MAIN_GIGACHAT_CREDENTIALS")
        if not credentials:
            return "❌ Токен GigaChat не найден в переменных окружения"
        
        # Декодируем credentials (base64)
        import base64
        decoded_credentials = base64.b64decode(credentials).decode('utf-8')
        client_id, client_secret = decoded_credentials.split(':')
        
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
                                return f"❌ Ошибка получения информации о токенах: {token_resp.status}"
                    else:
                        return "❌ Не удалось получить access token"
                else:
                    return f"❌ Ошибка авторизации: {resp.status}"
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
        if "quota" in error_msg.lower() or "limit" in error_msg.lower():
            additional_info = "\n\n💡 **Рекомендация:** Возможно, превышен лимит токенов."
        elif "unauthorized" in error_msg.lower() or "401" in error_msg:
            additional_info = "\n\n💡 **Рекомендация:** Проблема с авторизацией. Проверьте правильность токенов в переменных окружения."
        elif "422" in error_msg or "properties.state.properties" in error_msg:
            additional_info = "\n\n💡 **Рекомендация:** Ошибка формата запроса. Возможно, проблема с версией API или конфигурацией."
        
        return f"❌ **Ошибка GigaChat API:** {error_msg}\n\n{token_info}{additional_info}"
    else:
        # Для других ошибок используем стандартную обработку
        return _handle_tool_error(e, flag=flag)


def handle_gigachat_error(e: Exception, flag: bool = False) -> str:
    """Синхронная обработка ошибок GigaChat (для совместимости)"""
    if isinstance(e, gigachat.exceptions.ResponseError):
        error_msg = str(e)
        
        # Извлекаем информацию о токенах из ошибки
        token_info = ""
        if "quota" in error_msg.lower() or "limit" in error_msg.lower():
            token_info = "\n\n💡 **Информация о токенах:** Возможно, превышен лимит токенов. Проверьте остаток токенов в личном кабинете GigaChat."
        elif "unauthorized" in error_msg.lower() or "401" in error_msg:
            token_info = "\n\n💡 **Информация о токенах:** Проблема с авторизацией. Проверьте правильность токенов в переменных окружения."
        elif "422" in error_msg or "properties.state.properties" in error_msg:
            token_info = "\n\n💡 **Информация о токенах:** Ошибка формата запроса. Возможно, проблема с версией API или конфигурацией."
        
        return f"❌ **Ошибка GigaChat API:** {error_msg}{token_info}"
    else:
        # Для других ошибок используем стандартную обработку
        return _handle_tool_error(e, flag=flag)

tool_map = {}
repl_tool_map = {}
config = {}

load_project_env()


@asynccontextmanager
async def lifespan(app: FastAPI):
    client = MultiServerMCPClient(MCP_CONFIG)
    tools = TOOLS + await client.get_tools()
    config["tool_node"] = ToolNode(tools=tools)
    for tool in tools:
        tool_map[tool.name] = tool
    for tool in REPL_TOOLS:
        repl_tool_map[tool.__name__] = tool
    yield
    repl_tool_map.clear()
    tool_map.clear()
    config.clear()


app = FastAPI(lifespan=lifespan)


@app.post("/{tool_name}")
async def call_tool(tool_name: str, payload: dict = Body(...)):
    if tool_name in tool_map or tool_name in repl_tool_map:
        if tool_name in AGENT_MAP:
            return JSONResponse(
                status_code=500,
                content=f"Ты пытался вызвать '{tool_name}'. "
                f"Нельзя вызывать '{tool_name}' из кода! Вызывай их через function_call",
            )
        try:
            if tool_name in repl_tool_map:
                kwargs = payload.get("kwargs")
                return JSONResponse({"data": await repl_tool_map[tool_name](**kwargs)})
            tool = tool_map[tool_name]
            kwargs = payload.get("kwargs")
            state = payload.get("state")
            injected_args = config["tool_node"].inject_tool_args(
                {"name": tool.name, "args": kwargs, "id": "123"}, state, None
            )["args"]
            if tool.name == "python":
                injected_args["code"] = kwargs.get("code")
            try:
                tool._to_args_and_kwargs(injected_args, None)
            except ValidationError as e:
                content = handle_gigachat_error(e, flag=True)
                tool_schema = convert_to_gigachat_tool(tool)["function"]
                return JSONResponse(
                    status_code=500,
                    content=f"Ошибка в заполнении функции!\n{content}\nЗаполни параметры функции по следующей схеме: {tool_schema}",
                )
            data = await tool_map[tool_name].ainvoke(injected_args)
            return {"data": data}
        except Exception as e:
            traceback.print_exc()
            error_content = await handle_gigachat_error_async(e, flag=True)
            return JSONResponse(
                status_code=500, content=error_content
            )
    else:
        return JSONResponse(
            status_code=404, content=f"Tool with name {tool_name} not found!"
        )


@app.get("/tools")
async def get_tools():
    tools = []
    for tool in tool_map.values():
        tools.append(convert_to_gigachat_tool(tool)["function"])
    return tools
