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
npm run preview        # Preview a frontend change on :4905 (live data, live build untouched)
npm test               # Unit tests for the watch-page mode logic
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

## Watch Page Modes

`/watch/:id` is one video in six modes, picked with `?mode=` (default `video`):

| Mode | Component | What it is |
|------|-----------|------------|
| `video` | `VideoMode` | Player left, clickable transcript right (the original page) |
| `read` | `ReadMode` | Article layout; 純英文 / 純中文 / 中英 / 中英對照（逐句） |
| `podcast` | `PodcastMode` | Audio only, lyric-style captions |
| `type` | `TypeMode` | Typing practice; engine ported from takeENGLISH `/type` |
| `vocab` | `VocabMode` | Two-page notebook, Chinese blurred until tapped |
| `handout` | `HandoutMode` | Printable worksheet (main idea, words, sentences, cloze) |

- Shell: `frontend/src/routes/watch/[id]/+page.svelte` loads the video once and hands it down.
  Components live in `frontend/src/lib/components/modes/`; each mode owns its whole look.
- On wide screens the modes sit in the site header (`+layout.svelte`, skin `nav`) and the site
  links fold into the menu button; under 900px the in-page switcher shows instead.
- `ModeSwitcher` restyles itself per mode (`data-skin`) when shown in the page. Adding a mode = id in
  `lib/modes/text.ts` (`MODE_IDS` + copy), an icon and a skin in `ModeSwitcher`, a branch in the shell.
- Pure logic is in `lib/lesson.ts` and `lib/typing-core.ts`, tested with `npm test` (in `frontend/`).
- Modes never call AI on their own. The wordbook fills gaps from the offline dictionary
  (`/api/public/dict/:word`); translate / summary are buttons the user presses.
- `npm run preview` (repo root) builds into `frontend/build-preview` and serves it on :4905
  against the running server's data — look at a frontend change without touching the live build.

## Access Wall (visitors / free members / paid)

- Numbers live in one file: `frontend/src/lib/modes/access.ts` (`TIER_LIMITS`). Today:
  visitor 5 lines, no Chinese · free member 12 lines · paid plan, admin, or the video's
  owner: everything. Printing the handout is paid.
- `GET /api/videos/:id` returns `access: {tier, owner}` (`_access` in `video_routes.py`).
  The watch shell slices the transcript once and hands every mode a `gate`; modes show
  `ModeWall` where the material runs out, and playback stops at `gate.stopAt`.
- House rules (paywall-kit): no "Pro" labels on buttons, everyone can open every mode and
  really use it, the wall appears mid-use and is the only place that sells. Visitors get
  "free sign-in" + "see plans"; free members go straight to checkout.
- This is a UI wall. The API still returns the whole transcript and the media file is not
  protected, because the same text is public on `/blog/:id` for search engines. Making it a
  real wall means cutting the transcript in `get_video` and signing media URLs.

## SEO

- `/blog` and `/blog/:id` are rendered on the server (`+page.server.ts` →
  `lib/server/backend.ts`), so article text is in the HTML. If the backend read fails the
  page falls back to loading in the browser.
- `/sitemap.xml` and `/robots.txt` are generated routes (do not add `static/robots.txt` —
  a static file shadows the route). The host is taken from the request, never hard-coded.
- `SeoHead.svelte` sets title, description, canonical, share-preview tags and JSON-LD.
- Landing copy for the descriptive sections is in `lib/landing-text.ts`.

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

## AutoReel Import Bridge

`POST /api/import/autoreel` (backend/api/import_routes.py) — AutoReel 發完 IG 後把成品
(標題/IG 文案/雙語字幕/縮圖)推過來,直接落地成 status=ready 的 Video + Transcript,
跳過整條 download/whisper/translate 管線。IG 文案存在 appreciation.theme/igCaption。
Auth: Bearer = env `AUTOREEL_IMPORT_TOKEN`(backend/.env;與 AutoReel 端 REELSCRIPT_TOKEN 同值)。
以 source_url 去重,重送 = 更新(冪等)。進來的內容立即出現在 /blog、article、search。
