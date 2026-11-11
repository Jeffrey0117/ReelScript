<script lang="ts">
	// One video, six ways to use it. This page only loads the material and
	// decides which mode is on screen — every mode lives in its own component
	// and brings its own look.
	import { onMount, untrack } from 'svelte';
	import { page } from '$app/state';
	import { getVideo, translateVideo, appreciateVideo, type VideoDetail } from '$lib/api';
	import { t } from '$lib/i18n';
	import { getUser, onAuthChange } from '$lib/auth';
	import { loadSavedWords, resetWordbook } from '$lib/wordbook.svelte';
	import { mergeSentences, uniqueVocabulary } from '$lib/lesson';
	import { parseMode } from '$lib/modes/text';
	import { switchMode } from '$lib/modes/navigate';
	import { limitsFor, applyLimit, lockedAt, type Gate, type WallKind } from '$lib/modes/access';
	import ModeWall from '$lib/components/modes/ModeWall.svelte';
	import ModeSwitcher from '$lib/components/modes/ModeSwitcher.svelte';
	import VideoMode from '$lib/components/modes/VideoMode.svelte';
	import ReadMode from '$lib/components/modes/ReadMode.svelte';
	import PodcastMode from '$lib/components/modes/PodcastMode.svelte';
	import TypeMode from '$lib/components/modes/TypeMode.svelte';
	import VocabMode from '$lib/components/modes/VocabMode.svelte';
	import HandoutMode from '$lib/components/modes/HandoutMode.svelte';

	let video = $state<VideoDetail | null>(null);
	let loadError = $state('');
	let translating = $state(false);
	let appreciating = $state(false);

	let mode = $derived(parseMode(page.url.searchParams.get('mode')));

	// The wall. Visitors and free members get the first lines of a video in every
	// mode; the rest is held back here, so no mode can show it by accident.
	let limits = $derived(limitsFor(video?.access));
	let allSegments = $derived(video?.transcript?.segments ?? []);
	let visible = $derived(applyLimit(allSegments, limits.lines));
	let segments = $derived(
		limits.chinese ? visible.shown : visible.shown.map((s) => ({ ...s, translation: '' }))
	);
	let wall = $state<{ kind: WallKind; count: number } | null>(null);
	let gate = $derived<Gate>({
		tier: video?.access?.tier ?? 'guest',
		hiddenLines: visible.hidden,
		stopAt: lockedAt(allSegments, limits.lines),
		chinese: limits.chinese,
		print: limits.print,
		words: limits.words,
		open: (kind, count = visible.hidden) => (wall = { kind, count }),
	});

	let sentences = $derived(mergeSentences(segments));
	let vocabulary = $derived(uniqueVocabulary(segments));
	let hasTranslation = $derived(segments.some((s) => s.translation));

	// Where playback was when the user left a mode, so the next one resumes there.
	// Deliberately not reactive: it changes four times a second.
	// svelte-ignore non_reactive_update
	let position = 0;
	const rememberTime = (seconds: number) => {
		position = seconds;
	};

	async function load(id: string) {
		try {
			const fresh = await getVideo(id);
			// A slower answer for a video we already left must not replace the current one.
			if (id === page.params.id) video = fresh;
		} catch (e) {
			if (!video) loadError = e instanceof Error ? e.message : 'Failed to load';
		}
	}

	// Runs on arrival and again whenever the address points at another video.
	$effect(() => {
		const id = page.params.id ?? '';
		untrack(() => {
			if (video && video.id !== id) video = null;
			wall = null;
			void load(id);
		});
	});

	onMount(() => {
		if (getUser()) void loadSavedWords();
		let first = true;
		onAuthChange((u) => {
			if (u) void loadSavedWords();
			else resetWordbook();
			// Signing in or out changes what this person may see — ask again.
			if (!first) {
				wall = null;
				void load(page.params.id ?? '');
			}
			first = false;
		});
	});

	async function handleTranslate(): Promise<boolean> {
		if (!video?.transcript || translating) return false;
		translating = true;
		try {
			const result = await translateVideo(video.id);
			if (!result.success || !video?.transcript) return false;
			video = { ...video, transcript: { ...video.transcript, segments: result.segments } };
			return true;
		} catch (e) {
			alert(e instanceof Error ? e.message : 'Translation failed');
			return false;
		} finally {
			translating = false;
		}
	}

	async function handleAppreciate(): Promise<void> {
		if (!video?.transcript || appreciating) return;
		appreciating = true;
		try {
			const result = await appreciateVideo(video.id);
			if (result.success && video?.transcript) {
				video = { ...video, transcript: { ...video.transcript, appreciation: result.appreciation } };
			}
		} catch (e) {
			alert(e instanceof Error ? e.message : 'Failed');
		} finally {
			appreciating = false;
		}
	}
</script>

<svelte:head>
	<title>{video?.title || t('loading')} - ReelScript</title>
</svelte:head>

{#if loadError}
	<div class="loading">{loadError}</div>
{:else if !video}
	<div class="loading">{t('loading')}</div>
{:else}
	<div class="mode-shell" data-mode={mode}>
		<!-- On wide screens the modes live in the site header (see +layout.svelte). -->
		<div class="inline-switch">
			<ModeSwitcher {mode} onSwitch={(next) => switchMode(page.url, next)} />
		</div>

		{#key mode}
			<div class="mode-stage">
				{#if mode === 'read'}
					<ReadMode {video} {sentences} {hasTranslation} {translating} {gate} onTranslate={handleTranslate} />
				{:else if mode === 'podcast'}
					<PodcastMode
						{video}
						{segments}
						{hasTranslation}
						{gate}
						startAt={position}
						onTime={rememberTime}
					/>
				{:else if mode === 'type'}
					<TypeMode {video} {segments} {gate} startAt={position} onTime={rememberTime} />
				{:else if mode === 'vocab'}
					<VocabMode {video} {segments} {sentences} {vocabulary} {gate} />
				{:else if mode === 'handout'}
					<HandoutMode
						{video}
						{sentences}
						{vocabulary}
						{appreciating}
						{gate}
						onAppreciate={handleAppreciate}
					/>
				{:else}
					<VideoMode
						{video}
						{segments}
						{gate}
						{vocabulary}
						{hasTranslation}
						{translating}
						onTranslate={handleTranslate}
						startAt={position}
						onTime={rememberTime}
					/>
				{/if}
			</div>
		{/key}
	</div>

	{#if wall}
		<ModeWall modal tier={gate.tier} kind={wall.kind} count={wall.count} onClose={() => (wall = null)} />
	{/if}
{/if}

<style>
	.loading {
		text-align: center;
		padding: 80px 0;
		color: var(--text-dim);
	}

	.mode-shell {
		display: flex;
		flex-direction: column;
		gap: 24px;
	}

	.inline-switch {
		display: none;
	}

	@media (max-width: 900px) {
		.inline-switch {
			display: contents;
		}
	}

	.mode-stage {
		animation: stage-in 0.28s ease-out;
	}

	@keyframes stage-in {
		from {
			opacity: 0;
			transform: translateY(8px);
		}
		to {
			opacity: 1;
			transform: none;
		}
	}

	@media (prefers-reduced-motion: reduce) {
		.mode-stage {
			animation: none;
		}
	}

	@media (max-width: 640px) {
		.mode-shell {
			gap: 16px;
		}
	}

	@media print {
		.mode-stage {
			animation: none;
		}
	}
</style>
