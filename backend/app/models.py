import enum
import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Text, Integer, Enum, ForeignKey, 
    UniqueConstraint, DateTime
)
from sqlalchemy.types import TypeDecorator, CHAR
from sqlalchemy.orm import relationship
from app.database import Base

class GUID(TypeDecorator):
    impl = CHAR(36)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        return str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        return uuid.UUID(value)

class ContentStatus(str, enum.Enum):
    DRAFT = "draft"
    PUBLISHED = "published"

class ArtworkType(str, enum.Enum):
    POSTER = "poster"
    BANNER = "banner"
    THUMBNAIL = "thumbnail"

class Show(Base):
    __tablename__ = "shows"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    title = Column(String(255), nullable=False)
    synopsis = Column(Text, nullable=True)
    section = Column(String(100), nullable=True)
    category = Column(String(100), nullable=True)
    status = Column(Enum(ContentStatus), default=ContentStatus.DRAFT, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    seasons = relationship("Season", back_populates="show", cascade="all, delete-orphan")

class Season(Base):
    __tablename__ = "seasons"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    show_id = Column(GUID(), ForeignKey("shows.id", ondelete="CASCADE"), nullable=False)
    season_number = Column(Integer, nullable=False)
    title = Column(String(255), nullable=True)

    show = relationship("Show", back_populates="seasons")
    episodes = relationship("Episode", back_populates="season", cascade="all, delete-orphan")

class Episode(Base):
    __tablename__ = "episodes"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    season_id = Column(GUID(), ForeignKey("seasons.id", ondelete="CASCADE"), nullable=False)
    content_group = Column(String(100), nullable=False)
    language = Column(String(50), nullable=False)
    title = Column(String(255), nullable=False)
    synopsis = Column(Text, nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    status = Column(Enum(ContentStatus), default=ContentStatus.DRAFT, nullable=False)

    season = relationship("Season", back_populates="episodes")

    __table_args__ = (
        UniqueConstraint("content_group", "language", name="uq_content_group_language"),
    )

class Artwork(Base):
    __tablename__ = "artworks"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    parent_type = Column(String(50), nullable=False)
    parent_id = Column(GUID(), nullable=False)
    slot_type = Column(Enum(ArtworkType), nullable=False)
    file_path = Column(String(500), nullable=False)
    width = Column(Integer, nullable=False)
    height = Column(Integer, nullable=False)
    file_size_bytes = Column(Integer, nullable=False)

class PublishRun(Base):
    __tablename__ = "publish_runs"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    published_by = Column(String(100), nullable=False)
    shows_count = Column(Integer, default=0)
    episodes_count = Column(Integer, default=0)
    outcome = Column(String(50), nullable=False)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)