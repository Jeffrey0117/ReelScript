<script lang="ts">
	// Wordbook mode: an open notebook. English on the left of each row, Chinese
	// smudged out until you tap it.
	import { onMount, onDestroy } from 'svelte';
	import type { VideoDetail, TranscriptSegment, VocabularyItem } from '$lib/api';
	import { t } from '$lib/i18n';
	import { keyWords, exampleFor, type Sentence } from '$lib/lesson';
	import { wordState, markWord, lookupWordCached } from '$lib/wordbook.svelte';
	import { mt } from '$lib/modes/text';
	import { applyLimit, type Gate } from '$lib/modes/access';
	import ModeWall from './ModeWall.svelte';

	interface Entry {
		word: string;
		meaning: string;
		phonetic: string;
		example: string;
	}

	let {
		video,
		segments,
		sentences,
		vocabulary,
		gate,
	}: {
		video: VideoDetail;
		segments: TranscriptSegment[];
		sentences: Sentence[];
		vocabulary: VocabularyItem[];
		gate: Gate;
	} = $props();

	const ROWS_PER_PAGE = 10;
	const PER_SPREAD = ROWS_PER_PAGE * 2;
	const LOOKUP_LIMIT = 40;
	const LOOKUP_BATCH = 6;

	let looked = $state<Entry[]>([]);
	let looking = $state(true);
	let open = $state<Set<string>>(new Set());
	let order = $state<string[] | null>(null);
	let spread = $state(0);

	// Words the video's analysis already explained come first, then dictionary finds.
	let analyzed = $derived<Entry[]>(
		vocabulary.map((v) => ({
			word: v.word,
			meaning: v.translation,
			phonetic: '',
			example: exampleFor(sentences, v.word),
		}))
	);
	let found = $derived.by<Entry[]>(() => {
		const all = [...analyzed, ...looked];
		if (!order) return all;
		const byWord = new Map(all.map((e) => [e.word, e]));
		const shuffled = order.map((w) => byWord.get(w)).filter((e): e is Entry => Boolean(e));
		const rest = all.filter((e) => !order?.includes(e.word));
		return [...shuffled, ...rest];
	});
	// Visitors and free members get the first words; the count of the rest goes on the wall.
	let limited = $derived(applyLimit(found, gate.words));
	let entries = $derived(limited.shown);
	let spreads = $derived(Math.max(1, Math.ceil(entries.length / PER_SPREAD)));
	let visible = $derived(entries.slice(spread * PER_SPREAD, (spread + 1) * PER_SPREAD));
	let leftPage = $derived(visible.slice(0, ROWS_PER_PAGE));
	let rightPage = $derived(visible.slice(ROWS_PER_PAGE));
	let allOpen = $derived(entries.length > 0 && entries.every((e) => open.has(e.word)));

	// The offline dictionary fills in everything the analysis did not cover.
	// A few lookups at a time; words the dictionary does not know are dropped.
	let destroyed = false;
	onDestroy(() => {
		destroyed = true;
	});

	onMount(async () => {
		const candidates = keyWords(segments, vocabulary, LOOKUP_LIMIT);
		for (let i = 0; i < candidates.length; i += LOOKUP_BATCH) {
			const batch = candidates.slice(i, i + LOOKUP_BATCH);
			const found = await Promise.all(batch.map((word) => lookupWordCached(word)));
			if (destroyed) return; // left the mode: stop looking things up
			const fresh = found.flatMap((entry, at) =>
				entry?.found && entry.translation
					? [
							{
								word: entry.word || batch[at],
								meaning: entry.translation,
								phonetic: entry.phonetic ?? '',
								example: exampleFor(sentences, batch[at]),
							},
						]
					: []
			);
			// The dictionary answers with the base form ("smaller" → "small"), so two
			// lookups can come back as the same word — keep the first only.
			const known = new Set([...analyzed, ...looked].map((e) => e.word.toLowerCase()));
			const unique = fresh.filter((e) => {
				const key = e.word.toLowerCase();
				if (known.has(key)) return false;
				known.add(key);
				return true;
			});
			looked = [...looked, ...unique];
		}
		looking = false;
	});

	function toggle(word: string) {
		const next = new Set(open);
		if (next.has(word)) next.delete(word);
		else next.add(word);
		open = next;
	}

	function toggleAll() {
		open = allOpen ? new Set() : new Set(entries.map((e) => e.word));
	}

	function shuffle() {
		const words = entries.map((e) => e.word);
		for (let i = words.length - 1; i > 0; i -= 1) {
			const j = Math.floor(Math.random() * (i + 1));
			[words[i], words[j]] = [words[j], words[i]];
		}
		order = words;
		open = new Set();
		spread = 0;
	}

	function turn(step: number) {
		spread = Math.max(0, Math.min(spread + step, spreads - 1));
	}

	function save(entry: Entry) {
		if (wordState(entry.word) !== 'none') return;
		void markWord({ word: entry.word, translation: entry.meaning }, false, video.id);
	}
