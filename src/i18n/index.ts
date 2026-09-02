import { en } from './translations/en';
import { es } from './translations/es';
import { fr } from './translations/fr';
import { de } from './translations/de';
import { pt } from './translations/pt';
import { it } from './translations/it';
import { ja } from './translations/ja';
import { zh } from './translations/zh';
import type { Translations } from './types';
import { defaultLocale, isValidLocale, type LocaleCode } from './languages';

const dictionaries: Record<LocaleCode, Translations> = { en, es, fr, de, pt, it, ja, zh };

export function getTranslations(locale: string | undefined): Translations {
	if (isValidLocale(locale)) return dictionaries[locale];
	return dictionaries[defaultLocale];
}

export * from './languages';
export type * from './types';
