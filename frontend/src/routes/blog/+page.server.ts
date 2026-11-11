// The article list arrives already rendered, so search engines see every link.
import { allPublicVideos } from '$lib/server/public-videos';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async () => {
	const videos = await allPublicVideos();
	return { videos: videos ? videos.filter((v) => v.hasTranscript) : null };
};
