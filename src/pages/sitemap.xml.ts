export const prerender = true;

import type { APIRoute } from 'astro';
import { getCollection } from 'astro:content';
import { getAlternateLinks, languages, localizedPath, translatableRouteKeys } from '../i18n';

const SITE_URL = 'https://screenshottexteditor.com';

// Bump a page's lastmod (YYYY-MM-DD) when its content meaningfully changes. Google only trusts
// lastmod if it is accurate, so don't set it to the build date.
// Use-case pages take theirs from the `updated` frontmatter field instead.

// Prerendered pages are served as directories, so the slashless form 307-redirects to the
// trailing-slash URL. Sitemap entries must be the final 200 URL, hence the trailing slashes.
// /app is server-rendered and returns 200 either way.
const staticPages = [
	{ path: '/app', changefreq: 'weekly', priority: '0.9', lastmod: '2026-09-19' },
	{ path: '/privacy/', changefreq: 'yearly', priority: '0.2', lastmod: '2026-09-19' },
	{ path: '/terms/', changefreq: 'yearly', priority: '0.2', lastmod: '2026-09-19' },
];

const routeKeyPriority: Record<(typeof translatableRouteKeys)[number], string> = {
	'': '1.0',
	about: '0.5',
	contact: '0.4',
};

const routeKeyLastmod: Record<(typeof translatableRouteKeys)[number], string> = {
	'': '2026-09-19',
	about: '2026-09-19',
	contact: '2026-09-19',
};

type Entry = {
	path: string;
	lastmod: string;
	changefreq: string;
	priority: string;
	alternates?: { hreflang: string; href: string }[];
};

const renderEntry = ({ path, lastmod, changefreq, priority, alternates = [] }: Entry) => `
	<url>
		<loc>${SITE_URL}${path}</loc>
		<lastmod>${lastmod}</lastmod>
		<changefreq>${changefreq}</changefreq>
		<priority>${priority}</priority>${alternates
			.map((a) => `
		<xhtml:link rel="alternate" hreflang="${a.hreflang}" href="${a.href}" />`)
			.join('')}
	</url>`;

export const GET: APIRoute = async () => {
	const useCases = await getCollection('useCases');

	// Every locale's URL lists the full alternate set (including itself and x-default), as Google requires.
	const localizedEntries: Entry[] = translatableRouteKeys.flatMap((routeKey) =>
		languages.map((l) => ({
			path: localizedPath(l.code, routeKey),
			lastmod: routeKeyLastmod[routeKey],
			changefreq: routeKey === '' ? 'weekly' : 'monthly',
			priority: routeKeyPriority[routeKey],
			alternates: getAlternateLinks(routeKey),
		}))
	);

	const useCaseEntries: Entry[] = useCases.map((useCase) => ({
		path: `/${useCase.id}/`,
		lastmod: useCase.data.updated.toISOString().slice(0, 10),
		changefreq: 'monthly',
		priority: '0.7',
	}));

	const urls = [...localizedEntries, ...staticPages, ...useCaseEntries].map(renderEntry).join('');

	const xml = `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">${urls}
</urlset>`;

	return new Response(xml, {
		headers: {
			'Content-Type': 'application/xml',
		},
	});
};
