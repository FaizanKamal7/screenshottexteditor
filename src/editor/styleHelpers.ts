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
