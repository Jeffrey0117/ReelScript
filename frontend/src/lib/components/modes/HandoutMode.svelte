<script lang="ts">
	// Handout mode: the lesson as a worksheet you could print and hand out —
	// main idea, key points, quotes, word table, bilingual sentences, cloze.
	import type { VideoDetail, VocabularyItem } from '$lib/api';
	import { t } from '$lib/i18n';
	import type { Sentence } from '$lib/lesson';
	import { pickBlanks, autoBlankCount, wordSpans } from '$lib/typing-core';
	import { mt, type ModeTextKey } from '$lib/modes/text';
	import type { Gate } from '$lib/modes/access';
	import ModeWall from './ModeWall.svelte';

	interface ClozePart {
		text: string;
		blank: number | null; // answer number, null for plain text
	}

	let {
		video,
		sentences,
		vocabulary,
		appreciating,
		gate,
		onAppreciate,
	}: {
		video: VideoDetail;
		sentences: Sentence[];
		vocabulary: VocabularyItem[];
		appreciating: boolean;
		gate: Gate;
		onAppreciate: () => Promise<void>;
	} = $props();

	const CLOZE_LIMIT = 8;
	const CLOZE_MIN_WORDS = 5;

	let showAnswers = $state(false);
	let appreciation = $derived(video.transcript?.appreciation ?? null);
	let hasZh = $derived(sentences.some((s) => s.zh));

	// Cloze: the same deterministic blanks the typing mode uses, numbered across the sheet.
	let cloze = $derived.by(() => {
		const picked = sentences.filter((s) => wordSpans(s.en).length >= CLOZE_MIN_WORDS).slice(0, CLOZE_LIMIT);
		const answers: string[] = [];
		const items = picked.map((sentence) => {
			const blanks = pickBlanks(sentence.en, autoBlankCount(sentence.en));
			const parts: ClozePart[] = [];
			let at = 0;
			for (const blank of blanks) {
				if (blank.from > at) parts.push({ text: sentence.en.slice(at, blank.from), blank: null });
				answers.push(blank.word);
				parts.push({ text: blank.word, blank: answers.length });
				at = blank.to;
			}
			if (at < sentence.en.length) parts.push({ text: sentence.en.slice(at), blank: null });
			return { parts, zh: sentence.zh };
		});
		return { items, answers };
	});

	// Sections are numbered by what this video actually has.
	let sections = $derived.by(() => {
		const present: { id: string; title: ModeTextKey }[] = [];
		if (appreciation?.theme) present.push({ id: 'theme', title: 'handoutTheme' });
		if (appreciation?.keyPoints?.length) present.push({ id: 'points', title: 'handoutKeyPoints' });
		if (appreciation?.goldenQuotes?.length) present.push({ id: 'quotes', title: 'handoutQuotes' });
		if (vocabulary.length) present.push({ id: 'vocab', title: 'handoutVocab' });
		if (sentences.length) present.push({ id: 'sentences', title: 'handoutSentences' });
		if (cloze.items.length) present.push({ id: 'cloze', title: 'handoutCloze' });
		return present;
	});

	const numberOf = (id: string) => sections.findIndex((s) => s.id === id) + 1;
</script>

