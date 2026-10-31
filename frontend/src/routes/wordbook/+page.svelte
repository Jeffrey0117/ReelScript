<script lang="ts">
	import { onMount } from 'svelte';
	import { t } from '$lib/i18n';
	import {
		listWordbook,
		deleteWord,
		reviewQueue,
		reviewWord,
		exportWordbook,
		publishDeck,
		myDecks,
		deleteDeck,
		type SavedWord,
		type DeckSummary,
	} from '$lib/api';
	import { getUser, login, onAuthChange } from '$lib/auth';

	let words = $state<SavedWord[]>([]);
	let due = $state(0);
	let loading = $state(true);
	let isLoggedIn = $state(false);
	let decks = $state<DeckSummary[]>([]);

	// Review mode
	let reviewing = $state(false);
	let cards = $state<SavedWord[]>([]);
	let cardIdx = $state(0);
	let answerShown = $state(false);
	let reviewedCount = $state(0);
	let reviewFinished = $state(false);

	// Publish modal
	let showPublish = $state(false);
	let selectedIds = $state<Set<string>>(new Set());
	let deckTitle = $state('');
	let deckDesc = $state('');
	let publishing = $state(false);

	async function load() {
		const data = await listWordbook().catch(() => null);
		if (data) {
			words = data.words;
			due = data.due;
		}
		loading = false;
		const mine = await myDecks().catch(() => null);
		decks = mine?.decks ?? [];
	}

	onMount(() => {
		const user = getUser();
		isLoggedIn = !!user;
		if (user) void load();
		onAuthChange((u) => {
			const was = isLoggedIn;
			isLoggedIn = !!u;
			if (u && !was) void load();
		});
	});

	// ── Review ──
	async function startReview() {
		const q = await reviewQueue().catch(() => null);
		cards = q?.cards ?? [];
		if (cards.length === 0) return;
		cardIdx = 0;
		answerShown = false;
		reviewedCount = 0;
		reviewFinished = false;
		reviewing = true;
	}

	async function answer(correct: boolean) {
		const card = cards[cardIdx];
		if (!card) return;
		reviewedCount += 1;
		reviewWord(card.id, correct).catch(() => {});
		if (cardIdx + 1 < cards.length) {
			cardIdx += 1;
			answerShown = false;
		} else {
			reviewFinished = true;
		}
	}

	async function exitReview() {
		reviewing = false;
		await load();
	}

	// ── Export ──
	async function handleExport() {
		try {
			const tsv = await exportWordbook();
			const blob = new Blob([tsv], { type: 'text/tab-separated-values;charset=utf-8' });
			const url = URL.createObjectURL(blob);
			const a = document.createElement('a');
			a.href = url;
			a.download = 'reelscript-wordbook.txt';
			a.click();
			URL.revokeObjectURL(url);
		} catch {
			// no words or network error — nothing to download
		}
	}

	// ── Delete ──
	async function handleDelete(id: string) {
		try {
			await deleteWord(id);
			words = words.filter((w) => w.id !== id);
		} catch {
			// ignore
		}
	}

	// ── Publish ──
	function openPublish() {
		selectedIds = new Set(words.map((w) => w.id));
		deckTitle = '';
		deckDesc = '';
		showPublish = true;
	}

	function toggleSelect(id: string) {
		const next = new Set(selectedIds);
		if (next.has(id)) {
			next.delete(id);
		} else {
			next.add(id);
		}
		selectedIds = next;
	}

	async function handlePublish() {
		if (!deckTitle.trim() || selectedIds.size === 0 || publishing) return;
		publishing = true;
		try {
			await publishDeck({
				title: deckTitle.trim(),
				description: deckDesc.trim() || undefined,
				word_ids: words.filter((w) => selectedIds.has(w.id)).map((w) => w.id),
			});
			showPublish = false;
			const mine = await myDecks().catch(() => null);
			decks = mine?.decks ?? [];
		} catch {
			// keep modal open so nothing typed is lost
		} finally {
			publishing = false;
		}
	}

	async function handleUnpublish(id: string) {
		if (!confirm(t('confirmUnpublish'))) return;
		try {
			await deleteDeck(id);
			decks = decks.filter((d) => d.id !== id);
		} catch {
			// ignore
		}
	}

	const boxDots = (box: number) => Array.from({ length: 5 }, (_, i) => i < box);
