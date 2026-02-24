<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/state';
	import { publicArticle, publicAudio, audioFileUrl, thumbnailUrl, type ArticleData, type AudioData } from '$lib/api';
	import { t } from '$lib/i18n';

	let article = $state<ArticleData | null>(null);
	let audio = $state<AudioData | null>(null);
	let loading = $state(true);
	let error = $state('');
	let audioEl = $state<HTMLAudioElement | null>(null);
	let isPlaying = $state(false);
	let audioLoading = $state(false);

	const videoId = page.params.id;

	onMount(async () => {
		try {
			article = await publicArticle(videoId);
		} catch (e) {
			error = (e as Error).message || 'Failed to load article';
		} finally {
			loading = false;
		}
	});

	async function loadAndPlayAudio() {
		if (audioEl && audio) {
			if (isPlaying) {
				audioEl.pause();
			} else {
				audioEl.play();
			}
			return;
		}

		audioLoading = true;
		try {
			audio = await publicAudio(videoId);
		} catch {
			// Audio extraction may not be available
		} finally {
			audioLoading = false;
		}
	}

	function handleAudioPlay() {
		isPlaying = true;
	}

	function handleAudioPause() {
		isPlaying = false;
	}

	function formatDuration(seconds: number | null): string {
		if (!seconds) return '';
		const m = Math.floor(seconds / 60);
		const s = Math.floor(seconds % 60);
		return `${m}:${s.toString().padStart(2, '0')}`;
	}
</script>

<svelte:head>
	<title>{article?.title || t('loading')} — {t('blog')}</title>
</svelte:head>