{#snippet heading(id: string, title: ModeTextKey)}
	<h2><span class="num">{numberOf(id)}</span>{mt(title)}</h2>
{/snippet}

<div class="sheet-wrap">
	<div class="sheet-tools">
		{#if !appreciation?.theme && sentences.length > 0 && gate.hiddenLines === 0}
			<button class="tool" onclick={onAppreciate} disabled={appreciating}>
				{appreciating ? mt('handoutMaking') : mt('handoutMakeSummary')}
			</button>
		{/if}
		<button class="tool solid" onclick={() => (gate.print ? window.print() : gate.open('print'))}>
			<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M6 9V3h12v6M6 17H4v-7h16v7h-2M7 14h10v7H7z"/></svg>
			{mt('handoutPrint')}
		</button>
	</div>

	<article class="sheet">
		<header class="head">
			<div class="head-top">
				<span class="stamp">{mt('handoutLabel')}</span>
				<span class="fill">{mt('handoutName')}<i></i></span>
				<span class="fill">{mt('handoutDate')}<i></i></span>
			</div>
			<h1>{video.title || t('untitled')}</h1>
			{#if video.channel}<p class="source">{video.channel}</p>{/if}
		</header>

		{#if sentences.length === 0}
			<p class="empty">{mt('noTranscript')}</p>
		{/if}

		{#if appreciation?.theme}
			<section>
				{@render heading('theme', 'handoutTheme')}
				<p class="theme">{appreciation.theme}</p>
			</section>
		{/if}

		{#if appreciation?.keyPoints?.length}
			<section>
				{@render heading('points', 'handoutKeyPoints')}
				<ul class="points">
					{#each appreciation.keyPoints as point, i (i)}
						<li>{point}</li>
					{/each}
				</ul>
			</section>
		{/if}

		{#if appreciation?.goldenQuotes?.length}
			<section>
				{@render heading('quotes', 'handoutQuotes')}
				<div class="quotes">
					{#each appreciation.goldenQuotes as quote, i (i)}
						<blockquote>
							<p class="q-en">{quote.en}</p>
							<p class="q-zh">{quote.zh}</p>
						</blockquote>
					{/each}
				</div>
			</section>
		{/if}

		{#if vocabulary.length}
			<section>
				{@render heading('vocab', 'handoutVocab')}
				<table class="words">
					<thead>
						<tr>
							<th class="w-no">#</th>
							<th>{mt('handoutWord')}</th>
							<th>{mt('handoutMeaning')}</th>
							<th class="w-check">{mt('handoutCheck')}</th>
						</tr>
					</thead>
					<tbody>
						{#each vocabulary as item, i (item.word)}
							<tr>
								<td class="w-no">{i + 1}</td>
								<td class="w-en">{item.word}</td>
								<td>{item.translation}</td>
								<td class="w-check"><i></i></td>
							</tr>
						{/each}
					</tbody>
				</table>
			</section>
		{/if}

		{#if sentences.length}
			<section>
				{@render heading('sentences', 'handoutSentences')}
				<ol class="sentences">
					{#each sentences as sentence, i (i)}
						<li>
							<p class="s-en">{sentence.en}</p>
							{#if sentence.zh}<p class="s-zh">{sentence.zh}</p>{/if}
						</li>
					{/each}
				</ol>
			</section>
		{/if}

		{#if cloze.items.length}
			<section class="cloze-section">
				{@render heading('cloze', 'handoutCloze')}
				<p class="lead">{mt('handoutClozeHint')}</p>
				<ol class="cloze">
					{#each cloze.items as item, i (i)}
						<li>
							<p class="c-en">
								{#each item.parts as part, j (j)}{#if part.blank === null}{part.text}{:else}<span class="gap" class:filled={showAnswers} style="--ch: {part.text.length}"><sup>{part.blank}</sup>{#if showAnswers}{part.text}{/if}</span>{/if}{/each}
							</p>
							{#if hasZh && item.zh}<p class="s-zh">{item.zh}</p>{/if}
						</li>
					{/each}
				</ol>

				<div class="answers">
					<button class="tool no-print" onclick={() => (showAnswers = !showAnswers)}>
						{showAnswers ? mt('handoutHideAnswers') : mt('handoutShowAnswers')}
					</button>
					<p class="key" class:open={showAnswers}>
						<b>{mt('handoutAnswers')}</b>
						{#each cloze.answers as answer, i (i)}
							<span><sup>{i + 1}</sup>{answer}</span>
						{/each}
					</p>
				</div>
			</section>
		{/if}

		{#if gate.hiddenLines > 0}
			<ModeWall tier={gate.tier} kind="lines" count={gate.hiddenLines} />
		{/if}

		<footer class="foot">
			<span>ReelScript</span>
			<span>{video.url}</span>
		</footer>
	</article>
</div>

<style>
	.sheet-wrap {
		--ink: #1c1917;
		--ink-dim: #6b645a;
		--hair: #d6d0c4;
		max-width: 820px;
		margin: 0 auto;
	}

	.sheet-tools {
		display: flex;
		justify-content: flex-end;
		gap: 8px;
		margin-bottom: 14px;
	}

	.tool {
		display: inline-flex;
		align-items: center;
		gap: 7px;
		padding: 7px 14px;
		font-size: 13px;
		font-weight: 600;
		color: var(--text);
		border: 1.5px solid var(--text);
		border-radius: 4px;
		background: transparent;
		transition: transform 0.1s, box-shadow 0.1s;
	}

	.tool:hover:not(:disabled) {
		transform: translate(-1px, -1px);
		box-shadow: 3px 3px 0 var(--accent);
	}

	.tool:disabled {
		opacity: 0.5;
		cursor: not-allowed;
	}

	.tool.solid {
		background: var(--text);
		color: var(--bg);
	}

	/* The sheet is paper: white with dark ink in both themes, like a real printout. */
	.sheet {
		padding: 56px 64px 40px;
		color: var(--ink);
		background: #fff;
		border: 1px solid var(--hair);
		box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05), 0 24px 60px rgba(72, 60, 38, 0.16);
		font-size: 15px;
		line-height: 1.7;
	}

	.head {
		padding-bottom: 20px;
		border-bottom: 3px solid var(--ink);
		margin-bottom: 8px;
	}

	.head-top {
		display: flex;
		align-items: flex-end;
		gap: 22px;
		margin-bottom: 22px;
		font-size: 12.5px;
		color: var(--ink-dim);
	}

	.stamp {
		margin-right: auto;
		padding: 3px 10px;
		font-size: 11px;
		font-weight: 800;
		letter-spacing: 0.2em;
		color: #fff;
		background: var(--accent);
	}

	.fill {
		display: inline-flex;
		align-items: flex-end;
		gap: 6px;
	}

	.fill i {
		display: inline-block;
		width: 110px;
		border-bottom: 1px solid var(--ink);
	}

	h1 {
		font-size: 30px;
		font-weight: 800;
		line-height: 1.25;
		letter-spacing: -0.02em;
		text-wrap: balance;
	}

	.source {
		margin-top: 6px;
		font-size: 13px;
		color: var(--ink-dim);
	}

	section {
		padding-top: 26px;
	}

	h2 {
		display: flex;
		align-items: center;
		gap: 10px;
		font-size: 16px;
		font-weight: 800;
		letter-spacing: 0.04em;
		margin-bottom: 12px;
		padding-bottom: 6px;
		border-bottom: 1px solid var(--ink);
	}

	.num {
		display: grid;
		place-items: center;
		width: 24px;
		height: 24px;
		font-size: 13px;
		color: #fff;
		background: var(--ink);
		border-radius: 50%;
	}

	.theme {
		font-size: 17px;
		font-weight: 600;
		padding: 12px 16px;
		background: color-mix(in srgb, var(--accent) 8%, #fff);
		border-left: 4px solid var(--accent);
	}

	.points {
		list-style: none;
		display: grid;
		gap: 6px;
	}

	.points li {
		position: relative;
		padding-left: 26px;
	}

	.points li::before {
		content: '';
		position: absolute;
		left: 2px;
		top: 0.4em;
		width: 13px;
		height: 13px;
		border: 1.5px solid var(--ink);
		border-radius: 2px;
	}

	.quotes {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
		gap: 12px;
	}

	.quotes blockquote {
		padding: 12px 14px;
		border: 1px dashed var(--ink-dim);
		border-radius: 2px;
		break-inside: avoid;
	}

	.q-en {
		font-weight: 700;
		line-height: 1.45;
	}

	.q-zh,
	.s-zh {
		font-size: 13.5px;
		color: var(--ink-dim);
	}

	.q-zh {
		margin-top: 4px;
	}

	.words {
		width: 100%;
		border-collapse: collapse;
		font-size: 14.5px;
	}

	.words th,
	.words td {
		padding: 7px 10px;
		text-align: left;
		border: 1px solid var(--hair);
	}

	.words th {
		font-size: 11.5px;
		letter-spacing: 0.08em;
		color: var(--ink-dim);
		background: #f6f3ec;
	}

	.w-no {
		width: 40px;
		text-align: center !important;
		color: var(--ink-dim);
	}

	.w-en {
		font-weight: 700;
	}

	.w-check {
		width: 62px;
		text-align: center !important;
	}

	.w-check i {
		display: inline-block;
		width: 14px;
		height: 14px;
		border: 1.5px solid var(--ink);
		border-radius: 2px;
		vertical-align: middle;
	}

	.sentences,
	.cloze {
		padding-left: 1.9em;
		display: grid;
		gap: 10px;
	}

	.sentences li,
	.cloze li {
		break-inside: avoid;
	}

	.sentences li::marker,
	.cloze li::marker {
		font-size: 12.5px;
		font-weight: 700;
		color: var(--accent);
	}

	.s-en {
		font-weight: 500;
	}

	.lead {
		font-size: 13.5px;
		color: var(--ink-dim);
		margin-bottom: 10px;
	}

	.c-en {
		line-height: 2.1;
	}

	.gap {
		display: inline-block;
		min-width: calc(var(--ch) * 0.62em + 1.6em);
		padding: 0 4px;
		text-align: center;
		border-bottom: 1.5px solid var(--ink);
		line-height: 1.3;
		color: var(--accent);
		font-weight: 700;
	}

	.gap sup {
		float: left;
		font-size: 9.5px;
		font-weight: 700;
		color: var(--ink-dim);
		line-height: 1;
		margin-right: 2px;
	}

	.answers {
		margin-top: 18px;
		display: flex;
		flex-direction: column;
		align-items: flex-start;
		gap: 10px;
	}

	.answers .tool {
		color: var(--ink);
		border-color: var(--ink);
	}

	.key {
		display: none;
		flex-wrap: wrap;
		gap: 4px 16px;
		padding: 10px 14px;
		font-size: 13px;
		border: 1px dashed var(--ink-dim);
		width: 100%;
	}

	.key.open {
		display: flex;
	}

	.key b {
		font-size: 11.5px;
		letter-spacing: 0.1em;
		color: var(--ink-dim);
	}

	.key sup {
		font-size: 9.5px;
		color: var(--ink-dim);
		margin-right: 2px;
	}

	.foot {
		display: flex;
		justify-content: space-between;
		gap: 16px;
		margin-top: 36px;
		padding-top: 10px;
		border-top: 1px solid var(--hair);
		font-size: 11px;
		color: var(--ink-dim);
	}

	.foot span:last-child {
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	.empty {
		padding: 40px 0;
		text-align: center;
		color: var(--ink-dim);
	}

	@media (max-width: 640px) {
		.sheet {
			padding: 28px 20px 24px;
			font-size: 14.5px;
		}

		.head-top {
			flex-wrap: wrap;
			gap: 10px 16px;
		}

		.stamp {
			width: 100%;
			margin-right: 0;
			text-align: center;
		}

		.fill i {
			width: 80px;
		}

		h1 {
			font-size: 23px;
		}
	}

	/* Printing: only the sheet, flat, with the answer key at the very end. */
	@media print {
		/* Scoped to pages showing a sheet: this stylesheet stays loaded after leaving the mode. */
		:global(body:has(.sheet-wrap) .navbar),
		:global(body:has(.sheet-wrap) footer),
		.sheet-tools,
		.no-print {
			display: none !important;
		}

		:global(body:has(.sheet-wrap) .main) {
			padding: 0 !important;
			max-width: none !important;
		}

		.sheet-wrap {
			max-width: none;
		}

		.sheet {
			padding: 0;
			border: none;
			box-shadow: none;
		}

		.key {
			display: flex;
			margin-top: 12px;
		}

		.gap.filled {
			color: transparent;
		}

		.stamp,
		.num,
		.theme,
		.words th {
			-webkit-print-color-adjust: exact;
			print-color-adjust: exact;
		}
	}
</style>
