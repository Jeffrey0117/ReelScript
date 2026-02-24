import { getToken } from '$lib/auth';

const DEV = import.meta.env.DEV;
const API_BASE = DEV ? 'http://localhost:4005' : '';

async function request<T>(path: string, options?: RequestInit): Promise<T> {
	const token = getToken();
	const headers: Record<string, string> = {
		'Content-Type': 'application/json',
	};
	if (token) {
		headers['Authorization'] = `Bearer ${token}`;
	}
	// Merge caller headers (e.g. X-Admin-Key for legacy admin)
	if (options?.headers) {
		const extra = options.headers instanceof Headers
			? Object.fromEntries(options.headers.entries())
			: options.headers as Record<string, string>;
		Object.assign(headers, extra);
	}
	const res = await fetch(`${API_BASE}${path}`, {
		...options,
		headers,
	});
	if (!res.ok) {
		const err = await res.json().catch(() => ({ detail: res.statusText }));
		const error = new Error(err.detail || `HTTP ${res.status}`) as Error & { status: number };
		error.status = res.status;
		throw error;
	}
	return res.json();
}

// Videos
export const processVideo = (url: string) =>
	request<{ success: boolean; video_id: string; title: string }>('/api/videos/process', {
		method: 'POST',
		body: JSON.stringify({ url }),
	});

export const listVideos = () =>
	request<Video[]>('/api/videos');

export const getVideo = (id: string) =>
	request<VideoDetail>(`/api/videos/${id}`);

export const deleteVideo = (id: string) =>
	request<{ success: boolean }>(`/api/videos/${id}`, { method: 'DELETE' });

export const renameVideo = (id: string, title: string) =>
	request<{ success: boolean; id: string; title: string }>(`/api/videos/${id}`, {
		method: 'PATCH',
		body: JSON.stringify({ title }),
	});

export const batchDeleteVideos = (videoIds: string[]) =>
	request<{ success: boolean; deleted_count: number }>('/api/videos/batch-delete', {
		method: 'POST',
		body: JSON.stringify({ video_ids: videoIds }),
	});

export const retryVideo = (id: string) =>
	request<{ success: boolean; video_id: string; status: string }>(`/api/videos/${id}/retry`, {
		method: 'POST',
	});

export const retryAllFailed = () =>
	request<{ retried: number; video_ids: string[] }>('/api/videos/retry-all-failed', {
		method: 'POST',
	});

export const backfillThumbnails = () =>
	request<{ success: boolean; generated: number; total: number }>('/api/videos/backfill-thumbnails', {
		method: 'POST',
	});

export const translateVideo = (id: string) =>
	request<{ success: boolean; segments: TranscriptSegment[] }>(`/api/videos/${id}/translate`, {
		method: 'POST',
	});

export const analyzeVocabulary = (id: string) =>
	request<{ success: boolean; segments: TranscriptSegment[] }>(`/api/videos/${id}/analyze-vocabulary`, {
		method: 'POST',
	});

export const appreciateVideo = (id: string) =>
	request<{ success: boolean; appreciation: Appreciation }>(`/api/videos/${id}/appreciate`, {
		method: 'POST',
	});

// Collections
export const createCollection = (name: string, description?: string) =>
	request<{ id: string; name: string }>('/api/collections', {
		method: 'POST',
		body: JSON.stringify({ name, description }),
	});

export const listCollections = () =>
	request<Collection[]>('/api/collections');

export const getCollection = (id: string) =>
	request<CollectionDetail>(`/api/collections/${id}`);

export const addToCollection = (collectionId: string, videoId: string, notes?: string) =>
	request<{ success: boolean }>(`/api/collections/${collectionId}/add`, {
		method: 'POST',
		body: JSON.stringify({ video_id: videoId, notes }),
	});

export const removeFromCollection = (collectionId: string, videoId: string) =>
	request<{ success: boolean }>(`/api/collections/${collectionId}/remove/${videoId}`, {
		method: 'DELETE',
	});

export const deleteCollection = (id: string) =>
	request<{ success: boolean }>(`/api/collections/${id}`, { method: 'DELETE' });

// Quota
export const getQuota = () =>
	request<Quota>('/api/quota');

// Invite
export const getMyInviteCode = () =>
	request<{ code: string }>('/api/invite/my-code');

export const redeemInvite = (code: string) =>
	request<{ success: boolean; bonus: number }>('/api/invite/redeem', {
		method: 'POST',
		body: JSON.stringify({ code }),
	});

// Admin — Bearer token auto-injected by request(), X-Admin-Key for legacy fallback
export const adminStats = (adminKey = '') =>
	request<AdminStats>('/api/admin/stats', {
		headers: adminKey ? { 'X-Admin-Key': adminKey } : {},
	});

export const adminListVideos = (adminKey = '', params?: Record<string, string>) => {
	const query = params ? '?' + new URLSearchParams(params).toString() : '';
	return request<AdminVideo[]>(`/api/admin/videos${query}`, {
		headers: adminKey ? { 'X-Admin-Key': adminKey } : {},
	});
};

