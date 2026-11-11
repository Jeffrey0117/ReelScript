import { test } from 'node:test';
import assert from 'node:assert/strict';
import { absoluteUrl, summarize, jsonLd, xmlEscape, sitemapXml } from '../src/lib/seo.ts';

test('absoluteUrl publishes https for public hosts and keeps local ones as they are', () => {
	assert.equal(absoluteUrl(new URL('http://example.com/blog/1?x=1')), 'https://example.com/blog/1');
	assert.equal(absoluteUrl(new URL('http://example.com/a'), '/b'), 'https://example.com/b');
	assert.equal(absoluteUrl(new URL('http://example.com/a'), 'b'), 'https://example.com/b');
	assert.equal(absoluteUrl(new URL('http://localhost:4905/a')), 'http://localhost:4905/a');
	assert.equal(absoluteUrl(new URL('http://127.0.0.1:4005/a')), 'http://127.0.0.1:4005/a');
});

test('summarize collapses whitespace and keeps short text whole', () => {
	assert.equal(summarize('  a\n\n b   c '), 'a b c');
	assert.equal(summarize(null), '');
});

test('summarize cuts long text on a boundary and never exceeds the limit', () => {
	const long = 'word '.repeat(80);
	const out = summarize(long, 60);
	assert.ok(out.length <= 60);
	assert.ok(out.endsWith('…'));
	assert.ok(!out.includes('wor…'));
	const chinese = '這是一段很長的中文，'.repeat(20);
	assert.ok(summarize(chinese, 50).length <= 50);
});

test('jsonLd cannot break out of its script tag', () => {
	const out = jsonLd({ name: '</script><script>alert(1)</script>', note: 'a & b' });
	assert.equal(out.match(/<\/script>/g).length, 1);
	assert.ok(out.endsWith('</script>'));
	assert.ok(!out.includes('<script>alert'));
	const body = out.replace(/^<script[^>]*>/, '').replace(/<\/script>$/, '');
	assert.deepEqual(JSON.parse(body), { name: '</script><script>alert(1)</script>', note: 'a & b' });
});

test('xmlEscape escapes the five special characters', () => {
	assert.equal(xmlEscape(`a&b<c>d"e'f`), 'a&amp;b&lt;c&gt;d&quot;e&apos;f');
});

test('sitemapXml lists every entry, formats dates and drops bad ones', () => {
	const xml = sitemapXml('https://example.com', [
		{ path: '/' },
		{ path: '/blog/a&b', lastmod: '2026-11-01T10:19:12.819172' },
		{ path: '/blog/c', lastmod: 'not a date' },
	]);
	assert.ok(xml.startsWith('<?xml'));
	assert.equal(xml.match(/<url>/g).length, 3);
	assert.ok(xml.includes('<loc>https://example.com/blog/a&amp;b</loc><lastmod>2026-11-01</lastmod>'));
	assert.ok(xml.includes('<loc>https://example.com/blog/c</loc></url>'));
});
