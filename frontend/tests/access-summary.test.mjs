import { test } from 'node:test';
import assert from 'node:assert/strict';
import { gateSummary, TIER_LIMITS, FULL } from '../src/lib/modes/access.ts';

const summary = {
	theme: '如何讓小房間看起來更寬敞',
	keyPoints: ['選擇大地毯', '避免笨重傢俱'],
	goldenQuotes: [
		{ en: 'Your decisions are the problem, not your room.', zh: '你的決策才是問題所在。' },
		{ en: 'Less is generally more.', zh: '少即是多。' },
	],
};
const visible = 'Your room is not the problem. Your decisions are the problem, not your room! First is small rugs.';

test('full access gets the summary untouched', () => {
	assert.equal(gateSummary(summary, visible, FULL), summary);
});

test('no summary stays no summary', () => {
	assert.equal(gateSummary(null, visible, TIER_LIMITS.guest), null);
	assert.equal(gateSummary(undefined, visible, TIER_LIMITS.free), null);
});

test('a visitor gets no Chinese and only quotes from lines they can see', () => {
	const out = gateSummary(summary, visible, TIER_LIMITS.guest);
	assert.equal(out.theme, '');
	assert.deepEqual(out.keyPoints, []);
	assert.deepEqual(out.goldenQuotes, [{ en: 'Your decisions are the problem, not your room.', zh: '' }]);
});

test('a free member keeps the Chinese but still loses quotes from held-back lines', () => {
	const out = gateSummary(summary, visible, TIER_LIMITS.free);
	assert.equal(out.theme, summary.theme);
	assert.deepEqual(out.keyPoints, summary.keyPoints);
	assert.equal(out.goldenQuotes.length, 1);
	assert.equal(out.goldenQuotes[0].zh, '你的決策才是問題所在。');
});

test('gateSummary does not change the summary it was given', () => {
	const before = JSON.stringify(summary);
	gateSummary(summary, visible, TIER_LIMITS.guest);
	assert.equal(JSON.stringify(summary), before);
});

test('an empty quote never matches', () => {
	const out = gateSummary({ ...summary, goldenQuotes: [{ en: '...', zh: 'x' }] }, visible, TIER_LIMITS.free);
	assert.deepEqual(out.goldenQuotes, []);
});
