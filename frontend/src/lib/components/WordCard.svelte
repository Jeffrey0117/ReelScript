<script lang="ts">
	import { t } from '$lib/i18n';

	type WordState = 'none' | 'learning' | 'mastered';

	let {
		word,
		meaning = null,
		phonetic = null,
		loading = false,
		isPhrase = false,
		state = 'none',
		anchor,
		onLearning,
		onMastered,
		onUnmark,
		onClose,
	}: {
		word: string;
		meaning?: string | null;
		phonetic?: string | null;
		loading?: boolean;
		isPhrase?: boolean;
		state?: WordState;
		anchor: { top: number; bottom: number; left: number; width: number };
		onLearning: () => void;
		onMastered: () => void;
		onUnmark: () => void;
		onClose: () => void;
	} = $props();

	const CARD_W = 270;
	const CARD_H = 150;

	let pos = $derived.by(() => {
		const vw = typeof window !== 'undefined' ? window.innerWidth : 1200;
		const left = Math.min(Math.max(8, anchor.left + anchor.width / 2 - CARD_W / 2), vw - CARD_W - 8);
		// Prefer above the token (zerostudy style); fall back below near the top edge
		const above = anchor.top >= CARD_H + 16;
		const top = above ? anchor.top - CARD_H - 10 : anchor.bottom + 10;
		return { left, top };
	});

	function speak() {
		try {
			const u = new SpeechSynthesisUtterance(word);
			u.lang = 'en-US';
			u.rate = 0.9;
			speechSynthesis.cancel();
			speechSynthesis.speak(u);
		} catch {
			// speech unsupported — button is just inert
		}
	}
</script>

<!-- svelte-ignore a11y_click_events_have_key_events -->
<!-- svelte-ignore a11y_no_static_element_interactions -->
<div class="wc-backdrop" onclick={onClose}></div>

<div class="wc-card" style="left: {pos.left}px; top: {pos.top}px; width: {CARD_W}px;" role="dialog">
	<div class="wc-head">
		<span class="wc-word">{word}</span>
		{#if phonetic}
			<span class="wc-phonetic">/{phonetic}/</span>
		{/if}
		<button class="wc-speak" onclick={speak} aria-label="pronounce">
			<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
				<polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/>
				<path d="M15.54 8.46a5 5 0 0 1 0 7.07"/>
				<path d="M19.07 4.93a10 10 0 0 1 0 14.14"/>
			</svg>
		</button>
		<span class="wc-dot" class:learning={state === 'learning'} class:mastered={state === 'mastered'}></span>
	</div>
	<p class="wc-meaning">
		{#if loading}
			<span class="wc-loading">{t('dictLoading')}</span>
		{:else}
			<em class="wc-pos">{isPhrase ? 'phrase' : 'word'}</em>
			{#if meaning}
				{#each meaning.split('\n').slice(0, 3) as line, li (li)}
					{#if li > 0}<br />{/if}{line}
				{/each}
			{:else}
				{t('dictMiss')}
			{/if}
		{/if}
	</p>
	<div class="wc-actions">
		<button
			class="wc-btn"
			class:active-learning={state === 'learning'}
			onclick={() => (state === 'learning' ? onUnmark() : onLearning())}
		>
			{#if state === 'learning'}
				<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>
			{/if}
			{t('markLearning')}
		</button>
		<button
			class="wc-btn"
			class:active-mastered={state === 'mastered'}
			onclick={() => (state === 'mastered' ? onUnmark() : onMastered())}
		>
			{#if state === 'mastered'}
				<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>
			{/if}
			{t('markMastered')}
		</button>
	</div>
</div>

<style>
	.wc-backdrop {
		position: fixed;
		inset: 0;
		z-index: 400;
		background: transparent;
	}

	.wc-card {
		position: fixed;
		z-index: 401;
		background: var(--bg-card);
		border: 1px solid var(--border);
		border-radius: 12px;
		box-shadow: 0 12px 40px rgba(0, 0, 0, 0.22);
		padding: 14px 16px;
		display: flex;
		flex-direction: column;
		gap: 8px;
		animation: wc-in 0.15s ease-out;
	}

	@keyframes wc-in {
		from {
			opacity: 0;
			transform: translateY(4px);
		}
		to {
			opacity: 1;
			transform: translateY(0);
		}
	}

	.wc-head {
		display: flex;
		align-items: center;
		gap: 8px;
	}

	.wc-word {
		font-size: 18px;
		font-weight: 800;
		letter-spacing: -0.3px;
		color: var(--text);
	}

	.wc-speak {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 26px;
		height: 26px;
		border: none;
		border-radius: 50%;
		background: none;
		color: var(--accent);
		cursor: pointer;
	}

	.wc-speak:hover {
		background: color-mix(in srgb, var(--accent) 10%, transparent);
	}

	.wc-dot {
		margin-left: auto;
		width: 8px;
		height: 8px;
		border-radius: 50%;
		background: var(--border);
	}

	.wc-dot.learning {
		background: #3b82f6;
	}

	.wc-dot.mastered {
		background: #10b981;
	}

	.wc-meaning {
		font-size: 13.5px;
		color: var(--text);
		line-height: 1.55;
		max-height: 84px;
		overflow-y: auto;
	}

	.wc-phonetic {
		font-size: 12.5px;
		color: var(--text-dim);
	}

	.wc-loading {
		color: var(--text-dim);
	}

	.wc-pos {
		font-size: 12px;
		color: var(--text-dim);
		font-style: italic;
		margin-right: 6px;
	}

	.wc-actions {
		display: flex;
		gap: 8px;
		margin-top: 2px;
	}

	.wc-btn {
		flex: 1;
		display: inline-flex;
		align-items: center;
		justify-content: center;
		gap: 6px;
		padding: 8px 0;
		font-size: 13px;
		font-weight: 600;
		border: 1px solid var(--border);
		border-radius: 8px;
		background: var(--bg-card);
		color: var(--text);
		cursor: pointer;
		transition: border-color 0.15s, background 0.15s, color 0.15s;
	}

	.wc-btn:hover {
		border-color: var(--accent);
	}

	.wc-btn.active-learning {
		background: #3b82f6;
		border-color: #3b82f6;
		color: #fff;
	}

	.wc-btn.active-mastered {
		background: #10b981;
		border-color: #10b981;
		color: #fff;
	}
</style>
