export const prerender = true;

import type { APIRoute } from 'astro';
import { getCollection } from 'astro:content';
import { languages, localizedPath, translatableRouteKeys } from '../i18n';

const SITE_URL = 'https://screenshottexteditor.com';

const staticPages = [
	{ path: '/app', changefreq: 'weekly', priority: '0.9' },
	{ path: '/privacy', changefreq: 'yearly', priority: '0.2' },
	{ path: '/terms', changefreq: 'yearly', priority: '0.2' },
];

const routeKeyPriority: Record<(typeof translatableRouteKeys)[number], string> = {
	'': '1.0',
	pricing: '0.8',
	about: '0.5',
	contact: '0.4',
};

export const GET: APIRoute = async () => {
	const useCases = await getCollection('useCases');

	const localizedUrls = translatableRouteKeys.flatMap((routeKey) =>
		languages.map((l) => ({
			path: localizedPath(l.code, routeKey),
			changefreq: routeKey === '' ? 'weekly' : 'monthly',
			priority: routeKeyPriority[routeKey],
		}))
	);

	const urls = [
		...localizedUrls.map(
			({ path, changefreq, priority }) => `
	<url>
		<loc>${SITE_URL}${path}</loc>
		<changefreq>${changefreq}</changefreq>
		<priority>${priority}</priority>
	</url>`
		),
		...staticPages.map(
			({ path, changefreq, priority }) => `
	<url>
		<loc>${SITE_URL}${path}</loc>
		<changefreq>${changefreq}</changefreq>
		<priority>${priority}</priority>
	</url>`
		),
		...useCases.map(
			(useCase) => `
	<url>
		<loc>${SITE_URL}/${useCase.id}</loc>
		<changefreq>monthly</changefreq>
		<priority>0.7</priority>
	</url>`
		),
	].join('');

	const xml = `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">${urls}
</urlset>`;

	return new Response(xml, {
		headers: {
			'Content-Type': 'application/xml',
		},
	});
};
