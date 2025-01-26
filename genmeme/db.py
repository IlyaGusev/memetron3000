from sqlalchemy import create_engine, Column, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

SQL_DATABASE_URL = "sqlite:///./images.db"
SQL_ENGINE = create_engine(SQL_DATABASE_URL)
SessionLocal = sessionmaker(bind=SQL_ENGINE)
Base = declarative_base()


class ImageRecord(Base):  # type: ignore
    __tablename__ = "images"
    result_id = Column(String, primary_key=True)
    image_url = Column(String)
    public_url = Column(String)


Base.metadata.create_all(SQL_ENGINE)
