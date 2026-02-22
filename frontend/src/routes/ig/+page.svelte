<script lang="ts">
	import { onMount, onDestroy, tick } from 'svelte';
	import { goto } from '$app/navigation';
	import {
		listVideos,
		getVideo,
		videoFileUrl,
		thumbnailUrl,
		type Video,
		type VideoDetail,
	} from '$lib/api';
	import { t } from '$lib/i18n';

	// --- State ---
	let videos = $state<Video[]>([]);
	let currentIndex = $state(0);
	let videoDetails = $state<Map<string, VideoDetail>>(new Map());
	let videoEls = $state<Map<string, HTMLVideoElement>>(new Map());
	let currentTime = $state(0);
	let activeSegmentIndex = $state(-1);
	let sheetState = $state<'peek' | 'half' | 'full'>('half');
	let paused = $state(false);
	let playbackRate = $state(1);
	let loading = $state(true);

	// Scroll container ref
	let scrollContainer: HTMLDivElement | undefined = $state();
	let observer: IntersectionObserver | undefined;
	// Bottom sheet drag state
	let isDragging = $state(false);
	let dragStartY = 0;
	let dragStartTranslate = 0;
	let currentTranslateY = $state(0);

	// Transcript container ref for auto-scroll
	let transcriptEl: HTMLDivElement | undefined = $state();

	// Derived
	let currentVideo = $derived(videos[currentIndex]);
	let currentDetail = $derived(
		currentVideo ? videoDetails.get(currentVideo.id) : undefined
	);
	let segments = $derived(currentDetail?.transcript?.segments ?? []);
	let fullText = $derived(segments.map((s) => s.text).join(' '));
	let fullTranslation = $derived(
		segments.some((s) => s.translation)
			? segments.map((s) => s.translation || '').join('')
			: ''
	);
	let totalCount = $derived(videos.length);

	// Sheet heights (vh)
	const SHEET_PEEK = 60; // px
	const SHEET_HALF_VH = 30;
	const SHEET_FULL_VH = 80;

	function getSheetTranslateY(state: 'peek' | 'half' | 'full'): number {
		const vh = window.innerHeight;
		if (state === 'peek') return vh - SHEET_PEEK;
		if (state === 'half') return vh - (vh * SHEET_HALF_VH) / 100;
		return vh - (vh * SHEET_FULL_VH) / 100;
	}

	function snapToNearest(y: number): 'peek' | 'half' | 'full' {
		const vh = window.innerHeight;
		const peekY = vh - SHEET_PEEK;
		const halfY = vh - (vh * SHEET_HALF_VH) / 100;
		const fullY = vh - (vh * SHEET_FULL_VH) / 100;

		const dists = [
			{ state: 'peek' as const, d: Math.abs(y - peekY) },
			{ state: 'half' as const, d: Math.abs(y - halfY) },
			{ state: 'full' as const, d: Math.abs(y - fullY) },
		];
		dists.sort((a, b) => a.d - b.d);
		return dists[0].state;
	}

	// --- Lifecycle ---
	onMount(async () => {
		const allVideos = await listVideos();
		videos = allVideos.filter((v) => v.status === 'ready');
		loading = false;

		if (videos.length === 0) return;

		// Check for ?start=VIDEO_ID
		const startId = new URL(window.location.href).searchParams.get('start');
		if (startId) {
			const idx = videos.findIndex((v) => v.id === startId);
			if (idx >= 0) currentIndex = idx;
		}

		// Initialize sheet position
		currentTranslateY = getSheetTranslateY('half');

		// Set up IntersectionObserver and scroll to start
		await tick();
		setupObserver();

		// Scroll to start video if not first
		if (currentIndex > 0 && scrollContainer) {
			const slide = scrollContainer.children[currentIndex] as HTMLElement;
			slide?.scrollIntoView();
		}

		// Load initial video detail
		await loadDetail(videos[currentIndex].id);
	});

	onDestroy(() => {
		observer?.disconnect();
	});

	function getVideoEl(slide: Element, videoId: string): HTMLVideoElement | undefined {
		if (videoEls.has(videoId)) return videoEls.get(videoId);
		const el = slide.querySelector('video') as HTMLVideoElement | null;
		if (el) registerVideo(videoId, el);
		return el ?? undefined;
	}

	function setupObserver() {
		if (!scrollContainer) return;
		observer = new IntersectionObserver(
			(entries) => {
				for (const entry of entries) {
					const videoId = entry.target.getAttribute('data-video-id');
					if (!videoId) continue;

					const el = getVideoEl(entry.target, videoId);
					if (entry.isIntersecting) {
						const idx = videos.findIndex((v) => v.id === videoId);
						if (idx >= 0) {
							currentIndex = idx;
							activeSegmentIndex = -1;
							currentTime = 0;
							paused = false;
							playbackRate = 1;
						}
						if (el) {
							el.playbackRate = 1;
							el.play().catch(() => {});
						}
						loadDetail(videoId);
					} else {
						el?.pause();
					}
				}
			},
			{
				root: scrollContainer,
				threshold: 0.7,
			}
		);

		// Observe all slides
		const slides = scrollContainer.querySelectorAll('.ig-slide');
		slides.forEach((slide) => observer!.observe(slide));
	}

	async function loadDetail(videoId: string) {
		if (videoDetails.has(videoId)) return;
		try {
			const detail = await getVideo(videoId);
			videoDetails = new Map([...videoDetails, [videoId, detail]]);
		} catch {
			// ignore
		}
	}

	// --- Video time sync ---
	function handleTimeUpdate(videoId: string) {
		const el = videoEls.get(videoId);
		if (!el || videoId !== currentVideo?.id) return;
		currentTime = el.currentTime;

		const detail = videoDetails.get(videoId);
		if (!detail?.transcript?.segments) {
			activeSegmentIndex = -1;
			return;
		}

		const idx = detail.transcript.segments.findIndex(
			(s) => currentTime >= s.start && currentTime < s.end
		);
		if (idx !== activeSegmentIndex) {
			activeSegmentIndex = idx;
			// Auto-scroll transcript
			if (idx >= 0 && transcriptEl) {
				const activeEl = transcriptEl.querySelector(`[data-seg-idx="${idx}"]`);
				activeEl?.scrollIntoView({ behavior: 'smooth', block: 'center' });
			}
		}
	}


	function registerVideo(videoId: string, el: HTMLVideoElement | null) {
		if (el && !videoEls.has(videoId)) {
			videoEls = new Map([...videoEls, [videoId, el]]);
		}
	}

	// --- Tap to pause/play, long-press to speed up ---
	let longPressTimer: ReturnType<typeof setTimeout> | null = null;
	let isLongPress = false;

	function handleVideoPointerDown() {
		isLongPress = false;
		longPressTimer = setTimeout(() => {
			isLongPress = true;
			setPlaybackRate(2);
		}, 400);
	}

	function handleVideoPointerUp() {
		if (longPressTimer) {
			clearTimeout(longPressTimer);
			longPressTimer = null;
		}
		if (isLongPress) {
			// Release long press → back to normal speed
			setPlaybackRate(1);
			isLongPress = false;
			return;
		}
		// Short tap → toggle play/pause
		togglePlay();
	}

	function togglePlay() {
		if (!currentVideo) return;
		const el = videoEls.get(currentVideo.id);
		if (!el) return;
		if (el.paused) {
			el.play().catch(() => {});
			paused = false;
		} else {
			el.pause();
			paused = true;
		}
	}

	function setPlaybackRate(rate: number) {
		playbackRate = rate;
		if (!currentVideo) return;
		const el = videoEls.get(currentVideo.id);
		if (el) el.playbackRate = rate;
	}

	// --- Bottom sheet drag ---
	function onDragStart(clientY: number) {
		isDragging = true;
		dragStartY = clientY;
		dragStartTranslate = currentTranslateY;
	}

	function onDragMove(clientY: number) {
		if (!isDragging) return;
		const dy = clientY - dragStartY;
		const newY = dragStartTranslate + dy;
		// Clamp: don't go above full or below bottom of screen
		const minY = getSheetTranslateY('full');
		const maxY = window.innerHeight - 20;
		currentTranslateY = Math.max(minY, Math.min(maxY, newY));
	}

	function onDragEnd() {
		if (!isDragging) return;
		isDragging = false;
		sheetState = snapToNearest(currentTranslateY);
		currentTranslateY = getSheetTranslateY(sheetState);
	}

	// Touch handlers
	function handleTouchStart(e: TouchEvent) {
		onDragStart(e.touches[0].clientY);
	}

	function handleTouchMove(e: TouchEvent) {
		e.preventDefault();
		onDragMove(e.touches[0].clientY);
	}

	function handleTouchEnd() {
		onDragEnd();
	}

	// Mouse handlers
	function handleMouseDown(e: MouseEvent) {
		e.preventDefault();
		onDragStart(e.clientY);
		window.addEventListener('mousemove', handleMouseMove);
		window.addEventListener('mouseup', handleMouseUp);
	}

	function handleMouseMove(e: MouseEvent) {
		onDragMove(e.clientY);
	}

	function handleMouseUp() {
		onDragEnd();
		window.removeEventListener('mousemove', handleMouseMove);
		window.removeEventListener('mouseup', handleMouseUp);
	}

	function toggleSheet() {
		if (sheetState === 'peek') {
			sheetState = 'half';
		} else if (sheetState === 'half') {
			sheetState = 'full';
		} else {
			sheetState = 'peek';
		}
		currentTranslateY = getSheetTranslateY(sheetState);
	}
