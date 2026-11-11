<script lang="ts">
	// Typing practice: the video plays one line, stops, and waits for you to type it.
	// Same rules as takeENGLISH's /type page (lib/typing-core.ts is that engine).
	import { onDestroy } from 'svelte';
	import { videoFileUrl, type VideoDetail, type TranscriptSegment } from '$lib/api';
	import {
		same,
		lineDone,
		wordAt,
		pickBlanks,
		autoBlankCount,
		wholeLine,
		needsSeek,
		seekTarget,
		lineIndexAt,
		createScore,
		type Blank,
		type TypingLine,
	} from '$lib/typing-core';
		import { mt, type ModeTextKey } from '$lib/modes/text';
	import type { Gate } from '$lib/modes/access';
	import ModeWall from './ModeWall.svelte';
	import TypeHud from './TypeHud.svelte';
	import TypeResult from './TypeResult.svelte';
	import TypeLineList from './TypeLineList.svelte';

	type BlankMode = 'auto' | 0 | 1 | 2;
	type Done = 'cleared' | 'revealed';
	interface Line extends TypingLine {
		zh: string;
	}

	let {
		video,
		segments,
		gate,
		startAt = 0,
		onTime = () => {},
	}: {
		video: VideoDetail;
		segments: TranscriptSegment[];
		gate: Gate;
		startAt?: number;
		onTime?: (seconds: number) => void;
	} = $props();

	const TICK_MS = 100;
	const SEEK_JUMP = 1.5; // a bigger time step than this means the user scrubbed
	const END_GRACE = 0.12; // let the last syllable finish before pausing
	const CORRECT_MS = 480;
	const BLANK_MODES: { id: BlankMode; label: ModeTextKey }[] = [
		{ id: 'auto', label: 'typeBlankAuto' },
		{ id: 1, label: 'typeBlankOne' },
		{ id: 2, label: 'typeBlankTwo' },
		{ id: 0, label: 'typeBlankAll' },
	];

	let lines = $derived<Line[]>(
		segments
			.map((s) => ({ text: s.text.trim(), start: s.start, end: s.end, zh: s.translation ?? '' }))
			.filter((l) => l.text.length > 0)
	);

	let videoEl = $state<HTMLVideoElement | null>(null);
	let inputEl = $state<HTMLInputElement | null>(null);

	let index = $state(0);
	let typed = $state('');
	let waiting = $state(false);
	let revealed = $state(false);
	let rejected = $state(false);
	let correct = $state(false);
	let finished = $state(false);
	let started = $state(false);
	let playing = $state(false);
	let focused = $state(false);
	let shaking = $state(false);
	let done = $state<(Done | undefined)[]>([]);
	let blankMode = $state<BlankMode>('auto');
	let autoPause = $state(true);
	let cover = $state(false);
	let showZh = $state(true);
	let showLines = $state(false);
	let stats = $state({ wpm: 0, accuracy: 100 });

	const score = createScore();
	let lastTime = 0;
	let ready = false;
	let correctTimer: ReturnType<typeof setTimeout> | undefined;

	let line = $derived<Line | null>(lines[index] ?? null);
	let cleared = $derived(done.filter((d) => d === 'cleared').length);
	let peeked = $derived(done.filter((d) => d === 'revealed').length);
	let src = $derived(video.filename ? videoFileUrl(video.filename) : '');

	let blanks = $derived.by<Blank[]>(() => {
		if (!line) return [];
		const count = blankMode === 'auto' ? autoBlankCount(line.text) : blankMode;
		return count === 0 ? wholeLine(line.text) : pickBlanks(line.text, count);
	});

	// What each character of the line looks like right now.
	let chars = $derived.by(() => {
		if (!line) return [];
		const text = line.text;
		const result: { shown: string; cls: string }[] = [];
		for (let i = 0; i < text.length; i += 1) {
			const expected = text[i];
			const hidden = blanks.some((b) => i >= b.from && i < b.to);
			if (i < typed.length) {
				const hit = same(typed[i], expected);
				// A miss shows what was actually typed — otherwise you cannot see where it went wrong.
				result.push({ shown: hit ? expected : typed[i] === ' ' ? '␣' : typed[i], cls: hit ? 'hit' : 'miss' });
				continue;
			}
			const cursor = i === typed.length ? ' cursor' : '';
			if (!hidden) result.push({ shown: expected, cls: `context${cursor}` });
			else if (revealed) result.push({ shown: expected, cls: `revealed${cursor}` });
			else result.push({ shown: expected === ' ' ? ' ' : '·', cls: `masked${cursor}` });
		}
		return result;
	});

	let hint = $derived(
		correct
			? mt('typeCorrect')
			: rejected
				? mt('typeRejected')
				: revealed
					? mt('typeRevealed')
					: waiting
						? mt('typeWaiting')
						: started
							? mt('typeHint')
							: mt('typeStart')
	);

	const now = () => videoEl?.currentTime ?? 0;
	const play = () => void videoEl?.play().catch(() => {});
	const pause = () => videoEl?.pause();

	function seek(seconds: number) {
		if (!videoEl) return;
		videoEl.currentTime = Math.max(seconds, 0);
		lastTime = videoEl.currentTime;
	}

	function focusInput() {
		inputEl?.focus({ preventScroll: true });
	}

	function refreshStats() {
		stats = { wpm: score.wpm(), accuracy: score.accuracy() };
	}

	function resetLine() {
		typed = '';
		waiting = false;
		revealed = false;
		rejected = false;
		if (inputEl) inputEl.value = '';
	}

	function goTo(next: number, { seek: explicit = false, resume = false } = {}) {
		finished = false;
		score.stop();
		clearTimeout(correctTimer);
		correct = false;
		index = Math.max(0, Math.min(next, lines.length - 1));
		resetLine();
		const target = lines[index];
		// The video follows the line being typed: rewind if it already ran past,
		// jump if it is far ahead, otherwise let it arrive on its own.
		if (needsSeek(now(), target, explicit)) seek(seekTarget(target));
		if (resume) play();
		focusInput();
	}

	function finish() {
		score.stop();
		finished = true;
		waiting = false;
		pause();
		refreshStats();
		// Finished everything this viewer gets: the score first, then the wall.
		if (gate.hiddenLines > 0) gate.open('lines');
	}

	function advance() {
		clearTimeout(correctTimer);
		const resume = waiting;
		correct = false;
		if (index + 1 >= lines.length) return finish();
		goTo(index + 1, { resume });
	}

	function markDone(how: Done) {
		if (done[index]) return;
		const next = [...done];
		next[index] = how;
		done = next;
	}

	function completeLine() {
		if (!line) return;
		markDone('cleared');
		score.stop();
		// A revealed line still turns green when typed out, but stays out of the WPM.
		if (!revealed) score.lineCleared(line.text);
		correct = true;
		refreshStats();
		clearTimeout(correctTimer);
		correctTimer = setTimeout(advance, CORRECT_MS);
	}

	function shake() {
		shaking = false;
		requestAnimationFrame(() => (shaking = true));
	}

	function handleInput(event: Event) {
		if (!inputEl) return;
		// Half-composed input-method text is not a keystroke yet.
		if ((event as InputEvent).isComposing) return;
		if (!line || correct) {
			inputEl.value = '';
			return;
		}
		const next = inputEl.value;
		rejected = false;
		started = true;
		// Score only single keystrokes: backspace is free, paste does not count.
		if (!revealed && next.length === typed.length + 1) {
			const at = next.length - 1;
			const hit = same(next[at], line.text[at]);
			score.key(hit, hit ? '' : wordAt(line.text, at));
			if (!hit) shake();
			refreshStats();
		}
		typed = next;
	}

	// Enter: pass only when the whole line is right; otherwise stay put.
	function submit() {
		if (!line) return;
		if (correct) return advance();
		if (lineDone(typed, line.text)) return completeLine();
		rejected = true;
		shake();
	}

	// Tab: show the answer, keep the correct prefix, stay on this line.
	function reveal() {
		if (!line || correct) return;
		revealed = true;
		rejected = false;
		let good = 0;
		while (good < typed.length && same(typed[good], line.text[good])) good += 1;
		typed = typed.slice(0, good);
		if (inputEl) inputEl.value = typed;
		markDone('revealed');
		focusInput();
	}

	const prevLine = () => goTo(index - 1, { seek: true });

	function nextLine() {
		if (index + 1 < lines.length) goTo(index + 1, { seek: true, resume: waiting });
		else finish();
	}

	// Replay keeps what is already typed — you replay because you missed a word.
	function replayLine() {
		if (!line || finished) return goTo(index, { seek: true, resume: true });
		seek(seekTarget(line));
		waiting = false;
		play();
		focusInput();
	}

	function restart() {
		score.reset();
		done = [];
		refreshStats();
		goTo(0, { seek: true, resume: true });
	}

	function handleKeydown(event: KeyboardEvent) {
		// An input method (注音) is mid-composition: Enter belongs to it, not to us.
		if (event.isComposing || event.keyCode === 229) return;
		// Shift+Tab must still move focus out — otherwise the box is a keyboard trap.
		if (event.key === 'Tab' && event.shiftKey) return;
		const handlers: Record<string, () => void> = {
			Enter: () => (event.shiftKey ? replayLine() : submit()),
			// preventDefault matters: otherwise focus walks to the next button.
			Tab: reveal,
			ArrowDown: nextLine,
			ArrowUp: prevLine,
			Escape: replayLine,
		};
		const handler = handlers[event.key];
		if (!handler) return;
		event.preventDefault();
		handler();
	}

	function togglePlay() {
		if (!videoEl) return;
		started = true;
		// Paused at the end of a line waiting for typing: plain play would be paused
		// again by the next tick, so Play means "say that line again".
		if (waiting) return replayLine();
		if (videoEl.paused) play();
		else pause();
		focusInput();
	}

	function handleLoaded() {
		if (!videoEl) return;
		if (startAt > 0 && startAt < (videoEl.duration || Infinity)) {
			seek(startAt);
			index = lineIndexAt(startAt, lines);
		}
		ready = true;
	}

	function tick() {
		// Not until the saved position is applied — reporting 0 early would erase it.
		if (!videoEl || !ready || finished) return;
		const time = now();
		const jumped = Math.abs(time - lastTime) > SEEK_JUMP;
		lastTime = time;
		onTime(time);

		// The user scrubbed: practice whichever line lives there.
		if (jumped) {
			const at = lineIndexAt(time, lines);
			if (at !== index) {
				// Drop a pending "correct → next line" hop, or it would skip the line scrubbed to.
				clearTimeout(correctTimer);
				correct = false;
				score.stop();
				index = at;
				resetLine();
			}
			return;
		}

		// Never play into the held-back part, even with end-of-line pause switched off.
		if (gate.stopAt !== null && time >= gate.stopAt) {
			pause();
			seek(Math.max(gate.stopAt - 0.3, 0));
			waiting = true;
			focusInput();
			return;
		}

		if (line && autoPause && !waiting && playing && time >= line.end + END_GRACE) {
			waiting = true;
			pause();
			focusInput();
		}
	}

	const timer = setInterval(tick, TICK_MS);

	onDestroy(() => {
		clearInterval(timer);
		clearTimeout(correctTimer);
	});
