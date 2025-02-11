from typing import Optional
from datetime import datetime

from sqlalchemy import create_engine, String, DateTime
from sqlalchemy.orm import DeclarativeBase, sessionmaker, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class ImageRecord(Base):
    __tablename__ = "images"
    result_id: Mapped[str] = mapped_column(String, primary_key=True)
    image_url: Mapped[str]
    public_url: Mapped[str]
    query: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    label: Mapped[Optional[str]] = mapped_column(
        String, nullable=True, default="UNDEFINED"
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    captions: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    template_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)


SQL_DATABASE_URL = "sqlite:///./images.db"
SQL_ENGINE = create_engine(SQL_DATABASE_URL)
SessionLocal = sessionmaker(bind=SQL_ENGINE)
Base.metadata.create_all(SQL_ENGINE)
