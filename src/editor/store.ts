import { create } from 'zustand';

export interface CharBox {
	x: number;
	y: number;
	w: number;
	h: number;
}

export type RgbColor = [number, number, number];

export interface GradientStop {
	position: number;
	color: RgbColor;
}

export interface BackgroundFill {
	kind: 'flat' | 'gradient';
	color: RgbColor | null;
	angleDeg: number | null;
	stops: GradientStop[];
}

export interface UiElement {
	kind: 'button' | 'pill' | 'input' | 'unknown';
	bbox: [number, number, number, number];
	fillColor: RgbColor;
}

export interface FontCandidateScore {
	family: string;
	weight: number;
	score: number;
}

export interface Region {
	id: string;
	text: string;
	bbox: [number, number, number, number];
	blockId: string;
	chars: CharBox[];
	script: 'latin';
	direction: 'ltr' | 'rtl';
	confidence: number | null;
	alphaMaskPng: string | null;
	fontFamily: string | null;
	fontWeight: number | null;
	fontSize: number | null;
	letterSpacing: number;
	baselineY: number | null;
	xOffset: number | null;
	textColor: RgbColor | null;
	background: BackgroundFill | null;
	alignment: 'left' | 'center' | 'right';
	lineHeight: number | null;
	uiElement: UiElement | null;
	fontCandidates: FontCandidateScore[];
	// Manual "slight nudge" from the detected position — a drag or Alt+Arrow
	// in the editor (see Canvas.tsx) — on top of wherever stage 3 detected
	// the text and the expand-to-fit box puts it. Always present (defaults to
	// 0), never comes back from /analyze.
	offsetX: number;
	offsetY: number;
}

// Nudge drags/key-taps are clamped to this range (px) in both axes — "slight
// repositioning," not free placement; see the /app conversation about why
// free-drag isn't offered (the pipeline can only guarantee a clean result
// where it actually measured the background).
export const MAX_NUDGE_PX = 48;

// A region's replacement text plus the style stage 3 matched for it — the
// full payload /render needs to redo erase+re-render from the pristine
// original image. Keyed by region id and kept cumulative across edits: every
// /render call resends every edit made so far (against the original file),
// so edits never compound rendering error on top of a previous render.
export interface PendingEdit {
	regionId: string;
	bbox: [number, number, number, number];
	text: string;
	fontFamily: string;
	fontWeight: number;
	fontSize: number;
	letterSpacing: number;
	baselineY: number;
	xOffset: number;
	textColor: RgbColor;
	background: BackgroundFill | null;
	alignment: 'left' | 'center' | 'right';
	offsetX: number;
	offsetY: number;
}

interface RenderApiResult {
	region_id: string;
	font_size: number;
	overflowed: boolean;
}

interface RenderApiResponse {
	image_png_base64: string;
	results: RenderApiResult[];
}

function backgroundToWire(background: BackgroundFill | null) {
	if (!background) return null;
	return {
		kind: background.kind,
		color: background.color,
		angle_deg: background.angleDeg,
		stops: background.stops.map((stop) => ({ position: stop.position, color: stop.color })),
	};
}

// The subset of a region's style that the font override panel lets the user
// correct when stage 3's match is wrong.
export interface StyleOverride {
	fontFamily: string;
	fontWeight: number;
	fontSize: number;
	letterSpacing: number;
	textColor: RgbColor;
	alignment: 'left' | 'center' | 'right';
}

