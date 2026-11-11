// Switching mode = changing ?mode= on the same watch URL. Shared by the navbar
// (desktop) and the in-page switcher (phones) so both behave identically.
import { goto } from '$app/navigation';
import type { ModeId } from '$lib/modes/text';

export const WATCH_ROUTE = '/watch/[id]';

export function switchMode(current: URL, next: ModeId): Promise<void> {
	const url = new URL(current);
	if (next === 'video') url.searchParams.delete('mode');
	else url.searchParams.set('mode', next);
	return goto(url, { replaceState: true, noScroll: true, keepFocus: true });
}
