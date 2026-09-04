from pydantic import BaseModel
from typing import List, Optional
from uuid import UUID

class EpisodeOut(BaseModel):
    id: UUID
    title: str
    content_group: str
    language: str
    duration_seconds: Optional[int] = None
    synopsis: Optional[str] = None
    status: str

    class Config:
        from_attributes = True

class SeasonOut(BaseModel):
    id: UUID
    season_number: int
    title: Optional[str] = None
    episodes: List[EpisodeOut] = []

    class Config:
        from_attributes = True

class ShowOut(BaseModel):
    id: UUID
    title: str
    synopsis: Optional[str] = None
    section: Optional[str] = None
    category: Optional[str] = None
    status: str
    seasons: List[SeasonOut] = []

    class Config:
        from_attributes = True

class ShowUpdate(BaseModel):
    title: Optional[str] = None
    synopsis: Optional[str] = None
    section: Optional[str] = None
    category: Optional[str] = None

class PublishResponse(BaseModel):
    status: str
    message: str
    published_shows_count: int
    published_episodes_count: int

class ValidationIssue(BaseModel):
    level: str  # "error" or "warning"
    entity: str
    id: str
    message: str

class ValidationReport(BaseModel):
    can_publish: bool
    total_errors: int
    total_warnings: int
    issues: List[ValidationIssue]