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
import re
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
_SENTENCE_END = re.compile(r"[.!?]$")


class AnnotateRequest(BaseModel):
    sentences: list[str]


def _require_token(authorization: str | None) -> None:
    token = os.environ.get("ANNOTATE_TOKEN", "")
    if not token:
        raise HTTPException(status_code=503, detail="Annotation bridge not configured")
    supplied = ""
    if authorization and authorization.startswith("Bearer "):
        supplied = authorization[7:]
    # 轉成 bytes 再比:標頭裡有非 ASCII 字元時 compare_digest 會丟 TypeError
    if not supplied or not hmac.compare_digest(supplied.encode("utf-8"), token.encode("utf-8")):
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
    # translate_segments 會把「沒有句尾標點」的句子跟後面的併成一句來翻,
    # 譯文只放在第一句、其餘留空。這支接口要的是一句對一句,
    # 所以送去翻譯的那一份先補上句點,確保每一句各自成句。
    to_translate = [{"text": s if _SENTENCE_END.search(s) else s + "."} for s in sentences]
    loop = asyncio.get_running_loop()
    try:
        # 兩個都是同步的 LLM 呼叫,丟到執行緒裡同時跑,不要卡住事件迴圈
        translated, analyzed = await asyncio.gather(
            loop.run_in_executor(None, translate_segments, to_translate),
            loop.run_in_executor(None, analyze_segments, segments),
        )
    except Exception as exc:  # LLM 供應商全掛等
        logger.error("annotate failed: %s", exc)
        raise HTTPException(status_code=502, detail="Annotation engine failed")

    if len(translated) != len(sentences) or len(analyzed) != len(sentences):
        logger.error("annotate returned %d/%d items for %d sentences", len(translated), len(analyzed), len(sentences))
        raise HTTPException(status_code=502, detail="Annotation engine returned a mismatched result")
    # 翻譯批次失敗時 translate_segments 會回空字串而不是丟錯。
    # 呼叫端會把結果永久存檔,所以不完整的結果寧可整包算失敗,讓它之後重試。
    if any(not str(t.get("translation") or "").strip() for t in translated):
        logger.error("annotate: translation came back empty for some of %d sentences", len(sentences))
        raise HTTPException(status_code=502, detail="Annotation engine returned an incomplete translation")

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
