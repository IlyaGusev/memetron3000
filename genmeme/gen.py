import asyncio
import fire  # type: ignore
import random
import json
import time
from typing import List, Dict, Any, Optional

from jinja2 import Template

from genmeme.files import TEMPLATES_PATH, PROMPTS_DIR_PATH
from genmeme.anthropic_wrapper import anthropic_completion


MEMEGEN_HOST = "http://localhost:8082"
ALL_MEME_TEMPLATES = json.loads(TEMPLATES_PATH.read_text())
DEFAULT_MODEL_NAME = "claude-3-5-sonnet-20241022"
DEFAULT_GENERATE_PROMPT_PATH = str((PROMPTS_DIR_PATH / "gen.jinja").resolve())
DEFAULT_SELECT_PROMPT_PATH = str((PROMPTS_DIR_PATH / "select.jinja").resolve())
DEFAULT_SELECTED_TEMPLATES_COUNT = 10
DEFAULT_GENERATED_MEME_COUNT = 3


def clean_host(url: str) -> str:
    url = url.replace(MEMEGEN_HOST, "")
    url = url.replace("http://localhost:5000", "")
    url = url.replace("https://memegen.link", "")
    url = url.replace("http://memegen.link", "")
    url = url.replace("https://api.memegen.link", "")
    url = url.replace("http://api.memegen.link", "")
    return url


async def gen_image_url(
    query: str,
    generate_prompt_path: str = DEFAULT_GENERATE_PROMPT_PATH,
    select_prompt_path: str = DEFAULT_SELECT_PROMPT_PATH,
    model_name: str = DEFAULT_MODEL_NAME,
    selected_templates_count: int = DEFAULT_SELECTED_TEMPLATES_COUNT,
    generated_meme_count: int = DEFAULT_GENERATED_MEME_COUNT,
) -> str:
    random.seed(time.time())
    all_templates = ALL_MEME_TEMPLATES
    meme_templates = random.sample(all_templates, selected_templates_count)
    for template in meme_templates:
        url = template["example"]["url"]
        url = clean_host(url)
        template["example"]["url"] = url
        assert not url.startswith("http"), url

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
    image_url: Optional[str] = response.get("best_image_url")
    assert image_url
    image_url = clean_host(image_url).strip()
    if not image_url.endswith(".png") and not image_url.endswith(".jpg"):
        image_url += ".png"
    image_url += "?font=impact&watermark="
    final_url: str = MEMEGEN_HOST + image_url
    return final_url


def gen_image_url_sync(
    query: str,
    generate_prompt_path: str = DEFAULT_GENERATE_PROMPT_PATH,
    select_prompt_path: str = DEFAULT_SELECT_PROMPT_PATH,
    model_name: str = DEFAULT_MODEL_NAME,
    selected_templates_count: int = DEFAULT_SELECTED_TEMPLATES_COUNT,
    generated_meme_count: int = DEFAULT_GENERATED_MEME_COUNT,
) -> str:
    return asyncio.run(
        gen_image_url(
            query=query,
            model_name=model_name,
            generate_prompt_path=generate_prompt_path,
            select_prompt_path=select_prompt_path,
            selected_templates_count=selected_templates_count,
            generated_meme_count=generated_meme_count,
        )
    )


if __name__ == "__main__":
    fire.Fire(gen_image_url_sync)
