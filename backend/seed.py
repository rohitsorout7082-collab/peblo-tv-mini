import json
import os
import uuid
from app.database import engine, Base, SessionLocal
from app.models import Show, Season, Episode, ContentStatus

def run_seed():
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()

    seed_path = os.path.join("data", "seed_shows.json")
    if not os.path.exists(seed_path):
        print(f"Error: {seed_path} not found!")
        return

    with open(seed_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Clean existing records
    db.query(Episode).delete()
    db.query(Season).delete()
    db.query(Show).delete()
    db.commit()

    shows_map = {}
    seasons_map = {}
    seen_keys = set()
    ingested_episodes = 0
    duplicate_conflicts = 0

    # Handle both formats: list of flat episodes or list of shows
    rows = data if isinstance(data, list) else data.get("shows", [])

    for idx, row in enumerate(rows, 1):
        # 1. Get or create Show
        show_title = (row.get("show_title") or row.get("title") or f"[Untitled Show #{idx}]").strip()
        
        if show_title not in shows_map:
            show = Show(
                title=show_title,
                synopsis=row.get("show_synopsis") or row.get("synopsis"),
                section=row.get("section"),
                category=row.get("category"),
                status=ContentStatus.DRAFT
            )
            db.add(show)
            db.flush()
            shows_map[show_title] = show

        current_show = shows_map[show_title]

        # 2. Get or create Season
        s_num = row.get("season_number", 1)
        season_key = (current_show.id, s_num)
        if season_key not in seasons_map:
            season = Season(
                show_id=current_show.id,
                season_number=s_num,
                title="Trailers" if s_num == 0 else f"Season {s_num}"
            )
            db.add(season)
            db.flush()
            seasons_map[season_key] = season

        current_season = seasons_map[season_key]

        # 3. Check for (content_group, language) duplicate constraint
        cg = row.get("content_group") or f"cg_{uuid.uuid4().hex[:8]}"
        lang = (row.get("language") or "hi").strip().lower()
        key = (cg, lang)

        if key in seen_keys:
            duplicate_conflicts += 1
            # Append suffix so DB accepts it into Draft for CMS review
            cg_to_store = f"{cg}_dup{duplicate_conflicts}"
        else:
            cg_to_store = cg
            seen_keys.add(key)

        ep_title = (row.get("episode_title") or row.get("title") or "Untitled Episode").strip()

        episode = Episode(
            season_id=current_season.id,
            content_group=cg_to_store,
            language=lang,
            title=ep_title,
            synopsis=row.get("synopsis"),
            duration_seconds=row.get("duration_seconds"),
            status=ContentStatus.DRAFT
        )
        db.add(episode)
        ingested_episodes += 1

    db.commit()
    db.close()

    print(f"Seed complete:")
    print(f"- Total Shows: {len(shows_map)}")
    print(f"- Total Episodes: {ingested_episodes}")
    print(f"- Duplicate conflicts flagged: {duplicate_conflicts}")

if __name__ == "__main__":
    run_seed()
