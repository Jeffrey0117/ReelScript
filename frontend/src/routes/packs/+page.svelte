<script lang="ts">
	import { onMount } from 'svelte';
	import { t } from '$lib/i18n';
	import {
		publicPacks,
		publicDecks,
		thumbnailUrl,
		type PackSummary,
		type DeckSummary,
	} from '$lib/api';

	let tab = $state<'packs' | 'decks'>('packs');
	let packs = $state<PackSummary[]>([]);
	let decks = $state<DeckSummary[]>([]);
	let loading = $state(true);

	onMount(async () => {
		const [p, d] = await Promise.all([
			publicPacks().catch(() => null),
			publicDecks().catch(() => null),
		]);
		packs = p?.packs ?? [];
		decks = d?.decks ?? [];
		loading = false;
		// Deep link support: /packs#decks opens the decks tab
		if (location.hash === '#decks') tab = 'decks';
	});
</script>

<svelte:head>
	<title>{t('packsTitle')} - ReelScript</title>
</svelte:head>

<section class="packs-hero">
	<h1>{t('packsTitle')}</h1>
	<p class="subtitle">{t('packsSubtitle')}</p>

	<div class="tabs">
		<button class="tab" class:on={tab === 'packs'} onclick={() => (tab = 'packs')}>
			{t('packsTab')}
			{#if packs.length}<span class="tab-count">{packs.length}</span>{/if}
		</button>
		<button class="tab" class:on={tab === 'decks'} onclick={() => (tab = 'decks')}>
			{t('decksTab')}
			{#if decks.length}<span class="tab-count">{decks.length}</span>{/if}
		</button>
	</div>
</section>

{#if loading}
	<div class="grid">
		{#each Array(3) as _}
			<div class="card pack-card skeleton"></div>
		{/each}
	</div>
{:else if tab === 'packs'}
	{#if packs.length === 0}
		<p class="empty">{t('noPacks')}</p>
	{:else}
		<div class="grid">
			{#each packs as pack (pack.id)}
				<a class="card pack-card" href="/packs/{pack.id}">
					<div class="pack-cover">
						{#if pack.cover}
							<img src={thumbnailUrl(pack.cover)} alt="" loading="lazy" />
						{/if}
						{#if pack.is_official}
							<span class="official-badge">{t('officialBadge')}</span>
						{/if}
					</div>
					<div class="pack-body">
						<h3>{pack.name}</h3>
						{#if pack.description}
							<p class="pack-desc">{pack.description}</p>
						{/if}
						<span class="pack-meta">{pack.video_count} {t('packVideoCount')}</span>
					</div>
				</a>
			{/each}
		</div>
	{/if}
{:else if decks.length === 0}
	<p class="empty">{t('noDecks')}</p>
{:else}
	<div class="grid">
		{#each decks as deck (deck.id)}
			<a class="card deck-card" href="/decks/{deck.id}">
				<div class="deck-top">
					<h3>{deck.title}</h3>
					{#if deck.saves_count > 0}
						<span class="saves-pill">★ {deck.saves_count}</span>
					{/if}
				</div>
				{#if deck.description}
					<p class="pack-desc">{deck.description}</p>
				{/if}
				{#if deck.preview?.length}
					<div class="word-chips">
						{#each deck.preview as w (w)}
							<span class="word-chip">{w}</span>
						{/each}
						{#if deck.word_count > deck.preview.length}
							<span class="word-chip more">+{deck.word_count - deck.preview.length}</span>
						{/if}
					</div>
				{/if}
				<span class="pack-meta">
					{deck.word_count} {t('deckWordCount')}
					{#if deck.author_name}
						· {t('deckBy')} {deck.author_name}
					{/if}
				</span>
			</a>
		{/each}
	</div>
{/if}

<style>
	.packs-hero {
		padding: 40px 0 8px;
	}

	.packs-hero h1 {
		font-size: 28px;
		font-weight: 700;
		letter-spacing: -0.5px;
		margin-bottom: 6px;
	}

	.subtitle {
		color: var(--text-dim);
		font-size: 15px;
		margin-bottom: 24px;
	}

	.tabs {
		display: flex;
		gap: 8px;
		border-bottom: 1px solid var(--border);
		margin-bottom: 24px;
	}

	.tab {
		display: inline-flex;
		align-items: center;
		gap: 6px;
		padding: 10px 14px;
		font-size: 14px;
		font-weight: 600;
		color: var(--text-dim);
		background: none;
		border: none;
		border-bottom: 2px solid transparent;
		margin-bottom: -1px;
		cursor: pointer;
		transition: color 0.15s, border-color 0.15s;
	}

	.tab.on {
		color: var(--accent);
		border-bottom-color: var(--accent);
	}

	.tab-count {
		font-size: 11px;
		font-weight: 700;
		padding: 1px 7px;
		border-radius: 999px;
		background: color-mix(in srgb, var(--accent) 10%, transparent);
	}

	.grid {
		display: grid;
		grid-template-columns: repeat(3, 1fr);
		gap: 16px;
		padding-bottom: 48px;
	}

	.pack-card,
	.deck-card {
		display: flex;
		flex-direction: column;
		overflow: hidden;
		text-decoration: none;
		color: var(--text) !important;
		transition: border-color 0.2s, transform 0.15s, box-shadow 0.2s;
	}

	.pack-card:hover,
	.deck-card:hover {
		border-color: color-mix(in srgb, var(--accent) 40%, var(--border));
		transform: translateY(-2px);
		box-shadow: 0 8px 24px rgba(0, 0, 0, 0.1);
	}

	.pack-card.skeleton {
		min-height: 220px;
		animation: pulse 1.2s ease-in-out infinite;
	}

	@keyframes pulse {
		50% { opacity: 0.5; }
	}

	.pack-cover {
		position: relative;
		aspect-ratio: 16 / 9;
		background: var(--bg-hover);
	}

	.pack-cover img {
		width: 100%;
		height: 100%;
		object-fit: cover;
		display: block;
	}

	.official-badge {
		position: absolute;
		top: 10px;
		left: 10px;
		font-size: 11px;
		font-weight: 700;
		letter-spacing: 0.3px;
		color: #fff;
		background: var(--accent);
		border-radius: 6px;
		padding: 3px 8px;
	}

	.pack-body {
		padding: 14px 16px;
		display: flex;
		flex-direction: column;
		gap: 6px;
	}

	.pack-body h3,
	.deck-top h3 {
		font-size: 15.5px;
		font-weight: 700;
		letter-spacing: -0.2px;
	}

	.pack-desc {
		font-size: 13px;
		line-height: 1.5;
		color: var(--text-dim);
		display: -webkit-box;
		-webkit-line-clamp: 2;
		-webkit-box-orient: vertical;
		overflow: hidden;
	}

	.pack-meta {
		font-size: 12.5px;
		color: var(--text-dim);
	}

	.deck-card {
		padding: 16px;
		gap: 8px;
	}

	.deck-top {
		display: flex;
		align-items: flex-start;
		justify-content: space-between;
		gap: 8px;
	}

	.saves-pill {
		flex-shrink: 0;
		font-size: 12px;
		font-weight: 700;
		color: var(--accent);
		background: color-mix(in srgb, var(--accent) 10%, transparent);
		border-radius: 999px;
		padding: 2px 9px;
	}

	.word-chips {
		display: flex;
		flex-wrap: wrap;
		gap: 6px;
	}

	.word-chip {
		font-size: 12px;
		font-weight: 600;
		color: var(--text);
		background: var(--bg-hover);
		border-radius: 6px;
		padding: 3px 8px;
	}

	.word-chip.more {
		color: var(--text-dim);
	}

	.empty {
		color: var(--text-dim);
		font-size: 14px;
		padding: 32px 0 48px;
	}

	@media (max-width: 900px) {
		.grid {
			grid-template-columns: repeat(2, 1fr);
		}
	}

	@media (max-width: 640px) {
		.grid {
			grid-template-columns: 1fr;
		}
	}
</style>
