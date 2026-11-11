// The article arrives already rendered: title, bilingual text and vocabulary
// are in the HTML for search engines and share previews.
import { backendJson } from '$lib/server/backend';
import type { ArticleData } from '$lib/api';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ params }) => {
	const article = await backendJson<ArticleData>(`/api/public/videos/${encodeURIComponent(params.id)}/article`);
	return { article };
};
