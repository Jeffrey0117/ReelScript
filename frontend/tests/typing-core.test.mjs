import { test } from 'node:test';
import assert from 'node:assert/strict';
import {
	norm,
	same,
	lineDone,
	wordAt,
	wordSpans,
	pickBlanks,
	autoBlankCount,
	wholeLine,
	needsSeek,
	seekTarget,
	lineIndexAt,
	createScore,
	isWeakWord,
} from '../src/lib/typing-core.ts';

test('norm maps untypeable characters to typeable ones', () => {
	assert.equal(norm('’'), "'");
	assert.equal(norm('“'), '"');
	assert.equal(norm('—'), '-');
	assert.equal(norm('…'), '.');
	assert.equal(norm('é'), 'e');
	assert.equal(norm(' '), ' ');
	assert.equal(norm('a'), 'a');
});

test('same ignores case and smart quotes, rejects undefined', () => {
	assert.equal(same('i', 'I'), true);
	assert.equal(same("'", '’'), true);
	assert.equal(same('a', 'b'), false);
	assert.equal(same(undefined, 'a'), false);
});

test('lineDone needs the full line, not more and not less', () => {
	assert.equal(lineDone('less is more.', 'Less is more.'), true);
	assert.equal(lineDone('less is more', 'Less is more.'), false);
	assert.equal(lineDone('less is more..', 'Less is more.'), false);
	assert.equal(lineDone('less is mare.', 'Less is more.'), false);
});

test('wordAt returns the word under the cursor', () => {
	assert.equal(wordAt('small rugs here', 7), 'rugs');
	assert.equal(wordAt('small rugs', 0), 'small');
	assert.equal(wordAt('small', 99), '');
});

test('wordSpans locates english words', () => {
	assert.deepEqual(wordSpans("Don't stop"), [
		{ from: 0, to: 5, word: "Don't" },
		{ from: 6, to: 10, word: 'stop' },
	]);
});

test('pickBlanks is deterministic, prefers content words and stays sorted', () => {
	const text = 'A large rug will make the floor look bigger.';
	const first = pickBlanks(text, 2);
	assert.deepEqual(first, pickBlanks(text, 2));
	assert.equal(first.length, 2);
	assert.ok(first[0].from < first[1].from);
	for (const blank of first) {
		assert.equal(text.slice(blank.from, blank.to), blank.word);
		assert.equal(isWeakWord(blank.word), false);
		assert.ok(blank.word.length >= 4);
	}
});

test('pickBlanks still blanks something when every word is weak, and nothing for no words', () => {
	assert.equal(pickBlanks('Oh I do', 1).length, 1);
	assert.deepEqual(pickBlanks('... 123', 1), []);
	assert.equal(pickBlanks('Hello there', 9).length, 2);
});

test('autoBlankCount scales with line length', () => {
	assert.equal(autoBlankCount('Less is more.'), 1);
	assert.equal(autoBlankCount('one two three four five six seven eight nine ten eleven twelve'), 2);
});

test('wholeLine covers the entire text', () => {
	assert.deepEqual(wholeLine('abc'), [{ from: 0, to: 3, word: 'abc' }]);
	assert.deepEqual(wholeLine(''), []);
});

test('needsSeek rewinds inside a line, jumps when far, waits when close', () => {
	const line = { text: 'x', start: 10, end: 12 };
	assert.equal(needsSeek(11, line), true);
	assert.equal(needsSeek(2, line), true);
	assert.equal(needsSeek(8, line), false);
	assert.equal(needsSeek(8, line, true), true);
	assert.equal(needsSeek(8, null), false);
});

test('seekTarget starts slightly early but never below zero', () => {
	assert.equal(seekTarget({ text: 'x', start: 10, end: 12 }, 0.5), 9.5);
	assert.equal(seekTarget({ text: 'x', start: 0.1, end: 1 }), 0);
	assert.equal(seekTarget(null), 0);
});

test('lineIndexAt returns the first unfinished line, last line when past the end', () => {
	const lines = [
		{ text: 'a', start: 0, end: 1 },
		{ text: 'b', start: 1, end: 2 },
	];
	assert.equal(lineIndexAt(0.5, lines), 0);
	assert.equal(lineIndexAt(1.5, lines), 1);
	assert.equal(lineIndexAt(9, lines), 1);
	assert.equal(lineIndexAt(1, []), 0);
});

test('createScore counts only active typing time and tracks misses', () => {
	let clock = 0;
	const score = createScore({ now: () => clock });
	score.key(true);
	clock = 30_000;
	score.key(false, 'rug');
	score.key(false, 'rug');
	score.key(true);
	score.lineCleared('x'.repeat(50));
	clock = 600_000; // idle time after the line must not count
	assert.equal(score.seconds(), 30);
	assert.equal(score.wpm(), 20);
	assert.equal(score.accuracy(), 50);
	assert.deepEqual(score.top(), [['rug', 2]]);
	score.reset();
	assert.equal(score.wpm(), 0);
	assert.equal(score.accuracy(), 100);
	assert.deepEqual(score.top(), []);
});
