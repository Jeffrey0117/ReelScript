<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import {
		getVideo,
		translateVideo,
		analyzeVocabulary,
		appreciateVideo,
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

	let videoId = '';
	page.subscribe((p) => {
		videoId = p.params.id ?? '';
	});

	let segments = $derived(video?.transcript?.segments ?? []);

	let fullEnglish = $derived(
		segments.map((s) => s.text).join(' ')
	);

	let fullChinese = $derived(
		segments.map((s) => s.translation || '').join('')
	);

	let appreciation = $derived(video?.transcript?.appreciation ?? null);

	// Merge into proper sentences by splitting full text independently
	interface MergedSentence {
		en: string;
		zh: string;
		vocabulary: VocabularyItem[];
	}

	let sentences = $derived.by(() => {
		const fullEn = segments.map((s) => s.text).join(' ');
		const fullZh = segments.map((s) => s.translation || '').join('');

		// Split English into sentences by .!?
		const enSentences = fullEn.match(/[^.!?]+[.!?]+/g)?.map((s) => s.trim()) || [];
		if (!enSentences.length && fullEn.trim()) enSentences.push(fullEn.trim());

		// Split Chinese into sentences by 。！？
		let zhSentences: string[] = [];
		if (/[。！？]/.test(fullZh)) {
			zhSentences = fullZh.split(/(?<=[。！？])/).map((s) => s.trim()).filter(Boolean);
		} else if (fullZh.trim()) {
			// No Chinese sentence punctuation — split by ，and group to match English count
			const clauses = fullZh.split(/[，,]/).filter((s) => s.trim());
			if (clauses.length <= enSentences.length) {
				zhSentences = clauses;
			} else {
				const perGroup = Math.ceil(clauses.length / enSentences.length);
				for (let i = 0; i < clauses.length; i += perGroup) {
					zhSentences.push(clauses.slice(i, i + perGroup).join('，'));
				}
			}
		}

		// Collect all vocabulary for text matching
		const allVocab = segments.flatMap((s) => s.vocabulary ?? []);

		return enSentences.map((en, i) => {
			const matchedVocab = allVocab.filter((v) => {
				const escaped = v.word.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
				return new RegExp(`\\b${escaped}\\b`, 'i').test(en);
			});
			return {
				en,
				zh: zhSentences[i] || '',
				vocabulary: matchedVocab,
			};
		});
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
						<div class="bilingual-row">
							<span class="row-num">{i + 1}</span>
							<div class="row-content">
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

		.vocab-grid {
			grid-template-columns: 1fr;
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
