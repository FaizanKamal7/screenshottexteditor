import { defineMiddleware } from 'astro:middleware';

// Google was crawling and indexing https://screenshottexteditor.com, https://www...,
// http://screenshottexteditor.com, and http://www... as four separate URLs for the same
// content (GSC: "Alternate page with proper canonical tag"), splitting crawl priority
// across duplicates instead of the canonical apex/https URL.
const CANONICAL_HOST = 'screenshottexteditor.com';

export const onRequest = defineMiddleware((context, next) => {
	const { url, request } = context;
	const hostname = url.hostname;

	// Only touch the production domain — leaves localhost and *.pages.dev previews alone.
	if (hostname !== CANONICAL_HOST && hostname !== `www.${CANONICAL_HOST}`) {
		return next();
	}

	const protocol = request.headers.get('x-forwarded-proto') ?? url.protocol.replace(':', '');

	if (hostname !== CANONICAL_HOST || protocol !== 'https') {
		const target = new URL(url);
		target.protocol = 'https:';
		target.hostname = CANONICAL_HOST;
		return context.redirect(target.toString(), 301);
	}

	return next();
});
