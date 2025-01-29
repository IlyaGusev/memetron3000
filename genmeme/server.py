import time
from typing import Optional, Literal, Dict, Any
from datetime import datetime

import uvicorn
from pydantic import BaseModel
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles

from genmeme.gen import generate_meme, STORAGE_PATH
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

    file_name, meta_str = await generate_meme(request.prompt)
    base_url = get_base_url(req)
    public_url = f"{base_url}/output/{file_name}"

    db = SessionLocal()
    db_record = ImageRecord(
        result_id=request.result_id, image_url=meta_str, public_url=public_url
    )
    db.add(db_record)
    db.commit()
    db.close()

    total_time = time.time() - start_time
    print(f"Total processing time: {total_time:.3f}s")

    return PredictResponse(type="image", url=public_url)


@APP.get("/health")
async def health_check() -> Dict[str, Any]:
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}


APP.mount("/output", StaticFiles(directory=STORAGE_PATH), name="output")


if __name__ == "__main__":
    uvicorn.run(APP, host="0.0.0.0", port=8081)
