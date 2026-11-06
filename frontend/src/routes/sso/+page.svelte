<script lang="ts">
	// 從姊妹站帶著登入狀態過來的落地頁。
	// 網址長這樣:/sso#code=<一次性通行碼>&next=/某一頁
	// 拿通行碼跟 LetMeUse 換成本站的登入憑證,存好之後導到 next。
	// 換不到(過期、用過)就直接去 next,使用者再自己登入即可。
	import { onMount } from 'svelte';

	onMount(async () => {
		const params = new URLSearchParams(location.hash.slice(1));
		const code = params.get('code') || '';
		const wanted = params.get('next') || '/';
		// 只接受站內路徑,不然這一頁會變成任意轉址的跳板
		const next = wanted.startsWith('/') && !wanted.startsWith('//') ? wanted : '/';
		// 通行碼不要留在網址列和瀏覽紀錄裡
		history.replaceState(null, '', location.pathname);

		// 登入元件的位置與本站的 app 代號,都從 app.html 掛的那支 script 讀
		const sdkTag = document.querySelector<HTMLScriptElement>('script[data-app-id]');
		const appId = sdkTag?.dataset.appId || '';
		if (code && sdkTag && appId) {
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
					localStorage.setItem(`lmu_${appId}_access_token`, data.accessToken);
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
