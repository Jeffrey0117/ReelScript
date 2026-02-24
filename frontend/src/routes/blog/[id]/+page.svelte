<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/state';
	import { publicArticle, publicAudio, audioFileUrl, type ArticleData, type AudioData } from '$lib/api';
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
			// ignore
		} finally {
			audioLoading = false;
		}
	}

	function handleAudioPlay() { isPlaying = true; }
	function handleAudioPause() { isPlaying = false; }

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

<article class="post">
	<a href="/blog" class="back-link">
		<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
			<polyline points="15 18 9 12 15 6"/>
		</svg>
		{t('blogBackToList')}
	</a>

	{#if loading}
		<div class="post-skeleton">
			<div class="sk wide"></div>
			<div class="sk narrow"></div>
			<div class="sk wide"></div>
			<div class="sk wide"></div>
		</div>
	{:else if error}
		<p class="error-msg">{error}</p>
	{:else if article}
		<!-- Header -->
		<header class="post-header">
			<h1>{article.title || t('untitled')}</h1>
			<div class="post-meta">
				{#if article.channel}<span>{article.channel}</span>{/if}
				{#if article.duration}<span>{formatDuration(article.duration)}</span>{/if}
				<span class="badge {article.source === 'ig' ? 'badge-ig' : 'badge-youtube'}">
					{article.source === 'ig' ? 'Instagram' : 'YouTube'}
				</span>
			</div>
		</header>

		<!-- Audio -->
		<div class="audio-bar">
			<button class="audio-btn" onclick={loadAndPlayAudio} disabled={audioLoading}>
				{#if audioLoading}
					<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="spin"><path d="M21 12a9 9 0 1 1-6.219-8.56"/></svg>
				{:else if isPlaying}
					<svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><rect x="6" y="4" width="4" height="16"/><rect x="14" y="4" width="4" height="16"/></svg>
				{:else}
					<svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path d="M8 5v14l11-7z"/></svg>
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
					class="audio-el"
				></audio>
			{/if}
		</div>

		<!-- Theme intro -->
		{#if article.theme}
			<p class="lead">{article.theme}</p>
		{/if}

		<!-- Key points as intro bullets -->
		{#if article.keyPoints.length > 0}
			<ul class="highlights">
				{#each article.keyPoints as point}
					<li>{point}</li>
				{/each}
			</ul>
		{/if}

		<hr class="divider" />

		<!-- Body: full text as prose -->
		{#if article.fullText}
			<div class="prose">
				{#each article.fullText.split('\n').filter(Boolean) as paragraph}
					<p>{paragraph}</p>
				{/each}
			</div>
		{/if}

		<!-- Golden quotes as pull quotes -->
		{#if article.goldenQuotes.length > 0}
			<hr class="divider" />
			{#each article.goldenQuotes as quote}
				<blockquote class="pullquote">
					<p class="pq-en">"{quote.en}"</p>
					<p class="pq-zh">{quote.zh}</p>
				</blockquote>
			{/each}
		{/if}
	{/if}
</article>

<style>
	.post {
		max-width: 680px;
		margin: 0 auto;
		padding-bottom: 80px;
	}

	.back-link {
		display: inline-flex;
		align-items: center;
		gap: 4px;
		font-size: 13px;
		color: var(--text-dim);
		margin-bottom: 32px;
	}
	.back-link:hover { color: var(--accent); }

	/* Header */
	.post-header {
		margin-bottom: 24px;
	}

	.post-header h1 {
		font-size: 32px;
		font-weight: 700;
		line-height: 1.25;
		letter-spacing: -0.5px;
		margin-bottom: 12px;
	}

	.post-meta {
		display: flex;
		align-items: center;
		gap: 12px;
		font-size: 13px;
		color: var(--text-dim);
	}

	/* Audio */
	.audio-bar {
		display: flex;
		flex-direction: column;
		gap: 10px;
		margin-bottom: 28px;
	}

	.audio-btn {
		display: inline-flex;
		align-items: center;
		gap: 6px;
		padding: 8px 16px;
		font-size: 13px;
		font-weight: 500;
		color: var(--text-dim);
		background: var(--bg-card);
		border: 1px solid var(--border);
		border-radius: 20px;
		cursor: pointer;
		width: fit-content;
		transition: border-color 0.15s, color 0.15s;
	}
	.audio-btn:hover { border-color: var(--accent); color: var(--text); }
	.audio-btn:disabled { opacity: 0.5; cursor: not-allowed; }

	.audio-el {
		width: 100%;
		height: 36px;
		border-radius: 20px;
	}

	.spin { animation: spin 1s linear infinite; }
	@keyframes spin { to { transform: rotate(360deg); } }

	/* Lead / theme */
	.lead {
		font-size: 18px;
		line-height: 1.7;
		color: var(--text);
		margin-bottom: 20px;
		font-weight: 400;
	}

	/* Key points */
	.highlights {
		list-style: none;
		padding: 0;
		margin-bottom: 24px;
	}

	.highlights li {
		font-size: 15px;
		line-height: 1.7;
		padding: 4px 0 4px 18px;
		position: relative;
		color: var(--text);
	}

	.highlights li::before {
		content: '';
		position: absolute;
		left: 0;
		top: 13px;
		width: 6px;
		height: 6px;
		border-radius: 50%;
		background: var(--accent);
	}

	/* Divider */
	.divider {
		border: none;
		border-top: 1px solid var(--border);
		margin: 32px 0;
	}

	/* Prose body */
	.prose p {
		font-size: 16px;
		line-height: 1.8;
		margin-bottom: 20px;
		color: var(--text);
	}

	/* Pull quotes */
	.pullquote {
		margin: 28px 0;
		padding: 20px 24px;
		border-left: 3px solid var(--accent);
		background: var(--bg-card);
		border-radius: 0 var(--radius-sm) var(--radius-sm) 0;
	}

	.pq-en {
		font-size: 17px;
		font-style: italic;
		line-height: 1.6;
		font-weight: 500;
		margin-bottom: 6px;
	}

	.pq-zh {
		font-size: 14px;
		color: var(--text-dim);
		line-height: 1.5;
	}

	/* Skeleton */
	.post-skeleton { padding: 32px 0; }
	.sk {
		height: 16px;
		background: var(--border);
		border-radius: 4px;
		margin-bottom: 18px;
		animation: shimmer 1.5s infinite;
	}
	.sk.wide { width: 90%; }
	.sk.narrow { width: 45%; }

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
		.post-header h1 { font-size: 24px; }
		.lead { font-size: 16px; }
		.prose p { font-size: 15px; }
		.pq-en { font-size: 15px; }
	}
</style>
