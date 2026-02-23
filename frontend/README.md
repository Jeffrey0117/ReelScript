# ReelScript

**Video learning platform.** Turn Instagram Reels and YouTube videos into interactive study material with transcription, translation, and sentence-level repetition.

**影片學習平台。** 將 IG Reels 和 YouTube 影片轉化為互動學習教材，支援逐字稿、翻譯和逐句複習。

> Powered by [LetMeUse](https://github.com/Jeffrey0117/LetMeUse) for user authentication.
> 使用 [LetMeUse](https://github.com/Jeffrey0117/LetMeUse) 進行使用者認證。

---

## Features / 功能

| Feature | Description |
|---------|-------------|
| **Video Import** | Paste an IG Reel or YouTube URL to download and process<br>貼上 IG Reel 或 YouTube 網址即可下載處理 |
| **Auto Transcription** | Speech-to-text with word-level timestamps<br>語音轉文字，精確到字詞級別的時間戳 |
| **Interactive Transcript** | Click any sentence to seek the video<br>點擊任意句子跳轉影片對應位置 |
| **Study Mode** | Loop sentences, repeat, translate for language practice<br>循環播放句子、複述、翻譯，語言學習專用 |
| **Collections** | Organize videos into custom playlists<br>將影片整理到自訂播放清單 |
| **IG Mode** | Browse videos in a social media-style carousel<br>以社群媒體風格瀏覽影片 |
| **Shared Pool** | Videos processed once, reused across users (deduplication)<br>影片只處理一次，跨使用者共享（去重） |
| **Real-time** | WebSocket progress updates during processing<br>處理時透過 WebSocket 即時更新進度 |
| **Quota System** | Free tier with monthly upload limits<br>免費方案有每月上傳限制 |
| **i18n** | English + Chinese / 英文 + 中文 |
| **PWA** | Installable as a mobile app / 可安裝為手機 App |

---

## Pages / 頁面

| Route | Description |
|-------|-------------|
| `/` | Home — upload, library, quota stats / 首頁 — 上傳、影片庫、配額 |
| `/watch/[id]` | Video player + synchronized transcript / 影片播放 + 同步逐字稿 |
| `/study/[id]` | Study mode — loop, repeat, translate / 學習模式 — 循環、複述、翻譯 |
| `/collections` | Organize videos / 影片整理 |
| `/ig` | IG-style carousel viewer / IG 風格瀏覽 |
| `/admin` | Admin dashboard / 管理面板 |

---

## Architecture / 架構

```
server.js (Node.js, port 4005)
  ├── /api/*         → FastAPI backend (Python, port 5005)
  ├── /videos/*      → Static file serving (HTTP Range)
  ├── /thumbnails/*  → Static file serving
  └── /*             → SvelteKit frontend
```

---

## Quick Start / 快速開始

```bash
cd frontend && npm install && cd ..
npm install
cd frontend && npm run build && cd ..
npm start    # Starts backend + frontend on port 4005
```

> Port configurable via `REELSCRIPT_PORT` env var.
> 可透過 `REELSCRIPT_PORT` 環境變數設定端口。

---

## Auth Integration / 認證整合

ReelScript uses [LetMeUse](https://github.com/Jeffrey0117/LetMeUse) for authentication. The SDK is loaded in `frontend/src/app.html`:

ReelScript 使用 [LetMeUse](https://github.com/Jeffrey0117/LetMeUse) 進行認證。SDK 載入於 `frontend/src/app.html`：

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

The SDK provides `window.letmeuse` with login / register / profile modals, auth state, and JWT tokens for API calls.

SDK 提供 `window.letmeuse`，包含登入/註冊/個人資料 Modal、認證狀態和 JWT Token。

---

## Tech Stack / 技術棧

| Category | Technology |
|----------|------------|
| Frontend | SvelteKit 2 + Svelte 5 + TypeScript + Vite 7 |
| Backend | Python FastAPI + OpenAI Whisper |
| Server | Node.js http-proxy |
| Auth | LetMeUse SDK (JWT, OAuth) |
| Storage | Filesystem (videos, thumbnails, transcripts) |

---

## Product Roadmap / 產品路線圖

ReelScript is the first phase of a multi-brand platform:
ReelScript 是多品牌平台的第一階段：

| Brand | Content | Status |
|-------|---------|--------|
| **ReelScript** | IG Reels / TikTok (short form) | Active |
| **TubeScript** | YouTube (long form) | Planned |
| **DramaScript** | Drama / B-station (episodic) | Planned |
| **FilmScript** | Movies (cinematic) | Planned |

All brands share the same backend and video library.
所有品牌共用同一個後端與影片庫。

## License

MIT
