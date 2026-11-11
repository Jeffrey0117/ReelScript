// Small pure helpers for search-engine and share-preview tags.

const LOCAL_HOST = /^(localhost|127\.0\.0\.1|\[::1\])$/;

// The public address of a path. Behind the tunnel the server sees plain http,
// so anything that is not a local address is published as https.
export function absoluteUrl(current: URL, path = current.pathname): string {
	const protocol = LOCAL_HOST.test(current.hostname) ? current.protocol : 'https:';
	const clean = path.startsWith('/') ? path : `/${path}`;
	return `${protocol}//${current.host}${clean}`;
}

// One line for a description tag: collapsed whitespace, cut on a word or
// punctuation boundary, never longer than `max`.
export function summarize(text: string | null | undefined, max = 155): string {
	const flat = String(text ?? '').replace(/\s+/g, ' ').trim();
	if (flat.length <= max) return flat;
	const cut = flat.slice(0, max - 1);
	const boundary = Math.max(cut.lastIndexOf(' '), cut.lastIndexOf('，'), cut.lastIndexOf('。'), cut.lastIndexOf(', '));
	return `${(boundary > max * 0.6 ? cut.slice(0, boundary) : cut).trim()}…`;
}

// JSON-LD goes into a <script> tag as raw HTML, so anything that could close
// the tag or start a comment is escaped.
const LINE_SEPARATORS = new RegExp('[' + String.fromCharCode(0x2028, 0x2029) + ']', 'g');

export function jsonLd(data: unknown): string {
	const body = JSON.stringify(data)
		.replace(/</g, '\\u003c')
		.replace(/>/g, '\\u003e')
		.replace(/&/g, '\\u0026')
		// U+2028 / U+2029 end a line in JavaScript but are legal inside JSON strings.
		.replace(LINE_SEPARATORS, (ch) => '\\u' + ch.charCodeAt(0).toString(16));
	return `<script type="application/ld+json">${body}</` + `script>`;
}

export function xmlEscape(value: string): string {
	return value
		.replace(/&/g, '&amp;')
		.replace(/</g, '&lt;')
		.replace(/>/g, '&gt;')
		.replace(/"/g, '&quot;')
		.replace(/'/g, '&apos;');
}

export interface SitemapEntry {
	path: string;
	lastmod?: string | null;
}

export function sitemapXml(origin: string, entries: readonly SitemapEntry[]): string {
	const rows = entries.map(({ path, lastmod }) => {
		const day = lastmod && !Number.isNaN(Date.parse(lastmod)) ? new Date(lastmod).toISOString().slice(0, 10) : '';
		return `  <url><loc>${xmlEscape(origin + path)}</loc>${day ? `<lastmod>${day}</lastmod>` : ''}</url>`;
	});
	return `<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n${rows.join('\n')}\n</urlset>\n`;
}
