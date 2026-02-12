<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import {
		getVideo,
		deleteVideo,
		translateVideo,
		videoFileUrl,
		listCollections,
		addToCollection,
		type VideoDetail,
		type TranscriptSegment,
		type Collection,
	} from '$lib/api';
	import { goto } from '$app/navigation';

	let video = $state<VideoDetail | null>(null);
	let videoEl = $state<HTMLVideoElement | null>(null);
	let currentTime = $state(0);
	let activeSegmentIndex = $state(-1);
	let showCollectionPicker = $state(false);
	let collections = $state<Collection[]>([]);
	let copySuccess = $state(false);

	// Playback modes: 'off' | 'loop' | 'repeat-one'
	let playbackMode = $state<'off' | 'loop' | 'repeat-one'>('off');
	let repeatSegmentIndex = $state(-1);

	// Display mode: 'en' | 'zh' | 'both'
	let displayMode = $state<'en' | 'zh' | 'both'>('en');
	let translating = $state(false);
	let hasTranslation = $derived(
		video?.transcript?.segments?.some((s) => s.translation) ?? false
	);

	// Derive from page store
	let videoId = '';
	page.subscribe((p) => {
		videoId = p.params.id ?? '';
	});

	onMount(async () => {
		video = await getVideo(videoId);
	});

	function handleTimeUpdate() {
		if (!videoEl) return;
		currentTime = videoEl.currentTime;

		if (!video?.transcript?.segments) return;

		const idx = video.transcript.segments.findIndex(
			(s) => currentTime >= s.start && currentTime < s.end
		);
		activeSegmentIndex = idx;

		// Single sentence repeat: loop within the locked segment
		if (playbackMode === 'repeat-one' && repeatSegmentIndex >= 0) {
			const seg = video.transcript.segments[repeatSegmentIndex];
			if (seg && currentTime >= seg.end) {
				videoEl.currentTime = seg.start;
			}
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

	function lockSegment(index: number) {
		playbackMode = 'repeat-one';
		repeatSegmentIndex = index;
	}

	function handleVideoEnded() {
		if (playbackMode === 'loop' && videoEl) {
			videoEl.currentTime = 0;
			videoEl.play();
		}
	}

	function seekTo(segment: TranscriptSegment) {
		if (!videoEl) return;
		videoEl.currentTime = segment.start;
		videoEl.play();
	}

	function formatTime(seconds: number): string {
		const m = Math.floor(seconds / 60);
		const s = Math.floor(seconds % 60);
		return `${m}:${s.toString().padStart(2, '0')}`;
	}

	async function copyFullText() {
		if (!video?.transcript?.full_text) return;
		await navigator.clipboard.writeText(video.transcript.full_text);
		copySuccess = true;
		setTimeout(() => (copySuccess = false), 2000);
	}

	async function handleDelete() {
		if (!video) return;
		if (!confirm('Delete this video and its transcript?')) return;
		await deleteVideo(video.id);
		goto('/');
	}

	async function openCollectionPicker() {
		collections = await listCollections();
		showCollectionPicker = true;
	}

	async function handleAddToCollection(collectionId: string) {
		if (!video) return;
		try {
			await addToCollection(collectionId, video.id);
			showCollectionPicker = false;
		} catch (e) {
			alert(e instanceof Error ? e.message : 'Failed to add');
		}
	}

	async function handleTranslate() {
		if (!video || translating) return;
		translating = true;
		try {
			const result = await translateVideo(video.id);
			if (result.success && video.transcript) {
				video = {
					...video,
					transcript: {
						...video.transcript,
						segments: result.segments,
					},
				};
				displayMode = 'both';
			}
		} catch (e) {
			alert(e instanceof Error ? e.message : 'Translation failed');
		} finally {
			translating = false;
		}
	}

	function cycleDisplayMode() {
		if (displayMode === 'en') {
			displayMode = 'both';
		} else if (displayMode === 'both') {
			displayMode = 'zh';
		} else {
			displayMode = 'en';
		}
	}
</script>

<svelte:head>
	<title>{video?.title || 'Loading...'} — ReelScript</title>
</svelte:head>

{#if !video}
	<div class="loading">Loading...</div>
{:else}
	<div class="watch-layout">
		<!-- Left: Video Player -->
		<div class="player-panel">
			{#if video.filename}
				<video
					bind:this={videoEl}
					ontimeupdate={handleTimeUpdate}
					onended={handleVideoEnded}
					controls
					class="video-player"
					src={videoFileUrl(video.filename)}
				>
					<track kind="captions" />
				</video>
			{:else}
				<div class="video-placeholder">Video not available</div>
			{/if}

			<div class="video-info">
				<h1>{video.title || 'Untitled'}</h1>
				<div class="video-info-row">
					{#if video.channel}
						<span class="channel">{video.channel}</span>
					{/if}
					<span class="badge {video.source === 'ig' ? 'badge-ig' : 'badge-youtube'}">
						{video.source === 'ig' ? 'Instagram' : 'YouTube'}
					</span>
				</div>
			</div>

			<div class="actions">
				<button
					class="btn {playbackMode !== 'off' ? 'btn-active' : 'btn-ghost'}"
					onclick={cyclePlaybackMode}
					title={playbackMode === 'off' ? 'Loop: Off' : playbackMode === 'loop' ? 'Loop: All' : 'Loop: Sentence'}
				>
					{#if playbackMode === 'off'}
						Loop Off
					{:else if playbackMode === 'loop'}
						Loop All
					{:else}
						Loop 1
					{/if}
				</button>
				<button class="btn btn-ghost" onclick={openCollectionPicker}>
					+ Collection
				</button>
				<button class="btn btn-ghost" onclick={copyFullText}>
					{copySuccess ? 'Copied!' : 'Copy Text'}
				</button>
				<button class="btn btn-danger" onclick={handleDelete}>
					Delete
				</button>
			</div>
		</div>

		<!-- Right: Transcript -->
		<div class="transcript-panel">
			<div class="transcript-header">
				<h2>Transcript</h2>
				{#if video.transcript}
					<span class="segment-count">{video.transcript.segments.length} segments</span>
				{/if}
				<div class="transcript-actions">
					{#if hasTranslation}
						<button class="lang-toggle" onclick={cycleDisplayMode}>
							{displayMode === 'en' ? 'EN' : displayMode === 'zh' ? '中' : 'EN/中'}
						</button>
					{:else}
						<button
							class="btn btn-translate"
							onclick={handleTranslate}
							disabled={translating || !video.transcript}
						>
							{translating ? 'Translating...' : 'Translate 中文'}
						</button>
					{/if}
				</div>
			</div>

			{#if video.transcript?.segments}
				<div class="segments">
					{#each video.transcript.segments as segment, i (segment.index)}
						<div class="segment-row" class:active={i === activeSegmentIndex} class:repeating={playbackMode === 'repeat-one' && i === repeatSegmentIndex}>
						<button
							class="segment"
							onclick={() => seekTo(segment)}
						>
							<span class="segment-time">{formatTime(segment.start)}</span>
							<span class="segment-text-wrapper">
								{#if displayMode === 'en' || displayMode === 'both'}
									<span class="segment-text">{segment.text}</span>
								{/if}
								{#if (displayMode === 'zh' || displayMode === 'both') && segment.translation}
									<span class="segment-translation">{segment.translation}</span>
								{/if}
							</span>
						</button>
						<button
							class="segment-lock"
							class:locked={playbackMode === 'repeat-one' && i === repeatSegmentIndex}
							onclick={() => lockSegment(i)}
							title="Repeat this sentence"
						>
							{playbackMode === 'repeat-one' && i === repeatSegmentIndex ? '■' : '⟳'}
						</button>
					</div>
					{/each}
				</div>

				<div class="full-text-section">
					<h3>Full Text</h3>
					<div class="full-text">
						{video.transcript.full_text}
					</div>
				</div>
			{:else}
				<p class="no-transcript">No transcript available yet.</p>
			{/if}
		</div>
	</div>

	<!-- Collection Picker Modal -->
	{#if showCollectionPicker}
		<!-- svelte-ignore a11y_click_events_have_key_events -->
		<div class="modal-overlay" onclick={() => (showCollectionPicker = false)} role="presentation">
			<!-- svelte-ignore a11y_click_events_have_key_events a11y_interactive_supports_focus -->
			<div class="modal" onclick={(e) => e.stopPropagation()} role="dialog" tabindex="-1">
				<h3>Add to Collection</h3>
				{#if collections.length === 0}
					<p class="empty">No collections yet. Create one from the Collections page.</p>
				{:else}
					<div class="collection-list">
						{#each collections as col (col.id)}
							<button class="collection-option" onclick={() => handleAddToCollection(col.id)}>
								<span>{col.name}</span>
								<span class="count">{col.video_count} videos</span>
							</button>
						{/each}
					</div>
				{/if}
				<button class="btn btn-ghost" onclick={() => (showCollectionPicker = false)}>Cancel</button>
			</div>
		</div>
	{/if}
{/if}

<style>
	.loading {
		text-align: center;
		padding: 80px 0;
		color: var(--text-dim);
	}

	.watch-layout {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 32px;
		align-items: start;
	}

	@media (max-width: 900px) {
		.watch-layout {
			grid-template-columns: 1fr;
		}
	}

	/* Player Panel */
	.player-panel {
		position: sticky;
		top: 72px;
	}

	.video-player {
		width: 100%;
		border-radius: var(--radius);
		background: #000;
		aspect-ratio: 9 / 16;
		max-height: 70vh;
		object-fit: contain;
	}

	.video-placeholder {
		width: 100%;
		aspect-ratio: 9 / 16;
		background: var(--bg-card);
		border-radius: var(--radius);
		display: flex;
		align-items: center;
		justify-content: center;
		color: var(--text-dim);
	}

	.video-info {
		margin-top: 16px;
	}

	.video-info h1 {
		font-size: 20px;
		font-weight: 700;
		margin-bottom: 8px;
	}

	.video-info-row {
		display: flex;
		align-items: center;
		gap: 12px;
	}

	.channel {
		color: var(--text-dim);
		font-size: 14px;
	}

	.actions {
		display: flex;
		gap: 8px;
		margin-top: 16px;
		flex-wrap: wrap;
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

	.lang-toggle {
		padding: 4px 12px;
		border-radius: var(--radius-sm);
		font-size: 13px;
		font-weight: 600;
		background: var(--accent);
		color: white;
		transition: background 0.15s;
	}

	.lang-toggle:hover {
		background: var(--accent-hover);
	}

	.btn-translate {
		padding: 4px 12px;
		font-size: 13px;
		background: var(--bg-hover);
		color: var(--text-dim);
		border-radius: var(--radius-sm);
	}

	.btn-translate:hover:not(:disabled) {
		background: var(--accent);
		color: white;
	}

	.btn-translate:disabled {
		opacity: 0.5;
		cursor: not-allowed;
	}

	.segments {
		display: flex;
		flex-direction: column;
		gap: 2px;
		margin-bottom: 32px;
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
		margin-right: 8px;
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

	.btn-active {
		background: var(--accent);
		color: white;
	}

	.btn-active:hover {
		background: var(--accent-hover);
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

	.segment-translation {
		font-size: 14px;
		line-height: 1.5;
		color: var(--text-dim);
	}

	.segment-row.active .segment-translation {
		color: var(--accent);
	}

	.full-text-section {
		border-top: 1px solid var(--border);
		padding-top: 24px;
	}

	.full-text-section h3 {
		font-size: 16px;
		font-weight: 600;
		margin-bottom: 12px;
	}

	.full-text {
		font-size: 15px;
		line-height: 1.8;
		color: var(--text);
		white-space: pre-wrap;
		word-break: break-word;
	}

	.no-transcript {
		color: var(--text-dim);
		text-align: center;
		padding: 40px 0;
	}

	/* Modal */
	.modal-overlay {
		position: fixed;
		inset: 0;
		background: rgba(0, 0, 0, 0.6);
		display: flex;
		align-items: center;
		justify-content: center;
		z-index: 200;
	}

	.modal {
		background: var(--bg-card);
		border: 1px solid var(--border);
		border-radius: var(--radius);
		padding: 24px;
		width: 360px;
		max-width: 90vw;
	}

	.modal h3 {
		margin-bottom: 16px;
	}

	.empty {
		color: var(--text-dim);
		font-size: 14px;
		margin-bottom: 16px;
	}

	.collection-list {
		display: flex;
		flex-direction: column;
		gap: 4px;
		margin-bottom: 16px;
	}

	.collection-option {
		display: flex;
		justify-content: space-between;
		padding: 10px 12px;
		border-radius: var(--radius-sm);
		width: 100%;
		text-align: left;
	}

	.collection-option:hover {
		background: var(--bg-hover);
	}

	.count {
		color: var(--text-dim);
		font-size: 13px;
	}
</style>
