import os
import uuid
from io import BytesIO
from typing import List

from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from PIL import Image
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Show, Season, Episode, Artwork, ArtworkType, ContentStatus, PublishRun
from app.schemas import ShowOut, ValidationReport, ValidationIssue, ShowUpdate, PublishResponse

app = FastAPI(title="Peblo TV Mini API")

os.makedirs("media", exist_ok=True)
app.mount("/media", StaticFiles(directory="media"), name="media")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"message": "Peblo TV Mini API is running! Visit /docs for Swagger."}

@app.get("/health")
def health():
    return {"status": "ok", "service": "Peblo TV Mini"}

# 1. CMS endpoint: Fetch all shows (Draft & Published)
@app.get("/api/shows", response_model=List[ShowOut])
def get_shows(db: Session = Depends(get_db)):
    return db.query(Show).all()

# 2. Public Viewer endpoint: Only Published shows
@app.get("/api/viewer/shows", response_model=List[ShowOut])
def get_viewer_catalog(db: Session = Depends(get_db)):
    return db.query(Show).filter(Show.status == ContentStatus.PUBLISHED).all()

# 3. Update Show Metadata (Title, Category, Synopsis, Section)
@app.put("/api/shows/{show_id}", response_model=ShowOut)
def update_show(show_id: str, payload: ShowUpdate, db: Session = Depends(get_db)):
    try:
        show_uuid = uuid.UUID(show_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid show ID format")

    show = db.query(Show).filter(Show.id == show_uuid).first()
    if not show:
        raise HTTPException(status_code=404, detail="Show not found")
    
    if payload.title is not None:
        show.title = payload.title.strip()
    if payload.synopsis is not None:
        show.synopsis = payload.synopsis
    if payload.section is not None:
        show.section = payload.section
    if payload.category is not None:
        show.category = payload.category

    db.commit()
    db.refresh(show)
    return show

# 4. Resolve Content Group Conflict
@app.post("/api/episodes/{episode_id}/resolve")
def resolve_episode_conflict(episode_id: str, new_content_group: str, db: Session = Depends(get_db)):
    try:
        ep_uuid = uuid.UUID(episode_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid episode ID format")

    ep = db.query(Episode).filter(Episode.id == ep_uuid).first()
    if not ep:
        raise HTTPException(status_code=404, detail="Episode not found")
    
    ep.content_group = new_content_group.strip()
    db.commit()
    return {"status": "success", "message": f"Updated content_group to {new_content_group}"}

# 5. Validation Rules
@app.get("/api/validate", response_model=ValidationReport)
def validate_content(db: Session = Depends(get_db)):
    issues = []
    shows = db.query(Show).all()

    for s in shows:
        if not s.title or s.title.startswith("[Untitled Show"):
            issues.append(ValidationIssue(
                level="error",
                entity="show",
                id=str(s.id),
                message=f"Show '{s.title}' is missing a valid title."
            ))
        if not s.category or not s.category.strip():
            issues.append(ValidationIssue(
                level="warning",
                entity="show",
                id=str(s.id),
                message=f"Show '{s.title}' has no category assigned."
            ))

    episodes = db.query(Episode).all()
    for ep in episodes:
        if "_dup" in ep.content_group:
            issues.append(ValidationIssue(
                level="error",
                entity="episode",
                id=str(ep.id),
                message=f"Episode '{ep.title}' has a duplicate content_group key ({ep.content_group})."
            ))

    total_errors = sum(1 for i in issues if i.level == "error")
    total_warnings = sum(1 for i in issues if i.level == "warning")

    return ValidationReport(
        can_publish=(total_errors == 0),
        total_errors=total_errors,
        total_warnings=total_warnings,
        issues=issues
    )

# 6. Image Upload Validation (Max 200KB & 2:3 or 16:9 Aspect Ratio)
@app.post("/api/artworks/upload")
async def upload_artwork(
    parent_type: str = Form(...),
    parent_id: str = Form(...),
    slot_type: ArtworkType = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    try:
        parent_uuid = uuid.UUID(parent_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid parent ID format")

    contents = await file.read()
    file_size = len(contents)

    if file_size > 204800:
        raise HTTPException(
            status_code=400,
            detail=f"File size exceeds 200KB limit (Uploaded: {round(file_size / 1024, 2)} KB)."
        )

    try:
        img = Image.open(BytesIO(contents))
        width, height = img.size
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid image file.")

    ratio = width / height
    tolerance = 0.05

    if slot_type == ArtworkType.POSTER:
        if abs(ratio - (2 / 3)) > tolerance:
            raise HTTPException(status_code=400, detail=f"Invalid poster aspect ratio ({width}x{height}). Required: 2:3.")
    elif slot_type in [ArtworkType.BANNER, ArtworkType.THUMBNAIL]:
        if abs(ratio - (16 / 9)) > tolerance:
            raise HTTPException(status_code=400, detail=f"Invalid banner aspect ratio ({width}x{height}). Required: 16:9.")

    ext = os.path.splitext(file.filename)[1] or ".jpg"
    filename = f"{uuid.uuid4().hex}{ext}"
    filepath = os.path.join("media", filename)

    with open(filepath, "wb") as f:
        f.write(contents)

    artwork = Artwork(
        parent_type=parent_type,
        parent_id=parent_uuid,
        slot_type=slot_type,
        file_path=f"/media/{filename}",
        width=width,
        height=height,
        file_size_bytes=file_size
    )
    db.add(artwork)
    db.commit()

    return {
        "status": "success",
        "artwork_id": str(artwork.id),
        "url": artwork.file_path,
        "width": width,
        "height": height,
        "size_kb": round(file_size / 1024, 2)
    }

# 7. Atomic Publishing
@app.post("/api/publish", response_model=PublishResponse)
def atomic_publish(db: Session = Depends(get_db)):
    report = validate_content(db)
    if not report.can_publish:
        failed_run = PublishRun(
            published_by="admin",
            outcome="failed",
            error_message=f"Validation failed with {report.total_errors} blocking errors."
        )
        db.add(failed_run)
        db.commit()

        raise HTTPException(
            status_code=400,
            detail={
                "message": "Cannot publish: blocking errors exist.",
                "errors": [i.message for i in report.issues if i.level == "error"]
            }
        )

    try:
        shows = db.query(Show).all()
        episodes = db.query(Episode).all()

        for s in shows:
            s.status = ContentStatus.PUBLISHED
        for ep in episodes:
            ep.status = ContentStatus.PUBLISHED

        run_log = PublishRun(
            published_by="admin",
            outcome="success",
            shows_count=len(shows),
            episodes_count=len(episodes)
        )
        db.add(run_log)
        db.commit()

        return PublishResponse(
            status="success",
            message="All shows and episodes published atomically.",
            published_shows_count=len(shows),
            published_episodes_count=len(episodes)
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Atomic publish rolled back: {str(e)}")