import asyncio
import functools
import json
import os
from typing import Any

import aiohttp
import requests
from pydantic import BaseModel

from giga_agent.utils.jupyter import JupyterClient


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
                json={"kwargs": kwargs, "state": self.state},
                timeout=600.0,
            ) as res:
                if res.status == 200:
                    data = (await res.json())["data"]
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
            data = response.json()["data"]
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
                    f"Tool method '{func.__name__}' accepts named keyword arguments only"
                )
            # имя инструмента — само имя метода
            tool_name = func.__name__
            return self.execute(tool_name, kwargs)

        return wrapper


if __name__ == "__main__":
    tool_client = ToolClient(base_url="http://127.0.0.1:8811")

    @tool_client.call_tool
    def predict_sentiments(**kwargs):
        pass

    async def main():
        # client = JupyterClient(
        #     base_url=os.getenv("JUPYTER_CLIENT_API", "http://127.0.0.1:9090")
        # )
        # tool_client.set_state({"kernel_id": (await client.start_kernel())["id"]})
        print(predict_sentiments(texts=["крутой товар"]))

    asyncio.run(main())
