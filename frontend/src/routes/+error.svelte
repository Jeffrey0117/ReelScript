<script lang="ts">
	import { page } from '$app/stores';
	import { t } from '$lib/i18n';

	let status = $derived($page.status);
	let message = $derived($page.error?.message || '');
</script>

<svelte:head>
	<title>Error {status} — ReelScript</title>
</svelte:head>

<div class="error-page">
	<h1 class="error-code">{status}</h1>
	<p class="error-message">{message || 'Something went wrong'}</p>
	<div class="error-actions">
		<a href="/" class="btn btn-primary">{t('home')}</a>
	</div>
</div>

<style>
	.error-page {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		min-height: 50vh;
		text-align: center;
		padding: 32px;
	}

	.error-code {
		font-size: 72px;
		font-weight: 800;
		color: var(--accent);
		line-height: 1;
		margin-bottom: 12px;
	}

	.error-message {
		font-size: 18px;
		color: var(--text-dim);
		margin-bottom: 32px;
		max-width: 400px;
	}
</style>
