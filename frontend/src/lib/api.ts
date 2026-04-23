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
	request<{ success: boolean; video_id: string; title: string; status?: string }>('/api/videos/process', {
		method: 'POST',
		body: JSON.stringify({ url }),
	});

export const batchProcessVideos = (urls: string[]) =>
	request<BatchProcessResult>('/api/videos/batch-process', {
		method: 'POST',
		body: JSON.stringify({ urls }),
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

export const adminListUsers = (adminKey = '', params?: Record<string, string>) => {
	const query = params ? '?' + new URLSearchParams(params).toString() : '';
	return request<AdminUser[]>(`/api/admin/users${query}`, {
		headers: adminKey ? { 'X-Admin-Key': adminKey } : {},
	});
};

export const adminGetUser = (adminKey = '', userId: string) =>
	request<AdminUserDetail>(`/api/admin/users/${userId}`, {
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

// Speaking Coach file URL (uploaded recordings)
export const speakingFileUrl = (filename: string) => `${API_BASE}/speaking/files/${filename}`;

export const uploadSpeaking = async (file: File): Promise<{ success: boolean; session_id: string; status: string }> => {
	const token = getToken();
	const formData = new FormData();
	formData.append('file', file);
	const headers: Record<string, string> = {};
	if (token) {
		headers['Authorization'] = `Bearer ${token}`;
	}
	const res = await fetch(`${API_BASE}/api/speaking/upload`, {
		method: 'POST',
		headers,
		body: formData,
	});
	if (!res.ok) {
		const err = await res.json().catch(() => ({ detail: res.statusText }));
		const error = new Error(err.detail || `HTTP ${res.status}`) as Error & { status: number };
		error.status = res.status;
		throw error;
	}
	return res.json();
};

export const listSpeaking = () =>
	request<SpeakingSession[]>('/api/speaking');

export const getSpeaking = (id: string) =>
	request<SpeakingSessionDetail>(`/api/speaking/${id}`);

export const deleteSpeaking = (id: string) =>
	request<{ success: boolean }>(`/api/speaking/${id}`, { method: 'DELETE' });

// WebSocket
export function connectWS(onMessage: (data: Record<string, unknown>) => void): WebSocket {
	const wsProtocol = DEV ? 'ws' : (location.protocol === 'https:' ? 'wss' : 'ws');
	const wsHost = DEV ? 'localhost:4005' : location.host;
	const token = getToken();
	const wsUrl = token
		? `${wsProtocol}://${wsHost}/ws?token=${encodeURIComponent(token)}`
		: `${wsProtocol}://${wsHost}/ws`;
	const ws = new WebSocket(wsUrl);
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
	credits_used: number;
	bonus_credits: number;
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
	total_users: number;
	active_users_30d: number;
	plan_breakdown: Record<string, number>;
}

export interface AdminVideoUploader {
	id: string;
	email: string | null;
	name: string | null;
}

export interface AdminVideo extends Video {
	category: string | null;
	is_featured: boolean;
	uploader: AdminVideoUploader | null;
}

export interface AdminUser {
	id: string;
	email: string | null;
	name: string | null;
	role: string;
	avatar: string | null;
	plan: string;
	video_count: number;
	credits_used: number;
	credits_limit: number;
	first_seen_at: string | null;
	last_seen_at: string | null;
}

export interface AdminUserVideo {
	id: string;
	title: string | null;
	source: string;
	status: string;
	thumbnail: string | null;
	created_at: string | null;
}

export interface AdminUserDetail {
	user: {
		id: string;
		email: string | null;
		name: string | null;
		role: string;
		avatar: string | null;
		first_seen_at: string | null;
		last_seen_at: string | null;
	};
	plan: string;
	videos: AdminUserVideo[];
	quota_history: { period: string; credits_used: number; bonus_credits: number }[];
	invite: { code: string; redeemed_count: number } | null;
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

export interface BatchProcessResultItem {
	url: string;
	success: boolean;
	video_id?: string;
	title?: string;
	status?: string;
	duplicate?: boolean;
	error?: string;
}

export interface BatchProcessResult {
	success: boolean;
	results: BatchProcessResultItem[];
	total: number;
	started: number;
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

// Speaking Coach
export interface SpeakingIssue {
	type: 'grammar' | 'word_choice' | 'naturalness' | 'pronunciation_hint';
	highlight: string;
	explanation: string;
}

export interface CoachingSentence {
	index: number;
	original: string;
	corrected: string;
	issues: SpeakingIssue[];
	native_alt: string;
	score: number;
}

export interface CoachingResult {
	sentences: CoachingSentence[];
	overall: {
		fluency: number;
		grammar: number;
		vocabulary: number;
		naturalness: number;
		summary: string;
		strengths: string[];
		improvements: string[];
	};
}

export interface SpeakingSession {
	id: string;
	title: string | null;
	duration: number | null;
	status: string;
	error_message: string | null;
	created_at: string | null;
	overall_score: number | null;
}

export interface SpeakingSegment {
	index: number;
	start: number;
	end: number;
	text: string;
}

export interface SpeakingSessionDetail extends Omit<SpeakingSession, 'overall_score'> {
	filename: string;
	segments: SpeakingSegment[];
	coaching: CoachingResult | null;
}
