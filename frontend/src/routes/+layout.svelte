<script lang="ts">
	import '../app.css';
	import { onMount } from 'svelte';
	import { t, getLocale, setLocale, initLocale, onLocaleChange } from '$lib/i18n';

	let { children } = $props();

	let theme = $state<'dark' | 'light'>('dark');
	let locale = $state<'zh' | 'en'>('zh');
	let tick = $state(0);

	onMount(() => {
		const savedTheme = localStorage.getItem('reelscript-theme');
		if (savedTheme === 'light' || savedTheme === 'dark') {
			theme = savedTheme;
		}
		document.documentElement.setAttribute('data-theme', theme);

		initLocale();
		locale = getLocale();
		onLocaleChange(() => {
			locale = getLocale();
			tick++;
		});
	});

	function toggleTheme() {
		theme = theme === 'dark' ? 'light' : 'dark';
		document.documentElement.setAttribute('data-theme', theme);
		localStorage.setItem('reelscript-theme', theme);
	}

	function toggleLocale() {
		const next = locale === 'zh' ? 'en' : 'zh';
		setLocale(next);
	}
</script>

{#key tick}
<div class="app">
	<nav class="navbar">
		<a href="/" class="logo">ReelScript</a>
		<div class="nav-links">
			<a href="/">{t('home')}</a>
			<a href="/collections">{t('collections')}</a>
			<button class="locale-toggle" onclick={toggleLocale} title="Toggle language">
				{locale === 'zh' ? 'EN' : '中'}
			</button>
			<button class="theme-toggle" onclick={toggleTheme} title="Toggle theme">
				{theme === 'dark' ? '☀' : '●'}
			</button>
		</div>
	</nav>

	<main class="main">
		{@render children()}
	</main>
</div>
{/key}

<style>
	.app {
		min-height: 100vh;
		display: flex;
		flex-direction: column;
	}

	.navbar {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 0 32px;
		height: 56px;
		border-bottom: 1px solid var(--border);
		background: var(--bg-card);
		position: sticky;
		top: 0;
		z-index: 100;
	}

	.logo {
		font-size: 18px;
		font-weight: 700;
		color: var(--text) !important;
		letter-spacing: -0.5px;
	}

	.nav-links {
		display: flex;
		gap: 24px;
	}

	.nav-links a {
		color: var(--text-dim);
		font-size: 14px;
		font-weight: 500;
		transition: color 0.15s;
	}

	.nav-links a:hover {
		color: var(--text);
	}

	.locale-toggle {
		padding: 4px 10px;
		border-radius: var(--radius-sm);
		font-size: 13px;
		font-weight: 600;
		color: var(--text-dim);
		transition: background 0.15s, color 0.15s;
	}

	.locale-toggle:hover {
		background: var(--bg-hover);
		color: var(--text);
	}

	.theme-toggle {
		font-size: 18px;
		width: 36px;
		height: 36px;
		display: flex;
		align-items: center;
		justify-content: center;
		border-radius: var(--radius-sm);
		transition: background 0.15s;
		color: var(--text-dim);
	}

	.theme-toggle:hover {
		background: var(--bg-hover);
		color: var(--text);
	}

	.main {
		flex: 1;
		max-width: 1200px;
		width: 100%;
		margin: 0 auto;
		padding: 32px;
	}

	@media (max-width: 640px) {
		.navbar {
			padding: 0 16px;
			height: 48px;
		}

		.logo {
			font-size: 16px;
		}

		.nav-links {
			gap: 12px;
		}

		.nav-links a {
			font-size: 13px;
		}

		.main {
			padding: 16px;
		}
	}
</style>
