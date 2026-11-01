// Shared wordbook state — one saved-word map for every interactive-text
// surface (study transcript, study full text, watch transcript). Svelte 5
// runes module: reading `wordState()` inside a template is reactive.

import {
	saveWord,
	deleteWord,
	listWordbook,
	lookupWord,
	type SavedWord,
	type VocabularyItem,
	type DictEntry,
} from '$lib/api';
import { getUser, login } from '$lib/auth';

const MASTERED_BOX = 5;

const store = $state<{ map: Map<string, SavedWord> }>({ map: new Map() });

let loaded = false;

export async function loadSavedWords(force = false): Promise<void> {
	if (loaded && !force) return;
	loaded = true;
	const data = await listWordbook().catch(() => null);
	if (data) store.map = new Map(data.words.map((w) => [w.word.toLowerCase(), w]));
}

export function resetWordbook(): void {
	loaded = false;
	store.map = new Map();
}

export function wordState(word: string): 'none' | 'learning' | 'mastered' {
	const saved = store.map.get(word.toLowerCase());
	if (!saved) return 'none';
	return saved.box >= MASTERED_BOX ? 'mastered' : 'learning';
}

export async function markWord(v: VocabularyItem, mastered: boolean, videoId?: string): Promise<void> {
	if (!getUser()) {
		login();
		return;
	}
	try {
		const result = await saveWord({
			word: v.word,
			meaning: v.translation,
			video_id: videoId,
			mastered,
		});
		store.map = new Map(store.map).set(v.word.toLowerCase(), result.saved);
	} catch {
		// server is truth — UI simply stays unmarked
	}
}

export async function unmarkWord(word: string): Promise<void> {
	const saved = store.map.get(word.toLowerCase());
	if (!saved) return;
	const next = new Map(store.map);
	next.delete(word.toLowerCase());
	store.map = next;
	deleteWord(saved.id).catch(() => loadSavedWords(true));
}

// Dictionary lookups, cached per session
const dictCache = new Map<string, DictEntry | null>();

export async function lookupWordCached(raw: string): Promise<DictEntry | null> {
	const key = raw.toLowerCase();
	if (dictCache.has(key)) return dictCache.get(key) ?? null;
	const entry = await lookupWord(raw).catch(() => null);
	dictCache.set(key, entry);
	return entry;
}
