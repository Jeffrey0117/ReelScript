<script lang="ts">
	import { onMount } from 'svelte';
	import {
		adminStats,
		adminListVideos,
		adminUpdateVideo,
		adminDeleteVideo,
		adminListUsers,
		adminGetUser,
		thumbnailUrl,
		type AdminStats,
		type AdminVideo,
		type AdminUser,
		type AdminUserDetail,
	} from '$lib/api';
	import { t } from '$lib/i18n';
	import { onAuthChange, type AdmanUser } from '$lib/auth';

	const CATEGORIES = ['business', 'daily', 'tech', 'entertainment', 'motivation', 'education'];

	// Auth state
	let authMode = $state<'checking' | 'jwt' | 'password' | 'none'>('checking');
	let adminKey = $state('');
	let authenticated = $state(false);
	let authError = $state('');

	// Tab
	let activeTab = $state<'overview' | 'videos' | 'members'>('overview');

	// Stats
	let stats = $state<AdminStats | null>(null);
	let loadingStats = $state(false);

	// Videos
	let videos = $state<AdminVideo[]>([]);
	let loadingVideos = $state(false);
	let filterStatus = $state('');
	let filterCategory = $state('');
	let filterFeatured = $state('');
	let filterSearch = $state('');

	// Users
	let users = $state<AdminUser[]>([]);
	let loadingUsers = $state(false);
	let userSearch = $state('');
	let userPlanFilter = $state('');
	let userSort = $state('');
	let selectedUser = $state<AdminUserDetail | null>(null);
	let loadingUserDetail = $state(false);

	function getAdminKey(): string {
		return authMode === 'password' ? adminKey : '';
	}

	onMount(() => {
		const unsub = onAuthChange(async (user) => {
			if (user && user.role === 'admin') {
				authMode = 'jwt';
				await tryJwtAuth();
			} else if (authMode === 'checking') {
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
		try {
			const params: Record<string, string> = {};
			if (filterStatus) params.status = filterStatus;
			if (filterCategory) params.category = filterCategory;
			if (filterFeatured) params.featured = filterFeatured;
			if (filterSearch) params.search = filterSearch;
			videos = await adminListVideos(getAdminKey(), Object.keys(params).length > 0 ? params : undefined);
		} finally {
			loadingVideos = false;
		}
	}

	async function loadUsers() {
		loadingUsers = true;
		try {
			const params: Record<string, string> = {};
			if (userSearch) params.search = userSearch;
			if (userPlanFilter) params.plan = userPlanFilter;
			if (userSort) params.sort = userSort;
			users = await adminListUsers(getAdminKey(), Object.keys(params).length > 0 ? params : undefined);
		} finally {
			loadingUsers = false;
		}
	}

	async function showUserDetail(userId: string) {
		loadingUserDetail = true;
		try {
			selectedUser = await adminGetUser(getAdminKey(), userId);
		} finally {
			loadingUserDetail = false;
		}
	}

	function closeUserDetail() {
		selectedUser = null;
	}

	async function switchTab(tab: 'overview' | 'videos' | 'members') {
		activeTab = tab;
		if (tab === 'members' && users.length === 0) {
			await loadUsers();
		}
	}

	async function toggleFeatured(video: AdminVideo) {
		await adminUpdateVideo(getAdminKey(), video.id, { is_featured: !video.is_featured });
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
		await adminUpdateVideo(getAdminKey(), video.id, { category: cat ?? '' });
		videos = videos.map((v) =>
			v.id === video.id ? { ...v, category: cat ?? null } : v
		);
	}

	async function handleDelete(video: AdminVideo) {
		if (!confirm(`Delete "${video.title}"?`)) return;
		await adminDeleteVideo(getAdminKey(), video.id);
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

	function formatDate(iso: string | null): string {
		if (!iso) return '-';
		const d = new Date(iso);
		return d.toLocaleDateString('zh-TW', { month: 'short', day: 'numeric' }) + ' ' + d.toLocaleTimeString('zh-TW', { hour: '2-digit', minute: '2-digit' });
	}

	function formatCredits(used: number, limit: number): string {
		if (limit === -1) return `${used} / ${t('unlimited')}`;
		return `${used} / ${limit}`;
	}
</script>

<svelte:head>
	<title>{t('admin')} - ReelScript</title>
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

		<!-- Tab Bar -->
		<div class="tab-bar">
			<button
				class="tab-btn"
				class:active={activeTab === 'overview'}
				onclick={() => switchTab('overview')}
			>{t('overview')}</button>
			<button
				class="tab-btn"
				class:active={activeTab === 'videos'}
				onclick={() => switchTab('videos')}
			>{t('allVideos')}</button>
			<button
				class="tab-btn"
				class:active={activeTab === 'members'}
				onclick={() => switchTab('members')}
			>{t('members')}</button>
		</div>

		<!-- ═══ Overview Tab ═══ -->
		{#if activeTab === 'overview'}
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

				<!-- User stats row -->
				<div class="stats-grid">
					<div class="stat-card card">
						<div class="stat-value">{stats.total_users}</div>
						<div class="stat-label">{t('totalUsers')}</div>
					</div>
					<div class="stat-card card">
						<div class="stat-value">{stats.active_users_30d}</div>
						<div class="stat-label">{t('activeUsers30d')}</div>
					</div>
					<div class="stat-card card">
						<div class="stat-value">{stats.plan_breakdown?.free ?? 0}</div>
						<div class="stat-label">{t('freeUsers')}</div>
					</div>
					<div class="stat-card card">
						<div class="stat-value">{(stats.plan_breakdown?.pro ?? 0) + (stats.plan_breakdown?.unlimited ?? 0)}</div>
						<div class="stat-label">{t('proUsers')}</div>
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

		<!-- ═══ Videos Tab ═══ -->
		{:else if activeTab === 'videos'}
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
								<th>{t('uploader')}</th>
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
									<td class="td-uploader">
										{#if video.uploader}
											<button
												class="uploader-link"
												onclick={() => { switchTab('members'); showUserDetail(video.uploader!.id); }}
											>
												{video.uploader.name || video.uploader.email || video.uploader.id.slice(0, 8)}
											</button>
										{:else}
											<span class="text-dim">-</span>
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

		<!-- ═══ Members Tab ═══ -->
		{:else if activeTab === 'members'}
			{#if selectedUser}
				<!-- User Detail View -->
				<div class="user-detail">
					<button class="btn btn-ghost btn-sm" onclick={closeUserDetail}>&larr; {t('back')}</button>

					{#if loadingUserDetail}
						<p class="empty">{t('loading')}</p>
					{:else}
						<div class="user-detail-header">
							{#if selectedUser.user.avatar}
								<img class="user-avatar-lg" src={selectedUser.user.avatar} alt="" />
							{/if}
							<div>
								<h2>{selectedUser.user.name || selectedUser.user.email || selectedUser.user.id}</h2>
								<p class="text-dim">{selectedUser.user.email || ''}</p>
								<div class="user-meta">
									<span class="badge badge-plan">{selectedUser.plan}</span>
									<span class="text-dim">{t('firstSeen')}: {formatDate(selectedUser.user.first_seen_at)}</span>
									<span class="text-dim">{t('lastSeen')}: {formatDate(selectedUser.user.last_seen_at)}</span>
								</div>
							</div>
						</div>

						{#if selectedUser.invite}
							<div class="detail-section">
								<h3>{t('inviteCode')}</h3>
								<p><code>{selectedUser.invite.code}</code> — {t('redeemed')}: {selectedUser.invite.redeemed_count}</p>
							</div>
						{/if}

						{#if selectedUser.quota_history.length > 0}
							<div class="detail-section">
								<h3>{t('quotaHistory')}</h3>
								<table class="detail-table">
									<thead>
										<tr>
											<th>{t('period')}</th>
											<th>{t('used')}</th>
											<th>{t('bonus')}</th>
										</tr>
									</thead>
									<tbody>
										{#each selectedUser.quota_history as q}
											<tr>
												<td>{q.period}</td>
												<td>{q.credits_used}</td>
												<td>{q.bonus_credits}</td>
											</tr>
										{/each}
									</tbody>
								</table>
							</div>
						{/if}

						{#if selectedUser.videos.length > 0}
							<div class="detail-section">
								<h3>{t('allVideos')} ({selectedUser.videos.length})</h3>
								<div class="user-videos-grid">
									{#each selectedUser.videos as video}
										<a href="/watch/{video.id}" target="_blank" class="user-video-card card">
											{#if video.thumbnail}
												<img src={thumbnailUrl(video.thumbnail)} alt="" class="user-video-thumb" />
											{/if}
											<div class="user-video-info">
												<span class="user-video-title">{video.title || t('untitled')}</span>
												<span class="badge {video.status === 'ready' ? 'badge-ready' : video.status === 'failed' ? 'badge-ig' : 'badge-processing'}">{video.status}</span>
											</div>
										</a>
									{/each}
								</div>
							</div>
						{/if}
					{/if}
				</div>
			{:else}
				<!-- Users List -->
				<div class="filters">
					<input
						type="text"
						placeholder={t('searchUsers')}
						bind:value={userSearch}
						oninput={() => loadUsers()}
					/>
					<select bind:value={userPlanFilter} onchange={() => loadUsers()}>
						<option value="">{t('allPlans')}</option>
						<option value="free">Free</option>
						<option value="pro">Pro</option>
						<option value="unlimited">Unlimited</option>
					</select>
					<select bind:value={userSort} onchange={() => loadUsers()}>
						<option value="">{t('lastSeen')}</option>
						<option value="videos">{t('videoCount')}</option>
						<option value="credits">{t('credits')}</option>
					</select>
				</div>

				<div class="video-table">
					{#if loadingUsers}
						<p class="empty">{t('loading')}</p>
					{:else if users.length === 0}
						<p class="empty">{t('noUsers')}</p>
					{:else}
						<table>
							<thead>
								<tr>
									<th>{t('name')}</th>
									<th>{t('email')}</th>
									<th>{t('plan')}</th>
									<th>{t('videoCount')}</th>
									<th>{t('credits')}</th>
									<th>{t('lastSeen')}</th>
								</tr>
							</thead>
							<tbody>
								{#each users as user (user.id)}
									<tr class="clickable-row" onclick={() => showUserDetail(user.id)}>
										<td class="td-user-name">
											<div class="user-name-cell">
												{#if user.avatar}
													<img class="user-avatar-sm" src={user.avatar} alt="" />
												{/if}
												<span>{user.name || '-'}</span>
											</div>
										</td>
										<td>{user.email || '-'}</td>
										<td>
											<span class="badge badge-plan">{user.plan}</span>
										</td>
										<td>{user.video_count}</td>
										<td>{formatCredits(user.credits_used, user.credits_limit)}</td>
										<td>{formatDate(user.last_seen_at)}</td>
									</tr>
								{/each}
							</tbody>
						</table>
					{/if}
				</div>
			{/if}
		{/if}
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
		margin-bottom: 16px;
	}

	.admin-header h1 {
		font-size: 24px;
		font-weight: 700;
	}

	/* Tab Bar */
	.tab-bar {
		display: flex;
		gap: 0;
		border-bottom: 1px solid var(--border);
		margin-bottom: 20px;
	}

	.tab-btn {
		padding: 10px 20px;
		font-size: 14px;
		font-weight: 600;
		color: var(--text-dim);
		background: none;
		border: none;
		border-bottom: 2px solid transparent;
		cursor: pointer;
		transition: color 0.15s, border-color 0.15s;
	}

	.tab-btn:hover {
		color: var(--text);
	}

	.tab-btn.active {
		color: var(--accent);
		border-bottom-color: var(--accent);
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

	.clickable-row {
		cursor: pointer;
	}

	.td-title {
		max-width: 260px;
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

	.td-uploader {
		max-width: 120px;
	}

	.uploader-link {
		background: none;
		border: none;
		color: var(--accent);
		cursor: pointer;
		font-size: 13px;
		padding: 0;
		text-decoration: underline;
		text-underline-offset: 2px;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
		display: block;
		max-width: 120px;
	}

	.uploader-link:hover {
		opacity: 0.8;
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

	.text-dim {
		color: var(--text-dim);
		font-size: 13px;
	}

	/* Badge plan */
	.badge-plan {
		background: var(--bg-hover);
		color: var(--text);
		padding: 2px 8px;
		border-radius: 10px;
		font-size: 12px;
		font-weight: 600;
		text-transform: uppercase;
	}

	/* User list */
	.td-user-name {
		max-width: 180px;
	}

	.user-name-cell {
		display: flex;
		align-items: center;
		gap: 8px;
	}

	.user-avatar-sm {
		width: 24px;
		height: 24px;
		border-radius: 50%;
		object-fit: cover;
		flex-shrink: 0;
	}

	/* User detail */
	.user-detail {
		animation: fadeIn 0.15s ease;
	}

	@keyframes fadeIn {
		from { opacity: 0; transform: translateY(4px); }
		to { opacity: 1; transform: translateY(0); }
	}

	.user-detail-header {
		display: flex;
		align-items: center;
		gap: 16px;
		margin: 20px 0;
	}

	.user-detail-header h2 {
		font-size: 20px;
		font-weight: 700;
		margin-bottom: 4px;
	}

	.user-avatar-lg {
		width: 56px;
		height: 56px;
		border-radius: 50%;
		object-fit: cover;
		flex-shrink: 0;
	}

	.user-meta {
		display: flex;
		align-items: center;
		gap: 12px;
		margin-top: 6px;
		flex-wrap: wrap;
	}

	.detail-section {
		margin-bottom: 24px;
	}

	.detail-section h3 {
		font-size: 15px;
		font-weight: 700;
		margin-bottom: 10px;
		color: var(--text);
	}

	.detail-section code {
		background: var(--bg-hover);
		padding: 2px 8px;
		border-radius: 4px;
		font-size: 14px;
	}

	.detail-table {
		width: 100%;
		max-width: 400px;
	}

	/* User videos grid */
	.user-videos-grid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
		gap: 12px;
	}

	.user-video-card {
		display: block;
		padding: 0;
		overflow: hidden;
		text-decoration: none;
		color: var(--text);
		transition: transform 0.1s;
	}

	.user-video-card:hover {
		transform: translateY(-2px);
	}

	.user-video-thumb {
		width: 100%;
		aspect-ratio: 16/9;
		object-fit: cover;
		display: block;
	}

	.user-video-info {
		padding: 8px 12px;
		display: flex;
		justify-content: space-between;
		align-items: center;
		gap: 8px;
	}

	.user-video-title {
		font-size: 13px;
		font-weight: 600;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
		flex: 1;
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

		.user-videos-grid {
			grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
		}

		.user-detail-header {
			flex-direction: column;
			align-items: flex-start;
		}
	}
</style>
