<script lang="ts">
	// Podcast mode: no picture, just the show. Cover, transport, and the lines
	// scrolling by like lyrics.
	import { videoFileUrl, thumbnailUrl, type VideoDetail, type TranscriptSegment } from '$lib/api';
	import { t } from '$lib/i18n';
	import { formatTime, currentIndex } from '$lib/lesson';
	import { mt } from '$lib/modes/text';
	import type { Gate } from '$lib/modes/access';
	import ModeWall from './ModeWall.svelte';

	let {
		video,
		segments,
		hasTranslation,
		gate,
		startAt = 0,
		onTime = () => {},
	}: {
		video: VideoDetail;
		segments: TranscriptSegment[];
		hasTranslation: boolean;
		gate: Gate;
		startAt?: number;
		onTime?: (seconds: number) => void;
	} = $props();

	const RATES = [0.75, 1, 1.25, 1.5];
	const BAR_COUNT = 72;

	let audioEl = $state<HTMLAudioElement | null>(null);
	let linesEl = $state<HTMLDivElement | null>(null);
	let playing = $state(false);
	let time = $state(0);
	let duration = $state(0);
	let rate = $state(1);
	let showZh = $state(true);

	let src = $derived(video.filename ? videoFileUrl(video.filename) : '');
	let active = $derived(currentIndex(segments, time));
	let total = $derived(duration || segments[segments.length - 1]?.end || 0);
	let stopAt = $derived(gate.stopAt);
	let progress = $derived(total > 0 ? Math.min(time / total, 1) : 0);

	// A stand-in waveform: bar heights follow how much is being said at each
	// moment (characters per second), so it at least looks like this episode.
	let bars = $derived.by(() => {
		if (total <= 0) return Array(BAR_COUNT).fill(0.3);
		const density = Array(BAR_COUNT).fill(0);
		for (const segment of segments) {
			const span = Math.max(segment.end - segment.start, 0.2);
			const from = Math.floor((segment.start / total) * BAR_COUNT);
			const to = Math.min(Math.floor((segment.end / total) * BAR_COUNT), BAR_COUNT - 1);
			for (let i = from; i <= to; i += 1) density[i] = Math.max(density[i], segment.text.length / span);
		}
		const peak = Math.max(...density, 1);
		return density.map((value, i) => 0.18 + 0.82 * (value / peak) * (0.7 + 0.3 * Math.abs(Math.sin(i * 1.7))));
	});

	function handleLoaded() {
		if (!audioEl) return;
		duration = audioEl.duration || 0;
		const limit = stopAt ?? duration;
		if (startAt > 0 && startAt < Math.min(duration, limit)) audioEl.currentTime = startAt;
	}

	function handleTime() {
		if (!audioEl) return;
		time = audioEl.currentTime;
		// Reached the held-back part: stop just before it and bring up the wall.
		if (stopAt !== null && time >= stopAt) {
			audioEl.pause();
			audioEl.currentTime = Math.max(stopAt - 0.3, 0);
			time = audioEl.currentTime;
			gate.open('lines');
			return;
		}
		onTime(time);
	}

	function toggle() {
		if (!audioEl) return;
		if (audioEl.paused) void audioEl.play().catch(() => {});
		else audioEl.pause();
	}

	function seek(seconds: number, play = false) {
		if (!audioEl) return;
		if (stopAt !== null && seconds >= stopAt) return gate.open('lines');
		audioEl.currentTime = Math.max(0, Math.min(seconds, total || seconds));
		time = audioEl.currentTime;
		if (play) void audioEl.play().catch(() => {});
	}

	function seekFromBar(event: MouseEvent) {
		const box = (event.currentTarget as HTMLElement).getBoundingClientRect();
		seek(((event.clientX - box.left) / box.width) * total);
	}

	function cycleRate() {
		rate = RATES[(RATES.indexOf(rate) + 1) % RATES.length];
		if (audioEl) audioEl.playbackRate = rate;
	}

	function handleKey(event: KeyboardEvent) {
		const target = event.target as HTMLElement | null;
		// Leave browser shortcuts (Alt+← is Back) and anything being typed into alone.
		if (event.altKey || event.ctrlKey || event.metaKey) return;
		if (target && (target.isContentEditable || /^(INPUT|TEXTAREA|SELECT|BUTTON|A)$/.test(target.tagName))) return;
		if (event.key === ' ') {
			event.preventDefault();
			toggle();
		} else if (event.key === 'ArrowLeft') seek(time - 5);
		else if (event.key === 'ArrowRight') seek(time + 5);
	}

	// Keep the spoken line centred — scroll the list, never the page.
	$effect(() => {
		const row = linesEl?.children[active] as HTMLElement | undefined;
		if (!linesEl || !row) return;
		linesEl.scrollTo({
			top: row.offsetTop - linesEl.clientHeight / 2 + row.offsetHeight / 2,
			behavior: 'smooth',
		});
	});
