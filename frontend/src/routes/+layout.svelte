<script lang="ts">
	import '../app.css';
	import { onMount } from 'svelte';
	import { t, getLocale, setLocale, initLocale, onLocaleChange } from '$lib/i18n';
	import { initAuth, onAuthChange, login, logout, isAdmin, type AdmanUser } from '$lib/auth';

	let { children } = $props();

	let theme = $state<'dark' | 'light'>('dark');
	let locale = $state<'zh' | 'en'>('zh');
	let tick = $state(0);
	let user = $state<AdmanUser | null>(null);
	let showUserMenu = $state(false);

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

		initAuth();
		onAuthChange((u) => {
			user = u;
		});

		// Close user menu on outside click
		const handleClick = () => { showUserMenu = false; };
		document.addEventListener('click', handleClick);
		return () => document.removeEventListener('click', handleClick);
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

	function handleLogin() {
		login();
	}

	async function handleLogout() {
		await logout();
		showUserMenu = false;
	}

	function toggleUserMenu(e: MouseEvent) {
		e.stopPropagation();
		showUserMenu = !showUserMenu;
	}
</script>

{#key tick}
<div class="app">
	<nav class="navbar">
		<a href="/" class="logo">ReelScript <span class="logo-sub">一刷一句</span></a>

		<div class="nav-right">
			<div class="nav-links">
				<a href="/">{t('home')}</a>
				<a href="/collections">{t('collections')}</a>
				{#if user?.role === 'admin'}
					<a href="/admin">{t('admin')}</a>
				{/if}
			</div>

			<div class="nav-actions">
				<button class="nav-btn" onclick={toggleLocale} title="Toggle language">
					{locale === 'zh' ? 'EN' : '中'}
				</button>
				<button class="nav-btn" onclick={toggleTheme} title="Toggle theme">
					{#if theme === 'dark'}
						<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
							<circle cx="12" cy="12" r="5"/>
							<line x1="12" y1="1" x2="12" y2="3"/>
							<line x1="12" y1="21" x2="12" y2="23"/>
							<line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/>
							<line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/>
							<line x1="1" y1="12" x2="3" y2="12"/>
							<line x1="21" y1="12" x2="23" y2="12"/>
							<line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/>
							<line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/>
						</svg>
					{:else}
						<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
							<path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>
						</svg>
					{/if}
				</button>

				{#if user}
					<!-- svelte-ignore a11y_no_static_element_interactions -->
					<div class="user-menu-wrapper" onclick={toggleUserMenu}>
						<button class="nav-btn user-btn" title={user.displayName || user.email}>
							<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
								<path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>
								<circle cx="12" cy="7" r="4"/>
							</svg>
						</button>
						{#if showUserMenu}
							<div class="user-dropdown">
								<div class="user-info">
									<span class="user-name">{user.displayName || user.email}</span>
									<span class="user-email">{user.email}</span>
								</div>
								<button class="dropdown-item" onclick={handleLogout}>{t('logout')}</button>
							</div>
						{/if}
					</div>
				{:else}
					<button class="nav-btn login-btn" onclick={handleLogin}>
						{t('login')}
					</button>
				{/if}
			</div>
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
		display: flex;
		align-items: baseline;
		gap: 6px;
	}

	.logo-sub {
		font-size: 12px;
		font-weight: 500;
		color: var(--text-dim);
		letter-spacing: 1px;
	}

	.nav-right {
		display: flex;
		align-items: center;
		gap: 20px;
	}

	.nav-links {
		display: flex;
		align-items: center;
		gap: 20px;
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

	.nav-actions {
		display: flex;
		align-items: center;
		gap: 4px;
		border-left: 1px solid var(--border);
		padding-left: 16px;
	}

	.nav-btn {
		width: 36px;
		height: 36px;
		display: flex;
		align-items: center;
		justify-content: center;
		border-radius: var(--radius-sm);
		font-size: 13px;
		font-weight: 600;
		color: var(--text-dim);
		transition: background 0.15s, color 0.15s;
	}

	.nav-btn:hover {
		background: var(--bg-hover);
		color: var(--text);
	}

	.login-btn {
		width: auto;
		padding: 0 12px;
		font-size: 13px;
		font-weight: 600;
		color: var(--accent);
		border: 1px solid var(--accent);
		border-radius: var(--radius-sm);
	}

	.login-btn:hover {
		background: var(--accent);
		color: #fff;
	}

	.user-menu-wrapper {
		position: relative;
	}

	.user-btn {
		color: var(--accent);
	}

	.user-dropdown {
		position: absolute;
		top: 100%;
		right: 0;
		margin-top: 4px;
		background: var(--bg-card);
		border: 1px solid var(--border);
		border-radius: var(--radius-sm);
		box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
		min-width: 180px;
		z-index: 200;
		overflow: hidden;
	}

	.user-info {
		padding: 12px 16px;
		border-bottom: 1px solid var(--border);
	}

	.user-name {
		display: block;
		font-size: 14px;
		font-weight: 600;
		color: var(--text);
	}

	.user-email {
		display: block;
		font-size: 12px;
		color: var(--text-dim);
		margin-top: 2px;
	}

	.dropdown-item {
		width: 100%;
		padding: 10px 16px;
		font-size: 13px;
		color: var(--text);
		background: none;
		border: none;
		text-align: left;
		cursor: pointer;
	}

	.dropdown-item:hover {
		background: var(--bg-hover);
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

		.nav-right {
			gap: 12px;
		}

		.nav-links {
			gap: 12px;
		}

		.nav-links a {
			font-size: 13px;
		}

		.nav-actions {
			gap: 2px;
			padding-left: 10px;
		}

		.nav-btn {
			width: 32px;
			height: 32px;
		}

		.main {
			padding: 16px;
		}
	}
</style>
