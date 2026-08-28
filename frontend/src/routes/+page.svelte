<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { t } from '$lib/i18n';
	import { onAuthChange, login, getUser } from '$lib/auth';

	let isLoggedIn = $state(false);
	let visible = $state(false);

	onMount(() => {
		const user = getUser();
		if (user) {
			goto('/videos', { replaceState: true });
			return;
		}

		onAuthChange((u) => {
			isLoggedIn = !!u;
			if (u) {
				goto('/videos', { replaceState: true });
			}
		});

		requestAnimationFrame(() => { visible = true; });
	});

	function handleCta() {
		if (isLoggedIn) {
			goto('/videos');
		} else {
			login();
		}
	}

	const features = $derived([
		{
			icon: 'transcript',
			title: t('featureTranscribeTitle'),
			desc: t('featureTranscribeDesc'),
		},
		{
			icon: 'translate',
			title: t('featureTranslateTitle'),
			desc: t('featureTranslateDesc'),
		},
		{
			icon: 'vocab',
			title: t('featureVocabTitle'),
			desc: t('featureVocabDesc'),
		},
		{
			icon: 'quotes',
			title: t('featureQuotesTitle'),
			desc: t('featureQuotesDesc'),
		},
	]);
</script>

<svelte:head>
	<title>ReelScript · {t('heroTagline')}</title>
</svelte:head>