interface EditorState {
	imageUrl: string | null;
	imageFile: File | null;
	imageWidth: number;
	imageHeight: number;
	scaleFactor: 1 | 2 | 3;
	regions: Region[];
	selectedRegionId: string | null;
	editingRegionId: string | null;
	overridePanelRegionId: string | null;
	edits: Record<string, PendingEdit>;
	// 'uploading' has a real, observable percentage (uploadProgress, driven by
	// XHR upload progress events in Dropzone). 'analyzing' covers the
	// server-side OCR/separation/font-matching work, which has no progress
	// signal — the UI shows staged status text there instead of a percentage.
	status: 'idle' | 'uploading' | 'analyzing' | 'error';
	uploadProgress: number;
	// Real per-region progress during 'analyzing', driven by NDJSON progress
	// lines from /api/analyze (see Dropzone.handleFile) — null until the
	// first progress message arrives.
	analyzeProgress: { current: number; total: number } | null;
	errorMessage: string | null;
	isRendering: boolean;
	renderError: string | null;
	debugMode: boolean;
	setImage: (url: string, file: File, width: number, height: number) => void;
	setRegions: (regions: Region[]) => void;
	setScaleFactor: (scaleFactor: 1 | 2 | 3) => void;
	setUploadProgress: (percent: number) => void;
	setAnalyzeProgress: (current: number, total: number) => void;
	selectRegion: (id: string | null) => void;
	startEditing: (id: string) => void;
	// Selects, starts inline text editing, and expands the region's row in
	// the sidebar all at once — the single entry point for "work on this
	// region" from both the canvas and the sidebar (see LayersPanel).
	startEditingWithStyle: (id: string) => void;
	cancelEditing: () => void;
	commitEdit: (id: string, newText: string) => Promise<void>;
	// Adds (dx, dy) to the region's current offset (so repeated nudges
	// compose), clamps to MAX_NUDGE_PX, and re-renders once — called on drag
	// release or an Alt+Arrow key tap, never mid-drag (see Canvas.tsx).
	nudgeRegion: (id: string, dx: number, dy: number) => Promise<void>;
	openOverridePanel: (id: string) => void;
	closeOverridePanel: () => void;
	applyOverride: (id: string, overrides: StyleOverride) => Promise<void>;
	setStatus: (status: EditorState['status'], errorMessage?: string | null) => void;
	toggleDebugMode: () => void;
	reset: () => void;
}

