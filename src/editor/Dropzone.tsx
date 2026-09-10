import { useCallback, useRef, useState, type DragEvent } from 'react';
import {
	useEditorStore,
	type BackgroundFill,
	type CharBox,
	type FontCandidateScore,
	type Region,
	type RgbColor,
	type UiElement,
} from './store';

interface AnalyzeCharBox {
	x: number;
	y: number;
	w: number;
	h: number;
}

interface AnalyzeGradientStop {
	position: number;
	color: RgbColor;
}

interface AnalyzeBackgroundFill {
	kind: 'flat' | 'gradient';
	color: RgbColor | null;
	angle_deg: number | null;
	stops: AnalyzeGradientStop[];
}

interface AnalyzeUiElement {
	kind: 'button' | 'pill' | 'input' | 'unknown';
	bbox: [number, number, number, number];
	fill_color: RgbColor;
}

interface AnalyzeFontCandidateScore {
	family: string;
	weight: number;
	score: number;
}

interface AnalyzeRegion {
	id: string;
	text: string;
	bbox: [number, number, number, number];
	block_id: string;
	chars: AnalyzeCharBox[];
	script: 'latin';
	direction: 'ltr' | 'rtl';
	confidence: number | null;
	match_margin: number | null;
	alpha_mask_png: string | null;
	font_family: string | null;
	font_weight: number | null;
	font_size: number | null;
	font_size_hint: number | null;
	letter_spacing: number;
	baseline_y: number | null;
	x_offset: number | null;
	text_color: RgbColor | null;
	background: AnalyzeBackgroundFill | null;
	alignment: 'left' | 'center' | 'right';
	line_height: number | null;
	ui_element: AnalyzeUiElement | null;
	font_candidates: AnalyzeFontCandidateScore[];
}

interface AnalyzeResponse {
	image_width: number;
	image_height: number;
	scale_factor: 1 | 2 | 3;
	regions: AnalyzeRegion[];
}

function toCharBox(charBox: AnalyzeCharBox): CharBox {
	return { x: charBox.x, y: charBox.y, w: charBox.w, h: charBox.h };
}

function toBackgroundFill(background: AnalyzeBackgroundFill | null): BackgroundFill | null {
	if (!background) return null;
	return {
		kind: background.kind,
		color: background.color,
		angleDeg: background.angle_deg,
		stops: background.stops.map((stop) => ({ position: stop.position, color: stop.color })),
	};
}

function toUiElement(uiElement: AnalyzeUiElement | null): UiElement | null {
	if (!uiElement) return null;
	return { kind: uiElement.kind, bbox: uiElement.bbox, fillColor: uiElement.fill_color };
}

function toFontCandidateScore(candidate: AnalyzeFontCandidateScore): FontCandidateScore {
	return { family: candidate.family, weight: candidate.weight, score: candidate.score };
}

// Converts one wire-format region. enrichmentStatus defaults to 'ready'
// since every caller except the "detected" handler is converting an
// already-enriched region (a "region" or "result" message) — the
// "detected" handler overrides it to 'pending' explicitly (see below).
function toRegion(region: AnalyzeRegion): Region {
	return {
		id: region.id,
		text: region.text,
		bbox: region.bbox,
		blockId: region.block_id,
		chars: region.chars.map(toCharBox),
		script: region.script,
		direction: region.direction,
		confidence: region.confidence,
		matchMargin: region.match_margin,
		alphaMaskPng: region.alpha_mask_png,
		fontFamily: region.font_family,
		fontWeight: region.font_weight,
		fontSize: region.font_size,
		fontSizeHint: region.font_size_hint,
		letterSpacing: region.letter_spacing,
		baselineY: region.baseline_y,
		xOffset: region.x_offset,
		textColor: region.text_color,
		background: toBackgroundFill(region.background),
		alignment: region.alignment,
		lineHeight: region.line_height,
		uiElement: toUiElement(region.ui_element),
		fontCandidates: region.font_candidates.map(toFontCandidateScore),
		offsetX: 0,
		offsetY: 0,
		enrichmentStatus: 'ready',
		styleOverridden: false,
	};
}

