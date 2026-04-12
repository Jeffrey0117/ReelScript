<script lang="ts">
	import { onMount } from 'svelte';
	import { publicVideos, thumbnailUrl, type PublicVideo } from '$lib/api';
	import { t } from '$lib/i18n';

	let videos = $state<PublicVideo[]>([]);
	let loading = $state(true);

	onMount(async () => {
		try {
			const data = await publicVideos();
			videos = data.videos.filter((v) => v.hasTranscript);
		} catch {
			// empty
		} finally {
			loading = false;
		}
	});

	function formatDuration(seconds: number | null): string {
		if (!seconds) return '';
		const m = Math.floor(seconds / 60);
		const s = Math.floor(seconds % 60);
		return `${m}:${s.toString().padStart(2, '0')}`;
	}

	function formatDate(iso: string | null): string {
		if (!iso) return '';
		const d = new Date(iso);
		return d.toLocaleDateString('zh-TW', { year: 'numeric', month: 'short', day: 'numeric' });
	}
</script>

<svelte:head>
	<title>{t('blog')} - ReelScript</title>
</svelte:head>

<section class="blog-page">
	<h1 class="blog-heading">{t('blogTitle')}</h1>

	{#if loading}
		<div class="blog-grid">
			{#each Array(6) as _}
				<div class="blog-card skeleton">
					<div class="skeleton-thumb"></div>
					<div class="skeleton-body">
						<div class="skeleton-line wide"></div>
						<div class="skeleton-line narrow"></div>
					</div>
				</div>
			{/each}
		</div>
	{:else if videos.length === 0}
		<p class="blog-empty">{t('blogEmpty')}</p>
	{:else}
		<div class="blog-grid">
			{#each videos as video (video.id)}
				<a href="/blog/{video.id}" class="blog-card">
					{#if video.thumbnail}
						<div class="blog-thumb">
							<img src={thumbnailUrl(video.thumbnail)} alt="" loading="lazy" />
							{#if video.duration}
								<span class="blog-duration">{formatDuration(video.duration)}</span>
							{/if}
						</div>
					{:else}
						<div class="blog-thumb blog-thumb-empty">
							<svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" opacity="0.3">
								<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
								<polyline points="14 2 14 8 20 8"/>
								<line x1="16" y1="13" x2="8" y2="13"/>
								<line x1="16" y1="17" x2="8" y2="17"/>
							</svg>
						</div>
					{/if}
					<div class="blog-card-body">
						<div class="blog-meta">
							<span class="badge {video.source === 'ig' ? 'badge-ig' : 'badge-youtube'}">
								{video.source === 'ig' ? 'IG' : 'YT'}
							</span>
							{#if video.channel}
								<span class="blog-channel">{video.channel}</span>
							{/if}
						</div>
						<h2 class="blog-card-title">{video.title || t('untitled')}</h2>
						{#if video.createdAt}
							<span class="blog-date">{formatDate(video.createdAt)}</span>
						{/if}
					</div>
				</a>
			{/each}
		</div>
	{/if}
</section>

<style>
	.blog-page {
		padding-top: 8px;
	}

	.blog-heading {
		font-size: 24px;
		font-weight: 700;
		margin-bottom: 24px;
		letter-spacing: -0.5px;
	}

	.blog-empty {
		color: var(--text-dim);
		text-align: center;
		padding: 48px 0;
	}

	.blog-grid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
		gap: 20px;
		padding-bottom: 48px;
	}

	.blog-card {
		background: var(--bg-card);
		border: 1px solid var(--border);
		border-radius: var(--radius);
		overflow: hidden;
		transition: border-color 0.15s, transform 0.15s, box-shadow 0.15s;
		color: inherit;
		text-decoration: none;
		display: flex;
		flex-direction: column;
	}

	.blog-card:hover {
		border-color: var(--accent);
		transform: translateY(-2px);
		box-shadow: 0 4px 20px rgba(99, 102, 241, 0.1);
	}

	.blog-thumb {
		position: relative;
		aspect-ratio: 16 / 9;
		background: var(--border);
		overflow: hidden;
	}

	.blog-thumb img {
		width: 100%;
		height: 100%;
		object-fit: cover;
		display: block;
	}

	.blog-thumb-empty {
		display: flex;
		align-items: center;
		justify-content: center;
	}

	.blog-duration {
		position: absolute;
		bottom: 8px;
		right: 8px;
		background: rgba(0, 0, 0, 0.75);
		color: #fff;
		font-size: 12px;
		font-weight: 600;
		padding: 2px 8px;
		border-radius: 4px;
		font-variant-numeric: tabular-nums;
	}

	.blog-card-body {
		padding: 16px 20px 20px;
		flex: 1;
		display: flex;
		flex-direction: column;
	}

	.blog-meta {
		display: flex;
		align-items: center;
		gap: 8px;
		margin-bottom: 8px;
	}

	.blog-channel {
		font-size: 12px;
		color: var(--text-dim);
	}

	.blog-card-title {
		font-size: 16px;
		font-weight: 600;
		line-height: 1.4;
		margin-bottom: 8px;
		display: -webkit-box;
		-webkit-line-clamp: 2;
		-webkit-box-orient: vertical;
		overflow: hidden;
	}

	.blog-date {
		font-size: 12px;
		color: var(--text-dim);
		margin-top: auto;
	}

	/* Skeleton */
	.blog-card.skeleton {
		pointer-events: none;
	}

	.skeleton-thumb {
		aspect-ratio: 16 / 9;
		background: var(--border);
		animation: shimmer 1.5s infinite;
	}

	.skeleton-body {
		padding: 16px 20px 20px;
	}

	.skeleton-line {
		height: 14px;
		background: var(--border);
		border-radius: 4px;
		margin-bottom: 10px;
		animation: shimmer 1.5s infinite;
	}

	.skeleton-line.wide {
		width: 80%;
	}

	.skeleton-line.narrow {
		width: 40%;
	}

	@keyframes shimmer {
		0% { opacity: 0.5; }
		50% { opacity: 1; }
		100% { opacity: 0.5; }
	}

	@media (max-width: 640px) {
		.blog-heading {
			font-size: 20px;
		}

		.blog-grid {
			grid-template-columns: 1fr;
			gap: 16px;
		}
	}
</style>
