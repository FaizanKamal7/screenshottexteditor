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
	alpha_mask_png: string | null;
	font_family: string | null;
	font_weight: number | null;
	font_size: number | null;
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
		alphaMaskPng: region.alpha_mask_png,
		fontFamily: region.font_family,
		fontWeight: region.font_weight,
		fontSize: region.font_size,
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
	};
}

export function Dropzone() {
	const setImage = useEditorStore((s) => s.setImage);
	const setRegions = useEditorStore((s) => s.setRegions);
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
			// incrementally (xhr.onprogress, not just onload): /api/analyze now
			// streams newline-delimited JSON, one progress line per detected
			// text region as the pipeline actually finishes it, plus a final
			// result line — so "N of M" in the UI is real, not simulated.
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
					};
					if (message.type === 'progress' && typeof message.current === 'number' && typeof message.total === 'number') {
						setAnalyzeProgress(message.current, message.total);
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
					setRegions(finalResult.regions.map(toRegion));
					setScaleFactor(finalResult.scale_factor);
					setStatus('idle');
				} else {
					setStatus('error', streamError ?? `analyze failed with status ${xhr.status}`);
				}
			};
			xhr.onerror = () => {
				setStatus('error', 'analyze request failed');
			};

			xhr.send(formData);
		},
		[setImage, setRegions, setScaleFactor, setUploadProgress, setAnalyzeProgress, setStatus],
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
			className={`flex h-80 w-full max-w-xl cursor-pointer flex-col items-center justify-center gap-2 rounded-md border border-dashed text-sm transition-colors ${
				isDragging ? 'border-link bg-hairline-soft' : 'border-hairline bg-canvas-elevated'
			}`}
		>
			<p className="text-body">Drop a screenshot here, or click to choose a file</p>
			<p className="text-faint text-xs">PNG or JPEG</p>
			<p className="text-faint px-4 text-center text-xs">
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
