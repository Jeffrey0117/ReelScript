/**
 * ReelScript Production Server
 * Serves SvelteKit frontend and proxies API/WS to Python FastAPI backend.
 */

import { spawn } from 'child_process';
import { createServer } from 'http';
import { createReadStream, statSync } from 'fs';
import { join, extname } from 'path';
import { handler } from './frontend/build/handler.js';
import httpProxy from 'http-proxy';

const PORT = parseInt(process.env.PORT || '4005', 10);
const BACKEND_PORT = PORT + 1000; // Internal backend port
const BACKEND_HOST = `http://127.0.0.1:${BACKEND_PORT}`;
const VIDEOS_DIR = join(import.meta.dirname, 'data', 'videos');

// Create reverse proxy for API calls
const proxy = httpProxy.createProxyServer({
	target: BACKEND_HOST,
	ws: true,
	changeOrigin: true,
});

proxy.on('error', (err, _req, res) => {
	console.error('[proxy] error:', err.message);
	if (res.writeHead) {
		res.writeHead(502, { 'Content-Type': 'application/json' });
		res.end(JSON.stringify({ error: 'Backend unavailable' }));
	}
});

// Start Python FastAPI backend
const backend = spawn('python', ['backend/main.py'], {
	env: { ...process.env, REELSCRIPT_PORT: String(BACKEND_PORT) },
	stdio: ['ignore', 'pipe', 'pipe'],
});

backend.stdout.on('data', (data) => {
	process.stdout.write(`[backend] ${data}`);
});

backend.stderr.on('data', (data) => {
	process.stderr.write(`[backend] ${data}`);
});

backend.on('exit', (code) => {
	console.error(`[backend] exited with code ${code}`);
	process.exit(1);
});

// Serve video files directly with Range support (mobile needs this)
function serveVideo(req, res) {
	const filename = decodeURIComponent(req.url.replace('/videos/', ''));
	if (filename.includes('..') || filename.includes('/')) {
		res.writeHead(400);
		res.end('Bad request');
		return;
	}

	const filePath = join(VIDEOS_DIR, filename);
	let stat;
	try {
		stat = statSync(filePath);
	} catch {
		res.writeHead(404);
		res.end('Not found');
		return;
	}

	const mimeTypes = { '.mp4': 'video/mp4', '.webm': 'video/webm', '.mp3': 'audio/mpeg' };
	const contentType = mimeTypes[extname(filename)] || 'application/octet-stream';
	const range = req.headers.range;

	// Use file mtime as ETag for cache busting after re-encodes
	const etag = `"${stat.mtimeMs.toString(36)}-${stat.size.toString(36)}"`;
	const cacheHeaders = {
		'Content-Type': contentType,
		'Accept-Ranges': 'bytes',
		'ETag': etag,
		'Cache-Control': 'public, max-age=3600',
	};

	if (range) {
		const parts = range.replace(/bytes=/, '').split('-');
		const start = parseInt(parts[0], 10);
		const end = parts[1] ? parseInt(parts[1], 10) : stat.size - 1;
		res.writeHead(206, {
			...cacheHeaders,
			'Content-Range': `bytes ${start}-${end}/${stat.size}`,
			'Content-Length': end - start + 1,
		});
		createReadStream(filePath, { start, end }).pipe(res);
	} else {
		res.writeHead(200, {
			...cacheHeaders,
			'Content-Length': stat.size,
		});
		createReadStream(filePath).pipe(res);
	}
}

// HTTP server: videos direct, API to backend, rest to SvelteKit
const server = createServer((req, res) => {
	if (req.url?.startsWith('/videos/')) {
		serveVideo(req, res);
	} else if (req.url?.startsWith('/api/')) {
		proxy.web(req, res);
	} else {
		handler(req, res);
	}
});

// WebSocket upgrade
server.on('upgrade', (req, socket, head) => {
	if (req.url === '/ws') {
		proxy.ws(req, socket, head);
	} else {
		socket.destroy();
	}
});

// Wait for backend to be ready, then start
async function waitForBackend(maxRetries = 30) {
	for (let i = 0; i < maxRetries; i++) {
		try {
			const res = await fetch(`${BACKEND_HOST}/api/health`);
			if (res.ok) return true;
		} catch {
			// not ready yet
		}
		await new Promise((r) => setTimeout(r, 1000));
	}
	return false;
}

console.log(`[server] Starting backend on port ${BACKEND_PORT}...`);

waitForBackend().then((ready) => {
	if (!ready) {
		console.error('[server] Backend failed to start');
		process.exit(1);
	}

	server.listen(PORT, () => {
		console.log(`[server] ReelScript running at http://localhost:${PORT}`);
	});
});

// Graceful shutdown
function shutdown() {
	console.log('[server] Shutting down...');
	backend.kill('SIGTERM');
	server.close();
	process.exit(0);
}

process.on('SIGINT', shutdown);
process.on('SIGTERM', shutdown);
