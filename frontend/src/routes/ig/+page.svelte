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
		type TranscriptSegment,
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
						}
						el?.play().catch(() => {});
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

	function seekTo(segment: TranscriptSegment) {
		if (!currentVideo) return;
		const el = videoEls.get(currentVideo.id);
		if (!el) return;
		el.currentTime = segment.start;
		el.play().catch(() => {});
	}

	function formatTime(seconds: number): string {
		const m = Math.floor(seconds / 60);
		const s = Math.floor(seconds % 60);
		return `${m}:${s.toString().padStart(2, '0')}`;
	}

	function registerVideo(videoId: string, el: HTMLVideoElement | null) {
		if (el && !videoEls.has(videoId)) {
			videoEls = new Map([...videoEls, [videoId, el]]);
		}
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
							preload={Math.abs(i - currentIndex) <= 1 ? 'metadata' : 'none'}
							poster={video.thumbnail ? thumbnailUrl(video.thumbnail) : undefined}
							ontimeupdate={() => handleTimeUpdate(video.id)}
							onloadedmetadata={(e) => registerVideo(video.id, e.currentTarget as HTMLVideoElement)}
						>
							<source src={videoFileUrl(detail.filename)} type="video/mp4" />
						</video>
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
					{t('transcript')}
					{#if segments.length > 0}
						<span class="ig-seg-count">{segments.length} {t('segments')}</span>
					{/if}
				</span>
			</div>

			<div class="ig-sheet-content" bind:this={transcriptEl}>
				{#if segments.length === 0}
					<p class="ig-no-transcript">{t('noTranscript')}</p>
				{:else}
					{#each segments as seg, i (seg.index)}
						<!-- svelte-ignore a11y_click_events_have_key_events -->
						<!-- svelte-ignore a11y_no_static_element_interactions -->
						<div
							class="ig-segment"
							class:active={i === activeSegmentIndex}
							data-seg-idx={i}
							onclick={() => seekTo(seg)}
						>
							<span class="ig-seg-time">{formatTime(seg.start)}</span>
							<span class="ig-seg-text">{seg.text}</span>
							{#if seg.translation}
								<span class="ig-seg-translation">{seg.translation}</span>
							{/if}
						</div>
					{/each}
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
		background: var(--bg-card, #12121a);
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
		font-size: 14px;
		font-weight: 600;
		color: var(--text, #e4e4ef);
		display: flex;
		align-items: center;
		gap: 8px;
	}

	.ig-seg-count {
		font-size: 12px;
		font-weight: 400;
		color: var(--text-dim, #8888a0);
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

	/* Segments */
	.ig-segment {
		display: flex;
		flex-wrap: wrap;
		align-items: baseline;
		gap: 8px;
		padding: 10px 12px;
		border-radius: 8px;
		cursor: pointer;
		transition: background 0.15s;
	}

	.ig-segment:hover {
		background: rgba(255, 255, 255, 0.05);
	}

	.ig-segment.active {
		background: rgba(99, 102, 241, 0.15);
	}

	.ig-seg-time {
		font-size: 12px;
		color: var(--accent, #6366f1);
		font-variant-numeric: tabular-nums;
		flex-shrink: 0;
		min-width: 36px;
	}

	.ig-seg-text {
		font-size: 15px;
		color: var(--text, #e4e4ef);
		line-height: 1.5;
		flex: 1;
		min-width: 0;
	}

	.ig-seg-translation {
		width: 100%;
		font-size: 13px;
		color: var(--text-dim, #8888a0);
		padding-left: 44px;
		line-height: 1.4;
	}
</style>
