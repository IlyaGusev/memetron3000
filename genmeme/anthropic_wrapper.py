import logging
import time
import os
from typing import Optional, Any, List, Dict, cast

from anthropic import AsyncAnthropic, APIError
from anthropic.types import MessageParam

DEFAULT_MODEL = "claude-3-5-sonnet-20241022"
DEFAULT_SLEEP_TIME = 2


async def anthropic_completion(
    messages: List[Dict[str, Any]],
    model_name: str = DEFAULT_MODEL,
    temperature: float = 1.0,
    sleep_time: int = DEFAULT_SLEEP_TIME,
    api_key: Optional[str] = None,
    max_tokens: int = 2048,
    **kwargs: Any,
) -> str:
    if not api_key:
        api_key = os.environ.get("ANTHROPIC_API_KEY", None)

    system_message = ""
    if messages[0]["role"] == "system":
        system_message = messages[0]["content"]
        messages = messages[1:]

    typed_messages = [cast(MessageParam, m) for m in messages]

    while True:
        try:
            client = AsyncAnthropic(api_key=api_key)
            completion = await client.messages.create(
                system=system_message,
                messages=typed_messages,
                model=model_name,
                max_tokens=max_tokens,
                temperature=temperature,
                **kwargs,
            )
            break
        except APIError as e:
            logging.warning(f"Anthropic error: {e}.")
            time.sleep(sleep_time)
    content: str = completion.content[0].text
    return content
