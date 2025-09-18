import asyncio

import aiohttp
from pydantic import BaseModel


class KernelNotFoundException(Exception):
    pass


class JupyterClient(BaseModel):
    base_url: str

    async def execute(self, kernel_id, code):
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/code",
                json={"kernel_id": kernel_id, "script": code},
                timeout=60.0,
            ) as res:
                if res.status == 200:
                    data = await res.json()
                    return data
                elif res.status == 404:
                    raise KernelNotFoundException()
                else:
                    raise Exception(f"Error {res.status}: {res.reason}")

    async def start_kernel(self):
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/start",
                timeout=60.0,
            ) as res:
                if res.status == 200:
                    return await res.json()
                else:
                    raise Exception(f"Error {res.status}: {res.reason}")

    async def shutdown_kernel(self, kernel_id):
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/shutdown",
                json={"kernel_id": kernel_id},
                timeout=60.0,
            ) as res:
                if res.status == 200:
                    return await res.json()
                elif res.status == 404:
                    raise KernelNotFoundException()
                else:
                    raise Exception(f"Error {res.status}: {res.reason}")

    async def upload_file(self, file):
        async with aiohttp.ClientSession() as session:
            form = aiohttp.FormData()
            # Ожидаем кортеж (filename, bytes/IO). Иные варианты добавляем как есть
            try:
                if isinstance(file, tuple) and len(file) == 2:
                    filename, content = file
                    form.add_field("file", content, filename=str(filename))
                else:
                    form.add_field("file", file)
            except Exception:
                form.add_field("file", file)

            async with session.post(
                f"{self.base_url}/upload", data=form, timeout=60.0
            ) as res:
                if res.status == 200:
                    return await res.json()
                else:
                    raise Exception(f"Error {res.status}: {res.reason}")


if __name__ == "__main__":

    async def main():
        script = """
import pandas as pd
import numpy as np
import plotly.express as px

# Читаем CSV файл
df = pd.read_csv('files/moscow_flats_dataset.csv')

# Проверяем первые строки
print(df.head())

# Получаем общую информацию о структуре данных
print(df.info())

# Статистика по числовым признакам
print(df.describe())

# Строим гистограмму распределения цен
fig_price_hist = px.histogram(df, x='price', nbins=50, title='Распределение цен на квартиры')
fig_price_hist.show()

# Диаграмма рассеяния площади vs цена
fig_scatter_area_price = px.scatter(df, x='area', y='price', color='rooms', title='Площадь против цены квартир')
fig_scatter_area_price.show()
        """
        client = JupyterClient(base_url="http://127.0.0.1:9090")
        kernel_id = (await client.start_kernel())["id"]
        response = await client.execute(kernel_id, script)
        print(response)

    asyncio.run(main())
