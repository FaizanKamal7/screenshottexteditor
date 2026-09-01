import { useEffect, useRef, useState } from 'react';
import { useEditorStore, type RgbColor } from './store';
import { backgroundCss, fontFamilyCss, hexToRgb, rgbToHex } from './styleHelpers';

const WEIGHT_OPTIONS = [400, 500, 600, 700];
const ZOOM = 3;

// How long to wait after the user stops adjusting a value before firing the
// actual /render round trip. The Skia render itself is cheap; the round trip
// re-uploads/downloads the whole image, so firing on every keystroke would
// mean a multi-MB request per keystroke — this debounce is what makes
// "no Apply button" feel live without doing that.
const AUTO_APPLY_DEBOUNCE_MS = 450;

export function FontOverridePanel() {
	const regionId = useEditorStore((s) => s.overridePanelRegionId);
	const region = useEditorStore((s) => s.regions.find((r) => r.id === s.overridePanelRegionId));
	const imageUrl = useEditorStore((s) => s.imageUrl);
	const imageWidth = useEditorStore((s) => s.imageWidth);
	const imageHeight = useEditorStore((s) => s.imageHeight);
	const isRendering = useEditorStore((s) => s.isRendering);
	const closeOverridePanel = useEditorStore((s) => s.closeOverridePanel);
	const applyOverride = useEditorStore((s) => s.applyOverride);

	const [family, setFamily] = useState('Inter');
	const [weight, setWeight] = useState(400);
	const [size, setSize] = useState(16);
	const [letterSpacing, setLetterSpacing] = useState(0);
	const [color, setColor] = useState<RgbColor>([0, 0, 0]);
	const [alignment, setAlignment] = useState<'left' | 'center' | 'right'>('left');

	// Set synchronously by the sync-from-region effect below, and read+cleared
	// by the auto-apply effect in the same commit — not timing-dependent —
	// so switching regions never schedules a stray render call using the
	// outgoing region's stale local state against the newly selected region.
	const skipNextAutoApplyRef = useRef(false);

	useEffect(() => {
		if (!region) return;
		skipNextAutoApplyRef.current = true;
		setFamily(region.fontFamily ?? 'Inter');
		setWeight(region.fontWeight ?? 400);
		setSize(region.fontSize ?? 16);
		setLetterSpacing(region.letterSpacing);
		setColor(region.textColor ?? [0, 0, 0]);
		setAlignment(region.alignment);
	}, [regionId]);

	useEffect(() => {
		if (skipNextAutoApplyRef.current) {
			skipNextAutoApplyRef.current = false;
			return;
		}
		if (!region) return;

		const isDirty =
			family !== (region.fontFamily ?? 'Inter') ||
			weight !== (region.fontWeight ?? 400) ||
			size !== (region.fontSize ?? 16) ||
			letterSpacing !== region.letterSpacing ||
			color.join(',') !== (region.textColor ?? [0, 0, 0]).join(',') ||
			alignment !== region.alignment;
		if (!isDirty) return;

		const timeout = setTimeout(() => {
			applyOverride(region.id, { fontFamily: family, fontWeight: weight, fontSize: size, letterSpacing, textColor: color, alignment });
		}, AUTO_APPLY_DEBOUNCE_MS);
		return () => clearTimeout(timeout);
		// eslint-disable-next-line react-hooks/exhaustive-deps
	}, [family, weight, size, letterSpacing, color, alignment]);

	if (!region || !imageUrl) return null;

	const [bx, by, bw, bh] = region.bbox;

	return (
		<div className="flex flex-col gap-3 bg-hairline-soft/50 px-3.5 py-3.5">
			<div className="flex items-center justify-between">
				<p className="text-[13px] font-semibold tracking-tight text-ink">Style</p>
				<button
					type="button"
					onClick={closeOverridePanel}
					className="rounded-full px-2 py-0.5 text-[11px] text-faint transition-colors hover:bg-canvas-elevated hover:text-ink"
				>
					Collapse
				</button>
			</div>

			<p className="text-faint text-xs">confidence: {region.confidence != null ? region.confidence.toFixed(2) : 'n/a'}</p>

			<div className="flex gap-2 overflow-x-auto">
				<div
					className="shrink-0 rounded-md border border-hairline"
					style={{
						width: bw * ZOOM,
						height: bh * ZOOM,
						backgroundImage: `url(${imageUrl})`,
						backgroundSize: `${imageWidth * ZOOM}px ${imageHeight * ZOOM}px`,
						backgroundPosition: `-${bx * ZOOM}px -${by * ZOOM}px`,
					}}
					title="original"
				/>
				<div
					className="flex shrink-0 items-center overflow-hidden rounded-md border border-hairline bg-canvas-elevated px-1"
					style={{ width: bw * ZOOM, height: bh * ZOOM, background: backgroundCss(region.background) }}
					title="rendered preview (approximate — browser font rendering, not the actual Skia output)"
				>
					<span
						style={{
							fontFamily: fontFamilyCss(family),
							fontWeight: weight,
							fontSize: size * ZOOM,
							letterSpacing: letterSpacing * ZOOM,
							color: `rgb(${color.join(',')})`,
							whiteSpace: 'nowrap',
						}}
					>
						{region.text}
					</span>
				</div>
			</div>

			{region.fontCandidates.length > 0 && (
				<div className="flex flex-col gap-1">
					<p className="text-faint text-xs">Top candidates</p>
					{region.fontCandidates.map((candidate) => (
						<button
							key={`${candidate.family}-${candidate.weight}`}
							type="button"
							onClick={() => {
								setFamily(candidate.family);
								setWeight(candidate.weight);
							}}
							className={`flex items-center justify-between rounded-md border px-2 py-1 text-xs ${
								family === candidate.family && weight === candidate.weight
									? 'border-link bg-link/10 text-ink'
									: 'border-hairline bg-canvas-elevated text-body hover:bg-hairline-soft/60'
							}`}
						>
							<span>
								{candidate.family} {candidate.weight}
							</span>
							<span className="text-faint">{candidate.score.toFixed(2)}</span>
						</button>
					))}
				</div>
			)}

			<div className="flex flex-col gap-1 text-xs text-faint">
				Alignment
				<p className="text-[10px] font-normal normal-case text-faint">
					When replacement text needs more room, the box grows toward this side.
				</p>
				<div className="flex gap-1">
					{(['left', 'center', 'right'] as const).map((option) => (
						<button
							key={option}
							type="button"
							onClick={() => setAlignment(option)}
							className={`flex-1 rounded-md border px-2 py-1.5 text-[11px] capitalize transition-colors ${
								alignment === option
									? 'border-link bg-link/10 text-link'
									: 'border-hairline bg-canvas-elevated text-body hover:bg-hairline-soft/60'
							}`}
						>
							{option}
						</button>
					))}
				</div>
			</div>

			<label className="flex flex-col gap-1 text-xs text-faint">
				Size (px)
				<input
					type="number"
					value={size}
					min={4}
					step={0.5}
					onChange={(e) => setSize(Number(e.target.value))}
					className="rounded-md border border-hairline bg-canvas-elevated px-2 py-1.5 text-ink focus:border-link focus:outline-none"
				/>
			</label>

			<label className="flex flex-col gap-1 text-xs text-faint">
				Weight
				<select
					value={weight}
					onChange={(e) => setWeight(Number(e.target.value))}
					className="rounded-md border border-hairline bg-canvas-elevated px-2 py-1.5 text-ink focus:border-link focus:outline-none"
				>
					{WEIGHT_OPTIONS.map((w) => (
						<option key={w} value={w}>
							{w}
						</option>
					))}
				</select>
			</label>

			<label className="flex flex-col gap-1 text-xs text-faint">
				Letter spacing (px)
				<input
					type="number"
					value={letterSpacing}
					step={0.1}
					onChange={(e) => setLetterSpacing(Number(e.target.value))}
					className="rounded-md border border-hairline bg-canvas-elevated px-2 py-1.5 text-ink focus:border-link focus:outline-none"
				/>
			</label>

			<label className="flex flex-col gap-1 text-xs text-faint">
				Text color
				<input
					type="color"
					value={rgbToHex(color)}
					onChange={(e) => setColor(hexToRgb(e.target.value))}
					className="h-8 w-full rounded-md border border-hairline bg-canvas-elevated"
				/>
			</label>

			<p className="text-center text-[11px] text-faint">
				{isRendering ? 'Applying…' : 'Changes apply automatically'}
			</p>
		</div>
	);
}
