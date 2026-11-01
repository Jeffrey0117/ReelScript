import type { VocabularyItem } from '$lib/api';

// Sentence tokenization shared by every interactive-transcript surface.
// Analyzed vocabulary wins (longest entries first so phrases swallow the
// words inside them); every remaining English word becomes a dictionary
// token.

export interface SentenceToken {
	text: string;
	v?: VocabularyItem;
	dict?: boolean;
}

export function splitDictWords(text: string): SentenceToken[] {
	const tokens: SentenceToken[] = [];
	let last = 0;
	for (const m of text.matchAll(/[A-Za-z][A-Za-z'’-]*/g)) {
		const idx = m.index ?? 0;
		if (idx > last) tokens.push({ text: text.slice(last, idx) });
		tokens.push({ text: m[0], dict: true });
		last = idx + m[0].length;
	}
	if (last < text.length) tokens.push({ text: text.slice(last) });
	return tokens;
}

export function tokenizeSentence(text: string, vocabulary: VocabularyItem[]): SentenceToken[] {
	const sorted = [...vocabulary].sort((a, b) => b.word.length - a.word.length);
	const escaped = sorted
		.map((v) => v.word.trim())
		.filter(Boolean)
		.map((w) => w.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'));
	if (!escaped.length) return splitDictWords(text);
	const regex = new RegExp(`\\b(${escaped.join('|')})\\b`, 'gi');
	const byLower = new Map(sorted.map((v) => [v.word.trim().toLowerCase(), v]));

	const tokens: SentenceToken[] = [];
	let last = 0;
	for (const m of text.matchAll(regex)) {
		const idx = m.index ?? 0;
		if (idx > last) tokens.push(...splitDictWords(text.slice(last, idx)));
		tokens.push({ text: m[0], v: byLower.get(m[0].toLowerCase()) });
		last = idx + m[0].length;
	}
	if (last < text.length) tokens.push(...splitDictWords(text.slice(last)));
	return tokens;
}
