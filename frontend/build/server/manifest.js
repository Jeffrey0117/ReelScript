const manifest = (() => {
function __memo(fn) {
	let value;
	return () => value ??= (value = fn());
}

return {
	appDir: "_app",
	appPath: "_app",
	assets: new Set(["icon-192.png","icon-512.png","manifest.json","robots.txt","service-worker.js"]),
	mimeTypes: {".png":"image/png",".json":"application/json",".txt":"text/plain"},
	_: {
		client: {start:"_app/immutable/entry/start.BM9NJPSx.js",app:"_app/immutable/entry/app.HZMyzAEd.js",imports:["_app/immutable/entry/start.BM9NJPSx.js","_app/immutable/chunks/CH-_L_Z7.js","_app/immutable/chunks/O07TP1T7.js","_app/immutable/chunks/BrOrVmbY.js","_app/immutable/entry/app.HZMyzAEd.js","_app/immutable/chunks/O07TP1T7.js","_app/immutable/chunks/ChRBLpLg.js","_app/immutable/chunks/rHWd91Rh.js","_app/immutable/chunks/-4EPxQNd.js","_app/immutable/chunks/6e_4cIT2.js","_app/immutable/chunks/BrOrVmbY.js"],stylesheets:[],fonts:[],uses_env_dynamic_public:false},
		nodes: [
			__memo(() => import('./chunks/0-CtRLeFUa.js')),
			__memo(() => import('./chunks/1-DQX0MSug.js')),
			__memo(() => import('./chunks/2-DaSyO3sn.js')),
			__memo(() => import('./chunks/3-BR1fLRf6.js')),
			__memo(() => import('./chunks/4-DKNR3kSt.js')),
			__memo(() => import('./chunks/5-MydIqR1v.js')),
			__memo(() => import('./chunks/6-i0Sqm23i.js')),
			__memo(() => import('./chunks/7-B8TyB9BW.js')),
			__memo(() => import('./chunks/8-C54Wjoe_.js')),
			__memo(() => import('./chunks/9-n8jc6-oi.js'))
		],
		remotes: {
			
		},
		routes: [
			{
				id: "/",
				pattern: /^\/$/,
				params: [],
				page: { layouts: [0,], errors: [1,], leaf: 2 },
				endpoint: null
			},
			{
				id: "/admin",
				pattern: /^\/admin\/?$/,
				params: [],
				page: { layouts: [0,], errors: [1,], leaf: 3 },
				endpoint: null
			},
			{
				id: "/blog",
				pattern: /^\/blog\/?$/,
				params: [],
				page: { layouts: [0,], errors: [1,], leaf: 4 },
				endpoint: null
			},
			{
				id: "/blog/[id]",
				pattern: /^\/blog\/([^/]+?)\/?$/,
				params: [{"name":"id","optional":false,"rest":false,"chained":false}],
				page: { layouts: [0,], errors: [1,], leaf: 5 },
				endpoint: null
			},
			{
				id: "/collections",
				pattern: /^\/collections\/?$/,
				params: [],
				page: { layouts: [0,], errors: [1,], leaf: 6 },
				endpoint: null
			},
			{
				id: "/ig",
				pattern: /^\/ig\/?$/,
				params: [],
				page: { layouts: [0,], errors: [1,], leaf: 7 },
				endpoint: null
			},
			{
				id: "/study/[id]",
				pattern: /^\/study\/([^/]+?)\/?$/,
				params: [{"name":"id","optional":false,"rest":false,"chained":false}],
				page: { layouts: [0,], errors: [1,], leaf: 8 },
				endpoint: null
			},
			{
				id: "/watch/[id]",
				pattern: /^\/watch\/([^/]+?)\/?$/,
				params: [{"name":"id","optional":false,"rest":false,"chained":false}],
				page: { layouts: [0,], errors: [1,], leaf: 9 },
				endpoint: null
			}
		],
		prerendered_routes: new Set([]),
		matchers: async () => {
			
			return {  };
		},
		server_assets: {}
	}
}
})();

const prerendered = new Set([]);

const base = "";

export { base, manifest, prerendered };
//# sourceMappingURL=manifest.js.map
