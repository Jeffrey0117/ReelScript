<script lang="ts">
	// The one piece of chrome every mode shares — but it dresses to match the
	// mode it is in (data-skin), so switching feels like walking into another site.
	import { mt, MODE_IDS, type ModeId, type ModeTextKey } from '$lib/modes/text';

	let { mode, onSwitch }: { mode: ModeId; onSwitch: (next: ModeId) => void } = $props();

	const LABELS: Record<ModeId, ModeTextKey> = {
		video: 'modeVideo',
		read: 'modeRead',
		podcast: 'modePodcast',
		type: 'modeType',
		vocab: 'modeVocab',
		handout: 'modeHandout',
	};

	// 24×24 stroke icons, one path string each.
	const ICONS: Record<ModeId, string> = {
		video: 'M4 5h16a1 1 0 0 1 1 1v12a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V6a1 1 0 0 1 1-1zM10 9l5 3-5 3z',
		read: 'M4 5h10a3 3 0 0 1 3 3v11H7a3 3 0 0 1-3-3zM17 8h3v8a3 3 0 0 1-3 3M8 9h5M8 13h5',
		podcast: 'M12 3a3 3 0 0 1 3 3v5a3 3 0 0 1-6 0V6a3 3 0 0 1 3-3zM6 11a6 6 0 0 0 12 0M12 17v4M9 21h6',
		type: 'M3 6h18a1 1 0 0 1 1 1v10a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1zM6 10h1M10 10h1M14 10h1M18 10h0M7 14h10',
		vocab: 'M12 6c-2-1.5-5-2-8-1.5v13c3-.5 6 0 8 1.5 2-1.5 5-2 8-1.5v-13c-3-.5-6 0-8 1.5zM12 6v13',
		handout: 'M7 3h8l4 4v14H7zM15 3v4h4M10 12h6M10 16h6',
	};
</script>

