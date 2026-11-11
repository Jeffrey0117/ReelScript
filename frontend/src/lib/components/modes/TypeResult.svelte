<script lang="ts">
	// The scoreboard shown when every line of the typing practice is done.
	import { formatTime } from '$lib/lesson';
	import { mt } from '$lib/modes/text';

	let {
		wpm,
		accuracy,
		cleared,
		total,
		seconds,
		peeked,
		misses,
		onRetry,
	}: {
		wpm: number;
		accuracy: number;
		cleared: number;
		total: number;
		seconds: number;
		peeked: number;
		misses: [string, number][];
		onRetry: () => void;
	} = $props();
</script>

<div class="result">
	<h2>{mt('typeResultTitle')}</h2>
	<div class="grid">
		<p><b>{wpm}</b><span>{mt('typeWpm')}</span></p>
		<p><b>{accuracy}%</b><span>{mt('typeAccuracy')}</span></p>
		<p><b>{cleared}/{total}</b><span>{mt('typeCleared')}</span></p>
		<p><b>{formatTime(seconds)}</b><span>⏱</span></p>
	</div>
	{#if peeked > 0}
		<p class="note">{peeked} {mt('typeResultPeeked')}</p>
	{/if}
	{#if misses.length > 0}
		<p class="note">
			{mt('typeMisses')}：
			{#each misses as [word, times] (word)}
				<code>{word} ×{times}</code>
			{/each}
		</p>
	{/if}
	<button class="retry" onclick={onRetry}>{mt('typeRetry')}</button>
</div>

<style>
	.result {
		padding: 26px 24px;
		border: 1px solid #4ade80;
		border-radius: 10px;
		background: #12121c;
		margin-bottom: 16px;
	}

	h2 {
		font-size: 15px;
		color: #4ade80;
		margin-bottom: 18px;
	}

	h2::before {
		content: '✓ ';
	}

	.grid {
		display: grid;
		grid-template-columns: repeat(4, 1fr);
		gap: 12px;
		margin-bottom: 16px;
	}

	.grid p {
		display: flex;
		flex-direction: column;
		gap: 2px;
	}

	.grid b {
		font-size: 28px;
		font-variant-numeric: tabular-nums;
	}

	.grid span {
		font-size: 11px;
		letter-spacing: 0.08em;
		text-transform: uppercase;
		color: #7c7c96;
	}

	.note {
		font-size: 12.5px;
		color: #7c7c96;
		margin-bottom: 14px;
		line-height: 2;
	}

	.note code {
		margin-right: 8px;
		padding: 2px 7px;
		border-radius: 4px;
		color: #f87171;
		background: rgba(248, 113, 113, 0.12);
	}

	.retry {
		padding: 7px 14px;
		font-family: var(--font-mono);
		font-size: 12.5px;
		font-weight: 700;
		color: #0e0e16;
		background: #a5b4fc;
		border: 1px solid #6366f1;
		border-bottom-width: 3px;
		border-radius: 6px;
	}

	@media (max-width: 760px) {
		.grid {
			grid-template-columns: repeat(2, 1fr);
		}
	}
</style>
