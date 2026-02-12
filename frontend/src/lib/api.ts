const DEV = import.meta.env.DEV;
const API_BASE = DEV ? 'http://localhost:4005' : '';

async function request<T>(path: string, options?: RequestInit): Promise<T> {
	const res = await fetch(`${API_BASE}${path}`, {
		headers: { 'Content-Type': 'application/json' },
		...options,
	});
	if (!res.ok) {
		const err = await res.json().catch(() => ({ detail: res.statusText }));
		throw new Error(err.detail || `HTTP ${res.status}`);
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

// Video file URL
export const videoFileUrl = (filename: string) => `${API_BASE}/videos/${filename}`;

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

export interface Collection {
	id: string;
	name: string;
	description: string | null;
	video_count: number;
	created_at: string | null;
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
