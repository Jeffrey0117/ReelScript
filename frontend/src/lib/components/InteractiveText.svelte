<script lang="ts">
	import type { VocabularyItem } from '$lib/api';
	import { tokenizeSentence } from '$lib/words';
	import { wordState, markWord, unmarkWord, lookupWordCached } from '$lib/wordbook.svelte';
	import WordCard from './WordCard.svelte';

	let {
		text,
		vocabulary = [],
		videoId = undefined,
	}: {
		text: string;
		vocabulary?: VocabularyItem[];
		videoId?: string;
	} = $props();

	let activeCard = $state<{
		v: VocabularyItem;
		isPhrase: boolean;
		anchor: { top: number; bottom: number; left: number; width: number };
		phonetic?: string | null;
		loading?: boolean;
	} | null>(null);

	function anchorOf(e: MouseEvent) {
		const r = (e.currentTarget as HTMLElement).getBoundingClientRect();
		return { top: r.top, bottom: r.bottom, left: r.left, width: r.width };
	}

	function openVocab(e: MouseEvent, v: VocabularyItem) {
		e.preventDefault();
		e.stopPropagation();
		activeCard = { v, isPhrase: v.word.trim().includes(' '), anchor: anchorOf(e) };
	}

	async function openDict(e: MouseEvent, raw: string) {
		e.preventDefault();
		e.stopPropagation();
		const anchor = anchorOf(e);
		activeCard = { v: { word: raw, translation: '' }, isPhrase: false, anchor, loading: true };
		const entry = await lookupWordCached(raw);
		// The user may have closed or switched cards while we fetched.
		if (activeCard?.loading && activeCard.v.word === raw) {
			activeCard = {
				v: { word: entry?.found ? entry.word : raw, translation: entry?.translation ?? '' },
				isPhrase: false,
				anchor,
				phonetic: entry?.phonetic || null,
			};
		}
	}
</script>

{#each tokenizeSentence(text, vocabulary) as tk, ti (ti)}
	{#if tk.v}
		{@const st = wordState(tk.v.word)}
		<button
			class="wtk"
			class:phrase={tk.v.word.trim().includes(' ')}
			class:learning={st === 'learning'}
			class:mastered={st === 'mastered'}
			onclick={(e) => openVocab(e, tk.v)}
		>{tk.text}</button>
	{:else if tk.dict}
		{@const dst = wordState(tk.text)}
		<button
			class="dtk"
			class:learning={dst === 'learning'}
			class:mastered={dst === 'mastered'}
			onclick={(e) => openDict(e, tk.text)}
		>{tk.text}</button>
	{:else}{tk.text}{/if}
{/each}

{#if activeCard}
	<WordCard
		word={activeCard.v.word}
		meaning={activeCard.v.translation || null}
		phonetic={activeCard.phonetic ?? null}
		loading={activeCard.loading ?? false}
		isPhrase={activeCard.isPhrase}
		state={wordState(activeCard.v.word)}
		anchor={activeCard.anchor}
		onLearning={() => activeCard && markWord(activeCard.v, false, videoId)}
		onMastered={() => activeCard && markWord(activeCard.v, true, videoId)}
		onUnmark={() => activeCard && unmarkWord(activeCard.v.word)}
		onClose={() => (activeCard = null)}
	/>
{/if}

<style>
	/* Analyzed vocabulary tokens — word = blue family, phrase = green family */
	.wtk {
		display: inline;
		font: inherit;
		padding: 0 4px;
		margin: 0 1px;
		border: 1.5px solid rgba(59, 130, 246, 0.55);
		border-radius: 6px;
		background: rgba(59, 130, 246, 0.06);
		color: inherit;
		cursor: pointer;
		transition: background 0.15s, border-color 0.15s;
	}

	.wtk:hover {
		background: rgba(59, 130, 246, 0.16);
	}

	.wtk.phrase {
		border-color: rgba(16, 185, 129, 0.55);
		background: rgba(16, 185, 129, 0.06);
	}

	.wtk.phrase:hover {
		background: rgba(16, 185, 129, 0.16);
	}

	.wtk.learning {
		background: rgba(59, 130, 246, 0.22);
		border-color: #3b82f6;
	}

	.wtk.mastered {
		background: rgba(16, 185, 129, 0.22);
		border-color: #10b981;
	}

	/* Dictionary tokens: every other word, quiet until touched */
	.dtk {
		display: inline;
		font: inherit;
		padding: 0;
		margin: 0;
		border: none;
		background: none;
		color: inherit;
		cursor: pointer;
		border-radius: 3px;
		text-decoration-line: underline;
		text-decoration-style: dashed;
		text-decoration-color: transparent;
		text-underline-offset: 3px;
		transition: text-decoration-color 0.15s, background 0.15s;
	}

	.dtk:hover {
		text-decoration-color: color-mix(in srgb, var(--accent) 55%, transparent);
		background: color-mix(in srgb, var(--accent) 8%, transparent);
	}

	.dtk.learning {
		background: rgba(59, 130, 246, 0.18);
		text-decoration-color: #3b82f6;
	}

	.dtk.mastered {
		background: rgba(16, 185, 129, 0.18);
		text-decoration-color: #10b981;
	}
</style>
