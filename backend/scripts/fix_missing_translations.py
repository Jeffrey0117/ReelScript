"""
Fix missing translations for videos that were transcribed but not translated.

This script:
1. Finds all videos with segments but missing translations
2. Runs the translation service on each video
3. Updates the database with translated segments
"""

import sys
import io
from pathlib import Path

# Fix Windows console encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from models import get_db, Video
from services.translator import translate_segments


def main():
    db = next(get_db())

    print("=== Finding Videos with Missing Translations ===\n")

    videos = db.query(Video).filter(Video.status == "ready").all()
    need_translation = []

    for v in videos:
        if not v.transcript or not v.transcript.segments:
            continue

        segments = v.transcript.segments
        translated_count = sum(1 for s in segments if s.get("translation"))

        # If less than 50% translated, consider it needing translation
        if translated_count < len(segments) * 0.5:
            need_translation.append(v)
            print(f"Found: {v.title}")
            print(f"  ID: {v.id}")
            print(f"  Segments: {len(segments)}, Translated: {translated_count}")

    if not need_translation:
        print("\n[OK] All videos are properly translated!")
        return

    print(f"\n[INFO] Total videos needing translation: {len(need_translation)}")
    print("\nStarting translation process...\n")

    success_count = 0
    error_count = 0

    for i, video in enumerate(need_translation, 1):
        print(f"[{i}/{len(need_translation)}] Translating: {video.title}")

        try:
            # Get transcript segments
            segments = video.transcript.segments

            # Translate
            print(f"  Calling translator for {len(segments)} segments...")
            translated = translate_segments(segments)

            # Count successful translations
            new_translated = sum(1 for s in translated if s.get("translation"))

            # Update database
            video.transcript.segments = translated

            # Mark as modified for SQLAlchemy to detect JSON change
            from sqlalchemy.orm.attributes import flag_modified
            flag_modified(video.transcript, "segments")

            db.commit()

            print(f"  [OK] Success! Translated: {new_translated}/{len(translated)} segments")
            success_count += 1

        except Exception as e:
            print(f"  [ERROR] {e}")
            error_count += 1
            db.rollback()

    print(f"\n=== Summary ===")
    print(f"[OK] Successfully translated: {success_count}")
    print(f"[ERROR] Failed: {error_count}")
    print(f"[INFO] Total processed: {len(need_translation)}")


if __name__ == "__main__":
    main()