</script>

<svelte:window onkeydown={handleKey} />

<section class="studio">
	{#if src}
		<audio
			bind:this={audioEl}
			{src}
			preload="metadata"
			onloadedmetadata={handleLoaded}
			ontimeupdate={handleTime}
			onplay={() => (playing = true)}
			onpause={() => (playing = false)}
			onended={() => (playing = false)}
		></audio>
	{/if}

	<div class="deck">
		<div class="cover" class:spinning={playing}>
			{#if video.thumbnail}
				<img src={thumbnailUrl(video.thumbnail)} alt="" />
			{/if}
			<span class="cover-tag">{mt('podEpisode')}</span>
		</div>

		<div class="meta">
			<p class="on-air" class:live={playing}><i></i>{mt('podNowPlaying')}</p>
			<h1>{video.title || t('untitled')}</h1>
			{#if video.channel}<p class="host">{video.channel}</p>{/if}
		</div>

		<!-- svelte-ignore a11y_click_events_have_key_events -->
		<div class="wave" role="presentation" onclick={seekFromBar} style="--progress: {progress}">
			{#each bars as height, i (i)}
				<span class:played={i / BAR_COUNT < progress} style="height: {Math.round(height * 100)}%"></span>
			{/each}
		</div>
		<div class="clock">
			<span>{formatTime(time)}</span>
			<span>{formatTime(total)}</span>
		</div>

		<div class="transport">
			<button class="chip" onclick={cycleRate} title={mt('speed')}>{rate}x</button>
			<button class="skip" onclick={() => seek(time - 10)} title={mt('podBack')} aria-label={mt('podBack')}>
				<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M3 12a9 9 0 1 0 3-6.7"/><path d="M3 4v5h5"/></svg>
				<small>10</small>
			</button>
			<button class="play" onclick={toggle} disabled={!src} aria-label={playing ? mt('pause') : mt('play')}>
				{#if playing}
					<svg width="26" height="26" viewBox="0 0 24 24" fill="currentColor"><rect x="6" y="4.5" width="4.2" height="15" rx="1.2"/><rect x="13.8" y="4.5" width="4.2" height="15" rx="1.2"/></svg>
				{:else}
					<svg width="26" height="26" viewBox="0 0 24 24" fill="currentColor"><path d="M8 4.8v14.4a.8.8 0 0 0 1.2.7l11.6-7.2a.8.8 0 0 0 0-1.4L9.2 4.1A.8.8 0 0 0 8 4.8z"/></svg>
				{/if}
			</button>
			<button class="skip" onclick={() => seek(time + 10)} title={mt('podForward')} aria-label={mt('podForward')}>
				<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12a9 9 0 1 1-3-6.7"/><path d="M21 4v5h-5"/></svg>
				<small>10</small>
			</button>
			<button class="chip" class:on={showZh} onclick={() => (showZh = !showZh)} disabled={!hasTranslation} aria-pressed={showZh}>{mt('showZh')}</button>
		</div>
	</div>

	<div class="captions">
		<p class="captions-title">{mt('podTranscript')}</p>
		<div class="lines" bind:this={linesEl}>
			{#each segments as segment, i (i)}
				<button class="line" class:now={i === active} class:past={i < active} onclick={() => seek(segment.start, true)}>
					<span class="line-en">{segment.text}</span>
					{#if showZh && segment.translation}
						<span class="line-zh">{segment.translation}</span>
					{/if}
				</button>
			{:else}
				<p class="empty">{mt('noTranscript')}</p>
			{/each}
			{#if gate.hiddenLines > 0}
				<div class="locked">
					<ModeWall tier={gate.tier} kind="lines" count={gate.hiddenLines} tone="dark" />
				</div>
			{/if}
		</div>
	</div>
</section>

<style>
	.studio {
		--ink: #f1f0ff;
		--ink-dim: #9a98c9;
		--glow: #818cf8;
		display: grid;
		grid-template-columns: minmax(280px, 380px) 1fr;
		gap: 40px;
		padding: 40px;
		border-radius: 28px;
		color: var(--ink);
		background:
			radial-gradient(120% 90% at 0% 0%, rgba(99, 102, 241, 0.55) 0%, transparent 55%),
			radial-gradient(90% 80% at 100% 100%, rgba(168, 85, 247, 0.28) 0%, transparent 60%),
			#0d0c1f;
		box-shadow: 0 30px 80px rgba(30, 27, 75, 0.35);
		overflow: hidden;
	}

	.deck {
		display: flex;
		flex-direction: column;
		min-width: 0;
	}

	.cover {
		position: relative;
		width: 100%;
		max-width: 300px;
		aspect-ratio: 1;
		align-self: center;
		border-radius: 22px;
		overflow: hidden;
		background: linear-gradient(135deg, #4f46e5, #a855f7);
		box-shadow: 0 24px 60px rgba(0, 0, 0, 0.5);
		transition: transform 0.4s ease;
	}

	.cover.spinning {
		transform: scale(1.03);
	}

	.cover img {
		width: 100%;
		height: 100%;
		object-fit: cover;
		display: block;
	}

	.cover-tag {
		position: absolute;
		left: 12px;
		bottom: 12px;
		padding: 4px 10px;
		font-size: 11px;
		font-weight: 700;
		letter-spacing: 0.14em;
		text-transform: uppercase;
		border-radius: 999px;
		background: rgba(13, 12, 31, 0.72);
		backdrop-filter: blur(6px);
	}

	.meta {
		margin-top: 26px;
	}

	.on-air {
		display: inline-flex;
		align-items: center;
		gap: 7px;
		font-size: 11px;
		font-weight: 700;
		letter-spacing: 0.18em;
		text-transform: uppercase;
		color: var(--ink-dim);
	}

	.on-air i {
		width: 7px;
		height: 7px;
		border-radius: 50%;
		background: var(--ink-dim);
	}

	.on-air.live {
		color: #c7d2fe;
	}

	.on-air.live i {
		background: #f87171;
		box-shadow: 0 0 10px #f87171;
		animation: pulse 1.4s ease-in-out infinite;
	}

	@keyframes pulse {
		50% {
			opacity: 0.35;
		}
	}

	h1 {
		margin-top: 8px;
		font-size: 24px;
		font-weight: 800;
		line-height: 1.25;
		letter-spacing: -0.02em;
		text-wrap: balance;
	}

	.host {
		margin-top: 6px;
		font-size: 14px;
		color: var(--ink-dim);
	}

	.wave {
		display: flex;
		align-items: center;
		gap: 2px;
		height: 56px;
		margin-top: 24px;
		cursor: pointer;
	}

	.wave span {
		flex: 1;
		min-width: 1px;
		border-radius: 2px;
		background: rgba(255, 255, 255, 0.2);
		transition: background 0.15s;
	}

	.wave span.played {
		background: var(--glow);
	}

	.clock {
		display: flex;
		justify-content: space-between;
		margin-top: 6px;
		font-size: 12px;
		font-variant-numeric: tabular-nums;
		color: var(--ink-dim);
	}

	.transport {
		display: flex;
		align-items: center;
		justify-content: space-between;
		margin-top: 18px;
	}

	.play {
		width: 68px;
		height: 68px;
		border-radius: 50%;
		display: grid;
		place-items: center;
		color: #0d0c1f;
		background: #fff;
		box-shadow: 0 0 0 8px rgba(255, 255, 255, 0.08), 0 12px 30px rgba(129, 140, 248, 0.5);
		transition: transform 0.15s;
	}

	.play:hover:not(:disabled) {
		transform: scale(1.06);
	}

	.play:disabled {
		opacity: 0.4;
		cursor: not-allowed;
	}

	.skip {
		position: relative;
		width: 44px;
		height: 44px;
		display: grid;
		place-items: center;
		color: var(--ink);
		border-radius: 50%;
	}

	.skip small {
		position: absolute;
		font-size: 8.5px;
		font-weight: 700;
		top: 50%;
		left: 50%;
		transform: translate(-50%, -42%);
	}

	.skip:hover {
		background: rgba(255, 255, 255, 0.1);
	}

	.chip {
		min-width: 48px;
		padding: 6px 10px;
		font-size: 12.5px;
		font-weight: 700;
		color: var(--ink-dim);
		border: 1px solid rgba(255, 255, 255, 0.18);
		border-radius: 999px;
	}

	.chip:hover:not(:disabled) {
		color: var(--ink);
		border-color: rgba(255, 255, 255, 0.4);
	}

	.chip.on {
		color: #0d0c1f;
		background: #c7d2fe;
		border-color: #c7d2fe;
	}

	.chip:disabled {
		opacity: 0.35;
		cursor: not-allowed;
	}

	/* Captions */
	.captions {
		display: flex;
		flex-direction: column;
		min-width: 0;
		min-height: 0;
	}

	.captions-title {
		font-size: 11px;
		font-weight: 700;
		letter-spacing: 0.18em;
		text-transform: uppercase;
		color: var(--ink-dim);
		margin-bottom: 8px;
	}

	.lines {
		position: relative;
		flex: 1;
		height: 0;
		min-height: 520px;
		overflow-y: auto;
		padding: 30% 0;
		scrollbar-width: none;
		mask-image: linear-gradient(to bottom, transparent 0, #000 16%, #000 84%, transparent 100%);
		-webkit-mask-image: linear-gradient(to bottom, transparent 0, #000 16%, #000 84%, transparent 100%);
	}

	.lines::-webkit-scrollbar {
		display: none;
	}

	.line {
		display: flex;
		flex-direction: column;
		gap: 4px;
		width: 100%;
		padding: 10px 0;
		text-align: left;
		color: rgba(241, 240, 255, 0.34);
		transform-origin: left center;
		transition: color 0.25s, transform 0.25s;
	}

	.line:hover {
		color: rgba(241, 240, 255, 0.8);
	}

	.line.past {
		color: rgba(241, 240, 255, 0.5);
	}

	.line.now {
		color: #fff;
		transform: scale(1.04);
	}

	.line-en {
		font-size: 25px;
		font-weight: 700;
		line-height: 1.3;
		letter-spacing: -0.01em;
	}

	.line-zh {
		font-size: 15px;
		line-height: 1.5;
		opacity: 0.75;
	}

	.line.now .line-zh {
		color: #c7d2fe;
		opacity: 1;
	}

	.empty {
		color: var(--ink-dim);
	}

	.locked {
		padding: 4px 4px 0 0;
	}

	@media (max-width: 900px) {
		.studio {
			grid-template-columns: 1fr;
			gap: 26px;
			padding: 26px 22px;
			border-radius: 22px;
		}

		.cover {
			max-width: 200px;
		}

		.meta {
			text-align: center;
			margin-top: 20px;
		}

		.lines {
			height: 46vh;
			min-height: 300px;
			flex: none;
		}

		.line-en {
			font-size: 20px;
		}

		.line.now {
			transform: none;
		}
	}

	@media (prefers-reduced-motion: reduce) {
		.cover,
		.line {
			transition: none;
		}
		.on-air.live i {
			animation: none;
		}
	}
</style>
