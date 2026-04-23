<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import {
		getSpeaking,
		analyzeSpeakingDiscourse,
		type SpeakingSessionDetail,
		type DiscourseResult,
	} from '$lib/api';
	import { t } from '$lib/i18n';

	let session = $state<SpeakingSessionDetail | null>(null);
	let loading = $state(true);
	let error = $state('');
	let analyzing = $state(false);
	let discourse = $state<DiscourseResult | null>(null);
	let copied = $state(false);

	onMount(async () => {
		const id = $page.params.id;
		try {
			session = await getSpeaking(id);
			if (session.status !== 'ready') {
				error = 'Session not ready';
				loading = false;
				return;
			}
			discourse = session.discourse ?? null;
			// Auto-trigger analysis if not yet done
			if (!discourse?.topic) {
				await runAnalysis();
			}
		} catch {
			error = 'Session not found';
		} finally {
			loading = false;
		}
	});

	async function runAnalysis() {
		if (!session || analyzing) return;
		analyzing = true;
		try {
			const res = await analyzeSpeakingDiscourse(session.id);
			discourse = res.discourse;
		} catch (e: unknown) {
			const err = e as Error & { status?: number };
			if (err.status === 429) {
				error = t('quotaExceeded');
			} else {
				error = err.message || 'Analysis failed';
			}
		} finally {
			analyzing = false;
		}
	}

	function copyScript() {
		if (!discourse?.rewritten_segments?.length) return;
		const text = discourse.rewritten_segments
			.map((seg) => `${seg.en || seg.text || ''}\n${seg.zh || ''}`)
			.join('\n\n');
		navigator.clipboard.writeText(text).then(() => {
			copied = true;
			setTimeout(() => (copied = false), 2000);
		});
	}

	function scoreColor(score: number): string {
		if (score >= 8) return 'score-high';
		if (score >= 5) return 'score-mid';
		return 'score-low';
	}

	function categoryLabel(category: string): string {
		const map: Record<string, string> = {
			hook: 'Hook',
			opening: 'Hook',
			structure: 'Structure',
			transition: 'Transition',
			closing: 'Closing',
			vocabulary: 'Vocabulary',
			delivery: 'Delivery',
		};
		return map[category] || category;
	}
</script>

<svelte:head>
	<title>{t('discourseAnalysis')} - {session?.title || t('speakingCoach')} - ReelScript</title>
</svelte:head>

