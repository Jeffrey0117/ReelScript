<script lang="ts">
	// Reading mode: the transcript as a long-form article, in four language layouts.
	import { thumbnailUrl, type VideoDetail } from '$lib/api';
	import { t } from '$lib/i18n';
	import { toParagraphs, readingMinutes, type Sentence } from '$lib/lesson';
	import { mt, type ModeTextKey } from '$lib/modes/text';
	import InteractiveText from '$lib/components/InteractiveText.svelte';

	type Lang = 'en' | 'zh' | 'mixed' | 'pair';

	let {
		video,
		sentences,
		hasTranslation,
		translating,
		onTranslate,
	}: {
		video: VideoDetail;
		sentences: Sentence[];
		hasTranslation: boolean;
		translating: boolean;
		onTranslate: () => Promise<boolean>;
	} = $props();

	const LANGS: { id: Lang; label: ModeTextKey }[] = [
		{ id: 'en', label: 'readLangEn' },
		{ id: 'zh', label: 'readLangZh' },
		{ id: 'mixed', label: 'readLangMixed' },
		{ id: 'pair', label: 'readLangPair' },
	];
	const LANG_KEY = 'reelscript-read-lang';
	const SIZE_KEY = 'reelscript-read-size';
	const SIZES = [16, 18, 20, 22, 24];

	function stored(key: string): string | null {
		try {
			return localStorage.getItem(key);
		} catch {
			return null;
		}
	}

	function store(key: string, value: string) {
		try {
			localStorage.setItem(key, value);
		} catch {
			/* private mode: the choice just lasts for this visit */
		}
	}

	const savedLang = stored(LANG_KEY);
	const savedSize = Number(stored(SIZE_KEY));
	let lang = $state<Lang>(LANGS.some((l) => l.id === savedLang) ? (savedLang as Lang) : 'en');
	let size = $state(SIZES.includes(savedSize) ? savedSize : 18);

	let paragraphs = $derived(toParagraphs(sentences, 4));
	let appreciation = $derived(video.transcript?.appreciation ?? null);
	let quotes = $derived(appreciation?.goldenQuotes ?? []);
	// The stored title and theme exist only in Chinese. In the English-only view
	// the headline is the video's own best line instead (first golden quote, else
	// its opening sentence) so nothing Chinese is left on the page.
	let englishOnly = $derived(lang === 'en');
	let englishHeadline = $derived(quotes[0]?.en || sentences[0]?.en || '');
	let headline = $derived((englishOnly && englishHeadline) || video.title || t('untitled'));
	// Don't repeat the headline as the pull quote.
	let pullQuote = $derived((englishOnly && quotes[0]?.en ? quotes[1] : quotes[0]) ?? null);
	let needsZh = $derived(lang !== 'en' && !hasTranslation);
	let published = $derived(
		video.created_at
			? new Date(video.created_at).toLocaleDateString(englishOnly ? 'en-US' : undefined, { year: 'numeric', month: 'long', day: 'numeric' })
			: ''
	);

	function pickLang(next: Lang) {
		lang = next;
		store(LANG_KEY, next);
	}

	function resize(step: number) {
		const at = SIZES.indexOf(size) + step;
		if (at < 0 || at >= SIZES.length) return;
		size = SIZES[at];
		store(SIZE_KEY, String(size));
	}

	const joinEn = (group: Sentence[]) => group.map((s) => s.en).join(' ');
	const joinZh = (group: Sentence[]) => group.map((s) => s.zh).join('');
	const vocabOf = (group: Sentence[]) => group.flatMap((s) => s.vocabulary);
</script>

