<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import {
		getVideo,
		translateVideo,
		analyzeVocabulary,
		type VideoDetail,
		type VocabularyItem,
	} from '$lib/api';
	import { t } from '$lib/i18n';

	let video = $state<VideoDetail | null>(null);
	let loading = $state(true);
	let translating = $state(false);
	let analyzing = $state(false);

	let videoId = '';
	page.subscribe((p) => {
		videoId = p.params.id ?? '';
	});

	// Derived: all unique vocabulary items
	let allVocabulary = $derived(
		(video?.transcript?.segments ?? [])
			.flatMap((s) => s.vocabulary ?? [])
			.filter((v, i, arr) => arr.findIndex((a) => a.word === v.word) === i)
	);

	let hasTranslation = $derived(
		video?.transcript?.segments?.some((s) => s.translation) ?? false
	);

	let hasVocabulary = $derived(
		video?.transcript?.segments?.some((s) => s.vocabulary?.length) ?? false
	);

	onMount(async () => {
		video = await getVideo(videoId);
		loading = false;

		// Auto-trigger translation if not done
		if (video?.transcript?.segments && !video.transcript.segments.some((s) => s.translation)) {
			await handleTranslate();
		}
		// Auto-trigger vocabulary if not done
		if (video?.transcript?.segments && !video.transcript.segments.some((s) => s.vocabulary?.length)) {
			await handleAnalyze();
		}
	});

	async function handleTranslate() {
		if (!video || translating) return;
		translating = true;
		try {
			const result = await translateVideo(video.id);
			if (result.success && video.transcript) {
				video = {
					...video,
					transcript: { ...video.transcript, segments: result.segments },
				};
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
				video = {
					...video,
					transcript: { ...video.transcript, segments: result.segments },
				};
			}
		} catch (e) {
			console.error('Vocabulary analysis failed:', e);
		} finally {
			analyzing = false;
		}
	}

	function formatTime(seconds: number): string {
		const m = Math.floor(seconds / 60);
		const s = Math.floor(seconds % 60);
		return `${m}:${s.toString().padStart(2, '0')}`;
	}

	function highlightVocabulary(text: string, vocabulary: VocabularyItem[]): string {
		let result = text;
		for (const v of vocabulary) {
			const escaped = v.word.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
			const regex = new RegExp(`\\b(${escaped})\\b`, 'gi');
			result = result.replace(regex, '<mark class="vocab-highlight">$1</mark>');
		}
		return result;
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
	<div class="study-layout">
		<!-- Header -->
		<div class="study-header">
			<div class="study-header-left">
				<a href="/watch/{video.id}" class="btn btn-ghost">{t('backToVideo')}</a>
				<h1>{video.title || t('untitled')}</h1>
			</div>
			<div class="study-header-actions">
				{#if translating || analyzing}
					<span class="status-pill">
						{translating ? t('translating') : t('analyzing')}
					</span>
				{/if}
			</div>
		</div>

		<div class="study-content">
			<!-- Main: Transcript Segments -->
			<div class="segments-panel">
				{#if video.transcript?.segments}
					{#each video.transcript.segments as segment (segment.index)}
						<div class="study-segment">
							<span class="seg-time">{formatTime(segment.start)}</span>
							<div class="seg-body">
								<p class="seg-english">
									{#if segment.vocabulary?.length}
										{@html highlightVocabulary(segment.text, segment.vocabulary)}
									{:else}
										{segment.text}
									{/if}
								</p>
								{#if segment.translation}
									<p class="seg-chinese">{segment.translation}</p>
								{/if}
								{#if segment.vocabulary?.length}
									<div class="seg-vocab">
										{#each segment.vocabulary as v}
											<span class="vocab-chip">
												<strong>{v.word}</strong> {v.translation}
											</span>
										{/each}
									</div>
								{/if}
							</div>
						</div>
					{/each}
				{:else}
					<p class="empty">{t('noTranscript')}</p>
				{/if}
			</div>

			<!-- Sidebar: Vocabulary Summary -->
			<div class="vocab-sidebar">
				<h2>{t('vocabularyList')}</h2>
				{#if allVocabulary.length > 0}
					<div class="vocab-count">{allVocabulary.length} {t('word')}</div>
					<div class="vocab-table">
						{#each allVocabulary as v}
							<div class="vocab-row">
								<span class="vocab-word">{v.word}</span>
								<span class="vocab-meaning">{v.translation}</span>
							</div>
						{/each}
					</div>
				{:else if analyzing}
					<p class="empty">{t('analyzing')}</p>
				{:else}
					<p class="empty">{t('noVocabulary')}</p>
				{/if}
			</div>
		</div>
	</div>
{/if}

<style>
	.loading {
		text-align: center;
		padding: 80px 0;
		color: var(--text-dim);
	}

	.study-layout {
		max-width: 1200px;
		margin: 0 auto;
	}

	.study-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 16px;
		margin-bottom: 32px;
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

	.study-content {
		display: grid;
		grid-template-columns: 1fr 280px;
		gap: 32px;
		align-items: start;
	}

	@media (max-width: 900px) {
		.study-content {
			grid-template-columns: 1fr;
		}
	}

	/* Segments */
	.segments-panel {
		display: flex;
		flex-direction: column;
		gap: 4px;
	}

	.study-segment {
		display: flex;
		gap: 16px;
		padding: 16px;
		border-radius: var(--radius-sm);
		transition: background 0.15s;
	}

	.study-segment:hover {
		background: var(--bg-card);
	}

	.seg-time {
		color: var(--text-dim);
		font-size: 12px;
		font-variant-numeric: tabular-nums;
		min-width: 40px;
		padding-top: 3px;
		flex-shrink: 0;
	}

	.seg-body {
		flex: 1;
		min-width: 0;
	}

	.seg-english {
		font-size: 16px;
		line-height: 1.7;
		margin-bottom: 4px;
	}

	.seg-chinese {
		font-size: 15px;
		line-height: 1.6;
		color: var(--text-dim);
		margin-bottom: 6px;
	}

	.seg-vocab {
		display: flex;
		flex-wrap: wrap;
		gap: 6px;
		margin-top: 8px;
	}

	.vocab-chip {
		display: inline-flex;
		gap: 4px;
		padding: 2px 10px;
		border-radius: 20px;
		font-size: 12px;
		background: rgba(99, 102, 241, 0.1);
		color: var(--accent-hover);
	}

	.vocab-chip strong {
		color: var(--accent);
	}

	:global(.vocab-highlight) {
		background: rgba(99, 102, 241, 0.18);
		color: var(--accent-hover);
		border-radius: 3px;
		padding: 0 2px;
	}

	/* Sidebar */
	.vocab-sidebar {
		position: sticky;
		top: 72px;
		background: var(--bg-card);
		border: 1px solid var(--border);
		border-radius: var(--radius);
		padding: 20px;
	}

	.vocab-sidebar h2 {
		font-size: 16px;
		font-weight: 600;
		margin-bottom: 8px;
	}

	.vocab-count {
		font-size: 13px;
		color: var(--text-dim);
		margin-bottom: 16px;
	}

	.vocab-table {
		display: flex;
		flex-direction: column;
		gap: 2px;
		max-height: 60vh;
		overflow-y: auto;
	}

	.vocab-row {
		display: flex;
		justify-content: space-between;
		padding: 8px 10px;
		border-radius: var(--radius-sm);
		font-size: 14px;
	}

	.vocab-row:hover {
		background: var(--bg-hover);
	}

	.vocab-word {
		font-weight: 600;
		color: var(--accent);
	}

	.vocab-meaning {
		color: var(--text-dim);
		font-size: 13px;
	}

	.empty {
		color: var(--text-dim);
		font-size: 14px;
		padding: 16px 0;
	}
</style>
