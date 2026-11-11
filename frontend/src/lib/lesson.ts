// Pure helpers shared by every watch-page mode (read / podcast / type / vocab / handout).
// No Svelte, no DOM, no fetch — so `npm test` can run them directly under node.

import type { TranscriptSegment, VocabularyItem } from '$lib/api';

export interface Sentence {
	en: string;
	zh: string;
	vocabulary: VocabularyItem[];
	start: number;
	end: number;
}

export interface Timed {
	start: number;
	end: number;
}

const SENTENCE_END = /[.!?]["'”’)]*$/;

function toSentence(parts: TranscriptSegment[]): Sentence {
	return {
		en: parts.map((p) => p.text.trim()).join(' ').trim(),
		// Chinese translations already end with their own punctuation — join without a space.
		zh: parts.map((p) => (p.translation ?? '').trim()).filter(Boolean).join(''),
		vocabulary: parts.flatMap((p) => p.vocabulary ?? []),
		start: parts[0].start,
		end: parts[parts.length - 1].end,
	};
}

// Whisper cuts on breath, not on grammar. Glue fragments back together until
// one ends with sentence punctuation.
export function mergeSentences(segments: readonly TranscriptSegment[]): Sentence[] {
	const result: Sentence[] = [];
	let buffer: TranscriptSegment[] = [];
	for (const segment of segments) {
		if (!segment.text || !segment.text.trim()) continue;
		buffer = [...buffer, segment];
		if (SENTENCE_END.test(segment.text.trim())) {
			result.push(toSentence(buffer));
			buffer = [];
		}
	}
	if (buffer.length > 0) result.push(toSentence(buffer));
	return result;
}

export function uniqueVocabulary(segments: readonly TranscriptSegment[]): VocabularyItem[] {
	const seen = new Set<string>();
	const result: VocabularyItem[] = [];
	for (const item of segments.flatMap((s) => s.vocabulary ?? [])) {
		const key = item.word.trim().toLowerCase();
		if (!key || seen.has(key)) continue;
		seen.add(key);
		result.push(item);
	}
	return result;
}

export function toParagraphs<T>(items: readonly T[], size = 4): T[][] {
	const step = Math.max(1, Math.floor(size));
	const result: T[][] = [];
	for (let i = 0; i < items.length; i += step) result.push(items.slice(i, i + step));
	return result;
}

export function formatTime(seconds: number): string {
	const safe = Number.isFinite(seconds) && seconds > 0 ? seconds : 0;
	const m = Math.floor(safe / 60);
	const s = Math.floor(safe % 60);
	return `${m}:${s.toString().padStart(2, '0')}`;
}

// Which line is playing at `seconds`. -1 when between lines.
export function activeIndex(items: readonly Timed[], seconds: number): number {
	return items.findIndex((item) => seconds >= item.start && seconds < item.end);
}

// The line to show while audio plays: the one being spoken, otherwise the
// last one that already started (so the caption doesn't blank out in pauses).
export function currentIndex(items: readonly Timed[], seconds: number): number {
	let found = -1;
	for (let i = 0; i < items.length; i += 1) {
		if (items[i].start <= seconds) found = i;
		else break;
	}
	return found;
}

export function readingMinutes(sentences: readonly Sentence[], wordsPerMinute = 180): number {
	const words = sentences.reduce((sum, s) => sum + s.en.split(/\s+/).filter(Boolean).length, 0);
	return Math.max(1, Math.round(words / wordsPerMinute));
}

// Words that teach nothing when listed in a wordbook.
const COMMON_WORDS = new Set(
	(
		'about above after again against also always another around because been before being below between both ' +
		'cannot could does doing down during each every from further have having here hers herself himself into ' +
		'itself just like made make many more most much must myself never only other ours ourselves over really ' +
		'same should some such than that their theirs them themselves then there these they thing things this those ' +
		'through under until very want wants were what when where which while will with would your yours yourself ' +
		'going gonna gotta wanna yeah okay know think them look looks good well right first second third fourth ' +
		'fifth sixth last next back come comes came take takes even still people time year years away dont didnt ' +
		'doesnt cant wont isnt arent youre theyre thats heres theres lets'
	).split(' ')
);

// Candidate words for the wordbook when the video has little analyzed vocabulary:
// content words from the transcript, longest-lived first appearance order kept.
export function keyWords(
	segments: readonly TranscriptSegment[],
	known: readonly VocabularyItem[] = [],
	limit = 40
): string[] {
	const taken = new Set(known.map((v) => v.word.trim().toLowerCase()));
	const result: string[] = [];
	for (const segment of segments) {
		for (const match of (segment.text ?? '').matchAll(/[A-Za-z][A-Za-z'’-]*/g)) {
			const word = match[0].toLowerCase().replace(/’/g, "'");
			const bare = word.replace(/'/g, '');
			if (bare.length < 5) continue;
			if (word.includes("'")) continue;
			if (COMMON_WORDS.has(bare) || taken.has(word)) continue;
			taken.add(word);
			result.push(word);
			if (result.length >= limit) return result;
		}
	}
	return result;
}

// The sentence a word first appears in — shown as the example in the wordbook.
export function exampleFor(sentences: readonly Sentence[], word: string): string {
	const escaped = word.trim().replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
	if (!escaped) return '';
	const pattern = new RegExp(`\\b${escaped}`, 'i');
	return sentences.find((s) => pattern.test(s.en))?.en ?? '';
}
