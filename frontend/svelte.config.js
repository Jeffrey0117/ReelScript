import adapter from '@sveltejs/adapter-node';

/** @type {import('@sveltejs/kit').Config} */
const config = {
	kit: {
		adapter: adapter({
			// BUILD_OUT lets `npm run preview` build beside the live build instead of over it.
			out: process.env.BUILD_OUT || 'build',
		}),
	},
};

export default config;
