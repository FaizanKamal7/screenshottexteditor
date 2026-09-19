import { defineMiddleware } from 'astro:middleware';

// Google was crawling and indexing https://screenshottexteditor.com, https://www...,
// http://screenshottexteditor.com, and http://www... as four separate URLs for the same
// content (GSC: "Alternate page with proper canonical tag"), splitting crawl priority
// across duplicates instead of the canonical apex/https URL.
const CANONICAL_HOST = 'screenshottexteditor.com';

// HSTS is only honoured by browsers when received over HTTPS, so it is skipped on the
// http:// -> https:// redirect. No includeSubDomains/preload: other subdomains may not be
// HTTPS-only, and preload is effectively irreversible.
const HSTS = 'max-age=31536000';

const withHsts = (response: Response) => {
	response.headers.set('Strict-Transport-Security', HSTS);
	return response;
};

export const onRequest = defineMiddleware(async (context, next) => {
	const { url, request } = context;
	const hostname = url.hostname;

	// Only touch the production domain — leaves localhost and *.pages.dev previews alone.
	if (hostname !== CANONICAL_HOST && hostname !== `www.${CANONICAL_HOST}`) {
		return next();
	}

	const protocol = request.headers.get('x-forwarded-proto') ?? url.protocol.replace(':', '');
	const isHttps = protocol === 'https';

	if (hostname !== CANONICAL_HOST || !isHttps) {
		const target = new URL(url);
		target.protocol = 'https:';
		target.hostname = CANONICAL_HOST;
		const redirect = context.redirect(target.toString(), 301);
		return isHttps ? withHsts(redirect) : redirect;
	}

	return withHsts(await next());
});
