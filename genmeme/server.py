import os
import datetime
import traceback
import asyncio
from typing import Optional, Dict, Any
from contextlib import asynccontextmanager

import fire  # type: ignore
import uvicorn
from pydantic import BaseModel
from fastapi import FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv

from genmeme.files import STORAGE_PATH, PROMPT_PATH, TEMPLATES_PATH
from genmeme.gen import generate_meme
from genmeme.db import ImageRecord, SessionLocal
from genmeme.queue import QueueManager, JobStatus


NUM_RETRIES = 3
QUEUE_MANAGER = QueueManager()


class PredictRequest(BaseModel):
    prompt: str
    selected_template_id: Optional[str] = None


class PredictResponse(BaseModel):
    job_id: str
    position: int


class QueueSizeResponse(BaseModel):
    size: int


class JobStatusResponse(BaseModel):
    job_id: str
    status: JobStatus
    position: int
    created_at: datetime.datetime
    started_at: Optional[datetime.datetime] = None
    completed_at: Optional[datetime.datetime] = None
    result_url: Optional[str] = None
    error: Optional[str] = None


async def process_queue_worker() -> None:
    while True:
        job = await QUEUE_MANAGER.queue.get()
        try:
            QUEUE_MANAGER.update_job_status(job.job_id, JobStatus.PROCESSING)
            QUEUE_MANAGER.is_processing = True

            generate_prompt_path = str(PROMPT_PATH)
            env_prompt_path = os.getenv("PROMPT_PATH")
            if env_prompt_path:
                generate_prompt_path = env_prompt_path

            templates_path = str(TEMPLATES_PATH)
            env_templates_path = os.getenv("TEMPLATES_PATH")
            if env_templates_path:
                templates_path = env_templates_path

            for attempt in range(NUM_RETRIES):
                try:
                    response = await generate_meme(
                        job.prompt,
                        generate_prompt_path=generate_prompt_path,
                        templates_path=templates_path,
                        selected_template_id=job.selected_template_id,
                    )
                    print(f"Response: {response}")
                    break
                except Exception:
                    if attempt == NUM_RETRIES - 1:
                        raise
                    traceback.print_exc()

            public_url = f"/output/{response.file_name}"

            db = SessionLocal()
            db_record = ImageRecord(
                result_id=response.file_name.split(".")[0],
                public_url=public_url,
                query=job.prompt,
                created_at=datetime.datetime.now(datetime.UTC),
                template_id=response.template_id,
            )
            db.add(db_record)
            db.commit()
            db.close()

            QUEUE_MANAGER.update_job_status(
                job.job_id, JobStatus.COMPLETED, result_url=public_url
            )

        except Exception as e:
            error_msg = str(e)
            traceback.print_exc()
            QUEUE_MANAGER.update_job_status(
                job.job_id, JobStatus.FAILED, error=error_msg
            )
        finally:
            QUEUE_MANAGER.is_processing = False
            QUEUE_MANAGER.queue.task_done()


@asynccontextmanager
async def lifespan(app: FastAPI):  # type: ignore
    task = asyncio.create_task(process_queue_worker())
    yield
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


APP = FastAPI(lifespan=lifespan)


def get_base_url(request: Request) -> str:
    forwarded_proto = request.headers.get("X-Forwarded-Proto", "http")
    forwarded_host = request.headers.get(
        "X-Forwarded-Host", request.headers.get("Host", "localhost")
    )
    return f"{forwarded_proto}://{forwarded_host}"


@APP.post("/api/v1/predict", response_model=PredictResponse)
async def predict(request: PredictRequest, req: Request) -> PredictResponse:
    job = QUEUE_MANAGER.create_job(request.prompt, request.selected_template_id)
    position = await QUEUE_MANAGER.enqueue(job)
    return PredictResponse(job_id=job.job_id, position=position)


@APP.get("/api/v1/queue/size", response_model=QueueSizeResponse)
async def get_queue_size() -> QueueSizeResponse:
    size = QUEUE_MANAGER.get_queue_size()
    return QueueSizeResponse(size=size)


@APP.get("/api/v1/job/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str) -> JobStatusResponse:
    job = QUEUE_MANAGER.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return JobStatusResponse(
        job_id=job.job_id,
        status=job.status,
        position=job.position,
        created_at=job.created_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
        result_url=job.result_url,
        error=job.error,
    )


@APP.get("/health")
async def health_check() -> Dict[str, Any]:
    return {"status": "healthy", "timestamp": datetime.datetime.utcnow().isoformat()}


APP.mount("/output", StaticFiles(directory=STORAGE_PATH), name="output")


def main(host: str = "0.0.0.0", port: int = 8081) -> None:
    uvicorn.run(APP, host=host, port=port)


if __name__ == "__main__":
    load_dotenv()
    fire.Fire(main)
