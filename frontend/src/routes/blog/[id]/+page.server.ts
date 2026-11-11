// The article arrives already rendered: title, bilingual text and vocabulary
// are in the HTML for search engines and share previews.
import { error } from '@sveltejs/kit';
import { backendResult } from '$lib/server/backend';
import type { ArticleData } from '$lib/api';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ params }) => {
	const { status, data } = await backendResult<ArticleData>(
		`/api/public/videos/${encodeURIComponent(params.id)}/article`
	);
	// Gone or private: say so, instead of a 200 page search engines would index empty.
	if (status === 404) error(404, 'Not found');
	// Backend unreachable or slow: the page loads the article in the browser instead.
	return { article: data };
};
