// Arranging a member's pile of videos: search, filter by source, and group by
// how long ago they were added. Pure, so `npm test` covers it.

export interface ShelfVideo {
	id: string;
	title: string | null;
	channel: string | null;
	source: string;
	created_at: string | null;
}

export type SourceFilter = 'all' | 'ig' | 'youtube';
export type AgeKey = 'today' | 'week' | 'month' | 'older';

export interface ShelfGroup<T> {
	key: AgeKey;
	videos: T[];
}

const DAY_MS = 24 * 60 * 60 * 1000;
const AGE_ORDER: readonly AgeKey[] = ['today', 'week', 'month', 'older'];

export function filterVideos<T extends ShelfVideo>(
	videos: readonly T[],
	{ query = '', source = 'all' }: { query?: string; source?: SourceFilter } = {}
): T[] {
	const needle = query.trim().toLowerCase();
	return videos.filter((video) => {
		if (source !== 'all' && video.source !== source) return false;
		if (!needle) return true;
		return `${video.title ?? ''} ${video.channel ?? ''}`.toLowerCase().includes(needle);
	});
}

export function countBySource(videos: readonly ShelfVideo[]): Record<SourceFilter, number> {
	return {
		all: videos.length,
		ig: videos.filter((v) => v.source === 'ig').length,
		youtube: videos.filter((v) => v.source === 'youtube').length,
	};
}

// Videos without a usable date go to "older" rather than disappearing.
export function ageOf(createdAt: string | null, now: number): AgeKey {
	const at = createdAt ? Date.parse(createdAt) : NaN;
	if (Number.isNaN(at)) return 'older';
	const age = now - at;
	if (age < DAY_MS) return 'today';
	if (age < 7 * DAY_MS) return 'week';
	if (age < 30 * DAY_MS) return 'month';
	return 'older';
}

// Keeps the incoming order inside each group and drops empty groups.
export function groupByAge<T extends ShelfVideo>(videos: readonly T[], now: number): ShelfGroup<T>[] {
	return AGE_ORDER.map((key) => ({
		key,
		videos: videos.filter((video) => ageOf(video.created_at, now) === key),
	})).filter((group) => group.videos.length > 0);
}
