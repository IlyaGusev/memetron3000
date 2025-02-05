import os
import asyncio
import random
import json
import time
import uuid
from typing import Tuple

from jinja2 import Template
import aiofiles
import aiohttp
import fire  # type: ignore

from genmeme.files import TEMPLATES_PATH, PROMPTS_DIR_PATH
from genmeme.anthropic_wrapper import anthropic_completion
from genmeme.video import create_meme_video


STORAGE_PATH = "output"
VIDEOS_PATH = "videos"
MEMEGEN_HOST = "http://localhost:8082"
ALL_MEME_TEMPLATES = json.loads(TEMPLATES_PATH.read_text())
DEFAULT_MODEL_NAME = "claude-3-5-sonnet-20241022"
DEFAULT_GENERATE_PROMPT_PATH = str((PROMPTS_DIR_PATH / "gen.jinja").resolve())
DEFAULT_SELECTED_TEMPLATES_COUNT = 8
DEFAULT_GENERATED_MEME_COUNT = 3


async def download_file(url: str, file_path: str) -> bool:
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                print("Download status:", response.status)
                if response.status != 200:
                    return False
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                async with aiofiles.open(file_path, "wb") as f:
                    current_size = 0
                    async for chunk in response.content.iter_chunked(8192):
                        current_size += len(chunk)
                        await f.write(chunk)
                return True
    except Exception as e:
        print(e)
        if os.path.exists(file_path):
            os.remove(file_path)
        return False


async def generate_meme(
    query: str,
    generate_prompt_path: str = DEFAULT_GENERATE_PROMPT_PATH,
    model_name: str = DEFAULT_MODEL_NAME,
    selected_templates_count: int = DEFAULT_SELECTED_TEMPLATES_COUNT,
    generated_meme_count: int = DEFAULT_GENERATED_MEME_COUNT,
) -> Tuple[str, str]:
    random.seed(time.time())
    all_templates = ALL_MEME_TEMPLATES
    meme_templates = random.sample(all_templates, min(selected_templates_count, len(all_templates)))
    for template in meme_templates:
        if not isinstance(template["example"]["text"], str):
            template["example"]["text"] = json.dumps(
                template["example"]["text"], ensure_ascii=False
            )

    with open(generate_prompt_path) as f:
        template = Template(f.read())

    prompt = (
        template.render(
            query=query,
            meme_templates=meme_templates,
            generated_meme_count=generated_meme_count,
        ).strip()
        + "\n"
    )
    print(prompt)

    messages = [{"role": "user", "content": prompt}]
    content = await anthropic_completion(messages=messages, model_name=model_name)
    print(content)

    content = content[content.find("{") : content.rfind("}") + 1]
    response = json.loads(content)
    best_meme = response.get("best_meme")
    meme_id = best_meme["id"]
    meme_captions = best_meme["captions"]
    encoded_meme_captions = [c.replace(" ", "_").replace("?", "~q").replace("/", "|") for c in meme_captions]
    final_captions_str = "/".join(encoded_meme_captions)

    meme_templates = {m["id"]: m for m in meme_templates}
    selected_template = meme_templates.get(meme_id)
    if selected_template and selected_template.get("type") == "video":
        input_path = os.path.join(VIDEOS_PATH, meme_id + ".mp4")
        file_name = f"{uuid.uuid4()}.mp4"
        output_path = os.path.join(STORAGE_PATH, file_name)
        create_meme_video(input_path, output_path, meme_captions[0])
        return file_name, f"http://localhost/videos/{meme_id}/{final_captions_str}"

    prefix = f"{MEMEGEN_HOST}/images/{meme_id}/"
    suffix = ".jpg?font=impact&watermark="
    image_url = prefix + final_captions_str + suffix

    file_name = f"{uuid.uuid4()}.jpg"
    file_path = os.path.join(STORAGE_PATH, file_name)
    success = await download_file(image_url, file_path)
    assert success

    return file_name, image_url


def generate_meme_sync(
    query: str,
    generate_prompt_path: str = DEFAULT_GENERATE_PROMPT_PATH,
    model_name: str = DEFAULT_MODEL_NAME,
    selected_templates_count: int = DEFAULT_SELECTED_TEMPLATES_COUNT,
    generated_meme_count: int = DEFAULT_GENERATED_MEME_COUNT,
) -> Tuple[str, str]:
    return asyncio.run(
        generate_meme(
            query=query,
            model_name=model_name,
            generate_prompt_path=generate_prompt_path,
            selected_templates_count=selected_templates_count,
            generated_meme_count=generated_meme_count,
        )
    )


if __name__ == "__main__":
    fire.Fire(generate_meme_sync)
