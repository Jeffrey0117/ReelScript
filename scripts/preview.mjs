// Preview a frontend change without touching the live site.
//
//   npm run preview               builds frontend into frontend/build-preview, then serves it
//   npm run preview -- --no-build serves the preview build that is already there
//
// The live server keeps serving frontend/build. This serves the preview build on
// another port and forwards API / media requests to the running server, so the
// page uses real data while only the frontend is new.
import http from 'node:http';
import { execSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import httpProxy from 'http-proxy';

const PORT = parseInt(process.env.PREVIEW_PORT || '4905', 10);
const TARGET = process.env.PREVIEW_TARGET || 'http://127.0.0.1:4005';
const FORWARDED = ['/api/', '/videos/', '/audio/', '/thumbnails/', '/speaking/files/'];

if (!process.argv.includes('--no-build')) {
	// If the build fails this throws and nothing is served — better than serving a stale preview.
	execSync('npx vite build', {
		cwd: fileURLToPath(new URL('../frontend', import.meta.url)),
		env: { ...process.env, BUILD_OUT: 'build-preview' },
		stdio: 'inherit',
	});
}

// Pages rendered on the server fetch their data from the same running site.
process.env.BACKEND_URL ||= TARGET;

const { handler } = await import('../frontend/build-preview/handler.js');
const proxy = httpProxy.createProxyServer({ target: TARGET, ws: true });

proxy.on('error', (error, _req, res) => {
	console.error('[preview] upstream error:', error.message);
	if (res && 'writeHead' in res && !res.headersSent) {
		res.writeHead(502, { 'Content-Type': 'text/plain' });
		res.end('Preview upstream is not reachable');
	}
});

const server = http.createServer((req, res) => {
	if (FORWARDED.some((prefix) => req.url?.startsWith(prefix))) proxy.web(req, res);
	else handler(req, res);
});

server.on('upgrade', (req, socket, head) => proxy.ws(req, socket, head));

// Loopback only: this forwards to the live API, so it must not be reachable from the LAN.
server.listen(PORT, '127.0.0.1', () => {
	console.log(`[preview] http://localhost:${PORT}  (data from ${TARGET})`);
});
