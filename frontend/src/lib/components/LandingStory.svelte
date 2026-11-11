<script lang="ts">
	// The descriptive middle of the landing page: who this is for, what the six
	// modes are, and the questions people ask. Plain text on purpose — this is
	// the part search engines read.
	import { landingText } from '$lib/landing-text';

	const text = landingText();
</script>

<section class="story pain">
	<p class="kicker">{text.painKicker}</p>
	<h2>{text.painTitle}</h2>
	<p class="lead">{text.painLead}</p>
	<ul class="pains">
		{#each text.pains as pain, i (i)}
			<li><span class="tick" aria-hidden="true"></span>{pain}</li>
		{/each}
	</ul>
</section>

<section class="story ways">
	<p class="kicker">{text.waysKicker}</p>
	<h2>{text.waysTitle}</h2>
	<p class="lead">{text.waysLead}</p>
	<ol class="way-grid">
		{#each text.ways as way, i (way.name)}
			<li class="way">
				<span class="way-no">{String(i + 1).padStart(2, '0')}</span>
				<h3>{way.name}</h3>
				<p>{way.desc}</p>
			</li>
		{/each}
	</ol>
</section>

<section class="story faq">
	<h2>{text.faqTitle}</h2>
	<div class="faq-list">
		{#each text.faqs as item, i (i)}
			<details open={i === 0}>
				<summary>{item.q}</summary>
				<p>{item.a}</p>
			</details>
		{/each}
	</div>
</section>

<style>
	.story {
		max-width: 960px;
		margin: 0 auto;
		padding: 72px 0 8px;
	}

	.kicker {
		font-size: 12.5px;
		font-weight: 700;
		letter-spacing: 0.14em;
		color: var(--accent);
		margin-bottom: 12px;
	}

	h2 {
		font-size: clamp(26px, 4vw, 38px);
		font-weight: 800;
		line-height: 1.2;
		letter-spacing: -0.02em;
		text-wrap: balance;
	}

	.lead {
		margin-top: 12px;
		font-size: 16.5px;
		line-height: 1.7;
		color: var(--text-dim);
	}

	/* Pain points: a checklist people tick in their head */
	.pains {
		list-style: none;
		display: grid;
		gap: 10px;
		margin-top: 28px;
	}

	.pains li {
		display: flex;
		align-items: flex-start;
		gap: 14px;
		padding: 16px 20px;
		font-size: 17px;
		line-height: 1.55;
		background: var(--bg-card);
		border: 1px solid var(--border);
		border-left: 4px solid var(--accent);
		border-radius: var(--radius-sm);
	}

	.tick {
		flex-shrink: 0;
		width: 20px;
		height: 20px;
		margin-top: 3px;
		border: 2px solid var(--accent);
		border-radius: 5px;
		background: color-mix(in srgb, var(--accent) 10%, transparent);
	}

	/* Six ways */
	.way-grid {
		list-style: none;
		display: grid;
		grid-template-columns: repeat(3, 1fr);
		gap: 14px;
		margin-top: 30px;
	}

	.way {
		position: relative;
		padding: 22px 20px 20px;
		background: var(--bg-card);
		border: 1px solid var(--border);
		border-radius: var(--radius);
		box-shadow: var(--shadow-card);
	}

	.way-no {
		font-size: 12px;
		font-weight: 700;
		letter-spacing: 0.1em;
		color: var(--accent);
	}

	.way h3 {
		margin: 6px 0 8px;
		font-size: 19px;
		font-weight: 700;
	}

	.way p {
		font-size: 14.5px;
		line-height: 1.7;
		color: var(--text-dim);
	}

	/* FAQ */
	.faq {
		max-width: 760px;
	}

	.faq-list {
		margin-top: 22px;
		border-top: 1px solid var(--border);
	}

	details {
		border-bottom: 1px solid var(--border);
	}

	summary {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 16px;
		padding: 18px 2px;
		font-size: 17px;
		font-weight: 600;
		cursor: pointer;
		list-style: none;
	}

	summary::-webkit-details-marker {
		display: none;
	}

	summary::after {
		content: '+';
		flex-shrink: 0;
		font-size: 22px;
		font-weight: 400;
		color: var(--accent);
		transition: transform 0.2s;
	}

	details[open] summary::after {
		transform: rotate(45deg);
	}

	details p {
		padding: 0 2px 20px;
		font-size: 15.5px;
		line-height: 1.8;
		color: var(--text-dim);
	}

	@media (max-width: 760px) {
		.story {
			padding-top: 52px;
		}

		.way-grid {
			grid-template-columns: 1fr;
		}

		.pains li {
			padding: 14px 16px;
			font-size: 15.5px;
		}

		summary {
			font-size: 16px;
		}
	}
</style>
