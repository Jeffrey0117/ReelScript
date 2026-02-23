# ReelScript

Video learning platform that turns Instagram Reels and YouTube videos into interactive study material with transcription, translation, and sentence-level repetition.

> Sister project of [LetMeUse](https://github.com/Jeffrey0117/LetMeUse) - uses it for user authentication.

## Features

- **Video Import** - Paste an IG Reel or YouTube URL to download and process
- **Auto Transcription** - Speech-to-text with word-level timestamps
- **Interactive Transcript** - Click any sentence to seek the video
- **Study Mode** - Loop sentences, repeat, and translate for language practice
- **Collections** - Organize videos into custom playlists
- **IG Mode** - Browse videos in a social media-style carousel
- **Shared Video Pool** - Videos processed once, reused across users (deduplication)
- **Real-time Progress** - WebSocket updates during video processing
- **Quota System** - Free tier with monthly upload limits
- **Invite System** - Users can invite others to join
- **i18n** - English and Chinese
- **PWA** - Installable as a mobile app

## Pages

| Route | Description |
|-------|-------------|
| `/` | Home - video upload, library, quota stats |
| `/watch/[id]` | Video player with synchronized transcript panel |
| `/study/[id]` | Study mode - loop, repeat, translate sentences |
| `/collections` | Organize videos into collections |
| `/ig` | Instagram-style carousel viewer |
| `/admin` | Admin dashboard - video management, user stats |

## Architecture

```
server.js (Node.js, port 4005)
  ├── /api/*     → FastAPI backend (Python, port 5005)
  ├── /videos/*  → Static file serving with HTTP Range
  ├── /thumbnails/* → Static file serving
  └── /*         → SvelteKit frontend
```

- **Frontend**: SvelteKit 2 + Svelte 5 (TypeScript)
- **Backend**: Python FastAPI (video download, transcription, translation)
- **Auth**: [LetMeUse](https://github.com/Jeffrey0117/LetMeUse) SDK (JWT)
- **Proxy**: Node.js http-proxy routing all services through one port

## Quick Start

```bash
# Install frontend dependencies
cd frontend && npm install && cd ..

# Install root dependencies (proxy server)
npm install

# Build frontend
cd frontend && npm run build && cd ..

# Start (runs backend + frontend)
npm start
```

The server starts on port 4005 (configurable via `REELSCRIPT_PORT` env var) and auto-launches the Python backend on port 5005.

## Auth Integration

ReelScript uses LetMeUse for authentication. The SDK is loaded in `frontend/src/app.html`:

```html
<script
  src="https://letmeuse.isnowfriend.com/letmeuse.js?v=5"
  data-app-id="app_3lXIxPKb"
  data-theme="auto"
  data-accent="#6366f1"
  data-locale="zh"
  data-mode="modal"
></script>
```

The SDK provides `window.letmeuse` with login/register/profile modals, auth state management, and JWT tokens for API calls.

## Tech Stack

- **Frontend**: SvelteKit 2, Svelte 5, TypeScript, Vite 7
- **Backend**: Python FastAPI, OpenAI Whisper (transcription)
- **Server**: Node.js http-proxy
- **Auth**: LetMeUse SDK (JWT, OAuth, email verification)
- **Storage**: Filesystem (videos, thumbnails, transcripts)

## Product Roadmap

ReelScript is the first phase of a multi-brand platform:

| Brand | Content Type | Status |
|-------|-------------|--------|
| **ReelScript** | IG Reels / TikTok (short form) | Active |
| **TubeScript** | YouTube (long form) | Planned |
| **DramaScript** | Drama / B-station (episodic) | Planned |
| **FilmScript** | Movies (cinematic) | Planned |

All brands share the same backend and video library.

## License

MIT
