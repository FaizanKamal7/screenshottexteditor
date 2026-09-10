import type { BackgroundFill, RgbColor } from './store';

// Maps stage-3's matched family (always one of the licensed substitutes in
// fonts/registry.py, per docs/fonts.md) to a CSS stack for client-side
// previews. The web app doesn't self-host these yet, so unrecognized
// families and Liberation Sans (no free CDN webfont) fall back to a
// metrically-similar system font rather than silently rendering as serif.
export function fontFamilyCss(family: string | null): string {
	switch (family) {
		case 'Inter':
			return "'Inter', system-ui, sans-serif";
		case 'Roboto':
			return "'Roboto', system-ui, sans-serif";
		case 'Noto Sans':
			return "'Noto Sans', system-ui, sans-serif";
		case 'Liberation Sans':
			return 'Arial, Helvetica, sans-serif';
		default:
			return 'system-ui, sans-serif';
	}
}

// Measures how wide `text` renders at the given style, using a throwaway DOM
// span carrying the exact same font styling — the same reasoning as
// Canvas.tsx's mirrored-span technique (canvas measureText can under-measure
// a variable web font at a given weight). Used to size split-region
// fragments, where each fragment needs its own one-off measurement rather
// than a single persistent mirrored span.
export function measureTextWidthPx(
	text: string,
	style: { fontFamily: string | null; fontWeight: number | null; fontSize: number | null; letterSpacing: number },
): number {
	if (typeof document === 'undefined') return 0;
	const span = document.createElement('span');
	span.style.position = 'fixed';
	span.style.top = '-9999px';
	span.style.left = '-9999px';
	span.style.visibility = 'hidden';
	span.style.whiteSpace = 'pre';
	span.style.pointerEvents = 'none';
	span.style.fontFamily = fontFamilyCss(style.fontFamily);
	span.style.fontSize = `${style.fontSize ?? 16}px`;
	span.style.fontWeight = String(style.fontWeight ?? 400);
	span.style.letterSpacing = `${style.letterSpacing}px`;
	span.textContent = text || ' ';
	document.body.appendChild(span);
	const width = span.getBoundingClientRect().width;
	document.body.removeChild(span);
	return width;
}

export function backgroundCss(background: BackgroundFill | null): string {
	if (!background) return 'transparent';
	if (background.kind === 'flat' && background.color) {
		return `rgb(${background.color.join(',')})`;
	}
	if (background.kind === 'gradient' && background.stops.length >= 2) {
		const sorted = [...background.stops].sort((a, b) => a.position - b.position);
		const stopsCss = sorted.map((stop) => `rgb(${stop.color.join(',')}) ${stop.position * 100}%`).join(', ');
		return `linear-gradient(${background.angleDeg ?? 0}deg, ${stopsCss})`;
	}
	return 'transparent';
}

export function rgbToHex([r, g, b]: RgbColor): string {
	const toHex = (n: number) => Math.max(0, Math.min(255, Math.round(n))).toString(16).padStart(2, '0');
	return `#${toHex(r)}${toHex(g)}${toHex(b)}`;
}

export function hexToRgb(hex: string): RgbColor {
	const normalized = hex.replace('#', '');
	const r = parseInt(normalized.slice(0, 2), 16);
	const g = parseInt(normalized.slice(2, 4), 16);
	const b = parseInt(normalized.slice(4, 6), 16);
	return [r || 0, g || 0, b || 0];
}

// Per the brief's confidence UI: nothing shown above 0.95, a quiet dot
// 0.85-0.95, a visible warning below 0.85. Shared by Canvas (canvas dots)
// and LayersPanel (sidebar list rows).
export type ConfidenceLevel = 'none' | 'quiet' | 'warning';

export function confidenceLevel(confidence: number | null): ConfidenceLevel {
	if (confidence == null || confidence >= 0.95) return 'none';
	if (confidence >= 0.85) return 'quiet';
	return 'warning';
}

// A second, distinct signal from `confidence` (match *quality* — how good
// the pixel match is in absolute terms): the score gap between the winning
// candidate and the runner-up, i.e. "how sure are we it's this font and not
// the next-best alternative." A region can have high match quality and low
// certainty (two very similar open-license substitutes both fit well) or
// the reverse (a mediocre but clearly-best match). Thresholds are starting
// values, not measured against real usage data yet — see the font-matching
// accuracy plan's benchmarking step for where real numbers would come from.
export type MatchCertainty = 'n/a' | 'clear' | 'close call' | 'ambiguous';

export function matchCertaintyLabel(margin: number | null): MatchCertainty {
	if (margin == null) return 'n/a';
	if (margin >= 0.05) return 'clear';
	if (margin >= 0.02) return 'close call';
	return 'ambiguous';
}
