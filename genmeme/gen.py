import os
import random
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

import fire  # type: ignore
from typing import Optional
from jinja2 import Template
from dotenv import load_dotenv

from genmeme.files import TEMPLATES_PATH, PROMPT_PATH, IMAGES_PATH
from genmeme.llm import (
    openrouter_nano_banana_generate,
    OPENROUTER_DEFAULT_MODEL,
)


MEMEGEN_HOST = "http://localhost:5051"
DEFAULT_MODEL_NAME = OPENROUTER_DEFAULT_MODEL
DEFAULT_IMAGE_TEMPLATES_COUNT = 3
MAX_QUERY_LENGTH = 600


@dataclass
class MemeResponse:
    file_name: str
    template_ids: List[str] = field(default_factory=list)


async def generate_meme(
    query: str,
    generate_prompt_path: str = str(PROMPT_PATH),
    templates_path: str = str(TEMPLATES_PATH),
    selected_template_id: Optional[str] = None,
    model_name: str = DEFAULT_MODEL_NAME,
    image_templates_count: int = DEFAULT_IMAGE_TEMPLATES_COUNT,
) -> MemeResponse:
    random.seed(time.time())

    # Select templates
    all_templates = json.loads(Path(templates_path).read_text())

    if selected_template_id:
        meme_templates = [t for t in all_templates if t["id"] == selected_template_id]
    else:
        image_templates = [
            t for t in all_templates if t.get("type", "image") == "image"
        ]
        assert image_templates
        meme_templates = random.sample(image_templates, image_templates_count)
        random.shuffle(meme_templates)

    meme_images = []
    template_ids = []
    for template in meme_templates:
        meme_id = template["id"]
        file_path = os.path.join(IMAGES_PATH, f"{meme_id}.jpg")
        meme_images.append(file_path)
        template_ids.append(meme_id)

    # Generate prompt
    with open(generate_prompt_path) as f:
        prompt_template = Template(f.read())

    cut_query = query
    if len(query) >= MAX_QUERY_LENGTH:
        space_pos = query.find(" ", MAX_QUERY_LENGTH)
        if space_pos != -1:
            cut_query = query[:space_pos] + "..."

    prompt = (
        prompt_template.render(
            query=cut_query,
            meme_templates=meme_templates,
        ).strip()
        + "\n"
    )

    # Generate meme
    output_image_path = await openrouter_nano_banana_generate(
        prompt=prompt,
        input_images=meme_images,
        model_name=model_name,
    )

    return MemeResponse(
        file_name=output_image_path.name,
        template_ids=template_ids,
    )


if __name__ == "__main__":
    load_dotenv()
    fire.Fire(generate_meme)
