<script lang="ts">
	// The wall: what a visitor or free member meets when a mode runs out.
	// It is the only place that sells — nothing else on the page is labelled.
	//   visitor      → free sign-in, plus a link to the plans
	//   free member  → straight to checkout (no detour through the plans page)
	import { createCheckout } from '$lib/api';
	import { login } from '$lib/auth';
	import { PRO_PRICE, TIER_LIMITS, type Tier, type WallKind } from '$lib/modes/access';
	import { mt } from '$lib/modes/text';

	let {
		tier,
		kind = 'lines',
		count = 0,
		tone = 'light',
		modal = false,
		onClose = () => {},
	}: {
		tier: Tier;
		kind?: WallKind;
		count?: number;
		tone?: 'light' | 'dark';
		modal?: boolean;
		onClose?: () => void;
	} = $props();

	let busy = $state(false);
	let failed = $state(false);
	let guest = $derived(tier === 'guest');

	let headline = $derived(
		(kind === 'words'
			? `${mt('wallMoreWords')} ${count} ${mt('wallWordsUnit')}`
			: kind === 'chinese'
				? mt('wallChinese')
				: kind === 'print'
					? mt('wallPrint')
					: `${mt('wallMoreLines')} ${count} ${mt('wallLinesUnit')}`
		).trim()
	);

	// A visitor is told exactly what signing in opens up; a member what paying does.
	let detail = $derived(
		guest
			? `${mt('wallGuestGets')} ${TIER_LIMITS.free.lines} ${mt('wallLinesUnit')}${mt('wallGuestGetsTail')}`
			: mt('wallMemberGets')
	);

	async function upgrade() {
		if (busy) return;
		busy = true;
		failed = false;
		try {
			const { checkout_url } = await createCheckout('pro');
			window.location.href = checkout_url;
		} catch {
			failed = true;
			busy = false;
		}
	}

	function handleKey(event: KeyboardEvent) {
		if (modal && event.key === 'Escape') onClose();
	}
</script>

<svelte:window onkeydown={handleKey} />