<div class="landing" class:visible>
	<!-- Hero -->
	<section class="hero">
		<div class="hero-glow"></div>
		<div class="hero-content">
			<img src="/logo.png" alt="ReelScript" class="hero-logo" />
			<h1 class="hero-title">{t('heroTagline')}</h1>
			<p class="hero-sub">{t('heroSubtitle')}</p>
			<div class="hero-actions">
				<button class="cta-btn" onclick={handleCta}>
					{isLoggedIn ? t('heroCtaLoggedIn') : t('heroCta')}
					<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
						<line x1="5" y1="12" x2="19" y2="12"/>
						<polyline points="12 5 19 12 12 19"/>
					</svg>
				</button>
				<a href="/pricing" class="secondary-link">{t('pricing')}</a>
			</div>
		</div>

		<!-- Decorative floating cards -->
		<div class="hero-visual">
			<div class="float-card card-1">
				<div class="float-card-icon">
					<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
						<polygon points="5 3 19 12 5 21 5 3"/>
					</svg>
				</div>
				<div class="float-card-lines">
					<div class="line-en">How do you define success?</div>
					<div class="line-zh">你如何定義成功？</div>
				</div>
			</div>
			<div class="float-card card-2">
				<span class="vocab-word">resilience</span>
				<span class="vocab-pos">n.</span>
				<span class="vocab-zh">韌性、復原力</span>
			</div>
			<div class="float-card card-3">
				<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="var(--accent)" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
					<polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>
				</svg>
				<span class="quote-text">"The best way to predict the future is to create it."</span>
			</div>
		</div>
	</section>

	<!-- Features -->
	<section class="features">
		<div class="features-grid">
			{#each features as feature, i (feature.icon)}
				<div class="feature-card" style="--delay: {i * 80}ms">
					<div class="feature-icon">
						{#if feature.icon === 'transcript'}
							<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
								<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
								<polyline points="14 2 14 8 20 8"/>
								<line x1="16" y1="13" x2="8" y2="13"/>
								<line x1="16" y1="17" x2="8" y2="17"/>
							</svg>
						{:else if feature.icon === 'translate'}
							<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
								<path d="M5 8l6 6"/>
								<path d="M4 14l6-6 2-3"/>
								<path d="M2 5h12"/>
								<path d="M7 2h1"/>
								<path d="M22 22l-5-10-5 10"/>
								<path d="M14 18h6"/>
							</svg>
						{:else if feature.icon === 'vocab'}
							<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
								<path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/>
								<path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/>
								<line x1="8" y1="7" x2="16" y2="7"/>
								<line x1="8" y1="11" x2="13" y2="11"/>
							</svg>
						{:else}
							<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
								<path d="M3 21c3 0 7-1 7-8V5c0-1.25-.756-2.017-2-2H4c-1.25 0-2 .75-2 1.972V11c0 1.25.75 2 2 2 1 0 1 0 1 1v1c0 1-1 2-2 2s-1 .008-1 1.031V20c0 1 0 1 1 1z"/>
								<path d="M15 21c3 0 7-1 7-8V5c0-1.25-.757-2.017-2-2h-4c-1.25 0-2 .75-2 1.972V11c0 1.25.75 2 2 2h.75c0 2.25.25 4-2.75 4v3c0 1 0 1 1 1z"/>
							</svg>
						{/if}
					</div>
					<h3 class="feature-title">{feature.title}</h3>
					<p class="feature-desc">{feature.desc}</p>
				</div>
			{/each}
		</div>
	</section>

	<!-- Bottom CTA -->
	<section class="bottom-cta">
		<div class="cta-glow"></div>
		<h2>{t('bottomCtaTitle')}</h2>
		<p>{t('bottomCtaSubtitle')}</p>
		<button class="cta-btn" onclick={handleCta}>
			{isLoggedIn ? t('heroCtaLoggedIn') : t('heroCta')}
			<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
				<line x1="5" y1="12" x2="19" y2="12"/>
				<polyline points="12 5 19 12 12 19"/>
			</svg>
		</button>
	</section>
</div>

<style>
	.landing {
		opacity: 0;
		transition: opacity 0.5s ease;
	}

	.landing.visible {
		opacity: 1;
	}

	/* ── Hero ── */
	.hero {
		position: relative;
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 48px;
		padding: 80px 0 100px;
		overflow: hidden;
	}

	.hero-glow {
		position: absolute;
		top: -120px;
		left: 50%;
		transform: translateX(-50%);
		width: 600px;
		height: 400px;
		background: radial-gradient(ellipse, color-mix(in srgb, var(--accent) 12%, transparent) 0%, transparent 70%);
		pointer-events: none;
		z-index: 0;
	}

	.hero-content {
		position: relative;
		z-index: 1;
		flex: 1;
		max-width: 520px;
	}

	.hero-logo {
		height: 80px;
		width: auto;
		object-fit: contain;
		margin-bottom: 24px;
		border-radius: 16px;
	}

	:global([data-theme="dark"]) .hero-logo {
		filter: invert(1);
	}

	.hero-title {
		font-size: 48px;
		font-weight: 800;
		line-height: 1.1;
		letter-spacing: -1.5px;
		margin-bottom: 16px;
		background: linear-gradient(135deg, var(--text) 0%, var(--text-dim) 100%);
		-webkit-background-clip: text;
		-webkit-text-fill-color: transparent;
		background-clip: text;
	}

	.hero-sub {
		font-size: 17px;
		line-height: 1.65;
		color: var(--text-dim);
		margin-bottom: 32px;
		max-width: 440px;
	}

	.hero-actions {
		display: flex;
		align-items: center;
		gap: 20px;
	}

	.cta-btn {
		display: inline-flex;
		align-items: center;
		gap: 8px;
		padding: 14px 28px;
		background: var(--accent);
		color: white;
		font-size: 15px;
		font-weight: 600;
		border-radius: var(--radius);
		border: none;
		cursor: pointer;
		transition: background 0.2s, transform 0.15s, box-shadow 0.2s;
		box-shadow: 0 4px 16px color-mix(in srgb, var(--accent) 30%, transparent);
	}

	.cta-btn:hover {
		background: var(--accent-hover);
		transform: translateY(-1px);
		box-shadow: 0 6px 24px color-mix(in srgb, var(--accent) 40%, transparent);
	}

	.secondary-link {
		font-size: 14px;
		font-weight: 500;
		color: var(--text-dim) !important;
		text-decoration: none;
		transition: color 0.15s;
	}

	.secondary-link:hover {
		color: var(--text) !important;
	}

	/* ── Floating visual cards ── */
	.hero-visual {
		position: relative;
		z-index: 1;
		flex-shrink: 0;
		width: 360px;
		height: 320px;
	}

	.float-card {
		position: absolute;
		background: var(--bg-card);
		border: 1px solid var(--border);
		border-radius: var(--radius-sm);
		padding: 12px 16px;
		box-shadow: 0 8px 32px rgba(0, 0, 0, 0.15);
		animation: float-in 0.8s ease-out both;
	}

	.card-1 {
		top: 0;
		left: 0;
		right: 20px;
		display: flex;
		align-items: flex-start;
		gap: 12px;
		animation-delay: 0.3s;
	}

	.float-card-icon {
		flex-shrink: 0;
		width: 36px;
		height: 36px;
		display: flex;
		align-items: center;
		justify-content: center;
		border-radius: 8px;
		background: color-mix(in srgb, var(--accent) 12%, transparent);
		color: var(--accent);
	}

	.float-card-lines {
		display: flex;
		flex-direction: column;
		gap: 4px;
	}

	.line-en {
		font-size: 14px;
		font-weight: 500;
		color: var(--text);
	}

	.line-zh {
		font-size: 13px;
		color: var(--text-dim);
	}

	.card-2 {
		top: 110px;
		left: 20px;
		display: flex;
		align-items: center;
		gap: 8px;
		animation-delay: 0.5s;
	}

	.vocab-word {
		font-size: 15px;
		font-weight: 700;
		color: var(--accent);
	}

	.vocab-pos {
		font-size: 12px;
		color: var(--text-dim);
		font-style: italic;
	}

	.vocab-zh {
		font-size: 13px;
		color: var(--text-dim);
	}

	.card-3 {
		top: 190px;
		left: 40px;
		right: 0;
		display: flex;
		align-items: flex-start;
		gap: 8px;
		animation-delay: 0.7s;
	}

	.card-3 svg {
		flex-shrink: 0;
		margin-top: 2px;
	}

	.quote-text {
		font-size: 13px;
		font-weight: 500;
		color: var(--text);
		line-height: 1.5;
		font-style: italic;
	}

	@keyframes float-in {
		from {
			opacity: 0;
			transform: translateY(16px);
		}
		to {
			opacity: 1;
			transform: translateY(0);
		}
	}

	/* ── Features ── */
	.features {
		padding: 20px 0 80px;
	}

	.features-grid {
		display: grid;
		grid-template-columns: repeat(4, 1fr);
		gap: 16px;
	}

	.feature-card {
		background: var(--bg-card);
		border: 1px solid var(--border);
		border-radius: var(--radius);
		padding: 28px 24px;
		transition: border-color 0.2s, transform 0.2s, box-shadow 0.2s;
		animation: feature-in 0.6s ease-out both;
		animation-delay: var(--delay);
	}

	.feature-card:hover {
		border-color: color-mix(in srgb, var(--accent) 40%, var(--border));
		transform: translateY(-2px);
		box-shadow: 0 8px 24px rgba(0, 0, 0, 0.1);
	}

	@keyframes feature-in {
		from {
			opacity: 0;
			transform: translateY(20px);
		}
		to {
			opacity: 1;
			transform: translateY(0);
		}
	}

	.feature-icon {
		width: 44px;
		height: 44px;
		display: flex;
		align-items: center;
		justify-content: center;
		border-radius: 10px;
		background: color-mix(in srgb, var(--accent) 10%, transparent);
		color: var(--accent);
		margin-bottom: 16px;
	}

	.feature-title {
		font-size: 16px;
		font-weight: 700;
		margin-bottom: 8px;
		letter-spacing: -0.2px;
	}

	.feature-desc {
		font-size: 14px;
		line-height: 1.6;
		color: var(--text-dim);
	}

	/* ── Bottom CTA ── */
	.bottom-cta {
		position: relative;
		text-align: center;
		padding: 72px 0 80px;
		border-top: 1px solid var(--border);
		overflow: hidden;
	}

	.cta-glow {
		position: absolute;
		bottom: -80px;
		left: 50%;
		transform: translateX(-50%);
		width: 500px;
		height: 300px;
		background: radial-gradient(ellipse, color-mix(in srgb, var(--accent) 8%, transparent) 0%, transparent 70%);
		pointer-events: none;
	}

	.bottom-cta h2 {
		font-size: 28px;
		font-weight: 700;
		letter-spacing: -0.5px;
		margin-bottom: 8px;
		position: relative;
	}

	.bottom-cta p {
		font-size: 15px;
		color: var(--text-dim);
		margin-bottom: 28px;
		position: relative;
	}

	.bottom-cta .cta-btn {
		position: relative;
	}

	/* ── Responsive ── */
	@media (max-width: 900px) {
		.hero {
			flex-direction: column;
			text-align: center;
			padding: 48px 0 60px;
			gap: 40px;
		}

		.hero-content {
			max-width: 100%;
		}

		.hero-sub {
			max-width: 100%;
		}

		.hero-actions {
			justify-content: center;
		}

		.hero-visual {
			width: 100%;
			max-width: 360px;
			height: 280px;
			margin: 0 auto;
		}

		.features-grid {
			grid-template-columns: repeat(2, 1fr);
		}
	}

	@media (max-width: 640px) {
		.hero {
			padding: 32px 0 40px;
		}

		.hero-logo {
			height: 56px;
			margin-bottom: 16px;
		}

		.hero-title {
			font-size: 28px;
			letter-spacing: -1px;
		}

		.hero-sub {
			font-size: 14px;
			margin-bottom: 24px;
		}

		.hero-actions {
			flex-direction: column;
			gap: 12px;
		}

		.cta-btn {
			padding: 12px 24px;
			font-size: 14px;
			width: 100%;
			justify-content: center;
		}

		.hero-visual {
			display: none;
		}

		.features-grid {
			grid-template-columns: 1fr;
		}

		.feature-card {
			padding: 20px;
		}

		.bottom-cta {
			padding: 48px 0 56px;
		}

		.bottom-cta h2 {
			font-size: 22px;
		}

		.bottom-cta .cta-btn {
			width: auto;
		}
	}
</style>
