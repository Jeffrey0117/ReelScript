<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import { t } from '$lib/i18n';
	import { publicDeck, saveDeckToWordbook, type DeckDetail } from '$lib/api';
	import { getUser, login, onAuthChange } from '$lib/auth';

	let deck = $state<DeckDetail | null>(null);
	let loading = $state(true);
	let notFound = $state(false);
	let isLoggedIn = $state(false);
	let saving = $state(false);
	let savedNotice = $state('');

	onMount(async () => {
		isLoggedIn = !!getUser();
		onAuthChange((u) => (isLoggedIn = !!u));
		try {
			deck = await publicDeck($page.params.id);
		} catch {
			notFound = true;
		}
		loading = false;
	});

	async function handleSave() {
		if (!deck || saving) return;
		if (!isLoggedIn) {
			login();
			return;
		}
		saving = true;
		try {
			const result = await saveDeckToWordbook(deck.id);
			savedNotice = t('deckSavedNotice').replace('{n}', String(result.added));
			if (result.first_save) {
				deck = { ...deck, saves_count: deck.saves_count + 1 };
			}
		} catch {
			// leave notice empty — button stays usable
		} finally {
			saving = false;
		}
	}
</script>

<svelte:head>
	<title>{deck?.title || t('decksTab')} - ReelScript</title>
</svelte:head>

<a href="/packs#decks" class="back-link">← {t('backToPacks')}</a>

{#if loading}
	<p class="empty">{t('loading')}</p>
{:else if notFound || !deck}
	<p class="empty">{t('noDecks')}</p>
{:else}
	<section class="deck-head">
		<h1>{deck.title}</h1>
		{#if deck.description}
			<p class="desc">{deck.description}</p>
		{/if}
		<p class="meta">
			{deck.words.length} {t('deckWordCount')}
			{#if deck.author_name}
				· {t('deckBy')} {deck.author_name}
			{/if}
			{#if deck.saves_count > 0}
				· ★ {deck.saves_count} {t('deckSavesCount')}
			{/if}
		</p>
		<div class="actions">
			<button class="btn btn-primary" onclick={handleSave} disabled={saving}>
				{isLoggedIn ? t('saveDeck') : t('loginToSave')}
			</button>
			{#if savedNotice}
				<span class="notice" role="status">{savedNotice}</span>
			{/if}
		</div>
	</section>

	<div class="word-table card">
		{#each deck.words as w, i (i)}
			<div class="word-row">
				<span class="word-en">{w.word}</span>
				<span class="word-zh">{w.meaning || ''}</span>
			</div>
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

	.deck-head {
		margin: 8px 0 24px;
	}

	.deck-head h1 {
		font-size: 26px;
		font-weight: 700;
		letter-spacing: -0.5px;
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

	.actions {
		display: flex;
		align-items: center;
		gap: 14px;
		margin-top: 18px;
	}

	.notice {
		font-size: 13.5px;
		color: var(--accent);
	}

	.word-table {
		margin-bottom: 48px;
		overflow: hidden;
	}

	.word-row {
		display: flex;
		align-items: baseline;
		gap: 20px;
		padding: 12px 18px;
		border-bottom: 1px solid var(--border);
	}

	.word-row:last-child {
		border-bottom: none;
	}

	.word-en {
		flex-shrink: 0;
		min-width: 160px;
		font-size: 15px;
		font-weight: 700;
		color: var(--accent);
	}

	.word-zh {
		font-size: 14px;
		color: var(--text);
	}

	.empty {
		color: var(--text-dim);
		font-size: 14px;
		padding: 32px 0;
	}

	@media (max-width: 640px) {
		.word-row {
			flex-direction: column;
			gap: 3px;
		}

		.word-en {
			min-width: 0;
		}
	}
</style>
