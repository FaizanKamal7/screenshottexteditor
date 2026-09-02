import { useEffect, useLayoutEffect, useMemo, useRef, useState, type PointerEvent as ReactPointerEvent } from 'react';
import { MAX_NUDGE_PX, useEditorStore, type Region } from './store';
import { backgroundCss, confidenceLevel, fontFamilyCss } from './styleHelpers';

export function readingOrder(regions: Region[]): Region[] {
	return [...regions].sort((a, b) => a.bbox[1] - b.bbox[1] || a.bbox[0] - b.bbox[0]);
}

// Breathing room, in CSS px, kept around the scaled image inside the pane.
const FIT_PADDING = 48;

// What's actually happening per line during the "Analyzing text N of M"
// step (services/pipeline/main.py's _process_line: separate -> match_font
// -> estimate_color -> detect_ui_element). Lines run in parallel across
// worker processes, so no single one of these is "the" current step at any
// given moment — cycling through them still tells the truth about what
// the backend is doing as a whole, just not synced to one specific line.
const MATCHING_STEP_CAPTIONS = [
	'Separating text from background',
	'Matching fonts and sizes',
	'Detecting colors and styles',
	'Checking buttons and layout',
];
const MATCHING_STEP_INTERVAL_MS = 1400;

const MIN_ZOOM = 0.5;
const MAX_ZOOM = 1.5;
// How tall (px, on screen) a region should read as once focused for editing.
const FOCUS_TARGET_HEIGHT_PX = 56;

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
	const uploadProgress = useEditorStore((s) => s.uploadProgress);
	const analyzeProgress = useEditorStore((s) => s.analyzeProgress);
	const startEditingWithStyle = useEditorStore((s) => s.startEditingWithStyle);
	const cancelEditing = useEditorStore((s) => s.cancelEditing);
	const commitEdit = useEditorStore((s) => s.commitEdit);
	const nudgeRegion = useEditorStore((s) => s.nudgeRegion);
	const debugMode = useEditorStore((s) => s.debugMode);

	const orderedRegions = useMemo(() => readingOrder(regions), [regions]);
	const editingRegion = regions.find((r) => r.id === editingRegionId) ?? null;
	const isUploading = status === 'uploading';
	const isAnalyzing = status === 'analyzing';
	const isBusy = isUploading || isAnalyzing;
	const isDetecting = isAnalyzing && (!analyzeProgress || analyzeProgress.total === 0);
	const isMatching = isAnalyzing && !isDetecting;

	const [detectElapsedSeconds, setDetectElapsedSeconds] = useState(0);
	useEffect(() => {
		if (!isDetecting) {
			setDetectElapsedSeconds(0);
			return;
		}
		const interval = setInterval(() => setDetectElapsedSeconds((s) => s + 1), 1000);
		return () => clearInterval(interval);
	}, [isDetecting]);

	const [matchingCaptionIndex, setMatchingCaptionIndex] = useState(0);
	useEffect(() => {
		if (!isMatching) {
			setMatchingCaptionIndex(0);
			return;
		}
		const interval = setInterval(
			() => setMatchingCaptionIndex((i) => (i + 1) % MATCHING_STEP_CAPTIONS.length),
			MATCHING_STEP_INTERVAL_MS,
		);
		return () => clearInterval(interval);
	}, [isMatching]);

	const [draftText, setDraftText] = useState('');
	const inputRef = useRef<HTMLInputElement>(null);
	const paneRef = useRef<HTMLDivElement>(null);
	const [fitScale, setFitScale] = useState(1);
	const [zoom, setZoom] = useState(1);
	const zoomRef = useRef(1);
	const effectiveScale = fitScale * zoom;

	// Drag-to-nudge: live preview only (no network calls mid-drag — see
	// nudgeRegion in the store for why). dx/dy are in native image-pixel
	// units, already clamped to the total offset staying within
	// MAX_NUDGE_PX, so the visual preview never overshoots what will
	// actually commit on release.
	const [dragPreview, setDragPreview] = useState<{ regionId: string; dx: number; dy: number } | null>(null);
	const dragStartRef = useRef<{
		pointerId: number;
		startClientX: number;
		startClientY: number;
		baseOffsetX: number;
		baseOffsetY: number;
	} | null>(null);

	const beginDrag = (e: ReactPointerEvent, region: Region) => {
		e.stopPropagation();
		e.preventDefault();
		(e.currentTarget as Element).setPointerCapture(e.pointerId);
		dragStartRef.current = {
			pointerId: e.pointerId,
			startClientX: e.clientX,
			startClientY: e.clientY,
			baseOffsetX: region.offsetX,
			baseOffsetY: region.offsetY,
		};
		setDragPreview({ regionId: region.id, dx: 0, dy: 0 });
	};

	const updateDrag = (e: ReactPointerEvent) => {
		const start = dragStartRef.current;
		if (!start || start.pointerId !== e.pointerId) return;
		// Screen-pixel movement -> native-image-pixel movement, so "slight"
		// feels the same regardless of current zoom level.
		const dxNative = (e.clientX - start.startClientX) / effectiveScale;
		const dyNative = (e.clientY - start.startClientY) / effectiveScale;
		const clampTotal = (base: number, delta: number) => Math.max(-MAX_NUDGE_PX, Math.min(MAX_NUDGE_PX, base + delta)) - base;
		setDragPreview({
			regionId: dragPreview?.regionId ?? '',
			dx: clampTotal(start.baseOffsetX, dxNative),
			dy: clampTotal(start.baseOffsetY, dyNative),
		});
	};

	const endDrag = (e: ReactPointerEvent, region: Region) => {
		const start = dragStartRef.current;
		if (!start || start.pointerId !== e.pointerId) return;
		dragStartRef.current = null;
		const preview = dragPreview;
		setDragPreview(null);
		if (preview && (preview.dx !== 0 || preview.dy !== 0)) {
			nudgeRegion(region.id, preview.dx, preview.dy);
		}
	};

	const nudgeByKeyboard = (region: Region, key: string, shiftKey: boolean) => {
		const step = shiftKey ? 10 : 2;
		const dx = key === 'ArrowLeft' ? -step : key === 'ArrowRight' ? step : 0;
		const dy = key === 'ArrowUp' ? -step : key === 'ArrowDown' ? step : 0;
		if (dx !== 0 || dy !== 0) nudgeRegion(region.id, dx, dy);
	};

	useEffect(() => {
		zoomRef.current = zoom;
	}, [zoom]);

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
			setFitScale(next > 0 ? next : 1);
		};

		computeScale();
		const observer = new ResizeObserver(computeScale);
		observer.observe(pane);
		return () => observer.disconnect();
	}, [imageWidth, imageHeight]);

	// A newly loaded image always starts at fit — manual zoom shouldn't carry
	// over from whatever the user was looking at before.
	useEffect(() => {
		setZoom(1);
	}, [imageWidth, imageHeight]);

	// Ctrl/Cmd+scroll to zoom, anchored on the cursor so the point under it
	// stays put. A native listener with { passive: false } — not React's
	// onWheel — so preventDefault reliably blocks the browser's own
	// page-zoom/scroll; a plain scroll (no modifier) still scrolls the pane.
	//
	// Both this and the focus-zoom effect below need to move the scroll
	// position only *after* the new scale has actually been committed to the
	// DOM — a plain requestAnimationFrame right after setZoom fires too early
	// (the pane hasn't grown yet, so the browser clamps the scroll request to
	// whatever range still exists, usually 0 — which read as "always jumps to
	// the top-left no matter what was clicked"). Routing both through this one
	// ref + layout effect, keyed off effectiveScale, guarantees the DOM is
	// already up to date. scrollRequestVersion is a second dependency for the
	// case where the requested zoom happens to equal the zoom already in
	// effect (e.g. two different regions that both clamp to the same focus
	// zoom) — effectiveScale wouldn't change then, so the version bump is
	// what actually re-triggers the effect.
	const pendingScrollRef = useRef<
		| { mode: 'anchor'; nativeX: number; nativeY: number; cursorViewportX: number; cursorViewportY: number }
		| { mode: 'center'; nativeX: number; nativeY: number }
		| null
	>(null);
	const [scrollRequestVersion, setScrollRequestVersion] = useState(0);
	const requestScroll = (pending: NonNullable<typeof pendingScrollRef.current>) => {
		pendingScrollRef.current = pending;
		setScrollRequestVersion((v) => v + 1);
	};

	useEffect(() => {
		const pane = paneRef.current;
		if (!pane) return;

		const handleWheel = (e: WheelEvent) => {
			if (!(e.ctrlKey || e.metaKey)) return;
			e.preventDefault();

			const rect = pane.getBoundingClientRect();
			const currentScale = fitScale * zoomRef.current;
			const cursorViewportX = e.clientX - rect.left;
			const cursorViewportY = e.clientY - rect.top;
			const nativeX = (cursorViewportX + pane.scrollLeft) / currentScale;
			const nativeY = (cursorViewportY + pane.scrollTop) / currentScale;

			const factor = Math.exp(-e.deltaY * 0.001);
			const nextZoom = Math.min(MAX_ZOOM, Math.max(MIN_ZOOM, zoomRef.current * factor));

			requestScroll({ mode: 'anchor', nativeX, nativeY, cursorViewportX, cursorViewportY });
			setZoom(nextZoom);
		};

		pane.addEventListener('wheel', handleWheel, { passive: false });
		return () => pane.removeEventListener('wheel', handleWheel);
	}, [fitScale]);

	// Applies whichever scroll was requested (cursor-anchored from the wheel
	// handler, or region-centered from the focus-zoom effect below) once the
	// new scale has actually been committed to the DOM — see the long comment
	// above pendingScrollRef for why this can't just be a requestAnimationFrame.
	useLayoutEffect(() => {
		const pane = paneRef.current;
		const pending = pendingScrollRef.current;
		if (!pane || !pending) return;
		pendingScrollRef.current = null;

		if (pending.mode === 'anchor') {
			pane.scrollLeft = pending.nativeX * effectiveScale - pending.cursorViewportX;
			pane.scrollTop = pending.nativeY * effectiveScale - pending.cursorViewportY;
		} else {
			pane.scrollTo({
				left: pending.nativeX * effectiveScale - pane.clientWidth / 2,
				top: pending.nativeY * effectiveScale - pane.clientHeight / 2,
				behavior: 'smooth',
			});
		}
		// eslint-disable-next-line react-hooks/exhaustive-deps
	}, [effectiveScale, scrollRequestVersion]);

	// Focus mode: zoom into whatever region just started editing — centered on
	// that region's actual position, not the top of the image — so small,
	// dense UI text is legible while typing, then zoom back out to the
	// default fit view once editing ends — always back to fit, not whatever
	// manual zoom the user had before (predictable over clever).
	const prevEditingRef = useRef<string | null>(null);
	useEffect(() => {
		if (editingRegionId && editingRegionId !== prevEditingRef.current) {
			const region = regions.find((r) => r.id === editingRegionId);
			if (region) {
				const [rx, ry, rw, rh] = region.bbox;
				const focusZoom = Math.min(MAX_ZOOM, Math.max(1, FOCUS_TARGET_HEIGHT_PX / (rh * fitScale)));
				requestScroll({ mode: 'center', nativeX: rx + rw / 2, nativeY: ry + rh / 2 });
				setZoom(focusZoom);
			}
		} else if (!editingRegionId && prevEditingRef.current) {
			setZoom(1);
		}

		prevEditingRef.current = editingRegionId;
		// eslint-disable-next-line react-hooks/exhaustive-deps
	}, [editingRegionId, regions, fitScale]);

	if (!imageUrl) return null;

	const commitAndFocusNext = (direction: 1 | -1) => {
		if (!editingRegion) return;
		commitEdit(editingRegion.id, draftText);
		const index = orderedRegions.findIndex((r) => r.id === editingRegion.id);
		const next = orderedRegions[(index + direction + orderedRegions.length) % orderedRegions.length];
		if (next) startEditingWithStyle(next.id);
	};

	return (
		<div
			ref={paneRef}
			onDoubleClick={() => setZoom(1)}
			className="relative flex h-full w-full overflow-auto bg-canvas p-3 md:p-6"
		>
			{/* margin: auto (not the pane's own flex-centering) centers this while
			    it fits, and — critically — collapses to 0 once it overflows the
			    pane at higher zoom, so every edge stays reachable by scrolling.
			    Flex/grid centering on the scrollable pane itself would clip
			    whichever edge overflows past the centering point first, since a
			    centered overflow can't be reached by scrolling to a negative
			    offset — that's what made regions near the top of a tall image
			    become unreachable once zoomed in. */}
			<div className="relative m-auto" style={{ width: imageWidth * effectiveScale, height: imageHeight * effectiveScale }}>
				<div
					className="absolute left-0 top-0 transition-transform duration-200 ease-out"
					style={{ width: imageWidth, height: imageHeight, transform: `scale(${effectiveScale})`, transformOrigin: 'top left' }}
				>
					<img
						src={imageUrl}
						width={imageWidth}
						height={imageHeight}
						alt="Uploaded screenshot"
						className={`block shadow-sm transition-[filter,opacity] duration-300 ${isBusy ? 'opacity-60 blur-[1px]' : ''}`}
					/>
					{regions.map((region) => {
						const [x, y, w, h] = region.bbox;
						const isSelected = region.id === selectedRegionId;
						const isEditing = region.id === editingRegionId;

						if (isEditing) {
							const isDraggingThis = dragPreview?.regionId === region.id;
							const previewDx = isDraggingThis ? dragPreview.dx : 0;
							const previewDy = isDraggingThis ? dragPreview.dy : 0;

							return (
								<div key={region.id} className="absolute" style={{ left: x + region.offsetX, top: y + region.offsetY }}>
									<input
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
											} else if (e.altKey && e.key.startsWith('Arrow')) {
												// Alt-gated so it never collides with the input's native
												// arrow-key text-cursor movement.
												e.preventDefault();
												nudgeByKeyboard(region, e.key, e.shiftKey);
											}
										}}
										className="absolute rounded-sm border border-link bg-canvas-elevated px-0 shadow-[0_2px_8px_rgba(0,0,0,0.12)] outline-none ring-2 ring-link/15 transition-shadow"
										style={{
											left: 0,
											top: 0,
											width: w,
											height: h,
											transform: isDraggingThis ? `translate(${previewDx}px, ${previewDy}px)` : undefined,
											fontFamily: fontFamilyCss(region.fontFamily),
											fontSize: region.fontSize ?? undefined,
											fontWeight: region.fontWeight ?? undefined,
											letterSpacing: region.letterSpacing,
											color: region.textColor ? `rgb(${region.textColor.join(',')})` : undefined,
											textAlign: region.alignment,
											background: backgroundCss(region.background),
										}}
									/>
									{/* Drag handle: a separate element, not the input itself, so
									    dragging never conflicts with placing a text cursor or
									    selecting text. */}
									<span
										role="button"
										tabIndex={0}
										title="Drag to nudge position slightly (or Alt+Arrow)"
										onPointerDown={(e) => beginDrag(e, region)}
										onPointerMove={updateDrag}
										onPointerUp={(e) => endDrag(e, region)}
										onPointerCancel={(e) => endDrag(e, region)}
										className="absolute -left-2.5 -top-2.5 flex h-5 w-5 cursor-move items-center justify-center rounded-full border border-hairline bg-canvas-elevated text-faint shadow-sm hover:text-link"
										style={{ transform: isDraggingThis ? `translate(${previewDx}px, ${previewDy}px)` : undefined }}
									>
										<svg viewBox="0 0 16 16" className="h-3 w-3" fill="currentColor">
											{[4, 8, 12].flatMap((cy) => [5, 11].map((cx) => <circle key={`${cx}-${cy}`} cx={cx} cy={cy} r="1.2" />))}
										</svg>
									</span>
								</div>
							);
						}

						const confidence = confidenceLevel(region.confidence);

						return (
							<button
								key={region.id}
								type="button"
								onClick={() => startEditingWithStyle(region.id)}
								title={region.text}
								className={`group absolute rounded-sm border transition-colors ${
									isSelected ? 'border-link bg-link/10' : 'border-transparent hover:border-hairline hover:bg-hairline-soft/60'
								}`}
								style={{ left: x + region.offsetX, top: y + region.offsetY, width: w, height: h }}
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
										title={`match confidence: ${region.confidence?.toFixed(2) ?? 'n/a'}`}
										className={`pointer-events-none absolute -right-1 -top-1 h-2.5 w-2.5 rounded-full border border-canvas-elevated ${
											confidence === 'warning' ? 'bg-warning' : 'bg-link'
										}`}
									/>
								)}
							</button>
						);
					})}
				</div>
			</div>

			{zoom !== 1 && !isBusy && (
				<button
					type="button"
					onClick={() => setZoom(1)}
					title="Reset zoom to fit (or double-click the canvas)"
					className="absolute bottom-4 right-4 rounded-full border border-hairline bg-canvas-elevated px-3 py-1.5 text-xs text-body shadow-sm hover:text-link"
				>
					{Math.round(zoom * 100)}%
				</button>
			)}

			{isBusy && (
				<div className="pointer-events-none absolute inset-0 flex items-center justify-center">
					<div className="flex w-max min-w-72 max-w-sm flex-col items-center gap-3 rounded-lg border border-hairline bg-canvas-elevated/95 px-6 py-5 shadow-md backdrop-blur-sm">
						{isUploading ? (
							<>
								<div className="h-1.5 w-full overflow-hidden rounded-full bg-hairline">
									<div
										className="h-full rounded-full bg-link transition-[width] duration-150 ease-out"
										style={{ width: `${uploadProgress}%` }}
									/>
								</div>
								<p className="whitespace-nowrap text-[13px] text-body">Uploading screenshot… {uploadProgress}%</p>
							</>
						) : analyzeProgress && analyzeProgress.total > 0 ? (
							<>
								<div className="h-2 w-full overflow-hidden rounded-full bg-hairline">
									<div
										className="h-full rounded-full bg-link transition-[width] duration-300 ease-out"
										style={{ width: `${Math.round((analyzeProgress.current / analyzeProgress.total) * 100)}%` }}
									/>
								</div>
								<p className="whitespace-nowrap text-[13px] text-body">
									Analyzing text {analyzeProgress.current} of {analyzeProgress.total}…
								</p>
								<p className="whitespace-nowrap text-[11px] text-faint">{MATCHING_STEP_CAPTIONS[matchingCaptionIndex]}</p>
							</>
						) : (
							<>
								<div className="h-2 w-full overflow-hidden rounded-full bg-hairline">
									<div className="loader-indeterminate-bar h-full w-2/5 rounded-full bg-link" />
								</div>
								<p className="whitespace-nowrap text-[13px] text-body">
									Detecting text{detectElapsedSeconds > 0 ? `… ${detectElapsedSeconds}s` : '…'}
								</p>
								<p className="whitespace-nowrap text-[11px] text-faint">Reading text in image</p>
							</>
						)}
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
