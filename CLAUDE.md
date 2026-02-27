# ReelScript

Video learning platform — download, transcribe, translate, and analyze video content.

## Stack

- FastAPI + Python (backend on port 5005)
- SvelteKit + TypeScript (frontend)
- Node.js reverse proxy (server.js on port 4005, proxies /api/* to Python)
- SQLite3 + SQLAlchemy ORM
- Whisper (distil-large-v3) for transcription
- OpenAI / Groq for translation + analysis
- yt-dlp for video download
- Port: 4005 (Node) → 5005 (Python backend = PORT + 1000)

## Run

```bash
npm run dev:frontend   # SvelteKit dev server
npm start              # Production (Node spawns Python backend)
npm run build          # Build SvelteKit frontend
```

Python backend is auto-started by server.js in production.

## Key Files

```
server.js                          — Node reverse proxy + SvelteKit handler

backend/
  main.py                         — FastAPI app entry
  config.json                     — Whisper model config
  api/
    video_routes.py               — Video processing, list, delete, retry
    public_routes.py              — Public content (articles, cards, search, snippets)
    collection_routes.py          — User collections
    quota_routes.py               — Usage quota
    invite_routes.py              — Invite/referral system
    admin_routes.py               — Admin operations
    websocket.py                  — Real-time progress
  services/
    downloader.py                 — yt-dlp + thumbnail generation
    transcriber.py                — Whisper integration
    translator.py                 — LLM translation (OpenAI/Groq)
    vocabulary.py                 — Vocabulary extraction
    appreciation.py               — Theme, key points, golden quotes
  models/database.py              — SQLAlchemy models

frontend/src/                      — SvelteKit app
data/                              — SQLite DB + media files
```

## API (Key Endpoints)

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/videos/process` | Download + transcribe + translate + analyze (async) |
| GET | `/api/videos` | List user's videos |
| GET | `/api/videos/:id` | Get video with transcript |
| POST | `/api/videos/:id/translate` | Translate transcript to Chinese |
| POST | `/api/videos/:id/analyze-vocabulary` | Extract vocabulary |
| POST | `/api/videos/:id/appreciate` | Generate theme + quotes |
| GET | `/api/public/videos/:id/article` | Blog-ready article (bilingual) |
| GET | `/api/public/videos/:id/cards` | Learning cards |
| GET | `/api/public/videos/:id/audio` | MP3 + bilingual timeline |
| GET | `/api/public/search` | Keyword or semantic search |
| GET | `/api/public/snippet/random` | Random learning snippet |
| GET | `/api/public/snippet/daily` | Daily featured snippet |
| GET | `/api/public/vocabulary` | Aggregated word list |
| GET | `/api/public/quotes` | Golden quotes collection |
| GET | `/api/public/videos` | Public video catalog |
| GET | `/api/quota` | User quota (plan, used, remaining) |

## Pipeline

Video processing is async: `process` → download → transcribe → translate → appreciate.
Real-time progress via WebSocket at `/ws`.

## Supported Sources

YouTube, Instagram, Bilibili, TikTok (via yt-dlp)

## CloudPipe

- Manifest: `data/manifests/reelscript.json` (15 tools)
- Auth: bearer (env: REELSCRIPT_TOKEN)
- Entry: `server.js`
