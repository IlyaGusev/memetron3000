import os
import time
from typing import Optional, Literal, Dict, Any
from datetime import datetime

import fire
import uvicorn
from pydantic import BaseModel
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles

from genmeme.files import STORAGE_PATH, PROMPT_PATH, TEMPLATES_PATH
from genmeme.gen import generate_meme
from genmeme.db import ImageRecord, SessionLocal


APP = FastAPI()


class PredictRequest(BaseModel):
    result_id: Optional[int] = None
    prompt: str


class PredictResponse(BaseModel):
    type: Literal["image", "video"]
    url: Optional[str] = None


def get_base_url(request: Request) -> str:
    forwarded_proto = request.headers.get("X-Forwarded-Proto", "http")
    forwarded_host = request.headers.get(
        "X-Forwarded-Host", request.headers.get("Host", "localhost")
    )
    return f"{forwarded_proto}://{forwarded_host}"


@APP.post("/api/v1/predict", response_model=PredictResponse)
async def predict(request: PredictRequest, req: Request) -> PredictResponse:
    start_time = time.time()

    generate_prompt_path = PROMPT_PATH
    env_prompt_path = os.getenv("PROMPT_PATH")
    if env_prompt_path:
        generate_prompt_path = env_prompt_path

    templates_path = TEMPLATES_PATH
    env_templates_path = os.getenv("TEMPLATES_PATH")
    if env_templates_path:
        templates_path = env_templates_path

    response = await generate_meme(
        request.prompt,
        generate_prompt_path=generate_prompt_path,
        templates_path=templates_path,
    )
    base_url = get_base_url(req)
    public_url = f"{base_url}/output/{response.file_name}"

    db = SessionLocal()
    db_record = ImageRecord(
        result_id=request.result_id,
        image_url=response.image_url,
        public_url=public_url,
        query=request.prompt,
        created_at=datetime.utcnow(),
        captions=response.captions,
        template_id=response.template_id,
    )
    db.add(db_record)
    db.commit()
    db.close()

    total_time = time.time() - start_time
    print(f"Total processing time: {total_time:.3f}s")

    if public_url.endswith(".mp4"):
        return PredictResponse(type="video", url=public_url)
    return PredictResponse(type="image", url=public_url)


@APP.get("/health")
async def health_check() -> Dict[str, Any]:
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}


APP.mount("/output", StaticFiles(directory=STORAGE_PATH), name="output")


def main(host: str = "0.0.0.0", port: int = 8081):
    uvicorn.run(APP, host=host, port=port)


if __name__ == "__main__":
    fire.Fire(main)
