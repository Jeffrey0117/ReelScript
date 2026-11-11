// Server-side reads from the Python backend, for pages that should arrive
// with their content already in the HTML (search engines, share previews).
//
// server.js runs the backend on PORT + 1000. BACKEND_URL overrides that
// (scripts/preview.mjs points it at the running site).

import { env } from '$env/dynamic/private';

const FALLBACK_PORT = 4005;

function backendBase(): string {
	if (env.BACKEND_URL) return env.BACKEND_URL.replace(/\/$/, '');
	const port = parseInt(env.PORT || String(FALLBACK_PORT), 10);
	return `http://127.0.0.1:${(Number.isFinite(port) ? port : FALLBACK_PORT) + 1000}`;
}

// Returns null on any failure: the page then falls back to loading in the
// browser, exactly as it did before server rendering.
export async function backendJson<T>(path: string, timeoutMs = 4000): Promise<T | null> {
	try {
		const res = await fetch(`${backendBase()}${path}`, { signal: AbortSignal.timeout(timeoutMs) });
		if (!res.ok) return null;
		return (await res.json()) as T;
	} catch {
		return null;
	}
}