<article class="article-page">
	<a href="/blog" class="back-link">
		<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
			<polyline points="15 18 9 12 15 6"/>
		</svg>
		{t('blogBackToList')}
	</a>

	{#if loading}
		<div class="article-skeleton">
			<div class="skeleton-line wide"></div>
			<div class="skeleton-line narrow"></div>
			<div class="skeleton-line wide"></div>
			<div class="skeleton-line wide"></div>
			<div class="skeleton-line narrow"></div>
		</div>
	{:else if error}
		<p class="error-msg">{error}</p>
	{:else if article}
		<header class="article-header">
			<h1 class="article-title">{article.title || t('untitled')}</h1>
			<div class="article-meta">
				{#if article.channel}
					<span class="meta-item">{article.channel}</span>
				{/if}
				{#if article.source}
					<span class="meta-item badge {article.source === 'ig' ? 'badge-ig' : 'badge-youtube'}">
						{article.source === 'ig' ? 'IG' : 'YT'}
					</span>
				{/if}
				{#if article.duration}
					<span class="meta-item">{formatDuration(article.duration)}</span>
				{/if}
			</div>

			<!-- Audio player -->
			<div class="audio-section">
				<button
					class="btn-audio"
					onclick={loadAndPlayAudio}
					disabled={audioLoading}
				>
					{#if audioLoading}
						<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="spin">
							<path d="M21 12a9 9 0 1 1-6.219-8.56"/>
						</svg>
					{:else if isPlaying}
						<svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
							<rect x="6" y="4" width="4" height="16"/>
							<rect x="14" y="4" width="4" height="16"/>
						</svg>
					{:else}
						<svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
							<path d="M8 5v14l11-7z"/>
						</svg>
					{/if}
					{t('blogListenAudio')}
				</button>
				{#if audio}
					<audio
						bind:this={audioEl}
						src={audioFileUrl(audio.audioUrl)}
						onplay={handleAudioPlay}
						onpause={handleAudioPause}
						autoplay
						controls
						class="audio-player"
					></audio>
				{/if}
			</div>
		</header>

		<!-- Theme & Key Points -->
		{#if article.theme}
			<section class="article-section">
				<h2>{t('theme')}</h2>
				<p class="theme-text">{article.theme}</p>
			</section>
		{/if}

		{#if article.keyPoints.length > 0}
			<section class="article-section">
				<h2>{t('keyPoints')}</h2>
				<ul class="key-points">
					{#each article.keyPoints as point}
						<li>{point}</li>
					{/each}
				</ul>
			</section>
		{/if}

		<!-- Golden Quotes -->
		{#if article.goldenQuotes.length > 0}
			<section class="article-section">
				<h2>{t('goldenQuotes')}</h2>
				<div class="quotes">
					{#each article.goldenQuotes as quote}
						<blockquote class="quote-card">
							<p class="quote-en">{quote.en}</p>
							<p class="quote-zh">{quote.zh}</p>
						</blockquote>
					{/each}
				</div>
			</section>
		{/if}

		<!-- Transcript segments -->
		{#if article.segments.length > 0}
			<section class="article-section">
				<h2>{t('blogTranscript')}</h2>
				<div class="segments">
					{#each article.segments as seg}
						<div class="segment">
							<span class="seg-time">{seg.timestamp}</span>
							<div class="seg-text">
								<p class="seg-en">{seg.en}</p>
								<p class="seg-zh">{seg.zh}</p>
							</div>
						</div>
					{/each}
				</div>
			</section>
		{/if}

		<!-- Vocabulary -->
		{#if article.vocabulary.length > 0}
			<section class="article-section">
				<h2>{t('blogVocabulary')}</h2>
				<div class="vocab-grid">
					{#each article.vocabulary as item}
						<div class="vocab-item">
							<span class="vocab-word">{item.word}</span>
							<span class="vocab-meaning">{item.translation}</span>
						</div>
					{/each}
				</div>
			</section>
		{/if}
	{/if}
</article>

<style>
	.article-page {
		max-width: 720px;
		margin: 0 auto;
		padding-top: 8px;
		padding-bottom: 64px;
	}

	.back-link {
		display: inline-flex;
		align-items: center;
		gap: 4px;
		font-size: 14px;
		color: var(--text-dim);
		margin-bottom: 24px;
		transition: color 0.15s;
	}

	.back-link:hover {
		color: var(--accent);
	}

	.article-header {
		margin-bottom: 32px;
	}

	.article-title {
		font-size: 28px;
		font-weight: 700;
		line-height: 1.3;
		letter-spacing: -0.5px;
		margin-bottom: 12px;
	}

	.article-meta {
		display: flex;
		align-items: center;
		gap: 12px;
		margin-bottom: 16px;
	}

	.meta-item {
		font-size: 13px;
		color: var(--text-dim);
	}

	/* Audio */
	.audio-section {
		display: flex;
		flex-direction: column;
		gap: 12px;
	}

	.btn-audio {
		display: inline-flex;
		align-items: center;
		gap: 8px;
		padding: 10px 20px;
		background: var(--bg-hover);
		border: 1px solid var(--border);
		border-radius: var(--radius-sm);
		font-size: 14px;
		font-weight: 500;
		color: var(--text);
		cursor: pointer;
		transition: border-color 0.15s, background 0.15s;
		width: fit-content;
	}

	.btn-audio:hover {
		border-color: var(--accent);
		background: var(--bg-card);
	}

	.btn-audio:disabled {
		opacity: 0.6;
		cursor: not-allowed;
	}

	.audio-player {
		width: 100%;
		height: 40px;
		border-radius: var(--radius-sm);
	}

	.spin {
		animation: spin 1s linear infinite;
	}

	@keyframes spin {
		to { transform: rotate(360deg); }
	}

	/* Sections */
	.article-section {
		margin-bottom: 32px;
	}

	.article-section h2 {
		font-size: 18px;
		font-weight: 600;
		margin-bottom: 12px;
		padding-bottom: 8px;
		border-bottom: 1px solid var(--border);
	}

	.theme-text {
		font-size: 15px;
		line-height: 1.6;
		color: var(--text);
	}

	.key-points {
		list-style: none;
		padding: 0;
	}

	.key-points li {
		font-size: 14px;
		line-height: 1.6;
		padding: 6px 0 6px 20px;
		position: relative;
		color: var(--text);
	}

	.key-points li::before {
		content: '';
		position: absolute;
		left: 0;
		top: 14px;
		width: 6px;
		height: 6px;
		border-radius: 50%;
		background: var(--accent);
	}

	/* Quotes */
	.quotes {
		display: flex;
		flex-direction: column;
		gap: 12px;
	}

	.quote-card {
		background: var(--bg-card);
		border-left: 3px solid var(--accent);
		border-radius: 0 var(--radius-sm) var(--radius-sm) 0;
		padding: 16px 20px;
	}

	.quote-en {
		font-size: 15px;
		font-weight: 500;
		line-height: 1.5;
		margin-bottom: 4px;
		font-style: italic;
	}

	.quote-zh {
		font-size: 13px;
		color: var(--text-dim);
		line-height: 1.5;
	}

	/* Segments */
	.segments {
		display: flex;
		flex-direction: column;
		gap: 2px;
	}

	.segment {
		display: flex;
		gap: 12px;
		padding: 10px 12px;
		border-radius: var(--radius-sm);
		transition: background 0.15s;
	}

	.segment:hover {
		background: var(--bg-hover);
	}

	.seg-time {
		font-size: 12px;
		color: var(--text-dim);
		font-variant-numeric: tabular-nums;
		min-width: 42px;
		flex-shrink: 0;
		padding-top: 2px;
	}

	.seg-text {
		flex: 1;
	}

	.seg-en {
		font-size: 14px;
		line-height: 1.5;
		margin-bottom: 2px;
	}

	.seg-zh {
		font-size: 13px;
		color: var(--text-dim);
		line-height: 1.5;
	}

	/* Vocabulary */
	.vocab-grid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
		gap: 8px;
	}

	.vocab-item {
		display: flex;
		flex-direction: column;
		gap: 2px;
		padding: 10px 14px;
		background: var(--bg-card);
		border: 1px solid var(--border);
		border-radius: var(--radius-sm);
	}

	.vocab-word {
		font-size: 14px;
		font-weight: 600;
	}

	.vocab-meaning {
		font-size: 12px;
		color: var(--text-dim);
	}

	/* Skeleton */
	.article-skeleton {
		padding: 24px 0;
	}

	.skeleton-line {
		height: 16px;
		background: var(--border);
		border-radius: 4px;
		margin-bottom: 16px;
		animation: shimmer 1.5s infinite;
	}

	.skeleton-line.wide { width: 90%; }
	.skeleton-line.narrow { width: 50%; }

	@keyframes shimmer {
		0% { opacity: 0.5; }
		50% { opacity: 1; }
		100% { opacity: 0.5; }
	}

	.error-msg {
		color: var(--danger);
		text-align: center;
		padding: 48px 0;
	}

	@media (max-width: 640px) {
		.article-title {
			font-size: 22px;
		}

		.article-section h2 {
			font-size: 16px;
		}

		.vocab-grid {
			grid-template-columns: 1fr;
		}

		.segment {
			flex-direction: column;
			gap: 4px;
		}

		.seg-time {
			font-size: 11px;
		}
	}
</style>
