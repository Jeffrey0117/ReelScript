type Locale = 'zh' | 'en';

const translations = {
	zh: {
		// Navbar
		home: '首頁',
		collections: '收藏集',

		// Home page
		addVideo: '新增影片',
		urlPlaceholder: '貼上 YouTube 或 Instagram 連結...',
		processing: '處理中...',
		start: '開始',
		myVideos: '我的影片',
		noVideos: '還沒有影片，貼上連結開始吧！',
		statusReady: '完成',
		statusProcessing: '處理中',
		statusDownloading: '下載中',
		statusTranscribing: '轉錄中',
		statusFailed: '失敗',
		statusPending: '等待中',

		// Watch page
		loading: '載入中...',
		videoNotAvailable: '影片無法播放',
		untitled: '未命名',
		loopOff: '循環 關',
		loopAll: '循環 全部',
		loopOne: '循環 單句',
		addToCollection: '+ 收藏',
		copyText: '複製文字',
		copied: '已複製！',
		delete: '刪除',
		confirmDelete: '確定要刪除這部影片和逐字稿嗎？',
		transcript: '逐字稿',
		segments: '段',
		translateChinese: '翻譯中文',
		translating: '翻譯中...',
		fullText: '全文',
		noTranscript: '尚無逐字稿。',
		repeatSentence: '重複此句',

		// Collections page
		myCollections: '我的收藏集',
		newCollection: '新增收藏集',
		collectionName: '收藏集名稱',
		create: '建立',
		cancel: '取消',
		noCollections: '還沒有收藏集。',
		videos: '部影片',
		addToCollectionTitle: '加入收藏集',
		noCollectionsYet: '還沒有收藏集，請先到收藏集頁面建立。',
		removeFromCollection: '移除',
		notes: '筆記',
	},
	en: {
		// Navbar
		home: 'Home',
		collections: 'Collections',

		// Home page
		addVideo: 'Add Video',
		urlPlaceholder: 'Paste YouTube or Instagram URL...',
		processing: 'Processing...',
		start: 'Start',
		myVideos: 'My Videos',
		noVideos: 'No videos yet. Paste a URL to get started!',
		statusReady: 'Ready',
		statusProcessing: 'Processing',
		statusDownloading: 'Downloading',
		statusTranscribing: 'Transcribing',
		statusFailed: 'Failed',
		statusPending: 'Pending',

		// Watch page
		loading: 'Loading...',
		videoNotAvailable: 'Video not available',
		untitled: 'Untitled',
		loopOff: 'Loop Off',
		loopAll: 'Loop All',
		loopOne: 'Loop 1',
		addToCollection: '+ Collection',
		copyText: 'Copy Text',
		copied: 'Copied!',
		delete: 'Delete',
		confirmDelete: 'Delete this video and its transcript?',
		transcript: 'Transcript',
		segments: 'segments',
		translateChinese: 'Translate 中文',
		translating: 'Translating...',
		fullText: 'Full Text',
		noTranscript: 'No transcript available yet.',
		repeatSentence: 'Repeat this sentence',

		// Collections page
		myCollections: 'My Collections',
		newCollection: 'New Collection',
		collectionName: 'Collection name',
		create: 'Create',
		cancel: 'Cancel',
		noCollections: 'No collections yet.',
		videos: 'videos',
		addToCollectionTitle: 'Add to Collection',
		noCollectionsYet: 'No collections yet. Create one from the Collections page.',
		removeFromCollection: 'Remove',
		notes: 'Notes',
	},
} as const;

type TranslationKey = keyof typeof translations.zh;

let currentLocale: Locale = 'zh';
const subscribers: Set<() => void> = new Set();

export function getLocale(): Locale {
	return currentLocale;
}

export function setLocale(locale: Locale) {
	currentLocale = locale;
	if (typeof localStorage !== 'undefined') {
		localStorage.setItem('reelscript-locale', locale);
	}
	subscribers.forEach((fn) => fn());
}

export function initLocale() {
	if (typeof localStorage !== 'undefined') {
		const saved = localStorage.getItem('reelscript-locale');
		if (saved === 'en' || saved === 'zh') {
			currentLocale = saved;
		}
	}
}

export function t(key: TranslationKey): string {
	return translations[currentLocale][key] ?? translations.en[key] ?? key;
}

export function onLocaleChange(fn: () => void): () => void {
	subscribers.add(fn);
	return () => subscribers.delete(fn);
}
