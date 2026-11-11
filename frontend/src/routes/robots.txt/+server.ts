// robots.txt is generated so it can point at the sitemap with the address the
// site is actually served from (nothing about the host is written in the code).
import { absoluteUrl } from '$lib/seo';
import type { RequestHandler } from './$types';

export const GET: RequestHandler = ({ url }) => {
	const body = [
		'User-agent: *',
		// /api/ stays crawlable: pages that load their content in the browser
		// (materials, the landing demo) only render for a crawler if it may fetch it.
		'Disallow: /admin',
		'',
		`Sitemap: ${absoluteUrl(url, '/sitemap.xml')}`,
		'',
	].join('\n');
	return new Response(body, {
		headers: { 'Content-Type': 'text/plain; charset=utf-8', 'Cache-Control': 'public, max-age=3600' },
	});
};
