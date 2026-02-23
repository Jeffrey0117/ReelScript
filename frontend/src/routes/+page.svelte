<script lang="ts">
	import { onMount } from 'svelte';
	import {
		processVideo,
		listVideos,
		connectWS,
		renameVideo,
		batchDeleteVideos,
		retryVideo,
		retryAllFailed,
		deleteVideo,
		listCollections,
		createCollection,
		addToCollection,
		thumbnailUrl,
		getQuota,
		getMyInviteCode,
		type Video,
		type Collection,
		type Quota,
	} from '$lib/api';
	import { goto } from '$app/navigation';
	import { t } from '$lib/i18n';
	import { getUser, login, onAuthChange } from '$lib/auth';

	let url = $state('');
	let loading = $state(false);
	let loadingVideos = $state(true);
	let error = $state('');
	let videos = $state<Video[]>([]);
	let progress = $state<Record<string, number>>({});
	let isLoggedIn = $state(!!getUser());
	let quota = $state<Quota | null>(null);
	let inviteCode = $state('');
	let inviteCopied = $state(false);

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
	let failedVideos = $derived(videos.filter((v) => v.status === 'failed'));
	let activeVideos = $derived(videos.filter((v) => v.status !== 'failed'));
	let retryingIds = $state<Set<string>>(new Set());
	let retryingAll = $state(false);
	let selectedCount = $derived(selectedIds.size);
	let allSelected = $derived(
		readyVideos.length > 0 && readyVideos.every((v) => selectedIds.has(v.id))
	);

	onMount(async () => {
		onAuthChange(async (user) => {
			isLoggedIn = !!user;
			if (user) {
				videos = await listVideos().catch(() => []);
				loadingVideos = false;
				quota = await getQuota().catch(() => null);
				const inv = await getMyInviteCode().catch(() => null);
				inviteCode = inv?.code ?? '';
			} else {
				videos = [];
				loadingVideos = false;
				quota = null;
				inviteCode = '';
			}
		});

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

	async function handleShareInvite() {
		if (!inviteCode) return;
		const link = `https://reelscript.isnowfriend.com?invite=${inviteCode}`;
		try {
			await navigator.clipboard.writeText(link);
			inviteCopied = true;
			setTimeout(() => { inviteCopied = false; }, 2000);
		} catch {
			// Fallback for older browsers
			const input = document.createElement('input');
			input.value = link;
			document.body.appendChild(input);
			input.select();
			document.execCommand('copy');
			document.body.removeChild(input);
			inviteCopied = true;
			setTimeout(() => { inviteCopied = false; }, 2000);
		}
	}

	async function handleSubmit() {
		if (!url.trim()) return;

		loading = true;
		error = '';

		try {
			const result = await processVideo(url.trim());
			const existingIdx = videos.findIndex((v) => v.id === result.video_id);
			if (existingIdx >= 0) {
				videos = videos.map((v) =>
					v.id === result.video_id
						? { ...v, status: result.status || 'downloading', error_message: null }
						: v
				);
			} else {
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
						error_message: null,
						created_at: new Date().toISOString(),
					},
					...videos,
				];
			}
			url = '';
			quota = await getQuota().catch(() => null);
		} catch (e: unknown) {
			const err = e as Error & { status?: number };
			if (err.status === 401) {
				error = '請先登入';
				login();
			} else {
				error = err.message || 'Something went wrong';
			}
		} finally {
			loading = false;
		}
	}

	async function handleRetry(videoId: string) {
		retryingIds = new Set([...retryingIds, videoId]);
		try {
			await retryVideo(videoId);
			videos = videos.map((v) =>
				v.id === videoId ? { ...v, status: 'downloading', error_message: null } : v
			);
		} catch {
			// refresh list to get actual state
			videos = await listVideos();
		} finally {
			const next = new Set(retryingIds);
			next.delete(videoId);
			retryingIds = next;
		}
	}

	async function handleRetryAll() {
		retryingAll = true;
		try {
			const result = await retryAllFailed();
			if (result.retried > 0) {
				videos = videos.map((v) =>
					v.status === 'failed' ? { ...v, status: 'downloading', error_message: null } : v
				);
			}
		} catch {
			videos = await listVideos();
		} finally {
			retryingAll = false;
		}
	}

	async function handleDeleteFailed(videoId: string) {
		try {
			await deleteVideo(videoId);
			videos = videos.filter((v) => v.id !== videoId);
		} catch {
			// ignore
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

	{#if isLoggedIn}
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
		<div class="hero-meta">
			{#if quota && quota.plan === 'free'}
				<span class="quota-info">{quota.videos_used} / {quota.limit} {t('monthlyUsed')}</span>
			{/if}
			{#if inviteCode}
				<button class="invite-btn" onclick={handleShareInvite}>
					{inviteCopied ? t('linkCopied') : t('inviteFriends')}
				</button>
			{/if}
		</div>
	{:else}
		<button class="btn btn-primary" onclick={login}>{t('loginToStart')}</button>
	{/if}

	{#if error}
		<p class="error-msg">{error}</p>
	{/if}
</section>

{#if loadingVideos}
	<section class="video-list">
		<h2>{t('myVideos')}</h2>
		<div class="grid">
			{#each Array(3) as _}
				<div class="video-card card skeleton-card">
					<div class="skeleton-line short"></div>
					<div class="skeleton-line"></div>
					<div class="skeleton-line short"></div>
				</div>
			{/each}
		</div>
	</section>
{:else if videos.length > 0}
	<section class="video-list">
		<div class="video-list-header">
			<h2>{t('myVideos')}</h2>
			<div class="header-actions">
				{#if !manageMode && readyVideos.length > 0}
					<button class="btn btn-ghost btn-sm ig-mode-btn" onclick={() => goto('/ig')}>
						<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
							<rect x="2" y="2" width="20" height="20" rx="5" ry="5"/>
							<path d="M16 11.37A4 4 0 1 1 12.63 8 4 4 0 0 1 16 11.37z"/>
							<line x1="17.5" y1="6.5" x2="17.51" y2="6.5"/>
						</svg>
						{t('igMode')}
					</button>
				{/if}
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
			{#each activeVideos as video (video.id)}
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

					{#if video.thumbnail}
						<div class="video-thumb">
							<img src={thumbnailUrl(video.thumbnail)} alt="" loading="lazy" />
							{#if video.duration}
								<span class="thumb-duration">{formatDuration(video.duration)}</span>
							{/if}
							{#if !manageMode && isReady}
								<button
									class="ig-play-btn"
									onclick={(e) => { e.preventDefault(); e.stopPropagation(); goto(`/ig?start=${video.id}`); }}
									aria-label={t('igMode')}
								>
									<svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
										<path d="M8 5v14l11-7z"/>
									</svg>
								</button>
							{/if}
						</div>
					{/if}

					<div class="video-card-body">
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
						<div class="title-row">
							<!-- svelte-ignore a11y_click_events_have_key_events -->
							<!-- svelte-ignore a11y_no_static_element_interactions -->
							<!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
							<h3
								class="video-title"
								class:editable={isReady}
								onclick={(e) => {
									if (isReady) {
										e.preventDefault();
										e.stopPropagation();
										startEditing(video);
									}
								}}
							>
								{video.title || t('untitled')}
							</h3>
							{#if isReady}
								<button
									class="edit-btn"
									onclick={(e) => {
										e.preventDefault();
										e.stopPropagation();
										startEditing(video);
									}}
									aria-label="Rename"
								>
									<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
										<path d="M17 3a2.85 2.83 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5Z"/>
										<path d="m15 5 4 4"/>
									</svg>
								</button>
							{/if}
						</div>
					{/if}

					<div class="video-meta">
						{#if video.channel}
							<span>{video.channel}</span>
						{/if}
						{#if video.duration && !video.thumbnail}
							<span>{formatDuration(video.duration)}</span>
						{/if}
					</div>

					{#if progress[video.id] !== undefined && !isReady}
						<div class="progress-bar" style="margin-top: 12px;">
							<div class="progress-bar-fill" style="width: {progress[video.id]}%"></div>
						</div>
					{/if}
					</div>
				</div>
			{/each}
		</div>
	</section>
{/if}

{#if failedVideos.length > 0}
	<section class="failed-section">
		<div class="failed-header">
			<h2>{t('failedVideos2')} ({failedVideos.length})</h2>
			<button
				class="btn btn-primary btn-sm"
				onclick={handleRetryAll}
				disabled={retryingAll}
			>
				{retryingAll ? t('retrying') : t('retryAll')}
			</button>
		</div>
		<div class="failed-list">
			{#each failedVideos as video (video.id)}
				{@const isRetrying = retryingIds.has(video.id)}
				<div class="failed-item card">
					<div class="failed-info">
						<div class="failed-top">
							<span class="badge badge-ig">
								{video.source === 'ig' ? 'IG' : video.source === 'youtube' ? 'YT' : '?'}
							</span>
							<span class="failed-title">{video.title || video.url}</span>
						</div>
						{#if video.error_message}
							<p class="failed-error">{t('errorReason')}: {video.error_message}</p>
						{/if}
					</div>
					<div class="failed-actions">
						<button
							class="btn btn-primary btn-sm"
							onclick={() => handleRetry(video.id)}
							disabled={isRetrying}
						>
							{isRetrying ? t('retrying') : t('retry')}
						</button>
						<button
							class="btn btn-ghost btn-sm btn-danger-ghost"
							onclick={() => handleDeleteFailed(video.id)}
						>
							{t('deleteFailed')}
						</button>
					</div>
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

	.hero-meta {
		display: flex;
		align-items: center;
		justify-content: center;
		gap: 16px;
		margin-top: 10px;
	}

	.quota-info {
		font-size: 13px;
		color: var(--text-dim);
	}

	.invite-btn {
		font-size: 13px;
		color: var(--accent);
		background: none;
		border: 1px solid var(--accent);
		border-radius: var(--radius-sm);
		padding: 4px 12px;
		cursor: pointer;
		transition: background 0.15s, color 0.15s;
	}

	.invite-btn:hover {
		background: var(--accent);
		color: #fff;
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

	.video-thumb {
		position: relative;
		margin: -16px -16px 12px -16px;
		border-radius: var(--radius) var(--radius) 0 0;
		overflow: hidden;
		aspect-ratio: 16 / 9;
		background: var(--border);
	}

	.video-thumb img {
		width: 100%;
		height: 100%;
		object-fit: cover;
		display: block;
	}

	.thumb-duration {
		position: absolute;
		bottom: 6px;
		right: 6px;
		background: rgba(0, 0, 0, 0.75);
		color: #fff;
		font-size: 12px;
		font-weight: 600;
		padding: 2px 6px;
		border-radius: 4px;
		font-variant-numeric: tabular-nums;
	}

	.video-card-body {
		display: flex;
		flex-direction: column;
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

	.title-row {
		display: flex;
		align-items: center;
		gap: 4px;
		margin-bottom: 8px;
		position: relative;
		z-index: 2;
	}

	.video-title {
		font-size: 15px;
		font-weight: 600;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
		flex: 1;
		min-width: 0;
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

	.edit-btn {
		flex-shrink: 0;
		width: 28px;
		height: 28px;
		display: flex;
		align-items: center;
		justify-content: center;
		border-radius: 4px;
		font-size: 14px;
		color: var(--text-dim);
		opacity: 0;
		transition: opacity 0.15s;
	}

	.edit-btn:hover {
		background: var(--bg-hover);
		color: var(--text);
	}

	.video-card:hover .edit-btn {
		opacity: 1;
	}

	@media (pointer: coarse) {
		.edit-btn {
			opacity: 1;
		}
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

	/* Failed videos section */
	.failed-section {
		margin-top: 32px;
		margin-bottom: 24px;
	}

	.failed-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: 12px;
	}

	.failed-header h2 {
		font-size: 16px;
		font-weight: 600;
		color: var(--danger);
	}

	.failed-list {
		display: flex;
		flex-direction: column;
		gap: 8px;
	}

	.failed-item {
		display: flex;
		justify-content: space-between;
		align-items: center;
		gap: 12px;
		padding: 12px 16px;
	}

	.failed-info {
		flex: 1;
		min-width: 0;
	}

	.failed-top {
		display: flex;
		align-items: center;
		gap: 8px;
	}

	.failed-title {
		font-size: 14px;
		font-weight: 500;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	.failed-error {
		font-size: 12px;
		color: var(--text-dim);
		margin-top: 4px;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	.failed-actions {
		display: flex;
		gap: 6px;
		flex-shrink: 0;
	}

	.btn-danger-ghost {
		color: var(--danger);
		border-color: var(--danger);
	}

	.btn-danger-ghost:hover {
		background: color-mix(in srgb, var(--danger) 10%, transparent);
	}

	/* Skeleton loading */
	.skeleton-card {
		padding: 20px;
	}

	.skeleton-line {
		height: 14px;
		background: var(--border);
		border-radius: 4px;
		margin-bottom: 12px;
		animation: shimmer 1.5s infinite;
	}

	.skeleton-line.short {
		width: 40%;
	}

	@keyframes shimmer {
		0% { opacity: 0.5; }
		50% { opacity: 1; }
		100% { opacity: 0.5; }
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

		.failed-item {
			flex-direction: column;
			align-items: flex-start;
		}

		.failed-actions {
			width: 100%;
		}

		.failed-actions .btn {
			flex: 1;
		}
	}

	/* IG Mode button */
	.ig-mode-btn {
		border: 1px solid var(--border);
	}

	.ig-mode-btn svg {
		flex-shrink: 0;
	}

	/* IG play button on thumbnail */
	.ig-play-btn {
		position: absolute;
		bottom: 6px;
		left: 6px;
		z-index: 2;
		width: 32px;
		height: 32px;
		display: flex;
		align-items: center;
		justify-content: center;
		background: rgba(0, 0, 0, 0.6);
		color: #fff;
		border-radius: 50%;
		border: none;
		cursor: pointer;
		opacity: 0;
		transition: opacity 0.15s, background 0.15s;
	}

	.ig-play-btn:hover {
		background: var(--accent);
	}

	.video-card:hover .ig-play-btn {
		opacity: 1;
	}

	@media (pointer: coarse) {
		.ig-play-btn {
			opacity: 1;
		}
	}
</style>
