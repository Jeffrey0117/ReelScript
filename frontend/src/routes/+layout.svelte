<script lang="ts">
	import '../app.css';

	let { children } = $props();
</script>

<div class="app">
	<nav class="navbar">
		<a href="/" class="logo">ReelScript</a>
		<div class="nav-links">
			<a href="/">Home</a>
			<a href="/collections">Collections</a>
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

	.main {
		flex: 1;
		max-width: 1200px;
		width: 100%;
		margin: 0 auto;
		padding: 32px;
	}
</style>
