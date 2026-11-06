"""
Internal annotation bridge — 給姊妹站(takeENGLISH)用的「點字就懂」引擎。

POST /api/internal/annotate
  Authorization: Bearer <ANNOTATE_TOKEN>
  { "sentences": ["Once you break their trust, that's it.", ...] }
→ { "success": true, "items": [ { "translation": "…", "vocabulary": [ {"word","translation"} ] }, ... ] }

items 與 sentences 一一對應。直接重用本站的翻譯(services/translator)與
單字片語解析(services/vocabulary),所以兩邊的標註品質永遠一致。

這支會花 LLM 的錢,所以只認內部金鑰;ANNOTATE_TOKEN 沒設就整支停用(fail closed)。
呼叫端自己負責快取,同一段不要重複送。
"""

import os
import hmac
import asyncio
import logging

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

from services.translator import translate_segments
from services.vocabulary import analyze_segments

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/internal", tags=["internal"])

MAX_SENTENCES = 60
MAX_SENTENCE_CHARS = 600


class AnnotateRequest(BaseModel):
    sentences: list[str]


def _require_token(authorization: str | None) -> None:
    token = os.environ.get("ANNOTATE_TOKEN", "")
    if not token:
        raise HTTPException(status_code=503, detail="Annotation bridge not configured")
    supplied = ""
    if authorization and authorization.startswith("Bearer "):
        supplied = authorization[7:]
    if not supplied or not hmac.compare_digest(supplied, token):
        raise HTTPException(status_code=401, detail="Invalid annotation token")


@router.post("/annotate")
async def annotate(req: AnnotateRequest, authorization: str | None = Header(default=None)):
    _require_token(authorization)

    sentences = [s.strip() for s in req.sentences]
    if not sentences or len(sentences) > MAX_SENTENCES:
        raise HTTPException(status_code=400, detail=f"Send between 1 and {MAX_SENTENCES} sentences")
    if any(not s or len(s) > MAX_SENTENCE_CHARS for s in sentences):
        raise HTTPException(status_code=400, detail=f"Each sentence must be 1-{MAX_SENTENCE_CHARS} characters")

    segments = [{"text": s} for s in sentences]
    loop = asyncio.get_event_loop()
    try:
        # 兩個都是同步的 LLM 呼叫,丟到執行緒裡同時跑,不要卡住事件迴圈
        translated, analyzed = await asyncio.gather(
            loop.run_in_executor(None, translate_segments, segments),
            loop.run_in_executor(None, analyze_segments, segments),
        )
    except Exception as exc:  # LLM 供應商全掛等
        logger.error("annotate failed: %s", exc)
        raise HTTPException(status_code=502, detail="Annotation engine failed")

    if len(translated) != len(sentences) or len(analyzed) != len(sentences):
        logger.error("annotate returned %d/%d items for %d sentences", len(translated), len(analyzed), len(sentences))
        raise HTTPException(status_code=502, detail="Annotation engine returned a mismatched result")

    items = [
        {
            "translation": str(translated[i].get("translation") or ""),
            "vocabulary": [
                {"word": str(v.get("word") or ""), "translation": str(v.get("translation") or "")}
                for v in (analyzed[i].get("vocabulary") or [])
                if isinstance(v, dict)
            ],
        }
        for i in range(len(sentences))
    ]
    return {"success": True, "items": items}
