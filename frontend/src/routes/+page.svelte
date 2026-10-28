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

		// 示範影片只在捲到該區塊時自動播放,離開就暫停
		let observer: IntersectionObserver | undefined;
		if (demoSection) {
			observer = new IntersectionObserver(
				(entries) => {
					for (const entry of entries) demoVisible = entry.isIntersecting;
				},
				{ threshold: 0.25 }
			);
			observer.observe(demoSection);
		}

		requestAnimationFrame(() => { visible = true; });

		return () => observer?.disconnect();
	});

	function handleCta() {
		if (isLoggedIn) {
			goto('/videos');
		} else {
			login();
		}
	}

	const demos = [1, 2, 3, 4].map((n) => ({
		src: `/videos/demo-${n}.mp4`,
		poster: `/thumbnails/demo-${n}.jpg`,
	}));

	let demoIdx = $state(0);
	let demoVisible = $state(false);
	let demoSection: HTMLElement | undefined = $state();
	let demoVideos: HTMLVideoElement[] = $state([]);

	const mod = (n: number, m: number) => ((n % m) + m) % m;

	function demoPos(i: number, idx: number): 'center' | 'left' | 'right' | 'hidden' {
		if (i === idx) return 'center';
		if (i === mod(idx - 1, demos.length)) return 'left';
		if (i === mod(idx + 1, demos.length)) return 'right';
		return 'hidden';
	}

	$effect(() => {
		demoVideos.forEach((video, i) => {
			if (!video) return;
			if (i === demoIdx && demoVisible) video.play().catch(() => {});
			else video.pause();
		});
	});

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

	<!-- Demo videos: 暗幕劇院輪播 -->
	<section class="demos" bind:this={demoSection}>
		<div class="demos-glow"></div>
		<h2 class="demos-title">{t('demoTitle')}</h2>
		<p class="demos-sub">{t('demoSubtitle')}</p>
		<div class="demo-stage">
			{#key demoIdx}
				<div class="lcard lc-transcript" style="--lc-delay: 0.5s">
					<div class="lcard-cap"><span class="lcard-dot"></span>{t('demoCapTranscript')}</div>
					<div class="lcard-en">How do you define success?</div>
					<div class="lcard-zh">你如何定義成功？</div>
				</div>
				<div class="lcard lc-vocab" style="--lc-delay: 0.95s">
					<div class="lcard-cap"><span class="lcard-dot"></span>{t('demoCapVocab')}</div>
					<span class="lcard-word">resilience</span><span class="lcard-pos">n.</span><span class="lcard-zh">韌性、復原力</span>
				</div>
				<div class="lcard lc-quote" style="--lc-delay: 1.4s">
					<div class="lcard-cap"><span class="lcard-dot"></span>{t('demoCapQuote')}</div>
					<div class="lcard-quote">"The best way to predict the future is to create it."</div>
				</div>
			{/key}
			{#each demos as demo, i (demo.src)}
				<!-- svelte-ignore a11y_click_events_have_key_events -->
				<!-- svelte-ignore a11y_no_static_element_interactions -->
				<div
					class="demo-slot {demoPos(i, demoIdx)}"
					onclick={() => { if (i !== demoIdx) demoIdx = i; }}
				>
					<div class="demo-phone">
						<!-- svelte-ignore a11y_media_has_caption -->
						<video
							src={demo.src}
							poster={demo.poster}
							muted
							loop
							playsinline
							preload="metadata"
							bind:this={demoVideos[i]}
						></video>
					</div>
				</div>
			{/each}
		</div>
		<div class="demo-controls">
			<button class="demo-arrow" aria-label={t('demoPrev')} onclick={() => (demoIdx = mod(demoIdx - 1, demos.length))}>
				<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 18 9 12 15 6"/></svg>
			</button>
			<div class="demo-dots">
				{#each demos as demo, i (demo.src)}
					<button class:on={i === demoIdx} aria-label="demo {i + 1}" onclick={() => (demoIdx = i)}></button>
				{/each}
			</div>
			<button class="demo-arrow" aria-label={t('demoNext')} onclick={() => (demoIdx = mod(demoIdx + 1, demos.length))}>
				<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 18 15 12 9 6"/></svg>
			</button>
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

	/* ── Demo videos: 暗幕劇院 ──
	   固定純黑配色,亮暗主題都走同一個「劇院」視覺 */
	.demos {
		position: relative;
		width: 100vw;
		margin-left: calc(50% - 50vw);
		background: #050505;
		color: #ececec;
		padding: 64px 24px 56px;
		overflow: hidden;
		text-align: center;
	}

	.demos-glow {
		position: absolute;
		top: -140px;
		left: 50%;
		transform: translateX(-50%);
		width: 700px;
		height: 420px;
		background: radial-gradient(ellipse, rgba(255, 255, 255, 0.07) 0%, transparent 70%);
		pointer-events: none;
	}

	.demos-title {
		font-size: 28px;
		font-weight: 700;
		letter-spacing: -0.5px;
		margin-bottom: 8px;
		color: #fff;
	}

	.demos-sub {
		font-size: 15px;
		color: #9a9a9a;
	}

	.demo-stage {
		position: relative;
		max-width: 1100px;
		margin: 44px auto 0;
		height: 560px;
		perspective: 1200px;
	}

	.demo-slot {
		position: absolute;
		top: 0;
		left: 50%;
		width: 280px;
		transition: transform 0.55s cubic-bezier(0.3, 0.8, 0.3, 1), opacity 0.55s, filter 0.55s;
		cursor: pointer;
	}

	.demo-slot.center {
		transform: translateX(-50%);
		z-index: 3;
		cursor: default;
	}

	.demo-slot.left {
		transform: translateX(calc(-50% - 300px)) scale(0.76) rotateY(14deg);
		opacity: 0.32;
		filter: saturate(0.55) brightness(0.6);
		z-index: 2;
	}

	.demo-slot.right {
		transform: translateX(calc(-50% + 300px)) scale(0.76) rotateY(-14deg);
		opacity: 0.32;
		filter: saturate(0.55) brightness(0.6);
		z-index: 2;
	}

	.demo-slot.hidden {
		transform: translateX(-50%) scale(0.5);
		opacity: 0;
		pointer-events: none;
		z-index: 1;
	}

	.demo-phone {
		position: relative;
		border-radius: 28px;
		background: #000;
		padding: 10px;
		box-shadow: 0 30px 80px rgba(0, 0, 0, 0.7), inset 0 0 0 1.5px rgba(255, 255, 255, 0.12);
	}

	.demo-phone::after {
		content: '';
		position: absolute;
		top: 16px;
		left: 50%;
		transform: translateX(-50%);
		width: 72px;
		height: 16px;
		background: #000;
		border-radius: 999px;
		z-index: 3;
	}

	.demo-phone video {
		display: block;
		width: 100%;
		aspect-ratio: 9 / 16;
		object-fit: cover;
		border-radius: 20px;
		background: #111;
	}

	/* 學習浮卡 */
	.lcard {
		position: absolute;
		background: #141414;
		border: 1px solid #2c2c2c;
		border-radius: var(--radius-sm);
		padding: 10px 14px;
		box-shadow: 0 12px 36px rgba(0, 0, 0, 0.5);
		opacity: 0;
		z-index: 5;
		text-align: left;
		animation: lcard-in 0.6s cubic-bezier(0.2, 0.9, 0.3, 1.2) both;
		animation-delay: var(--lc-delay);
	}

	@keyframes lcard-in {
		from {
			opacity: 0;
			transform: translateY(14px) scale(0.92);
		}
		to {
			opacity: 1;
			transform: translateY(0) scale(1);
		}
	}

	.lc-transcript {
		top: 60px;
		right: calc(50% + 170px);
		max-width: 230px;
	}

	.lc-vocab {
		top: 250px;
		left: calc(50% + 170px);
	}

	.lc-quote {
		top: 380px;
		right: calc(50% + 180px);
		max-width: 220px;
	}

	.lcard-cap {
		display: inline-flex;
		align-items: center;
		gap: 5px;
		font-size: 10.5px;
		font-weight: 700;
		letter-spacing: 0.4px;
		color: var(--accent-hover);
		text-transform: uppercase;
		margin-bottom: 5px;
	}

	.lcard-dot {
		width: 5px;
		height: 5px;
		border-radius: 50%;
		background: var(--accent-hover);
	}

	.lcard-en {
		font-size: 13.5px;
		font-weight: 600;
		color: #ececec;
	}

	.lcard-zh {
		font-size: 12.5px;
		color: #9a9a9a;
		margin-top: 3px;
	}

	.lcard-word {
		font-size: 14px;
		font-weight: 700;
		color: var(--accent-hover);
	}

	.lcard-pos {
		font-size: 11px;
		font-style: italic;
		color: #9a9a9a;
		margin: 0 5px;
	}

	.lcard-quote {
		font-size: 12.5px;
		font-style: italic;
		line-height: 1.5;
		color: #d6d6d6;
	}

	/* 輪播控制 */
	.demo-controls {
		display: flex;
		align-items: center;
		justify-content: center;
		gap: 28px;
		margin-top: 36px;
		position: relative;
		z-index: 4;
	}

	.demo-arrow {
		width: 42px;
		height: 42px;
		border-radius: 50%;
		border: 1px solid #2c2c2c;
		background: #141414;
		color: #ececec;
		cursor: pointer;
		display: flex;
		align-items: center;
		justify-content: center;
		transition: border-color 0.2s, transform 0.15s;
		flex-shrink: 0;
	}

	.demo-arrow:hover {
		border-color: var(--accent);
		transform: scale(1.06);
	}

	.demo-dots {
		display: flex;
		gap: 8px;
	}

	.demo-dots button {
		width: 8px;
		height: 8px;
		border-radius: 999px;
		border: none;
		background: rgba(255, 255, 255, 0.25);
		cursor: pointer;
		padding: 0;
		transition: width 0.25s, background 0.25s;
	}

	.demo-dots button.on {
		width: 24px;
		background: #fff;
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

		.demo-stage {
			height: 500px;
		}

		.demo-slot {
			width: 240px;
		}

		.demo-slot.left {
			transform: translateX(calc(-50% - 210px)) scale(0.7) rotateY(14deg);
		}

		.demo-slot.right {
			transform: translateX(calc(-50% + 210px)) scale(0.7) rotateY(-14deg);
		}

		.lcard {
			display: none;
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

		.demos {
			padding: 48px 16px 44px;
		}

		.demos-title {
			font-size: 22px;
		}

		.demo-stage {
			height: 440px;
			margin-top: 32px;
		}

		.demo-slot {
			width: 210px;
		}

		.demo-slot.left {
			transform: translateX(calc(-50% - 150px)) scale(0.66) rotateY(14deg);
		}

		.demo-slot.right {
			transform: translateX(calc(-50% + 150px)) scale(0.66) rotateY(-14deg);
		}

		.demo-controls {
			margin-top: 24px;
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
