import { defineMiddleware } from 'astro:middleware';

// Google was crawling and indexing https://screenshottexteditor.com, https://www...,
// http://screenshottexteditor.com, and http://www... as four separate URLs for the same
// content (GSC: "Alternate page with proper canonical tag"), splitting crawl priority
// across duplicates instead of the canonical apex/https URL.
const CANONICAL_HOST = new URL(import.meta.env.SITE).hostname;

// /app is server-rendered, so Astro answers both /app and /app/ with a 200 and a self-referencing
// canonical. /app is the preferred URL (sitemap, internal links), so the slashed form redirects.
const APP_SLASHED = '/app/';

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

	// Host/protocol normalization only touches the production domain — leaves localhost and
	// *.pages.dev previews alone. The /app/ redirect applies everywhere.
	const isProductionHost = hostname === CANONICAL_HOST || hostname === `www.${CANONICAL_HOST}`;
	const protocol = request.headers.get('x-forwarded-proto') ?? url.protocol.replace(':', '');
	const isHttps = protocol === 'https';

	const needsHostRedirect = isProductionHost && (hostname !== CANONICAL_HOST || !isHttps);
	const needsAppRedirect = url.pathname === APP_SLASHED;

	// One combined 301, so http://www.../app/ doesn't become a redirect chain.
	if (needsHostRedirect || needsAppRedirect) {
		const target = new URL(url);
		if (isProductionHost) {
			target.protocol = 'https:';
			target.hostname = CANONICAL_HOST;
		}
		if (needsAppRedirect) target.pathname = '/app';
		const redirect = context.redirect(target.toString(), 301);
		return isProductionHost && isHttps ? withHsts(redirect) : redirect;
	}

	const response = await next();
	return isProductionHost ? withHsts(response) : response;
});
