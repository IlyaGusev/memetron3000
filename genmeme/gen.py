import asyncio
import fire  # type: ignore
import random
import json
import time
from typing import List, Dict, Any, Optional

from jinja2 import Template

from genmeme.files import TEMPLATES_PATH, PROMPTS_DIR_PATH
from genmeme.anthropic_wrapper import anthropic_completion

# MEMEGEN_HOST = "https://api.memegen.link"
MEMEGEN_HOST = "http://localhost:8082"
ALL_MEME_TEMPLATES = json.loads(TEMPLATES_PATH.read_text())
DEFAULT_MODEL_NAME = "claude-3-5-sonnet-20241022"
DEFAULT_PROMPT_PATH = str((PROMPTS_DIR_PATH / "gen.jinja").resolve())
DEFAULT_TEMPLATES_COUNT = 4


async def get_memegen_meme(
    query: str,
    all_templates: List[Dict[str, Any]],
    prompt_path: str,
    model_name: str,
    templates_count: int
) -> str:
    with open(prompt_path) as f:
        template = Template(f.read())

    meme_templates = random.sample(all_templates, templates_count)
    prompt = template.render(
        query=query,
        meme_templates=meme_templates
    ).strip() + "\n"
    print(prompt)

    messages = [{"role": "user", "content": prompt}]
    content = await anthropic_completion(messages=messages, model_name=model_name)
    print(content)

    content = content[content.find("{"):content.rfind("}") + 1]
    response = json.loads(content)
    image_url: Optional[str] = response.get("best_image_url")
    assert image_url
    image_url += "?font=impact&watermark="
    final_url: str = MEMEGEN_HOST + image_url
    return final_url


async def gen_image_url(
    query: str,
    prompt_path: str = DEFAULT_PROMPT_PATH,
    model_name: str = DEFAULT_MODEL_NAME,
    templates_count: int = DEFAULT_TEMPLATES_COUNT,
) -> str:
    random.seed(time.time())
    all_templates = ALL_MEME_TEMPLATES
    for template in all_templates:
        template["example"]["url"] = template["example"]["url"].replace(MEMEGEN_HOST, "")
        template["example"]["url"] = template["example"]["url"].replace("http://localhost:5000", "")
        assert not template["example"]["url"].startswith("http"), template["example"]["url"]
    image_url = await get_memegen_meme(
        query=query,
        all_templates=all_templates,
        prompt_path=prompt_path,
        model_name=model_name,
        templates_count=templates_count
    )
    print(image_url)
    return image_url


def gen_image_url_sync(
    query: str,
    prompt_path: str = DEFAULT_PROMPT_PATH,
    model_name: str = DEFAULT_MODEL_NAME,
    templates_count: int = DEFAULT_TEMPLATES_COUNT,
) -> str:
    return asyncio.run(gen_image_url(
        query=query,
        prompt_path=prompt_path,
        model_name=model_name,
        templates_count=templates_count,
    ))


if __name__ == "__main__":
    fire.Fire(gen_image_url_sync)
