<script lang="ts">
	// Top bar of the typing practice: live speed, accuracy and progress.
	import { mt } from '$lib/modes/text';

	let {
		wpm,
		accuracy,
		cleared,
		total,
	}: { wpm: number; accuracy: number; cleared: number; total: number } = $props();
</script>

<header class="hud">
	<span class="prompt">~/reelscript/type</span>
	<div class="gauges">
		<span><b>{wpm}</b>{mt('typeWpm')}</span>
		<span><b>{accuracy}%</b>{mt('typeAccuracy')}</span>
		<span><b>{cleared}/{total}</b>{mt('typeProgress')}</span>
	</div>
</header>
<div class="meter"><i style="width: {total ? (cleared / total) * 100 : 0}%"></i></div>

<style>
	.hud {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 16px;
		padding: 12px 18px;
		border-bottom: 1px solid #2a2a3a;
		background: #12121c;
	}

	.prompt {
		font-size: 12.5px;
		color: #7c7c96;
	}

	.prompt::before {
		content: '$ ';
		color: #a5b4fc;
	}

	.gauges {
		display: flex;
		gap: 22px;
		font-size: 11px;
		letter-spacing: 0.08em;
		text-transform: uppercase;
		color: #7c7c96;
	}

	.gauges b {
		margin-right: 6px;
		font-size: 17px;
		letter-spacing: 0;
		color: #e4e4ef;
		font-variant-numeric: tabular-nums;
	}

	.meter {
		height: 2px;
		background: #2a2a3a;
	}

	.meter i {
		display: block;
		height: 100%;
		background: #a5b4fc;
		box-shadow: 0 0 10px #a5b4fc;
		transition: width 0.3s ease;
	}

	@media (max-width: 760px) {
		.hud {
			flex-direction: column;
			align-items: flex-start;
			gap: 8px;
			padding: 10px 14px;
		}

		.gauges {
			gap: 16px;
		}
	}
</style>
