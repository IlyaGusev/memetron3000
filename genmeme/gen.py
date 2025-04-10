import os
import asyncio
import random
import json
import time
import uuid
from dataclasses import dataclass
from pathlib import Path

from jinja2 import Template
import aiofiles
import aiohttp
import fire  # type: ignore

from genmeme.files import TEMPLATES_PATH, STORAGE_PATH, VIDEOS_PATH, PROMPT_PATH
from genmeme.anthropic_wrapper import anthropic_completion
from genmeme.video import create_meme_video


MEMEGEN_HOST = "http://localhost:5051"
DEFAULT_TEMPLATES_PATH = TEMPLATES_PATH
DEFAULT_MODEL_NAME = "claude-3-5-sonnet-20241022"
DEFAULT_GENERATE_PROMPT_PATH = PROMPT_PATH
DEFAULT_VIDEO_TEMPLATES_COUNT = 4
DEFAULT_IMAGE_TEMPLATES_COUNT = 2
DEFAULT_GENERATED_MEME_COUNT = 3
MAX_QUERY_LENGTH = 600


@dataclass
class MemeResponse:
    file_name: str
    image_url: str = ""
    template_id: str = ""
    captions: str = ""


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
    generate_prompt_path: str = str(DEFAULT_GENERATE_PROMPT_PATH),
    templates_path: str = str(DEFAULT_TEMPLATES_PATH),
    model_name: str = DEFAULT_MODEL_NAME,
    video_templates_count: int = DEFAULT_VIDEO_TEMPLATES_COUNT,
    image_templates_count: int = DEFAULT_IMAGE_TEMPLATES_COUNT,
    generated_meme_count: int = DEFAULT_GENERATED_MEME_COUNT,
) -> MemeResponse:
    random.seed(time.time())
    all_templates = json.loads(Path(templates_path).read_text())

    video_templates = [t for t in all_templates if t.get("type", "image") == "video"]
    image_templates = [t for t in all_templates if t.get("type", "image") == "image"]
    selected_video_templates = []
    selected_image_templates = []
    if video_templates:
        count = min(video_templates_count, len(video_templates))
        selected_video_templates = random.sample(video_templates, count)
    if image_templates:
        count = min(image_templates_count, len(image_templates))
        selected_image_templates = random.sample(image_templates, count)
    meme_templates = selected_video_templates + selected_image_templates
    random.shuffle(meme_templates)

    for template in meme_templates:
        if "example" in template and not isinstance(template["example"]["text"], str):
            template["example"]["text"] = json.dumps(
                template["example"]["text"], ensure_ascii=False
            )

    with open(generate_prompt_path) as f:
        template = Template(f.read())

    cut_query = query
    if len(query) >= MAX_QUERY_LENGTH:
        space_pos = query.find(" ", MAX_QUERY_LENGTH)
        if space_pos != -1:
            cut_query = query[:space_pos] + "..."

    prompt = (
        template.render(
            query=cut_query,
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
    encoded_meme_captions = [
        c.replace(" ", "_").replace("?", "~q").replace("/", "|") for c in meme_captions
    ]
    final_captions_str = "/".join(encoded_meme_captions)

    id_to_meme_templates = {m["id"]: m for m in meme_templates}
    selected_template = id_to_meme_templates.get(meme_id)
    if selected_template and selected_template.get("type") == "video":
        input_path = os.path.join(VIDEOS_PATH, meme_id + ".mp4")
        file_name = f"{uuid.uuid4()}.mp4"
        output_path = os.path.join(STORAGE_PATH, file_name)
        video_caption = "\n".join(meme_captions)
        create_meme_video(input_path, output_path, video_caption)
        url = f"http://localhost/videos/{meme_id}/{final_captions_str}"

        return MemeResponse(
            file_name=file_name,
            image_url=url,
            template_id=meme_id,
            captions=json.dumps(meme_captions, ensure_ascii=False),
        )

    prefix = f"{MEMEGEN_HOST}/images/{meme_id}/"
    suffix = ".jpg?font=impact&watermark="
    image_url = prefix + final_captions_str + suffix

    file_name = f"{uuid.uuid4()}.jpg"
    file_path = os.path.join(STORAGE_PATH, file_name)
    success = await download_file(image_url, file_path)
    assert success

    return MemeResponse(
        file_name=file_name,
        image_url=image_url,
        template_id=meme_id,
        captions=json.dumps(meme_captions, ensure_ascii=False),
    )


def generate_meme_sync(
    query: str,
    generate_prompt_path: str = str(DEFAULT_GENERATE_PROMPT_PATH),
    templates_path: str = str(DEFAULT_TEMPLATES_PATH),
    model_name: str = DEFAULT_MODEL_NAME,
    video_templates_count: int = DEFAULT_VIDEO_TEMPLATES_COUNT,
    image_templates_count: int = DEFAULT_IMAGE_TEMPLATES_COUNT,
    generated_meme_count: int = DEFAULT_GENERATED_MEME_COUNT,
) -> None:
    print(
        asyncio.run(
            generate_meme(
                query=query,
                model_name=model_name,
                generate_prompt_path=generate_prompt_path,
                templates_path=templates_path,
                video_templates_count=video_templates_count,
                image_templates_count=image_templates_count,
                generated_meme_count=generated_meme_count,
            )
        )
    )


if __name__ == "__main__":
    fire.Fire(generate_meme_sync)
