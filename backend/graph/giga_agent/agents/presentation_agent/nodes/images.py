import asyncio
import base64
import re

from langchain_core.output_parsers import JsonOutputParser
from langchain_core.runnables import (
    RunnableConfig,
    RunnableParallel,
    RunnablePassthrough,
)
from giga_agent.agents.presentation_agent.config import PresentationState, llm
from giga_agent.agents.presentation_agent.prompts.ru import IMAGE_PROMPT
from giga_agent.generators.image import load_image_gen


async def image_node(state: PresentationState, config: RunnableConfig):
    slides_for_images = []
    uuid_pattern = (
        "^[0-9a-f]{8}-[0-9a-f]{4}-[0-5][0-9a-f]{3}-[089ab][0-9a-f]{3}-[0-9a-f]{12}$"
    )
    for idx, slide in enumerate(state["slides"]):
        if not slide.get("graphs"):
            slides_for_images.append(f"{idx + 1}. {slide.get('name')}")
        else:
            graph_not_valid = True
            for graph in slide["graphs"]:
                if graph.startswith("graph:") and graph_not_valid:
                    graph_not_valid = False
                    break
                elif re.match(uuid_pattern, graph):
                    graph_not_valid = False
                    break
            if graph_not_valid:
                slides_for_images.append(f"{idx + 1}. {slide.get('name')}")
    slides_text = "\n".join(slides_for_images)
    img_chain = (
        IMAGE_PROMPT
        | llm
        | RunnableParallel(
            {"message": RunnablePassthrough(), "json": JsonOutputParser()}
        )
    ).with_retry()
    img_resp = await img_chain.ainvoke(
        {
            "messages": state["messages"][-2:]
            + [
                (
                    "user",
                    f"Придумай список изображений для следующих слайдов: {slides_text}. Ты можешь придумывать не для каждого слайда изображения, а только там где считаешь нужным. Помни, что графики мы будем брать исходя из переписки с пользователем выше! Тебе нужно сгенерировать описание изображения для: предметов, интерьеров, ландшафтов, людей и т.д. все, что может относится к презентации! Инфографика не нужна! Изображения нужны только в тех слайдах где нет инфографики!",
                ),
            ]
        }
    )
    images = img_resp["json"]["images"]
    if config["configurable"].get("print_messages", False):
        img_resp["message"].pretty_print()
    generator = load_image_gen()
    await generator.init()
    tasks = [
        generator.generate_image(i["description"], i["width"], i["height"])
        for i in images
    ]
    images_data = await asyncio.gather(*tasks, return_exceptions=True)
    slide_map = {}
    images_base_64 = state.get("images_base_64", {})
    for i, b in zip(images, images_data):
        if isinstance(b, Exception):
            continue
        slide_map.setdefault(i["slide_index"], []).append(i)
        images_base_64[i["name"]] = b
        if config["configurable"].get("save_files", False):
            with open(i["name"], "wb") as f:
                await asyncio.to_thread(f.write, base64.b64decode(b))
    return {"slide_map": slide_map, "images_base_64": images_base_64}