</script>

<svelte:head>
	<title>IG Mode - ReelScript</title>
</svelte:head>

<div class="ig-container">
	{#if loading}
		<div class="ig-loading">
			<p>{t('loading')}</p>
		</div>
	{:else if videos.length === 0}
		<div class="ig-empty">
			<p>{t('noReadyVideos')}</p>
			<button class="btn btn-ghost" onclick={() => goto('/')}>
				{t('exitIgMode')}
			</button>
		</div>
	{:else}
		<!-- Floating header -->
		<div class="ig-header">
			<button class="ig-back" onclick={() => goto('/')}>
				<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
					<path d="M15 18l-6-6 6-6"/>
				</svg>
				{t('exitIgMode')}
			</button>
			<div class="ig-header-info">
				<span class="ig-title">{currentVideo?.title || t('untitled')}</span>
				<span class="ig-counter">{currentIndex + 1} / {totalCount}</span>
			</div>
		</div>

		<!-- Scroll-snap container -->
		<div class="ig-scroll" bind:this={scrollContainer}>
			{#each videos as video, i (video.id)}
				{@const detail = videoDetails.get(video.id)}
				<div class="ig-slide" data-video-id={video.id}>
					{#if detail?.filename}
						<!-- svelte-ignore a11y_media_has_caption -->
						<video
							playsinline
							muted
							loop
							preload={Math.abs(i - currentIndex) <= 1 ? 'metadata' : 'none'}
							poster={video.thumbnail ? thumbnailUrl(video.thumbnail) : undefined}
							ontimeupdate={() => handleTimeUpdate(video.id)}
							onloadedmetadata={(e) => registerVideo(video.id, e.currentTarget as HTMLVideoElement)}
							onpointerdown={handleVideoPointerDown}
							onpointerup={handleVideoPointerUp}
						>
							<source src={videoFileUrl(detail.filename)} type="video/mp4" />
						</video>
						{#if paused && video.id === currentVideo?.id}
							<div class="ig-play-overlay">
								<svg width="48" height="48" viewBox="0 0 24 24" fill="white" opacity="0.8">
									<path d="M8 5v14l11-7z"/>
								</svg>
							</div>
						{/if}
						{#if playbackRate > 1 && video.id === currentVideo?.id}
							<div class="ig-speed-overlay">{playbackRate}x</div>
						{/if}
					{:else if video.thumbnail}
						<img class="ig-poster" src={thumbnailUrl(video.thumbnail)} alt="" />
					{:else}
						<div class="ig-placeholder"></div>
					{/if}
				</div>
			{/each}
		</div>

		<!-- Bottom sheet -->
		<div
			class="ig-sheet"
			class:dragging={isDragging}
			style="transform: translateY({currentTranslateY}px)"
		>
			<!-- svelte-ignore a11y_no_static_element_interactions -->
			<div
				class="ig-sheet-handle"
				ontouchstart={handleTouchStart}
				ontouchmove={handleTouchMove}
				ontouchend={handleTouchEnd}
				onmousedown={handleMouseDown}
				onclick={toggleSheet}
			>
				<div class="ig-handle-bar"></div>
				<span class="ig-sheet-title">
					{t('fullText')}
				</span>
			</div>

			<div class="ig-sheet-content" bind:this={transcriptEl}>
				{#if segments.length === 0}
					<p class="ig-no-transcript">{t('noTranscript')}</p>
				{:else}
					<div class="ig-article">
						<p class="ig-article-en">{fullText}</p>
						{#if fullTranslation}
							<p class="ig-article-zh">{fullTranslation}</p>
						{/if}
					</div>
				{/if}
			</div>
		</div>
	{/if}
</div>

<style>
	.ig-container {
		position: fixed;
		inset: 0;
		z-index: 500;
		background: #000;
		color: #fff;
		overflow: hidden;
	}

	.ig-loading,
	.ig-empty {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		height: 100%;
		gap: 16px;
		color: var(--text-dim);
	}

	/* Floating header */
	.ig-header {
		position: fixed;
		top: 0;
		left: 0;
		right: 0;
		z-index: 520;
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 12px 16px;
		background: linear-gradient(to bottom, rgba(0, 0, 0, 0.7) 0%, transparent 100%);
		pointer-events: none;
	}

	.ig-header > * {
		pointer-events: auto;
	}

	.ig-back {
		display: flex;
		align-items: center;
		gap: 4px;
		color: #fff;
		font-size: 15px;
		font-weight: 500;
		background: none;
		border: none;
		cursor: pointer;
		padding: 4px 8px;
		border-radius: 8px;
	}

	.ig-back:hover {
		background: rgba(255, 255, 255, 0.15);
	}

	.ig-header-info {
		display: flex;
		flex-direction: column;
		align-items: flex-end;
		gap: 2px;
	}

	.ig-title {
		font-size: 14px;
		font-weight: 600;
		max-width: 200px;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	.ig-counter {
		font-size: 12px;
		color: rgba(255, 255, 255, 0.6);
		font-variant-numeric: tabular-nums;
	}

	/* Scroll-snap slides */
	.ig-scroll {
		width: 100%;
		height: 100%;
		overflow-y: scroll;
		scroll-snap-type: y mandatory;
		-webkit-overflow-scrolling: touch;
	}

	.ig-scroll::-webkit-scrollbar {
		display: none;
	}

	.ig-slide {
		position: relative;
		height: 100vh;
		height: 100dvh;
		scroll-snap-align: start;
		display: flex;
		align-items: center;
		justify-content: center;
		background: #000;
	}

	.ig-slide video {
		width: 100%;
		height: 70%;
		object-fit: contain;
		background: #000;
	}

	.ig-poster {
		width: 100%;
		height: 70%;
		object-fit: contain;
	}

	.ig-placeholder {
		width: 100%;
		height: 70%;
		background: #111;
	}

	/* Bottom sheet */
	.ig-sheet {
		position: fixed;
		left: 0;
		right: 0;
		top: 0;
		height: 100vh;
		height: 100dvh;
		z-index: 510;
		background: rgba(18, 18, 26, 0.85);
		backdrop-filter: blur(12px);
		-webkit-backdrop-filter: blur(12px);
		border-radius: 16px 16px 0 0;
		display: flex;
		flex-direction: column;
		transition: transform 0.3s ease;
		will-change: transform;
	}

	.ig-sheet.dragging {
		transition: none;
	}

	.ig-sheet-handle {
		flex-shrink: 0;
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 8px;
		padding: 12px 16px 8px;
		cursor: grab;
		user-select: none;
		touch-action: none;
	}

	.ig-handle-bar {
		width: 36px;
		height: 4px;
		border-radius: 2px;
		background: rgba(255, 255, 255, 0.3);
	}

	.ig-sheet-title {
		font-size: 12px;
		font-weight: 600;
		color: rgba(228, 228, 239, 0.8);
		display: flex;
		align-items: center;
		gap: 8px;
	}

	.ig-sheet-content {
		flex: 1;
		overflow-y: auto;
		padding: 4px 16px 24px;
		-webkit-overflow-scrolling: touch;
	}

	.ig-no-transcript {
		color: var(--text-dim, #8888a0);
		text-align: center;
		padding: 24px 0;
		font-size: 14px;
	}

	/* Article-style transcript */
	.ig-article {
		padding: 4px 0 24px;
	}

	.ig-article-en {
		font-size: 13px;
		line-height: 1.7;
		color: rgba(228, 228, 239, 0.9);
		margin: 0;
	}

	.ig-article-zh {
		font-size: 12px;
		line-height: 1.7;
		color: rgba(136, 136, 160, 0.85);
		margin: 16px 0 0;
		padding-top: 16px;
		border-top: 1px solid rgba(255, 255, 255, 0.08);
	}

	/* Video overlays */
	.ig-play-overlay {
		position: absolute;
		inset: 0;
		display: flex;
		align-items: center;
		justify-content: center;
		pointer-events: none;
	}

	.ig-speed-overlay {
		position: absolute;
		top: 80px;
		left: 50%;
		transform: translateX(-50%);
		background: rgba(0, 0, 0, 0.6);
		color: #fff;
		font-size: 14px;
		font-weight: 600;
		padding: 4px 12px;
		border-radius: 16px;
		pointer-events: none;
	}
</style>
