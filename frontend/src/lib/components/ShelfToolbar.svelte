<script lang="ts">
	// Search box and source chips above "my videos".
	import { getLocale } from '$lib/i18n';
	import type { SourceFilter } from '$lib/video-shelf';

	let {
		query = $bindable(''),
		source = $bindable<SourceFilter>('all'),
		counts,
		shown,
	}: {
		query?: string;
		source?: SourceFilter;
		counts: Record<SourceFilter, number>;
		shown: number;
	} = $props();

	const zh = getLocale() !== 'en';
	const text = {
		search: zh ? '搜尋標題或頻道' : 'Search title or channel',
		all: zh ? '全部' : 'All',
		clear: zh ? '清除' : 'Clear',
		found: zh ? '支符合' : 'found',
	};

	const chips: { id: SourceFilter; label: string }[] = [
		{ id: 'all', label: text.all },
		{ id: 'ig', label: 'Instagram' },
		{ id: 'youtube', label: 'YouTube' },
	];
	// A chip for a source the member has nothing from is only noise.
	let visibleChips = $derived(chips.filter((chip) => chip.id === 'all' || counts[chip.id] > 0));
</script>

<div class="toolbar">
	<label class="search">
		<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><circle cx="11" cy="11" r="7"/><path d="M20 20l-3.5-3.5"/></svg>
		<input type="search" bind:value={query} placeholder={text.search} aria-label={text.search} />
		{#if query}
			<button class="clear" onclick={() => (query = '')} aria-label={text.clear}>×</button>
		{/if}
	</label>

	{#if visibleChips.length > 2}
		<div class="chips" role="tablist">
			{#each visibleChips as chip (chip.id)}
				<button role="tab" aria-selected={source === chip.id} class:on={source === chip.id} onclick={() => (source = chip.id)}>
					{chip.label}<span>{counts[chip.id]}</span>
				</button>
			{/each}
		</div>
	{/if}

	{#if query}
		<span class="found">{shown} {text.found}</span>
	{/if}
</div>

<style>
	.toolbar {
		display: flex;
		align-items: center;
		flex-wrap: wrap;
		gap: 10px 14px;
		margin-bottom: 18px;
	}

	.search {
		display: flex;
		align-items: center;
		gap: 8px;
		flex: 1 1 240px;
		max-width: 360px;
		padding: 0 12px;
		height: 38px;
		color: var(--text-dim);
		background: var(--bg-card);
		border: 1px solid var(--border);
		border-radius: 999px;
		transition: border-color 0.15s;
	}

	.search:focus-within {
		border-color: var(--accent);
	}

	.search input {
		flex: 1;
		min-width: 0;
		padding: 0;
		border: none;
		background: none;
		font-size: 14px;
		color: var(--text);
		outline: none;
	}

	.search input::-webkit-search-cancel-button {
		display: none;
	}

	.clear {
		font-size: 18px;
		line-height: 1;
		color: var(--text-dim);
	}

	.chips {
		display: flex;
		gap: 6px;
	}

	.chips button {
		display: inline-flex;
		align-items: center;
		gap: 6px;
		height: 34px;
		padding: 0 12px;
		font-size: 13px;
		font-weight: 600;
		color: var(--text-dim);
		border: 1px solid var(--border);
		border-radius: 999px;
		background: var(--bg-card);
	}

	.chips button span {
		font-size: 12px;
		font-weight: 500;
		font-variant-numeric: tabular-nums;
		opacity: 0.7;
	}

	.chips button:hover {
		color: var(--text);
	}

	.chips button.on {
		color: var(--bg);
		background: var(--text);
		border-color: var(--text);
	}

	.found {
		font-size: 13px;
		color: var(--text-dim);
	}

	@media (max-width: 640px) {
		.search {
			max-width: none;
			flex-basis: 100%;
		}
	}
</style>
