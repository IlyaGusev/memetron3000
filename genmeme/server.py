import os
import datetime
import traceback
import asyncio
import json
import logging
from typing import Optional, Dict, Any, List
from contextlib import asynccontextmanager
from pathlib import Path

import fire  # type: ignore
import uvicorn
from pydantic import BaseModel
from fastapi import FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from dotenv import load_dotenv

from genmeme.files import STORAGE_PATH, PROMPT_PATH, TEMPLATES_PATH
from genmeme.gen import generate_meme
from genmeme.db import ImageRecord, SessionLocal
from genmeme.queue import QueueManager, JobStatus
from genmeme.thumbnails import create_thumbnail


logger = logging.getLogger("uvicorn")


class EndpointFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        # Filter out queue size and job status polling endpoints
        message = record.getMessage()
        return "/api/v1/queue/size" not in message and "/api/v1/job/" not in message


NUM_RETRIES = 5
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
    selected_template_id: Optional[str] = None
    started_at: Optional[datetime.datetime] = None
    completed_at: Optional[datetime.datetime] = None
    result_url: Optional[str] = None
    error: Optional[str] = None


class TemplateInfo(BaseModel):
    id: str
    name: str
    description: str


class MemeInfo(BaseModel):
    result_id: str
    public_url: str
    thumbnail_url: Optional[str] = None
    query: Optional[str] = None
    created_at: Optional[datetime.datetime] = None
    template_ids: Optional[str] = None


class GalleryResponse(BaseModel):
    memes: List[MemeInfo]
    total: int
    page: int
    page_size: int
    total_pages: int


class ConfigResponse(BaseModel):
    generation_enabled: bool


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
                    break
                except Exception:
                    if attempt == NUM_RETRIES - 1:
                        raise
                    traceback.print_exc()

            public_url = f"output/{response.file_name}"

            # Generate thumbnail
            image_path = Path(STORAGE_PATH) / response.file_name
            thumbnail_dir = Path(STORAGE_PATH) / "thumbnails"
            thumbnail_dir.mkdir(exist_ok=True)
            thumbnail_name = response.file_name
            thumbnail_path = thumbnail_dir / thumbnail_name
            thumbnail_url = f"output/thumbnails/{thumbnail_name}"

            try:
                create_thumbnail(image_path, thumbnail_path)
            except Exception as e:
                logger.error(f"Failed to create thumbnail: {e}")
                thumbnail_url = public_url

            logger.info(
                f'OUTPUT job_id="{job.job_id}" file="{response.file_name}" templates="{",".join(response.template_ids)}"'
            )

            db = SessionLocal()
            db_record = ImageRecord(
                result_id=response.file_name.split(".")[0],
                public_url=public_url,
                thumbnail_url=thumbnail_url,
                query=job.prompt,
                created_at=datetime.datetime.now(datetime.UTC),
                template_ids=",".join(response.template_ids),
            )
            db.add(db_record)
            db.commit()
            db.close()

            QUEUE_MANAGER.update_job_status(
                job.job_id,
                JobStatus.COMPLETED,
                result_url=public_url,
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
    generation_enabled = os.getenv("ENABLE_GENERATION", "false").lower() == "true"
    if not generation_enabled:
        raise HTTPException(
            status_code=503, detail="Meme generation is currently disabled"
        )
    job = QUEUE_MANAGER.create_job(request.prompt, request.selected_template_id)
    position = await QUEUE_MANAGER.enqueue(job)
    logger.info(
        f'QUERY job_id="{job.job_id}" template="{request.selected_template_id or "random"}" prompt="{request.prompt[:100]}"'
    )
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
        selected_template_id=job.selected_template_id,
        started_at=job.started_at,
        completed_at=job.completed_at,
        result_url=job.result_url,
        error=job.error,
    )


@APP.get("/api/v1/templates", response_model=List[TemplateInfo])
async def get_templates() -> List[TemplateInfo]:
    templates_path = str(TEMPLATES_PATH)
    env_templates_path = os.getenv("TEMPLATES_PATH")
    if env_templates_path:
        templates_path = env_templates_path

    templates_data = json.loads(Path(templates_path).read_text())
    # Filter to only include image templates, not video
    image_templates = [t for t in templates_data if t.get("type", "image") == "image"]
    return [
        TemplateInfo(
            id=t["id"],
            name=t["name"],
            description=t.get("description", ""),
        )
        for t in image_templates
    ]


@APP.get("/api/v1/gallery", response_model=GalleryResponse)
async def get_gallery(page: int = 1, page_size: int = 24) -> GalleryResponse:
    db = SessionLocal()
    try:
        # Ensure valid pagination parameters
        page = max(1, page)
        page_size = max(1, min(100, page_size))  # Max 100 items per page

        # Get total count
        total = db.query(ImageRecord).count()

        # Calculate total pages
        total_pages = (total + page_size - 1) // page_size if total > 0 else 1

        # Get paginated records
        offset = (page - 1) * page_size
        records = (
            db.query(ImageRecord)
            .order_by(ImageRecord.created_at.asc())
            .limit(page_size)
            .offset(offset)
            .all()
        )

        memes = [
            MemeInfo(
                result_id=r.result_id,
                public_url=r.public_url,
                thumbnail_url=r.thumbnail_url or r.public_url,
                query=r.query,
                created_at=r.created_at,
                template_ids=r.template_ids,
            )
            for r in records
        ]

        return GalleryResponse(
            memes=memes,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )
    finally:
        db.close()


@APP.get("/", response_class=HTMLResponse)
async def root() -> str:
    static_dir = Path(__file__).parent.parent / "static"
    index_path = static_dir / "index.html"
    if index_path.exists():
        return index_path.read_text()
    return "<h1>MEMETRON 3000</h1><p>Frontend not found</p>"


@APP.get("/gallery", response_class=HTMLResponse)
async def gallery() -> str:
    static_dir = Path(__file__).parent.parent / "static"
    gallery_path = static_dir / "gallery.html"
    if gallery_path.exists():
        return gallery_path.read_text()
    return "<h1>Gallery</h1><p>Gallery page not found</p>"


@APP.get("/api/v1/config", response_model=ConfigResponse)
async def get_config() -> ConfigResponse:
    generation_enabled = os.getenv("ENABLE_GENERATION", "false").lower() == "true"
    return ConfigResponse(generation_enabled=generation_enabled)


@APP.get("/health")
async def health_check() -> Dict[str, Any]:
    return {"status": "healthy", "timestamp": datetime.datetime.utcnow().isoformat()}


APP.mount("/output", StaticFiles(directory=STORAGE_PATH), name="output")


def main(host: str = "0.0.0.0", port: int = 8090) -> None:
    # Add filter to uvicorn access logger to exclude polling endpoints
    logging.getLogger("uvicorn.access").addFilter(EndpointFilter())
    uvicorn.run(APP, host=host, port=port)


if __name__ == "__main__":
    load_dotenv()
    fire.Fire(main)
