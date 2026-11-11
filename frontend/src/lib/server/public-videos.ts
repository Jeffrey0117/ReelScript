// Every public video, for the article list and the sitemap. The API pages at
// 100, so one request would silently drop everything past the first page.
import type { PublicVideo, PublicVideoList } from '$lib/api';
import { backendJson } from './backend';

const PAGE = 100;
const MAX_PAGES = 30;
const FRESH_MS = 5 * 60 * 1000;

let cached: { at: number; videos: PublicVideo[] } | null = null;

async function fetchAll(): Promise<PublicVideo[] | null> {
	const first = await backendJson<PublicVideoList>(`/api/public/videos?limit=${PAGE}&offset=0`);
	if (!first) return null;
	let videos = [...first.videos];
	for (let page = 1; page < MAX_PAGES && videos.length < first.total; page += 1) {
		const next = await backendJson<PublicVideoList>(`/api/public/videos?limit=${PAGE}&offset=${page * PAGE}`);
		// A page that fails means an incomplete list: report failure rather than
		// publish a sitemap with entries quietly missing.
		if (!next) return null;
		if (next.videos.length === 0) break;
		videos = [...videos, ...next.videos];
	}
	return videos;
}

// The list is identical for every visitor, so one answer serves them all for a
// few minutes. When a refresh fails the last good list is kept.
export async function allPublicVideos(now = Date.now()): Promise<PublicVideo[] | null> {
	if (cached && now - cached.at < FRESH_MS) return cached.videos;
	const videos = await fetchAll();
	if (videos) cached = { at: now, videos };
	return videos ?? cached?.videos ?? null;
}
