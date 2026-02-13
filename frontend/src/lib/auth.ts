/**
 * Auth wrapper for adman SDK.
 * SDK is loaded via static <script> tag in app.html.
 * This module provides reactive helpers around window.adman.
 */

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

/** Connect to adman SDK (already loaded via app.html script tag). */
export function initAuth(): void {
	if (typeof window === 'undefined') return;

	function tryConnect() {
		if (!window.adman) return false;
		sdkReady = true;
		window.adman.onAuthChange((user) => {
			currentUser = user;
			notify();
		});
		return true;
	}

	// SDK might already be loaded
	if (tryConnect()) return;

	// Otherwise wait for it
	const check = setInterval(() => {
		if (tryConnect()) clearInterval(check);
	}, 100);

	// Stop checking after 5s
	setTimeout(() => clearInterval(check), 5000);
}

/** Subscribe to auth state changes. Returns unsubscribe function. */
export function onAuthChange(cb: (user: AdmanUser | null) => void): () => void {
	subscribers.add(cb);
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