<div class="discourse-page">
	<nav class="page-nav">
		<button class="btn btn-ghost" onclick={() => goto(`/speaking/${$page.params.id}`)}>
			<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M19 12H5"/><path d="M12 19l-7-7 7-7"/></svg>
			{t('back')}
		</button>
		<h1>{t('discourseAnalysis')}</h1>
	</nav>

	{#if loading || analyzing}
		<div class="center-state">
			<svg class="spinner" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
				<path d="M12 2a10 10 0 0 1 10 10"/>
			</svg>
			<p>{analyzing ? t('analyzingDiscourse') : t('loading')}</p>
			{#if analyzing}
				<p class="hint">{t('discourseQuotaCost')}</p>
			{/if}
		</div>
	{:else if error}
		<div class="center-state">
			<p class="error-text">{error}</p>
			<button class="btn btn-ghost" onclick={() => goto(`/speaking/${$page.params.id}`)}>{t('back')}</button>
		</div>
	{:else if discourse?.topic}
		<div class="discourse-content">
			<!-- Topic -->
			<section class="topic-section">
				<span class="label">{t('topic')}</span>
				<p class="topic-text">{discourse.topic}</p>
			</section>

			<!-- Scores -->
			<section class="scores-section">
				<div class="score-row">
					<div class="score-chip">
						<span class="score-name">{t('clarity')}</span>
						<span class="score-num {scoreColor(discourse.scores.clarity)}">{discourse.scores.clarity}</span>
					</div>
					<div class="score-chip">
						<span class="score-name">{t('organization')}</span>
						<span class="score-num {scoreColor(discourse.scores.organization)}">{discourse.scores.organization}</span>
					</div>
					<div class="score-chip">
						<span class="score-name">{t('persuasiveness')}</span>
						<span class="score-num {scoreColor(discourse.scores.persuasiveness)}">{discourse.scores.persuasiveness}</span>
					</div>
					<div class="score-chip">
						<span class="score-name">{t('engagement')}</span>
						<span class="score-num {scoreColor(discourse.scores.engagement)}">{discourse.scores.engagement}</span>
					</div>
				</div>
			</section>

			<!-- Structure Analysis -->
			<section class="analysis-section">
				<h2>{t('structureAnalysis')}</h2>
				<div class="analysis-card">
					<div class="analysis-row">
						<span class="row-label">{t('currentStructure')}</span>
						<p>{discourse.structure_analysis.current}</p>
					</div>
					{#if discourse.structure_analysis?.problems?.length > 0}
						<div class="analysis-row">
							<span class="row-label">{t('structureProblems')}</span>
							<ul class="problem-list">
								{#each discourse.structure_analysis.problems as problem}
									<li>{problem}</li>
								{/each}
							</ul>
						</div>
					{/if}
					<div class="analysis-row">
						<span class="row-label">{t('structureSuggestion')}</span>
						<p>{discourse.structure_analysis.suggestion}</p>
					</div>
				</div>
			</section>

			<!-- Tips -->
			{#if discourse.tips?.length > 0}
				<section class="tips-section">
					<h2>{t('expressionTips')}</h2>
					<div class="tips-grid">
						{#each discourse.tips as tip}
							<div class="tip-card">
								<span class="tip-badge">{categoryLabel(tip.category)}</span>
								<p class="tip-advice">{tip.tip}</p>
								<p class="tip-example">{tip.example}</p>
							</div>
						{/each}
					</div>
				</section>
			{/if}

			<!-- Rewritten Script -->
			{#if discourse.rewritten_segments?.length > 0}
				<section class="script-section">
					<div class="script-header">
						<h2>{t('rewrittenScript')}</h2>
						<button class="btn btn-ghost btn-sm" onclick={copyScript}>
							{copied ? t('copied') : t('copyScript')}
						</button>
					</div>
					<div class="script-body">
						{#each discourse.rewritten_segments as seg}
							<div class="script-line">
								<span class="line-num">{seg.index}</span>
								<div class="line-bilingual">
									<p class="line-en">{seg.en || seg.text || ''}</p>
									{#if seg.zh}
										<p class="line-zh">{seg.zh}</p>
									{/if}
									{#if seg.note}
										<p class="line-note">{seg.note}</p>
									{/if}
								</div>
							</div>
						{/each}
					</div>
				</section>
			{/if}
		</div>
	{:else}
		<div class="center-state">
			<p>No analysis result</p>
			<button class="btn btn-primary" onclick={runAnalysis}>{t('discourseAnalysis')}</button>
		</div>
	{/if}
</div>

<style>
	.discourse-page {
		max-width: 720px;
		margin: 0 auto;
		padding: 0 16px;
	}

	.page-nav {
		display: flex;
		align-items: center;
		gap: 16px;
		margin-bottom: 32px;
	}

	.page-nav h1 {
		font-size: 20px;
		font-weight: 700;
	}

	.center-state {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		gap: 12px;
		padding: 80px 0;
		text-align: center;
		color: var(--text-dim);
	}

	.hint {
		font-size: 13px;
		color: var(--text-dim);
	}

	.error-text {
		color: var(--danger);
	}

	.spinner {
		animation: spin 0.8s linear infinite;
	}

	@keyframes spin {
		to { transform: rotate(360deg); }
	}

	/* Content */
	.discourse-content {
		display: flex;
		flex-direction: column;
		gap: 24px;
		padding-bottom: 64px;
	}

	/* Topic */
	.topic-section {
		padding: 20px;
		background: var(--bg-card);
		border-radius: var(--radius);
		border: 1px solid var(--border);
	}

	.label {
		display: block;
		font-size: 11px;
		font-weight: 600;
		text-transform: uppercase;
		letter-spacing: 0.5px;
		color: var(--accent);
		margin-bottom: 8px;
	}

	.topic-text {
		font-size: 18px;
		font-weight: 600;
		line-height: 1.5;
		color: var(--text);
	}

	/* Scores */
	.scores-section {
		padding: 16px 20px;
		background: var(--bg-card);
		border-radius: var(--radius);
		border: 1px solid var(--border);
	}

	.score-row {
		display: grid;
		grid-template-columns: repeat(4, 1fr);
		gap: 12px;
	}

	.score-chip {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 4px;
	}

	.score-name {
		font-size: 11px;
		font-weight: 500;
		color: var(--text-dim);
		text-transform: uppercase;
		letter-spacing: 0.5px;
	}

	.score-num {
		font-size: 28px;
		font-weight: 700;
		font-variant-numeric: tabular-nums;
	}

	.score-high { color: var(--success); }
	.score-mid { color: var(--accent); }
	.score-low { color: var(--danger); }

	/* Analysis */
	.analysis-section h2,
	.tips-section h2,
	.script-section h2 {
		font-size: 16px;
		font-weight: 700;
		margin-bottom: 12px;
	}

	.analysis-card {
		padding: 20px;
		background: var(--bg-card);
		border-radius: var(--radius);
		border: 1px solid var(--border);
		display: flex;
		flex-direction: column;
		gap: 16px;
	}

	.analysis-row {
		display: flex;
		flex-direction: column;
		gap: 4px;
	}

	.row-label {
		font-size: 12px;
		font-weight: 600;
		color: var(--text-dim);
	}

	.analysis-row p {
		font-size: 15px;
		line-height: 1.6;
		color: var(--text);
	}

	.problem-list {
		list-style: none;
		display: flex;
		flex-direction: column;
		gap: 6px;
	}

	.problem-list li {
		font-size: 15px;
		line-height: 1.5;
		color: var(--text);
		padding-left: 18px;
		position: relative;
	}

	.problem-list li::before {
		content: '';
		position: absolute;
		left: 0;
		top: 9px;
		width: 6px;
		height: 6px;
		border-radius: 50%;
		background: var(--danger);
	}

	/* Tips */
	.tips-grid {
		display: flex;
		flex-direction: column;
		gap: 12px;
	}

	.tip-card {
		padding: 16px;
		background: var(--bg-card);
		border-radius: var(--radius);
		border: 1px solid var(--border);
	}

	.tip-badge {
		display: inline-block;
		font-size: 11px;
		font-weight: 600;
		padding: 2px 10px;
		border-radius: 10px;
		background: color-mix(in srgb, var(--accent) 15%, transparent);
		color: var(--accent);
		margin-bottom: 8px;
	}

	.tip-advice {
		font-size: 15px;
		line-height: 1.6;
		color: var(--text);
		margin-bottom: 6px;
	}

	.tip-example {
		font-size: 14px;
		line-height: 1.5;
		color: var(--text-dim);
		font-style: italic;
	}

	/* Rewritten Script */
	.script-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
	}

	.script-header h2 {
		margin-bottom: 0;
	}

	.btn-sm {
		padding: 4px 10px;
		font-size: 12px;
	}

	.script-body {
		margin-top: 12px;
		display: flex;
		flex-direction: column;
		gap: 4px;
	}

	.script-line {
		display: flex;
		gap: 12px;
		padding: 12px 16px;
		background: var(--bg-card);
		border-radius: var(--radius-sm);
		border-left: 3px solid var(--accent);
	}

	.line-num {
		font-size: 13px;
		font-weight: 600;
		color: var(--text-dim);
		min-width: 20px;
		flex-shrink: 0;
		padding-top: 2px;
	}

	.line-bilingual {
		display: flex;
		flex-direction: column;
		gap: 4px;
		min-width: 0;
	}

	.line-en {
		font-size: 16px;
		line-height: 1.7;
		color: var(--text);
	}

	.line-zh {
		font-size: 14px;
		line-height: 1.5;
		color: var(--text-dim);
	}

	.line-note {
		font-size: 13px;
		line-height: 1.5;
		color: var(--accent);
		margin-top: 4px;
		padding: 6px 10px;
		background: color-mix(in srgb, var(--accent) 8%, transparent);
		border-radius: 6px;
	}

	.btn-primary {
		background: var(--accent);
		color: white;
	}

	.btn-primary:hover {
		background: var(--accent-hover);
	}

	/* Mobile */
	@media (max-width: 640px) {
		.score-row {
			grid-template-columns: repeat(2, 1fr);
		}

		.topic-text {
			font-size: 16px;
		}

		.line-en {
			font-size: 15px;
		}
	}
</style>
