// Sitemap: the fixed pages plus one entry per public article.
import { allPublicVideos } from '$lib/server/public-videos';
import { absoluteUrl, sitemapXml, type SitemapEntry } from '$lib/seo';
import type { RequestHandler } from './$types';

const FIXED: SitemapEntry[] = [{ path: '/' }, { path: '/blog' }, { path: '/packs' }, { path: '/pricing' }];

export const GET: RequestHandler = async ({ url }) => {
	const videos = (await allPublicVideos()) ?? [];
	const articles = videos
		.filter((v) => v.hasTranscript)
		.map((v) => ({ path: `/blog/${v.id}`, lastmod: v.createdAt }));
	const origin = absoluteUrl(url, '/').replace(/\/$/, '');
	return new Response(sitemapXml(origin, [...FIXED, ...articles]), {
		headers: { 'Content-Type': 'application/xml; charset=utf-8', 'Cache-Control': 'public, max-age=3600' },
	});
};
