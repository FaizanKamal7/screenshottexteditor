import { useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react';
import { useEditorStore, type Region } from './store';
import { backgroundCss, confidenceLevel, fontFamilyCss } from './styleHelpers';

export function readingOrder(regions: Region[]): Region[] {
	return [...regions].sort((a, b) => a.bbox[1] - b.bbox[1] || a.bbox[0] - b.bbox[0]);
}

// Breathing room, in CSS px, kept around the scaled image inside the pane.
const FIT_PADDING = 48;

interface CanvasProps {
	embedded?: boolean;
}

export function Canvas({ embedded = false }: CanvasProps) {
	const imageUrl = useEditorStore((s) => s.imageUrl);
	const imageWidth = useEditorStore((s) => s.imageWidth);
	const imageHeight = useEditorStore((s) => s.imageHeight);
	const regions = useEditorStore((s) => s.regions);
	const selectedRegionId = useEditorStore((s) => s.selectedRegionId);
	const editingRegionId = useEditorStore((s) => s.editingRegionId);
	const isRendering = useEditorStore((s) => s.isRendering);
	const renderError = useEditorStore((s) => s.renderError);
	const status = useEditorStore((s) => s.status);
	const startEditing = useEditorStore((s) => s.startEditing);
	const cancelEditing = useEditorStore((s) => s.cancelEditing);
	const commitEdit = useEditorStore((s) => s.commitEdit);
	const openOverridePanel = useEditorStore((s) => s.openOverridePanel);
	const debugMode = useEditorStore((s) => s.debugMode);

	const orderedRegions = useMemo(() => readingOrder(regions), [regions]);
	const editingRegion = regions.find((r) => r.id === editingRegionId) ?? null;
	const isAnalyzing = status === 'analyzing';

	const [draftText, setDraftText] = useState('');
	const inputRef = useRef<HTMLInputElement>(null);
	const paneRef = useRef<HTMLDivElement>(null);
	const [scale, setScale] = useState(1);

	useEffect(() => {
		if (editingRegion) {
			setDraftText(editingRegion.text);
		}
	}, [editingRegion?.id]);

	useEffect(() => {
		if (editingRegionId) {
			inputRef.current?.focus();
			inputRef.current?.select();
		}
	}, [editingRegionId]);

	// Zoom-to-fit: the image and every region overlay stay positioned in
	// native image-pixel coordinates (unchanged from the pipeline's output);
	// this just scales the whole layer to fill the available pane so a 3x
	// retina screenshot doesn't render at native size in a scrollbox.
	useLayoutEffect(() => {
		const pane = paneRef.current;
		if (!pane || !imageWidth || !imageHeight) return;

		const computeScale = () => {
			const availableWidth = pane.clientWidth - FIT_PADDING * 2;
			const availableHeight = pane.clientHeight - FIT_PADDING * 2;
			if (availableWidth <= 0 || availableHeight <= 0) return;
			const next = Math.min(availableWidth / imageWidth, availableHeight / imageHeight);
			setScale(next > 0 ? next : 1);
		};

		computeScale();
		const observer = new ResizeObserver(computeScale);
		observer.observe(pane);
		return () => observer.disconnect();
	}, [imageWidth, imageHeight]);

	if (!imageUrl) return null;

	const commitAndFocusNext = (direction: 1 | -1) => {
		if (!editingRegion) return;
		commitEdit(editingRegion.id, draftText);
		const index = orderedRegions.findIndex((r) => r.id === editingRegion.id);
		const next = orderedRegions[(index + direction + orderedRegions.length) % orderedRegions.length];
		if (next) startEditing(next.id);
	};

	return (
		<div ref={paneRef} className="relative flex h-full w-full items-center justify-center overflow-auto bg-canvas p-6">
			<div className="relative" style={{ width: imageWidth * scale, height: imageHeight * scale }}>
				<div
					className="absolute left-0 top-0"
					style={{ width: imageWidth, height: imageHeight, transform: `scale(${scale})`, transformOrigin: 'top left' }}
				>
					<img
						src={imageUrl}
						width={imageWidth}
						height={imageHeight}
						alt="Uploaded screenshot"
						className={`block shadow-sm transition-[filter,opacity] duration-300 ${isAnalyzing ? 'opacity-60 blur-[1px]' : ''}`}
					/>
					{regions.map((region) => {
						const [x, y, w, h] = region.bbox;
						const isSelected = region.id === selectedRegionId;
						const isEditing = region.id === editingRegionId;

						if (isEditing) {
							return (
								<input
									key={region.id}
									ref={inputRef}
									value={draftText}
									onChange={(e) => setDraftText(e.target.value)}
									onBlur={() => {
										// Committing/cancelling unmounts this input, which can itself
										// fire a native blur — guard so that stray event doesn't
										// re-cancel a Tab-focused next region or re-fire after Enter.
										if (useEditorStore.getState().editingRegionId === region.id) {
											cancelEditing();
										}
									}}
									onKeyDown={(e) => {
										if (e.key === 'Enter') {
											e.preventDefault();
											commitEdit(region.id, draftText);
										} else if (e.key === 'Escape') {
											e.preventDefault();
											cancelEditing();
										} else if (e.key === 'Tab') {
											e.preventDefault();
											commitAndFocusNext(e.shiftKey ? -1 : 1);
										}
									}}
									className="absolute rounded-sm border border-link bg-canvas-elevated px-0 shadow-[0_2px_8px_rgba(0,0,0,0.12)] outline-none ring-2 ring-link/15 transition-shadow"
									style={{
										left: x,
										top: y,
										width: w,
										height: h,
										fontFamily: fontFamilyCss(region.fontFamily),
										fontSize: region.fontSize ?? undefined,
										fontWeight: region.fontWeight ?? undefined,
										letterSpacing: region.letterSpacing,
										color: region.textColor ? `rgb(${region.textColor.join(',')})` : undefined,
										textAlign: region.alignment,
										background: backgroundCss(region.background),
									}}
								/>
							);
						}

						const confidence = confidenceLevel(region.confidence);

						return (
							<button
								key={region.id}
								type="button"
								onClick={() => startEditing(region.id)}
								title={region.text}
								className={`group absolute rounded-sm border transition-colors ${
									isSelected ? 'border-link bg-link/10' : 'border-transparent hover:border-hairline hover:bg-hairline-soft/60'
								}`}
								style={{ left: x, top: y, width: w, height: h }}
							>
								{debugMode &&
									region.chars.map((charBox, index) => (
										<span
											key={index}
											className="absolute top-0 h-full border-l border-warning/70"
											style={{ left: charBox.x - x, width: charBox.w }}
										/>
									))}
								{confidence !== 'none' && (
									<span
										role="button"
										tabIndex={0}
										onClick={(e) => {
											e.stopPropagation();
											openOverridePanel(region.id);
										}}
										onKeyDown={(e) => {
											if (e.key === 'Enter' || e.key === ' ') {
												e.stopPropagation();
												e.preventDefault();
												openOverridePanel(region.id);
											}
										}}
										title={`match confidence: ${region.confidence?.toFixed(2) ?? 'n/a'} — click to review font match`}
										className={`absolute -right-1 -top-1 h-2.5 w-2.5 rounded-full border border-canvas-elevated ${
											confidence === 'warning' ? 'bg-warning' : 'bg-link'
										}`}
									/>
								)}
								{/* Always reachable, not just when the score is low: the matcher
								    can be confidently wrong (e.g. picks bold when the source is
								    regular), so the correction path can't be gated on the score. */}
								<span
									role="button"
									tabIndex={0}
									onClick={(e) => {
										e.stopPropagation();
										openOverridePanel(region.id);
									}}
									onKeyDown={(e) => {
										if (e.key === 'Enter' || e.key === ' ') {
											e.stopPropagation();
											e.preventDefault();
											openOverridePanel(region.id);
										}
									}}
									title="review or correct the matched font"
									className="absolute -bottom-1 -right-1 flex h-4 w-4 items-center justify-center rounded-full border border-hairline bg-canvas-elevated text-[9px] leading-none text-faint opacity-0 transition-opacity group-hover:opacity-100 hover:text-link"
								>
									Aa
								</span>
							</button>
						);
					})}
				</div>
			</div>

			{isAnalyzing && (
				<div className="pointer-events-none absolute inset-0 flex items-center justify-center">
					<div className="flex flex-col items-center gap-3 rounded-lg border border-hairline bg-canvas-elevated/95 px-6 py-5 shadow-md backdrop-blur-sm">
						<Spinner />
						<p className="text-[13px] text-body">Analyzing your screenshot…</p>
					</div>
				</div>
			)}

			{isRendering && (
				<div
					className={`${embedded ? 'absolute' : 'fixed'} bottom-4 left-1/2 -translate-x-1/2 rounded-md border border-hairline bg-canvas-elevated px-3 py-1.5 text-xs text-link shadow-sm`}
				>
					Rendering…
				</div>
			)}
			{renderError && (
				<div
					className={`${embedded ? 'absolute' : 'fixed'} bottom-4 left-1/2 -translate-x-1/2 rounded-md border border-hairline bg-canvas-elevated px-3 py-1.5 text-xs text-error shadow-sm`}
				>
					{renderError}
				</div>
			)}
		</div>
	);
}

function Spinner() {
	return (
		<svg className="h-6 w-6 animate-spin text-link" viewBox="0 0 24 24" fill="none" aria-hidden="true">
			<circle className="opacity-20" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" />
			<path d="M22 12a10 10 0 0 0-10-10" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
		</svg>
	);
}
