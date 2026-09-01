import { useEffect, useState } from 'react';
import { useEditorStore, type RgbColor } from './store';
import { backgroundCss, fontFamilyCss, hexToRgb, rgbToHex } from './styleHelpers';

const WEIGHT_OPTIONS = [400, 500, 600, 700];
const ZOOM = 3;

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

	useEffect(() => {
		if (!region) return;
		setFamily(region.fontFamily ?? 'Inter');
		setWeight(region.fontWeight ?? 400);
		setSize(region.fontSize ?? 16);
		setLetterSpacing(region.letterSpacing);
		setColor(region.textColor ?? [0, 0, 0]);
	}, [regionId]);

	if (!region || !imageUrl) return null;

	const [bx, by, bw, bh] = region.bbox;
	const isDirty =
		family !== (region.fontFamily ?? 'Inter') ||
		weight !== (region.fontWeight ?? 400) ||
		size !== (region.fontSize ?? 16) ||
		letterSpacing !== region.letterSpacing ||
		color.join(',') !== (region.textColor ?? [0, 0, 0]).join(',');

	return (
		<div className="flex h-full w-full flex-col gap-3 overflow-y-auto p-3">
			<div className="flex items-center justify-between">
				<p className="text-sm text-ink">Font match</p>
				<button type="button" onClick={closeOverridePanel} className="text-faint text-xs hover:text-ink">
					Close
				</button>
			</div>

			<p className="truncate text-xs text-body" title={region.text}>
				"{region.text}"
			</p>
			<p className="text-faint text-xs">confidence: {region.confidence != null ? region.confidence.toFixed(2) : 'n/a'}</p>

			<div className="flex gap-2">
				<div
					className="border border-hairline"
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
					className="flex items-center overflow-hidden border border-hairline px-1"
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
							className={`flex items-center justify-between rounded-sm border px-2 py-1 text-xs ${
								family === candidate.family && weight === candidate.weight
									? 'border-link bg-link/10 text-ink'
									: 'border-hairline text-body hover:bg-hairline-soft/60'
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

			<label className="flex flex-col gap-1 text-xs text-faint">
				Size (px)
				<input
					type="number"
					value={size}
					min={4}
					step={0.5}
					onChange={(e) => setSize(Number(e.target.value))}
					className="rounded-sm border border-hairline bg-canvas px-2 py-1 text-ink"
				/>
			</label>

			<label className="flex flex-col gap-1 text-xs text-faint">
				Weight
				<select
					value={weight}
					onChange={(e) => setWeight(Number(e.target.value))}
					className="rounded-sm border border-hairline bg-canvas px-2 py-1 text-ink"
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
					className="rounded-sm border border-hairline bg-canvas px-2 py-1 text-ink"
				/>
			</label>

			<label className="flex flex-col gap-1 text-xs text-faint">
				Text color
				<input
					type="color"
					value={rgbToHex(color)}
					onChange={(e) => setColor(hexToRgb(e.target.value))}
					className="h-8 w-full rounded-sm border border-hairline bg-canvas"
				/>
			</label>

			<button
				type="button"
				disabled={!isDirty || isRendering}
				onClick={() => applyOverride(region.id, { fontFamily: family, fontWeight: weight, fontSize: size, letterSpacing, textColor: color })}
				className="rounded-sm border border-link bg-link/10 px-2 py-1.5 text-xs text-link disabled:cursor-not-allowed disabled:opacity-40"
			>
				{isRendering ? 'Applying…' : 'Apply'}
			</button>
		</div>
	);
}
