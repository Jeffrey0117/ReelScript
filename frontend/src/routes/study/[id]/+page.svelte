<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import {
		getVideo,
		translateVideo,
		analyzeVocabulary,
		appreciateVideo,
		videoFileUrl,
		type VideoDetail,
		type VocabularyItem,
		type Appreciation,
	} from '$lib/api';
	import { t } from '$lib/i18n';

	let video = $state<VideoDetail | null>(null);
	let loading = $state(true);
	let translating = $state(false);
	let analyzing = $state(false);
	let appreciating = $state(false);

	// Audio player state
	let audioEl = $state<HTMLAudioElement | null>(null);
	let playing = $state(false);
	let currentTime = $state(0);
	let duration = $state(0);
	let playbackRate = $state(1);
	let volume = $state(1);

	let videoId = '';
	page.subscribe((p) => {
		videoId = p.params.id ?? '';
	});

	let segments = $derived(video?.transcript?.segments ?? []);

	let fullEnglish = $derived(
		segments.map((s) => s.text).join(' ')
	);

	// Sentence translations already end with 。so just join directly
	let fullChinese = $derived(
		segments.filter((s) => s.translation).map((s) => s.translation).join('')
	);

	let appreciation = $derived(video?.transcript?.appreciation ?? null);

	let audioSrc = $derived(
		video?.filename ? videoFileUrl(video.filename) : ''
	);

	// Playback state for transcript
	let activeSentenceIndex = $state(-1);
	let repeatIndex = $state(-1);

	// Merge whisper fragments into proper sentences
	interface MergedSentence {
		en: string;
		zh: string;
		vocabulary: VocabularyItem[];
		start: number;
		end: number;
	}

	let sentences = $derived.by(() => {
		const result: MergedSentence[] = [];
		let enBuf = '';
		let zhParts: string[] = [];
		let vocabBuf: VocabularyItem[] = [];
		let startTime = 0;
		let endTime = 0;

		for (const seg of segments) {
			if (!enBuf) startTime = seg.start;
			endTime = seg.end;
			enBuf += (enBuf ? ' ' : '') + seg.text;
			if (seg.translation) zhParts.push(seg.translation);
			vocabBuf = [...vocabBuf, ...(seg.vocabulary ?? [])];

			if (/[.!?]$/.test(seg.text.trim())) {
				result.push({
					en: enBuf.trim(),
					zh: zhParts.join(''),
					vocabulary: vocabBuf,
					start: startTime,
					end: endTime,
				});
				enBuf = '';
				zhParts = [];
				vocabBuf = [];
			}
		}
		if (enBuf.trim()) {
			result.push({ en: enBuf.trim(), zh: zhParts.join(''), vocabulary: vocabBuf, start: startTime, end: endTime });
		}
		return result;
	});

	let allVocabulary = $derived(
		segments
			.flatMap((s) => s.vocabulary ?? [])
			.filter((v, i, arr) => arr.findIndex((a) => a.word === v.word) === i)
	);

	onMount(async () => {
		video = await getVideo(videoId);
		loading = false;

		if (video?.transcript?.segments && !video.transcript.segments.some((s) => s.translation)) {
			await handleTranslate();
		}
		if (video?.transcript?.segments && !video.transcript.segments.some((s) => s.vocabulary?.length)) {
			await handleAnalyze();
		}
		if (video?.transcript?.full_text && !video.transcript.appreciation?.theme) {
			await handleAppreciate();
		}
	});

	async function handleTranslate() {
		if (!video || translating) return;
		translating = true;
		try {
			const result = await translateVideo(video.id);
			if (result.success && video.transcript) {
				video = { ...video, transcript: { ...video.transcript, segments: result.segments } };
			}
		} catch (e) {
			console.error('Translation failed:', e);
		} finally {
			translating = false;
		}
	}

	async function handleAnalyze() {
		if (!video || analyzing) return;
		analyzing = true;
		try {
			const result = await analyzeVocabulary(video.id);
			if (result.success && video.transcript) {
				video = { ...video, transcript: { ...video.transcript, segments: result.segments } };
			}
		} catch (e) {
			console.error('Vocabulary analysis failed:', e);
		} finally {
			analyzing = false;
		}
	}

	async function handleAppreciate() {
		if (!video || appreciating) return;
		appreciating = true;
		try {
			const result = await appreciateVideo(video.id);
			if (result.success && video.transcript) {
				video = { ...video, transcript: { ...video.transcript, appreciation: result.appreciation } };
			}
		} catch (e) {
			console.error('Appreciation failed:', e);
		} finally {
			appreciating = false;
		}
	}

	function highlightVocabulary(text: string, vocabulary: VocabularyItem[]): string {
		let result = text;
		for (const v of vocabulary) {
			const escaped = v.word.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
			const regex = new RegExp(`\\b(${escaped})\\b`, 'gi');
			result = result.replace(regex, '<mark class="vocab-hl">$1</mark>');
		}
		return result;
	}

	// Audio controls
	function togglePlay() {
		if (!audioEl) return;
		if (playing) {
			audioEl.pause();
		} else {
			audioEl.play();
		}
	}

	function onTimeUpdate() {
		if (!audioEl) return;
		currentTime = audioEl.currentTime;

		// Track active sentence
		const idx = sentences.findIndex(
			(s) => currentTime >= s.start && currentTime < s.end
		);
		activeSentenceIndex = idx;

		// Repeat single sentence
		if (repeatIndex >= 0 && repeatIndex < sentences.length) {
			const sent = sentences[repeatIndex];
			if (currentTime >= sent.end) {
				audioEl.currentTime = sent.start;
			}
		}
	}

	function onLoadedMetadata() {
		if (audioEl) duration = audioEl.duration;
	}

	function seekToBar(e: MouseEvent) {
		if (!audioEl || !duration) return;
		const bar = e.currentTarget as HTMLElement;
		const rect = bar.getBoundingClientRect();
		const ratio = (e.clientX - rect.left) / rect.width;
		audioEl.currentTime = ratio * duration;
	}

	function seekToSentence(index: number) {
		if (!audioEl || index < 0 || index >= sentences.length) return;
		audioEl.currentTime = sentences[index].start;
		audioEl.play();
	}

	function toggleRepeat(index: number) {
		if (repeatIndex === index) {
			repeatIndex = -1;
		} else {
			repeatIndex = index;
			seekToSentence(index);
		}
	}

	function cycleSpeed() {
		const speeds = [1, 1.25, 1.5, 0.75];
		const idx = speeds.indexOf(playbackRate);
		playbackRate = speeds[(idx + 1) % speeds.length];
		if (audioEl) audioEl.playbackRate = playbackRate;
	}

	function onVolumeChange(e: Event) {
		const input = e.target as HTMLInputElement;
		volume = parseFloat(input.value);
		if (audioEl) audioEl.volume = volume;
	}

	function formatTime(sec: number): string {
		const m = Math.floor(sec / 60);
		const s = Math.floor(sec % 60);
		return `${m}:${s.toString().padStart(2, '0')}`;
	}
