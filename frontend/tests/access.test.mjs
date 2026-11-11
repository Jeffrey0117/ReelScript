import { test } from 'node:test';
import assert from 'node:assert/strict';
import { limitsFor, applyLimit, lockedAt, TIER_LIMITS, FULL } from '../src/lib/modes/access.ts';

test('visitors and free members are limited, paid members are not', () => {
	assert.equal(limitsFor({ tier: 'guest', owner: false }), TIER_LIMITS.guest);
	assert.equal(limitsFor({ tier: 'free', owner: false }), TIER_LIMITS.free);
	assert.equal(limitsFor({ tier: 'pro', owner: false }), FULL);
});

test('a member never hits a wall on their own video', () => {
	assert.equal(limitsFor({ tier: 'free', owner: true }), FULL);
});

test('missing or unknown access is treated as a visitor, never as full access', () => {
	assert.equal(limitsFor(null), TIER_LIMITS.guest);
	assert.equal(limitsFor(undefined), TIER_LIMITS.guest);
	assert.equal(limitsFor({ tier: 'vip', owner: false }), TIER_LIMITS.guest);
});

test('free members get more than visitors, and visitors get no Chinese', () => {
	assert.ok(TIER_LIMITS.free.lines > TIER_LIMITS.guest.lines);
	assert.ok(TIER_LIMITS.free.words > TIER_LIMITS.guest.words);
	assert.equal(TIER_LIMITS.guest.chinese, false);
	assert.equal(TIER_LIMITS.free.chinese, true);
	assert.equal(TIER_LIMITS.free.print, false);
});

test('applyLimit keeps the first N and counts the rest', () => {
	assert.deepEqual(applyLimit([1, 2, 3, 4], 3), { shown: [1, 2, 3], hidden: 1 });
	assert.deepEqual(applyLimit([1, 2], 5), { shown: [1, 2], hidden: 0 });
	assert.deepEqual(applyLimit([1, 2], Infinity), { shown: [1, 2], hidden: 0 });
	assert.deepEqual(applyLimit([1, 2], -1), { shown: [], hidden: 2 });
});

test('applyLimit returns a copy', () => {
	const input = [1, 2];
	const { shown } = applyLimit(input, 9);
	shown.push(3);
	assert.deepEqual(input, [1, 2]);
});

test('lockedAt is the start of the first hidden line, null when nothing is hidden', () => {
	const lines = [{ start: 0 }, { start: 2 }, { start: 5 }];
	assert.equal(lockedAt(lines, 2), 5);
	assert.equal(lockedAt(lines, 3), null);
	assert.equal(lockedAt(lines, Infinity), null);
	assert.equal(lockedAt([], 2), null);
});
