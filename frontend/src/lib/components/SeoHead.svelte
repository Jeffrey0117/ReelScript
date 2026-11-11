<script lang="ts">
	// Title, description, canonical address and share-preview tags for one page.
	import { page } from '$app/state';
	import { absoluteUrl, jsonLd } from '$lib/seo';

	let {
		title,
		description = '',
		image = '/icon-512.png',
		type = 'website',
		schema = undefined,
	}: {
		title: string;
		description?: string;
		image?: string;
		type?: 'website' | 'article';
		schema?: Record<string, unknown>;
	} = $props();

	let canonical = $derived(absoluteUrl(page.url));
	let imageUrl = $derived(/^https?:\/\//.test(image) ? image : absoluteUrl(page.url, image));
</script>

<svelte:head>
	<title>{title}</title>
	<link rel="canonical" href={canonical} />
	{#if description}
		<meta name="description" content={description} />
		<meta property="og:description" content={description} />
		<meta name="twitter:description" content={description} />
	{/if}
	<meta property="og:type" content={type} />
	<meta property="og:site_name" content="ReelScript" />
	<meta property="og:title" content={title} />
	<meta property="og:url" content={canonical} />
	<meta property="og:image" content={imageUrl} />
	<meta name="twitter:card" content="summary_large_image" />
	<meta name="twitter:title" content={title} />
	<meta name="twitter:image" content={imageUrl} />
	{#if schema}
		<!-- eslint-disable-next-line svelte/no-at-html-tags -- jsonLd() escapes everything that could leave the tag -->
		{@html jsonLd(schema)}
	{/if}
</svelte:head>
