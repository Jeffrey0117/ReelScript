<script lang="ts">
	import { t } from '$lib/i18n';
	import { onMount } from 'svelte';
	import { getQuota, type Quota } from '$lib/api';
	import { onAuthChange } from '$lib/auth';

	let quota = $state<Quota | null>(null);

	onMount(() => {
		getQuota().then((q) => (quota = q)).catch(() => {});
		onAuthChange(async (user) => {
			if (user) {
				quota = await getQuota().catch(() => null);
			}
		});
	});

	const plans = $derived([
		{
			key: 'free' as const,
			name: t('planFree'),
			desc: t('planFreeDesc'),
			price: '$0',
			priceLabel: t('freePriceLabel'),
			credits: `5 ${t('creditsPerMonth')}`,
			features: [
				t('featureDownload'),
				t('featureTranslate'),
				t('featureVocab'),
				t('featureQuotes'),
				t('inviteBonusFeature'),
			],
			highlight: false,
		},
		{
			key: 'pro' as const,
			name: t('planPro'),
			desc: t('planProDesc'),
			price: '$5',
			priceLabel: `$5 ${t('perMonth')}`,
			credits: `80 ${t('creditsPerMonth')}`,
			features: [
				t('featureDownload'),
				t('featureTranslate'),
				t('featureVocab'),
				t('featureQuotes'),
				t('featurePriority'),
				t('inviteBonusFeature'),
			],
			highlight: true,
		},
		{
			key: 'unlimited' as const,
			name: t('planUnlimited'),
			desc: t('planUnlimitedDesc'),
			price: '$12',
			priceLabel: `$12 ${t('perMonth')}`,
			credits: t('unlimitedCredits'),
			features: [
				t('featureDownload'),
				t('featureTranslate'),
				t('featureVocab'),
				t('featureQuotes'),
				t('featurePriority'),
				t('featureSupport'),
			],
			highlight: false,
		},
	]);
</script>

<svelte:head>
	<title>{t('pricing')} - ReelScript</title>
</svelte:head>

