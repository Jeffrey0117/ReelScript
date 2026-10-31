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
    is_public = Column(Boolean, default=False)  # visible on public surfaces (blog, search, snippets)
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
    is_public = Column(Boolean, default=False)  # visible as a material pack on /packs
    is_official = Column(Boolean, default=False)  # admin-curated, listed first
    created_at = Column(DateTime, default=datetime.utcnow)

    items = relationship("CollectionItem", back_populates="collection", cascade="all, delete-orphan")


class SavedWord(Base):
    """A member's personal wordbook entry with Leitner SRS state."""
    __tablename__ = "saved_words"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, nullable=False, index=True)
    word = Column(String, nullable=False)
    meaning = Column(Text, nullable=True)
    example = Column(Text, nullable=True)
    video_id = Column(String, nullable=True)  # source video, informational only
    box = Column(Integer, default=1)  # Leitner box 1..5
    due_at = Column(DateTime, default=datetime.utcnow)
    reviews = Column(Integer, default=0)
    lapses = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (UniqueConstraint("user_id", "word", name="uq_user_word"),)


class SharedDeck(Base):
    """A published snapshot of wordbook entries, browsable by everyone."""
    __tablename__ = "shared_decks"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, nullable=False, index=True)
    author_name = Column(String, nullable=True)  # snapshot at publish time
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    saves_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    words = relationship("SharedDeckWord", back_populates="deck", cascade="all, delete-orphan")


class SharedDeckWord(Base):
    __tablename__ = "shared_deck_words"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    deck_id = Column(String, ForeignKey("shared_decks.id"), nullable=False, index=True)
    word = Column(String, nullable=False)
    meaning = Column(Text, nullable=True)
    example = Column(Text, nullable=True)
    position = Column(Integer, default=0)

    deck = relationship("SharedDeck", back_populates="words")


class DeckSave(Base):
    """Who saved which deck — dedupes the saves_count reputation metric."""
    __tablename__ = "deck_saves"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    deck_id = Column(String, nullable=False, index=True)
    user_id = Column(String, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (UniqueConstraint("deck_id", "user_id", name="uq_deck_save"),)


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


class SpeakingSession(Base):
    __tablename__ = "speaking_sessions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, nullable=False, index=True)
    title = Column(String, nullable=True)
    filename = Column(String, nullable=True)
    duration = Column(Float, nullable=True)
    status = Column(String, default="uploading")  # uploading, transcribing, analyzing, ready, failed
    error_message = Column(Text, nullable=True)
    segments = Column(JSON, nullable=True)  # [{index, start, end, text}]
    coaching = Column(JSON, nullable=True)  # LLM analysis result
    discourse = Column(JSON, nullable=True)  # Discourse analysis result
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
        if "is_public" not in video_cols:
            conn.execute(text("ALTER TABLE videos ADD COLUMN is_public BOOLEAN DEFAULT 0"))
            # Backfill: admin-owned videos (incl. legacy dev_admin) and ownerless
            # imports (AutoReel) were the public catalog before per-member isolation.
            conn.execute(text("""
                UPDATE videos SET is_public = 1 WHERE
                    id IN (
                        SELECT video_id FROM user_videos
                        WHERE user_id = 'dev_admin'
                           OR user_id IN (SELECT id FROM users WHERE role = 'admin')
                    )
                    OR id NOT IN (SELECT video_id FROM user_videos)
            """))
            conn.commit()

        # Add user_id to collections if missing
        if "collections" in inspector.get_table_names():
            col_cols = [c["name"] for c in inspector.get_columns("collections")]
            if "user_id" not in col_cols:
                conn.execute(text("ALTER TABLE collections ADD COLUMN user_id VARCHAR"))
                conn.commit()
            if "is_public" not in col_cols:
                conn.execute(text("ALTER TABLE collections ADD COLUMN is_public BOOLEAN DEFAULT 0"))
                conn.commit()
            if "is_official" not in col_cols:
                conn.execute(text("ALTER TABLE collections ADD COLUMN is_official BOOLEAN DEFAULT 0"))
                conn.commit()

        # Add discourse column to speaking_sessions if missing
        if "speaking_sessions" in inspector.get_table_names():
            speaking_cols = [c["name"] for c in inspector.get_columns("speaking_sessions")]
            if "discourse" not in speaking_cols:
                conn.execute(text("ALTER TABLE speaking_sessions ADD COLUMN discourse JSON"))
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
