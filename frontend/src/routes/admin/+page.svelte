<script lang="ts">
	import { onMount } from 'svelte';
	import {
		adminStats,
		adminListVideos,
		adminUpdateVideo,
		adminDeleteVideo,
		type AdminStats,
		type AdminVideo,
	} from '$lib/api';
	import { t } from '$lib/i18n';
	import { onAuthChange, isAdmin, type AdmanUser } from '$lib/auth';

	const CATEGORIES = ['business', 'daily', 'tech', 'entertainment', 'motivation', 'education'];

	// Auth state: JWT (adman) or legacy password
	let authMode = $state<'checking' | 'jwt' | 'password' | 'none'>('checking');
	let adminKey = $state('');
	let authenticated = $state(false);
	let authError = $state('');

	let stats = $state<AdminStats | null>(null);
	let videos = $state<AdminVideo[]>([]);
	let loadingStats = $state(false);
	let loadingVideos = $state(false);

	// Filters
	let filterStatus = $state('');
	let filterCategory = $state('');
	let filterFeatured = $state('');
	let filterSearch = $state('');

	onMount(() => {
		// Listen for adman auth state
		const unsub = onAuthChange(async (user) => {
			if (user && user.role === 'admin') {
				// Auto-authenticate via JWT
				authMode = 'jwt';
				await tryJwtAuth();
			} else if (authMode === 'checking') {
				// No JWT admin, check for saved legacy key
				const saved = sessionStorage.getItem('admin-key');
				if (saved) {
					adminKey = saved;
					authMode = 'password';
					await tryLegacyLogin();
				} else {
					authMode = 'none';
				}
			}
		});

		// Fallback: if SDK doesn't load within 2s, show password form
		setTimeout(() => {
			if (authMode === 'checking') {
				const saved = sessionStorage.getItem('admin-key');
				if (saved) {
					adminKey = saved;
					authMode = 'password';
					tryLegacyLogin();
				} else {
					authMode = 'none';
				}
			}
		}, 2000);

		return unsub;
	});

	async function tryJwtAuth() {
		authError = '';
		try {
			loadingStats = true;
			stats = await adminStats();
			authenticated = true;
			await loadVideos();
		} catch {
			authError = t('wrongPassword');
			authenticated = false;
			authMode = 'none';
		} finally {
			loadingStats = false;
		}
	}

	async function tryLegacyLogin() {
		authError = '';
		try {
			loadingStats = true;
			stats = await adminStats(adminKey);
			authenticated = true;
			sessionStorage.setItem('admin-key', adminKey);
			await loadVideos();
		} catch {
			authError = t('wrongPassword');
			authenticated = false;
		} finally {
			loadingStats = false;
		}
	}

	async function loadVideos() {
		loadingVideos = true;
		const params: Record<string, string> = {};
		if (filterStatus) params.status = filterStatus;
		if (filterCategory) params.category = filterCategory;
		if (filterFeatured) params.featured = filterFeatured;
		if (filterSearch) params.search = filterSearch;
		const key = authMode === 'password' ? adminKey : '';
		videos = await adminListVideos(key, Object.keys(params).length > 0 ? params : undefined);
		loadingVideos = false;
	}

	async function toggleFeatured(video: AdminVideo) {
		const key = authMode === 'password' ? adminKey : '';
		await adminUpdateVideo(key, video.id, { is_featured: !video.is_featured });
		videos = videos.map((v) =>
			v.id === video.id ? { ...v, is_featured: !v.is_featured } : v
		);
		if (stats) {
			stats = {
				...stats,
				featured_count: stats.featured_count + (video.is_featured ? -1 : 1),
			};
		}
	}

	async function setCategory(video: AdminVideo, category: string) {
		const cat = category || undefined;
		const key = authMode === 'password' ? adminKey : '';
		await adminUpdateVideo(key, video.id, { category: cat ?? '' });
		videos = videos.map((v) =>
			v.id === video.id ? { ...v, category: cat ?? null } : v
		);
	}

	async function handleDelete(video: AdminVideo) {
		if (!confirm(`Delete "${video.title}"?`)) return;
		const key = authMode === 'password' ? adminKey : '';
		await adminDeleteVideo(key, video.id);
		videos = videos.filter((v) => v.id !== video.id);
		if (stats) {
			stats = { ...stats, total_videos: stats.total_videos - 1 };
		}
	}

	function handleLogout() {
		authenticated = false;
		adminKey = '';
		authMode = 'none';
		sessionStorage.removeItem('admin-key');
	}
</script>

<svelte:head>
	<title>{t('admin')} — ReelScript</title>
