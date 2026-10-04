/**
 * Auth wrapper for LetMeUse SDK.
 * SDK is loaded via static <script> tag in app.html.
 * This module provides reactive helpers around window.letmeuse.
 */

export interface AuthUser {
	id: string;
	email: string;
	displayName: string;
	avatar?: string;
	role: string;
	appId: string;
}

interface LetMeUseSDK {
	ready: boolean;
	user: AuthUser | null;
	login(): void;
	register(): void;
	logout(): Promise<void>;
	getToken(): string | null;
	onAuthChange(cb: (user: AuthUser | null) => void): () => void;
	openAdmin(): void;
	openProfile?(): void;
}

declare global {
	interface Window {
		letmeuse?: LetMeUseSDK;
	}
}

let currentUser: AuthUser | null = null;
let sdkReady = false;
const subscribers: Set<(user: AuthUser | null) => void> = new Set();

function notify() {
	for (const fn of subscribers) {
		try {
			fn(currentUser);
		} catch {
			// ignore subscriber errors
		}
	}
}

/** Connect to LetMeUse SDK (already loaded via app.html script tag). */
export function initAuth(): void {
	if (typeof window === 'undefined') return;

	function tryConnect() {
		if (!window.letmeuse) return false;
		sdkReady = true;
		window.letmeuse.onAuthChange((user) => {
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
export function onAuthChange(cb: (user: AuthUser | null) => void): () => void {
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
export function getUser(): AuthUser | null {
	if (typeof window === 'undefined') return null;
	return window.letmeuse?.user ?? currentUser;
}

/** Get current JWT token. */
export function getToken(): string | null {
	if (typeof window === 'undefined') return null;
	return window.letmeuse?.getToken() ?? null;
}

/**
 * Resolve once the SDK has finished init — including the silent refresh that
 * swaps the (4h) access token for a fresh one via the (30d) refresh token.
 * Falls through after a timeout so the app still works if the SDK never loads.
 */
export function whenAuthReady(timeoutMs = 8000): Promise<void> {
	if (typeof window === 'undefined') return Promise.resolve();
	if (window.letmeuse?.ready) return Promise.resolve();
	return new Promise((resolve) => {
		const started = Date.now();
		const check = setInterval(() => {
			if (window.letmeuse?.ready || Date.now() - started > timeoutMs) {
				clearInterval(check);
				resolve();
			}
		}, 50);
	});
}

/**
 * Token that's safe to put on the wire: waits out the SDK's silent refresh so
 * we never send yesterday's expired JWT. Sending the stale one is what made
 * every return visit 401 and flash「請先登入」at people who WERE logged in.
 */
export async function getFreshToken(): Promise<string | null> {
	await whenAuthReady();
	return getToken();
}

/** Check if user is admin. */
export function isAdmin(): boolean {
	const user = getUser();
	return user?.role === 'admin';
}

/** Open login modal. */
export function login(): void {
	window.letmeuse?.login();
}

/** Open register modal. */
export function register(): void {
	window.letmeuse?.register();
}

/** Logout. */
export async function logout(): Promise<void> {
	await window.letmeuse?.logout();
}

/** Open profile/account settings. */
export function openProfile(): void {
	window.letmeuse?.openProfile?.();
}
