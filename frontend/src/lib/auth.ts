/**
 * Auth wrapper for adman SDK.
 * Dynamically loads the SDK and provides reactive user state.
 */

const ADMAN_URL = 'https://adman.isnowfriend.com';
const APP_ID = 'app_yX0u0SiJ';

interface AdmanUser {
	id: string;
	email: string;
	displayName: string;
	role: 'user' | 'admin';
}

interface AdmanSDK {
	ready: boolean;
	user: AdmanUser | null;
	login(): void;
	register(): void;
	logout(): Promise<void>;
	getToken(): string | null;
	onAuthChange(cb: (user: AdmanUser | null) => void): () => void;
	openAdmin(): void;
}

declare global {
	interface Window {
		adman?: AdmanSDK;
	}
}

let currentUser: AdmanUser | null = null;
let sdkReady = false;
const subscribers: Set<(user: AdmanUser | null) => void> = new Set();

function notify() {
	for (const fn of subscribers) {
		try {
			fn(currentUser);
		} catch {
			// ignore subscriber errors
		}
	}
}

/** Load adman SDK script and set up auth change listener. */
export function initAuth(): void {
	if (typeof document === 'undefined') return;
	if (document.getElementById('adman-sdk')) return;

	const script = document.createElement('script');
	script.id = 'adman-sdk';
	script.src = `${ADMAN_URL}/sdk.js`;
	script.setAttribute('data-app-id', APP_ID);
	script.setAttribute('data-theme', document.documentElement.getAttribute('data-theme') || 'dark');
	script.setAttribute('data-accent', '#6366f1');
	script.setAttribute('data-locale', localStorage.getItem('reelscript-locale') || 'zh');
	script.setAttribute('data-mode', 'modal');

	script.onload = () => {
		if (!window.adman) return;
		sdkReady = true;
		window.adman.onAuthChange((user) => {
			currentUser = user;
			notify();
		});
	};

	document.head.appendChild(script);
}

/** Subscribe to auth state changes. Returns unsubscribe function. */
export function onAuthChange(cb: (user: AdmanUser | null) => void): () => void {
	subscribers.add(cb);
	// Immediately call with current state if SDK is ready
	if (sdkReady) {
		try {
			cb(currentUser);
		} catch {
			// ignore
		}
	}
	return () => {
		subscribers.delete(cb);
	};
}

/** Get current user (snapshot). */
export function getUser(): AdmanUser | null {
	return window.adman?.user ?? currentUser;
}

/** Get current JWT token. */
export function getToken(): string | null {
	return window.adman?.getToken() ?? null;
}

/** Check if user is admin. */
export function isAdmin(): boolean {
	const user = getUser();
	return user?.role === 'admin';
}

/** Open login modal. */
export function login(): void {
	window.adman?.login();
}

/** Open register modal. */
export function register(): void {
	window.adman?.register();
}

/** Logout. */
export async function logout(): Promise<void> {
	await window.adman?.logout();
}

export type { AdmanUser };
