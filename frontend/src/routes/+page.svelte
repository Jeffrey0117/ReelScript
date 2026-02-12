<script lang="ts">
	import { onMount } from 'svelte';
	import { processVideo, listVideos, connectWS, type Video } from '$lib/api';
	import { t } from '$lib/i18n';

	let url = $state('');
	let loading = $state(false);
	let error = $state('');
	let videos = $state<Video[]>([]);
	let progress = $state<Record<string, number>>({});

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
		<h2>{t('myVideos')}</h2>

		<div class="grid">
			{#each videos as video (video.id)}
				{@const isReady = video.status === 'ready'}
				<a
					href={isReady ? `/watch/${video.id}` : undefined}
					class="video-card card"
					class:disabled={!isReady}
				>
					<div class="video-card-header">
						<span class="badge {video.source === 'ig' ? 'badge-ig' : 'badge-youtube'}">
							{video.source === 'ig' ? 'IG' : video.source === 'youtube' ? 'YT' : '?'}
						</span>
						<span class="badge {statusBadgeClass(video.status)}">{statusLabel(video.status)}</span>
					</div>

					<h3 class="video-title">{video.title || t('untitled')}</h3>

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
				</a>
			{/each}
		</div>
	</section>
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

	.video-list h2 {
		font-size: 18px;
		font-weight: 600;
		margin-bottom: 16px;
	}

	.grid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
		gap: 16px;
	}

	.video-card {
		display: block;
		transition: border-color 0.15s, transform 0.15s;
		color: inherit;
	}

	.video-card:hover:not(.disabled) {
		border-color: var(--accent);
		transform: translateY(-2px);
	}

	.video-card.disabled {
		opacity: 0.7;
		cursor: default;
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
	}

	.video-meta {
		display: flex;
		gap: 12px;
		font-size: 13px;
		color: var(--text-dim);
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
	}
</style>
