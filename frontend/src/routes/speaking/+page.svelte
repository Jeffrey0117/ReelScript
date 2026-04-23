<script lang="ts">
	import { onMount } from 'svelte';
	import {
		listSpeaking,
		uploadSpeaking,
		deleteSpeaking,
		connectWS,
		type SpeakingSession,
	} from '$lib/api';
	import { goto } from '$app/navigation';
	import { t } from '$lib/i18n';
	import { onAuthChange, login } from '$lib/auth';

	let sessions = $state<SpeakingSession[]>([]);
	let loading = $state(true);
	let uploading = $state(false);
	let error = $state('');
	let dragOver = $state(false);
	let isLoggedIn = $state(false);

	onMount(async () => {
		sessions = await listSpeaking().catch(() => []);
		loading = false;

		onAuthChange(async (user) => {
			isLoggedIn = !!user;
			if (user) {
				sessions = await listSpeaking().catch(() => []);
			}
		});

		connectWS((msg: Record<string, unknown>) => {
			const type = msg.type as string;
			const data = msg.data as Record<string, unknown>;

			if (
				type === 'speaking_completed' ||
				type === 'speaking_error'
			) {
				listSpeaking().then((s) => (sessions = s));
			}

			if (type === 'speaking_transcribe_started' || type === 'speaking_analyze_started') {
				const sessionId = data?.session_id as string;
				if (sessionId) {
					const newStatus = type === 'speaking_transcribe_started' ? 'transcribing' : 'analyzing';
					sessions = sessions.map((s) =>
						s.id === sessionId ? { ...s, status: newStatus } : s
					);
				}
			}
		});
	});

	async function handleFileSelect(files: FileList | null) {
		if (!files || files.length === 0) return;
		const file = files[0];

		uploading = true;
		error = '';

		try {
			const result = await uploadSpeaking(file);
			sessions = [
				{
					id: result.session_id,
					title: file.name.replace(/\.[^.]+$/, '') || 'Speaking Session',
					duration: null,
					status: result.status,
					error_message: null,
					created_at: new Date().toISOString(),
					overall_score: null,
				},
				...sessions,
			];
		} catch (e: unknown) {
			const err = e as Error & { status?: number };
			if (err.status === 401) {
				error = t('loginRequired');
				login();
			} else {
				error = err.message || 'Upload failed';
			}
		} finally {
			uploading = false;
		}
	}

	function handleDrop(e: DragEvent) {
		e.preventDefault();
		dragOver = false;
		handleFileSelect(e.dataTransfer?.files ?? null);
	}

	function handleDragOver(e: DragEvent) {
		e.preventDefault();
		dragOver = true;
	}

	function handleDragLeave() {
		dragOver = false;
	}

	async function handleDelete(sessionId: string) {
		if (!confirm(t('confirmDelete'))) return;
		try {
			await deleteSpeaking(sessionId);
			sessions = sessions.filter((s) => s.id !== sessionId);
		} catch {
			// ignore
		}
	}

	function statusLabel(status: string): string {
		const map: Record<string, () => string> = {
			uploading: () => t('processing'),
			transcribing: () => t('statusTranscribing'),
			analyzing: () => t('statusAnalyzing'),
			ready: () => t('statusReady'),
			failed: () => t('statusFailed'),
		};
		return (map[status] ?? (() => status))();
	}

	function statusClass(status: string): string {
		if (status === 'ready') return 'badge-ready';
		if (status === 'failed') return 'badge-ig';
		return 'badge-processing';
	}

	function formatDate(iso: string | null): string {
		if (!iso) return '';
		const d = new Date(iso);
		return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
	}

	function formatDuration(seconds: number | null): string {
		if (!seconds) return '';
		const m = Math.floor(seconds / 60);
		const s = Math.floor(seconds % 60);
		return `${m}:${s.toString().padStart(2, '0')}`;
	}
</script>