</script>

<section class="rig">
	<TypeHud wpm={stats.wpm} accuracy={stats.accuracy} {cleared} total={lines.length} />

	{#if lines.length === 0}
		<p class="empty">{mt('noTranscript')}</p>
	{:else}
		<div class="bench">
			<div class="screen">
				{#if src}
					<!-- svelte-ignore a11y_media_has_caption -->
					<video
						bind:this={videoEl}
						{src}
						playsinline
						preload="auto"
						onloadedmetadata={handleLoaded}
						onplay={() => (playing = true)}
						onpause={() => (playing = false)}
						onclick={togglePlay}
					></video>
				{/if}
				{#if cover}
					<div class="blind">{mt('typeCoverNote')}</div>
				{/if}
				<button class="screen-play" onclick={togglePlay} aria-label={playing ? mt('pause') : mt('play')}>
					{playing ? '❚❚' : '▶'}
				</button>
			</div>

			<div class="work">
				{#if finished}
					<TypeResult
						wpm={stats.wpm}
						accuracy={stats.accuracy}
						{cleared}
						total={lines.length}
						seconds={score.seconds()}
						{peeked}
						misses={score.top()}
						onRetry={restart}
					/>
				{:else}
					<!-- svelte-ignore a11y_click_events_have_key_events -->
					<div
						class="box"
						role="presentation"
						class:focused
						class:wrong={shaking}
						class:ok={correct}
						onclick={focusInput}
						onanimationend={() => (shaking = false)}
					>
						<p class="line" class:correct>
							{#each chars as ch, i (i)}<span class="ch {ch.cls}">{ch.shown}</span>{/each}
						</p>
						{#if showZh && line?.zh}
							<p class="zh">{line.zh}</p>
						{/if}
						<input
							bind:this={inputEl}
							class="input"
							type="text"
							autocomplete="off"
							autocapitalize="off"
							autocorrect="off"
							spellcheck="false"
							maxlength={line?.text.length ?? 0}
							aria-label={mt('modeType')}
							oninput={handleInput}
							onkeydown={handleKeydown}
							onfocus={() => (focused = true)}
							onblur={() => (focused = false)}
						/>
					</div>
					<p class="hint" class:alert={waiting || revealed || rejected} class:good={correct}>{hint}</p>
				{/if}

				<div class="keys">
					<button class="key primary" onclick={togglePlay}>{playing ? mt('pause') : mt('play')}</button>
					<button class="key" onclick={replayLine}>{mt('typeAgain')}</button>
					<button class="key" onclick={prevLine} disabled={index === 0}>{mt('typePrev')}</button>
					<button class="key" onclick={nextLine}>{mt('typeNext')}</button>
					<button class="key" onclick={reveal}>{mt('typeReveal')}</button>
				</div>
				<div class="keys">
					<select class="key" bind:value={blankMode} onchange={focusInput} aria-label={mt('typeBlankAuto')}>
						{#each BLANK_MODES as option (option.id)}
							<option value={option.id}>{mt(option.label)}</option>
						{/each}
					</select>
					<button class="key toggle" class:on={autoPause} aria-pressed={autoPause} onclick={() => (autoPause = !autoPause)}>{mt('typeAutoPause')}</button>
					<button class="key toggle" class:on={cover} aria-pressed={cover} onclick={() => (cover = !cover)}>{mt('typeCover')}</button>
					<button class="key toggle" class:on={showZh} aria-pressed={showZh} onclick={() => (showZh = !showZh)}>{mt('showZh')}</button>
					<button class="key toggle" class:on={showLines} aria-pressed={showLines} onclick={() => (showLines = !showLines)}>{mt('typeLines')}</button>
					<button class="key" onclick={restart}>{mt('typeRestart')}</button>
				</div>
			</div>
		</div>

		{#if gate.hiddenLines > 0}
			<div class="locked">
				<ModeWall tier={gate.tier} kind="lines" count={gate.hiddenLines} tone="dark" />
			</div>
		{/if}

		<TypeLineList {lines} {index} {done} open={showLines} onPick={(i) => goTo(i, { seek: true, resume: true })} />
	{/if}
</section>

<style>
	.rig {
		--ink: #e4e4ef;
		--ink-dim: #7c7c96;
		--line: #2a2a3a;
		--hit: #a5b4fc;
		--ok: #4ade80;
		--bad: #f87171;
		font-family: var(--font-mono);
		color: var(--ink);
		background: #0e0e16;
		border: 1px solid var(--line);
		border-radius: 12px;
		overflow: hidden;
		background-image: linear-gradient(rgba(129, 140, 248, 0.035) 1px, transparent 1px);
		background-size: 100% 28px;
	}

	.bench {
		display: grid;
		grid-template-columns: 220px 1fr;
		gap: 24px;
		padding: 24px;
		align-items: start;
	}

	.screen {
		position: relative;
		border-radius: 8px;
		overflow: hidden;
		background: #000;
		border: 1px solid var(--line);
	}

	.screen video {
		display: block;
		width: 100%;
		aspect-ratio: 9 / 16;
		max-height: 390px;
		object-fit: contain;
		cursor: pointer;
	}

	.blind {
		position: absolute;
		inset: 0;
		display: grid;
		place-items: center;
		padding: 16px;
		text-align: center;
		font-size: 12.5px;
		color: var(--ink-dim);
		background: repeating-linear-gradient(45deg, #12121c 0 10px, #171724 10px 20px);
	}

	.screen-play {
		position: absolute;
		right: 8px;
		bottom: 8px;
		width: 34px;
		height: 34px;
		border-radius: 6px;
		font-size: 12px;
		color: #0e0e16;
		background: var(--hit);
	}

	.work {
		min-width: 0;
	}

	.box {
		position: relative;
		padding: 26px 24px;
		border: 1px solid var(--line);
		border-radius: 10px;
		background: #12121c;
		cursor: text;
		transition: border-color 0.15s, box-shadow 0.15s;
	}

	.box.focused {
		border-color: #4f4f8f;
		box-shadow: 0 0 0 3px rgba(129, 140, 248, 0.14);
	}

	.box.ok {
		border-color: var(--ok);
	}

	.box.wrong {
		animation: shake 0.16s;
	}

	@keyframes shake {
		25% {
			transform: translateX(-4px);
		}
		75% {
			transform: translateX(4px);
		}
	}

	.line {
		font-size: 26px;
		line-height: 1.6;
		white-space: pre-wrap;
		overflow-wrap: break-word;
		min-height: 1.6em;
	}

	.ch.context {
		color: #8a8aa6;
	}
	.ch.masked {
		color: #45455c;
	}
	.ch.revealed {
		color: #7dd3fc;
	}
	.ch.hit {
		color: var(--hit);
	}
	.ch.miss {
		color: var(--bad);
		background: rgba(248, 113, 113, 0.16);
	}
	.ch.cursor {
		box-shadow: inset 0 -3px 0 var(--hit);
	}
	.box.focused .ch.cursor {
		animation: blink 1s step-end infinite;
	}

	@keyframes blink {
		50% {
			box-shadow: none;
		}
	}

	.line.correct {
		animation: pop 0.22s ease-out;
	}
	.line.correct .ch {
		color: var(--ok);
		background: none;
		box-shadow: none;
		animation: none;
	}

	@keyframes pop {
		50% {
			transform: scale(1.015);
		}
	}

	.zh {
		margin-top: 12px;
		font-family: 'Noto Sans TC', sans-serif;
		font-size: 14.5px;
		color: var(--ink-dim);
	}

	/* The real input sits on top, invisible: it owns the caret, IME and mobile keyboard. */
	.input {
		position: absolute;
		inset: 0;
		width: 100%;
		height: 100%;
		padding: 0;
		border: none;
		background: transparent;
		color: transparent;
		caret-color: transparent;
		font-size: 16px;
		opacity: 0.01;
		cursor: text;
	}

	.input:focus {
		outline: none;
	}

	.hint {
		min-height: 2.9em;
		margin: 12px 2px 16px;
		font-size: 12px;
		line-height: 1.6;
		color: var(--ink-dim);
	}

	.hint.alert {
		color: #fbbf24;
	}

	.hint.good {
		color: var(--ok);
	}

	.keys {
		display: flex;
		flex-wrap: wrap;
		gap: 8px;
		margin-top: 8px;
	}

	.key {
		padding: 7px 12px;
		font-family: var(--font-mono);
		font-size: 12.5px;
		color: var(--ink);
		background: #171724;
		border: 1px solid var(--line);
		border-bottom-width: 3px;
		border-radius: 6px;
		transition: transform 0.05s, border-color 0.15s, color 0.15s;
	}

	.key:hover:not(:disabled) {
		border-color: #4f4f8f;
	}

	.key:active:not(:disabled) {
		transform: translateY(2px);
		border-bottom-width: 1px;
		margin-bottom: 2px;
	}

	.key:disabled {
		opacity: 0.35;
		cursor: not-allowed;
	}

	.key.primary {
		color: #0e0e16;
		background: var(--hit);
		border-color: #6366f1;
		font-weight: 700;
	}

	.key.toggle {
		color: var(--ink-dim);
	}

	.key.toggle::before {
		content: '○ ';
	}

	.key.toggle.on {
		color: var(--hit);
		border-color: #4f4f8f;
	}

	.key.toggle.on::before {
		content: '● ';
	}

	select.key {
		appearance: none;
		padding-right: 26px;
		background-image: linear-gradient(45deg, transparent 50%, var(--ink-dim) 50%), linear-gradient(135deg, var(--ink-dim) 50%, transparent 50%);
		background-position: calc(100% - 14px) 55%, calc(100% - 9px) 55%;
		background-size: 5px 5px;
		background-repeat: no-repeat;
	}

	.locked {
		padding: 0 24px 24px;
		font-family: 'Inter', 'Noto Sans TC', sans-serif;
	}

	.empty {
		padding: 60px 0;
		text-align: center;
		color: var(--ink-dim);
	}

	@media (max-width: 760px) {
		.bench {
			grid-template-columns: 1fr;
			gap: 16px;
			padding: 14px;
		}

		.screen {
			width: 132px;
			margin: 0 auto;
		}

		.box {
			padding: 18px 16px;
		}

		.line {
			font-size: 20px;
		}
	}

	@media (prefers-reduced-motion: reduce) {
		.box.wrong,
		.line.correct,
		.box.focused .ch.cursor {
			animation: none;
		}
	}
</style>