export const useEditorStore = create<EditorState>((set, get) => {
	// Superseding an in-flight /render call (a newer edit/override landing
	// before the previous one's response) aborts the older request instead of
	// letting both race — the debounced auto-apply in FontOverridePanel can
	// fire several of these close together as the user drags a slider.
	let renderAbortController: AbortController | null = null;

	function pendingEditFor(region: Region, text: string, overrides?: StyleOverride): PendingEdit {
		return {
			regionId: region.id,
			bbox: region.bbox,
			text,
			fontFamily: overrides?.fontFamily ?? region.fontFamily ?? 'Inter',
			fontWeight: overrides?.fontWeight ?? region.fontWeight ?? 400,
			fontSize: overrides?.fontSize ?? region.fontSize ?? 16,
			letterSpacing: overrides?.letterSpacing ?? region.letterSpacing,
			baselineY: region.baselineY ?? region.bbox[1] + region.bbox[3] * 0.8,
			xOffset: region.xOffset ?? region.bbox[0],
			textColor: overrides?.textColor ?? region.textColor ?? [0, 0, 0],
			background: region.background,
			alignment: overrides?.alignment ?? region.alignment,
			offsetX: region.offsetX,
			offsetY: region.offsetY,
		};
	}

	// Shared by commitEdit and applyOverride: always re-renders every edit made
	// so far against the pristine original file (never the last output), so
	// edits/overrides don't compound rendering error on top of each other.
	async function postRender(nextEdits: Record<string, PendingEdit>) {
		const state = get();
		if (!state.imageFile) return;

		renderAbortController?.abort();
		const controller = new AbortController();
		renderAbortController = controller;

		set({ isRendering: true, renderError: null, edits: nextEdits });

		try {
			const formData = new FormData();
			formData.set('file', state.imageFile);
			formData.set(
				'edits',
				JSON.stringify(
					Object.values(nextEdits).map((edit) => ({
						region_id: edit.regionId,
						bbox: edit.bbox,
						text: edit.text,
						font_family: edit.fontFamily,
						font_weight: edit.fontWeight,
						font_size: edit.fontSize,
						letter_spacing: edit.letterSpacing,
						baseline_y: edit.baselineY,
						x_offset: edit.xOffset,
						text_color: edit.textColor,
						background: backgroundToWire(edit.background),
						alignment: edit.alignment,
						offset_x: edit.offsetX,
						offset_y: edit.offsetY,
					})),
				),
			);

			const response = await fetch('/api/render', { method: 'POST', body: formData, signal: controller.signal });
			if (!response.ok) {
				throw new Error(`render failed with status ${response.status}`);
			}
			const data = (await response.json()) as RenderApiResponse;

			set({ imageUrl: `data:image/png;base64,${data.image_png_base64}`, isRendering: false });
		} catch (err) {
			// A newer postRender call already aborted this one and owns
			// isRendering/renderError now — touching state here would clobber it.
			if (err instanceof DOMException && err.name === 'AbortError') return;
			set({ isRendering: false, renderError: err instanceof Error ? err.message : 'render failed' });
		}
	}

	return {
		imageUrl: null,
		imageFile: null,
		imageWidth: 0,
		imageHeight: 0,
		scaleFactor: 1,
		regions: [],
		selectedRegionId: null,
		editingRegionId: null,
		overridePanelRegionId: null,
		edits: {},
		status: 'idle',
		uploadProgress: 0,
		analyzeProgress: null,
		errorMessage: null,
		isRendering: false,
		renderError: null,
		debugMode: false,
		setImage: (url, file, width, height) =>
			set({
				imageUrl: url,
				imageFile: file,
				imageWidth: width,
				imageHeight: height,
				regions: [],
				selectedRegionId: null,
				editingRegionId: null,
				overridePanelRegionId: null,
				edits: {},
				uploadProgress: 0,
				analyzeProgress: null,
			}),
		setRegions: (regions) => set({ regions }),
		setScaleFactor: (scaleFactor) => set({ scaleFactor }),
		setUploadProgress: (percent) => set({ uploadProgress: percent }),
		setAnalyzeProgress: (current, total) => set({ analyzeProgress: { current, total } }),
		selectRegion: (id) => set({ selectedRegionId: id }),
		startEditing: (id) => set({ selectedRegionId: id, editingRegionId: id, overridePanelRegionId: null, renderError: null }),
		startEditingWithStyle: (id) =>
			set({ selectedRegionId: id, editingRegionId: id, overridePanelRegionId: id, renderError: null }),
		cancelEditing: () => set({ editingRegionId: null }),
		commitEdit: async (id, newText) => {
			const state = get();
			const region = state.regions.find((r) => r.id === id);
			if (!region || !state.imageFile) {
				set({ editingRegionId: null });
				return;
			}
			if (newText === region.text) {
				set({ editingRegionId: null });
				return;
			}

			set({ editingRegionId: null, regions: state.regions.map((r) => (r.id === id ? { ...r, text: newText } : r)) });
			await postRender({ ...state.edits, [id]: pendingEditFor(region, newText) });
		},
		nudgeRegion: async (id, dx, dy) => {
			const state = get();
			const region = state.regions.find((r) => r.id === id);
			if (!region || !state.imageFile) return;

			const clamp = (v: number) => Math.max(-MAX_NUDGE_PX, Math.min(MAX_NUDGE_PX, v));
			const merged: Region = { ...region, offsetX: clamp(region.offsetX + dx), offsetY: clamp(region.offsetY + dy) };
			set({ regions: state.regions.map((r) => (r.id === id ? merged : r)) });
			await postRender({ ...state.edits, [id]: pendingEditFor(merged, merged.text) });
		},
		openOverridePanel: (id) => set({ overridePanelRegionId: id, editingRegionId: null, selectedRegionId: id }),
		closeOverridePanel: () => set({ overridePanelRegionId: null }),
		applyOverride: async (id, overrides) => {
			const state = get();
			const region = state.regions.find((r) => r.id === id);
			if (!region || !state.imageFile) return;

			const merged: Region = { ...region, ...overrides };
			set({ regions: state.regions.map((r) => (r.id === id ? merged : r)) });
			await postRender({ ...state.edits, [id]: pendingEditFor(merged, merged.text, overrides) });
		},
		setStatus: (status, errorMessage = null) => set({ status, errorMessage }),
		toggleDebugMode: () => set((s) => ({ debugMode: !s.debugMode })),
		reset: () =>
			set({
				imageUrl: null,
				imageFile: null,
				imageWidth: 0,
				imageHeight: 0,
				scaleFactor: 1,
				regions: [],
				selectedRegionId: null,
				editingRegionId: null,
				overridePanelRegionId: null,
				edits: {},
				status: 'idle',
				uploadProgress: 0,
				analyzeProgress: null,
				errorMessage: null,
				isRendering: false,
				renderError: null,
				debugMode: false,
			}),
	};
});