export const adminUpdateVideo = (adminKey = '', videoId: string, data: { category?: string; is_featured?: boolean; title?: string }) =>
	request<{ success: boolean }>(`/api/admin/videos/${videoId}`, {
		method: 'PATCH',
		headers: adminKey ? { 'X-Admin-Key': adminKey } : {},
		body: JSON.stringify(data),
	});

export const adminDeleteVideo = (adminKey = '', videoId: string) =>
	request<{ success: boolean }>(`/api/admin/videos/${videoId}`, {
		method: 'DELETE',
		headers: adminKey ? { 'X-Admin-Key': adminKey } : {},
	});

// Public API (no auth required)
export const publicVideos = (featured = false) =>
	request<PublicVideoList>(`/api/public/videos?limit=100${featured ? '&featured=true' : ''}`);

export const publicArticle = (id: string) =>
	request<ArticleData>(`/api/public/videos/${id}/article`);

export const publicAudio = (id: string) =>
	request<AudioData>(`/api/public/videos/${id}/audio`);

// Video file URL (cache key changes when videos are re-encoded)
export const videoFileUrl = (filename: string) => `${API_BASE}/videos/${filename}?v=5`;

// Thumbnail URL — local file served from /thumbnails/
export const thumbnailUrl = (thumb: string) => `${API_BASE}/thumbnails/${thumb}`;

// Audio file URL
export const audioFileUrl = (path: string) => `${API_BASE}${path}`;

// WebSocket
export function connectWS(onMessage: (data: Record<string, unknown>) => void): WebSocket {
	const wsProtocol = DEV ? 'ws' : (location.protocol === 'https:' ? 'wss' : 'ws');
	const wsHost = DEV ? 'localhost:4005' : location.host;
	const ws = new WebSocket(`${wsProtocol}://${wsHost}/ws`);
	ws.onmessage = (event) => {
		try {
			onMessage(JSON.parse(event.data));
		} catch {
			// ignore parse errors
		}
	};
	ws.onclose = () => {
		// Auto-reconnect after 3s
		setTimeout(() => connectWS(onMessage), 3000);
	};
	return ws;
}

// Types
export interface Video {
	id: string;
	url: string;
	title: string | null;
	source: string;
	duration: number | null;
	thumbnail: string | null;
	channel: string | null;
	status: string;
	error_message: string | null;
	created_at: string | null;
}

export interface VocabularyItem {
	word: string;
	translation: string;
}

export interface TranscriptSegment {
	index: number;
	start: number;
	end: number;
	text: string;
	translation: string;
	vocabulary: VocabularyItem[];
}

export interface GoldenQuote {
	en: string;
	zh: string;
}

export interface Appreciation {
	theme: string;
	keyPoints: string[];
	goldenQuotes: GoldenQuote[];
}

export interface VideoDetail extends Video {
	filename: string | null;
	transcript: {
		language: string;
		segments: TranscriptSegment[];
		full_text: string;
		appreciation: Appreciation | null;
	} | null;
}

export interface Quota {
	plan: string;
	period: string;
	videos_used: number;
	bonus_videos: number;
	limit: number;
	remaining: number;
}

export interface Collection {
	id: string;
	name: string;
	description: string | null;
	video_count: number;
	created_at: string | null;
}

export interface AdminStats {
	total_videos: number;
	ready_videos: number;
	failed_videos: number;
	featured_count: number;
	total_collections: number;
	sources: Record<string, number>;
	categories: Record<string, number>;
}

export interface AdminVideo extends Video {
	category: string | null;
	is_featured: boolean;
}

export interface PublicVideoList {
	total: number;
	offset: number;
	limit: number;
	videos: PublicVideo[];
}

export interface PublicVideo {
	id: string;
	title: string | null;
	source: string;
	channel: string | null;
	duration: number | null;
	thumbnail: string | null;
	category: string | null;
	hasTranscript: boolean;
	hasAppreciation: boolean;
	createdAt: string | null;
}

export interface ArticleSegment {
	index: number;
	timestamp: string;
	en: string;
	zh: string;
}

export interface ArticleData {
	videoId: string;
	title: string | null;
	source: string;
	channel: string | null;
	duration: number | null;
	theme: string;
	keyPoints: string[];
	goldenQuotes: GoldenQuote[];
	segments: ArticleSegment[];
	vocabulary: VocabularyItem[];
	fullText: string;
}

export interface AudioData {
	videoId: string;
	title: string | null;
	channel: string | null;
	duration: number | null;
	audioUrl: string;
	segments: { index: number; start: number; end: number; en: string; zh: string }[];
}

export interface CollectionDetail {
	id: string;
	name: string;
	description: string | null;
	videos: {
		item_id: string;
		video_id: string;
		title: string | null;
		source: string;
		duration: number | null;
		thumbnail: string | null;
		channel: string | null;
		status: string;
		notes: string | null;
		added_at: string | null;
	}[];
}
