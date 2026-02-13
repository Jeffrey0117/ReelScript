<script lang="ts">
	import { onMount } from 'svelte';
	import {
		processVideo,
		listVideos,
		connectWS,
		renameVideo,
		batchDeleteVideos,
		listCollections,
		createCollection,
		addToCollection,
		type Video,
		type Collection,
	} from '$lib/api';
	import { t } from '$lib/i18n';

	let url = $state('');
	let loading = $state(false);
	let error = $state('');
	let videos = $state<Video[]>([]);
	let progress = $state<Record<string, number>>({});

	// Inline rename state
	let editingVideoId = $state<string | null>(null);
	let editTitle = $state('');

	// Manage mode state
	let manageMode = $state(false);
	let selectedIds = $state<Set<string>>(new Set());

	// Collection modal state
	let showCollectionModal = $state(false);
	let modalCollections = $state<Collection[]>([]);
	let newCollectionName = $state('');
	let creatingCollection = $state(false);

	let readyVideos = $derived(videos.filter((v) => v.status === 'ready'));
	let selectedCount = $derived(selectedIds.size);
	let allSelected = $derived(
		readyVideos.length > 0 && readyVideos.every((v) => selectedIds.has(v.id))
	);

	onMount(async () => {
		videos = await listVideos();

		connectWS((msg: Record<string, unknown>) => {
			const data = msg.data as Record<string, unknown>;
			const type = msg.type as string;

			if (type === 'download_progress' && data?.video_id) {
				progress = { ...progress, [data.video_id as string]: data.progress as number };
			}

			if (
				type === 'transcribe_completed' ||
				type === 'download_error' ||
				type === 'process_error'
			) {
				listVideos().then((v) => (videos = v));
			}
		});
	});

	async function handleSubmit() {
		if (!url.trim()) return;

		loading = true;
		error = '';

		try {
			const result = await processVideo(url.trim());
			videos = [
				{
					id: result.video_id,
					url: url,
					title: result.title || 'Processing...',
					source: 'unknown',
					duration: null,
					thumbnail: null,
					channel: null,
					status: 'downloading',
					created_at: new Date().toISOString(),
				},
				...videos,
			];
			url = '';
		} catch (e) {
			error = e instanceof Error ? e.message : 'Something went wrong';
		} finally {
			loading = false;
		}
	}

	function formatDuration(seconds: number | null): string {
		if (!seconds) return '';
		const m = Math.floor(seconds / 60);
		const s = Math.floor(seconds % 60);
		return `${m}:${s.toString().padStart(2, '0')}`;
	}

	function statusBadgeClass(status: string): string {
		const map: Record<string, string> = {
			downloading: 'badge-processing',
			transcribing: 'badge-processing',
			ready: 'badge-ready',
			failed: 'badge-ig',
		};
		return map[status] || 'badge-processing';
	}

	function statusLabel(status: string): string {
		const map: Record<string, () => string> = {
			ready: () => t('statusReady'),
			downloading: () => t('statusDownloading'),
			transcribing: () => t('statusTranscribing'),
			failed: () => t('statusFailed'),
			pending: () => t('statusPending'),
		};
		return (map[status] ?? (() => status))();
	}

	// Inline rename
	function startEditing(video: Video) {
		editingVideoId = video.id;
		editTitle = video.title || '';
	}

	async function saveTitle() {
		if (!editingVideoId || !editTitle.trim()) {
			editingVideoId = null;
			return;
		}
		try {
			await renameVideo(editingVideoId, editTitle.trim());
			videos = videos.map((v) =>
				v.id === editingVideoId ? { ...v, title: editTitle.trim() } : v
			);
		} catch {
			// revert silently
		}
		editingVideoId = null;
	}

	function cancelEditing() {
		editingVideoId = null;
	}

	function handleTitleKeydown(e: KeyboardEvent) {
		if (e.key === 'Enter') {
			e.preventDefault();
			saveTitle();
		} else if (e.key === 'Escape') {
			cancelEditing();
		}
	}

	// Manage mode
	function toggleManageMode() {
		manageMode = !manageMode;
		if (!manageMode) {
			selectedIds = new Set();
		}
	}

	function toggleSelect(videoId: string) {
		const next = new Set(selectedIds);
		if (next.has(videoId)) {
			next.delete(videoId);
		} else {
			next.add(videoId);
		}
		selectedIds = next;
	}

	function toggleSelectAll() {
		if (allSelected) {
			selectedIds = new Set();
		} else {
			selectedIds = new Set(readyVideos.map((v) => v.id));
		}
	}

	// Batch delete
	async function handleBatchDelete() {
		if (selectedCount === 0) return;
		const msg = t('confirmBatchDelete').replace('{count}', String(selectedCount));
		if (!confirm(msg)) return;

		try {
			await batchDeleteVideos([...selectedIds]);
			videos = videos.filter((v) => !selectedIds.has(v.id));
			selectedIds = new Set();
		} catch {
			// ignore
		}
	}

	// Collection modal
	async function openCollectionModal() {
		modalCollections = await listCollections();
		newCollectionName = '';
		showCollectionModal = true;
	}

	function closeCollectionModal() {
		showCollectionModal = false;
	}

	async function handleCreateAndAdd() {
		if (!newCollectionName.trim()) return;
		creatingCollection = true;
		try {
			const col = await createCollection(newCollectionName.trim());
			for (const id of selectedIds) {
				await addToCollection(col.id, id);
			}
			selectedIds = new Set();
			showCollectionModal = false;
		} finally {
			creatingCollection = false;
		}
	}

	async function handleAddToExisting(colId: string) {
		try {
			for (const id of selectedIds) {
				await addToCollection(colId, id);
			}
			selectedIds = new Set();
			showCollectionModal = false;
		} catch {
			// ignore
		}
	}
