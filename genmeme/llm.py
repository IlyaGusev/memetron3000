import os
import uuid
from typing import Optional, Any, List, cast
import base64
from pathlib import Path

from openai import AsyncOpenAI
from openai.types.chat.chat_completion_message_param import ChatCompletionMessageParam

from genmeme.files import STORAGE_PATH


OPENROUTER_DEFAULT_MODEL = "google/gemini-3-pro-image-preview"


async def openrouter_nano_banana_generate(
    prompt: str,
    input_images: List[str],
    model_name: str = OPENROUTER_DEFAULT_MODEL,
    api_key: Optional[str] = None,
    **kwargs: Any,
) -> Path:
    if not api_key:
        api_key = os.environ.get("OPENROUTER_API_KEY", None)
    client = AsyncOpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
    )

    content_parts = []
    for input_image_path in input_images:
        assert os.path.exists(input_image_path)
        with open(input_image_path, "rb") as f:
            image_bytes = f.read()
        base64_data = base64.b64encode(image_bytes).decode("utf-8")
        image_url = f"data:image/jpeg;base64,{base64_data}"
        content_parts.append({"type": "image_url", "image_url": {"url": image_url}})
    content_parts.append({"type": "text", "text": prompt})
    messages = [
        {
            "role": "user",
            "content": content_parts,
        }
    ]
    casted_messages = [
        cast(ChatCompletionMessageParam, message) for message in messages
    ]

    response = await client.chat.completions.create(
        model=model_name,
        messages=casted_messages,
        extra_body={
            "modalities": ["image"],
            "image_config": {
                "image_size": "1K",
            },
        },
        **kwargs,
    )

    response = response.choices[0].message
    if not hasattr(response, "images"):
        raise ValueError("No image generated, response: " + str(response))

    file_name = str(uuid.uuid4()) + ".jpg"
    file_path = STORAGE_PATH / file_name
    assert response.images
    assert len(response.images) == 1
    image_url = response.images[0]["image_url"]["url"]
    base64_data = image_url.split(",")[1]
    with open(file_path, "wb") as f:
        f.write(base64.b64decode(base64_data))
    return file_path
