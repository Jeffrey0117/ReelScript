// Typing-practice logic: compare one character, pick the blanks, keep score.
// Ported from takeENGLISH's public/typing-core.js (the /type page) so both
// sites grade typing the same way. Pure — no DOM — so it runs under node --test.

export interface Blank {
	from: number;
	to: number;
	word: string;
}

export interface TypingLine {
	text: string;
	start: number;
	end: number;
}

// Characters a keyboard cannot type → the one it can. Subtitles are full of
// curly quotes, dashes, full-width spaces and ellipses.
const SUBSTITUTES: Record<string, string> = {
	'’': "'",
	'‘': "'",
	'ʼ': "'",
	'´': "'",
	'′': "'",
	'`': "'",
	'“': '"',
	'”': '"',
	'–': '-',
	'—': '-',
	'−': '-',
	' ': ' ',
	'　': ' ',
	'…': '.',
};

// café → typing "e" counts. Otherwise one letter can deadlock a whole line.
export function norm(ch: string): string {
	const substitute = SUBSTITUTES[ch];
	if (substitute) return substitute;
	const base = ch.normalize('NFD').replace(/\p{M}/gu, '');
	return base || ch;
}

// Case-insensitive: you cannot hear capital letters.
export function same(a: string | undefined, b: string | undefined): boolean {
	return a !== undefined && b !== undefined && norm(a).toLowerCase() === norm(b).toLowerCase();
}

export function lineDone(typed: string, text: string): boolean {
	if (typed.length !== text.length) return false;
	for (let i = 0; i < text.length; i += 1) {
		if (!same(typed[i], text[i])) return false;
	}
	return true;
}

// The word under the cursor — recorded on a miss so the result can list them.
export function wordAt(text: string, index: number): string {
	if (index >= text.length) return '';
	let from = index;
	let to = index;
	while (from > 0 && /\S/.test(text[from - 1])) from -= 1;
	while (to < text.length && /\S/.test(text[to])) to += 1;
	return text.slice(from, to).trim();
}

// Words not worth blanking: articles, pronouns, auxiliaries.
const SKIP_WORDS = new Set(
	(
		'a an the and or but of to in on at for from with is are am was were be been it its this that these those ' +
		'i me my you your we us our he him his she her they them their so if as do does did not no up out can will just ' +
		'any all now too very oh yeah na la ooh hey'
	).split(' ')
);

function hash(text: string): number {
	let value = 5381;
	for (let i = 0; i < text.length; i += 1) value = ((value << 5) + value + text.charCodeAt(i)) >>> 0;
	return value;
}

export const isWeakWord = (word: string): boolean => SKIP_WORDS.has(String(word || '').toLowerCase());

export function wordSpans(text: string): Blank[] {
	const spans: Blank[] = [];
	for (const match of String(text || '').matchAll(/[A-Za-z][A-Za-z'’-]*/g)) {
		const from = match.index ?? 0;
		spans.push({ from, to: from + match[0].length, word: match[0] });
	}
	return spans;
}

// Dictation: the whole line stays visible, one or two key words are masked.
// The choice is deterministic (same line → same blanks) so a retry is a retry.
export function pickBlanks(text: string, count = 1): Blank[] {
	const spans = wordSpans(text);
	if (spans.length === 0) return [];
	const worth = (span: Blank, min: number) => span.word.length >= min && !SKIP_WORDS.has(span.word.toLowerCase());
	const long = spans.filter((s) => worth(s, 4));
	const medium = spans.filter((s) => worth(s, 3));
	const pool = long.length ? long : medium.length ? medium : spans;
	const want = Math.max(1, Math.min(count, pool.length));
	const start = hash(text) % pool.length;
	const order = [...pool.slice(start), ...pool.slice(0, start)];
	const picked: Blank[] = [];
	for (let i = 0; i < want; i += 1) picked.push(order[Math.floor((i * order.length) / want)]);
	return [...picked].sort((a, b) => a.from - b.from);
}

// Short line → one blank, long line → two, in between decided by the line's hash.
export function autoBlankCount(text: string): number {
	const count = wordSpans(text).length;
	if (count < 7) return 1;
	if (count >= 12) return 2;
	return hash(text) % 3 === 0 ? 2 : 1;
}

export function wholeLine(text: string): Blank[] {
	return text ? [{ from: 0, to: text.length, word: text }] : [];
}

const SEEK_LEAD_SECONDS = 4;

// After changing lines, should the media jump?
//   explicit (user clicked)            → always
//   already inside this line           → rewind to its start
//   far ahead (skipped several lines)  → jump forward
//   about to be spoken                 → leave it alone
export function needsSeek(
	seconds: number,
	line: TypingLine | null | undefined,
	explicit = false,
	lead = SEEK_LEAD_SECONDS
): boolean {
	if (explicit) return true;
	if (!line) return false;
	if (seconds > line.start) return true;
	return seconds < line.start - lead;
}

// Start a little early: subtitle start times lag behind the first syllable.
const LEAD_IN_SECONDS = 0.35;
export const seekTarget = (line: TypingLine | null | undefined, leadIn = LEAD_IN_SECONDS): number =>
	Math.max((line ? line.start : 0) - leadIn, 0);

// The line to practice at this time: the first one not finished yet.
export function lineIndexAt(seconds: number, lines: readonly TypingLine[]): number {
	if (!Array.isArray(lines) || lines.length === 0) return 0;
	const at = lines.findIndex((line) => seconds < line.end);
	return at === -1 ? lines.length - 1 : at;
}

export interface Score {
	begin(): void;
	stop(): void;
	key(correct: boolean, word?: string): void;
	lineCleared(text: string): void;
	reset(): void;
	seconds(): number;
	wpm(): number;
	accuracy(): number;
	top(n?: number): [string, number][];
}

// WPM by the old rule (5 characters = one word); accuracy = correct keys / all keys.
// Only time spent actually typing counts — intros and auto-pauses do not.
export function createScore({ now = Date.now }: { now?: () => number } = {}): Score {
	const misses = new Map<string, number>();
	let keys = 0;
	let wrong = 0;
	let correctChars = 0;
	let activeMs = 0;
	let segmentStart: number | null = null;

	function begin() {
		if (segmentStart === null) segmentStart = now();
	}

	function stop() {
		if (segmentStart === null) return;
		activeMs += now() - segmentStart;
		segmentStart = null;
	}

	function seconds() {
		return (activeMs + (segmentStart === null ? 0 : now() - segmentStart)) / 1000;
	}

	return {
		begin,
		stop,
		key(correct, word = '') {
			begin();
			keys += 1;
			if (correct) return;
			wrong += 1;
			if (word) misses.set(word, (misses.get(word) || 0) + 1);
		},
		lineCleared(text) {
			correctChars += text.length;
			stop();
		},
		reset() {
			misses.clear();
			keys = 0;
			wrong = 0;
			correctChars = 0;
			activeMs = 0;
			segmentStart = null;
		},
		seconds,
		wpm() {
			const minutes = seconds() / 60;
			return minutes > 0 ? Math.round(correctChars / 5 / minutes) : 0;
		},
		accuracy() {
			return keys > 0 ? Math.round(((keys - wrong) / keys) * 100) : 100;
		},
		top(n = 5) {
			return [...misses.entries()].sort((a, b) => b[1] - a[1]).slice(0, n);
		},
	};
}
