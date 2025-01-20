import os
from typing import Optional, Literal
import uuid
import asyncio
from datetime import datetime

import uvicorn
import aiofiles
import aiohttp
from pydantic import BaseModel
from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles

from genmeme.gen import gen


class PredictRequest(BaseModel):
    result_id: Optional[int] = None
    prompt: str


class PredictResponse(BaseModel):
    type: Literal["image", "video"]
    url: Optional[str] = None


APP = FastAPI()
STORAGE_PATH = "output"


def get_base_url(request: Request) -> str:
    if os.getenv("BASE_URL"):
        return os.getenv("BASE_URL")
    forwarded_proto = request.headers.get("X-Forwarded-Proto", "http")
    forwarded_host = request.headers.get("X-Forwarded-Host", request.headers.get("Host", "localhost"))
    return f"{forwarded_proto}://{forwarded_host}"


async def download_file(url: str, file_path: str) -> bool:
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                print("Download status:", response.status)
                if response.status != 200:
                    return False
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                async with aiofiles.open(file_path, 'wb') as f:
                    current_size = 0
                    async for chunk in response.content.iter_chunked(8192):
                        current_size += len(chunk)
                        await f.write(chunk)
                return True
    except Exception:
        if os.path.exists(file_path):
            os.remove(file_path)
        return False


@APP.post("/api/v1/predict", response_model=PredictResponse)
async def predict(request: PredictRequest, req: Request):
    image_url = await gen(request.prompt)

    file_name = f"{uuid.uuid4()}.jpg"
    file_path = os.path.join(STORAGE_PATH, file_name)
    success = await download_file(image_url, file_path)
    if not success:
        print("Download failed!")
    base_url = get_base_url(req)
    public_url = f"{base_url}/output/{file_name}"
    return PredictResponse(
        type="image",
        url=public_url
    )


@APP.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}


APP.mount("/output", StaticFiles(directory=STORAGE_PATH), name="output")


if __name__ == "__main__":
    uvicorn.run(APP, host="0.0.0.0", port=8081)
