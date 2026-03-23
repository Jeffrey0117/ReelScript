from sqlalchemy import create_engine, Column, String, DateTime, Text, Integer, Float, Boolean, ForeignKey, JSON, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import uuid
import secrets
import string

DATABASE_URL = "sqlite:///./data/reelscript.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    pool_size=10,
    max_overflow=20,
    pool_timeout=30,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class User(Base):
    """Local cache of authenticated users (from LetMeUse JWT)."""
    __tablename__ = "users"

    id = Column(String, primary_key=True)  # JWT sub
    email = Column(String, nullable=True, index=True)
    name = Column(String, nullable=True)
    role = Column(String, default="user")
    avatar = Column(Text, nullable=True)
    first_seen_at = Column(DateTime, default=datetime.utcnow)
    last_seen_at = Column(DateTime, default=datetime.utcnow)


class Video(Base):
    __tablename__ = "videos"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    url = Column(Text, nullable=False)
    title = Column(String, nullable=True)
    source = Column(String, default="unknown")  # ig, youtube
    content_type = Column(String, default="video")  # video, lyrics
    duration = Column(Float, nullable=True)
    thumbnail = Column(Text, nullable=True)
    channel = Column(String, nullable=True)
    filename = Column(String, nullable=True)
    status = Column(String, default="pending")  # pending, downloading, transcribing, ready, failed
    error_message = Column(Text, nullable=True)
    category = Column(String, nullable=True)  # e.g. business, daily, tech, entertainment
    is_featured = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    transcript = relationship("Transcript", back_populates="video", uselist=False, cascade="all, delete-orphan")
    collection_items = relationship("CollectionItem", back_populates="video", cascade="all, delete-orphan")
    user_videos = relationship("UserVideo", back_populates="video", cascade="all, delete-orphan")


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
    user_id = Column(String, nullable=True, index=True)
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


class UserVideo(Base):
    __tablename__ = "user_videos"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, nullable=False, index=True)
    video_id = Column(String, ForeignKey("videos.id"), nullable=False)
    added_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (UniqueConstraint("user_id", "video_id", name="uq_user_video"),)

    video = relationship("Video", back_populates="user_videos")


class UserQuota(Base):
    __tablename__ = "user_quotas"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, nullable=False, index=True)
    period = Column(String, nullable=False)  # "2026-02"
    credits_used = Column(Integer, default=0)
    bonus_credits = Column(Integer, default=0)  # from invites
    plan = Column(String, default="free")  # "free" | "pro"

    __table_args__ = (UniqueConstraint("user_id", "period", name="uq_user_period"),)


def _generate_invite_code():
    chars = string.ascii_uppercase + string.digits
    return "".join(secrets.choice(chars) for _ in range(8))


class Subscription(Base):
    """Cached subscription state from PayGate webhooks."""
    __tablename__ = "subscriptions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, nullable=False, unique=True, index=True)
    plan = Column(String, default="free")  # "free" | "pro" | "unlimited"
    tier = Column(String, default="free")
    status = Column(String, default="active")  # "active" | "expired" | "cancelled"
    paygate_sub_id = Column(String, nullable=True)
    credits_per_month = Column(Integer, default=30)
    expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)


class Invite(Base):
    __tablename__ = "invites"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    inviter_id = Column(String, nullable=False, index=True)
    code = Column(String, unique=True, nullable=False, default=_generate_invite_code)
    used_by = Column(String, nullable=True)
    used_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


def init_db():
    Base.metadata.create_all(bind=engine)
    # Enable WAL mode for concurrent read/write access
    with engine.connect() as conn:
        from sqlalchemy import text, inspect
        conn.execute(text("PRAGMA journal_mode=WAL"))
        conn.execute(text("PRAGMA busy_timeout=5000"))
        conn.commit()
        inspector = inspect(engine)

        transcript_cols = [c["name"] for c in inspector.get_columns("transcripts")]
        if "appreciation" not in transcript_cols:
            conn.execute(text("ALTER TABLE transcripts ADD COLUMN appreciation JSON"))
            conn.commit()

        video_cols = [c["name"] for c in inspector.get_columns("videos")]
        if "category" not in video_cols:
            conn.execute(text("ALTER TABLE videos ADD COLUMN category VARCHAR"))
            conn.commit()
        if "is_featured" not in video_cols:
            conn.execute(text("ALTER TABLE videos ADD COLUMN is_featured BOOLEAN DEFAULT 0"))
            conn.commit()
        if "content_type" not in video_cols:
            conn.execute(text("ALTER TABLE videos ADD COLUMN content_type VARCHAR DEFAULT 'video'"))
            conn.commit()

        # Add user_id to collections if missing
        if "collections" in inspector.get_table_names():
            col_cols = [c["name"] for c in inspector.get_columns("collections")]
            if "user_id" not in col_cols:
                conn.execute(text("ALTER TABLE collections ADD COLUMN user_id VARCHAR"))
                conn.commit()

        # Migrate videos_used → credits_used (universal credit system)
        if "user_quotas" in inspector.get_table_names():
            quota_cols = [c["name"] for c in inspector.get_columns("user_quotas")]
            if "videos_used" in quota_cols and "credits_used" not in quota_cols:
                conn.execute(text("ALTER TABLE user_quotas ADD COLUMN credits_used INTEGER DEFAULT 0"))
                conn.execute(text("UPDATE user_quotas SET credits_used = videos_used * 10"))
                conn.commit()
            if "bonus_videos" in quota_cols and "bonus_credits" not in quota_cols:
                conn.execute(text("ALTER TABLE user_quotas ADD COLUMN bonus_credits INTEGER DEFAULT 0"))
                conn.execute(text("UPDATE user_quotas SET bonus_credits = bonus_videos * 6"))
                conn.commit()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