</script>

{#snippet sheet(rows: Entry[], offset: number, side: 'left' | 'right')}
	<div class="page {side}">
		<div class="page-head">
			<span>{mt('vocabEnglish')}</span>
			<span>{mt('vocabChinese')}</span>
		</div>
		<ol class="rows">
			{#each rows as entry, i (entry.word)}
				{@const shown = open.has(entry.word)}
				{@const saved = wordState(entry.word) !== 'none'}
				<li class="row">
					<span class="no">{offset + i + 1}</span>
					<span class="word" title={entry.example}>
						{entry.word}
						{#if entry.phonetic}<small>/{entry.phonetic}/</small>{/if}
					</span>
					<button class="meaning" class:shown onclick={() => toggle(entry.word)} aria-pressed={shown}>
						<span>{entry.meaning}</span>
					</button>
					<button
						class="star"
						class:saved
						onclick={() => save(entry)}
						title={saved ? mt('vocabSaved') : mt('vocabSave')}
						aria-label={saved ? mt('vocabSaved') : mt('vocabSave')}
					>
						<svg width="15" height="15" viewBox="0 0 24 24" fill={saved ? 'currentColor' : 'none'} stroke="currentColor" stroke-width="1.8" stroke-linejoin="round"><path d="M12 3.5l2.6 5.4 5.9.8-4.3 4.1 1 5.8L12 16.9 6.8 19.6l1-5.8-4.3-4.1 5.9-.8z"/></svg>
					</button>
				</li>
			{/each}
			{#each Array(Math.max(0, ROWS_PER_PAGE - rows.length)) as _, i (i)}
				<li class="row blank" aria-hidden="true"></li>
			{/each}
		</ol>
		<span class="folio">{mt('vocabPage')} {spread * 2 + (side === 'left' ? 1 : 2)}</span>
	</div>
{/snippet}

<section class="desk">
	<div class="book">
		<header class="label">
			<div>
				<p class="label-title">{mt('vocabTitle')}</p>
				<p class="label-sub">{video.title || t('untitled')}</p>
			</div>
			<p class="label-count">
				<b>{entries.length}</b> {mt('vocabWords')}
				{#if looking}<em>{mt('vocabLooking')}</em>{/if}
			</p>
		</header>

		<div class="tools">
			<button onclick={toggleAll} disabled={entries.length === 0}>{allOpen ? mt('vocabHideAll') : mt('vocabRevealAll')}</button>
			<button onclick={shuffle} disabled={entries.length < 2}>{mt('vocabShuffle')}</button>
			<span class="tip">{mt('vocabTapHint')}</span>
		</div>

		{#if entries.length === 0 && !looking}
			<p class="empty">{mt('vocabEmpty')}</p>
		{:else}
			<div class="spread">
				{@render sheet(leftPage, spread * PER_SPREAD, 'left')}
				<div class="spine" aria-hidden="true">
					{#each Array(7) as _, i (i)}<i></i>{/each}
				</div>
				{@render sheet(rightPage, spread * PER_SPREAD + ROWS_PER_PAGE, 'right')}
			</div>

			{#if !looking && limited.hidden > 0}
				<ModeWall tier={gate.tier} kind="words" count={limited.hidden} />
			{:else if !looking && gate.hiddenLines > 0}
				<!-- The word list is short only because most of the video is held back. -->
				<ModeWall tier={gate.tier} kind="lines" count={gate.hiddenLines} />
			{/if}

			{#if spreads > 1}
				<div class="turn">
					<button onclick={() => turn(-1)} disabled={spread === 0}>← {mt('vocabPrev')}</button>
					<span>{spread + 1} / {spreads}</span>
					<button onclick={() => turn(1)} disabled={spread >= spreads - 1}>{mt('vocabNext')} →</button>
				</div>
			{/if}
		{/if}
	</div>
</section>

<style>
	.desk {
		--paper: var(--bg-card);
		--rule: color-mix(in srgb, var(--accent) 22%, var(--border));
		--margin-line: color-mix(in srgb, #ef4444 45%, transparent);
		--row-h: 46px;
	}

	.book {
		position: relative;
		padding: 22px 26px 26px;
		border-radius: 6px 18px 18px 6px;
		background: var(--paper);
		border: 1px solid var(--border);
		box-shadow:
			0 1px 0 var(--border),
			6px 6px 0 -1px var(--paper),
			6px 6px 0 0 var(--border),
			12px 12px 0 -1px var(--paper),
			12px 12px 0 0 var(--border),
			0 30px 60px rgba(72, 60, 38, 0.14);
	}

	.label {
		display: flex;
		align-items: flex-end;
		justify-content: space-between;
		gap: 16px;
		padding-bottom: 12px;
		border-bottom: 2px solid var(--text);
	}

	.label-title {
		font-family: var(--font-hand);
		font-size: 38px;
		font-weight: 700;
		line-height: 1;
		color: var(--accent);
	}

	.label-sub {
		margin-top: 4px;
		font-size: 13.5px;
		color: var(--text-dim);
	}

	.label-count {
		flex-shrink: 0;
		font-size: 13px;
		color: var(--text-dim);
		text-align: right;
	}

	.label-count b {
		font-family: var(--font-hand);
		font-size: 30px;
		color: var(--text);
		line-height: 1;
	}

	.label-count em {
		display: block;
		font-style: normal;
		font-size: 12px;
		color: var(--accent);
	}

	.tools {
		display: flex;
		align-items: center;
		gap: 8px;
		padding: 12px 0;
	}

	.tools button,
	.turn button {
		padding: 5px 12px;
		font-size: 13px;
		font-weight: 600;
		color: var(--text);
		border: 1.5px solid var(--text);
		border-radius: 999px 14px 999px 14px;
		transition: background 0.15s, color 0.15s;
	}

	.tools button:hover:not(:disabled),
	.turn button:hover:not(:disabled) {
		background: var(--text);
		color: var(--paper);
	}

	.tools button:disabled,
	.turn button:disabled {
		opacity: 0.3;
		cursor: not-allowed;
	}

	.tip {
		margin-left: auto;
		font-family: var(--font-hand);
		font-size: 18px;
		color: var(--text-dim);
		transform: rotate(-1.5deg);
	}

	/* Two ruled pages and a ring-bound spine */
	.spread {
		display: grid;
		grid-template-columns: 1fr 34px 1fr;
	}

	.page {
		position: relative;
		min-width: 0;
		padding-bottom: 26px;
		background-image: linear-gradient(to right, transparent 43px, var(--margin-line) 43px, var(--margin-line) 44px, transparent 44px);
	}

	.page-head {
		display: grid;
		grid-template-columns: 44px 1fr 1fr 30px;
		height: 30px;
		align-items: center;
		font-size: 10.5px;
		font-weight: 700;
		letter-spacing: 0.18em;
		text-transform: uppercase;
		color: var(--text-dim);
		border-bottom: 1px solid var(--rule);
	}

	.page-head span:first-child {
		grid-column: 2;
		padding-left: 10px;
	}

	.rows {
		list-style: none;
	}

	.row {
		display: grid;
		grid-template-columns: 44px 1fr 1fr 30px;
		align-items: center;
		height: var(--row-h);
		border-bottom: 1px solid var(--rule);
	}

	.no {
		font-family: var(--font-hand);
		font-size: 17px;
		color: var(--text-dim);
		text-align: center;
	}

	.word {
		padding-left: 10px;
		font-family: var(--font-serif);
		font-size: 18px;
		font-weight: 600;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	.word small {
		margin-left: 6px;
		font-family: 'Inter', sans-serif;
		font-size: 11px;
		font-weight: 400;
		color: var(--text-dim);
	}

	.meaning {
		height: 100%;
		padding: 0 8px;
		text-align: left;
		font-size: 15px;
		overflow: hidden;
	}

	.meaning span {
		display: -webkit-box;
		-webkit-line-clamp: 2;
		line-clamp: 2;
		-webkit-box-orient: vertical;
		overflow: hidden;
		line-height: 1.35;
		padding: 2px 6px;
		margin: 0 -6px;
		border-radius: 4px;
		filter: blur(7px);
		background: color-mix(in srgb, var(--accent) 16%, transparent);
		user-select: none;
		transition: filter 0.22s ease, background 0.22s ease;
	}

	.meaning:hover span {
		filter: blur(5.5px);
	}

	.meaning.shown span {
		filter: none;
		background: transparent;
		user-select: auto;
	}

	.star {
		display: grid;
		place-items: center;
		width: 28px;
		height: 28px;
		border-radius: 50%;
		color: var(--border);
		transition: color 0.15s;
	}

	.row:hover .star,
	.star:focus-visible {
		color: var(--text-dim);
	}

	.star.saved {
		color: #f59e0b;
	}

	.folio {
		position: absolute;
		bottom: 0;
		font-family: var(--font-hand);
		font-size: 16px;
		color: var(--text-dim);
	}

	.page.left .folio {
		left: 54px;
	}

	.page.right .folio {
		right: 8px;
	}

	.spine {
		display: flex;
		flex-direction: column;
		justify-content: space-around;
		align-items: center;
		padding: 34px 0 30px;
		background: linear-gradient(
			to right,
			transparent 0,
			color-mix(in srgb, var(--text) 9%, transparent) 50%,
			transparent 100%
		);
	}

	.spine i {
		width: 26px;
		height: 9px;
		border-radius: 999px;
		background: linear-gradient(#d4d4d8, #71717a);
		box-shadow: 0 1px 2px rgba(0, 0, 0, 0.3);
	}

	.turn {
		display: flex;
		align-items: center;
		justify-content: center;
		gap: 18px;
		margin-top: 18px;
		font-family: var(--font-hand);
		font-size: 19px;
		color: var(--text-dim);
	}

	.empty {
		padding: 60px 0;
		text-align: center;
		color: var(--text-dim);
	}

	@media (max-width: 760px) {
		.desk {
			--row-h: 44px;
		}

		.book {
			padding: 16px 14px 20px;
			border-radius: 6px 14px 14px 6px;
			box-shadow:
				4px 4px 0 -1px var(--paper),
				4px 4px 0 0 var(--border),
				0 20px 40px rgba(72, 60, 38, 0.12);
		}

		.label-title {
			font-size: 30px;
		}

		.tip {
			display: none;
		}

		/* One page above the other; the spine turns into a fold line. */
		.spread {
			grid-template-columns: 1fr;
		}

		.spine {
			flex-direction: row;
			height: 26px;
			padding: 0 24px;
			background: none;
		}

		.spine i {
			width: 9px;
			height: 18px;
		}

		.page {
			background-image: linear-gradient(to right, transparent 33px, var(--margin-line) 33px, var(--margin-line) 34px, transparent 34px);
		}

		.page-head,
		.row {
			grid-template-columns: 34px 1fr 1fr 28px;
		}

		.row.blank {
			display: none;
		}

		.word {
			font-size: 16px;
		}

		.word small {
			display: none;
		}

		.meaning {
			font-size: 14px;
		}

		.page.left .folio {
			left: 44px;
		}
	}
</style>
