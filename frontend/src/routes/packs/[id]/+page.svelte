<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import { t } from '$lib/i18n';
	import { publicPack, thumbnailUrl, type PackVideo } from '$lib/api';

	let name = $state('');
	let description = $state<string | null>(null);
	let isOfficial = $state(false);
	let videos = $state<PackVideo[]>([]);
	let loading = $state(true);
	let notFound = $state(false);

	onMount(async () => {
		try {
			const pack = await publicPack($page.params.id);
			name = pack.name;
			description = pack.description;
			isOfficial = pack.is_official;
			videos = pack.videos;
		} catch {
			notFound = true;
		}
		loading = false;
	});

	function formatDuration(seconds: number | null): string {
		if (!seconds) return '';
		const m = Math.floor(seconds / 60);
		const s = Math.floor(seconds % 60);
		return `${m}:${s.toString().padStart(2, '0')}`;
	}
</script>

<svelte:head>
	<title>{name || t('packsTitle')} - ReelScript</title>
</svelte:head>

<a href="/packs" class="back-link">← {t('backToPacks')}</a>

{#if loading}
	<p class="empty">{t('loading')}</p>
{:else if notFound}
	<p class="empty">{t('noPacks')}</p>
{:else}
	<section class="pack-head">
		<div class="title-row">
			<h1>{name}</h1>
			{#if isOfficial}
				<span class="official-badge">{t('officialBadge')}</span>
			{/if}
		</div>
		{#if description}
			<p class="desc">{description}</p>
		{/if}
		<p class="meta">{videos.length} {t('packVideoCount')}</p>
	</section>

	<div class="video-list">
		{#each videos as v (v.id)}
			<a class="card video-row" href="/watch/{v.id}">
				{#if v.thumbnail}
					<div class="thumb">
						<img src={thumbnailUrl(v.thumbnail)} alt="" loading="lazy" />
						{#if v.duration}
							<span class="duration">{formatDuration(v.duration)}</span>
						{/if}
					</div>
				{/if}
				<div class="row-body">
					<h3>{v.title || t('untitled')}</h3>
					<div class="row-meta">
						<span class="badge {v.source === 'ig' ? 'badge-ig' : 'badge-youtube'}">
							{v.source === 'ig' ? 'IG' : v.source === 'youtube' ? 'YT' : '?'}
						</span>
						{#if v.channel}
							<span class="channel">{v.channel}</span>
						{/if}
					</div>
				</div>
			</a>
		{/each}
	</div>
{/if}

<style>
	.back-link {
		display: inline-block;
		font-size: 13.5px;
		color: var(--text-dim) !important;
		margin: 24px 0 8px;
		text-decoration: none;
	}

	.back-link:hover {
		color: var(--text) !important;
	}

	.pack-head {
		margin: 8px 0 24px;
	}

	.title-row {
		display: flex;
		align-items: center;
		gap: 10px;
	}

	.pack-head h1 {
		font-size: 26px;
		font-weight: 700;
		letter-spacing: -0.5px;
	}

	.official-badge {
		font-size: 11px;
		font-weight: 700;
		letter-spacing: 0.3px;
		color: #fff;
		background: var(--accent);
		border-radius: 6px;
		padding: 3px 8px;
	}

	.desc {
		color: var(--text-dim);
		font-size: 14.5px;
		line-height: 1.6;
		margin-top: 8px;
		max-width: 640px;
	}

	.meta {
		color: var(--text-dim);
		font-size: 13px;
		margin-top: 8px;
	}

	.video-list {
		display: flex;
		flex-direction: column;
		gap: 10px;
		padding-bottom: 48px;
	}

	.video-row {
		display: flex;
		gap: 14px;
		padding: 12px;
		text-decoration: none;
		color: var(--text) !important;
		transition: border-color 0.2s, transform 0.15s;
	}

	.video-row:hover {
		border-color: color-mix(in srgb, var(--accent) 40%, var(--border));
		transform: translateY(-1px);
	}

	.thumb {
		position: relative;
		flex-shrink: 0;
		width: 140px;
		aspect-ratio: 16 / 9;
		border-radius: var(--radius-sm);
		overflow: hidden;
		background: var(--bg-hover);
	}

	.thumb img {
		width: 100%;
		height: 100%;
		object-fit: cover;
		display: block;
	}

	.duration {
		position: absolute;
		bottom: 6px;
		right: 6px;
		font-size: 11px;
		font-weight: 600;
		color: #fff;
		background: rgba(0, 0, 0, 0.7);
		border-radius: 4px;
		padding: 1px 5px;
	}

	.row-body {
		display: flex;
		flex-direction: column;
		gap: 8px;
		justify-content: center;
		min-width: 0;
	}

	.row-body h3 {
		font-size: 15px;
		font-weight: 600;
		letter-spacing: -0.2px;
	}

	.row-meta {
		display: flex;
		align-items: center;
		gap: 8px;
	}

	.channel {
		font-size: 12.5px;
		color: var(--text-dim);
	}

	.empty {
		color: var(--text-dim);
		font-size: 14px;
		padding: 32px 0;
	}

	@media (max-width: 640px) {
		.thumb {
			width: 110px;
		}
	}
</style>
