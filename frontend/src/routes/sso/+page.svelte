<script lang="ts">
	// 從姊妹站帶著登入狀態過來的落地頁。
	// 網址長這樣:/sso#code=<一次性通行碼>&next=/某一頁
	// 拿通行碼跟 LetMeUse 換成本站的登入憑證,存好之後導到 next。
	// 換不到(過期、用過)就直接去 next,使用者再自己登入即可。
	import { onMount } from 'svelte';

	// 只有從這些站點過來的通行碼才收。瀏覽器送的 Referer 別人偽造不了,
	// 所以外人沒辦法做一條「點了就被登入成他的帳號」的連結。
	const TRUSTED_SOURCES = ['https://phrase.pipee.tw'];

	// 只接受站內路徑。用 URL 解析後比對 origin:
	// 光看開頭是不是 "/" 擋不住 "/\evil.com" 或夾了 Tab 的寫法。
	function safeNext(wanted: string): string {
		try {
			const url = new URL(wanted, location.origin);
			return url.origin === location.origin ? url.pathname + url.search + url.hash : '/';
		} catch {
			return '/';
		}
	}

	function cameFromTrustedSite(): boolean {
		try {
			return TRUSTED_SOURCES.includes(new URL(document.referrer).origin);
		} catch {
			return false;
		}
	}

	onMount(async () => {
		const params = new URLSearchParams(location.hash.slice(1));
		const code = params.get('code') || '';
		const next = safeNext(params.get('next') || '/');
		// 通行碼不要留在網址列和瀏覽紀錄裡
		history.replaceState(null, '', location.pathname);

		// 登入元件的位置與本站的 app 代號,都從 app.html 掛的那支 script 讀
		const sdkTag = document.querySelector<HTMLScriptElement>('script[data-app-id]');
		const appId = sdkTag?.dataset.appId || '';
		const accessKey = `lmu_${appId}_access_token`;
		// 已經登入的人不換帳號:不然一條連結就能把別人的登入蓋掉
		const alreadySignedIn = Boolean(appId && localStorage.getItem(accessKey));

		if (code && sdkTag && appId && !alreadySignedIn && cameFromTrustedSite()) {
			try {
				const base = new URL(sdkTag.src).origin;
				const res = await fetch(`${base}/api/auth/sso/redeem`, {
					method: 'POST',
					headers: { 'Content-Type': 'application/json' },
					body: JSON.stringify({ code, appId })
				});
				const json = await res.json();
				const data = json.data || json;
				if (res.ok && typeof data.accessToken === 'string') {
					localStorage.setItem(accessKey, data.accessToken);
					if (typeof data.refreshToken === 'string') {
						localStorage.setItem(`lmu_${appId}_refresh_token`, data.refreshToken);
					}
				}
			} catch {
				// 換失敗就當沒登入
			}
		}
		// 整頁重新載入,登入元件才會讀到剛存的憑證
		location.replace(next);
	});
</script>

<svelte:head>
	<title>登入中… | ReelScript</title>
	<meta name="robots" content="noindex" />
</svelte:head>

<p style="padding: 48px 24px; text-align: center; opacity: 0.7;">登入中…</p>