<nav class="switcher" data-skin={mode} aria-label={mt('switcherLabel')}>
	{#each MODE_IDS as id (id)}
		<button
			class="tab"
			class:on={id === mode}
			aria-current={id === mode ? 'page' : undefined}
			onclick={() => onSwitch(id)}
		>
			<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
				<path d={ICONS[id]} />
			</svg>
			<span>{mt(LABELS[id])}</span>
		</button>
	{/each}
</nav>

<style>
	.switcher {
		display: flex;
		gap: 6px;
		overflow-x: auto;
		scrollbar-width: none;
		-webkit-overflow-scrolling: touch;
		transition: background 0.25s ease, border-color 0.25s ease, padding 0.25s ease, border-radius 0.25s ease;
	}

	.switcher::-webkit-scrollbar {
		display: none;
	}

	.tab {
		display: inline-flex;
		align-items: center;
		gap: 7px;
		flex-shrink: 0;
		padding: 8px 14px;
		font-size: 14px;
		font-weight: 600;
		color: var(--text-dim);
		white-space: nowrap;
		transition: color 0.15s, background 0.15s, border-color 0.15s, box-shadow 0.15s;
	}

	.tab:focus-visible {
		outline: 2px solid var(--accent);
		outline-offset: 2px;
	}

	/* ── video: the app's own pills ── */
	[data-skin='video'] .tab {
		border-radius: 999px;
		background: var(--bg-card);
		border: 1px solid var(--border);
	}
	[data-skin='video'] .tab:hover {
		color: var(--text);
		border-color: var(--accent);
	}
	[data-skin='video'] .tab.on {
		background: var(--accent);
		border-color: var(--accent);
		color: #fff;
	}

	/* ── read: a newspaper section bar ── */
	[data-skin='read'] {
		max-width: 760px;
		width: 100%;
		margin: 0 auto;
		gap: 0;
		justify-content: space-between;
		border-top: 3px double var(--text);
		border-bottom: 1px solid var(--text);
	}
	[data-skin='read'] .tab {
		font-family: var(--font-serif);
		font-size: 13px;
		letter-spacing: 0.08em;
		text-transform: uppercase;
		padding: 10px 10px 9px;
		border-bottom: 2px solid transparent;
		margin-bottom: -1px;
	}
	[data-skin='read'] .tab svg {
		display: none;
	}
	[data-skin='read'] .tab:hover {
		color: var(--text);
	}
	[data-skin='read'] .tab.on {
		color: var(--text);
		border-bottom-color: var(--accent);
	}

	/* ── podcast: a dark capsule ── */
	[data-skin='podcast'] {
		align-self: center;
		max-width: 100%;
		gap: 2px;
		padding: 5px;
		border-radius: 999px;
		background: #14132b;
		box-shadow: 0 8px 30px rgba(49, 46, 129, 0.35);
	}
	[data-skin='podcast'] .tab {
		border-radius: 999px;
		color: #a5a3d6;
		padding: 8px 15px;
	}
	[data-skin='podcast'] .tab:hover {
		color: #fff;
	}
	[data-skin='podcast'] .tab.on {
		background: linear-gradient(135deg, #818cf8, #6366f1);
		color: #fff;
		box-shadow: 0 0 18px rgba(129, 140, 248, 0.55);
	}

	/* ── type: a terminal tab line ── */
	[data-skin='type'] {
		gap: 0;
		padding: 0 6px;
		background: #0e0e16;
		border: 1px solid #2a2a3a;
		border-radius: 10px;
	}
	[data-skin='type'] .tab {
		font-family: var(--font-mono);
		font-size: 13px;
		font-weight: 500;
		color: #7c7c96;
		padding: 11px 12px;
		border-radius: 0;
	}
	[data-skin='type'] .tab svg {
		display: none;
	}
	[data-skin='type'] .tab::before {
		content: '[ ';
		opacity: 0.45;
	}
	[data-skin='type'] .tab::after {
		content: ' ]';
		opacity: 0.45;
	}
	[data-skin='type'] .tab:hover {
		color: #e4e4ef;
	}
	[data-skin='type'] .tab.on {
		color: #a5b4fc;
		box-shadow: inset 0 -2px 0 #818cf8;
	}

	/* ── vocab: index tabs sticking out of a notebook ── */
	[data-skin='vocab'] {
		gap: 4px;
		align-items: flex-end;
		padding: 0 18px;
		margin-bottom: -24px;
		position: relative;
		z-index: 1;
	}
	[data-skin='vocab'] .tab {
		font-family: var(--font-hand);
		font-size: 18px;
		font-weight: 700;
		padding: 6px 14px 8px;
		border-radius: 10px 10px 0 0;
		background: color-mix(in srgb, var(--accent) 12%, var(--bg-card));
		border: 1px solid var(--border);
		border-bottom: none;
		color: var(--text-dim);
	}
	[data-skin='vocab'] .tab:nth-child(3n + 1) {
		background: color-mix(in srgb, #f59e0b 16%, var(--bg-card));
	}
	[data-skin='vocab'] .tab:nth-child(3n + 2) {
		background: color-mix(in srgb, #10b981 14%, var(--bg-card));
	}
	[data-skin='vocab'] .tab:hover {
		color: var(--text);
		padding-bottom: 12px;
	}
	[data-skin='vocab'] .tab.on {
		background: var(--bg-card);
		color: var(--accent);
		padding-bottom: 14px;
	}

	/* ── handout: checkbox-style stamps ── */
	[data-skin='handout'] {
		max-width: 820px;
		width: 100%;
		margin: 0 auto;
		gap: 8px;
	}
	[data-skin='handout'] .tab {
		border: 1.5px dashed var(--border);
		border-radius: 4px;
		font-size: 13px;
		padding: 7px 12px;
		background: transparent;
	}
	[data-skin='handout'] .tab:hover {
		color: var(--text);
		border-color: var(--text-dim);
	}
	[data-skin='handout'] .tab.on {
		border-style: solid;
		border-color: var(--text);
		color: var(--text);
		background: var(--bg-card);
		box-shadow: 3px 3px 0 var(--text);
	}

	@media (max-width: 640px) {
		.tab {
			padding: 7px 11px;
			font-size: 13px;
		}
		[data-skin='read'] {
			justify-content: flex-start;
		}
		[data-skin='podcast'] {
			align-self: stretch;
			border-radius: 16px;
		}
		[data-skin='vocab'] {
			padding: 0 8px;
			margin-bottom: -16px;
		}
		[data-skin='vocab'] .tab {
			font-size: 16px;
			padding: 5px 10px 7px;
		}
	}

	@media print {
		.switcher {
			display: none;
		}
	}
</style>
