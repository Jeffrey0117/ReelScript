<script lang="ts">
	import '../app.css';
	import { onMount } from 'svelte';

	let { children } = $props();

	let theme = $state<'dark' | 'light'>('dark');

	onMount(() => {
		const saved = localStorage.getItem('reelscript-theme');
		if (saved === 'light' || saved === 'dark') {
			theme = saved;
		}
		document.documentElement.setAttribute('data-theme', theme);
	});

	function toggleTheme() {
		theme = theme === 'dark' ? 'light' : 'dark';
		document.documentElement.setAttribute('data-theme', theme);
		localStorage.setItem('reelscript-theme', theme);
	}
</script>

<div class="app">
	<nav class="navbar">
		<a href="/" class="logo">ReelScript</a>
		<div class="nav-links">
			<a href="/">Home</a>
			<a href="/collections">Collections</a>
			<button class="theme-toggle" onclick={toggleTheme} title="Toggle theme">
				{theme === 'dark' ? '☀' : '●'}
			</button>
		</div>
	</nav>

	<main class="main">
		{@render children()}
	</main>
</div>

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
</style>
