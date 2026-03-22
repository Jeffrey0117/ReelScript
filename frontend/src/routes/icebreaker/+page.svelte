<script lang="ts">
	import { onMount } from 'svelte';
	import { t, getLocale } from '$lib/i18n';
	import { onAuthChange, login, getUser } from '$lib/auth';
	import { goto } from '$app/navigation';

	interface IcebreakerCard {
		id: number;
		en: string;
		zh: string;
		category: string;
		planted?: 'snippet' | 'vocab' | 'quote';
	}

	interface Snippet {
		en: string;
		zh: string;
		timestamp: string;
		videoTitle: string | null;
		videoId: string;
		source: string;
		channel: string | null;
	}

	interface VocabWord {
		word: string;
		translation: string;
		videoTitle: string | null;
	}

	interface Quote {
		en: string;
		zh: string;
		videoTitle: string | null;
		channel: string | null;
	}

	const allCards: IcebreakerCard[] = [
		// Life & Experience
		{ id: 1, en: "What's the best trip you've ever taken?", zh: '你去過最棒的旅行是什麼？', category: 'life' },
		{ id: 2, en: "If you could live anywhere in the world, where would it be?", zh: '如果你能住在世界上任何地方，你會選哪裡？', category: 'life' },
		{ id: 3, en: "What's the most adventurous thing you've ever done?", zh: '你做過最冒險的事是什麼？', category: 'life' },
		{ id: 4, en: "What's your morning routine like?", zh: '你的早晨日常是什麼樣的？', category: 'life' },
		{ id: 5, en: "If you could relive one day of your life, which day would it be?", zh: '如果你能重新過一天，你會選哪一天？', category: 'life' },
		{ id: 6, en: "What's the best advice you've ever received?", zh: '你收過最好的建議是什麼？', category: 'life' },
		{ id: 7, en: "What's something you've always wanted to try but haven't yet?", zh: '有什麼事你一直想嘗試但還沒做過？', category: 'life' },
		{ id: 8, en: "What's your happiest childhood memory?", zh: '你最快樂的童年回憶是什麼？', category: 'life' },

		// Food & Culture
		{ id: 9, en: "What's your go-to comfort food?", zh: '你最愛的療癒食物是什麼？', category: 'food' },
		{ id: 10, en: "What's the weirdest food you've ever tried?", zh: '你吃過最奇怪的食物是什麼？', category: 'food' },
		{ id: 11, en: "If you could only eat one cuisine for the rest of your life, what would it be?", zh: '如果你這輩子只能吃一種料理，你會選什麼？', category: 'food' },
		{ id: 12, en: "Do you prefer cooking at home or eating out?", zh: '你比較喜歡在家煮還是外食？', category: 'food' },

		// Entertainment & Hobbies
		{ id: 13, en: "What's the last movie that made you cry?", zh: '最近一部讓你哭的電影是什麼？', category: 'entertainment' },
		{ id: 14, en: "What song do you know all the lyrics to?", zh: '你能完整唱出歌詞的歌是哪首？', category: 'entertainment' },
		{ id: 15, en: "What TV show are you currently binge-watching?", zh: '你最近在追什麼劇？', category: 'entertainment' },
		{ id: 16, en: "Do you have any hidden talents?", zh: '你有什麼隱藏才能嗎？', category: 'entertainment' },
		{ id: 17, en: "What hobby would you pick up if time and money weren't an issue?", zh: '如果時間和金錢不是問題，你想培養什麼嗜好？', category: 'entertainment' },

		// Work & Goals
		{ id: 18, en: "What do you do for a living, and do you enjoy it?", zh: '你的工作是什麼？你喜歡嗎？', category: 'work' },
		{ id: 19, en: "What did you want to be when you were a kid?", zh: '你小時候想當什麼？', category: 'work' },
		{ id: 20, en: "If you didn't need to work, what would you do with your time?", zh: '如果不用工作，你會怎麼利用你的時間？', category: 'work' },
		{ id: 21, en: "What skill are you currently trying to learn?", zh: '你目前正在學什麼技能？', category: 'work' },
		{ id: 22, en: "What's one goal you want to accomplish this year?", zh: '你今年想完成的一個目標是什麼？', category: 'work' },

		// Hypothetical & Fun
		{ id: 23, en: "If you could have dinner with anyone, dead or alive, who would it be?", zh: '如果你能和任何人共進晚餐（不論古今），你會選誰？', category: 'fun' },
		{ id: 24, en: "If you won the lottery, what's the first thing you'd do?", zh: '如果你中了樂透，你第一件會做的事是什麼？', category: 'fun' },
		{ id: 25, en: "If you could have any superpower, what would you choose?", zh: '如果你能擁有一種超能力，你會選什麼？', category: 'fun' },
		{ id: 26, en: "If you could time travel, would you go to the past or the future?", zh: '如果你能穿越時空，你會去過去還是未來？', category: 'fun' },
		{ id: 27, en: "What three things would you bring to a desert island?", zh: '你會帶哪三樣東西去無人島？', category: 'fun' },
		{ id: 28, en: "If you could instantly master any language, which one would you pick?", zh: '如果你能瞬間精通一種語言，你會選哪個？', category: 'fun' },
		{ id: 29, en: "Would you rather explore outer space or the deep ocean?", zh: '你比較想探索外太空還是深海？', category: 'fun' },

		// People & Relationships
		{ id: 30, en: "Who has been the biggest influence in your life?", zh: '誰對你的人生影響最大？', category: 'people' },
		{ id: 31, en: "What quality do you value most in a friend?", zh: '你最重視朋友的什麼特質？', category: 'people' },
		{ id: 32, en: "What's the nicest thing someone has ever done for you?", zh: '別人為你做過最好的事是什麼？', category: 'people' },
		{ id: 33, en: "How do you like to spend time with your family?", zh: '你喜歡怎麼跟家人共度時光？', category: 'people' },

		// Technology & Modern Life
		{ id: 34, en: "What app on your phone do you use the most?", zh: '你手機上最常用的 app 是什麼？', category: 'tech' },
		{ id: 35, en: "Do you think AI will change our lives for better or worse?", zh: '你覺得 AI 會讓我們的生活變好還是變差？', category: 'tech' },
		{ id: 36, en: "How do you unplug from technology?", zh: '你怎麼從科技中抽離放鬆？', category: 'tech' },

		// Self-reflection
		{ id: 37, en: "What are you most grateful for right now?", zh: '你現在最感恩的事是什麼？', category: 'self' },
		{ id: 38, en: "How would your best friend describe you in three words?", zh: '你最好的朋友會用哪三個字形容你？', category: 'self' },
		{ id: 39, en: "What does a perfect weekend look like for you?", zh: '你理想中的完美週末是什麼樣子？', category: 'self' },
		{ id: 40, en: "Are you a morning person or a night owl?", zh: '你是早起的人還是夜貓子？', category: 'self' },

		// Random & Quirky
		{ id: 41, en: "What's the most useless fact you know?", zh: '你知道最沒用的冷知識是什麼？', category: 'quirky' },
		{ id: 42, en: "If your life had a theme song, what would it be?", zh: '如果你的人生有一首主題曲，會是哪首？', category: 'quirky' },
		{ id: 43, en: "What's the funniest thing that happened to you this week?", zh: '你這週發生最好笑的事是什麼？', category: 'quirky' },
		{ id: 44, en: "If you could send a message to your future self, what would you say?", zh: '如果你能傳一則訊息給未來的自己，你會說什麼？', category: 'quirky' },

		// ── Planted: Video Learning ──
		{ id: 45, en: "Have you ever tried learning English by watching YouTube videos?", zh: '你有試過用 YouTube 影片學英文嗎？', category: 'learning', planted: 'snippet' },
		{ id: 46, en: "What's the most useful English phrase you picked up from a video?", zh: '你從影片中學到最實用的英文片語是什麼？', category: 'learning', planted: 'vocab' },
		{ id: 47, en: "Do you prefer learning English from movies, podcasts, or short videos?", zh: '你比較喜歡從電影、Podcast 還是短影片學英文？', category: 'learning', planted: 'snippet' },
		{ id: 48, en: "If you could have subtitles in real life, would you turn them on?", zh: '如果現實生活可以開字幕，你會開嗎？', category: 'learning', planted: 'snippet' },
		{ id: 49, en: "What's a new English word you recently learned that you're proud of?", zh: '你最近學到哪個英文單字讓你最得意？', category: 'learning', planted: 'vocab' },
		{ id: 50, en: "Have you ever tried shadowing along with an English speaker in a video?", zh: '你有跟著影片裡的英文一起跟讀過嗎？', category: 'learning', planted: 'snippet' },
		{ id: 51, en: "What YouTube channel has taught you something you didn't expect?", zh: '哪個 YouTube 頻道教了你意想不到的東西？', category: 'learning', planted: 'quote' },
		{ id: 52, en: "Do you think watching videos with Chinese subtitles helps or hurts your English?", zh: '你覺得看影片配中文字幕對學英文有幫助還是有害？', category: 'learning', planted: 'snippet' },
	];

	const categoryLabels: Record<string, { en: string; zh: string }> = {
		life: { en: 'Life & Experience', zh: '生活與經歷' },
		food: { en: 'Food & Culture', zh: '美食與文化' },
		entertainment: { en: 'Entertainment', zh: '娛樂嗜好' },
		work: { en: 'Work & Goals', zh: '工作目標' },
		fun: { en: 'Hypothetical', zh: '假設情境' },
		people: { en: 'Relationships', zh: '人際關係' },
		tech: { en: 'Tech & Modern', zh: '科技生活' },
		self: { en: 'Self-reflection', zh: '自我反思' },
		quirky: { en: 'Random & Fun', zh: '隨機趣味' },
		learning: { en: 'English Learning', zh: '英文學習' },
	};

	const categoryColors: Record<string, string> = {
		life: '#6366f1',
		food: '#f59e0b',
		entertainment: '#ec4899',
		work: '#3b82f6',
		fun: '#8b5cf6',
		people: '#10b981',
		tech: '#06b6d4',
		self: '#f97316',
		quirky: '#ef4444',
		learning: '#22c55e',
	};

	let deck = $state<IcebreakerCard[]>([]);
	let currentIndex = $state(-1);
	let isFlipping = $state(false);
	let isRevealed = $state(false);
	let drawnCount = $state(0);
	let visible = $state(false);
	let showAllCards = $state(false);
	let isLoggedIn = $state(false);

	// API data for planted cards
	let snippets = $state<Snippet[]>([]);
	let vocabWords = $state<VocabWord[]>([]);
	let quotes = $state<Quote[]>([]);
	let snippetIdx = $state(0);
	let vocabIdx = $state(0);
	let quoteIdx = $state(0);

	function shuffle(arr: IcebreakerCard[]): IcebreakerCard[] {
		const shuffled = [...arr];
		for (let i = shuffled.length - 1; i > 0; i--) {
			const j = Math.floor(Math.random() * (i + 1));
			[shuffled[i], shuffled[j]] = [shuffled[j], shuffled[i]];
		}
		return shuffled;
	}

	function initDeck() {
		deck = shuffle(allCards);
		currentIndex = -1;
		isRevealed = false;
		drawnCount = 0;
	}

	function drawCard() {
		if (isFlipping) return;

		if (currentIndex >= deck.length - 1) {
			initDeck();
			return;
		}

		isFlipping = true;
		isRevealed = false;

		setTimeout(() => {
			currentIndex += 1;
			drawnCount += 1;
			isRevealed = true;
			isFlipping = false;

			// Cycle through examples for planted cards
			const card = deck[currentIndex];
			if (card.planted === 'snippet') snippetIdx = (snippetIdx + 1) % Math.max(snippets.length, 1);
			if (card.planted === 'vocab') vocabIdx = (vocabIdx + 1) % Math.max(vocabWords.length, 1);
			if (card.planted === 'quote') quoteIdx = (quoteIdx + 1) % Math.max(quotes.length, 1);
		}, 300);
	}

	async function fetchExamples() {
		try {
			const [snippetRes, vocabRes, quoteRes] = await Promise.all([
				fetch('/api/public/snippet/random').then(r => r.ok ? r.json() : null),
				fetch('/api/public/vocabulary?limit=8').then(r => r.ok ? r.json() : null),
				fetch('/api/public/quotes?limit=5').then(r => r.ok ? r.json() : null),
			]);

			// Collect multiple snippets
			if (snippetRes) snippets = [snippetRes];
			// Fetch a few more snippets
			for (let i = 0; i < 4; i++) {
				try {
					const extra = await fetch('/api/public/snippet/random').then(r => r.ok ? r.json() : null);
					if (extra && extra.en !== snippets[0]?.en) snippets = [...snippets, extra];
				} catch { /* skip */ }
			}

			if (vocabRes?.words) vocabWords = vocabRes.words;
			if (quoteRes?.quotes) quotes = quoteRes.quotes;
		} catch { /* API unavailable, planted cards show without examples */ }
	}

	function handleCta() {
		if (isLoggedIn) {
			goto('/videos');
		} else {
			login();
		}
	}

	onMount(() => {
		initDeck();
		fetchExamples();
		onAuthChange((u) => {
			isLoggedIn = !!u;
		});
		requestAnimationFrame(() => { visible = true; });
	});

	let currentCard = $derived(currentIndex >= 0 ? deck[currentIndex] : null);
	let locale = $derived(getLocale());

	let currentSnippet = $derived(snippets.length > 0 ? snippets[snippetIdx % snippets.length] : null);
	let currentVocab = $derived(vocabWords.length >= 3 ? vocabWords.slice(vocabIdx, vocabIdx + 3) : vocabWords);
	let currentQuote = $derived(quotes.length > 0 ? quotes[quoteIdx % quotes.length] : null);
