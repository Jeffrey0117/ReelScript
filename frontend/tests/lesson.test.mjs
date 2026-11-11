import { test } from 'node:test';
import assert from 'node:assert/strict';
import {
	mergeSentences,
	uniqueVocabulary,
	toParagraphs,
	formatTime,
	activeIndex,
	currentIndex,
	readingMinutes,
	keyWords,
	exampleFor,
} from '../src/lib/lesson.ts';

const seg = (index, start, end, text, translation = '', vocabulary = []) => ({
	index,
	start,
	end,
	text,
	translation,
	vocabulary,
});

test('mergeSentences glues whisper fragments until sentence punctuation', () => {
	const result = mergeSentences([
		seg(1, 0, 1, 'A large rug', '一塊大地毯'),
		seg(2, 1, 2, 'will make the floor look bigger.', '會讓地板看起來更大。'),
		seg(3, 2, 3, 'Less is more!', '少即是多！'),
	]);
	assert.equal(result.length, 2);
	assert.equal(result[0].en, 'A large rug will make the floor look bigger.');
	assert.equal(result[0].zh, '一塊大地毯會讓地板看起來更大。');
	assert.equal(result[0].start, 0);
	assert.equal(result[0].end, 2);
	assert.equal(result[1].en, 'Less is more!');
});

test('mergeSentences keeps a trailing fragment and skips empty segments', () => {
	const result = mergeSentences([seg(1, 0, 1, '   '), seg(2, 1, 2, 'Done.'), seg(3, 2, 3, 'and then')]);
	assert.deepEqual(
		result.map((s) => s.en),
		['Done.', 'and then']
	);
});

test('mergeSentences treats a closing quote after the period as an ending', () => {
	const result = mergeSentences([seg(1, 0, 1, 'He said "stop."'), seg(2, 1, 2, 'Fine.')]);
	assert.equal(result.length, 2);
});

test('mergeSentences does not mutate its input', () => {
	const input = [seg(1, 0, 1, 'One.'), seg(2, 1, 2, 'Two.')];
	const snapshot = JSON.stringify(input);
	mergeSentences(input);
	assert.equal(JSON.stringify(input), snapshot);
});

test('uniqueVocabulary dedupes case-insensitively and keeps first seen', () => {
	const result = uniqueVocabulary([
		seg(1, 0, 1, 'x', '', [{ word: 'Rug', translation: '地毯' }]),
		seg(2, 1, 2, 'y', '', [
			{ word: 'rug', translation: '毯子' },
			{ word: 'bulky', translation: '笨重的' },
		]),
	]);
	assert.deepEqual(
		result.map((v) => v.word),
		['Rug', 'bulky']
	);
	assert.equal(result[0].translation, '地毯');
});

test('toParagraphs chunks and never loops on a bad size', () => {
	assert.deepEqual(toParagraphs([1, 2, 3, 4, 5], 2), [[1, 2], [3, 4], [5]]);
	assert.deepEqual(toParagraphs([1, 2], 0), [[1], [2]]);
	assert.deepEqual(toParagraphs([], 3), []);
});

test('formatTime handles minutes and bad input', () => {
	assert.equal(formatTime(0), '0:00');
	assert.equal(formatTime(65.9), '1:05');
	assert.equal(formatTime(NaN), '0:00');
	assert.equal(formatTime(-3), '0:00');
});

test('activeIndex is -1 between lines, currentIndex holds the last started line', () => {
	const lines = [
		{ start: 0, end: 1 },
		{ start: 2, end: 3 },
	];
	assert.equal(activeIndex(lines, 0.5), 0);
	assert.equal(activeIndex(lines, 1.5), -1);
	assert.equal(currentIndex(lines, 1.5), 0);
	assert.equal(currentIndex(lines, 2.2), 1);
	assert.equal(currentIndex(lines, -1), -1);
	assert.equal(currentIndex(lines, 99), 1);
});

test('readingMinutes is at least one minute', () => {
	assert.equal(readingMinutes([]), 1);
	const long = [{ en: Array(400).fill('word').join(' '), zh: '', vocabulary: [], start: 0, end: 1 }];
	assert.equal(readingMinutes(long), 2);
});

test('keyWords picks content words once, skipping known, short, common and contracted ones', () => {
	const result = keyWords(
		[
			seg(1, 0, 1, "Here's six things I would not do in a small room."),
			seg(2, 1, 2, 'Avoid bulky furniture, bulky Furniture really.'),
		],
		[{ word: 'furniture', translation: '傢俱' }]
	);
	assert.deepEqual(result, ['small', 'avoid', 'bulky']);
});

test('keyWords respects the limit', () => {
	const result = keyWords([seg(1, 0, 1, 'alpha bravo charlie delta echoes foxtrot')], [], 2);
	assert.deepEqual(result, ['alpha', 'bravo']);
});

test('exampleFor finds the first sentence containing the word and survives regex characters', () => {
	const sentences = [
		{ en: 'First is small rugs.', zh: '', vocabulary: [], start: 0, end: 1 },
		{ en: 'A large rug helps.', zh: '', vocabulary: [], start: 1, end: 2 },
	];
	assert.equal(exampleFor(sentences, 'rug'), 'First is small rugs.');
	assert.equal(exampleFor(sentences, 'large'), 'A large rug helps.');
	assert.equal(exampleFor(sentences, 'c++ (x'), '');
	assert.equal(exampleFor(sentences, ''), '');
});
