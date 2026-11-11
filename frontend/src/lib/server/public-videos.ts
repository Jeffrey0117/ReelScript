// Every public video, for the article list and the sitemap. The API pages at
// 100, so one request would silently drop everything past the first page.
import type { PublicVideo, PublicVideoList } from '$lib/api';
import { backendJson } from './backend';

const PAGE = 100;
const MAX_PAGES = 30;

export async function allPublicVideos(): Promise<PublicVideo[] | null> {
	const first = await backendJson<PublicVideoList>(`/api/public/videos?limit=${PAGE}&offset=0`);
	if (!first) return null;
	let videos = [...first.videos];
	for (let page = 1; page < MAX_PAGES && videos.length < first.total; page += 1) {
		const next = await backendJson<PublicVideoList>(`/api/public/videos?limit=${PAGE}&offset=${page * PAGE}`);
		if (!next || next.videos.length === 0) break;
		videos = [...videos, ...next.videos];
	}
	return videos;
}
