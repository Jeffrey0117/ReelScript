<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import {
		getSpeaking,
		deleteSpeaking,
		connectWS,
		speakingFileUrl,
		type SpeakingSessionDetail,
		type SpeakingSegment,
	} from '$lib/api';
	import { t } from '$lib/i18n';

	let session = $state<SpeakingSessionDetail | null>(null);
	let loading = $state(true);
	let error = $state('');

	// Player
	let mediaEl = $state<HTMLVideoElement | HTMLAudioElement | null>(null);
	let currentTime = $state(0);
	let activeSegmentIndex = $state(-1);

	// Playback modes: 'off' | 'loop' | 'repeat-one'
	let playbackMode = $state<'off' | 'loop' | 'repeat-one'>('off');
	let repeatSegmentIndex = $state(-1);

	// Display mode: 'original' | 'corrected' | 'both'
	let displayMode = $state<'original' | 'corrected' | 'both'>('both');

	// Issues expand state per segment
	let expandedIssues = $state<Set<number>>(new Set());

	// Determine media type from filename
	let isVideo = $derived(
		session?.filename ? /\.(mp4|webm)$/i.test(session.filename) : false
	);

	// Merge segments with coaching sentences by index
	interface MergedSegment {
		index: number;
		start: number;
		end: number;
		text: string;
		corrected: string;
		issues: { type: string; highlight: string; explanation: string }[];
		native_alt: string;
		score: number;
	}

	let mergedSegments = $derived.by(() => {
		if (!session) return [];
		const segments = session.segments ?? [];
		const sentences = session.coaching?.sentences ?? [];
		const sentenceMap = new Map(sentences.map((s) => [s.index, s]));

		return segments.map((seg): MergedSegment => {
			const coached = sentenceMap.get(seg.index);
			return {
				index: seg.index,
				start: seg.start,
				end: seg.end,
				text: seg.text,
				corrected: coached?.corrected ?? seg.text,
				issues: coached?.issues ?? [],
				native_alt: coached?.native_alt ?? '',
				score: coached?.score ?? 0,
			};
		});
	});

	let overall = $derived(session?.coaching?.overall ?? null);

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

	function handleTimeUpdate() {
		if (!mediaEl) return;
		currentTime = mediaEl.currentTime;

		const idx = mergedSegments.findIndex(
			(s) => currentTime >= s.start && currentTime < s.end
		);
		activeSegmentIndex = idx;

		// Single sentence repeat
		if (playbackMode === 'repeat-one' && repeatSegmentIndex >= 0) {
			const seg = mergedSegments[repeatSegmentIndex];
			if (seg && currentTime >= seg.end) {
				mediaEl.currentTime = seg.start;
			}
		}
	}

	function handleMediaEnded() {
		if (playbackMode === 'loop' && mediaEl) {
			mediaEl.currentTime = 0;
			mediaEl.play();
		}
	}

	function cyclePlaybackMode() {
		if (playbackMode === 'off') {
			playbackMode = 'loop';
		} else if (playbackMode === 'loop') {
			playbackMode = 'repeat-one';
			repeatSegmentIndex = activeSegmentIndex >= 0 ? activeSegmentIndex : 0;
		} else {
			playbackMode = 'off';
			repeatSegmentIndex = -1;
		}
	}

	function seekTo(seg: MergedSegment) {
		if (!mediaEl) return;
		mediaEl.currentTime = seg.start;
		mediaEl.play().catch(() => {});
	}

	function lockSegment(index: number) {
		playbackMode = 'repeat-one';
		repeatSegmentIndex = index;
		const seg = mergedSegments[index];
		if (seg && mediaEl) {
			mediaEl.currentTime = seg.start;
			mediaEl.play().catch(() => {});
		}
	}

	function formatTime(seconds: number): string {
		const m = Math.floor(seconds / 60);
		const s = Math.floor(seconds % 60);
		return `${m}:${s.toString().padStart(2, '0')}`;
	}

	function cycleDisplayMode() {
		if (displayMode === 'both') {
			displayMode = 'original';
		} else if (displayMode === 'original') {
			displayMode = 'corrected';
		} else {
			displayMode = 'both';
		}
	}

	function toggleIssues(index: number) {
		const next = new Set(expandedIssues);
		if (next.has(index)) {
			next.delete(index);
		} else {
			next.add(index);
		}
		expandedIssues = next;
	}

	function scoreColor(score: number): string {
		if (score >= 8) return 'score-high';
		if (score >= 5) return 'score-mid';
		return 'score-low';
	}

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

	async function handleDelete() {
		if (!session) return;
		if (!confirm(t('confirmDelete'))) return;
		await deleteSpeaking(session.id);
		goto('/speaking');
	}
