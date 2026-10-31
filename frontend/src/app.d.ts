// See https://svelte.dev/docs/kit/types#app.d.ts
// for information about these interfaces
declare global {
	namespace App {
		// interface Error {}
		// interface Locals {}
		// interface PageData {}
		// interface PageState {}
		// interface Platform {}
	}

	// onboarding-kit vanilla build, loaded via /vendor/onboard.js in app.html
	interface Window {
		OnboardTour?: {
			start(
				steps: Array<{ sel?: string; title: string; body: string }>,
				opts?: {
					labels?: { next?: string; prev?: string; skip?: string; done?: string };
					onComplete?: () => void;
					onClose?: () => void;
					accent?: string;
				}
			): void;
			stop(): void;
		};
	}
}

export {};
