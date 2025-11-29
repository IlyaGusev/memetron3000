import asyncio
import uuid
import datetime
from dataclasses import dataclass
from typing import Optional, Dict
from enum import Enum


class JobStatus(str, Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class Job:
    job_id: str
    prompt: str
    selected_template_id: Optional[str]
    status: JobStatus
    created_at: datetime.datetime
    started_at: Optional[datetime.datetime] = None
    completed_at: Optional[datetime.datetime] = None
    result_url: Optional[str] = None
    result_template_id: Optional[str] = None
    error: Optional[str] = None
    position: int = 0


class QueueManager:
    def __init__(self) -> None:
        self.queue: asyncio.Queue[Job] = asyncio.Queue()
        self.jobs: Dict[str, Job] = {}
        self.is_processing: bool = False

    def create_job(
        self, prompt: str, selected_template_id: Optional[str] = None
    ) -> Job:
        job_id = str(uuid.uuid4())
        job = Job(
            job_id=job_id,
            prompt=prompt,
            selected_template_id=selected_template_id,
            status=JobStatus.QUEUED,
            created_at=datetime.datetime.now(datetime.UTC),
        )
        self.jobs[job_id] = job
        return job

    async def enqueue(self, job: Job) -> int:
        await self.queue.put(job)
        position = self.queue.qsize()
        job.position = position
        return position

    def get_job(self, job_id: str) -> Optional[Job]:
        return self.jobs.get(job_id)

    def get_queue_size(self) -> int:
        return self.queue.qsize()

    def update_job_status(
        self,
        job_id: str,
        status: JobStatus,
        result_url: Optional[str] = None,
        result_template_id: Optional[str] = None,
        error: Optional[str] = None,
    ) -> None:
        job = self.jobs.get(job_id)
        if job:
            job.status = status
            if status == JobStatus.PROCESSING:
                job.started_at = datetime.datetime.now(datetime.UTC)
            elif status in (JobStatus.COMPLETED, JobStatus.FAILED):
                job.completed_at = datetime.datetime.now(datetime.UTC)
            if result_url:
                job.result_url = result_url
            if result_template_id:
                job.result_template_id = result_template_id
            if error:
                job.error = error
