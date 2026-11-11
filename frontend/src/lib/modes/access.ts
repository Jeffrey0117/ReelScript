// Where the learning modes stop for visitors and free members.
// This is the single place to change the numbers.
//
// Rule of the house: nothing is labelled "Pro" up front. Everyone can open
// every mode and really use it; the wall appears in the middle of using it.
// A member's own videos are never cut short.

export type Tier = 'guest' | 'free' | 'pro';

export interface Access {
	tier: Tier;
	owner: boolean;
}

/** What ran out when the wall appears. */
export type WallKind = 'lines' | 'words' | 'chinese' | 'print';

export interface Limits {
	/** Nothing is held back. */
	full: boolean;
	/** Transcript lines available in every mode. */
	lines: number;
	/** Words listed in the wordbook. */
	words: number;
	/** Chinese translation is shown. */
	chinese: boolean;
	/** The handout can be printed. */
	print: boolean;
}

/** Everything a mode needs to know about the wall, handed down by the watch page. */
export interface Gate {
	tier: Tier;
	/** Transcript lines held back (0 = nothing). */
	hiddenLines: number;
	/** Playback must not pass this second; null = no limit. */
	stopAt: number | null;
	chinese: boolean;
	print: boolean;
	/** Words the wordbook may list. */
	words: number;
	/** Open the wall as a dialog. */
	open: (kind: WallKind, count?: number) => void;
}

export const FULL: Limits = { full: true, lines: Infinity, words: Infinity, chinese: true, print: true };

export const TIER_LIMITS: Record<Exclude<Tier, 'pro'>, Limits> = {
	guest: { full: false, lines: 5, words: 6, chinese: false, print: false },
	free: { full: false, lines: 12, words: 12, chinese: true, print: false },
};

/** What a paid plan costs — shown on the wall. Charged amount lives in PayGate, not here. */
export const PRO_PRICE = 'NT$150';

// No access info (older server, failed lookup) is treated as a visitor.
export function limitsFor(access: Access | null | undefined): Limits {
	if (!access) return TIER_LIMITS.guest;
	if (access.owner || access.tier === 'pro') return FULL;
	return TIER_LIMITS[access.tier] ?? TIER_LIMITS.guest;
}

export interface Limited<T> {
	shown: T[];
	hidden: number;
}

export function applyLimit<T>(items: readonly T[], limit: number): Limited<T> {
	if (!Number.isFinite(limit) || items.length <= limit) return { shown: [...items], hidden: 0 };
	const keep = Math.max(0, Math.floor(limit));
	return { shown: items.slice(0, keep), hidden: items.length - keep };
}

// The moment playback reaches held-back material (start of the first hidden line).
export function lockedAt(items: readonly { start: number }[], limit: number): number | null {
	if (!Number.isFinite(limit) || items.length <= limit) return null;
	return items[Math.max(0, Math.floor(limit))]?.start ?? null;
}
