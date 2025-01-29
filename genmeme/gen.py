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
DEFAULT_GENERATE_PROMPT_PATH = str((PROMPTS_DIR_PATH / "gen.jinja").resolve())
DEFAULT_SELECT_PROMPT_PATH = str((PROMPTS_DIR_PATH / "select.jinja").resolve())
DEFAULT_INITIAL_TEMPLATES_COUNT = 30
DEFAULT_SELECTED_TEMPLATES_COUNT = 10
DEFAULT_GENERATED_MEME_COUNT = 3
RANDOM_SELECT = True


def clean_host(url: str) -> str:
    url = url.replace(MEMEGEN_HOST, "")
    url = url.replace("http://localhost:5000", "")
    url = url.replace("https://memegen.link", "")
    url = url.replace("http://memegen.link", "")
    url = url.replace("https://api.memegen.link", "")
    url = url.replace("http://api.memegen.link", "")
    return url


async def select_templates(
    query: str,
    all_templates: List[Dict[str, Any]],
    prompt_path: str,
    model_name: str,
    initial_templates_count: int,
    selected_templates_count: int,
) -> List[Dict[str, Any]]:
    with open(prompt_path) as f:
        template = Template(f.read())

    meme_templates = random.sample(all_templates, initial_templates_count)
    prompt = (
        template.render(
            query=query,
            meme_templates=meme_templates,
            selected_templates_count=selected_templates_count,
        ).strip()
        + "\n"
    )

    messages = [{"role": "user", "content": prompt}]
    content = await anthropic_completion(messages=messages, model_name=model_name)

    content = content[content.find("{") : content.rfind("}") + 1]
    response = json.loads(content)
    memes = response["memes"]
    return [meme_templates[i - 1] for i in memes]


async def generate_meme(
    query: str,
    all_templates: List[Dict[str, Any]],
    select_prompt_path: str,
    generate_prompt_path: str,
    model_name: str,
    initial_templates_count: int,
    selected_templates_count: int,
    generated_meme_count: int,
    random_select: bool = True
) -> str:
    if not random_select:
        meme_templates = await select_templates(
            query=query,
            all_templates=all_templates,
            prompt_path=select_prompt_path,
            model_name=model_name,
            initial_templates_count=initial_templates_count,
            selected_templates_count=selected_templates_count,
        )
    else:
        meme_templates = random.sample(all_templates, selected_templates_count)

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


async def gen_image_url(
    query: str,
    generate_prompt_path: str = DEFAULT_GENERATE_PROMPT_PATH,
    select_prompt_path: str = DEFAULT_SELECT_PROMPT_PATH,
    model_name: str = DEFAULT_MODEL_NAME,
    initial_templates_count: int = DEFAULT_INITIAL_TEMPLATES_COUNT,
    selected_templates_count: int = DEFAULT_SELECTED_TEMPLATES_COUNT,
    generated_meme_count: int = DEFAULT_GENERATED_MEME_COUNT,
    random_select: bool = RANDOM_SELECT,
) -> str:
    random.seed(time.time())
    all_templates = ALL_MEME_TEMPLATES
    for template in all_templates:
        url = template["example"]["url"]
        template["example"]["url"] = clean_host(url)
        assert not template["example"]["url"].startswith("http"), template["example"][
            "url"
        ]
    image_url = await generate_meme(
        query=query,
        all_templates=all_templates,
        select_prompt_path=select_prompt_path,
        generate_prompt_path=generate_prompt_path,
        model_name=model_name,
        initial_templates_count=initial_templates_count,
        selected_templates_count=selected_templates_count,
        generated_meme_count=generated_meme_count,
        random_select=random_select,
    )
    print(image_url)
    return image_url


def gen_image_url_sync(
    query: str,
    generate_prompt_path: str = DEFAULT_GENERATE_PROMPT_PATH,
    select_prompt_path: str = DEFAULT_SELECT_PROMPT_PATH,
    model_name: str = DEFAULT_MODEL_NAME,
    initial_templates_count: int = DEFAULT_INITIAL_TEMPLATES_COUNT,
    selected_templates_count: int = DEFAULT_SELECTED_TEMPLATES_COUNT,
    generated_meme_count: int = DEFAULT_GENERATED_MEME_COUNT,
) -> str:
    return asyncio.run(
        gen_image_url(
            query=query,
            model_name=model_name,
            generate_prompt_path=generate_prompt_path,
            select_prompt_path=select_prompt_path,
            initial_templates_count=initial_templates_count,
            selected_templates_count=selected_templates_count,
            generated_meme_count=generated_meme_count,
        )
    )


if __name__ == "__main__":
    fire.Fire(gen_image_url_sync)