<svelte:head>
	<title>{t('speakingCoach')} - ReelScript</title>
</svelte:head>

<section class="hero">
	<div class="hero-icon">
		<svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
			<path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/>
			<path d="M19 10v2a7 7 0 0 1-14 0v-2"/>
			<line x1="12" y1="19" x2="12" y2="23"/>
			<line x1="8" y1="23" x2="16" y2="23"/>
		</svg>
	</div>
	<h1>{t('speakingCoach')}</h1>
	<p class="hero-subtitle">{t('dragDropHint')}</p>

	<!-- svelte-ignore a11y_no_static_element_interactions -->
	<div
		class="upload-zone"
		class:drag-over={dragOver}
		class:uploading
		ondrop={handleDrop}
		ondragover={handleDragOver}
		ondragleave={handleDragLeave}
		onclick={() => {
			if (!uploading) document.getElementById('file-input')?.click();
		}}
		onkeydown={(e) => {
			if (e.key === 'Enter' || e.key === ' ') {
				e.preventDefault();
				if (!uploading) document.getElementById('file-input')?.click();
			}
		}}
		role="button"
		tabindex="0"
	>
		{#if uploading}
			<svg class="spinner" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
				<path d="M12 2a10 10 0 0 1 10 10"/>
			</svg>
			<span>{t('processing')}</span>
		{:else}
			<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
				<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
				<polyline points="17 8 12 3 7 8"/>
				<line x1="12" y1="3" x2="12" y2="15"/>
			</svg>
			<span>{t('uploadAudio')}</span>
		{/if}
		<input
			id="file-input"
			type="file"
			accept="audio/*,video/*"
			onchange={(e) => handleFileSelect((e.target as HTMLInputElement).files)}
			style="display: none"
		/>
	</div>

	<div class="upload-meta">
		<span class="meta-text">{t('uploadLimit')}</span>
		<span class="meta-dot"></span>
		<span class="meta-text">{t('speakingQuotaCost')}</span>
	</div>

	{#if error}
		<p class="error-msg">{error}</p>
	{/if}
</section>

{#if loading}
	<section class="session-list">
		<h2>{t('sessions')}</h2>
		<div class="session-items">
			{#each Array(3) as _}
				<div class="session-card card skeleton-card">
					<div class="skeleton-line"></div>
					<div class="skeleton-line short"></div>
				</div>
			{/each}
		</div>
	</section>
{:else if sessions.length > 0}
	<section class="session-list">
		<h2>{t('sessions')}</h2>
		<div class="session-items">
			{#each sessions as session (session.id)}
				{@const isReady = session.status === 'ready'}
				<div class="session-card card" class:clickable={isReady}>
					{#if isReady}
						<a href="/speaking/{session.id}" class="card-link"></a>
					{/if}
					<div class="session-body">
						<div class="session-top">
							<h3 class="session-title">{session.title || t('recording')}</h3>
							{#if isReady && session.overall_score}
								<span class="score-badge">{session.overall_score}</span>
							{/if}
						</div>
						<div class="session-meta">
							<span class="badge {statusClass(session.status)}">{statusLabel(session.status)}</span>
							{#if session.duration}
								<span class="meta-duration">{formatDuration(session.duration)}</span>
							{/if}
							<span class="meta-date">{formatDate(session.created_at)}</span>
						</div>
					</div>
					{#if session.status === 'failed'}
						<div class="session-actions">
							{#if session.error_message}
								<span class="error-text">{session.error_message}</span>
							{/if}
							<button
								class="btn btn-ghost btn-sm btn-danger-ghost"
								onclick={(e) => {
									e.stopPropagation();
									handleDelete(session.id);
								}}
							>
								{t('delete')}
							</button>
						</div>
					{/if}
				</div>
			{/each}
		</div>
	</section>
{:else}
	<section class="empty-state">
		<p>{t('noSessions')}</p>
	</section>
{/if}

<style>
	.hero {
		text-align: center;
		padding: 56px 0 32px;
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
		margin-bottom: 28px;
	}

	.upload-zone {
		max-width: 480px;
		margin: 0 auto;
		padding: 32px;
		border: 2px dashed var(--border);
		border-radius: var(--radius);
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 12px;
		cursor: pointer;
		transition: border-color 0.2s, background 0.2s;
		color: var(--text-dim);
		font-size: 15px;
		font-weight: 500;
	}

	.upload-zone:hover {
		border-color: var(--accent);
		background: color-mix(in srgb, var(--accent) 4%, transparent);
		color: var(--accent);
	}

	.upload-zone.drag-over {
		border-color: var(--accent);
		background: color-mix(in srgb, var(--accent) 8%, transparent);
		color: var(--accent);
	}

	.upload-zone.uploading {
		pointer-events: none;
		opacity: 0.7;
	}

	.upload-meta {
		display: flex;
		align-items: center;
		justify-content: center;
		gap: 8px;
		margin-top: 14px;
	}

	.meta-text {
		font-size: 13px;
		color: var(--text-dim);
	}

	.meta-dot {
		width: 3px;
		height: 3px;
		border-radius: 50%;
		background: var(--text-dim);
	}

	.error-msg {
		color: var(--danger);
		font-size: 14px;
		margin-top: 14px;
	}

	.spinner {
		animation: spin 0.8s linear infinite;
	}

	@keyframes spin {
		to { transform: rotate(360deg); }
	}

	.session-list {
		margin-top: 16px;
	}

	.session-list h2 {
		font-size: 18px;
		font-weight: 600;
		margin-bottom: 16px;
	}

	.session-items {
		display: flex;
		flex-direction: column;
		gap: 8px;
	}

	.session-card {
		position: relative;
		padding: 16px 20px;
		transition: border-color 0.15s;
	}

	.session-card.clickable {
		cursor: pointer;
	}

	.session-card.clickable:hover {
		border-color: var(--accent);
	}

	.card-link {
		position: absolute;
		inset: 0;
		z-index: 1;
	}

	.session-body {
		display: flex;
		flex-direction: column;
		gap: 8px;
	}

	.session-top {
		display: flex;
		justify-content: space-between;
		align-items: center;
		gap: 12px;
	}

	.session-title {
		font-size: 15px;
		font-weight: 600;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
		flex: 1;
		min-width: 0;
	}

	.score-badge {
		flex-shrink: 0;
		display: inline-flex;
		align-items: center;
		justify-content: center;
		width: 36px;
		height: 36px;
		border-radius: 50%;
		background: color-mix(in srgb, var(--accent) 12%, transparent);
		color: var(--accent);
		font-size: 14px;
		font-weight: 700;
	}

	.session-meta {
		display: flex;
		align-items: center;
		gap: 8px;
	}

	.meta-duration {
		font-size: 12px;
		color: var(--text-dim);
	}

	.meta-date {
		font-size: 12px;
		color: var(--text-dim);
	}

	.session-actions {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 8px;
		margin-top: 8px;
		position: relative;
		z-index: 2;
	}

	.error-text {
		font-size: 12px;
		color: var(--text-dim);
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
		flex: 1;
		min-width: 0;
	}

	.btn-danger-ghost {
		color: var(--danger);
		border-color: var(--danger);
	}

	.btn-danger-ghost:hover {
		background: color-mix(in srgb, var(--danger) 10%, transparent);
	}

	.empty-state {
		text-align: center;
		padding: 48px 0;
		color: var(--text-dim);
		font-size: 15px;
	}

	.skeleton-card {
		padding: 20px;
	}

	.skeleton-line {
		height: 14px;
		background: var(--border);
		border-radius: 4px;
		animation: shimmer 1.5s infinite;
		margin-bottom: 10px;
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

		.hero h1 {
			font-size: 22px;
		}

		.upload-zone {
			padding: 24px;
		}
	}
</style>
