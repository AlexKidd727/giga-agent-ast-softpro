"""
Граф Google Calendar Agent (Service Account)
"""

import logging
from typing import Annotated, TypedDict
from datetime import datetime

from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, ToolMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langgraph.prebuilt import InjectedState
from langgraph.constants import START, END
from langgraph.graph import StateGraph
from langgraph.graph.ui import push_ui_message

from giga_agent.agents.calendar_agent.nodes.simple_events import (
    simple_create_event, simple_list_events, simple_get_available_slots, 
    simple_delete_event, simple_calendar_status
)

logger = logging.getLogger(__name__)

# Инструменты календаря (Service Account)
CALENDAR_TOOLS = [
    simple_create_event,
    simple_list_events,
    simple_get_available_slots,
    simple_delete_event,
    simple_calendar_status,
]

@tool
async def calendar_agent(
    user_request: str,
    user_id: str = "default_user",
    state: Annotated[dict, InjectedState] = None
):
    """
    Агент для работы с Google Calendar через Service Account
    
    Обрабатывает запросы пользователя связанные с календарем:
    - Просмотр событий и расписания
    - Создание событий
    - Проверка статуса календаря
    - Получение свободных слотов
    
    Args:
        user_request: Запрос пользователя (например, "показать события", "создать событие")
        user_id: Идентификатор пользователя (необязательно)
    """
    
    try:
        user_input = user_request.lower()
        
        # Команды работы с событиями
        if any(phrase in user_input for phrase in ["показать события", "мои встречи", "расписание", "календарь на", "что запланировано", "события на", "месяц вперед", "на месяц"]):
            # Определяем количество дней для показа
            days_ahead = 30  # по умолчанию месяц
            if "неделя" in user_input or "неделю" in user_input:
                days_ahead = 7
            elif "день" in user_input or "дня" in user_input:
                days_ahead = 1
            elif "месяц" in user_input or "месяца" in user_input:
                days_ahead = 30
            
            result = await simple_list_events.ainvoke({"days_ahead": days_ahead})
            return result
            
        elif any(phrase in user_input for phrase in ["создать событие", "создать встречу", "добавить в календарь", "запланировать", "создай событие", "добавь событие", "добавь встречу"]):
            # Пытаемся извлечь информацию о событии из запроса
            from datetime import datetime, timedelta
            import re
            
            # Извлекаем название события
            title = "Событие"
            if '"' in user_request:
                # Ищем текст в кавычках
                title_match = re.search(r'"([^"]*)"', user_request)
                if title_match:
                    title = title_match.group(1)
            elif "названием" in user_input:
                # Ищем после слова "названием"
                title_match = re.search(r'названием\s+"([^"]*)"', user_input)
                if title_match:
                    title = title_match.group(1)
            
            # Определяем дату и время
            start_datetime = None
            end_datetime = None
            
            # Проверяем "сегодня"
            if "сегодня" in user_input:
                today = datetime.now()
                date_str = today.strftime("%d.%m.%Y")
                
                # Ищем время
                time_match = re.search(r'(\d{1,2}):(\d{2})', user_input)
                if time_match:
                    hour = int(time_match.group(1))
                    minute = int(time_match.group(2))
                    start_datetime = f"{date_str} {hour:02d}:{minute:02d}"
                    
                    # Конец события через час
                    end_hour = hour + 1
                    if end_hour >= 24:
                        end_hour = 0
                        end_date = today + timedelta(days=1)
                        end_date_str = end_date.strftime("%d.%m.%Y")
                    else:
                        end_date_str = date_str
                    end_datetime = f"{end_date_str} {end_hour:02d}:{minute:02d}"
            
            # Проверяем "завтра"
            elif "завтра" in user_input:
                tomorrow = datetime.now() + timedelta(days=1)
                date_str = tomorrow.strftime("%d.%m.%Y")
                
                # Ищем время
                time_match = re.search(r'(\d{1,2}):(\d{2})', user_input)
                if time_match:
                    hour = int(time_match.group(1))
                    minute = int(time_match.group(2))
                    start_datetime = f"{date_str} {hour:02d}:{minute:02d}"
                    
                    # Конец события через час
                    end_hour = hour + 1
                    if end_hour >= 24:
                        end_hour = 0
                        end_date = tomorrow + timedelta(days=1)
                        end_date_str = end_date.strftime("%d.%m.%Y")
                    else:
                        end_date_str = date_str
                    end_datetime = f"{end_date_str} {end_hour:02d}:{minute:02d}"
            
            # Проверяем конкретную дату
            date_match = re.search(r'(\d{1,2})\.(\d{1,2})\.(\d{4})', user_input)
            if date_match and not start_datetime:
                day = int(date_match.group(1))
                month = int(date_match.group(2))
                year = int(date_match.group(3))
                date_str = f"{day:02d}.{month:02d}.{year}"
                
                # Ищем время
                time_match = re.search(r'(\d{1,2}):(\d{2})', user_input)
                if time_match:
                    hour = int(time_match.group(1))
                    minute = int(time_match.group(2))
                    start_datetime = f"{date_str} {hour:02d}:{minute:02d}"
                    
                    # Конец события через час
                    end_hour = hour + 1
                    if end_hour >= 24:
                        end_hour = 0
                        from datetime import date
                        event_date = date(year, month, day)
                        end_date = event_date + timedelta(days=1)
                        end_date_str = end_date.strftime("%d.%m.%Y")
                    else:
                        end_date_str = date_str
                    end_datetime = f"{end_date_str} {end_hour:02d}:{minute:02d}"
            
            # Если удалось извлечь все параметры, создаем событие
            if start_datetime and end_datetime:
                try:
                    result = await simple_create_event.ainvoke({
                        "title": title,
                        "start_datetime": start_datetime,
                        "end_datetime": end_datetime,
                        "description": f"Событие создано через GigaChat Agent",
                        "user_id": user_id
                    })
                    return result
                except Exception as e:
                    logger.error(f"Ошибка создания события: {e}")
                    return f"❌ Ошибка создания события: {str(e)}"
            else:
                return """📋 **Создание события**

Для создания события используйте инструмент simple_create_event с параметрами:
• title: Название события
• start_datetime: Дата и время начала в формате "дд.мм.гггг чч:мм"
• end_datetime: Дата и время окончания в формате "дд.мм.гггг чч:мм"
• description: Описание (необязательно)
• user_id: Ваш ID пользователя

Пример: создать встречу "Совещание" на завтра 15:00-16:00"""
            
        elif any(phrase in user_input for phrase in ["свободные слоты", "доступное время", "когда свободен", "свободное время"]):
            # Извлекаем дату из запроса
            date = None
            for word in user_input.split():
                if len(word) == 10 and word.count('-') == 2:  # формат YYYY-MM-DD
                    date = word
                    break
                elif len(word) == 10 and word.count('.') == 2:  # формат DD.MM.YYYY
                    try:
                        from datetime import datetime
                        date_obj = datetime.strptime(word, "%d.%m.%Y")
                        date = date_obj.strftime("%Y-%m-%d")
                        break
                    except:
                        pass
            
            if not date:
                return "❌ **Укажите дату**\n\nПример: 'показать свободные слоты на 2025-01-20' или 'свободное время на 20.01.2025'"
            
            result = await simple_get_available_slots.ainvoke({"date": date})
            return result
            
        elif any(phrase in user_input for phrase in ["статус календар", "проверить календарь", "подключен ли календарь", "календарь подключен"]):
            result = await simple_calendar_status.ainvoke({})
            return result
            
        elif any(phrase in user_input for phrase in ["удалить событие", "удали событие", "отменить событие"]):
            return """🗑️ **Удаление события**

Для удаления события используйте инструмент simple_delete_event с параметрами:
• event_id: ID события для удаления
• user_id: Ваш ID пользователя

Сначала получите список событий, чтобы найти ID нужного события."""
            
        else:
            return """📅 **Google Calendar Agent (Service Account)**

Доступные команды:
• "показать события" - показать список событий
• "показать события на месяц" - события на месяц вперед
• "показать события на неделю" - события на неделю
• "создать событие" - создать новое событие
• "свободные слоты на [дата]" - показать доступное время
• "статус календаря" - проверить подключение

Примеры:
• "покажи что у меня запланировано на месяц вперед"
• "свободные слоты на 20.01.2025"
• "создай встречу на завтра в 15:00" """
            
    except Exception as e:
        logger.error(f"Ошибка в calendar_agent: {e}")
        return f"❌ Ошибка обработки запроса: {str(e)}"

# Создаем промпт для агента
CALENDAR_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """Ты - эксперт по работе с Google Calendar через Service Account.

Твоя задача - помочь пользователю с управлением календарем:
- Показывать события и расписание
- Создавать новые события
- Проверять статус подключения
- Показывать свободные временные слоты

Используй только простые инструменты (simple_*), так как OAuth не настроен.
Всегда отвечай на русском языке и будь дружелюбным."""),
    MessagesPlaceholder("messages"),
])

# Создаем граф
def create_calendar_graph():
    """Создание графа calendar_agent"""
    
    # Определяем состояние
    class CalendarAgentState(TypedDict):
        messages: Annotated[list, "Список сообщений"]
        user_request: str
        user_id: str
        current_step: str
        error: str

    # Создаем граф
    workflow = StateGraph(CalendarAgentState)
    
    # Добавляем узлы
    workflow.add_node("calendar_agent", calendar_agent)
    
    # Добавляем ребра
    workflow.add_edge(START, "calendar_agent")
    workflow.add_edge("calendar_agent", END)
    
    # Компилируем граф
    return workflow.compile()

# Создаем экземпляр графа
graph = create_calendar_graph()