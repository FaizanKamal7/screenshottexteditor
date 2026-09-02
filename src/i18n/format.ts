/** Languages that don't use spaces between words, so auto-inserted joiner spaces must be suppressed. */
export function isCjk(lang: string): boolean {
	return lang === 'ja' || lang === 'zh';
}

const NO_SPACE_BEFORE = /^[.,;:!?)\]}»"'、。，！？」』]/;

/** Space to insert before `text` when splicing translated sentence fragments around an inline link. */
export function spaceBefore(text: string, lang: string): string {
	if (isCjk(lang) || !text) return '';
	return NO_SPACE_BEFORE.test(text) ? '' : ' ';
}

/** Space to insert before an inline link that follows `pre`. */
export function spaceAfter(lang: string): string {
	return isCjk(lang) ? '' : ' ';
}
