import { test } from 'node:test';
import assert from 'node:assert/strict';
import { filterVideos, countBySource, ageOf, groupByAge } from '../src/lib/video-shelf.ts';

const NOW = Date.parse('2026-11-11T12:00:00Z');
const hoursAgo = (h) => new Date(NOW - h * 3600 * 1000).toISOString();
const v = (id, title, source, created_at, channel = null) => ({ id, title, source, created_at, channel });

const pile = [
	v('a', 'Small room mistakes', 'ig', hoursAgo(2), 'hansdesign'),
	v('b', '如何提升睡眠品質', 'ig', hoursAgo(50)),
	v('c', 'Why elephants have trunks', 'youtube', hoursAgo(24 * 20)),
	v('d', null, 'youtube', hoursAgo(24 * 90)),
	v('e', 'No date', 'ig', null),
];

test('filterVideos matches title or channel, ignoring case and outer spaces', () => {
	assert.deepEqual(filterVideos(pile, { query: '  ROOM ' }).map((x) => x.id), ['a']);
	assert.deepEqual(filterVideos(pile, { query: 'hans' }).map((x) => x.id), ['a']);
	assert.deepEqual(filterVideos(pile, { query: '睡眠' }).map((x) => x.id), ['b']);
	assert.deepEqual(filterVideos(pile, { query: 'zzz' }), []);
});

test('filterVideos filters by source and combines with the query', () => {
	assert.deepEqual(filterVideos(pile, { source: 'youtube' }).map((x) => x.id), ['c', 'd']);
	assert.deepEqual(filterVideos(pile, { source: 'ig', query: 'date' }).map((x) => x.id), ['e']);
	assert.equal(filterVideos(pile).length, pile.length);
});

test('filterVideos returns a new array and survives a missing title', () => {
	const out = filterVideos(pile);
	assert.notEqual(out, pile);
	assert.deepEqual(filterVideos(pile, { query: 'null' }), []);
});

test('countBySource counts each source', () => {
	assert.deepEqual(countBySource(pile), { all: 5, ig: 3, youtube: 2 });
	assert.deepEqual(countBySource([]), { all: 0, ig: 0, youtube: 0 });
});

test('ageOf buckets by age and never loses an undated video', () => {
	assert.equal(ageOf(hoursAgo(1), NOW), 'today');
	assert.equal(ageOf(hoursAgo(25), NOW), 'week');
	assert.equal(ageOf(hoursAgo(24 * 8), NOW), 'month');
	assert.equal(ageOf(hoursAgo(24 * 31), NOW), 'older');
	assert.equal(ageOf(null, NOW), 'older');
	assert.equal(ageOf('garbage', NOW), 'older');
});

test('groupByAge keeps order, drops empty groups and loses nothing', () => {
	const groups = groupByAge(pile, NOW);
	assert.deepEqual(groups.map((g) => g.key), ['today', 'week', 'month', 'older']);
	assert.deepEqual(groups[3].videos.map((x) => x.id), ['d', 'e']);
	assert.equal(groups.reduce((n, g) => n + g.videos.length, 0), pile.length);
	assert.deepEqual(groupByAge([pile[0]], NOW).map((g) => g.key), ['today']);
	assert.deepEqual(groupByAge([], NOW), []);
});
