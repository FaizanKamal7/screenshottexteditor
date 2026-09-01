export const prerender = true;

import type { APIRoute } from 'astro';
import { getCollection } from 'astro:content';

const SITE_URL = 'https://screenshottexteditor.com';

const staticPages = [
	{ path: '/', changefreq: 'weekly', priority: '1.0' },
	{ path: '/app', changefreq: 'weekly', priority: '0.9' },
	{ path: '/pricing', changefreq: 'monthly', priority: '0.8' },
	{ path: '/about', changefreq: 'monthly', priority: '0.5' },
	{ path: '/contact', changefreq: 'monthly', priority: '0.4' },
	{ path: '/privacy', changefreq: 'yearly', priority: '0.2' },
	{ path: '/terms', changefreq: 'yearly', priority: '0.2' },
];

export const GET: APIRoute = async () => {
	const useCases = await getCollection('useCases');

	const urls = [
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