{#snippet card()}
	<div class="wall" class:dark={tone === 'dark'} class:floating={modal} role={modal ? 'dialog' : undefined} aria-modal={modal ? 'true' : undefined} aria-label={headline}>
		{#if modal}
			<button class="close" onclick={onClose} aria-label={mt('wallClose')}>
				<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M6 6l12 12M18 6L6 18"/></svg>
			</button>
		{/if}
		<span class="lock" aria-hidden="true">
			<svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="4.5" y="10.5" width="15" height="10" rx="2.5"/><path d="M8 10.5V7.5a4 4 0 0 1 8 0v3"/></svg>
		</span>
		<h3>{headline}</h3>
		<p class="detail">{detail}</p>

		{#if !guest}
		<ul class="perks">
			<li>{mt('wallPerkModes')}</li>
			<li>{mt('wallPerkLibrary')}</li>
			<li>{mt('wallPerkCredits')}</li>
			<li>{mt('wallPerkPrint')}</li>
		</ul>
		{/if}

		<div class="actions" class:spaced={guest}>
			{#if guest}
				<button class="go" onclick={() => login()}>{mt('wallLogin')}</button>
				<a class="quiet" href="/pricing">{mt('wallPlans')}</a>
			{:else}
				<button class="go" onclick={upgrade} disabled={busy}>
					{busy ? mt('wallWorking') : mt('wallUpgrade')}
					<span class="price">{PRO_PRICE}{mt('wallPerMonth')}</span>
				</button>
			{/if}
		</div>
		{#if failed}
			<p class="failed">{mt('wallFailed')} <a href="/pricing">{mt('wallPlans')}</a></p>
		{/if}
	</div>
{/snippet}

{#if modal}
	<!-- svelte-ignore a11y_click_events_have_key_events -->
	<div class="veil" role="presentation" onclick={(e) => e.target === e.currentTarget && onClose()}>
		{@render card()}
	</div>
{:else}
	{@render card()}
{/if}

<style>
	.wall {
		--w-bg: var(--bg-card);
		--w-ink: var(--text);
		--w-dim: var(--text-dim);
		--w-line: var(--border);
		position: relative;
		margin: 28px auto 0;
		max-width: 560px;
		padding: 30px 28px 26px;
		text-align: center;
		color: var(--w-ink);
		font-family: 'Inter', 'Noto Sans TC', sans-serif;
		border-radius: 20px;
		/* Gradient frame: the one loud thing on the page. */
		border: 2px solid transparent;
		background:
			linear-gradient(var(--w-bg), var(--w-bg)) padding-box,
			linear-gradient(135deg, #6366f1, #a855f7 55%, #f59e0b) border-box;
		box-shadow: 0 18px 50px color-mix(in srgb, var(--accent) 26%, transparent);
	}

	.wall.dark {
		--w-bg: #15142c;
		--w-ink: #f1f0ff;
		--w-dim: #a5a3d6;
		--w-line: rgba(255, 255, 255, 0.16);
	}

	.wall.floating {
		margin: 0;
		width: min(560px, calc(100vw - 32px));
		max-height: calc(100vh - 32px);
		overflow-y: auto;
		animation: rise 0.22s ease-out;
	}

	@keyframes rise {
		from {
			opacity: 0;
			transform: translateY(14px) scale(0.98);
		}
	}

	.veil {
		position: fixed;
		inset: 0;
		z-index: 300;
		display: grid;
		place-items: center;
		background: rgba(10, 10, 20, 0.62);
		backdrop-filter: blur(5px);
	}

	.close {
		position: absolute;
		top: 12px;
		right: 12px;
		width: 34px;
		height: 34px;
		display: grid;
		place-items: center;
		border-radius: 50%;
		color: var(--w-dim);
	}

	.close:hover {
		color: var(--w-ink);
		background: color-mix(in srgb, var(--w-ink) 10%, transparent);
	}

	.lock {
		display: inline-grid;
		place-items: center;
		width: 56px;
		height: 56px;
		margin-bottom: 14px;
		border-radius: 18px;
		color: #fff;
		background: linear-gradient(135deg, #6366f1, #a855f7);
		box-shadow: 0 10px 26px rgba(99, 102, 241, 0.45);
	}

	h3 {
		font-size: 24px;
		font-weight: 800;
		letter-spacing: -0.02em;
		line-height: 1.25;
	}

	.detail {
		margin-top: 8px;
		font-size: 14.5px;
		line-height: 1.6;
		color: var(--w-dim);
	}

	.perks {
		list-style: none;
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 8px 16px;
		margin: 20px 0 22px;
		padding: 16px 0;
		border-top: 1px solid var(--w-line);
		border-bottom: 1px solid var(--w-line);
		text-align: left;
		font-size: 13.5px;
		line-height: 1.45;
	}

	.perks li {
		position: relative;
		padding-left: 22px;
	}

	.perks li::before {
		content: '';
		position: absolute;
		left: 2px;
		top: 0.28em;
		width: 11px;
		height: 6px;
		border-left: 2.5px solid #6366f1;
		border-bottom: 2.5px solid #6366f1;
		transform: rotate(-45deg);
	}

	.wall.dark .perks li::before {
		border-color: #a5b4fc;
	}

	.actions {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 10px;
	}

	.actions.spaced {
		margin-top: 22px;
	}

	.go {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		gap: 10px;
		width: 100%;
		padding: 14px 20px;
		font-size: 16px;
		font-weight: 700;
		color: #fff;
		border-radius: 14px;
		background: linear-gradient(135deg, #6366f1, #7c3aed);
		box-shadow: 0 10px 24px rgba(99, 102, 241, 0.4);
		transition: transform 0.12s, box-shadow 0.12s;
	}

	.go:hover:not(:disabled) {
		transform: translateY(-1px);
		box-shadow: 0 14px 30px rgba(99, 102, 241, 0.5);
	}

	.go:disabled {
		opacity: 0.6;
		cursor: wait;
	}

	.price {
		padding: 2px 9px;
		font-size: 13px;
		font-weight: 700;
		border-radius: 999px;
		background: rgba(255, 255, 255, 0.2);
	}

	.quiet {
		font-size: 13.5px;
		font-weight: 600;
		color: var(--w-dim);
		text-decoration: underline;
		text-underline-offset: 3px;
	}

	.quiet:hover {
		color: var(--w-ink);
	}

	.failed {
		margin-top: 12px;
		font-size: 13px;
		color: #ef4444;
	}

	@media (max-width: 520px) {
		.wall {
			padding: 24px 18px 20px;
		}

		h3 {
			font-size: 20px;
		}

		.perks {
			grid-template-columns: 1fr;
		}
	}

	@media (prefers-reduced-motion: reduce) {
		.wall.floating {
			animation: none;
		}
	}

	@media print {
		.wall,
		.veil {
			display: none;
		}
	}
</style>
