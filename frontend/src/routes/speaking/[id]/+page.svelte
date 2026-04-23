<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import {
		getSpeaking,
		connectWS,
		type SpeakingSessionDetail,
		type CoachingSentence,
	} from '$lib/api';
	import { t } from '$lib/i18n';

	let session = $state<SpeakingSessionDetail | null>(null);
	let loading = $state(true);
	let error = $state('');
	let tab = $state<'results' | 'practice'>('results');

	// Practice mode state
	let practiceIndex = $state(0);

	let sentences = $derived(session?.coaching?.sentences ?? []);
	let overall = $derived(session?.coaching?.overall ?? null);
	let currentPractice = $derived(sentences[practiceIndex] ?? null);

	onMount(async () => {
		const id = $page.params.id;
		try {
			session = await getSpeaking(id);
		} catch {
			error = 'Session not found';
		} finally {
			loading = false;
		}

		connectWS((msg: Record<string, unknown>) => {
			const type = msg.type as string;
			const data = msg.data as Record<string, unknown>;
			if (data?.session_id !== id) return;

			if (type === 'speaking_completed') {
				getSpeaking(id).then((s) => (session = s));
			}
			if (type === 'speaking_analyze_started' && session) {
				session = { ...session, status: 'analyzing' };
			}
			if (type === 'speaking_error' && session) {
				session = { ...session, status: 'failed', error_message: (data.error as string) || 'Failed' };
			}
		});
	});

	function issueColor(type: string): string {
		const map: Record<string, string> = {
			grammar: 'issue-grammar',
			word_choice: 'issue-word-choice',
			naturalness: 'issue-naturalness',
			pronunciation_hint: 'issue-pronunciation',
		};
		return map[type] || 'issue-grammar';
	}

	function issueLabel(type: string): string {
		const map: Record<string, () => string> = {
			grammar: () => t('issueGrammar'),
			word_choice: () => t('issueWordChoice'),
			naturalness: () => t('issueNaturalness'),
			pronunciation_hint: () => t('issuePronunciation'),
		};
		return (map[type] ?? (() => type))();
	}

	function scoreColor(score: number): string {
		if (score >= 8) return 'score-high';
		if (score >= 5) return 'score-mid';
		return 'score-low';
	}

	function prevPractice() {
		if (practiceIndex > 0) practiceIndex--;
	}

	function nextPractice() {
		if (practiceIndex < sentences.length - 1) practiceIndex++;
	}
</script>

<svelte:head>
	<title>{session?.title || t('speakingCoach')} - ReelScript</title>
</svelte:head>

<div class="page-header">
	<button class="btn btn-ghost btn-sm" onclick={() => goto('/speaking')}>
		<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
			<polyline points="15 18 9 12 15 6"/>
		</svg>
		{t('back')}
	</button>
	<h1>{session?.title || t('speakingCoach')}</h1>
</div>

