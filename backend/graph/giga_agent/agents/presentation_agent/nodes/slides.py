import asyncio
import os
import re

from langchain_core.runnables import (
    RunnableConfig,
    RunnableParallel,
    RunnablePassthrough,
)

from giga_agent.output_parsers.html_parser import HTMLParser
from giga_agent.agents.presentation_agent.config import PresentationState, llm
from giga_agent.agents.presentation_agent.prompts.ru import SLIDE_PROMPT

slide_sem = asyncio.Semaphore(4)

__location__ = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))

with open(os.path.join(__location__, "presentation.html")) as f:
    presentation_html = f.read()


async def generate_slide(messages):
    async with slide_sem:
        ch_2 = (
            SLIDE_PROMPT
            | llm
            | RunnableParallel({"message": RunnablePassthrough(), "html": HTMLParser()})
        ).with_retry()
        slide_resp = await ch_2.ainvoke({"messages": messages})
        html = slide_resp.get("html", "")
        reg = r",\s*"
        html = re.sub(
            r'data-background-gradient="linear-gradient\(([^)]*)\)"',
            lambda m: f'data-background-gradient="linear-gradient({re.sub(reg, ", ", m.group(1))})"',
            html,
        )
        return html


async def slides_node(state: PresentationState, config: RunnableConfig):
    slide_tasks = []
    uuid_pattern = (
        "^[0-9a-f]{8}-[0-9a-f]{4}-[0-5][0-9a-f]{3}-[089ab][0-9a-f]{3}-[0-9a-f]{12}$"
    )
    for idx, slide in enumerate(state["slides"]):
        user_message = f"Придумай {idx + 1} слайд '{slide.get('name')}'. Используй строго тот градиент, который указан в самом недавнем плане презентации! Всегда используй градиент типа 'to bottom'"
        if (idx + 1) in state["slide_map"]:
            images = state["slide_map"][(idx + 1)]
            for image in images:
                user_message += f"\nУ тебя доступно изображение '{image.get('name')}' — '{image.get('description')}'. Помни, что это изображение не для фона! Используй его как контент. Помни про то, что нужен class='img' в теге img!"
        if slide.get("graphs", []):
            for graph in slide.get("graphs", []):
                if not isinstance(graph, str):
                    continue
                if graph.startswith("graph:"):
                    user_message += f"\nИспользуй график: '{graph}'"
                elif re.match(uuid_pattern, graph):
                    user_message += f"\nИспользуй график: 'graph:{graph}'"
        slide_tasks.append(generate_slide(state["messages"] + [("user", user_message)]))
    slide_resps = await asyncio.gather(*slide_tasks)
    result = presentation_html.replace("<SECTIONS></SECTIONS>", "\n".join(slide_resps))
    return {"presentation_html": result}