</script>

<svelte:head>
	<title>English Icebreaker Cards - ReelScript</title>
	<meta name="description" content="52 English icebreaker conversation topics with Chinese translations. Perfect for practicing English speaking skills." />
</svelte:head>

<div class="page" class:visible>
	<!-- Hero -->
	<section class="hero">
		<div class="hero-glow"></div>
		<h1 class="hero-title">
			<span class="title-icon">
				<svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
					<rect x="2" y="2" width="20" height="20" rx="3"/>
					<path d="M8 8h.01M12 12h.01M16 8h.01M8 16h.01M16 16h.01"/>
				</svg>
			</span>
			English Icebreaker Cards
		</h1>
		<p class="hero-sub">52 張英文破冰話題卡——隨機抽一張，開口說英文！</p>
		<p class="hero-sub-en">Draw a card, start a conversation. Perfect for English speaking practice.</p>
	</section>

	<!-- Card Area -->
	<section class="card-area">
		{#if currentCard && isRevealed}
			<div class="drawn-card" class:flip-in={isRevealed} class:planted-card={!!currentCard.planted}>
				<div class="card-category" style="--cat-color: {categoryColors[currentCard.category]}">
					{locale === 'zh' ? categoryLabels[currentCard.category].zh : categoryLabels[currentCard.category].en}
				</div>
				<div class="card-number">#{currentCard.id}</div>
				<p class="card-en">{currentCard.en}</p>
				<p class="card-zh">{currentCard.zh}</p>

				<!-- Planted card: show real example -->
				{#if currentCard.planted === 'snippet' && currentSnippet}
					<div class="example-box">
						<div class="example-label">
							<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
								<polygon points="5 3 19 12 5 21 5 3"/>
							</svg>
							{locale === 'zh' ? '看看真實影片中的例子：' : 'Here\'s a real example from a video:'}
						</div>
						<div class="example-snippet">
							<div class="snippet-meta">
								{#if currentSnippet.channel}<span class="snippet-channel">{currentSnippet.channel}</span>{/if}
								<span class="snippet-time">{currentSnippet.timestamp}</span>
							</div>
							<p class="snippet-en">"{currentSnippet.en}"</p>
							<p class="snippet-zh">{currentSnippet.zh}</p>
						</div>
						<a href="/blog" class="example-cta">
							{locale === 'zh' ? '在 ReelScript 上探索更多影片學習' : 'Explore more on ReelScript'}
							<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/></svg>
						</a>
					</div>
				{:else if currentCard.planted === 'vocab' && currentVocab.length > 0}
					<div class="example-box">
						<div class="example-label">
							<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
								<path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/>
								<path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/>
							</svg>
							{locale === 'zh' ? '用戶從影片中學到的真實單字：' : 'Real words learned from videos:'}
						</div>
						<div class="example-vocab">
							{#each currentVocab as word}
								<div class="vocab-row">
									<span class="vocab-word">{word.word}</span>
									<span class="vocab-trans">{word.translation}</span>
								</div>
							{/each}
						</div>
						<a href="/blog" class="example-cta">
							{locale === 'zh' ? '在 ReelScript 上建立你的單字庫' : 'Build your word bank on ReelScript'}
							<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/></svg>
						</a>
					</div>
				{:else if currentCard.planted === 'quote' && currentQuote}
					<div class="example-box">
						<div class="example-label">
							<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--accent)" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
								<polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>
							</svg>
							{locale === 'zh' ? '來自真實影片的金句：' : 'A golden quote from a real video:'}
						</div>
						<div class="example-quote">
							<p class="quote-en">"{currentQuote.en}"</p>
							<p class="quote-zh">{currentQuote.zh}</p>
							{#if currentQuote.channel}
								<p class="quote-source">— {currentQuote.channel}</p>
							{/if}
						</div>
						<a href="/blog" class="example-cta">
							{locale === 'zh' ? '在 ReelScript 上發現更多金句' : 'Discover more quotes on ReelScript'}
							<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/></svg>
						</a>
					</div>
				{:else}
					<div class="card-tip">
						<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
							<path d="M12 20h9"/><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"/>
						</svg>
						Try answering in English!
					</div>
				{/if}
			</div>
		{:else}
			<div class="card-back" class:flip-out={isFlipping} onclick={drawCard} role="button" tabindex="0" onkeydown={(e) => e.key === 'Enter' && drawCard()}>
				<div class="card-back-content">
					<div class="card-back-icon">?</div>
					<p class="card-back-text">
						{currentIndex === -1 ? 'Tap to draw your first card' : 'Drawing...'}
					</p>
				</div>
			</div>
		{/if}

		<div class="card-controls">
			<button class="draw-btn" onclick={drawCard} disabled={isFlipping}>
				{#if currentIndex >= deck.length - 1}
					<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
						<polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/>
					</svg>
					Reshuffle & Restart
				{:else}
					<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
						<rect x="3" y="3" width="18" height="18" rx="3"/><path d="M12 8v8M8 12h8"/>
					</svg>
					{currentIndex === -1 ? 'Draw a Card' : 'Next Card'}
				{/if}
			</button>
			<div class="card-counter">
				{drawnCount} / 52
			</div>
		</div>
	</section>

	<!-- All Cards Toggle -->
	<section class="all-section">
		<button class="toggle-all-btn" onclick={() => showAllCards = !showAllCards}>
			<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
				{#if showAllCards}
					<polyline points="18 15 12 9 6 15"/>
				{:else}
					<polyline points="6 9 12 15 18 9"/>
				{/if}
			</svg>
			{showAllCards ? 'Hide All Cards' : 'View All 52 Cards'}
		</button>

		{#if showAllCards}
			<div class="all-cards-grid">
				{#each allCards as card (card.id)}
					<div class="mini-card" style="--cat-color: {categoryColors[card.category]}">
						<div class="mini-header">
							<span class="mini-number">#{card.id}</span>
							<span class="mini-category">
								{locale === 'zh' ? categoryLabels[card.category].zh : categoryLabels[card.category].en}
							</span>
						</div>
						<p class="mini-en">{card.en}</p>
						<p class="mini-zh">{card.zh}</p>
					</div>
				{/each}
			</div>
		{/if}
	</section>

	<!-- Banner Ad -->
	<section class="banner">
		<div class="banner-bg">
			<div class="banner-gradient"></div>
			<div class="banner-dots"></div>
		</div>
		<div class="banner-inner">
			<!-- Left: Product Mockup -->
			<div class="banner-mockup">
				<div class="mockup-window">
					<div class="mockup-toolbar">
						<div class="mockup-dots">
							<span></span><span></span><span></span>
						</div>
						<span class="mockup-url">reelscript.isnowfriend.com</span>
					</div>
					<div class="mockup-content">
						<div class="mockup-video">
							<svg width="24" height="24" viewBox="0 0 24 24" fill="white" opacity="0.8"><polygon points="5 3 19 12 5 21 5 3"/></svg>
						</div>
						<div class="mockup-transcript">
							<div class="mockup-line">
								<span class="ml-time">0:15</span>
								<span class="ml-en">The key to success is consistency.</span>
							</div>
							<div class="mockup-line-zh">成功的關鍵是持之以恆。</div>
							<div class="mockup-line">
								<span class="ml-time">0:18</span>
								<span class="ml-en">You have to show up every single day.</span>
							</div>
							<div class="mockup-line-zh">你必須每天都到場。</div>
							<div class="mockup-line">
								<span class="ml-time">0:22</span>
								<span class="ml-en">It's not about talent, it's about discipline.</span>
							</div>
							<div class="mockup-line-zh">這不是天賦的問題，而是紀律。</div>
						</div>
						<div class="mockup-vocab">
							<span class="mv-word">consistency</span>
							<span class="mv-pos">n.</span>
							<span class="mv-zh">一致性；堅持</span>
						</div>
					</div>
				</div>
			</div>

			<!-- Right: Copy + CTA -->
			<div class="banner-copy">
				<div class="banner-badge">ReelScript</div>
				<h2 class="banner-title">
					{locale === 'zh' ? '把 YouTube 影片變成你的英文教室' : 'Turn YouTube Videos Into Your English Classroom'}
				</h2>
				<p class="banner-desc">
					{locale === 'zh'
						? 'AI 自動產生逐字稿、中英對照翻譯、單字分析、金句提取——一鍵完成，用你喜歡的影片學英文。'
						: 'AI-powered transcripts, bilingual translations, vocabulary analysis, and golden quotes — learn English from videos you actually enjoy.'
					}
				</p>
				<div class="banner-stats">
					<div class="stat">
						<span class="stat-icon">
							<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
						</span>
						<span>{locale === 'zh' ? 'AI 逐字稿' : 'AI Transcript'}</span>
					</div>
					<div class="stat">
						<span class="stat-icon">
							<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 8l6 6"/><path d="M4 14l6-6 2-3"/><path d="M2 5h12"/><path d="M7 2h1"/><path d="M22 22l-5-10-5 10"/><path d="M14 18h6"/></svg>
						</span>
						<span>{locale === 'zh' ? '中英翻譯' : 'Translation'}</span>
					</div>
					<div class="stat">
						<span class="stat-icon">
							<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/></svg>
						</span>
						<span>{locale === 'zh' ? '單字分析' : 'Vocabulary'}</span>
					</div>
					<div class="stat">
						<span class="stat-icon">
							<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>
						</span>
						<span>{locale === 'zh' ? '金句提取' : 'Quotes'}</span>
					</div>
				</div>
				<button class="banner-cta" onclick={handleCta}>
					{locale === 'zh' ? '免費開始使用' : 'Start Free'}
					<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/></svg>
				</button>
				<p class="banner-note">{locale === 'zh' ? '每月 30 點免費額度 · 不需信用卡' : '30 free credits/month · No credit card'}</p>
			</div>
		</div>
	</section>
</div>

<style>
	.page {
		opacity: 0;
		transition: opacity 0.5s ease;
	}

	.page.visible {
		opacity: 1;
	}

	/* ── Hero ── */
	.hero {
		position: relative;
		text-align: center;
		padding: 56px 0 32px;
		overflow: hidden;
	}

	.hero-glow {
		position: absolute;
		top: -100px;
		left: 50%;
		transform: translateX(-50%);
		width: 600px;
		height: 350px;
		background: radial-gradient(ellipse, color-mix(in srgb, var(--accent) 10%, transparent) 0%, transparent 70%);
		pointer-events: none;
	}

	.hero-title {
		position: relative;
		display: flex;
		align-items: center;
		justify-content: center;
		gap: 12px;
		font-size: 36px;
		font-weight: 800;
		letter-spacing: -1px;
		margin-bottom: 12px;
		background: linear-gradient(135deg, var(--text) 0%, var(--text-dim) 100%);
		-webkit-background-clip: text;
		-webkit-text-fill-color: transparent;
		background-clip: text;
	}

	.title-icon {
		display: flex;
		color: var(--accent);
		-webkit-text-fill-color: var(--accent);
	}

	.hero-sub {
		position: relative;
		font-size: 17px;
		color: var(--text);
		margin-bottom: 4px;
		font-weight: 500;
	}

	.hero-sub-en {
		position: relative;
		font-size: 14px;
		color: var(--text-dim);
		margin-bottom: 0;
	}

	/* ── Card Area ── */
	.card-area {
		display: flex;
		flex-direction: column;
		align-items: center;
		padding: 32px 0 40px;
	}

	.drawn-card {
		width: 100%;
		max-width: 480px;
		background: var(--bg-card);
		border: 2px solid var(--border);
		border-radius: 16px;
		padding: 32px 28px;
		text-align: center;
		position: relative;
		box-shadow: 0 8px 40px rgba(0, 0, 0, 0.12);
		transition: border-color 0.3s;
	}

	.drawn-card:hover {
		border-color: color-mix(in srgb, var(--accent) 40%, var(--border));
	}

	.planted-card {
		border-color: color-mix(in srgb, #22c55e 30%, var(--border));
		max-width: 520px;
	}

	.flip-in {
		animation: card-flip-in 0.4s ease-out;
	}

	@keyframes card-flip-in {
		0% { opacity: 0; transform: rotateY(90deg) scale(0.9); }
		50% { opacity: 0.5; }
		100% { opacity: 1; transform: rotateY(0deg) scale(1); }
	}

	.card-category {
		display: inline-block;
		font-size: 11px;
		font-weight: 600;
		text-transform: uppercase;
		letter-spacing: 1px;
		padding: 4px 12px;
		border-radius: 20px;
		background: color-mix(in srgb, var(--cat-color) 15%, transparent);
		color: var(--cat-color);
		margin-bottom: 16px;
	}

	.card-number {
		position: absolute;
		top: 16px;
		right: 20px;
		font-size: 13px;
		font-weight: 600;
		color: var(--text-dim);
		opacity: 0.5;
	}

	.card-en {
		font-size: 22px;
		font-weight: 700;
		line-height: 1.4;
		color: var(--text);
		margin-bottom: 12px;
		letter-spacing: -0.3px;
	}

	.card-zh {
		font-size: 16px;
		color: var(--text-dim);
		line-height: 1.5;
		margin-bottom: 20px;
	}

	.card-tip {
		display: inline-flex;
		align-items: center;
		gap: 6px;
		font-size: 12px;
		color: var(--accent);
		font-weight: 500;
		opacity: 0.7;
	}

	/* ── Example Box (Planted Cards) ── */
	.example-box {
		margin-top: 4px;
		padding-top: 20px;
		border-top: 1px dashed var(--border);
		text-align: left;
	}

	.example-label {
		display: flex;
		align-items: center;
		gap: 6px;
		font-size: 12px;
		font-weight: 600;
		color: #22c55e;
		margin-bottom: 12px;
		text-transform: uppercase;
		letter-spacing: 0.5px;
	}

	.example-snippet {
		background: var(--bg-hover);
		border-radius: var(--radius-sm);
		padding: 14px 16px;
		margin-bottom: 12px;
	}

	.snippet-meta {
		display: flex;
		align-items: center;
		gap: 8px;
		margin-bottom: 8px;
	}

	.snippet-channel {
		font-size: 11px;
		font-weight: 600;
		color: var(--accent);
		background: color-mix(in srgb, var(--accent) 10%, transparent);
		padding: 2px 8px;
		border-radius: 4px;
	}

	.snippet-time {
		font-size: 11px;
		color: var(--text-dim);
		font-family: monospace;
	}

	.snippet-en {
		font-size: 14px;
		font-weight: 600;
		color: var(--text);
		line-height: 1.5;
		margin-bottom: 4px;
		font-style: italic;
	}

	.snippet-zh {
		font-size: 13px;
		color: var(--text-dim);
		line-height: 1.4;
	}

	.example-vocab {
		display: flex;
		flex-direction: column;
		gap: 8px;
		margin-bottom: 12px;
	}

	.vocab-row {
		display: flex;
		align-items: center;
		gap: 12px;
		padding: 8px 12px;
		background: var(--bg-hover);
		border-radius: 6px;
	}

	.vocab-word {
		font-size: 14px;
		font-weight: 700;
		color: var(--accent);
		min-width: 100px;
	}

	.vocab-trans {
		font-size: 13px;
		color: var(--text-dim);
	}

	.example-quote {
		background: var(--bg-hover);
		border-radius: var(--radius-sm);
		padding: 16px;
		margin-bottom: 12px;
		border-left: 3px solid var(--accent);
	}

	.quote-en {
		font-size: 15px;
		font-weight: 600;
		color: var(--text);
		line-height: 1.5;
		font-style: italic;
		margin-bottom: 6px;
	}

	.quote-zh {
		font-size: 13px;
		color: var(--text-dim);
		margin-bottom: 6px;
	}

	.quote-source {
		font-size: 12px;
		color: var(--text-dim);
		opacity: 0.7;
	}

	.example-cta {
		display: inline-flex;
		align-items: center;
		gap: 4px;
		font-size: 12px;
		font-weight: 600;
		color: var(--accent) !important;
		text-decoration: none;
		transition: gap 0.15s;
	}

	.example-cta:hover {
		gap: 8px;
	}

	/* Card Back */
	.card-back {
		width: 100%;
		max-width: 480px;
		height: 260px;
		background: linear-gradient(145deg, var(--bg-card), color-mix(in srgb, var(--accent) 5%, var(--bg-card)));
		border: 2px dashed var(--border);
		border-radius: 16px;
		display: flex;
		align-items: center;
		justify-content: center;
		cursor: pointer;
		transition: border-color 0.2s, transform 0.2s;
	}

	.card-back:hover {
		border-color: var(--accent);
		transform: scale(1.01);
	}

	.flip-out { animation: card-flip-out 0.3s ease-in; }

	@keyframes card-flip-out {
		0% { transform: scale(1); opacity: 1; }
		100% { transform: scale(0.95) rotateY(90deg); opacity: 0; }
	}

	.card-back-content { text-align: center; }

	.card-back-icon {
		font-size: 48px;
		font-weight: 800;
		color: var(--accent);
		margin-bottom: 8px;
		opacity: 0.6;
	}

	.card-back-text {
		font-size: 14px;
		color: var(--text-dim);
	}

	/* Controls */
	.card-controls {
		display: flex;
		align-items: center;
		gap: 16px;
		margin-top: 24px;
	}

	.draw-btn {
		display: inline-flex;
		align-items: center;
		gap: 8px;
		padding: 14px 28px;
		background: var(--accent);
		color: white;
		font-size: 15px;
		font-weight: 600;
		border-radius: var(--radius);
		border: none;
		cursor: pointer;
		transition: background 0.2s, transform 0.15s, box-shadow 0.2s;
		box-shadow: 0 4px 16px color-mix(in srgb, var(--accent) 30%, transparent);
	}

	.draw-btn:hover:not(:disabled) {
		background: var(--accent-hover);
		transform: translateY(-1px);
		box-shadow: 0 6px 24px color-mix(in srgb, var(--accent) 40%, transparent);
	}

	.draw-btn:disabled { opacity: 0.6; cursor: not-allowed; }

	.card-counter {
		font-size: 14px;
		font-weight: 600;
		color: var(--text-dim);
		padding: 8px 16px;
		background: var(--bg-card);
		border: 1px solid var(--border);
		border-radius: var(--radius-sm);
	}

	/* ── All Cards ── */
	.all-section {
		padding: 0 0 48px;
		text-align: center;
	}

	.toggle-all-btn {
		display: inline-flex;
		align-items: center;
		gap: 6px;
		padding: 10px 20px;
		background: transparent;
		color: var(--text-dim);
		font-size: 14px;
		font-weight: 500;
		border: 1px solid var(--border);
		border-radius: var(--radius-sm);
		cursor: pointer;
		transition: all 0.15s;
	}

	.toggle-all-btn:hover {
		color: var(--text);
		border-color: var(--accent);
	}

	.all-cards-grid {
		display: grid;
		grid-template-columns: repeat(3, 1fr);
		gap: 12px;
		margin-top: 24px;
		text-align: left;
	}

	.mini-card {
		background: var(--bg-card);
		border: 1px solid var(--border);
		border-radius: var(--radius-sm);
		padding: 16px;
		transition: border-color 0.2s, transform 0.15s;
		border-left: 3px solid var(--cat-color);
	}

	.mini-card:hover {
		border-color: color-mix(in srgb, var(--cat-color) 50%, var(--border));
		transform: translateY(-1px);
	}

	.mini-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		margin-bottom: 8px;
	}

	.mini-number { font-size: 12px; font-weight: 700; color: var(--text-dim); opacity: 0.5; }
	.mini-category { font-size: 10px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; color: var(--cat-color); }
	.mini-en { font-size: 14px; font-weight: 600; color: var(--text); line-height: 1.4; margin-bottom: 4px; }
	.mini-zh { font-size: 12px; color: var(--text-dim); line-height: 1.4; }

	/* ── Banner Ad ── */
	.banner {
		position: relative;
		margin: 0 -32px;
		padding: 0;
		overflow: hidden;
	}

	.banner-bg {
		position: absolute;
		inset: 0;
		background: linear-gradient(135deg, #1e1b4b 0%, #312e81 40%, #4338ca 100%);
		z-index: 0;
	}

	:global([data-theme="light"]) .banner-bg {
		background: linear-gradient(135deg, #eef2ff 0%, #c7d2fe 40%, #a5b4fc 100%);
	}

	.banner-gradient {
		position: absolute;
		top: -50%;
		right: -20%;
		width: 500px;
		height: 500px;
		background: radial-gradient(circle, rgba(99, 102, 241, 0.3) 0%, transparent 70%);
		pointer-events: none;
	}

	.banner-dots {
		position: absolute;
		inset: 0;
		background-image: radial-gradient(rgba(255, 255, 255, 0.07) 1px, transparent 1px);
		background-size: 24px 24px;
		pointer-events: none;
	}

	:global([data-theme="light"]) .banner-dots {
		background-image: radial-gradient(rgba(0, 0, 0, 0.05) 1px, transparent 1px);
	}

	.banner-inner {
		position: relative;
		z-index: 1;
		display: flex;
		align-items: center;
		gap: 48px;
		max-width: 1200px;
		margin: 0 auto;
		padding: 56px 48px;
	}

	/* Mockup */
	.banner-mockup {
		flex-shrink: 0;
		width: 380px;
	}

	.mockup-window {
		background: #0f0f17;
		border-radius: 12px;
		overflow: hidden;
		box-shadow: 0 20px 60px rgba(0, 0, 0, 0.4);
		border: 1px solid rgba(255, 255, 255, 0.08);
	}

	:global([data-theme="light"]) .mockup-window {
		background: #fff;
		border-color: #d4d4d8;
		box-shadow: 0 20px 60px rgba(0, 0, 0, 0.12);
	}

	.mockup-toolbar {
		display: flex;
		align-items: center;
		gap: 12px;
		padding: 10px 14px;
		background: rgba(255, 255, 255, 0.04);
		border-bottom: 1px solid rgba(255, 255, 255, 0.06);
	}

	:global([data-theme="light"]) .mockup-toolbar {
		background: #f5f5f5;
		border-bottom-color: #e4e4e7;
	}

	.mockup-dots {
		display: flex;
		gap: 6px;
	}

	.mockup-dots span {
		width: 8px;
		height: 8px;
		border-radius: 50%;
		background: rgba(255, 255, 255, 0.15);
	}

	:global([data-theme="light"]) .mockup-dots span {
		background: #d4d4d8;
	}

	.mockup-dots span:first-child { background: #ef4444; }
	.mockup-dots span:nth-child(2) { background: #f59e0b; }
	.mockup-dots span:nth-child(3) { background: #22c55e; }

	.mockup-url {
		font-size: 11px;
		color: rgba(255, 255, 255, 0.35);
		font-family: monospace;
	}

	:global([data-theme="light"]) .mockup-url { color: #a1a1aa; }

	.mockup-content { padding: 12px; }

	.mockup-video {
		background: linear-gradient(135deg, #1a1a2e, #16213e);
		border-radius: 8px;
		height: 60px;
		display: flex;
		align-items: center;
		justify-content: center;
		margin-bottom: 12px;
	}

	:global([data-theme="light"]) .mockup-video {
		background: linear-gradient(135deg, #e0e7ff, #c7d2fe);
	}

	:global([data-theme="light"]) .mockup-video svg { fill: #4338ca; }

	.mockup-transcript {
		display: flex;
		flex-direction: column;
		gap: 2px;
		margin-bottom: 10px;
	}

	.mockup-line {
		display: flex;
		align-items: center;
		gap: 8px;
		padding: 4px 8px;
		border-radius: 4px;
	}

	.mockup-line:first-child {
		background: rgba(99, 102, 241, 0.12);
	}

	.ml-time {
		font-size: 10px;
		font-family: monospace;
		color: rgba(255, 255, 255, 0.3);
		flex-shrink: 0;
	}

	:global([data-theme="light"]) .ml-time { color: #a1a1aa; }

	.ml-en {
		font-size: 12px;
		color: rgba(255, 255, 255, 0.85);
		font-weight: 500;
	}

	:global([data-theme="light"]) .ml-en { color: #18181b; }

	.mockup-line-zh {
		font-size: 11px;
		color: rgba(255, 255, 255, 0.4);
		padding-left: 44px;
		margin-bottom: 4px;
	}

	:global([data-theme="light"]) .mockup-line-zh { color: #71717a; }

	.mockup-vocab {
		display: flex;
		align-items: center;
		gap: 6px;
		padding: 6px 10px;
		background: rgba(99, 102, 241, 0.08);
		border-radius: 6px;
		border: 1px solid rgba(99, 102, 241, 0.15);
	}

	.mv-word { font-size: 12px; font-weight: 700; color: #818cf8; }
	.mv-pos { font-size: 10px; color: rgba(255, 255, 255, 0.3); font-style: italic; }
	.mv-zh { font-size: 11px; color: rgba(255, 255, 255, 0.5); }

	:global([data-theme="light"]) .mv-word { color: #4f46e5; }
	:global([data-theme="light"]) .mv-pos { color: #a1a1aa; }
	:global([data-theme="light"]) .mv-zh { color: #71717a; }

	/* Banner Copy */
	.banner-copy {
		flex: 1;
		min-width: 0;
	}

	.banner-badge {
		display: inline-block;
		font-size: 11px;
		font-weight: 700;
		letter-spacing: 1.5px;
		text-transform: uppercase;
		padding: 4px 12px;
		border-radius: 20px;
		background: rgba(255, 255, 255, 0.12);
		color: #c7d2fe;
		margin-bottom: 16px;
	}

	:global([data-theme="light"]) .banner-badge {
		background: rgba(67, 56, 202, 0.12);
		color: #4338ca;
	}

	.banner-title {
		font-size: 28px;
		font-weight: 800;
		letter-spacing: -0.5px;
		color: white;
		margin-bottom: 12px;
		line-height: 1.2;
	}

	:global([data-theme="light"]) .banner-title { color: #1e1b4b; }

	.banner-desc {
		font-size: 15px;
		line-height: 1.65;
		color: rgba(255, 255, 255, 0.7);
		margin-bottom: 20px;
	}

	:global([data-theme="light"]) .banner-desc { color: #4338ca; opacity: 0.8; }

	.banner-stats {
		display: grid;
		grid-template-columns: repeat(2, 1fr);
		gap: 8px;
		margin-bottom: 24px;
	}

	.stat {
		display: flex;
		align-items: center;
		gap: 8px;
		font-size: 13px;
		font-weight: 500;
		color: rgba(255, 255, 255, 0.85);
	}

	:global([data-theme="light"]) .stat { color: #312e81; }

	.stat-icon {
		display: flex;
		color: #a5b4fc;
	}

	:global([data-theme="light"]) .stat-icon { color: #6366f1; }

	.banner-cta {
		display: inline-flex;
		align-items: center;
		gap: 8px;
		padding: 14px 32px;
		background: white;
		color: #312e81;
		font-size: 15px;
		font-weight: 700;
		border-radius: var(--radius);
		border: none;
		cursor: pointer;
		transition: transform 0.15s, box-shadow 0.2s;
		box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2);
		margin-bottom: 10px;
	}

	:global([data-theme="light"]) .banner-cta {
		background: #4338ca;
		color: white;
		box-shadow: 0 4px 20px rgba(67, 56, 202, 0.3);
	}

	.banner-cta:hover {
		transform: translateY(-1px);
		box-shadow: 0 8px 30px rgba(0, 0, 0, 0.3);
	}

	:global([data-theme="light"]) .banner-cta:hover {
		box-shadow: 0 8px 30px rgba(67, 56, 202, 0.4);
	}

	.banner-note {
		font-size: 12px;
		color: rgba(255, 255, 255, 0.45);
	}

	:global([data-theme="light"]) .banner-note { color: #6366f1; }

	/* ── Responsive ── */
	@media (max-width: 900px) {
		.all-cards-grid { grid-template-columns: repeat(2, 1fr); }

		.banner-inner {
			flex-direction: column;
			padding: 40px 32px;
			gap: 32px;
		}

		.banner-mockup {
			width: 100%;
			max-width: 380px;
		}

		.banner-copy { text-align: center; }
		.banner-stats { max-width: 320px; margin-left: auto; margin-right: auto; }
	}

	@media (max-width: 640px) {
		.hero { padding: 36px 0 20px; }
		.hero-title { font-size: 24px; flex-direction: column; gap: 8px; }
		.hero-sub { font-size: 15px; }
		.card-en { font-size: 18px; }
		.card-zh { font-size: 14px; }
		.drawn-card { padding: 24px 20px; }
		.planted-card { max-width: 100%; }
		.card-back { height: 220px; }
		.draw-btn { padding: 12px 24px; font-size: 14px; }
		.card-controls { flex-direction: column; gap: 12px; }
		.all-cards-grid { grid-template-columns: 1fr; }

		.banner { margin: 0 -12px; }
		.banner-inner { padding: 32px 20px; }
		.banner-title { font-size: 22px; }
		.banner-desc { font-size: 14px; }
		.banner-stats { grid-template-columns: 1fr; }
		.banner-cta { width: 100%; justify-content: center; }

		.mockup-window { transform: scale(0.92); transform-origin: top center; }
	}
</style>