</script>

<svelte:head>
	<title>{session?.title || t('speakingCoach')} - ReelScript</title>
</svelte:head>

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
{:else if session}
	<div class="watch-layout">
		<!-- Left: Player Panel -->
		<div class="player-panel">
			{#if session.filename}
				{#if isVideo}
					<!-- svelte-ignore a11y_media_has_caption -->
					<video
						bind:this={mediaEl}
						ontimeupdate={handleTimeUpdate}
						onended={handleMediaEnded}
						controls
						playsinline
						preload="auto"
						class="media-player video-player"
					>
						<source src={speakingFileUrl(session.filename)} />
					</video>
				{:else}
					<div class="audio-player-wrapper">
						<div class="audio-icon">
							<svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
								<path d="M9 18V5l12-2v13"/>
								<circle cx="6" cy="18" r="3"/>
								<circle cx="18" cy="16" r="3"/>
							</svg>
						</div>
						<!-- svelte-ignore a11y_media_has_caption -->
						<audio
							bind:this={mediaEl}
							ontimeupdate={handleTimeUpdate}
							onended={handleMediaEnded}
							controls
							preload="auto"
							class="media-player audio-player"
						>
							<source src={speakingFileUrl(session.filename)} />
						</audio>
					</div>
				{/if}
			{:else}
				<div class="media-placeholder">{t('videoNotAvailable')}</div>
			{/if}

			<div class="media-info">
				<h1>{session.title || t('speakingCoach')}</h1>
				{#if session.created_at}
					<span class="meta-date">{new Date(session.created_at).toLocaleDateString()}</span>
				{/if}
			</div>

			<div class="actions">
				<button
					class="btn {playbackMode !== 'off' ? 'btn-active' : 'btn-ghost'}"
					onclick={cyclePlaybackMode}
				>
					{#if playbackMode === 'off'}
						{t('loopOff')}
					{:else if playbackMode === 'loop'}
						{t('loopAll')}
					{:else}
						{t('loopOne')}
					{/if}
				</button>
				<button class="btn btn-danger" onclick={handleDelete}>
					{t('delete')}
				</button>
			</div>

			<!-- Coaching Summary -->
			{#if overall}
				<section class="coaching-summary">
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
		</div>

		<!-- Right: Transcript Panel -->
		<div class="transcript-panel">
			<div class="transcript-header">
				<h2>{t('transcript')}</h2>
				<span class="segment-count">{mergedSegments.length} {t('segments')}</span>
				<div class="transcript-actions">
					<button class="display-toggle" onclick={cycleDisplayMode}>
						{#if displayMode === 'original'}
							{t('displayOriginal')}
						{:else if displayMode === 'corrected'}
							{t('displayCorrected')}
						{:else}
							{t('displayBoth')}
						{/if}
					</button>
				</div>
			</div>

			<div class="segments">
				{#each mergedSegments as seg, i (seg.index)}
					<div
						class="segment-row"
						class:active={i === activeSegmentIndex}
						class:repeating={playbackMode === 'repeat-one' && i === repeatSegmentIndex}
					>
						<button
							class="segment"
							onclick={() => seekTo(seg)}
						>
							<span class="segment-time">{formatTime(seg.start)}</span>
							<span class="segment-text-wrapper">
								{#if displayMode === 'original' || displayMode === 'both'}
									<span class="segment-text">{seg.text}</span>
								{/if}
								{#if (displayMode === 'corrected' || displayMode === 'both') && seg.corrected !== seg.text}
									<span class="segment-corrected">{seg.corrected}</span>
								{:else if displayMode === 'corrected'}
									<span class="segment-text">{seg.corrected}</span>
								{/if}
							</span>
						</button>

						<div class="segment-controls">
							{#if seg.issues.length > 0}
								<button
									class="issue-badge-btn"
									onclick={() => toggleIssues(seg.index)}
									title={t('issueCount').replace('{n}', String(seg.issues.length))}
								>
									{seg.issues.length}
								</button>
							{/if}
							<button
								class="segment-lock"
								class:locked={playbackMode === 'repeat-one' && i === repeatSegmentIndex}
								onclick={() => lockSegment(i)}
								title={t('repeatSentence')}
							>
								{#if playbackMode === 'repeat-one' && i === repeatSegmentIndex}
									<svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><rect x="6" y="6" width="12" height="12" rx="2"/></svg>
								{:else}
									<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17 2l4 4-4 4"/><path d="M3 11v-1a4 4 0 0 1 4-4h14"/><path d="M7 22l-4-4 4-4"/><path d="M21 13v1a4 4 0 0 1-4 4H3"/></svg>
								{/if}
							</button>
						</div>
					</div>

					<!-- Expanded issues for this segment -->
					{#if expandedIssues.has(seg.index) && seg.issues.length > 0}
						<div class="segment-issues">
							{#each seg.issues as issue}
								<div class="issue">
									<span class="issue-type-badge {issueColor(issue.type)}">{issueLabel(issue.type)}</span>
									<span class="issue-highlight">{issue.highlight}</span>
									<span class="issue-explain">{issue.explanation}</span>
								</div>
							{/each}
							{#if seg.native_alt && seg.native_alt !== seg.corrected}
								<div class="native-alt-inline">
									<span class="native-alt-label">{t('nativeAlt')}</span>
									<span class="native-alt-text">{seg.native_alt}</span>
								</div>
							{/if}
						</div>
					{/if}
				{/each}
			</div>
		</div>
	</div>
{/if}

<style>
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

	/* Watch-style Layout */
	.watch-layout {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 32px;
		align-items: start;
	}

	/* Player Panel */
	.player-panel {
		position: sticky;
		top: 72px;
	}

	.media-player {
		width: 100%;
		border-radius: var(--radius);
		background: #000;
	}

	.video-player {
		aspect-ratio: 16 / 9;
		max-height: 50vh;
		object-fit: contain;
	}

	.audio-player-wrapper {
		background: var(--bg-card);
		border-radius: var(--radius);
		padding: 32px;
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 24px;
	}

	.audio-icon {
		color: var(--text-dim);
		opacity: 0.5;
	}

	.audio-player {
		width: 100%;
		border-radius: var(--radius-sm);
	}

	.media-placeholder {
		width: 100%;
		aspect-ratio: 16 / 9;
		background: var(--bg-card);
		border-radius: var(--radius);
		display: flex;
		align-items: center;
		justify-content: center;
		color: var(--text-dim);
	}

	.media-info {
		margin-top: 16px;
	}

	.media-info h1 {
		font-size: 20px;
		font-weight: 700;
		margin-bottom: 4px;
	}

	.meta-date {
		font-size: 13px;
		color: var(--text-dim);
	}

	.actions {
		display: flex;
		gap: 8px;
		margin-top: 16px;
		flex-wrap: wrap;
	}

	.btn-active {
		background: var(--accent);
		color: white;
	}

	.btn-active:hover {
		background: var(--accent-hover);
	}

	/* Coaching Summary */
	.coaching-summary {
		margin-top: 24px;
		padding: 20px;
		background: var(--bg-card);
		border-radius: var(--radius);
		border: 1px solid var(--border);
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

	/* Transcript Panel */
	.transcript-panel {
		min-height: 60vh;
	}

	.transcript-header {
		display: flex;
		align-items: baseline;
		gap: 12px;
		margin-bottom: 16px;
	}

	.transcript-header h2 {
		font-size: 18px;
		font-weight: 600;
	}

	.segment-count {
		color: var(--text-dim);
		font-size: 13px;
	}

	.transcript-actions {
		margin-left: auto;
	}

	.display-toggle {
		padding: 4px 12px;
		border-radius: var(--radius-sm);
		font-size: 13px;
		font-weight: 600;
		background: var(--accent);
		color: white;
		transition: background 0.15s;
	}

	.display-toggle:hover {
		background: var(--accent-hover);
	}

	/* Segments */
	.segments {
		display: flex;
		flex-direction: column;
		gap: 2px;
	}

	.segment-row {
		display: flex;
		align-items: center;
		border-radius: var(--radius-sm);
		transition: background 0.15s;
	}

	.segment-row:hover {
		background: var(--bg-hover);
	}

	.segment-row.active {
		background: rgba(99, 102, 241, 0.12);
	}

	.segment-row.active .segment-text {
		color: var(--accent-hover);
	}

	.segment-row.repeating {
		background: rgba(99, 102, 241, 0.18);
		outline: 1px solid var(--accent);
	}

	.segment {
		display: flex;
		gap: 12px;
		padding: 10px 12px;
		text-align: left;
		width: 100%;
		flex: 1;
		min-width: 0;
	}

	.segment-time {
		color: var(--text-dim);
		font-size: 12px;
		font-variant-numeric: tabular-nums;
		min-width: 40px;
		padding-top: 2px;
		flex-shrink: 0;
	}

	.segment-text-wrapper {
		display: flex;
		flex-direction: column;
		gap: 2px;
		min-width: 0;
	}

	.segment-text {
		font-size: 15px;
		line-height: 1.6;
	}

	.segment-corrected {
		font-size: 14px;
		line-height: 1.5;
		color: var(--success);
		font-weight: 500;
	}

	.segment-row.active .segment-corrected {
		color: var(--success);
	}

	.segment-controls {
		display: flex;
		align-items: center;
		gap: 4px;
		flex-shrink: 0;
		margin-right: 8px;
	}

	.issue-badge-btn {
		width: 22px;
		height: 22px;
		display: flex;
		align-items: center;
		justify-content: center;
		border-radius: 50%;
		font-size: 11px;
		font-weight: 700;
		background: color-mix(in srgb, var(--danger) 15%, transparent);
		color: var(--danger);
		cursor: pointer;
		transition: background 0.15s;
	}

	.issue-badge-btn:hover {
		background: color-mix(in srgb, var(--danger) 25%, transparent);
	}

	.segment-lock {
		flex-shrink: 0;
		width: 32px;
		height: 32px;
		display: flex;
		align-items: center;
		justify-content: center;
		border-radius: var(--radius-sm);
		font-size: 14px;
		color: var(--text-dim);
		opacity: 0;
		transition: opacity 0.15s, color 0.15s, background 0.15s;
	}

	.segment-row:hover .segment-lock {
		opacity: 1;
	}

	.segment-lock:hover {
		background: var(--bg-hover);
		color: var(--accent);
	}

	.segment-lock.locked {
		opacity: 1;
		color: var(--accent);
		background: rgba(99, 102, 241, 0.2);
	}

	/* Segment Issues Expanded */
	.segment-issues {
		display: flex;
		flex-direction: column;
		gap: 8px;
		padding: 12px 16px 12px 64px;
		background: var(--bg);
		border-radius: var(--radius-sm);
		margin-bottom: 4px;
	}

	.issue {
		display: flex;
		align-items: baseline;
		gap: 8px;
		font-size: 13px;
		line-height: 1.5;
	}

	.issue-type-badge {
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

	.native-alt-inline {
		display: flex;
		align-items: baseline;
		gap: 8px;
		padding-top: 8px;
		border-top: 1px solid var(--border);
		margin-top: 4px;
	}

	.native-alt-label {
		font-size: 11px;
		font-weight: 600;
		text-transform: uppercase;
		letter-spacing: 0.5px;
		color: var(--accent);
		flex-shrink: 0;
	}

	.native-alt-text {
		font-size: 13px;
		color: var(--text-dim);
		font-style: italic;
		line-height: 1.5;
	}

	/* Mobile */
	@media (max-width: 900px) {
		.watch-layout {
			grid-template-columns: 1fr;
		}

		.player-panel {
			position: static;
		}
	}

	@media (max-width: 640px) {
		.watch-layout {
			gap: 20px;
		}

		.video-player {
			max-height: 40vh;
		}

		.media-info h1 {
			font-size: 17px;
		}

		.actions {
			gap: 6px;
		}

		.score-grid {
			grid-template-columns: repeat(2, 1fr);
		}

		.feedback-cols {
			grid-template-columns: 1fr;
		}

		.transcript-header {
			flex-wrap: wrap;
			gap: 8px;
		}

		.transcript-header h2 {
			font-size: 16px;
		}

		.segment {
			padding: 8px 8px;
			gap: 8px;
		}

		.segment-text {
			font-size: 14px;
		}

		.segment-corrected {
			font-size: 13px;
		}

		.segment-lock {
			opacity: 1;
			width: 28px;
			height: 28px;
		}

		.segment-issues {
			padding-left: 16px;
		}

		.audio-player-wrapper {
			padding: 20px;
		}
	}
</style>