<article class="paper" style="--read-size: {size}px">
	<header class="masthead">
		<p class="kicker">
			<span>ReelScript</span>
			<span class="dot">·</span>
			<span>{englishOnly ? 'Read' : mt('readKicker')}</span>
		</p>
		<h1 class:latin={englishOnly && Boolean(englishHeadline)}>{headline}</h1>
		{#if appreciation?.theme && !englishOnly}
			<p class="dek">{appreciation.theme}</p>
		{/if}
		<p class="byline">
			{#if video.channel}<span class="by">{video.channel}</span>{/if}
			{#if published}<span>{published}</span>{/if}
			<span>{readingMinutes(sentences)} {englishOnly ? 'min read' : mt('readMinutes')}</span>
			<span>{sentences.length} {englishOnly ? 'sentences' : mt('readSentences')}</span>
		</p>
	</header>

	<div class="toolbar">
		<div class="langs" role="tablist">
			{#each LANGS as option (option.id)}
				<button
					role="tab"
					aria-selected={lang === option.id}
					class:on={lang === option.id}
					onclick={() => pickLang(option.id)}
				>{mt(option.label)}</button>
			{/each}
		</div>
		<div class="sizes">
			<button onclick={() => resize(-1)} disabled={size === SIZES[0]} title={mt('readFontSmaller')} aria-label={mt('readFontSmaller')}>A<small>−</small></button>
			<button onclick={() => resize(1)} disabled={size === SIZES[SIZES.length - 1]} title={mt('readFontLarger')} aria-label={mt('readFontLarger')}><b>A</b><small>+</small></button>
		</div>
	</div>

	{#if sentences.length === 0}
		<p class="notice">{mt('noTranscript')}</p>
	{:else if needsZh}
		<div class="notice">
			<p>{mt('needTranslation')}</p>
			<button class="btn btn-primary" onclick={onTranslate} disabled={translating}>
				{translating ? mt('translating') : mt('translate')}
			</button>
		</div>
	{:else if lang === 'pair'}
		<div class="pair">
			<div class="pair-head">
				<span></span>
				<span>{mt('readEnglish')}</span>
				<span>{mt('readChinese')}</span>
			</div>
			{#each sentences as sentence, i (i)}
				<div class="pair-row">
					<span class="pair-no">{String(i + 1).padStart(2, '0')}</span>
					<p class="pair-en"><InteractiveText text={sentence.en} vocabulary={sentence.vocabulary} videoId={video.id} /></p>
					<p class="pair-zh">{sentence.zh}</p>
				</div>
			{/each}
		</div>
	{:else}
		<div class="body" class:zh-only={lang === 'zh'}>
			{#if video.thumbnail}
				<figure class="figure">
					<img src={thumbnailUrl(video.thumbnail)} alt="" loading="lazy" />
					{#if video.channel}<figcaption>{video.channel}</figcaption>{/if}
				</figure>
			{/if}

			{#each paragraphs as group, i (i)}
				{#if lang === 'en' || lang === 'mixed'}
					<p class="en" class:lead={i === 0}>
						<InteractiveText text={joinEn(group)} vocabulary={vocabOf(group)} videoId={video.id} />
					</p>
				{/if}
				{#if lang === 'zh' || lang === 'mixed'}
					<p class="zh" class:lead={i === 0 && lang === 'zh'} class:gloss={lang === 'mixed'}>{joinZh(group)}</p>
				{/if}

				{#if i === 0 && pullQuote && paragraphs.length > 1}
					<blockquote class="pull">
						{#if lang !== 'zh'}<p>{pullQuote.en}</p>{/if}
						{#if lang !== 'en'}<p class="pull-zh">{pullQuote.zh}</p>{/if}
					</blockquote>
				{/if}
			{/each}
		</div>
	{/if}

	<!-- Key points are stored in Chinese only, so the English-only view leaves them out. -->
	{#if appreciation?.keyPoints?.length && !englishOnly}
		<aside class="points">
			<h2>{mt('readKeyPoints')}</h2>
			<ol>
				{#each appreciation.keyPoints as point, i (i)}
					<li>{point}</li>
				{/each}
			</ol>
		</aside>
	{/if}
</article>

<style>
	.paper {
		max-width: 760px;
		margin: 0 auto;
		font-family: var(--font-serif);
		color: var(--text);
	}

	/* Masthead */
	.masthead {
		text-align: center;
		padding: 12px 0 28px;
	}

	.kicker {
		display: inline-flex;
		gap: 8px;
		font-family: 'Inter', 'Noto Sans TC', sans-serif;
		font-size: 11.5px;
		font-weight: 700;
		letter-spacing: 0.22em;
		text-transform: uppercase;
		color: var(--accent);
		margin-bottom: 18px;
	}

	.kicker .dot {
		color: var(--text-dim);
	}

	h1 {
		font-family: var(--font-serif);
		font-size: clamp(30px, 5.4vw, 50px);
		font-weight: 700;
		line-height: 1.14;
		letter-spacing: -0.02em;
		text-wrap: balance;
	}

	h1.latin {
		letter-spacing: -0.025em;
	}

	.dek {
		margin: 18px auto 0;
		max-width: 560px;
		font-size: 19px;
		line-height: 1.6;
		font-style: italic;
		color: var(--text-dim);
		text-wrap: balance;
	}

	.byline {
		display: flex;
		flex-wrap: wrap;
		justify-content: center;
		gap: 6px 18px;
		margin-top: 22px;
		font-family: 'Inter', 'Noto Sans TC', sans-serif;
		font-size: 12.5px;
		letter-spacing: 0.04em;
		color: var(--text-dim);
	}

	.byline .by {
		color: var(--text);
		font-weight: 600;
	}

	/* Toolbar */
	.toolbar {
		position: sticky;
		top: 64px;
		z-index: 5;
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 12px;
		padding: 10px 0;
		margin-bottom: 30px;
		border-top: 1px solid var(--border);
		border-bottom: 1px solid var(--border);
		background: color-mix(in srgb, var(--bg) 92%, transparent);
		backdrop-filter: blur(8px);
		font-family: 'Inter', 'Noto Sans TC', sans-serif;
	}

	.langs {
		display: flex;
		gap: 2px;
		overflow-x: auto;
		scrollbar-width: none;
	}

	.langs button {
		flex-shrink: 0;
		padding: 6px 12px;
		font-size: 13px;
		font-weight: 600;
		color: var(--text-dim);
		border-radius: 4px;
		white-space: nowrap;
	}

	.langs button:hover {
		color: var(--text);
	}

	.langs button.on {
		color: var(--bg);
		background: var(--text);
	}

	.sizes {
		display: flex;
		gap: 2px;
		flex-shrink: 0;
	}

	.sizes button {
		padding: 4px 9px;
		font-family: var(--font-serif);
		font-size: 15px;
		color: var(--text-dim);
		border-radius: 4px;
	}

	.sizes button:hover:not(:disabled) {
		color: var(--text);
		background: var(--bg-hover);
	}

	.sizes button:disabled {
		opacity: 0.35;
		cursor: default;
	}

	.sizes b {
		font-size: 18px;
	}

	.sizes small {
		font-size: 11px;
		margin-left: 1px;
	}

	/* Body copy */
	.body {
		font-size: var(--read-size);
		line-height: 1.85;
	}

	.body::after {
		content: '';
		display: block;
		clear: both;
	}

	.body p {
		margin-bottom: 1.25em;
		overflow-wrap: break-word;
	}

	.en {
		hyphens: auto;
	}

	.en.lead::first-letter,
	.zh.lead::first-letter {
		float: left;
		font-size: 3.5em;
		line-height: 0.82;
		font-weight: 700;
		padding: 0.08em 0.1em 0 0;
		color: var(--accent);
	}

	.zh {
		font-family: 'Noto Serif TC', var(--font-serif);
		line-height: 2;
		letter-spacing: 0.02em;
	}

	.zh.gloss {
		font-size: 0.88em;
		color: var(--text-dim);
		padding-left: 16px;
		border-left: 2px solid color-mix(in srgb, var(--accent) 45%, transparent);
		margin-top: -0.5em;
		margin-bottom: 1.9em;
	}

	.figure {
		float: right;
		width: 190px;
		margin: 6px 0 16px 28px;
	}

	.figure img {
		display: block;
		width: 100%;
		aspect-ratio: 4 / 5;
		object-fit: cover;
		border-radius: 2px;
		filter: saturate(0.9);
	}

	.figure figcaption {
		margin-top: 6px;
		font-family: 'Inter', 'Noto Sans TC', sans-serif;
		font-size: 11.5px;
		color: var(--text-dim);
		border-bottom: 1px solid var(--border);
		padding-bottom: 6px;
	}

	.pull {
		clear: both;
		margin: 1.6em 0 1.8em;
		padding: 22px 0;
		border-top: 2px solid var(--text);
		border-bottom: 1px solid var(--border);
		text-align: center;
	}

	.pull p {
		margin: 0;
		font-size: 1.4em;
		line-height: 1.4;
		font-weight: 600;
		font-style: italic;
		text-wrap: balance;
	}

	.pull p::before {
		content: '“';
	}

	.pull p::after {
		content: '”';
	}

	.pull .pull-zh {
		margin-top: 10px;
		font-family: 'Noto Serif TC', var(--font-serif);
		font-size: 0.95em;
		font-style: normal;
		font-weight: 500;
		color: var(--text-dim);
	}

	.pull .pull-zh::before,
	.pull .pull-zh::after {
		content: none;
	}

	.pull .pull-zh:only-child {
		font-size: 1.3em;
		color: var(--text);
	}

	/* Side-by-side */
	.pair {
		font-size: calc(var(--read-size) - 1px);
		line-height: 1.7;
	}

	.pair-head,
	.pair-row {
		display: grid;
		grid-template-columns: 34px 1fr 1fr;
		gap: 0 22px;
	}

	.pair-head {
		font-family: 'Inter', 'Noto Sans TC', sans-serif;
		font-size: 11px;
		font-weight: 700;
		letter-spacing: 0.16em;
		text-transform: uppercase;
		color: var(--text-dim);
		padding-bottom: 8px;
		border-bottom: 2px solid var(--text);
	}

	.pair-row {
		padding: 14px 0;
		border-bottom: 1px solid var(--border);
	}

	.pair-no {
		font-family: var(--font-mono);
		font-size: 12px;
		color: var(--accent);
		padding-top: 0.35em;
	}

	.pair-zh {
		font-family: 'Noto Serif TC', var(--font-serif);
		color: var(--text-dim);
		padding-left: 22px;
		border-left: 1px solid var(--border);
	}

	/* Key points */
	.points {
		margin-top: 44px;
		padding: 22px 26px;
		border: 1px solid var(--text);
		background: var(--bg-card);
	}

	.points h2 {
		font-family: 'Inter', 'Noto Sans TC', sans-serif;
		font-size: 11.5px;
		font-weight: 700;
		letter-spacing: 0.2em;
		text-transform: uppercase;
		color: var(--accent);
		margin-bottom: 12px;
	}

	.points ol {
		padding-left: 1.3em;
		font-family: 'Noto Serif TC', var(--font-serif);
		font-size: 16px;
		line-height: 1.9;
	}

	.points li::marker {
		font-family: var(--font-serif);
		font-weight: 700;
		color: var(--accent);
	}

	.notice {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 14px;
		padding: 56px 0;
		font-family: 'Inter', 'Noto Sans TC', sans-serif;
		color: var(--text-dim);
		text-align: center;
	}

	@media (max-width: 640px) {
		.masthead {
			padding: 4px 0 20px;
		}

		.dek {
			font-size: 16.5px;
		}

		.toolbar {
			top: 56px;
			margin-bottom: 22px;
		}

		.langs button {
			padding: 6px 9px;
			font-size: 12.5px;
		}

		.figure {
			width: 112px;
			margin: 4px 0 10px 16px;
		}

		.pair-head {
			display: none;
		}

		.pair-row {
			grid-template-columns: 28px 1fr;
			gap: 4px 10px;
		}

		.pair-zh {
			grid-column: 2;
			padding-left: 0;
			border-left: none;
			font-size: 0.93em;
		}

		.points {
			padding: 18px;
		}
	}
</style>
