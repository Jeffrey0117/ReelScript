from sqlalchemy import create_engine, Column, String, DateTime, Text, Integer, Float, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import uuid

DATABASE_URL = "sqlite:///./data/reelscript.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Video(Base):
    __tablename__ = "videos"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    url = Column(Text, nullable=False)
    title = Column(String, nullable=True)
    source = Column(String, default="unknown")  # ig, youtube
    duration = Column(Float, nullable=True)
    thumbnail = Column(Text, nullable=True)
    channel = Column(String, nullable=True)
    filename = Column(String, nullable=True)
    status = Column(String, default="pending")  # pending, downloading, transcribing, ready, failed
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    transcript = relationship("Transcript", back_populates="video", uselist=False, cascade="all, delete-orphan")
    collection_items = relationship("CollectionItem", back_populates="video", cascade="all, delete-orphan")


class Transcript(Base):
    __tablename__ = "transcripts"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    video_id = Column(String, ForeignKey("videos.id"), nullable=False, unique=True)
    language = Column(String, default="en")
    segments = Column(JSON, nullable=True)  # [{index, start, end, text, translation}]
    full_text = Column(Text, nullable=True)  # plain text version
    appreciation = Column(JSON, nullable=True)  # {theme, keyPoints, goldenQuotes}
    created_at = Column(DateTime, default=datetime.utcnow)

    video = relationship("Video", back_populates="transcript")


class Collection(Base):
    __tablename__ = "collections"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    items = relationship("CollectionItem", back_populates="collection", cascade="all, delete-orphan")


class CollectionItem(Base):
    __tablename__ = "collection_items"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    collection_id = Column(String, ForeignKey("collections.id"), nullable=False)
    video_id = Column(String, ForeignKey("videos.id"), nullable=False)
    notes = Column(Text, nullable=True)
    added_at = Column(DateTime, default=datetime.utcnow)

    collection = relationship("Collection", back_populates="items")
    video = relationship("Video", back_populates="collection_items")


def init_db():
    Base.metadata.create_all(bind=engine)
    # Migrate: add appreciation column if missing
    with engine.connect() as conn:
        from sqlalchemy import text, inspect
        inspector = inspect(engine)
        columns = [c["name"] for c in inspector.get_columns("transcripts")]
        if "appreciation" not in columns:
            conn.execute(text("ALTER TABLE transcripts ADD COLUMN appreciation JSON"))
            conn.commit()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