{#if loading}
	<div class="loading-state">
		<svg class="spinner" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
			<path d="M12 2a10 10 0 0 1 10 10"/>
		</svg>
		<span>{t('loading')}</span>
	</div>
{:else if error}
	<div class="error-state">
		<p>{error}</p>
	</div>
{:else if session && session.status !== 'ready'}
	<div class="processing-state">
		<svg class="spinner" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
			<path d="M12 2a10 10 0 0 1 10 10"/>
		</svg>
		<h2>
			{#if session.status === 'transcribing'}
				{t('statusTranscribing')}
			{:else if session.status === 'analyzing'}
				{t('statusAnalyzing')}
			{:else}
				{t('processing')}
			{/if}
		</h2>
		<p class="processing-hint">{t('preparing')}</p>
	</div>
{:else if session && session.coaching}
	<!-- Tabs -->
	<div class="tabs">
		<button
			class="tab"
			class:active={tab === 'results'}
			onclick={() => (tab = 'results')}
		>
			{t('results')}
		</button>
		<button
			class="tab"
			class:active={tab === 'practice'}
			onclick={() => (tab = 'practice')}
		>
			{t('practiceMode')}
		</button>
	</div>

	{#if tab === 'results'}
		<!-- Overall Scores -->
		{#if overall}
			<section class="overall card">
				<div class="score-grid">
					<div class="score-item">
						<span class="score-label">{t('fluency')}</span>
						<span class="score-value {scoreColor(overall.fluency)}">{overall.fluency}</span>
					</div>
					<div class="score-item">
						<span class="score-label">{t('grammar')}</span>
						<span class="score-value {scoreColor(overall.grammar)}">{overall.grammar}</span>
					</div>
					<div class="score-item">
						<span class="score-label">{t('vocabulary')}</span>
						<span class="score-value {scoreColor(overall.vocabulary)}">{overall.vocabulary}</span>
					</div>
					<div class="score-item">
						<span class="score-label">{t('naturalness')}</span>
						<span class="score-value {scoreColor(overall.naturalness)}">{overall.naturalness}</span>
					</div>
				</div>

				{#if overall.summary}
					<p class="summary-text">{overall.summary}</p>
				{/if}

				<div class="feedback-cols">
					{#if overall.strengths && overall.strengths.length > 0}
						<div class="feedback-col">
							<h4 class="feedback-title strengths-title">{t('strengths')}</h4>
							<ul class="feedback-list">
								{#each overall.strengths as item}
									<li>{item}</li>
								{/each}
							</ul>
						</div>
					{/if}
					{#if overall.improvements && overall.improvements.length > 0}
						<div class="feedback-col">
							<h4 class="feedback-title improvements-title">{t('improvements')}</h4>
							<ul class="feedback-list">
								{#each overall.improvements as item}
									<li>{item}</li>
								{/each}
							</ul>
						</div>
					{/if}
				</div>
			</section>
		{/if}

		<!-- Sentence-by-sentence -->
		<section class="sentences">
			{#each sentences as sentence (sentence.index)}
				<div class="sentence-card card">
					<div class="sentence-header">
						<span class="sentence-num">#{sentence.index}</span>
						<span class="sentence-score {scoreColor(sentence.score)}">{sentence.score}/10</span>
					</div>

					<div class="sentence-row">
						<span class="row-label">{t('original')}</span>
						<p class="sentence-text original-text">{sentence.original}</p>
					</div>

					{#if sentence.corrected !== sentence.original}
						<div class="sentence-row">
							<span class="row-label">{t('corrected')}</span>
							<p class="sentence-text corrected-text">{sentence.corrected}</p>
						</div>
					{/if}

					{#if sentence.issues && sentence.issues.length > 0}
						<div class="issues">
							{#each sentence.issues as issue}
								<div class="issue">
									<span class="issue-badge {issueColor(issue.type)}">{issueLabel(issue.type)}</span>
									<span class="issue-highlight">{issue.highlight}</span>
									<span class="issue-explain">{issue.explanation}</span>
								</div>
							{/each}
						</div>
					{/if}

					{#if sentence.native_alt && sentence.native_alt !== sentence.corrected}
						<details class="native-alt">
							<summary>{t('nativeAlt')}</summary>
							<p>{sentence.native_alt}</p>
						</details>
					{/if}
				</div>
			{/each}
		</section>
	{:else}
		<!-- Practice Mode -->
		<section class="practice">
			{#if currentPractice}
				<div class="practice-card card">
					<div class="practice-header">
						<span class="practice-num">{practiceIndex + 1} / {sentences.length}</span>
						<span class="sentence-score {scoreColor(currentPractice.score)}">{currentPractice.score}/10</span>
					</div>

					{#if currentPractice.corrected !== currentPractice.original}
						<div class="practice-original">
							<span class="row-label">{t('original')}</span>
							<p class="practice-original-text">{currentPractice.original}</p>
						</div>
					{/if}

					<p class="practice-text">{currentPractice.corrected}</p>

					{#if currentPractice.native_alt && currentPractice.native_alt !== currentPractice.corrected}
						<div class="practice-alt">
							<span class="row-label">{t('nativeAlt')}</span>
							<p>{currentPractice.native_alt}</p>
						</div>
					{/if}
				</div>

				<div class="practice-nav">
					<button
						class="btn btn-ghost"
						onclick={prevPractice}
						disabled={practiceIndex === 0}
					>
						<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
							<polyline points="15 18 9 12 15 6"/>
						</svg>
						{t('prevSentence')}
					</button>
					<button
						class="btn btn-primary"
						onclick={nextPractice}
						disabled={practiceIndex >= sentences.length - 1}
					>
						{t('nextSentence')}
						<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
							<polyline points="9 18 15 12 9 6"/>
						</svg>
					</button>
				</div>
			{:else}
				<p class="empty-practice">{t('noSessions')}</p>
			{/if}
		</section>
	{/if}
{/if}

<style>
	.page-header {
		display: flex;
		align-items: center;
		gap: 16px;
		margin-bottom: 24px;
	}

	.page-header h1 {
		font-size: 22px;
		font-weight: 700;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	.loading-state,
	.error-state,
	.processing-state {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		gap: 12px;
		padding: 64px 0;
		text-align: center;
		color: var(--text-dim);
	}

	.processing-state h2 {
		font-size: 18px;
		color: var(--text);
	}

	.processing-hint {
		font-size: 14px;
		color: var(--text-dim);
	}

	.spinner {
		animation: spin 0.8s linear infinite;
	}

	@keyframes spin {
		to { transform: rotate(360deg); }
	}

	/* Tabs */
	.tabs {
		display: flex;
		gap: 0;
		border-bottom: 1px solid var(--border);
		margin-bottom: 24px;
	}

	.tab {
		padding: 12px 24px;
		font-size: 14px;
		font-weight: 600;
		color: var(--text-dim);
		border-bottom: 2px solid transparent;
		transition: color 0.15s, border-color 0.15s;
		cursor: pointer;
		background: none;
	}

	.tab:hover {
		color: var(--text);
	}

	.tab.active {
		color: var(--accent);
		border-bottom-color: var(--accent);
	}

	/* Overall */
	.overall {
		margin-bottom: 24px;
	}

	.score-grid {
		display: grid;
		grid-template-columns: repeat(4, 1fr);
		gap: 16px;
		margin-bottom: 20px;
	}

	.score-item {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 6px;
	}

	.score-label {
		font-size: 12px;
		font-weight: 500;
		color: var(--text-dim);
		text-transform: uppercase;
		letter-spacing: 0.5px;
	}

	.score-value {
		font-size: 28px;
		font-weight: 700;
		font-variant-numeric: tabular-nums;
	}

	.score-high { color: var(--success); }
	.score-mid { color: var(--accent); }
	.score-low { color: var(--danger); }

	.summary-text {
		font-size: 15px;
		line-height: 1.6;
		color: var(--text);
		margin-bottom: 20px;
		padding: 16px;
		background: var(--bg);
		border-radius: var(--radius-sm);
	}

	.feedback-cols {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 16px;
	}

	.feedback-col {
		padding: 16px;
		border-radius: var(--radius-sm);
		background: var(--bg);
	}

	.feedback-title {
		font-size: 13px;
		font-weight: 600;
		margin-bottom: 10px;
	}

	.strengths-title { color: var(--success); }
	.improvements-title { color: var(--accent); }

	.feedback-list {
		list-style: none;
		display: flex;
		flex-direction: column;
		gap: 6px;
	}

	.feedback-list li {
		font-size: 14px;
		line-height: 1.5;
		color: var(--text);
		padding-left: 16px;
		position: relative;
	}

	.feedback-list li::before {
		content: '';
		position: absolute;
		left: 0;
		top: 8px;
		width: 6px;
		height: 6px;
		border-radius: 50%;
		background: var(--text-dim);
	}

	/* Sentences */
	.sentences {
		display: flex;
		flex-direction: column;
		gap: 12px;
	}

	.sentence-card {
		padding: 16px 20px;
	}

	.sentence-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: 12px;
	}

	.sentence-num {
		font-size: 13px;
		font-weight: 600;
		color: var(--text-dim);
	}

	.sentence-score {
		font-size: 13px;
		font-weight: 700;
		padding: 2px 10px;
		border-radius: 20px;
	}

	.sentence-score.score-high { background: color-mix(in srgb, var(--success) 12%, transparent); }
	.sentence-score.score-mid { background: color-mix(in srgb, var(--accent) 12%, transparent); }
	.sentence-score.score-low { background: color-mix(in srgb, var(--danger) 12%, transparent); }

	.sentence-row {
		margin-bottom: 10px;
	}

	.row-label {
		display: block;
		font-size: 11px;
		font-weight: 600;
		text-transform: uppercase;
		letter-spacing: 0.5px;
		color: var(--text-dim);
		margin-bottom: 4px;
	}

	.sentence-text {
		font-size: 15px;
		line-height: 1.6;
	}

	.original-text {
		color: var(--text-dim);
	}

	.corrected-text {
		color: var(--text);
		font-weight: 500;
	}

	/* Issues */
	.issues {
		display: flex;
		flex-direction: column;
		gap: 8px;
		margin: 12px 0;
		padding: 12px;
		background: var(--bg);
		border-radius: var(--radius-sm);
	}

	.issue {
		display: flex;
		align-items: baseline;
		gap: 8px;
		font-size: 13px;
		line-height: 1.5;
	}

	.issue-badge {
		flex-shrink: 0;
		font-size: 11px;
		font-weight: 600;
		padding: 1px 8px;
		border-radius: 10px;
	}

	.issue-grammar {
		background: color-mix(in srgb, var(--danger) 15%, transparent);
		color: var(--danger);
	}

	.issue-word-choice {
		background: rgba(249, 115, 22, 0.15);
		color: #f97316;
	}

	.issue-naturalness {
		background: color-mix(in srgb, var(--accent) 15%, transparent);
		color: var(--accent);
	}

	.issue-pronunciation {
		background: rgba(168, 85, 247, 0.15);
		color: #a855f7;
	}

	.issue-highlight {
		font-weight: 600;
		color: var(--text);
	}

	.issue-explain {
		color: var(--text-dim);
	}

	/* Native alternative */
	.native-alt {
		margin-top: 8px;
		font-size: 14px;
	}

	.native-alt summary {
		color: var(--accent);
		cursor: pointer;
		font-size: 13px;
		font-weight: 500;
	}

	.native-alt p {
		margin-top: 6px;
		color: var(--text-dim);
		font-style: italic;
		line-height: 1.5;
	}

	/* Practice Mode */
	.practice {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 24px;
		padding: 24px 0;
	}

	.practice-card {
		width: 100%;
		max-width: 640px;
		padding: 32px;
		text-align: center;
	}

	.practice-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: 24px;
	}

	.practice-num {
		font-size: 14px;
		font-weight: 600;
		color: var(--text-dim);
	}

	.practice-original {
		margin-bottom: 20px;
		padding-bottom: 16px;
		border-bottom: 1px solid var(--border);
	}

	.practice-original-text {
		font-size: 15px;
		color: var(--text-dim);
		line-height: 1.6;
		text-decoration: line-through;
		text-decoration-color: color-mix(in srgb, var(--danger) 40%, transparent);
	}

	.practice-text {
		font-size: 24px;
		font-weight: 600;
		line-height: 1.5;
		color: var(--text);
		padding: 16px 0;
	}

	.practice-alt {
		margin-top: 16px;
		padding-top: 16px;
		border-top: 1px solid var(--border);
	}

	.practice-alt p {
		font-size: 16px;
		color: var(--text-dim);
		font-style: italic;
		line-height: 1.5;
	}

	.practice-nav {
		display: flex;
		gap: 16px;
		width: 100%;
		max-width: 640px;
		justify-content: space-between;
	}

	.practice-nav .btn {
		flex: 1;
		justify-content: center;
	}

	.empty-practice {
		color: var(--text-dim);
		font-size: 15px;
		padding: 48px 0;
	}

	@media (max-width: 640px) {
		.page-header {
			flex-wrap: wrap;
			gap: 8px;
		}

		.page-header h1 {
			font-size: 18px;
			width: 100%;
		}

		.score-grid {
			grid-template-columns: repeat(2, 1fr);
		}

		.feedback-cols {
			grid-template-columns: 1fr;
		}

		.practice-text {
			font-size: 20px;
		}

		.practice-card {
			padding: 20px;
		}
	}
</style>
