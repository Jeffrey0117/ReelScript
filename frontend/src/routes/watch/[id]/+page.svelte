<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import {
		getVideo,
		deleteVideo,
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

	// Derive from page store
	let videoId = '';
	page.subscribe((p) => {
		videoId = p.params.id;
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
			</div>

			{#if video.transcript?.segments}
				<div class="segments">
					{#each video.transcript.segments as segment, i (segment.index)}
						<button
							class="segment"
							class:active={i === activeSegmentIndex}
							onclick={() => seekTo(segment)}
						>
							<span class="segment-time">{formatTime(segment.start)}</span>
							<span class="segment-text">{segment.text}</span>
						</button>
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
		<div class="modal-overlay" onclick={() => (showCollectionPicker = false)} role="presentation">
			<div class="modal" onclick={(e) => e.stopPropagation()} role="dialog">
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

	.segments {
		display: flex;
		flex-direction: column;
		gap: 2px;
		margin-bottom: 32px;
	}

	.segment {
		display: flex;
		gap: 12px;
		padding: 10px 12px;
		border-radius: var(--radius-sm);
		text-align: left;
		transition: background 0.15s;
		width: 100%;
	}

	.segment:hover {
		background: var(--bg-hover);
	}

	.segment.active {
		background: rgba(99, 102, 241, 0.12);
	}

	.segment.active .segment-text {
		color: var(--accent-hover);
	}

	.segment-time {
		color: var(--text-dim);
		font-size: 12px;
		font-variant-numeric: tabular-nums;
		min-width: 40px;
		padding-top: 2px;
		flex-shrink: 0;
	}

	.segment-text {
		font-size: 15px;
		line-height: 1.6;
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
