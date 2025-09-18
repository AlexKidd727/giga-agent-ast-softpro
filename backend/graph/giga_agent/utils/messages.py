from langchain_core.messages import ToolMessage


def filter_tool_messages(messages):
    filtered_messages = []
    for idx, msg in enumerate(messages):
        if isinstance(msg, ToolMessage):
            if idx - 1 <= 0:
                continue
            # Безопасная проверка additional_kwargs
            function_call = None
            if hasattr(messages[idx - 1], 'additional_kwargs'):
                function_call = messages[idx - 1].additional_kwargs.get("function_call")
            
            ai_message_tool_called = (
                function_call
                or getattr(messages[idx - 1], 'tool_calls', None)
            )
            if not ai_message_tool_called:
                continue
        filtered_messages.append(msg)
    return filtered_messages


def filter_tool_calls(message):
    last_mes = message.model_copy()
    last_mes.tool_calls = None
    
    # Безопасная работа с additional_kwargs
    if hasattr(last_mes, 'additional_kwargs'):
        last_mes.additional_kwargs["function_call"] = None
        last_mes.additional_kwargs["functions_state_id"] = None
        if "tool_calls" in last_mes.additional_kwargs:
            if not last_mes.content:
                last_mes.content = "."
            del last_mes.additional_kwargs["tool_calls"]
    
    return last_mes
