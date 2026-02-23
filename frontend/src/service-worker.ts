/// <reference types="@sveltejs/kit" />
/// <reference no-default-lib="true"/>
/// <reference lib="esnext" />
/// <reference lib="webworker" />

import { build, files, version } from '$service-worker';

const sw = self as unknown as ServiceWorkerGlobalScope;
const CACHE_NAME = `reelscript-${version}`;

// Static assets to cache on install
const ASSETS = [...build, ...files];

sw.addEventListener('install', (event) => {
	event.waitUntil(
		caches.open(CACHE_NAME).then((cache) => cache.addAll(ASSETS))
	);
});

sw.addEventListener('activate', (event) => {
	// Delete old caches
	event.waitUntil(
		caches.keys().then((keys) =>
			Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k)))
		)
	);
});

sw.addEventListener('fetch', (event) => {
	if (event.request.method !== 'GET') return;

	const url = new URL(event.request.url);

	// Only handle same-origin requests — skip third-party (adman SDK, Cloudflare, etc.)
	if (url.origin !== sw.location.origin) return;

	// API calls: network-first (never cache)
	if (url.pathname.startsWith('/api/') || url.pathname.startsWith('/ws')) return;

	// Video/thumbnail files: network-first
	if (url.pathname.startsWith('/videos/') || url.pathname.startsWith('/thumbnails/')) return;

	// Static assets: cache-first
	event.respondWith(
		caches.match(event.request).then((cached) => {
			return cached || fetch(event.request);
		})
	);
});