</script>

<svelte:head>
	<title>ReelScript</title>
</svelte:head>

<section class="hero">
	<h1>{t('addVideo')}</h1>
	<p>{t('urlPlaceholder')}</p>

	<form class="url-form" onsubmit={(e) => { e.preventDefault(); handleSubmit(); }}>
		<input
			type="url"
			bind:value={url}
			placeholder="https://www.instagram.com/reel/... or YouTube link"
			disabled={loading}
		/>
		<button class="btn btn-primary" type="submit" disabled={loading || !url.trim()}>
			{loading ? t('processing') : t('start')}
		</button>
	</form>

	{#if error}
		<p class="error-msg">{error}</p>
	{/if}
</section>

{#if videos.length > 0}
	<section class="video-list">
		<div class="video-list-header">
			<h2>{t('myVideos')}</h2>
			<div class="header-actions">
				{#if manageMode}
					<button class="btn btn-ghost btn-sm" onclick={toggleSelectAll}>
						{allSelected ? t('deselectAll') : t('selectAll')}
					</button>
				{/if}
				<button
					class="btn {manageMode ? 'btn-primary' : 'btn-ghost'} btn-sm"
					onclick={toggleManageMode}
				>
					{manageMode ? t('done') : t('manage')}
				</button>
			</div>
		</div>

		<div class="grid">
			{#each videos as video (video.id)}
				{@const isReady = video.status === 'ready'}
				{@const isSelected = selectedIds.has(video.id)}
				{@const isEditing = editingVideoId === video.id}
				<div
					class="video-card card"
					class:disabled={!isReady}
					class:selected={isSelected}
					onclick={() => {
						if (manageMode && isReady) {
							toggleSelect(video.id);
						}
					}}
					onkeydown={(e) => {
						if (manageMode && isReady && (e.key === 'Enter' || e.key === ' ')) {
							e.preventDefault();
							toggleSelect(video.id);
						}
					}}
					role={manageMode ? 'checkbox' : undefined}
					aria-checked={manageMode ? isSelected : undefined}
					tabindex={manageMode ? 0 : undefined}
				>
					{#if manageMode && isReady}
						<div class="checkbox-overlay">
							<input
								type="checkbox"
								checked={isSelected}
								onclick={(e) => e.stopPropagation()}
								onchange={() => toggleSelect(video.id)}
								tabindex={-1}
							/>
						</div>
					{/if}

					{#if !manageMode && isReady}
						<a href="/watch/{video.id}" class="card-link" aria-label={video.title || t('untitled')}></a>
					{/if}

					<div class="video-card-header">
						<span class="badge {video.source === 'ig' ? 'badge-ig' : 'badge-youtube'}">
							{video.source === 'ig' ? 'IG' : video.source === 'youtube' ? 'YT' : '?'}
						</span>
						<span class="badge {statusBadgeClass(video.status)}">{statusLabel(video.status)}</span>
					</div>

					{#if isEditing}
						<!-- svelte-ignore a11y_autofocus -->
					<input
							class="title-input"
							type="text"
							bind:value={editTitle}
							onkeydown={handleTitleKeydown}
							onblur={saveTitle}
							onclick={(e) => e.stopPropagation()}
							autofocus
						/>
					{:else}
						<!-- svelte-ignore a11y_click_events_have_key_events -->
						<!-- svelte-ignore a11y_no_static_element_interactions -->
						<!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
						<h3
							class="video-title"
							class:editable={isReady && !manageMode}
							onclick={(e) => {
								if (isReady && !manageMode) {
									e.preventDefault();
									e.stopPropagation();
									startEditing(video);
								}
							}}
						>
							{video.title || t('untitled')}
						</h3>
					{/if}

					<div class="video-meta">
						{#if video.channel}
							<span>{video.channel}</span>
						{/if}
						{#if video.duration}
							<span>{formatDuration(video.duration)}</span>
						{/if}
					</div>

					{#if progress[video.id] !== undefined && !isReady}
						<div class="progress-bar" style="margin-top: 12px;">
							<div class="progress-bar-fill" style="width: {progress[video.id]}%"></div>
						</div>
					{/if}
				</div>
			{/each}
		</div>
	</section>
{/if}

<!-- Floating action bar -->
{#if manageMode && selectedCount > 0}
	<div class="floating-bar">
		<span class="selected-count">{selectedCount} {t('selected')}</span>
		<div class="floating-actions">
			<button class="btn btn-primary btn-sm" onclick={openCollectionModal}>
				{t('addSelectedToCollection')}
			</button>
			<button class="btn btn-danger btn-sm" onclick={handleBatchDelete}>
				{t('deleteSelected')}
			</button>
		</div>
	</div>
{/if}

<!-- Collection modal -->
{#if showCollectionModal}
	<!-- svelte-ignore a11y_click_events_have_key_events -->
	<!-- svelte-ignore a11y_no_static_element_interactions -->
	<div class="modal-overlay" onclick={closeCollectionModal}>
		<!-- svelte-ignore a11y_click_events_have_key_events -->
		<!-- svelte-ignore a11y_no_static_element_interactions -->
		<div class="modal" onclick={(e) => e.stopPropagation()}>
			<h3>{t('selectCollection')}</h3>

			{#if modalCollections.length > 0}
				<div class="modal-list">
					{#each modalCollections as col (col.id)}
						<button class="modal-list-item" onclick={() => handleAddToExisting(col.id)}>
							<span>{col.name}</span>
							<span class="col-count-badge">{col.video_count}</span>
						</button>
					{/each}
				</div>
			{/if}

			<div class="modal-create">
				<p class="modal-label">{t('createNewCollection')}</p>
				<form class="modal-create-form" onsubmit={(e) => { e.preventDefault(); handleCreateAndAdd(); }}>
					<input
						type="text"
						bind:value={newCollectionName}
						placeholder={t('collectionName')}
						disabled={creatingCollection}
					/>
					<button class="btn btn-primary btn-sm" type="submit" disabled={creatingCollection || !newCollectionName.trim()}>
						{t('create')}
					</button>
				</form>
			</div>

			<button class="btn btn-ghost btn-sm modal-cancel" onclick={closeCollectionModal}>
				{t('cancel')}
			</button>
		</div>
	</div>
{/if}

<style>
	.hero {
		text-align: center;
		padding: 48px 0 40px;
	}

	.hero h1 {
		font-size: 32px;
		font-weight: 700;
		letter-spacing: -0.5px;
		margin-bottom: 8px;
	}

	.hero p {
		color: var(--text-dim);
		font-size: 16px;
		margin-bottom: 28px;
	}

	.url-form {
		display: flex;
		gap: 12px;
		max-width: 640px;
		margin: 0 auto;
	}

	.url-form input {
		flex: 1;
	}

	.error-msg {
		color: var(--danger);
		font-size: 14px;
		margin-top: 12px;
	}

	.video-list {
		margin-top: 16px;
	}

	.video-list-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: 16px;
	}

	.video-list-header h2 {
		font-size: 18px;
		font-weight: 600;
	}

	.header-actions {
		display: flex;
		gap: 8px;
	}

	.btn-ghost {
		background: transparent;
		color: var(--text);
		border: 1px solid var(--border);
	}

	.btn-ghost:hover {
		background: var(--bg-hover);
	}

	.btn-sm {
		padding: 6px 12px;
		font-size: 13px;
	}

	.grid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
		gap: 16px;
		padding-bottom: 80px;
	}

	.video-card {
		position: relative;
		display: block;
		transition: border-color 0.15s, transform 0.15s;
		color: inherit;
		cursor: default;
	}

	.video-card:hover:not(.disabled) {
		border-color: var(--accent);
		transform: translateY(-2px);
	}

	.video-card.disabled {
		opacity: 0.7;
		cursor: default;
	}

	.video-card.selected {
		border-color: var(--accent);
		background: color-mix(in srgb, var(--accent) 8%, transparent);
	}

	.card-link {
		position: absolute;
		inset: 0;
		z-index: 1;
	}

	.checkbox-overlay {
		position: absolute;
		top: 12px;
		right: 12px;
		z-index: 2;
	}

	.checkbox-overlay input[type='checkbox'] {
		width: 18px;
		height: 18px;
		cursor: pointer;
		accent-color: var(--accent);
	}

	.video-card-header {
		display: flex;
		gap: 8px;
		margin-bottom: 12px;
	}

	.video-title {
		font-size: 15px;
		font-weight: 600;
		margin-bottom: 8px;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
		position: relative;
		z-index: 2;
	}

	.video-title.editable {
		cursor: text;
		border-radius: 4px;
		padding: 2px 4px;
		margin: -2px -4px;
	}

	.video-title.editable:hover {
		background: var(--bg-hover);
	}

	.title-input {
		font-size: 15px;
		font-weight: 600;
		margin-bottom: 8px;
		width: 100%;
		padding: 2px 4px;
		border: 1px solid var(--accent);
		border-radius: 4px;
		background: var(--bg);
		color: var(--text);
		outline: none;
		position: relative;
		z-index: 2;
	}

	.video-meta {
		display: flex;
		gap: 12px;
		font-size: 13px;
		color: var(--text-dim);
	}

	/* Floating action bar */
	.floating-bar {
		position: fixed;
		bottom: 24px;
		left: 50%;
		transform: translateX(-50%);
		background: var(--bg-card);
		border: 1px solid var(--border);
		border-radius: var(--radius);
		padding: 12px 20px;
		display: flex;
		align-items: center;
		gap: 16px;
		box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
		z-index: 100;
	}

	.selected-count {
		font-size: 14px;
		font-weight: 600;
		white-space: nowrap;
	}

	.floating-actions {
		display: flex;
		gap: 8px;
	}

	/* Collection modal */
	.modal-overlay {
		position: fixed;
		inset: 0;
		background: rgba(0, 0, 0, 0.6);
		display: flex;
		align-items: center;
		justify-content: center;
		z-index: 200;
		padding: 16px;
	}

	.modal {
		background: var(--bg-card);
		border: 1px solid var(--border);
		border-radius: var(--radius);
		padding: 24px;
		width: 100%;
		max-width: 400px;
		max-height: 80vh;
		overflow-y: auto;
	}

	.modal h3 {
		font-size: 18px;
		font-weight: 600;
		margin-bottom: 16px;
	}

	.modal-list {
		display: flex;
		flex-direction: column;
		gap: 4px;
		margin-bottom: 20px;
	}

	.modal-list-item {
		display: flex;
		justify-content: space-between;
		align-items: center;
		padding: 10px 12px;
		border-radius: var(--radius-sm);
		text-align: left;
		width: 100%;
	}

	.modal-list-item:hover {
		background: var(--bg-hover);
	}

	.col-count-badge {
		background: var(--bg-hover);
		color: var(--text-dim);
		font-size: 12px;
		padding: 2px 8px;
		border-radius: 10px;
	}

	.modal-create {
		border-top: 1px solid var(--border);
		padding-top: 16px;
	}

	.modal-label {
		font-size: 13px;
		color: var(--text-dim);
		margin-bottom: 8px;
	}

	.modal-create-form {
		display: flex;
		gap: 8px;
	}

	.modal-create-form input {
		flex: 1;
		padding: 8px 12px;
		font-size: 14px;
	}

	.modal-cancel {
		margin-top: 16px;
		width: 100%;
	}

	@media (max-width: 640px) {
		.hero {
			padding: 32px 0 24px;
		}

		.hero h1 {
			font-size: 24px;
		}

		.hero p {
			font-size: 14px;
			margin-bottom: 20px;
		}

		.url-form {
			flex-direction: column;
		}

		.url-form input {
			width: 100%;
		}

		.grid {
			grid-template-columns: 1fr;
		}

		.floating-bar {
			left: 16px;
			right: 16px;
			transform: none;
			flex-wrap: wrap;
			justify-content: center;
		}

		.video-list-header {
			flex-wrap: wrap;
			gap: 8px;
		}
	}
</style>
