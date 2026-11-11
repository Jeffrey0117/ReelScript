<script lang="ts">
	// Every line of the typing practice. Lines not practiced yet stay blurred —
	// they are the answers — unless the user asks to see the text.
	let {
		lines,
		index,
		done,
		open,
		onPick,
	}: {
		lines: { text: string }[];
		index: number;
		done: ('cleared' | 'revealed' | undefined)[];
		open: boolean;
		onPick: (index: number) => void;
	} = $props();

	let listEl = $state<HTMLDivElement | null>(null);

	// Keep the current line in view inside the list (never scroll the page).
	$effect(() => {
		const row = listEl?.children[index] as HTMLElement | undefined;
		if (!listEl || !row) return;
		listEl.scrollTop = Math.max(0, row.offsetTop - listEl.clientHeight / 2 + row.offsetHeight / 2);
	});
</script>

<div class="list" class:open bind:this={listEl}>
	{#each lines as item, i (i)}
		<button
			class="row"
			class:active={i === index}
			class:cleared={done[i] === 'cleared'}
			class:peeked={done[i] === 'revealed'}
			onclick={() => onPick(i)}
		>
			<span class="no">{String(i + 1).padStart(2, '0')}</span>
			<span class="text">{item.text}</span>
		</button>
	{/each}
</div>

<style>
	.list {
		max-height: 230px;
		overflow-y: auto;
		position: relative;
		border-top: 1px solid #2a2a3a;
		padding: 8px 12px;
		background: #0b0b12;
	}

	.row {
		display: flex;
		gap: 12px;
		width: 100%;
		padding: 5px 10px;
		text-align: left;
		font-family: var(--font-mono);
		font-size: 13px;
		color: #7c7c96;
		border-radius: 4px;
	}

	.row:hover {
		background: #171724;
	}

	.no {
		color: #45455c;
		flex-shrink: 0;
	}

	.text {
		filter: blur(5px);
		user-select: none;
		transition: filter 0.2s;
	}

	.list.open .text,
	.row.cleared .text,
	.row.peeked .text {
		filter: none;
		user-select: auto;
	}

	.row.active {
		background: rgba(129, 140, 248, 0.12);
		color: #e4e4ef;
	}

	.row.active .no {
		color: #a5b4fc;
	}

	.row.cleared {
		color: #4ade80;
	}

	.row.peeked {
		color: #7dd3fc;
	}
</style>
