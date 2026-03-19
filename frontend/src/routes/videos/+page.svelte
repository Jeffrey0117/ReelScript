<script lang="ts">
	import { onMount } from 'svelte';
	import {
		processVideo,
		batchProcessVideos,
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
	let isLoggedIn = $state(false);
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
		// Load videos immediately (works with DEV_BYPASS_AUTH or logged-in users)
		videos = await listVideos().catch(() => []);
		loadingVideos = false;
		quota = await getQuota().catch(() => null);

		onAuthChange(async (user) => {
			isLoggedIn = !!user;
			if (user) {
				videos = await listVideos().catch(() => []);
				quota = await getQuota().catch(() => null);
				const inv = await getMyInviteCode().catch(() => null);
				inviteCode = inv?.code ?? '';
			} else {
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

	function parseUrls(input: string): string[] {
		return input
			.split(/[\s\n]+/)
			.map((s) => s.trim())
			.filter((s) => s.startsWith('http'));
	}

	async function handleSubmit() {
		if (!url.trim()) return;

		const urls = parseUrls(url);
		if (urls.length === 0) return;

		loading = true;
		error = '';

		try {
			if (urls.length === 1) {
				const result = await processVideo(urls[0]);
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
							url: urls[0],
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
			} else {
				const result = await batchProcessVideos(urls);
				const newVideos: Video[] = result.results
					.filter((r) => r.success && r.video_id)
					.map((r) => ({
						id: r.video_id!,
						url: r.url,
						title: r.title || 'Processing...',
						source: 'unknown',
						duration: null,
						thumbnail: null,
						channel: null,
						status: r.status || 'downloading',
						error_message: null,
						created_at: new Date().toISOString(),
					}));
				const existingIds = new Set(videos.map((v) => v.id));
				const toAdd = newVideos.filter((v) => !existingIds.has(v.id));
				videos = [...toAdd, ...videos];
				const failed = result.results.filter((r) => !r.success);
				if (failed.length > 0) {
					error = `${result.started}/${result.total} 開始處理，${failed.length} 個失敗`;
				}
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
	<title>{t('myVideos')} - ReelScript</title>
</svelte:head>

<section class="hero">
	<div class="hero-icon">
		<svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
			<polygon points="5 3 19 12 5 21 5 3"/>
		</svg>
	</div>
	<h1>{t('addVideo')}</h1>
	<p class="hero-subtitle">{t('urlPlaceholder')}</p>

	<form class="url-form" onsubmit={(e) => { e.preventDefault(); handleSubmit(); }}>
		<div class="input-wrapper">
			<textarea
				bind:value={url}
				placeholder="貼上 IG 或 YouTube 連結..."
				disabled={loading}
				rows={parseUrls(url).length > 1 ? 3 : 1}
				onkeydown={(e) => {
					if (e.key === 'Enter' && !e.shiftKey) {
						const urls = parseUrls(url);
						if (urls.length <= 1) {
							e.preventDefault();
							handleSubmit();
						}
					}
				}}
			></textarea>
			<button class="submit-btn" type="submit" disabled={loading || !url.trim()}>
				{#if loading}
					<svg class="spinner" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
						<path d="M12 2a10 10 0 0 1 10 10"/>
					</svg>
				{:else}
					{@const count = parseUrls(url).length}
					<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
						<line x1="5" y1="12" x2="19" y2="12"/>
						<polyline points="12 5 19 12 12 19"/>
					</svg>
					{#if count > 1}
						<span>{count}</span>
					{/if}
				{/if}
			</button>
		</div>
	</form>
	<div class="hero-meta">
		{#if quota && quota.plan === 'free'}
			<a href="/pricing" class="quota-pill">
				<svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor" stroke="none">
					<polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>
				</svg>
				<span>{quota.remaining} {t('creditsRemaining')}</span>
			</a>
		{/if}
		{#if inviteCode}
			<button class="invite-btn" onclick={handleShareInvite}>
				{inviteCopied ? t('linkCopied') : t('inviteFriends')}
			</button>
		{/if}
	</div>

	{#if error}
		<p class="error-msg">{error}</p>
	{/if}
</section>

{#if loadingVideos}
	<section class="video-list">
		<h2>{t('myVideos')}</h2>
		<div class="video-list-items">
			{#each Array(3) as _}
				<div class="video-row card skeleton-card">
					<div class="skeleton-thumb"></div>
					<div class="skeleton-body">
						<div class="skeleton-line"></div>
						<div class="skeleton-line short"></div>
					</div>
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
					<button class="btn btn-ghost btn-sm ig-mode-btn" onclick={() => goto('/blog')}>
						<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
							<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
							<polyline points="14 2 14 8 20 8"/>
							<line x1="16" y1="13" x2="8" y2="13"/>
							<line x1="16" y1="17" x2="8" y2="17"/>
						</svg>
						{t('blog')}
					</button>
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

		<div class="video-list-items">
			{#each activeVideos as video (video.id)}
				{@const isReady = video.status === 'ready'}
				{@const isSelected = selectedIds.has(video.id)}
				{@const isEditing = editingVideoId === video.id}
				<div
					class="video-row card"
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
						</div>
					{/if}

					<div class="video-row-body">
						<div class="video-row-top">
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
						</div>

						<div class="video-row-bottom">
							<div class="video-card-header">
								<span class="badge {video.source === 'ig' ? 'badge-ig' : 'badge-youtube'}">
									{video.source === 'ig' ? 'IG' : video.source === 'youtube' ? 'YT' : '?'}
								</span>
								<span class="badge {statusBadgeClass(video.status)}">{statusLabel(video.status)}</span>
								{#if video.duration && !video.thumbnail}
									<span class="meta-duration">{formatDuration(video.duration)}</span>
								{/if}
							</div>
						</div>

						{#if progress[video.id] !== undefined && !isReady}
							<div class="progress-bar" style="margin-top: 8px;">
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
		padding: 56px 0 44px;
	}

	.hero-icon {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		width: 64px;
		height: 64px;
		border-radius: 16px;
		background: color-mix(in srgb, var(--accent) 10%, transparent);
		color: var(--accent);
		margin-bottom: 20px;
	}

	.hero h1 {
		font-size: 28px;
		font-weight: 700;
		letter-spacing: -0.5px;
		margin-bottom: 6px;
	}

	.hero-subtitle {
		color: var(--text-dim);
		font-size: 15px;
		margin-bottom: 32px;
	}

	.url-form {
		max-width: 560px;
		margin: 0 auto;
	}

	.input-wrapper {
		display: flex;
		align-items: stretch;
		background: var(--bg-card);
		border: 1px solid var(--border);
		border-radius: var(--radius);
		overflow: hidden;
		transition: border-color 0.2s, box-shadow 0.2s;
	}

	.input-wrapper:focus-within {
		border-color: var(--accent);
		box-shadow: 0 0 0 3px color-mix(in srgb, var(--accent) 15%, transparent);
	}

	.input-wrapper textarea {
		flex: 1;
		resize: none;
		font-family: inherit;
		font-size: 15px;
		line-height: 1.5;
		padding: 12px 16px;
		border: none;
		background: transparent;
		color: var(--text);
		outline: none;
		field-sizing: content;
		min-height: 46px;
		max-height: 120px;
	}

	.submit-btn {
		display: flex;
		align-items: center;
		justify-content: center;
		gap: 4px;
		padding: 0 20px;
		background: var(--accent);
		color: white;
		font-weight: 600;
		font-size: 14px;
		border: none;
		cursor: pointer;
		transition: background 0.15s;
		flex-shrink: 0;
	}

	.submit-btn:hover:not(:disabled) {
		background: var(--accent-hover);
	}

	.submit-btn:disabled {
		opacity: 0.4;
		cursor: not-allowed;
	}

	.spinner {
		animation: spin 0.8s linear infinite;
	}

	@keyframes spin {
		to { transform: rotate(360deg); }
	}

	.hero-meta {
		display: flex;
		align-items: center;
		justify-content: center;
		gap: 12px;
		margin-top: 14px;
	}

	.quota-pill {
		display: inline-flex;
		align-items: center;
		gap: 5px;
		font-size: 13px;
		font-weight: 500;
		color: var(--text-dim) !important;
		text-decoration: none;
		padding: 4px 12px;
		border-radius: 20px;
		background: color-mix(in srgb, var(--accent) 6%, transparent);
		transition: background 0.15s, color 0.15s;
	}

	.quota-pill svg {
		color: var(--accent);
	}

	.quota-pill:hover {
		background: color-mix(in srgb, var(--accent) 12%, transparent);
		color: var(--text) !important;
	}

	.invite-btn {
		font-size: 13px;
		font-weight: 500;
		color: var(--text-dim);
		background: none;
		border: 1px solid var(--border);
		border-radius: 20px;
		padding: 4px 14px;
		cursor: pointer;
		transition: all 0.15s;
	}

	.invite-btn:hover {
		border-color: var(--accent);
		color: var(--accent);
		background: color-mix(in srgb, var(--accent) 6%, transparent);
	}

	.error-msg {
		color: var(--danger);
		font-size: 14px;
		margin-top: 14px;
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

	.video-list-items {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
		gap: 12px;
		padding-bottom: 80px;
	}

	.video-row {
		position: relative;
		display: flex;
		flex-direction: column;
		gap: 0;
		padding: 0;
		transition: border-color 0.15s;
		color: inherit;
		cursor: default;
		overflow: hidden;
	}

	.video-thumb {
		position: relative;
		flex-shrink: 0;
		width: 100%;
		border-radius: 0;
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
		bottom: 4px;
		right: 4px;
		background: rgba(0, 0, 0, 0.75);
		color: #fff;
		font-size: 11px;
		font-weight: 600;
		padding: 1px 5px;
		border-radius: 3px;
		font-variant-numeric: tabular-nums;
	}

	.video-row-body {
		flex: 1;
		min-width: 0;
		display: flex;
		flex-direction: column;
		gap: 6px;
		padding: 10px 14px 12px;
	}

	.video-row:hover:not(.disabled) {
		border-color: var(--accent);
	}

	.video-row.disabled {
		opacity: 0.7;
		cursor: default;
	}

	.video-row.selected {
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
		top: 8px;
		right: 8px;
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
		gap: 6px;
		align-items: center;
	}

	.meta-duration {
		font-size: 12px;
		color: var(--text-dim);
		margin-left: 4px;
	}

	.title-row {
		display: flex;
		align-items: center;
		gap: 4px;
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

	.video-row:hover .edit-btn {
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
		padding: 12px 16px;
	}

	.skeleton-thumb {
		flex-shrink: 0;
		width: 160px;
		aspect-ratio: 16 / 9;
		background: var(--border);
		border-radius: var(--radius-sm);
		animation: shimmer 1.5s infinite;
	}

	.skeleton-body {
		flex: 1;
		display: flex;
		flex-direction: column;
		gap: 10px;
	}

	.skeleton-line {
		height: 14px;
		background: var(--border);
		border-radius: 4px;
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
			padding: 36px 0 24px;
		}

		.hero-icon {
			width: 52px;
			height: 52px;
			margin-bottom: 16px;
		}

		.hero-icon svg {
			width: 28px;
			height: 28px;
		}

		.hero h1 {
			font-size: 22px;
		}

		.hero-subtitle {
			font-size: 14px;
			margin-bottom: 24px;
		}

		.video-list-items {
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

</style>
