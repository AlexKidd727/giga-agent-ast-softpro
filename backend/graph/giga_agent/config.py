import os
from operator import add
from typing import TypedDict, Annotated, List

from langchain_core.messages import AnyMessage
from langgraph.graph import add_messages

# Применяем HTTP патчер для перехвата запросов к GigaChat API
import logging
logger = logging.getLogger(__name__)
logger.info("🔧 CONFIG: Импорт HTTP патчера...")
from giga_agent.utils.http_patcher import patch_httpx
logger.info("🔧 CONFIG: Применение HTTP патчера...")
patch_httpx()
logger.info("🔧 CONFIG: HTTP патчер применен!")

from giga_agent.repl_tools.llm import summarize
from giga_agent.repl_tools.sentiment import predict_sentiments, get_embeddings
from giga_agent.tools.another import (
    search,
    ask_about_image,
    gen_image,
)
from giga_agent.tools.github import (
    get_workflow_runs,
    list_pull_requests,
    get_pull_request,
)
from giga_agent.tools.repl import shell
from giga_agent.tools.scraper import get_urls
from giga_agent.tools.vk import vk_get_posts, vk_get_comments, vk_get_last_comments
from giga_agent.tools.weather import weather

from giga_agent.agents.landing_agent.graph import create_landing
from giga_agent.agents.lean_canvas import lean_canvas
from giga_agent.agents.meme_agent.graph import create_meme
from giga_agent.agents.podcast.graph import podcast_generate
from giga_agent.agents.presentation_agent.graph import generate_presentation
from giga_agent.agents.gis_agent.graph import city_explore
from giga_agent.agents.calendar_agent.graph import calendar_agent
from giga_agent.agents.pc_agent.graph import pc_agent
from giga_agent.agents.tinkoff_agent.graph import tinkoff_agent
from giga_agent.utils.env import load_project_env
from giga_agent.utils.llm import load_llm

BASEDIR = os.path.abspath(os.path.dirname(__file__))

load_project_env()


class AgentState(TypedDict):  # noqa: D101
    messages: Annotated[list[AnyMessage], add_messages]
    file_ids: Annotated[List[str], add]
    kernel_id: str
    tool_call_index: int
    tools: list


llm = load_llm()

if os.getenv("REPL_FROM_MESSAGE", "1") == "1":
    from giga_agent.tools.repl.message_tool import python
else:
    from giga_agent.tools.repl.args_tool import python


MCP_CONFIG = {}

TOOLS_REQUIRED_ENVS = {
    gen_image.name: ["IMAGE_GEN_NAME"],
    get_urls.name: ["TAVILY_API_KEY"],
    search.name: ["TAVILY_API_KEY"],
    vk_get_posts.name: ["VK_TOKEN"],
    vk_get_comments.name: ["VK_TOKEN"],
    vk_get_last_comments.name: ["VK_TOKEN"],
    get_workflow_runs.name: ["GITHUB_PERSONAL_ACCESS_TOKEN"],
    list_pull_requests.name: ["GITHUB_PERSONAL_ACCESS_TOKEN"],
    get_pull_request.name: ["GITHUB_PERSONAL_ACCESS_TOKEN"],
}

# Переменные окружения для агентов
AGENTS_REQUIRED_ENVS = {
    lean_canvas.name: [],
    generate_presentation.name: ["IMAGE_GEN_NAME"],
    create_landing.name: ["IMAGE_GEN_NAME"],
    podcast_generate.name: ["SALUTE_SPEECH"],
    create_meme.name: ["IMAGE_GEN_NAME"],
    city_explore.name: ["TWOGIS_TOKEN"],
    calendar_agent.name: ["GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET"],
    pc_agent.name: [],
    tinkoff_agent.name: ["TINKOFF_TOKEN"],
}


def has_required_envs(tool) -> bool:
    """Проверяет, что для `tool` установлены все обязательные переменные окружения.

    Если тул не указан в `TOOLS_REQUIRED_ENVS`, считаем, что у него нет обязательных
    переменных окружения и включаем его.
    """
    required_env_names = TOOLS_REQUIRED_ENVS.get(tool.name)
    if required_env_names is None:
        return True
    for env_name in required_env_names:
        if not os.getenv(env_name):
            return False
    return True


def has_required_envs_for_agent(agent) -> bool:
    """Проверяет, что для `agent` установлены все обязательные переменные окружения.

    Если агент не указан в `AGENTS_REQUIRED_ENVS`, считаем, что у него нет обязательных
    переменных окружения и включаем его.
    """
    required_env_names = AGENTS_REQUIRED_ENVS.get(agent.name)
    if required_env_names is None:
        return True
    for env_name in required_env_names:
        if not os.getenv(env_name):
            return False
    return True


def filter_tools_by_env(tools: list) -> list:
    """Возвращает список тулов, прошедших проверку обязательных env переменных."""
    return [tool for tool in tools if has_required_envs(tool)]


def filter_agents_by_env(agents: list) -> list:
    """Возвращает список агентов, прошедших проверку обязательных env переменных."""
    return [agent for agent in agents if has_required_envs_for_agent(agent)]


SERVICE_TOOLS = [
    weather,
    # VK TOOLS
    vk_get_posts,
    vk_get_comments,
    vk_get_last_comments,
    # GITHUB TOOLS
    get_workflow_runs,
    list_pull_requests,
    get_pull_request,
]

AGENTS = filter_agents_by_env([
    lean_canvas,
    generate_presentation,
    create_landing,
    podcast_generate,
    create_meme,
    city_explore,
    calendar_agent,
    pc_agent,
    tinkoff_agent,
])

# Инструменты, которые не являются агентами
SIMPLE_TOOLS = [
    ask_about_image,
    gen_image,
    get_urls,
    search,
]

TOOLS = filter_tools_by_env(
    [
        # REPL
        python,
        shell,
    ]
    + SIMPLE_TOOLS
    + SERVICE_TOOLS
    + AGENTS  # Добавляем агентов к списку инструментов
)

REPL_TOOLS = [predict_sentiments, summarize, get_embeddings]

AGENT_MAP = {agent.name: agent for agent in AGENTS}
