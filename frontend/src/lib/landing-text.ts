// Copy for the descriptive part of the landing page (what it is, who it is for,
// questions people ask). Kept apart from lib/i18n.ts, which is at its size limit.
//
// Chinese is a working draft in the house structure (concrete everyday scenes,
// blame the method not the reader, numbers over adjectives) — meant to be
// reworded by Jeff, who owns the voice.

import { getLocale } from '$lib/i18n';

export interface LandingText {
	description: string;
	painKicker: string;
	painTitle: string;
	painLead: string;
	pains: string[];
	waysKicker: string;
	waysTitle: string;
	waysLead: string;
	ways: { name: string; desc: string }[];
	faqTitle: string;
	faqs: { q: string; a: string }[];
}

const zh: LandingText = {
	description:
		'ReelScript 把 YouTube、Instagram Reels 影片變成英文教材：貼上連結，自動產生逐字稿、中英對照、單字本，同一支影片還能切成閱讀、Podcast、打字練習、講義六種學法。',

	painKicker: '看短影音學英文，卡在哪',
	painTitle: '你不是不夠認真，是短影音本來就不是拿來學的',
	painLead: '中了兩個以上，下面那段就是寫給你的。',
	pains: [
		'收藏了一堆英文 Reels，一支都沒有回去看',
		'聽得懂七成，剩下三成永遠不知道他到底講了什麼',
		'開字幕看完就忘，關掉字幕又跟不上',
		'想抄一個單字，暫停、倒帶、查字典，三十秒的片弄了十分鐘',
		'單字書背了好幾輪，真人一開口還是聽不出來',
	],

	waysKicker: '貼上連結就好',
	waysTitle: '同一支影片，六種學法',
	waysLead: '逐字稿、翻譯、單字都自動做好，你只要挑今天想怎麼用它。',
	ways: [
		{ name: '影片', desc: '左邊影片、右邊逐字稿，點哪一句就從哪一句播，可以單句重複。' },
		{ name: '閱讀', desc: '整支影片變成一篇文章：純英文、純中文、中英、逐句對照，四種排法。' },
		{ name: 'Podcast', desc: '不看畫面只用聽的，字幕像歌詞一樣跟著走，通勤也能練聽力。' },
		{ name: '打字練習', desc: '播一句停一句，把聽到的打出來，關鍵字挖空要用耳朵補，打完看速度和正確率。' },
		{ name: '單字本', desc: '這支影片的單字排成一本筆記，中文先蓋住，想到了再點開對答案。' },
		{ name: '講義', desc: '主旨、重點、金句、單字表、逐句對照、填空練習，一頁印出來就能上課。' },
	],

	faqTitle: '常見問題',
	faqs: [
		{
			q: 'ReelScript 是什麼？',
			a: 'ReelScript 是看影片學英文的工具。貼上 YouTube 或 Instagram Reels 的連結，它會把影片變成逐字稿、中英對照和單字表，再讓你用六種方式練習同一支影片。',
		},
		{
			q: '支援哪些影片？',
			a: 'YouTube、Instagram、TikTok、Bilibili 的英文影片都可以，短影音最適合，一支三十秒到幾分鐘的片就是一堂課。',
		},
		{
			q: '跟直接開字幕看有什麼不一樣？',
			a: '字幕是一閃就過。這裡每一句都留在畫面上，可以點、可以重播、可以查單字、可以收藏，還能換成用聽的、用打的、用印的。',
		},
		{
			q: '要付費嗎？',
			a: '免費註冊每個月有 30 點可以處理自己的影片，官方教材不用點數就能打開。想把每支影片整支用完，再升級就好。',
		},
		{
			q: '沒有自己的影片也能用嗎？',
			a: '可以。教材頁有整理好的影片，逐字稿、翻譯、單字都做完了，打開就能練。',
		},
	],
};

const en: LandingText = {
	description:
		'ReelScript turns YouTube videos and Instagram Reels into English lessons: paste a link and get a transcript, Chinese translation and a wordbook, then study the same video six ways — watch, read, listen, type, review words, print a handout.',

	painKicker: 'Learning English from short videos',
	painTitle: 'You are not lazy. Short videos were never built for studying.',
	painLead: 'If two of these sound like you, keep reading.',
	pains: [
		'A folder full of saved English Reels you never opened again',
		'You catch 70% and never find out what the other 30% was',
		'With subtitles you forget it; without them you cannot keep up',
		'Looking up one word means pause, rewind, dictionary — ten minutes for a 30-second clip',
		'You finished the vocabulary book and still cannot follow a real person talking',
	],

	waysKicker: 'Just paste a link',
	waysTitle: 'One video, six ways to study it',
	waysLead: 'Transcript, translation and vocabulary are done for you. Pick how you want to use it today.',
	ways: [
		{ name: 'Video', desc: 'Video on the left, transcript on the right. Click a line to play from it, or loop one sentence.' },
		{ name: 'Read', desc: 'The video as an article: English only, Chinese only, mixed, or side by side.' },
		{ name: 'Podcast', desc: 'Audio only with captions that follow along like lyrics.' },
		{ name: 'Typing', desc: 'It plays a line and waits while you type it. Key words are blanked so your ears do the work.' },
		{ name: 'Wordbook', desc: 'The words of this video in a notebook, Chinese hidden until you tap it.' },
		{ name: 'Handout', desc: 'Main idea, key points, quotes, word table, sentences and a cloze exercise on one printable page.' },
	],

	faqTitle: 'Questions',
	faqs: [
		{
			q: 'What is ReelScript?',
			a: 'ReelScript is a tool for learning English from videos. Paste a YouTube or Instagram Reels link and it becomes a transcript, a translation and a word list you can practice six different ways.',
		},
		{
			q: 'Which videos work?',
			a: 'English videos from YouTube, Instagram, TikTok and Bilibili. Short videos work best.',
		},
		{
			q: 'How is this different from turning subtitles on?',
			a: 'Subtitles flash by. Here every line stays on the page: click it, replay it, look up a word, save it — or switch to listening, typing or a printout.',
		},
		{
			q: 'Is it free?',
			a: 'A free account gets 30 credits a month for your own videos, and the official library opens without credits. Upgrade when you want every video to the end.',
		},
		{
			q: 'What if I have no videos of my own?',
			a: 'The library has prepared videos with transcript, translation and vocabulary already done.',
		},
	],
};

export function landingText(): LandingText {
	return getLocale() === 'en' ? en : zh;
}
