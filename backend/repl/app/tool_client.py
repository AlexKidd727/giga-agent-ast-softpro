import asyncio
import functools
import json
from typing import Any

import aiohttp
import requests
from pydantic import BaseModel


class ToolExecuteException(Exception):
    pass


class ToolNotFoundException(Exception):
    pass


class ToolClient(BaseModel):
    base_url: str
    state: Any = {}

    def set_state(self, state):
        self.state = state

    async def aexecute(self, tool_name, kwargs):
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/{tool_name}",
                json=kwargs,
                timeout=600.0,
            ) as res:
                if res.status == 200:
                    data = (await res.json())['data']
                    try:
                        data = json.loads(data)
                    except Exception:
                        pass
                    return data
                elif res.status == 404:
                    raise ToolNotFoundException((await res.json()))
                else:
                    raise ToolExecuteException((await res.json()))

    def execute(self, tool_name, kwargs):
        url = f"{self.base_url}/{tool_name}"
        try:
            response = requests.post(
                url, json={"kwargs": kwargs, "state": self.state}, timeout=600.0
            )
        except requests.RequestException as e:
            # Ошибка сети или таймаут
            raise ToolExecuteException(str(e))

        if response.status_code == 200:
            data = response.json()['data']
            try:
                data = json.loads(data)
            except Exception:
                pass
            return data
        elif response.status_code == 404:
            # Инструмент не найден
            raise ToolNotFoundException(response.json())
        else:
            # Любая другая ошибка выполнения
            raise ToolExecuteException(response.json())

    async def get_tools(self):
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{self.base_url}/tools",
                timeout=600.0,
            ) as res:
                return await res.json()

    def call_tool(self, func):
        """
        Декоратор для методов ToolClient:
        - берёт имя функции как название инструмента,
        - собирает все именованные аргументы в dict,
        - вызывает self.execute(tool_name, kwargs) и возвращает результат.
        """

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if args:
                raise TypeError(
                    f"Tool method '{func.__name__}' принимает только именованные аргументы"
                )
            # имя инструмента — само имя метода
            tool_name = func.__name__
            return self.execute(tool_name, kwargs)

        return wrapper
