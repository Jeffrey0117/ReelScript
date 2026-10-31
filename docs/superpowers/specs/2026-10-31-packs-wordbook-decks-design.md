# 教材包＋單字本(SRS)＋會員學習集 — 設計規格

> 2026-10-31 Jeff 核准「照順序開做 ①②③」。目標:官方教材鋪底 → 單字本複習黏住人 → 會員分享學習集點火 UGC 飛輪。

## ① 教材包 (Material Packs)

公開的「收藏集」就是教材包。官方(admin)標記 official 的排最前。

### 資料
- `collections` 加欄位:`is_public BOOLEAN DEFAULT 0`、`is_official BOOLEAN DEFAULT 0`(啟動時 ALTER TABLE 遷移,沿用既有 pattern)。

### API
- `PATCH /api/collections/{id}` (owner):name / description / is_public;`is_official` 僅 admin 可改。
- `GET /api/public/packs`:公開收藏集列表(official 優先、新→舊),帶 video_count(只計 is_public+ready 影片)、cover(第一支公開影片縮圖)、作者名。video_count=0 的不列。
- `GET /api/public/packs/{id}`:教材包詳情,只回 is_public+ready 的影片(會員私有影片不外洩)。

### 前端
- `/packs`:教材瀏覽頁(tab 1 = 教材包,tab 2 = 學習集,見③),訪客可看。
- `/packs/[id]`:教材包詳情 → 影片卡點進 /watch。
- `/collections`:每個收藏集加「公開/私人」切換;admin 多一個「官方」切換。
- navbar 加「教材」(登入與否都顯示),登入再加「單字本」。

### 限制(記載於此,接受)
- 會員上傳的影片是私有的 → 會員公開的教材包只會露出其中公開影片;會員 UGC 主力在③的單字學習集,不是影片包。

## ② 單字本 + SRS 複習 (Wordbook)

### 資料
- `saved_words`:id, user_id(idx), word, meaning, example(nullable), video_id(nullable), box INT default 1, due_at DATETIME default now, reviews INT default 0, lapses INT default 0, created_at。UNIQUE(user_id, word)——重複收藏=更新 meaning/example/video_id,不重置 SRS 進度。

### SRS:Leitner 5 盒
- 間隔(天):box1=1, box2=3, box3=7, box4=14, box5=30。
- 新字 box=1、due=now(立即可複習)。
- 答對:box=min(5, box+1),due=now+interval[新box]。
- 答錯:box=1,due=now+10分鐘,lapses+1。

### API (`/api/wordbook`,全部 require_auth)
- `POST /api/wordbook` {word, meaning, example?, video_id?} — upsert。
- `GET /api/wordbook` — 全列表(含 box/due)。
- `DELETE /api/wordbook/{id}`。
- `GET /api/wordbook/review?limit=20` — due_at <= now 的卡,box 小的優先。
- `POST /api/wordbook/{id}/review` {correct: bool} — 套用 Leitner,回新狀態。
- `GET /api/wordbook/export` — TSV(word \t meaning \t example),Anki 可直接匯入。(.apkg 之後再說)

### 前端
- `/wordbook`:統計(總數/今日待複習)+「開始複習」→ 翻卡模式(英文面 → 顯示答案 → 記得/忘記)+ 單字列表(刪除)+ 匯出 TSV + 發布學習集(③)。
- `/study/[id]` 單字卡加「＋收藏」按鈕(已收藏顯示 ✓);quota 零消耗。

## ③ 會員學習集 (Shared Decks)

發布 = 從單字本挑字做**快照**(之後改單字本不影響已發布的集)。

### 資料
- `shared_decks`:id, user_id(idx), author_name(發布時從 users.name/email 快照), title, description(nullable), saves_count INT default 0, created_at。
- `shared_deck_words`:id, deck_id(idx), word, meaning, example(nullable), position INT。
- `deck_saves`:deck_id, user_id,UNIQUE(deck_id, user_id)——防重複計數。

### API
- `POST /api/decks` {title, description?, word_ids[]} — 從自己單字本快照發布(1~500字)。
- `GET /api/decks/mine` — 我發布的集(管理/下架)。
- `DELETE /api/decks/{id}` (owner)。
- `POST /api/decks/{id}/save` (auth) — 整集 upsert 進我的單字本(不重置已有字的進度),deck_saves 首存才 saves_count+1。
- `GET /api/public/decks` — 公開列表(收藏數降冪、新→舊),帶字數/作者/前3字預覽。
- `GET /api/public/decks/{id}` — 詳情含全部字(訪客可看,存入需登入)。

### 前端
- `/packs` tab 2:學習集卡片(標題/作者/N 字/收藏數/預覽)。
- `/decks/[id]`:字表 +「存進我的單字本」(未登入→login())。
- `/wordbook`:「發布學習集」modal(勾選單字→標題/描述→發布→跳轉詳情頁)。

## 通用
- 不動 quota(收藏單字/複習/發布全免費)。
- i18n zh+en 全覆蓋。
- 不加新 python 依賴。
- 風格沿用現有 token(--accent/--bg-card/badge 等),灰階降噪,非零數字才上色。

## 驗收
- build 過、部署成功。
- 行為指紋:`GET /api/public/packs` 200;收藏單字→出現在 /wordbook→複習答對 box+1;發布集→公開頁可見→另一帳號(或 API)save→saves_count=1 且字進單字本。