<section class="pricing-page">
	<div class="pricing-header">
		<h1>{t('pricingTitle')}</h1>
		<p>{t('pricingSubtitle')}</p>
	</div>

	<div class="plans-grid">
		{#each plans as plan (plan.key)}
			<div class="plan-card" class:highlight={plan.highlight}>
				{#if plan.highlight}
					<div class="popular-badge">Popular</div>
				{/if}
				<div class="plan-top">
					<h2 class="plan-name">{plan.name}</h2>
					<p class="plan-desc">{plan.desc}</p>
				</div>
				<div class="plan-price">
					<span class="price-amount">{plan.price}</span>
					{#if plan.key !== 'free'}
						<span class="price-period">{t('perMonth')}</span>
					{/if}
				</div>
				<div class="plan-credits">
					<svg class="credits-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
						<polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>
					</svg>
					<span>{plan.credits}</span>
				</div>
				<ul class="plan-features">
					{#each plan.features as feature}
						<li>
							<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="var(--success)" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
								<polyline points="20 6 9 17 4 12"/>
							</svg>
							<span>{feature}</span>
						</li>
					{/each}
				</ul>
				<button
					class="plan-btn"
					class:plan-btn-highlight={plan.highlight}
					disabled={plan.key === 'free' && quota?.plan === 'free'}
				>
					{#if plan.key === 'free' && quota?.plan === 'free'}
						{t('currentPlan')}
					{:else if plan.key === 'free'}
						{t('planFree')}
					{:else}
						{t('comingSoon')}
					{/if}
				</button>
			</div>
		{/each}
	</div>
</section>

<style>
	.pricing-page {
		max-width: 960px;
		margin: 0 auto;
		padding: 48px 0 64px;
	}

	.pricing-header {
		text-align: center;
		margin-bottom: 48px;
	}

	.pricing-header h1 {
		font-size: 32px;
		font-weight: 700;
		letter-spacing: -0.5px;
		margin-bottom: 8px;
	}

	.pricing-header p {
		color: var(--text-dim);
		font-size: 16px;
	}

	.plans-grid {
		display: grid;
		grid-template-columns: repeat(3, 1fr);
		gap: 20px;
		align-items: start;
	}

	.plan-card {
		position: relative;
		background: var(--bg-card);
		border: 1px solid var(--border);
		border-radius: var(--radius);
		padding: 32px 24px;
		display: flex;
		flex-direction: column;
		gap: 24px;
		transition: border-color 0.2s, box-shadow 0.2s;
	}

	.plan-card:hover {
		border-color: color-mix(in srgb, var(--accent) 40%, var(--border));
	}

	.plan-card.highlight {
		border-color: var(--accent);
		box-shadow: 0 0 0 1px var(--accent), 0 8px 32px rgba(99, 102, 241, 0.12);
	}

	.popular-badge {
		position: absolute;
		top: -12px;
		left: 50%;
		transform: translateX(-50%);
		background: var(--accent);
		color: white;
		font-size: 12px;
		font-weight: 600;
		padding: 4px 16px;
		border-radius: 20px;
		letter-spacing: 0.5px;
	}

	.plan-top {
		text-align: center;
	}

	.plan-name {
		font-size: 20px;
		font-weight: 700;
		margin-bottom: 4px;
	}

	.plan-desc {
		font-size: 13px;
		color: var(--text-dim);
	}

	.plan-price {
		text-align: center;
		display: flex;
		align-items: baseline;
		justify-content: center;
		gap: 2px;
	}

	.price-amount {
		font-size: 40px;
		font-weight: 800;
		letter-spacing: -1px;
		line-height: 1;
	}

	.price-period {
		font-size: 14px;
		color: var(--text-dim);
		font-weight: 500;
	}

	.plan-credits {
		display: flex;
		align-items: center;
		justify-content: center;
		gap: 6px;
		font-size: 14px;
		font-weight: 600;
		color: var(--accent);
		background: color-mix(in srgb, var(--accent) 8%, transparent);
		padding: 8px 16px;
		border-radius: var(--radius-sm);
	}

	.credits-icon {
		flex-shrink: 0;
	}

	.plan-features {
		list-style: none;
		display: flex;
		flex-direction: column;
		gap: 10px;
		flex: 1;
	}

	.plan-features li {
		display: flex;
		align-items: center;
		gap: 8px;
		font-size: 14px;
		color: var(--text);
	}

	.plan-features li svg {
		flex-shrink: 0;
	}

	.plan-btn {
		width: 100%;
		padding: 12px;
		border-radius: var(--radius-sm);
		font-size: 14px;
		font-weight: 600;
		background: var(--bg-hover);
		color: var(--text);
		border: 1px solid var(--border);
		transition: all 0.15s;
		cursor: pointer;
	}

	.plan-btn:hover:not(:disabled) {
		background: color-mix(in srgb, var(--accent) 15%, transparent);
		border-color: var(--accent);
		color: var(--accent);
	}

	.plan-btn:disabled {
		opacity: 0.6;
		cursor: not-allowed;
	}

	.plan-btn-highlight {
		background: var(--accent);
		color: white;
		border-color: var(--accent);
	}

	.plan-btn-highlight:hover:not(:disabled) {
		background: var(--accent-hover);
		color: white;
	}

	@media (max-width: 768px) {
		.plans-grid {
			grid-template-columns: 1fr;
			max-width: 400px;
			margin: 0 auto;
		}

		.pricing-header h1 {
			font-size: 24px;
		}

		.pricing-page {
			padding: 32px 0 48px;
		}

		.price-amount {
			font-size: 32px;
		}

		.plan-card {
			padding: 24px 20px;
			gap: 20px;
		}
	}
</style>