</script>

<svelte:head>
	<title>{video?.title || t('loading')} — {t('studyMode')} — ReelScript</title>
</svelte:head>

{#if loading}
	<div class="loading">{t('preparing')}</div>
{:else if !video}
	<div class="loading">Video not found</div>
{:else}
	<div class="study-page">
		<!-- Header -->
		<div class="study-header">
			<div class="study-header-left">
				<a href="/watch/{video.id}" class="btn btn-ghost">{t('backToVideo')}</a>
				<h1>{video.title || t('untitled')}</h1>
			</div>
			{#if translating || analyzing || appreciating}
				<span class="status-pill">
					{translating ? t('translating') : analyzing ? t('analyzing') : t('appreciating')}
				</span>
			{/if}
		</div>

		{#if segments.length > 0}
			<!-- Section 1: 主旨 (top) -->
			<section class="section">
				<h2>{t('mainIdea')}</h2>
				{#if appreciation?.theme}
					<div class="appreciation-block">
						<div class="appr-item">
							<h3>{t('theme')}</h3>
							<p class="appr-theme">{appreciation.theme}</p>
						</div>

						{#if appreciation.keyPoints?.length}
							<div class="appr-item">
								<h3>{t('keyPoints')}</h3>
								<ul class="appr-points">
									{#each appreciation.keyPoints as point}
										<li>{point}</li>
									{/each}
								</ul>
							</div>
						{/if}

						{#if appreciation.goldenQuotes?.length}
							<div class="appr-item">
								<h3>{t('goldenQuotes')}</h3>
								<div class="quotes-list">
									{#each appreciation.goldenQuotes as quote}
										<blockquote class="golden-quote">
											<p class="quote-en">"{quote.en}"</p>
											<p class="quote-zh">{quote.zh}</p>
										</blockquote>
									{/each}
								</div>
							</div>
						{/if}
					</div>
				{:else if appreciating}
					<p class="empty">{t('appreciating')}</p>
				{/if}
			</section>

			<!-- Section 2: Vocabulary -->
			<section class="section">
				<h2>{t('vocabularyList')}</h2>
				{#if allVocabulary.length > 0}
					<div class="vocab-grid">
						{#each allVocabulary as v}
							<div class="vocab-card">
								<span class="vocab-en">{v.word}</span>
								<span class="vocab-zh">{v.translation}</span>
							</div>
						{/each}
					</div>
				{:else if analyzing}
					<p class="empty">{t('analyzing')}</p>
				{:else}
					<p class="empty">{t('noVocabulary')}</p>
				{/if}
			</section>

			<!-- Section 3: Sentence-by-Sentence Bilingual -->
			<section class="section">
				<h2>{t('transcript')}</h2>
				<div class="bilingual-list">
					{#each sentences as sent, i}
						<div class="bilingual-row" class:active={i === activeSentenceIndex} class:repeating={i === repeatIndex}>
							<div class="row-controls">
								<button
									class="row-play-btn"
									onclick={() => seekToSentence(i)}
									title="Play"
								>
									{#if i === activeSentenceIndex && playing}
										<svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><rect x="6" y="4" width="4" height="16" rx="1"/><rect x="14" y="4" width="4" height="16" rx="1"/></svg>
									{:else}
										<svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><polygon points="5,3 19,12 5,21"/></svg>
									{/if}
								</button>
								<button
									class="row-repeat-btn"
									class:locked={i === repeatIndex}
									onclick={() => toggleRepeat(i)}
									title="Repeat"
								>
									{#if i === repeatIndex}
										<svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><rect x="6" y="6" width="12" height="12" rx="2"/></svg>
									{:else}
										<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17 2l4 4-4 4"/><path d="M3 11v-1a4 4 0 0 1 4-4h14"/><path d="M7 22l-4-4 4-4"/><path d="M21 13v1a4 4 0 0 1-4 4H3"/></svg>
									{/if}
								</button>
							</div>
							<div class="row-content" role="button" tabindex="0" onclick={() => seekToSentence(i)} onkeydown={(e) => e.key === 'Enter' && seekToSentence(i)}>
								<p class="row-en">
									{#if sent.vocabulary.length}
										{@html highlightVocabulary(sent.en, sent.vocabulary)}
									{:else}
										{sent.en}
									{/if}
								</p>
								{#if sent.zh}
									<p class="row-zh">{sent.zh}</p>
								{/if}
							</div>
						</div>
					{/each}
				</div>
			</section>

			<!-- Section 4: Full Text -->
			<section class="section">
				<h2>{t('fullText')}</h2>
				<div class="fulltext-block">
					<div class="fulltext-en">{fullEnglish}</div>
					{#if fullChinese}
						<div class="fulltext-zh">{fullChinese}</div>
					{/if}
				</div>
			</section>
		{:else}
			<p class="empty">{t('noTranscript')}</p>
		{/if}
	</div>

	<!-- Audio Player Bar — fixed bottom -->
	{#if audioSrc}
		<div class="audio-bar">
			<audio
				bind:this={audioEl}
				ontimeupdate={onTimeUpdate}
				onloadedmetadata={onLoadedMetadata}
				onplay={() => playing = true}
				onpause={() => playing = false}
				onended={() => playing = false}
				preload="auto"
				playsinline
			>
				<source src={audioSrc} type="video/mp4" />
			</audio>
			<button class="audio-play-btn" onclick={togglePlay}>
				{#if playing}
					<svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor"><rect x="6" y="4" width="4" height="16" rx="1"/><rect x="14" y="4" width="4" height="16" rx="1"/></svg>
				{:else}
					<svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor"><polygon points="5,3 19,12 5,21"/></svg>
				{/if}
			</button>
			<span class="audio-time">{formatTime(currentTime)}</span>
			<!-- svelte-ignore a11y_click_events_have_key_events -->
			<!-- svelte-ignore a11y_no_static_element_interactions -->
			<div class="audio-progress" onclick={seekToBar}>
				<div class="audio-progress-fill" style="width: {duration ? (currentTime / duration * 100) : 0}%"></div>
			</div>
			<span class="audio-time">{formatTime(duration)}</span>
			<button class="audio-speed-btn" onclick={cycleSpeed}>
				{playbackRate}x
			</button>
			<input
				class="audio-volume"
				type="range"
				min="0"
				max="1"
				step="0.05"
				value={volume}
				oninput={onVolumeChange}
			/>
		</div>
	{/if}
{/if}

<style>
	.loading {
		text-align: center;
		padding: 80px 0;
		color: var(--text-dim);
	}

	.study-page {
		max-width: 800px;
		margin: 0 auto;
		padding-bottom: 88px;
	}

	/* Header */
	.study-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 16px;
		margin-bottom: 20px;
		flex-wrap: wrap;
	}

	.study-header-left {
		display: flex;
		align-items: center;
		gap: 16px;
	}

	.study-header h1 {
		font-size: 20px;
		font-weight: 700;
	}

	.status-pill {
		padding: 4px 12px;
		border-radius: 20px;
		font-size: 13px;
		background: rgba(99, 102, 241, 0.12);
		color: var(--accent);
		animation: pulse 1.5s infinite;
	}

	@keyframes pulse {
		0%, 100% { opacity: 1; }
		50% { opacity: 0.5; }
	}

	/* Audio Player Bar — fixed bottom like music app */
	.audio-bar {
		display: flex;
		align-items: center;
		gap: 12px;
		padding: 12px 24px;
		background: var(--bg-card);
		border-top: 1px solid var(--border);
		position: fixed;
		bottom: 0;
		left: 0;
		right: 0;
		z-index: 50;
		box-shadow: 0 -4px 20px rgba(0, 0, 0, 0.15);
	}

	.audio-play-btn {
		width: 36px;
		height: 36px;
		border-radius: 50%;
		border: none;
		background: var(--accent);
		color: white;
		font-size: 14px;
		cursor: pointer;
		display: flex;
		align-items: center;
		justify-content: center;
		flex-shrink: 0;
		transition: background 0.15s;
	}

	.audio-play-btn:hover {
		background: var(--accent-hover);
	}

	.audio-time {
		font-size: 12px;
		color: var(--text-dim);
		font-variant-numeric: tabular-nums;
		min-width: 36px;
		flex-shrink: 0;
	}

	.audio-progress {
		flex: 1;
		height: 6px;
		background: var(--border);
		border-radius: 3px;
		cursor: pointer;
		position: relative;
		min-width: 0;
	}

	.audio-progress-fill {
		height: 100%;
		background: var(--accent);
		border-radius: 3px;
		transition: width 0.1s linear;
	}

	.audio-speed-btn {
		padding: 2px 8px;
		border-radius: 12px;
		border: 1px solid var(--border);
		background: transparent;
		color: var(--text-dim);
		font-size: 12px;
		cursor: pointer;
		flex-shrink: 0;
		transition: border-color 0.15s, color 0.15s;
	}

	.audio-speed-btn:hover {
		border-color: var(--accent);
		color: var(--accent);
	}

	.audio-volume {
		width: 64px;
		height: 4px;
		-webkit-appearance: none;
		appearance: none;
		background: var(--border);
		border-radius: 2px;
		outline: none;
		flex-shrink: 0;
		cursor: pointer;
	}

	.audio-volume::-webkit-slider-thumb {
		-webkit-appearance: none;
		width: 14px;
		height: 14px;
		border-radius: 50%;
		background: var(--accent);
		cursor: pointer;
	}

	.audio-volume::-moz-range-thumb {
		width: 14px;
		height: 14px;
		border-radius: 50%;
		background: var(--accent);
		border: none;
		cursor: pointer;
	}

	/* Sections */
	.section {
		margin-bottom: 48px;
	}

	.section h2 {
		font-size: 16px;
		font-weight: 600;
		color: var(--text-dim);
		text-transform: uppercase;
		letter-spacing: 1px;
		margin-bottom: 16px;
		padding-bottom: 8px;
		border-bottom: 1px solid var(--border);
	}

	/* Appreciation / Main Idea */
	.appreciation-block {
		display: flex;
		flex-direction: column;
		gap: 28px;
	}

	.appr-item h3 {
		font-size: 14px;
		font-weight: 600;
		color: var(--accent);
		margin-bottom: 8px;
	}

	.appr-theme {
		font-size: 18px;
		font-weight: 600;
		line-height: 1.6;
		color: var(--text);
	}

	.appr-points {
		list-style: none;
		padding: 0;
		display: flex;
		flex-direction: column;
		gap: 8px;
	}

	.appr-points li {
		font-size: 15px;
		line-height: 1.6;
		color: var(--text);
		padding-left: 16px;
		position: relative;
	}

	.appr-points li::before {
		content: '\B7';
		position: absolute;
		left: 0;
		color: var(--accent);
		font-weight: 700;
	}

	.quotes-list {
		display: flex;
		flex-direction: column;
		gap: 16px;
	}

	.golden-quote {
		margin: 0;
		padding: 16px 20px;
		border-left: 3px solid var(--accent);
		background: var(--bg-card);
		border-radius: 0 var(--radius-sm) var(--radius-sm) 0;
	}

	.quote-en {
		font-size: 15px;
		line-height: 1.7;
		color: var(--text);
		font-style: italic;
		margin-bottom: 6px;
	}

	.quote-zh {
		font-size: 14px;
		line-height: 1.6;
		color: var(--text-dim);
	}

	/* Vocabulary Grid */
	.vocab-grid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
		gap: 8px;
	}

	.vocab-card {
		display: flex;
		flex-direction: column;
		gap: 4px;
		padding: 12px 16px;
		border-radius: var(--radius-sm);
		background: var(--bg-card);
		border: 1px solid var(--border);
		transition: border-color 0.15s;
	}

	.vocab-card:hover {
		border-color: var(--accent);
	}

	.vocab-en {
		font-weight: 600;
		font-size: 15px;
		color: var(--accent);
		word-break: break-word;
	}

	.vocab-zh {
		font-size: 14px;
		color: var(--text-dim);
	}

	/* Bilingual */
	.bilingual-list {
		display: flex;
		flex-direction: column;
		gap: 2px;
	}

	.bilingual-row {
		display: flex;
		gap: 12px;
		padding: 14px 16px;
		border-radius: var(--radius-sm);
		transition: background 0.15s;
		cursor: pointer;
	}

	.bilingual-row:hover {
		background: var(--bg-card);
	}

	.bilingual-row.active {
		background: rgba(99, 102, 241, 0.1);
	}

	.bilingual-row.active .row-en {
		color: var(--accent-hover);
	}

	.bilingual-row.repeating {
		background: rgba(99, 102, 241, 0.16);
		outline: 1px solid var(--accent);
	}

	.row-controls {
		display: flex;
		flex-direction: column;
		gap: 4px;
		flex-shrink: 0;
		padding-top: 2px;
	}

	.row-play-btn,
	.row-repeat-btn {
		width: 28px;
		height: 28px;
		border-radius: 50%;
		display: flex;
		align-items: center;
		justify-content: center;
		font-size: 12px;
		color: var(--text-dim);
		background: transparent;
		transition: background 0.15s, color 0.15s;
	}

	.row-play-btn:hover {
		background: var(--accent);
		color: white;
	}

	.row-repeat-btn {
		opacity: 0;
		font-size: 14px;
	}

	.bilingual-row:hover .row-repeat-btn {
		opacity: 1;
	}

	.row-repeat-btn:hover {
		background: var(--bg-hover);
		color: var(--accent);
	}

	.row-repeat-btn.locked {
		opacity: 1;
		color: var(--accent);
		background: rgba(99, 102, 241, 0.2);
	}

	.row-content {
		flex: 1;
		min-width: 0;
	}

	.row-en {
		font-size: 16px;
		line-height: 1.7;
		margin-bottom: 4px;
		color: var(--text);
	}

	.row-zh {
		font-size: 14px;
		line-height: 1.6;
		color: var(--text-dim);
	}

	:global(.vocab-hl) {
		background: rgba(99, 102, 241, 0.18);
		color: var(--accent-hover);
		border-radius: 3px;
		padding: 0 2px;
	}

	/* Full Text */
	.fulltext-block {
		display: flex;
		flex-direction: column;
		gap: 24px;
	}

	.fulltext-en {
		font-size: 17px;
		line-height: 2;
		color: var(--text);
	}

	.fulltext-zh {
		font-size: 16px;
		line-height: 2;
		color: var(--text-dim);
		padding-top: 16px;
		border-top: 1px dashed var(--border);
	}

	.empty {
		color: var(--text-dim);
		font-size: 14px;
		padding: 16px 0;
	}

	@media (max-width: 640px) {
		.study-header {
			margin-bottom: 12px;
		}

		.study-header-left {
			flex-direction: column;
			align-items: flex-start;
			gap: 8px;
		}

		.study-header h1 {
			font-size: 17px;
		}

		.audio-bar {
			gap: 6px;
			padding: 10px 16px;
		}

		.audio-play-btn {
			width: 40px;
			height: 40px;
			font-size: 16px;
		}

		.audio-volume {
			display: none;
		}

		.section {
			margin-bottom: 32px;
		}

		.vocab-grid {
			grid-template-columns: 1fr;
		}

		.bilingual-row {
			padding: 10px 8px;
			gap: 8px;
		}

		.row-controls {
			flex-direction: row;
			gap: 2px;
		}

		.row-play-btn {
			width: 32px;
			height: 32px;
			font-size: 14px;
		}

		.row-repeat-btn {
			opacity: 1;
			width: 32px;
			height: 32px;
		}

		.row-en {
			font-size: 14px;
		}

		.row-zh {
			font-size: 13px;
		}

		.fulltext-en {
			font-size: 15px;
			line-height: 1.8;
		}

		.fulltext-zh {
			font-size: 14px;
			line-height: 1.8;
		}

		.appr-theme {
			font-size: 16px;
		}

		.golden-quote {
			padding: 12px 16px;
		}
	}
</style>
