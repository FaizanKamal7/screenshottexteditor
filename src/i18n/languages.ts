export interface Language {
	code: string;
	label: string;
	nativeLabel: string;
	flag: string;
}

export const languages: Language[] = [
	{ code: 'en', label: 'English', nativeLabel: 'English', flag: '🇺🇸' },
	{ code: 'es', label: 'Spanish', nativeLabel: 'Español', flag: '🇪🇸' },
	{ code: 'fr', label: 'French', nativeLabel: 'Français', flag: '🇫🇷' },
	{ code: 'de', label: 'German', nativeLabel: 'Deutsch', flag: '🇩🇪' },
	{ code: 'pt', label: 'Portuguese', nativeLabel: 'Português', flag: '🇵🇹' },
	{ code: 'it', label: 'Italian', nativeLabel: 'Italiano', flag: '🇮🇹' },
	{ code: 'ja', label: 'Japanese', nativeLabel: '日本語', flag: '🇯🇵' },
	{ code: 'zh', label: 'Chinese', nativeLabel: '中文', flag: '🇨🇳' },
];

export const defaultLocale = 'en';

export type LocaleCode = (typeof languages)[number]['code'];

export const localeCodes = languages.map((l) => l.code);

/** Route keys that have a translated page in every supported locale. Everything else (legal pages, use-case articles, the editor app) only exists in English. */
export type TranslatableRouteKey = '' | 'about' | 'contact';

export const translatableRouteKeys: TranslatableRouteKey[] = ['', 'about', 'contact'];

export function isValidLocale(code: string | undefined): code is LocaleCode {
	return !!code && localeCodes.includes(code);
}

/** Paths carry a trailing slash: the static pages are served as directories, and the slashless form 307-redirects to it (which breaks hreflang, per SEO audits). */
export function localizedPath(locale: string, routeKey: TranslatableRouteKey): string {
	const base = locale === defaultLocale ? '' : `/${locale}`;
	if (routeKey === '') return `${base}/`;
	return `${base}/${routeKey}/`;
}

const siteOrigin = 'https://screenshottexteditor.com';

export function getAlternateLinks(routeKey: TranslatableRouteKey): { hreflang: string; href: string }[] {
	const links = languages.map((l) => ({
		hreflang: l.code,
		href: `${siteOrigin}${localizedPath(l.code, routeKey)}`,
	}));
	links.push({ hreflang: 'x-default', href: `${siteOrigin}${localizedPath(defaultLocale, routeKey)}` });
	return links;
}