export function Dropzone() {
	const setImage = useEditorStore((s) => s.setImage);
	const setRegions = useEditorStore((s) => s.setRegions);
	const upsertRegion = useEditorStore((s) => s.upsertRegion);
	const markPendingRegionsFailed = useEditorStore((s) => s.markPendingRegionsFailed);
	const setScaleFactor = useEditorStore((s) => s.setScaleFactor);
	const setUploadProgress = useEditorStore((s) => s.setUploadProgress);
	const setAnalyzeProgress = useEditorStore((s) => s.setAnalyzeProgress);
	const setStatus = useEditorStore((s) => s.setStatus);
	const status = useEditorStore((s) => s.status);
	const errorMessage = useEditorStore((s) => s.errorMessage);
	const [isDragging, setIsDragging] = useState(false);
	const inputRef = useRef<HTMLInputElement>(null);

	const handleFile = useCallback(
		async (file: File) => {
			const url = URL.createObjectURL(file);
			const dimensions = await new Promise<{ width: number; height: number }>((resolve, reject) => {
				const img = new Image();
				img.onload = () => resolve({ width: img.naturalWidth, height: img.naturalHeight });
				img.onerror = reject;
				img.src = url;
			});

			setImage(url, file, dimensions.width, dimensions.height);
			setStatus('uploading');

			const formData = new FormData();
			formData.set('file', file);

			// XMLHttpRequest, not fetch, because fetch has no upload-progress
			// event — this is what drives the real (not simulated) progress bar
			// while the file is in transit. The response side is also read
			// incrementally (xhr.onprogress, not just onload): /api/analyze
			// streams newline-delimited JSON — a "detected" line (every line's
			// text/bbox, no styling yet) as soon as OCR finishes, one "progress"
			// and one "region" line (that region's full styling) per detected
			// line as its enrichment completes, and a final "result" line — so
			// both "N of M" and the regions actually on screen update for real,
			// not simulated.
			const xhr = new XMLHttpRequest();
			xhr.open('POST', '/api/analyze');

			let bytesRead = 0;
			let buffer = '';
			let finalResult: AnalyzeResponse | null = null;
			let streamError: string | null = null;

			const handleLine = (line: string) => {
				const trimmed = line.trim();
				if (!trimmed) return;
				try {
					const message = JSON.parse(trimmed) as { type: string } & Partial<AnalyzeResponse> & {
						current?: number;
						total?: number;
						region?: AnalyzeRegion;
					};
					if (message.type === 'progress' && typeof message.current === 'number' && typeof message.total === 'number') {
						setAnalyzeProgress(message.current, message.total);
					} else if (message.type === 'detected' && Array.isArray(message.regions)) {
						// Text/position for every detected line, before any of them
						// have a font/color yet. This is the new readiness point:
						// status flips to 'enriching' here (not at the final
						// "result") so the editor becomes usable — regions
						// visible, selectable, and editable — right after OCR,
						// while exact font matching continues in the background.
						// Every region starts 'pending'; see commitEdit/
						// nudgeRegion/applyOverride in store.ts for how an edit on
						// a still-pending region waits for its own "region"
						// message instead of using a fallback style.
						setRegions(message.regions.map((r) => ({ ...toRegion(r), enrichmentStatus: 'pending' as const })));
						setStatus('enriching');
					} else if (message.type === 'region' && message.region) {
						// One region's enrichment just finished — replace its
						// "detected" stub (same id) with the fully-styled version.
						upsertRegion(toRegion(message.region));
					} else if (message.type === 'result') {
						finalResult = message as unknown as AnalyzeResponse;
					}
				} catch {
					streamError = 'could not parse analyze response';
				}
			};

			xhr.upload.onprogress = (event) => {
				if (event.lengthComputable) {
					setUploadProgress(Math.round((event.loaded / event.total) * 100));
				}
			};
			xhr.upload.onload = () => {
				setStatus('analyzing');
			};

			xhr.onprogress = () => {
				const text = xhr.responseText;
				buffer += text.slice(bytesRead);
				bytesRead = text.length;
				const lines = buffer.split('\n');
				buffer = lines.pop() ?? '';
				for (const line of lines) handleLine(line);
			};

			xhr.onload = () => {
				if (buffer) {
					handleLine(buffer);
					buffer = '';
				}
				if (xhr.status >= 200 && xhr.status < 300 && finalResult && !streamError) {
					// Per-region upsert (merge), not a blanket setRegions replace:
					// the user may have already edited text, nudged a position, or
					// applied a style override on a region while its own "region"
					// message was still in flight — a raw replace here would
					// silently discard that. upsertRegion also resolves any
					// commitEdit/nudgeRegion/applyOverride still waiting on a
					// region whose "region" message never arrived for some reason
					// (the final result is the authoritative last word on every
					// region's enrichment either way).
					for (const region of finalResult.regions) {
						upsertRegion(toRegion(region));
					}
					setScaleFactor(finalResult.scale_factor);
					setStatus('idle');
				} else {
					markPendingRegionsFailed(streamError ?? `analyze failed with status ${xhr.status}`);
					setStatus('error', streamError ?? `analyze failed with status ${xhr.status}`);
				}
			};
			xhr.onerror = () => {
				markPendingRegionsFailed('analyze request failed');
				setStatus('error', 'analyze request failed');
			};

			xhr.send(formData);
		},
		[
			setImage,
			setRegions,
			upsertRegion,
			markPendingRegionsFailed,
			setScaleFactor,
			setUploadProgress,
			setAnalyzeProgress,
			setStatus,
		],
	);

	const onDrop = useCallback(
		(event: DragEvent<HTMLDivElement>) => {
			event.preventDefault();
			setIsDragging(false);
			const file = event.dataTransfer.files[0];
			if (file) handleFile(file);
		},
		[handleFile],
	);

	return (
		<div
			onDragOver={(e) => {
				e.preventDefault();
				setIsDragging(true);
			}}
			onDragLeave={() => setIsDragging(false)}
			onDrop={onDrop}
			onClick={() => inputRef.current?.click()}
			className={`flex w-full max-w-xl cursor-pointer flex-col items-center justify-center gap-3 rounded-xl border border-dashed px-4 py-10 text-center transition-colors sm:gap-4 sm:px-8 sm:py-14 ${
				isDragging ? 'border-link bg-hairline-soft' : 'border-hairline bg-canvas-elevated'
			}`}
		>
			<img src="/icon.png" alt="ScreenshotTextEditor logo" width="44" height="44" className="h-10 w-10 sm:h-11 sm:w-11" />

			<div className="flex flex-col gap-1">
				<p className="text-ink text-sm font-medium sm:text-base">Drop a screenshot here, or click to choose a file</p>
				<p className="text-faint text-xs">PNG or JPEG</p>
			</div>

			<button
				type="button"
				onClick={(e) => {
					e.stopPropagation();
					inputRef.current?.click();
				}}
				className="rounded-full bg-ink px-4 py-2 text-[13px] font-medium text-on-primary transition-colors hover:bg-ink/90"
			>
				Choose a file
			</button>

			<p className="text-faint max-w-sm px-2 text-center text-xs">
				Latin-script text on flat or simple-gradient backgrounds — CJK and RTL scripts aren't supported yet
			</p>
			{(status === 'uploading' || status === 'analyzing') && <p className="text-link text-xs">Uploading…</p>}
			{status === 'error' && <p className="text-error text-xs">{errorMessage}</p>}
			<input
				ref={inputRef}
				type="file"
				accept="image/png,image/jpeg"
				className="hidden"
				onChange={(e) => {
					const file = e.target.files?.[0];
					if (file) handleFile(file);
				}}
			/>
		</div>
	);
}