</script>

<svelte:head>
	<title>{t('wordbook')} - ReelScript</title>
</svelte:head>

{#if !isLoggedIn}
	<section class="gate">
		<p>{t('loginRequired')}</p>
		<button class="btn btn-primary" onclick={() => login()}>{t('login')}</button>
	</section>
{:else if reviewing}
	<!-- ── Review mode ── -->
	<section class="review">
		{#if reviewFinished}
			<div class="review-card card done-card">
				<h2>{t('reviewDone')}</h2>
				<p>{t('reviewedCount').replace('{n}', String(reviewedCount))}</p>
				<button class="btn btn-primary" onclick={exitReview}>{t('done')}</button>
			</div>
		{:else}
			{@const card = cards[cardIdx]}
			<div class="review-progress">
				<span>{cardIdx + 1} / {cards.length}</span>
				<button class="btn btn-ghost btn-sm" onclick={exitReview}>{t('exitReview')}</button>
			</div>
			<div class="review-card card">
				<span class="review-word">{card.word}</span>
				{#if answerShown}
					<span class="review-meaning">{card.meaning || '—'}</span>
					{#if card.example}
						<p class="review-example">{card.example}</p>
					{/if}
				{/if}
			</div>
			<div class="review-actions">
				{#if !answerShown}
					<button class="btn btn-primary review-btn" onclick={() => (answerShown = true)}>
						{t('showAnswer')}
					</button>
				{:else}
					<button class="btn btn-ghost review-btn forgot" onclick={() => answer(false)}>
						{t('forgotIt')}
					</button>
					<button class="btn btn-primary review-btn" onclick={() => answer(true)}>
						{t('knowIt')}
					</button>
				{/if}
			</div>
		{/if}
	</section>
{:else}
	<!-- ── Overview ── -->
	<section class="head">
		<h1>{t('wordbook')}</h1>
		<div class="stats">
			<div class="stat card">
				<span class="stat-num">{words.length}</span>
				<span class="stat-label">{t('totalWords')}</span>
			</div>
			<div class="stat card" class:hot={due > 0}>
				<span class="stat-num">{due}</span>
				<span class="stat-label">{t('dueToday')}</span>
			</div>
		</div>
		<div class="head-actions">
			<button class="btn btn-primary" onclick={startReview} disabled={due === 0}>
				{due > 0 ? `${t('startReview')} (${due})` : t('noDueCards')}
			</button>
			{#if words.length > 0}
				<button class="btn btn-ghost" onclick={openPublish}>{t('publishDeck')}</button>
				<button class="btn btn-ghost" onclick={handleExport}>{t('exportAnki')}</button>
			{/if}
		</div>
	</section>

	{#if decks.length > 0}
		<section class="my-decks">
			<h2>{t('myPublishedDecks')}</h2>
			<div class="deck-rows">
				{#each decks as deck (deck.id)}
					<div class="deck-row card">
						<a href="/decks/{deck.id}" class="deck-link">
							<span class="deck-title">{deck.title}</span>
							<span class="deck-meta">
								{deck.word_count} {t('deckWordCount')}
								{#if deck.saves_count > 0}
									· ★ {deck.saves_count}
								{/if}
							</span>
						</a>
						<button class="btn btn-ghost btn-sm" onclick={() => handleUnpublish(deck.id)}>
							{t('unpublish')}
						</button>
					</div>
				{/each}
			</div>
		</section>
	{/if}

	<section class="word-list">
		{#if loading}
			<p class="empty">{t('loading')}</p>
		{:else if words.length === 0}
			<p class="empty">{t('wordbookEmpty')}</p>
		{:else}
			<div class="word-table card">
				{#each words as w (w.id)}
					<div class="word-row">
						<div class="word-main">
							<span class="word-en">{w.word}</span>
							<span class="word-zh">{w.meaning || ''}</span>
						</div>
						<div class="word-side">
							<span class="box-dots" title="{t('boxLabel')} {w.box}/5">
								{#each boxDots(w.box) as filled, i (i)}
									<span class="dot" class:filled></span>
								{/each}
							</span>
							<button class="del-btn" onclick={() => handleDelete(w.id)} aria-label={t('deleteWord')}>
								<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
									<polyline points="3 6 5 6 21 6"/>
									<path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
								</svg>
							</button>
						</div>
					</div>
				{/each}
			</div>
		{/if}
	</section>
{/if}

<!-- ── Publish modal ── -->
{#if showPublish}
	<!-- svelte-ignore a11y_click_events_have_key_events -->
	<!-- svelte-ignore a11y_no_static_element_interactions -->
	<div class="modal-overlay" onclick={() => (showPublish = false)}>
		<!-- svelte-ignore a11y_click_events_have_key_events -->
		<!-- svelte-ignore a11y_no_static_element_interactions -->
		<div class="modal card" onclick={(e) => e.stopPropagation()}>
			<h3>{t('publishDeck')}</h3>
			<p class="modal-hint">{t('publishDeckHint')}</p>

			<input type="text" bind:value={deckTitle} placeholder={t('deckTitleLabel')} maxlength="100" />
			<input type="text" bind:value={deckDesc} placeholder={t('deckDescLabel')} maxlength="500" />

			<div class="pick-list">
				{#each words as w (w.id)}
					<label class="pick-row">
						<input
							type="checkbox"
							checked={selectedIds.has(w.id)}
							onchange={() => toggleSelect(w.id)}
						/>
						<span class="word-en">{w.word}</span>
						<span class="word-zh">{w.meaning || ''}</span>
					</label>
				{/each}
			</div>

			<div class="modal-actions">
				<span class="pick-count">{t('selectedWords').replace('{n}', String(selectedIds.size))}</span>
				<button class="btn btn-ghost btn-sm" onclick={() => (showPublish = false)}>{t('cancel')}</button>
				<button
					class="btn btn-primary btn-sm"
					onclick={handlePublish}
					disabled={publishing || !deckTitle.trim() || selectedIds.size === 0}
				>
					{publishing ? t('publishing') : t('publish')}
				</button>
			</div>
		</div>
	</div>
{/if}

<style>
	.gate {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 16px;
		padding: 80px 0;
		color: var(--text-dim);
	}

	.head {
		padding: 40px 0 24px;
	}

	.head h1 {
		font-size: 28px;
		font-weight: 700;
		letter-spacing: -0.5px;
		margin-bottom: 20px;
	}

	.stats {
		display: flex;
		gap: 12px;
		margin-bottom: 20px;
	}

	.stat {
		display: flex;
		flex-direction: column;
		gap: 2px;
		padding: 16px 24px;
		min-width: 120px;
	}

	.stat-num {
		font-size: 26px;
		font-weight: 800;
		font-variant-numeric: tabular-nums;
		color: var(--text-dim);
	}

	.stat.hot .stat-num {
		color: var(--accent);
	}

	.stat-label {
		font-size: 12.5px;
		color: var(--text-dim);
	}

	.head-actions {
		display: flex;
		align-items: center;
		gap: 10px;
		flex-wrap: wrap;
	}

	/* ── Review ── */
	.review {
		max-width: 520px;
		margin: 48px auto;
		display: flex;
		flex-direction: column;
		gap: 20px;
	}

	.review-progress {
		display: flex;
		align-items: center;
		justify-content: space-between;
		font-size: 13.5px;
		color: var(--text-dim);
		font-variant-numeric: tabular-nums;
	}

	.review-card {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		gap: 14px;
		min-height: 260px;
		padding: 36px 28px;
		text-align: center;
	}

	.review-word {
		font-size: 34px;
		font-weight: 800;
		letter-spacing: -0.5px;
		color: var(--accent);
	}

	.review-meaning {
		font-size: 19px;
		color: var(--text);
	}

	.review-example {
		font-size: 14px;
		color: var(--text-dim);
		font-style: italic;
		line-height: 1.6;
	}

	.review-actions {
		display: flex;
		gap: 12px;
	}

	.review-btn {
		flex: 1;
		padding: 13px 0;
		font-size: 15px;
	}

	.review-btn.forgot {
		border: 1px solid var(--border);
	}

	.done-card h2 {
		font-size: 24px;
		font-weight: 700;
	}

	.done-card p {
		color: var(--text-dim);
		font-size: 14.5px;
	}

	/* ── My decks ── */
	.my-decks {
		margin-bottom: 28px;
	}

	.my-decks h2 {
		font-size: 17px;
		font-weight: 700;
		margin-bottom: 12px;
	}

	.deck-rows {
		display: flex;
		flex-direction: column;
		gap: 8px;
	}

	.deck-row {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 12px;
		padding: 12px 16px;
	}

	.deck-link {
		display: flex;
		flex-direction: column;
		gap: 2px;
		text-decoration: none;
		min-width: 0;
	}

	.deck-title {
		font-size: 14.5px;
		font-weight: 600;
		color: var(--text);
	}

	.deck-meta {
		font-size: 12.5px;
		color: var(--text-dim);
	}

	/* ── Word list ── */
	.word-list {
		padding-bottom: 48px;
	}

	.word-table {
		overflow: hidden;
	}

	.word-row {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 16px;
		padding: 11px 18px;
		border-bottom: 1px solid var(--border);
	}

	.word-row:last-child {
		border-bottom: none;
	}

	.word-main {
		display: flex;
		align-items: baseline;
		gap: 16px;
		min-width: 0;
	}

	.word-en {
		flex-shrink: 0;
		font-size: 15px;
		font-weight: 700;
		color: var(--accent);
	}

	.word-zh {
		font-size: 13.5px;
		color: var(--text-dim);
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	.word-side {
		display: flex;
		align-items: center;
		gap: 14px;
		flex-shrink: 0;
	}

	.box-dots {
		display: inline-flex;
		gap: 3px;
	}

	.dot {
		width: 6px;
		height: 6px;
		border-radius: 50%;
		background: var(--border);
	}

	.dot.filled {
		background: var(--accent);
	}

	.del-btn {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 28px;
		height: 28px;
		border-radius: var(--radius-sm);
		border: none;
		background: none;
		color: var(--text-dim);
		cursor: pointer;
		transition: color 0.15s, background 0.15s;
	}

	.del-btn:hover {
		color: var(--danger);
		background: var(--bg-hover);
	}

	.empty {
		color: var(--text-dim);
		font-size: 14px;
		padding: 24px 0;
	}

	/* ── Publish modal ── */
	.modal-overlay {
		position: fixed;
		inset: 0;
		background: rgba(0, 0, 0, 0.4);
		display: flex;
		align-items: center;
		justify-content: center;
		z-index: 300;
		padding: 16px;
	}

	.modal {
		width: 100%;
		max-width: 480px;
		max-height: 80vh;
		display: flex;
		flex-direction: column;
		gap: 12px;
		padding: 22px;
	}

	.modal h3 {
		font-size: 17px;
		font-weight: 700;
	}

	.modal-hint {
		font-size: 13px;
		color: var(--text-dim);
		line-height: 1.5;
	}

	.modal input[type='text'] {
		width: 100%;
		padding: 10px 12px;
		font-size: 14px;
		font-family: inherit;
		border: 1px solid var(--border);
		border-radius: var(--radius-sm);
		background: var(--bg);
		color: var(--text);
		outline: none;
	}

	.modal input[type='text']:focus {
		border-color: var(--accent);
	}

	.pick-list {
		flex: 1;
		overflow-y: auto;
		border: 1px solid var(--border);
		border-radius: var(--radius-sm);
		min-height: 120px;
	}

	.pick-row {
		display: flex;
		align-items: baseline;
		gap: 10px;
		padding: 8px 12px;
		border-bottom: 1px solid var(--border);
		cursor: pointer;
		font-size: 13.5px;
	}

	.pick-row:last-child {
		border-bottom: none;
	}

	.pick-row:hover {
		background: var(--bg-hover);
	}

	.pick-row .word-zh {
		white-space: normal;
	}

	.modal-actions {
		display: flex;
		align-items: center;
		gap: 10px;
	}

	.pick-count {
		flex: 1;
		font-size: 12.5px;
		color: var(--text-dim);
	}

	@media (max-width: 640px) {
		.stats {
			width: 100%;
		}

		.stat {
			flex: 1;
			min-width: 0;
		}
	}
</style>