</svelte:head>

{#if authMode === 'checking'}
	<div class="login-page">
		<p class="loading-text">{t('loading')}</p>
	</div>
{:else if !authenticated}
	<div class="login-page">
		<div class="login-card card">
			<h1>{t('admin')}</h1>
			<p>{t('adminLogin')}</p>
			<form onsubmit={(e) => { e.preventDefault(); authMode = 'password'; tryLegacyLogin(); }}>
				<!-- svelte-ignore a11y_autofocus -->
				<input
					type="password"
					bind:value={adminKey}
					placeholder={t('adminPassword')}
					autofocus
				/>
				<button class="btn btn-primary" type="submit" disabled={!adminKey || loadingStats}>
					{loadingStats ? '...' : t('enter')}
				</button>
			</form>
			{#if authError}
				<p class="error-msg">{authError}</p>
			{/if}
		</div>
	</div>
{:else}
	<div class="admin-page">
		<div class="admin-header">
			<h1>{t('admin')}</h1>
			{#if authMode === 'password'}
				<button class="btn btn-ghost btn-sm" onclick={handleLogout}>{t('logout')}</button>
			{/if}
		</div>

		<!-- Stats Dashboard -->
		{#if stats}
			<div class="stats-grid">
				<div class="stat-card card">
					<div class="stat-value">{stats.total_videos}</div>
					<div class="stat-label">{t('totalVideos')}</div>
				</div>
				<div class="stat-card card">
					<div class="stat-value">{stats.ready_videos}</div>
					<div class="stat-label">{t('readyVideos')}</div>
				</div>
				<div class="stat-card card">
					<div class="stat-value">{stats.failed_videos}</div>
					<div class="stat-label">{t('failedVideos')}</div>
				</div>
				<div class="stat-card card">
					<div class="stat-value">{stats.featured_count}</div>
					<div class="stat-label">{t('featuredVideos')}</div>
				</div>
				<div class="stat-card card">
					<div class="stat-value">{stats.total_collections}</div>
					<div class="stat-label">{t('collections')}</div>
				</div>
			</div>

			{#if Object.keys(stats.sources).length > 0}
				<div class="breakdown">
					<span class="breakdown-label">{t('source')}:</span>
					{#each Object.entries(stats.sources) as [src, count]}
						<span class="badge {src === 'ig' ? 'badge-ig' : 'badge-youtube'}">{src} {count}</span>
					{/each}
				</div>
			{/if}
		{/if}

		<!-- Filters -->
		<div class="filters">
			<input
				type="text"
				placeholder="Search..."
				bind:value={filterSearch}
				oninput={() => loadVideos()}
			/>
			<select bind:value={filterStatus} onchange={() => loadVideos()}>
				<option value="">All Status</option>
				<option value="ready">Ready</option>
				<option value="failed">Failed</option>
				<option value="downloading">Downloading</option>
			</select>
			<select bind:value={filterCategory} onchange={() => loadVideos()}>
				<option value="">All Categories</option>
				{#each CATEGORIES as cat}
					<option value={cat}>{cat}</option>
				{/each}
			</select>
			<select bind:value={filterFeatured} onchange={() => loadVideos()}>
				<option value="">All</option>
				<option value="true">{t('featured')}</option>
			</select>
		</div>

		<!-- Video Table -->
		<div class="video-table">
			{#if loadingVideos}
				<p class="empty">{t('loading')}</p>
			{:else if videos.length === 0}
				<p class="empty">{t('noVideos')}</p>
			{:else}
				<table>
					<thead>
						<tr>
							<th>Title</th>
							<th>{t('source')}</th>
							<th>{t('category')}</th>
							<th>{t('featured')}</th>
							<th>Status</th>
							<th></th>
						</tr>
					</thead>
					<tbody>
						{#each videos as video (video.id)}
							<tr>
								<td class="td-title">
									<a href="/watch/{video.id}" target="_blank">{video.title || t('untitled')}</a>
									{#if video.channel}
										<span class="td-channel">{video.channel}</span>
									{/if}
								</td>
								<td>
									<span class="badge {video.source === 'ig' ? 'badge-ig' : 'badge-youtube'}">
										{video.source === 'ig' ? 'IG' : video.source === 'youtube' ? 'YT' : video.source}
									</span>
								</td>
								<td>
									<select
										value={video.category || ''}
										onchange={(e) => setCategory(video, (e.target as HTMLSelectElement).value)}
									>
										<option value="">{t('noCategory')}</option>
										{#each CATEGORIES as cat}
											<option value={cat}>{cat}</option>
										{/each}
									</select>
								</td>
								<td>
									<button
										class="star-btn"
										class:active={video.is_featured}
										onclick={() => toggleFeatured(video)}
									>
										{video.is_featured ? '★' : '☆'}
									</button>
								</td>
								<td>
									<span class="badge {video.status === 'ready' ? 'badge-ready' : video.status === 'failed' ? 'badge-ig' : 'badge-processing'}">
										{video.status}
									</span>
								</td>
								<td>
									<button class="btn btn-danger btn-sm" onclick={() => handleDelete(video)}>x</button>
								</td>
							</tr>
						{/each}
					</tbody>
				</table>
			{/if}
		</div>
	</div>
{/if}

<style>
	/* Login */
	.login-page {
		display: flex;
		align-items: center;
		justify-content: center;
		min-height: 60vh;
	}

	.loading-text {
		color: var(--text-dim);
		font-size: 14px;
	}

	.login-card {
		padding: 32px;
		text-align: center;
		max-width: 360px;
		width: 100%;
	}

	.login-card h1 {
		font-size: 24px;
		font-weight: 700;
		margin-bottom: 8px;
	}

	.login-card p {
		color: var(--text-dim);
		font-size: 14px;
		margin-bottom: 20px;
	}

	.login-card form {
		display: flex;
		gap: 8px;
	}

	.login-card input {
		flex: 1;
	}

	.error-msg {
		color: var(--danger);
		font-size: 13px;
		margin-top: 12px;
	}

	/* Admin page */
	.admin-page {
		max-width: 1100px;
		margin: 0 auto;
	}

	.admin-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: 24px;
	}

	.admin-header h1 {
		font-size: 24px;
		font-weight: 700;
	}

	/* Stats */
	.stats-grid {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
		gap: 12px;
		margin-bottom: 16px;
	}

	.stat-card {
		padding: 16px;
		text-align: center;
	}

	.stat-value {
		font-size: 28px;
		font-weight: 700;
		color: var(--accent);
	}

	.stat-label {
		font-size: 13px;
		color: var(--text-dim);
		margin-top: 4px;
	}

	.breakdown {
		display: flex;
		align-items: center;
		gap: 8px;
		margin-bottom: 24px;
		font-size: 13px;
	}

	.breakdown-label {
		color: var(--text-dim);
	}

	/* Filters */
	.filters {
		display: flex;
		gap: 8px;
		margin-bottom: 16px;
		flex-wrap: wrap;
	}

	.filters input {
		flex: 1;
		min-width: 160px;
		padding: 8px 12px;
		font-size: 14px;
	}

	.filters select {
		padding: 8px 12px;
		font-size: 13px;
		background: var(--bg-card);
		color: var(--text);
		border: 1px solid var(--border);
		border-radius: var(--radius-sm);
	}

	/* Table */
	.video-table {
		overflow-x: auto;
	}

	table {
		width: 100%;
		border-collapse: collapse;
		font-size: 14px;
	}

	th {
		text-align: left;
		padding: 10px 12px;
		border-bottom: 1px solid var(--border);
		color: var(--text-dim);
		font-size: 12px;
		font-weight: 600;
		text-transform: uppercase;
		letter-spacing: 0.5px;
	}

	td {
		padding: 10px 12px;
		border-bottom: 1px solid var(--border);
		vertical-align: middle;
	}

	tr:hover {
		background: var(--bg-hover);
	}

	.td-title {
		max-width: 300px;
	}

	.td-title a {
		font-weight: 600;
		display: block;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	.td-channel {
		font-size: 12px;
		color: var(--text-dim);
	}

	td select {
		padding: 4px 8px;
		font-size: 12px;
		background: var(--bg);
		color: var(--text);
		border: 1px solid var(--border);
		border-radius: var(--radius-sm);
	}

	.star-btn {
		font-size: 20px;
		color: var(--text-dim);
		background: none;
		border: none;
		cursor: pointer;
		padding: 4px;
		line-height: 1;
	}

	.star-btn.active {
		color: #f59e0b;
	}

	.btn-sm {
		padding: 4px 8px;
		font-size: 12px;
	}

	.btn-ghost {
		background: transparent;
		color: var(--text);
		border: 1px solid var(--border);
	}

	.empty {
		color: var(--text-dim);
		text-align: center;
		padding: 32px 0;
	}

	@media (max-width: 768px) {
		.stats-grid {
			grid-template-columns: repeat(2, 1fr);
		}

		.filters {
			flex-direction: column;
		}

		.td-title {
			max-width: 180px;
		}
	}
</style>
