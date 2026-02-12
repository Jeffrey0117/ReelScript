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

	let segments = $derived(video?.transcript?.segments ?? []);

	let fullEnglish = $derived(
		segments.map((s) => s.text).join(' ')
	);

	let fullChinese = $derived(
		segments.filter((s) => s.translation).map((s) => s.translation).join(' ')
	);

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

	function highlightVocabulary(text: string, vocabulary: VocabularyItem[]): string {
		let result = text;
		for (const v of vocabulary) {
			const escaped = v.word.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
			const regex = new RegExp(`\\b(${escaped})\\b`, 'gi');
			result = result.replace(regex, '<mark class="vocab-hl">$1</mark>');
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
	<div class="study-page">
		<!-- Header -->
		<div class="study-header">
			<div class="study-header-left">
				<a href="/watch/{video.id}" class="btn btn-ghost">{t('backToVideo')}</a>
				<h1>{video.title || t('untitled')}</h1>
			</div>
			{#if translating || analyzing}
				<span class="status-pill">
					{translating ? t('translating') : t('analyzing')}
				</span>
			{/if}
		</div>

		{#if segments.length > 0}
			<!-- Section 1: Full Text -->
			<section class="section">
				<h2>{t('fullText')}</h2>
				<div class="fulltext-block">
					<div class="fulltext-en">{fullEnglish}</div>
					{#if fullChinese}
						<div class="fulltext-zh">{fullChinese}</div>
					{/if}
				</div>
			</section>

			<!-- Section 2: Sentence-by-Sentence Bilingual -->
			<section class="section">
				<h2>{t('transcript')}</h2>
				<div class="bilingual-list">
					{#each segments as seg, i (seg.index)}
						<div class="bilingual-row">
							<span class="row-num">{i + 1}</span>
							<div class="row-content">
								{#if seg.translation}
									<p class="row-zh">{seg.translation}</p>
								{/if}
								<p class="row-en">
									{#if seg.vocabulary?.length}
										{@html highlightVocabulary(seg.text, seg.vocabulary)}
									{:else}
										{seg.text}
									{/if}
								</p>
							</div>
						</div>
					{/each}
				</div>
			</section>

			<!-- Section 3: Vocabulary -->
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
		{:else}
			<p class="empty">{t('noTranscript')}</p>
		{/if}
	</div>
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
	}

	/* Header */
	.study-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 16px;
		margin-bottom: 40px;
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

	/* Section 1: Full Text */
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

	/* Section 2: Bilingual */
	.bilingual-list {
		display: flex;
		flex-direction: column;
		gap: 2px;
	}

	.bilingual-row {
		display: flex;
		gap: 16px;
		padding: 14px 16px;
		border-radius: var(--radius-sm);
		transition: background 0.15s;
	}

	.bilingual-row:hover {
		background: var(--bg-card);
	}

	.row-num {
		color: var(--text-dim);
		font-size: 12px;
		min-width: 28px;
		padding-top: 3px;
		flex-shrink: 0;
		text-align: right;
		font-variant-numeric: tabular-nums;
	}

	.row-content {
		flex: 1;
		min-width: 0;
	}

	.row-zh {
		font-size: 16px;
		line-height: 1.7;
		margin-bottom: 2px;
	}

	.row-en {
		font-size: 15px;
		line-height: 1.6;
		color: var(--text-dim);
	}

	:global(.vocab-hl) {
		background: rgba(99, 102, 241, 0.18);
		color: var(--accent-hover);
		border-radius: 3px;
		padding: 0 2px;
	}

	/* Section 3: Vocabulary Grid */
	.vocab-grid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
		gap: 8px;
	}

	.vocab-card {
		display: flex;
		justify-content: space-between;
		align-items: center;
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
	}

	.vocab-zh {
		font-size: 14px;
		color: var(--text-dim);
	}

	.empty {
		color: var(--text-dim);
		font-size: 14px;
		padding: 16px 0;
	}

	@media (max-width: 640px) {
		.study-header {
			margin-bottom: 24px;
		}

		.study-header-left {
			flex-direction: column;
			align-items: flex-start;
			gap: 8px;
		}

		.study-header h1 {
			font-size: 17px;
		}

		.section {
			margin-bottom: 32px;
		}

		.fulltext-en {
			font-size: 15px;
			line-height: 1.8;
		}

		.fulltext-zh {
			font-size: 14px;
			line-height: 1.8;
		}

		.bilingual-row {
			padding: 10px 8px;
			gap: 10px;
		}

		.row-num {
			min-width: 22px;
			font-size: 11px;
		}

		.row-en {
			font-size: 14px;
		}

		.row-zh {
			font-size: 13px;
		}

		.vocab-grid {
			grid-template-columns: 1fr;
		}
	}
</style>
