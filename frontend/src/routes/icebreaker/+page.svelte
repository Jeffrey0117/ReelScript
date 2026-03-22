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
		{ id: 13, en: "What's a dish from your culture that everyone should try?", zh: '你的文化中有什麼菜每個人都該嘗嘗？', category: 'food' },

		// Entertainment & Hobbies
		{ id: 14, en: "What's the last movie that made you cry?", zh: '最近一部讓你哭的電影是什麼？', category: 'entertainment' },
		{ id: 15, en: "What song do you know all the lyrics to?", zh: '你能完整唱出歌詞的歌是哪首？', category: 'entertainment' },
		{ id: 16, en: "What TV show are you currently binge-watching?", zh: '你最近在追什麼劇？', category: 'entertainment' },
		{ id: 17, en: "Do you have any hidden talents?", zh: '你有什麼隱藏才能嗎？', category: 'entertainment' },
		{ id: 18, en: "What hobby would you pick up if time and money weren't an issue?", zh: '如果時間和金錢不是問題，你想培養什麼嗜好？', category: 'entertainment' },
		{ id: 19, en: "What's the best concert or live event you've been to?", zh: '你去過最棒的演唱會或現場活動是什麼？', category: 'entertainment' },
		{ id: 20, en: "What book changed the way you think?", zh: '哪本書改變了你的思考方式？', category: 'entertainment' },

		// Work & Goals
		{ id: 21, en: "What do you do for a living, and do you enjoy it?", zh: '你的工作是什麼？你喜歡嗎？', category: 'work' },
		{ id: 22, en: "What did you want to be when you were a kid?", zh: '你小時候想當什麼？', category: 'work' },
		{ id: 23, en: "What's the most interesting project you've worked on?", zh: '你做過最有趣的專案是什麼？', category: 'work' },
		{ id: 24, en: "If you didn't need to work, what would you do with your time?", zh: '如果不用工作，你會怎麼利用你的時間？', category: 'work' },
		{ id: 25, en: "What skill are you currently trying to learn?", zh: '你目前正在學什麼技能？', category: 'work' },
		{ id: 26, en: "What's one goal you want to accomplish this year?", zh: '你今年想完成的一個目標是什麼？', category: 'work' },

		// Hypothetical & Fun
		{ id: 27, en: "If you could have dinner with anyone, dead or alive, who would it be?", zh: '如果你能和任何人共進晚餐（不論古今），你會選誰？', category: 'fun' },
		{ id: 28, en: "If you won the lottery, what's the first thing you'd do?", zh: '如果你中了樂透，你第一件會做的事是什麼？', category: 'fun' },
		{ id: 29, en: "If you could have any superpower, what would you choose?", zh: '如果你能擁有一種超能力，你會選什麼？', category: 'fun' },
		{ id: 30, en: "If you could time travel, would you go to the past or the future?", zh: '如果你能穿越時空，你會去過去還是未來？', category: 'fun' },
		{ id: 31, en: "If you could switch lives with someone for a day, who would it be?", zh: '如果你能跟某人交換一天人生，你會選誰？', category: 'fun' },
		{ id: 32, en: "What three things would you bring to a desert island?", zh: '你會帶哪三樣東西去無人島？', category: 'fun' },
		{ id: 33, en: "If you could instantly master any language, which one would you pick?", zh: '如果你能瞬間精通一種語言，你會選哪個？', category: 'fun' },
		{ id: 34, en: "Would you rather explore outer space or the deep ocean?", zh: '你比較想探索外太空還是深海？', category: 'fun' },

		// People & Relationships
		{ id: 35, en: "Who has been the biggest influence in your life?", zh: '誰對你的人生影響最大？', category: 'people' },
		{ id: 36, en: "What quality do you value most in a friend?", zh: '你最重視朋友的什麼特質？', category: 'people' },
		{ id: 37, en: "What's the nicest thing someone has ever done for you?", zh: '別人為你做過最好的事是什麼？', category: 'people' },
		{ id: 38, en: "How do you like to spend time with your family?", zh: '你喜歡怎麼跟家人共度時光？', category: 'people' },

		// Technology & Modern Life
		{ id: 39, en: "What app on your phone do you use the most?", zh: '你手機上最常用的 app 是什麼？', category: 'tech' },
		{ id: 40, en: "Do you think AI will change our lives for better or worse?", zh: '你覺得 AI 會讓我們的生活變好還是變差？', category: 'tech' },
		{ id: 41, en: "What's the best purchase you've made recently?", zh: '你最近買過最值得的東西是什麼？', category: 'tech' },
		{ id: 42, en: "How do you unplug from technology?", zh: '你怎麼從科技中抽離放鬆？', category: 'tech' },

		// Self-reflection
		{ id: 43, en: "What are you most grateful for right now?", zh: '你現在最感恩的事是什麼？', category: 'self' },
		{ id: 44, en: "How would your best friend describe you in three words?", zh: '你最好的朋友會用哪三個字形容你？', category: 'self' },
		{ id: 45, en: "What's something you've changed your mind about recently?", zh: '你最近改變看法的一件事是什麼？', category: 'self' },
		{ id: 46, en: "What's your biggest pet peeve?", zh: '什麼事情最讓你受不了？', category: 'self' },
		{ id: 47, en: "What does a perfect weekend look like for you?", zh: '你理想中的完美週末是什麼樣子？', category: 'self' },
		{ id: 48, en: "Are you a morning person or a night owl?", zh: '你是早起的人還是夜貓子？', category: 'self' },

		// Random & Quirky
		{ id: 49, en: "What's the most useless fact you know?", zh: '你知道最沒用的冷知識是什麼？', category: 'quirky' },
		{ id: 50, en: "If your life had a theme song, what would it be?", zh: '如果你的人生有一首主題曲，會是哪首？', category: 'quirky' },
		{ id: 51, en: "What's the funniest thing that happened to you this week?", zh: '你這週發生最好笑的事是什麼？', category: 'quirky' },
		{ id: 52, en: "If you could send a message to your future self, what would you say?", zh: '如果你能傳一則訊息給未來的自己，你會說什麼？', category: 'quirky' },
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
	};

	let deck = $state<IcebreakerCard[]>([]);
	let currentIndex = $state(-1);
	let isFlipping = $state(false);
	let isRevealed = $state(false);
	let drawnCount = $state(0);
	let visible = $state(false);
	let showAllCards = $state(false);
	let isLoggedIn = $state(false);

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
		}, 300);
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
		onAuthChange((u) => {
			isLoggedIn = !!u;
		});
		requestAnimationFrame(() => { visible = true; });
	});

	let currentCard = $derived(currentIndex >= 0 ? deck[currentIndex] : null);
	let locale = $derived(getLocale());
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
			<div class="drawn-card" class:flip-in={isRevealed}>
				<div class="card-category" style="--cat-color: {categoryColors[currentCard.category]}">
					{locale === 'zh' ? categoryLabels[currentCard.category].zh : categoryLabels[currentCard.category].en}
				</div>
				<div class="card-number">#{currentCard.id}</div>
				<p class="card-en">{currentCard.en}</p>
				<p class="card-zh">{currentCard.zh}</p>
				<div class="card-tip">
					<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
						<path d="M12 20h9"/><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"/>
					</svg>
					Try answering in English!
				</div>
			</div>
		{:else}
			<div class="card-back" class:flip-out={isFlipping}>
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

	<!-- ReelScript Promo -->
	<section class="promo">
		<div class="promo-glow"></div>
		<div class="promo-content">
			<div class="promo-badge">ReelScript</div>
			<h2 class="promo-title">
				{locale === 'zh' ? '想讓英文口說更流利？' : 'Want to speak English more fluently?'}
			</h2>
			<p class="promo-desc">
				{locale === 'zh'
					? '用真實影片學英文——逐字稿、翻譯、單字分析、金句提取，一鍵搞定。把 YouTube 影片變成你的私人英文教室。'
					: 'Learn English from real videos — transcripts, translations, vocabulary analysis, and golden quotes, all in one click. Turn YouTube videos into your personal English classroom.'
				}
			</p>
			<div class="promo-features">
				<div class="promo-feature">
					<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
						<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
						<polyline points="14 2 14 8 20 8"/>
						<line x1="16" y1="13" x2="8" y2="13"/>
						<line x1="16" y1="17" x2="8" y2="17"/>
					</svg>
					<span>{locale === 'zh' ? 'AI 自動逐字稿' : 'AI Auto Transcription'}</span>
				</div>
				<div class="promo-feature">
					<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
						<path d="M5 8l6 6"/><path d="M4 14l6-6 2-3"/><path d="M2 5h12"/><path d="M7 2h1"/>
						<path d="M22 22l-5-10-5 10"/><path d="M14 18h6"/>
					</svg>
					<span>{locale === 'zh' ? '中英對照翻譯' : 'Bilingual Translation'}</span>
				</div>
				<div class="promo-feature">
					<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
						<path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/>
						<path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/>
					</svg>
					<span>{locale === 'zh' ? '智慧單字分析' : 'Vocabulary Analysis'}</span>
				</div>
				<div class="promo-feature">
					<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
						<polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>
					</svg>
					<span>{locale === 'zh' ? '金句提取' : 'Golden Quotes'}</span>
				</div>
			</div>
			<button class="promo-cta" onclick={handleCta}>
				{locale === 'zh' ? '免費開始使用 ReelScript' : 'Try ReelScript for Free'}
				<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
					<line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/>
				</svg>
			</button>
			<p class="promo-note">
				{locale === 'zh' ? '每月 30 點免費額度，不需信用卡' : '30 free credits/month, no credit card required'}
			</p>
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

	.flip-in {
		animation: card-flip-in 0.4s ease-out;
	}

	@keyframes card-flip-in {
		0% {
			opacity: 0;
			transform: rotateY(90deg) scale(0.9);
		}
		50% {
			opacity: 0.5;
		}
		100% {
			opacity: 1;
			transform: rotateY(0deg) scale(1);
		}
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

	.flip-out {
		animation: card-flip-out 0.3s ease-in;
	}

	@keyframes card-flip-out {
		0% {
			transform: scale(1);
			opacity: 1;
		}
		100% {
			transform: scale(0.95) rotateY(90deg);
			opacity: 0;
		}
	}

	.card-back-content {
		text-align: center;
	}

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

	.draw-btn:disabled {
		opacity: 0.6;
		cursor: not-allowed;
	}

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

	.mini-number {
		font-size: 12px;
		font-weight: 700;
		color: var(--text-dim);
		opacity: 0.5;
	}

	.mini-category {
		font-size: 10px;
		font-weight: 600;
		text-transform: uppercase;
		letter-spacing: 0.5px;
		color: var(--cat-color);
	}

	.mini-en {
		font-size: 14px;
		font-weight: 600;
		color: var(--text);
		line-height: 1.4;
		margin-bottom: 4px;
	}

	.mini-zh {
		font-size: 12px;
		color: var(--text-dim);
		line-height: 1.4;
	}

	/* ── Promo ── */
	.promo {
		position: relative;
		border-top: 1px solid var(--border);
		padding: 64px 0 72px;
		overflow: hidden;
	}

	.promo-glow {
		position: absolute;
		bottom: -60px;
		left: 50%;
		transform: translateX(-50%);
		width: 500px;
		height: 300px;
		background: radial-gradient(ellipse, color-mix(in srgb, var(--accent) 8%, transparent) 0%, transparent 70%);
		pointer-events: none;
	}

	.promo-content {
		position: relative;
		text-align: center;
		max-width: 560px;
		margin: 0 auto;
	}

	.promo-badge {
		display: inline-block;
		font-size: 12px;
		font-weight: 700;
		letter-spacing: 1.5px;
		text-transform: uppercase;
		padding: 6px 16px;
		border-radius: 20px;
		background: color-mix(in srgb, var(--accent) 12%, transparent);
		color: var(--accent);
		margin-bottom: 20px;
	}

	.promo-title {
		font-size: 28px;
		font-weight: 700;
		letter-spacing: -0.5px;
		margin-bottom: 12px;
	}

	.promo-desc {
		font-size: 15px;
		line-height: 1.7;
		color: var(--text-dim);
		margin-bottom: 28px;
	}

	.promo-features {
		display: grid;
		grid-template-columns: repeat(2, 1fr);
		gap: 12px;
		margin-bottom: 32px;
	}

	.promo-feature {
		display: flex;
		align-items: center;
		gap: 10px;
		padding: 12px 16px;
		background: var(--bg-card);
		border: 1px solid var(--border);
		border-radius: var(--radius-sm);
		font-size: 13px;
		font-weight: 500;
		color: var(--text);
	}

	.promo-feature svg {
		flex-shrink: 0;
		color: var(--accent);
	}

	.promo-cta {
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
		margin-bottom: 12px;
	}

	.promo-cta:hover {
		background: var(--accent-hover);
		transform: translateY(-1px);
		box-shadow: 0 6px 24px color-mix(in srgb, var(--accent) 40%, transparent);
	}

	.promo-note {
		font-size: 13px;
		color: var(--text-dim);
	}

	/* ── Responsive ── */
	@media (max-width: 900px) {
		.all-cards-grid {
			grid-template-columns: repeat(2, 1fr);
		}
	}

	@media (max-width: 640px) {
		.hero {
			padding: 36px 0 20px;
		}

		.hero-title {
			font-size: 24px;
			flex-direction: column;
			gap: 8px;
		}

		.hero-sub {
			font-size: 15px;
		}

		.card-en {
			font-size: 18px;
		}

		.card-zh {
			font-size: 14px;
		}

		.drawn-card {
			padding: 24px 20px;
		}

		.card-back {
			height: 220px;
		}

		.draw-btn {
			padding: 12px 24px;
			font-size: 14px;
		}

		.card-controls {
			flex-direction: column;
			gap: 12px;
		}

		.all-cards-grid {
			grid-template-columns: 1fr;
		}

		.promo-title {
			font-size: 22px;
		}

		.promo-features {
			grid-template-columns: 1fr;
		}

		.promo-cta {
			width: 100%;
			justify-content: center;
		}
	}
</style>
