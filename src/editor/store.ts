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

// Explicit enrichment lifecycle for a detected region — never inferred from
// whether fontFamily/etc happen to be null, so a region that hasn't received
// its real MatchResult can't be silently mistaken for one that has.
//
// Only three states, not four: the backend submits every detected line's
// enrichment work to its process pool in one batch right after the
// "detected" message, with no observable "queued but not yet started"
// signal in between — from the client's perspective there is no way to
// distinguish "pending" from "in progress" for a region that hasn't
// produced a "region" message yet, so modeling them as two states would be
// fake precision the data doesn't support.
export type EnrichmentStatus = 'pending' | 'ready' | 'failed';

export interface Region {
	id: string;
	text: string;
	bbox: [number, number, number, number];
	blockId: string;
	chars: CharBox[];
	script: 'latin';
	direction: 'ltr' | 'rtl';
	confidence: number | null;
	// Score gap between the winning font candidate and the runner-up — a
	// distinct signal from `confidence` (match *quality* in absolute terms):
	// a small margin means a close call between two plausible fonts even
	// when both scored reasonably well. See FontOverridePanel's "Confidence"
	// label (kept separate from "Match quality", which is `confidence`).
	matchMargin: number | null;
	alphaMaskPng: string | null;
	fontFamily: string | null;
	fontWeight: number | null;
	fontSize: number | null;
	// Estimated size the real platform font (Helvetica Neue, SF Pro — see
	// docs/fonts.md's substitution table) would be set at, converted from
	// fontSize via cap-height ratio. Display-only hint for FontOverridePanel;
	// never sent to /render, since fontSize (not this) is what the substitute
	// font actually gets rendered at. null when the matched candidate has no
	// well-documented true-font target.
	fontSizeHint: number | null;
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
	enrichmentStatus: EnrichmentStatus;
	// True once the user has explicitly picked a style via FontOverridePanel
	// — protects that deliberate choice from being clobbered if the
	// automatic match (a "region" NDJSON message) for this same id arrives
	// afterward (see mergeEnrichedRegion).
	styleOverridden: boolean;
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

// One piece of a region being split by applyStyleToSelection: a substring of
// the original text, its measured on-screen width (native image-pixel
// space — same units as Region.bbox), and, only for the fragment(s) actually
// restyled, the style to apply. A fragment with no `overrides` keeps the
// source region's existing style — still needed as its own Region/PendingEdit
// so its slice of the image gets redrawn instead of left stale (see
// applyStyleToSelection).
export interface StyleFragment {
	text: string;
	widthPx: number;
	overrides?: StyleOverride;
}

// A point-in-time copy of everything undo/redo needs to restore: the region
// list (text, position, style) and the cumulative edit payload /render was
// last called with. Safe to store by reference rather than deep-cloning —
// every store action replaces `regions`/`edits` wholesale (map/spread), never
// mutates them in place, so a past snapshot can't be silently changed out
// from under it by a later action.
interface HistorySnapshot {
	regions: Region[];
	edits: Record<string, PendingEdit>;
}

// "Last five actions" per the editor's undo affordance — deliberately small:
// each entry pins a full regions/edits snapshot, and undo/redo both re-render
// against the backend, so this isn't meant as a deep scrollback.
const MAX_UNDO_STEPS = 5;

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
	// The current native browser text selection inside the editing `<input>`
	// for editingRegionId, as character offsets into that region's `text` —
	// null when there's no selection (or nothing is being edited). Lets
	// FontOverridePanel offer "style just the selection" instead of always
	// restyling the whole region. Set by Canvas.tsx's input onSelect/onChange;
	// cleared whenever editing starts/stops or a style is committed, so a
	// stale range can never be applied against a region it no longer matches.
	editingSelection: { start: number; end: number } | null;
	edits: Record<string, PendingEdit>;
	// past[last] is the state one undo away; future[0] is the state one redo
	// away. Any new edit (commitEdit/nudgeRegion/applyOverride) clears future —
	// standard undo/redo semantics, redoing a branch abandoned by a fresh edit
	// isn't supported.
	past: HistorySnapshot[];
	future: HistorySnapshot[];
	// 'uploading' has a real, observable percentage (uploadProgress, driven by
	// XHR upload progress events in Dropzone). 'analyzing' covers OCR
	// detection only, up through the "detected" NDJSON message — no regions
	// exist yet, so the canvas/sidebar stay in their blocking loading state.
	// 'enriching' begins the moment "detected" arrives: regions are visible,
	// selectable, and editable (see commitEdit/nudgeRegion/applyOverride's
	// wait-for-enrichment below), while exact font matching continues in the
	// background — the UI shows a small non-blocking progress indicator
	// instead of the full loading overlay. 'idle' is reached only once the
	// final "result" message lands.
	status: 'idle' | 'uploading' | 'analyzing' | 'enriching' | 'error';
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
	// Used only for the "detected" message: replaces the whole region list
	// with fresh, unenriched stubs (enrichmentStatus: 'pending'). Never used
	// once enrichment has started — see upsertRegion for that.
	setRegions: (regions: Region[]) => void;
	// Applies one completed enrichment result: merges it into the existing
	// region with the same id (added by setRegions from the "detected"
	// message) — preserving whatever the user has already done to it
	// (edited text, nudged position, or an explicit style override) rather
	// than overwriting those with the backend's stale, pre-edit values — or
	// appends it if no id matches yet. Always leaves the region
	// enrichmentStatus: 'ready' and resolves any commitEdit/nudgeRegion/
	// applyOverride call currently waiting on this region id. Used for both
	// the "region" NDJSON message (as each line's enrichment finishes) and,
	// per region, the final "result" message. See Dropzone.handleFile.
	upsertRegion: (region: Region) => void;
	// Marks every region still 'pending' as 'failed' and rejects any
	// commitEdit/nudgeRegion/applyOverride call currently waiting on one of
	// them, rather than leaving it hanging forever — called when the
	// /api/analyze stream ends in error, or completes without ever
	// resolving some region (defensive; shouldn't happen in practice since
	// the final "result" message reconciles every region).
	markPendingRegionsFailed: (message: string) => void;
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
	setEditingSelection: (range: { start: number; end: number } | null) => void;
	// Splits a region into adjacent regions at fragment boundaries and gives
	// each fragment its own style — how the editor supports mixing styles
	// within what was one detected text region (see FontOverridePanel's
	// selection mode). `fragments` must already be in left-to-right order and
	// carry their own measured widths (native image-pixel space) and, for
	// whichever fragment(s) the user restyled, the style to apply; a fragment
	// with no override just carries the source region's existing style
	// forward. No-ops if fewer than two fragments have non-empty text — that
	// isn't a split.
	applyStyleToSelection: (regionId: string, fragments: StyleFragment[]) => Promise<void>;
	// Steps one entry back/forward through past/future, restoring that
	// snapshot's regions+edits and re-rendering against it. No-op if there's
	// nothing to undo/redo.
	undo: () => Promise<void>;
	redo: () => Promise<void>;
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

	// Resolved/rejected by upsertRegion (real enrichment arriving) or
	// markPendingRegionsFailed (the stream ending without it) — see
	// waitForEnrichedRegion. Keyed by region id; a given id can have more
	// than one waiter if the user re-commits the same region before the
	// first commit's wait has resolved.
	const enrichmentWaiters = new Map<string, Array<{ resolve: (region: Region) => void; reject: (err: Error) => void }>>();

	function resolveEnrichmentWaiters(id: string, region: Region) {
		const waiters = enrichmentWaiters.get(id);
		if (!waiters) return;
		enrichmentWaiters.delete(id);
		for (const waiter of waiters) waiter.resolve(region);
	}

	function rejectEnrichmentWaiters(id: string, message: string) {
		const waiters = enrichmentWaiters.get(id);
		if (!waiters) return;
		enrichmentWaiters.delete(id);
		for (const waiter of waiters) waiter.reject(new Error(message));
	}

	// The wait-for-exact-style gate: commitEdit/nudgeRegion/applyOverride all
	// call this before touching /render. Resolves immediately if the region
	// is already enriched; rejects immediately if it already failed;
	// otherwise queues on enrichmentWaiters until upsertRegion or
	// markPendingRegionsFailed settles it. Never falls back to a default
	// style — a caller that gets a rejection must surface an error, not
	// render anyway (see commitEdit/nudgeRegion/applyOverride below).
	function waitForEnrichedRegion(id: string): Promise<Region> {
		const region = get().regions.find((r) => r.id === id);
		if (!region) return Promise.reject(new Error('this region no longer exists'));
		if (region.enrichmentStatus === 'ready') return Promise.resolve(region);
		if (region.enrichmentStatus === 'failed') {
			return Promise.reject(new Error("could not determine this region's exact style"));
		}
		return new Promise((resolve, reject) => {
			const waiters = enrichmentWaiters.get(id) ?? [];
			waiters.push({ resolve, reject });
			enrichmentWaiters.set(id, waiters);
		});
	}

	// Applies one completed enrichment result on top of whatever the region
	// currently holds, rather than replacing it outright — the incoming
	// payload reflects the pristine OCR text/position (the backend has no
	// idea the user may have already edited or nudged this region while its
	// enrichment was still in flight), and if the user already applied an
	// explicit style override, that deliberate choice must win over the
	// automatic match arriving late.
	function mergeEnrichedRegion(current: Region, incoming: Region): Region {
		const styleFields = current.styleOverridden
			? {
					fontFamily: current.fontFamily,
					fontWeight: current.fontWeight,
					fontSize: current.fontSize,
					fontSizeHint: current.fontSizeHint,
					letterSpacing: current.letterSpacing,
					textColor: current.textColor,
					alignment: current.alignment,
				}
			: {
					fontFamily: incoming.fontFamily,
					fontWeight: incoming.fontWeight,
					fontSize: incoming.fontSize,
					fontSizeHint: incoming.fontSizeHint,
					letterSpacing: incoming.letterSpacing,
					textColor: incoming.textColor,
					alignment: incoming.alignment,
				};
		return {
			...incoming,
			...styleFields,
			text: current.text,
			offsetX: current.offsetX,
			offsetY: current.offsetY,
			styleOverridden: current.styleOverridden,
			enrichmentStatus: 'ready',
		};
	}

	function pendingEditFor(region: Region, text: string, overrides?: StyleOverride): PendingEdit {
		// The ?? fallbacks below are a defensive safety net for genuine data
		// edge cases (e.g. an empty crop the backend itself couldn't fit a
		// color to), not a routine path: every caller of pendingEditFor first
		// awaits waitForEnrichedRegion, so by the time this runs the region's
		// machine-owned fields are already populated from a real MatchResult.
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

	// A gradient background is fit and re-normalized per-region server-side
	// (see docs/pipeline-tuning.md) — reusing one gradient BackgroundFill
	// across several narrower split-fragment bboxes would redraw the *entire*
	// gradient inside each fragment and produce a hard seam at every split
	// point. Approximating each fragment as a flat color, sampled from the
	// original gradient at the fragment's horizontal center, sidesteps that;
	// exact continuous-gradient-across-fragments rendering isn't supported.
	function flattenBackgroundForFragment(
		background: BackgroundFill | null,
		fragmentBbox: [number, number, number, number],
		originalBbox: [number, number, number, number],
	): BackgroundFill | null {
		if (!background || background.kind !== 'gradient' || background.stops.length === 0) return background;
		const fragmentCenterX = fragmentBbox[0] + fragmentBbox[2] / 2;
		const t = originalBbox[2] > 0 ? (fragmentCenterX - originalBbox[0]) / originalBbox[2] : 0;
		const clampedT = Math.max(0, Math.min(1, t));
		return { kind: 'flat', color: interpolateGradientColor(background.stops, clampedT), angleDeg: null, stops: [] };
	}

	function interpolateGradientColor(stops: GradientStop[], t: number): RgbColor {
		const sorted = [...stops].sort((a, b) => a.position - b.position);
		let lower = sorted[0];
		let upper = sorted[sorted.length - 1];
		for (let i = 0; i < sorted.length - 1; i++) {
			if (t >= sorted[i].position && t <= sorted[i + 1].position) {
				lower = sorted[i];
				upper = sorted[i + 1];
				break;
			}
		}
		const span = upper.position - lower.position;
		const localT = span > 0 ? (t - lower.position) / span : 0;
		const mix = (a: number, b: number) => Math.round(a + (b - a) * localT);
		return [mix(lower.color[0], upper.color[0]), mix(lower.color[1], upper.color[1]), mix(lower.color[2], upper.color[2])];
	}

	// Called by commitEdit/nudgeRegion/applyOverride right before they touch
	// regions/edits, so `past`'s top entry is always "state right before this
	// action" — not the result of it. Starting a fresh action always clears
	// `future`: redoing a branch abandoned by a new edit isn't supported.
	function pushHistory() {
		const state = get();
		const entry: HistorySnapshot = { regions: state.regions, edits: state.edits };
		set({ past: [...state.past, entry].slice(-MAX_UNDO_STEPS), future: [] });
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
		editingSelection: null,
		edits: {},
		past: [],
		future: [],
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
				editingSelection: null,
				edits: {},
				past: [],
				future: [],
				uploadProgress: 0,
				analyzeProgress: null,
			}),
		setRegions: (regions) => set({ regions }),
		upsertRegion: (incoming) => {
			const state = get();
			const index = state.regions.findIndex((r) => r.id === incoming.id);
			const merged: Region = index === -1 ? { ...incoming, enrichmentStatus: 'ready' } : mergeEnrichedRegion(state.regions[index], incoming);
			set({
				regions: index === -1 ? [...state.regions, merged] : state.regions.map((r, i) => (i === index ? merged : r)),
			});
			// After the state update commits, so any waiter's continuation sees
			// the merged region already reflected in the store.
			resolveEnrichmentWaiters(incoming.id, merged);
		},
		markPendingRegionsFailed: (message) => {
			const state = get();
			const pendingIds = state.regions.filter((r) => r.enrichmentStatus === 'pending').map((r) => r.id);
			if (pendingIds.length === 0) return;
			set({
				regions: state.regions.map((r) => (r.enrichmentStatus === 'pending' ? { ...r, enrichmentStatus: 'failed' as const } : r)),
			});
			for (const id of pendingIds) rejectEnrichmentWaiters(id, message);
		},
		setScaleFactor: (scaleFactor) => set({ scaleFactor }),
		setUploadProgress: (percent) => set({ uploadProgress: percent }),
		setAnalyzeProgress: (current, total) => set({ analyzeProgress: { current, total } }),
		selectRegion: (id) => set({ selectedRegionId: id }),
		startEditing: (id) =>
			set({ selectedRegionId: id, editingRegionId: id, overridePanelRegionId: null, editingSelection: null, renderError: null }),
		startEditingWithStyle: (id) =>
			set({ selectedRegionId: id, editingRegionId: id, overridePanelRegionId: id, editingSelection: null, renderError: null }),
		cancelEditing: () => set({ editingRegionId: null, editingSelection: null }),
		setEditingSelection: (range) => set({ editingSelection: range }),
		commitEdit: async (id, newText) => {
			const state = get();
			const region = state.regions.find((r) => r.id === id);
			if (!region || !state.imageFile) {
				set({ editingRegionId: null, editingSelection: null });
				return;
			}
			if (newText === region.text) {
				set({ editingRegionId: null, editingSelection: null });
				return;
			}

			pushHistory();

			// Optimistic text update happens immediately, regardless of
			// enrichment state, so the canvas/sidebar reflect the edit right
			// away — only the actual /render call (which needs the exact
			// MatchResult) waits.
			set({
				editingRegionId: null,
				editingSelection: null,
				regions: state.regions.map((r) => (r.id === id ? { ...r, text: newText } : r)),
			});

			let ready: Region;
			try {
				ready = await waitForEnrichedRegion(id);
			} catch (err) {
				set({ renderError: err instanceof Error ? err.message : "could not determine this region's exact style" });
				return;
			}
			// Re-read edits fresh: other regions may have committed while this
			// one was waiting on its own enrichment.
			await postRender({ ...get().edits, [id]: pendingEditFor(ready, ready.text) });
		},
		nudgeRegion: async (id, dx, dy) => {
			const state = get();
			const region = state.regions.find((r) => r.id === id);
			if (!region || !state.imageFile) return;

			pushHistory();

			const clamp = (v: number) => Math.max(-MAX_NUDGE_PX, Math.min(MAX_NUDGE_PX, v));
			const optimistic: Region = { ...region, offsetX: clamp(region.offsetX + dx), offsetY: clamp(region.offsetY + dy) };
			set({ regions: state.regions.map((r) => (r.id === id ? optimistic : r)) });

			let ready: Region;
			try {
				ready = await waitForEnrichedRegion(id);
			} catch (err) {
				set({ renderError: err instanceof Error ? err.message : "could not determine this region's exact style" });
				return;
			}
			await postRender({ ...get().edits, [id]: pendingEditFor(ready, ready.text) });
		},
		openOverridePanel: (id) => set({ overridePanelRegionId: id, editingRegionId: null, selectedRegionId: id }),
		closeOverridePanel: () => set({ overridePanelRegionId: null }),
		applyOverride: async (id, overrides) => {
			const state = get();
			const region = state.regions.find((r) => r.id === id);
			if (!region || !state.imageFile) return;

			pushHistory();

			const optimistic: Region = { ...region, ...overrides, styleOverridden: true };
			set({ regions: state.regions.map((r) => (r.id === id ? optimistic : r)) });

			let ready: Region;
			try {
				ready = await waitForEnrichedRegion(id);
			} catch (err) {
				set({ renderError: err instanceof Error ? err.message : "could not determine this region's exact style" });
				return;
			}
			await postRender({ ...get().edits, [id]: pendingEditFor(ready, ready.text, overrides) });
		},
		applyStyleToSelection: async (regionId, fragments) => {
			const state = get();
			const region = state.regions.find((r) => r.id === regionId);
			const nonEmpty = fragments.filter((f) => f.text.length > 0);
			// Fewer than two non-empty fragments isn't a split — nothing to do
			// (the caller should fall back to a whole-region applyOverride).
			if (!region || !state.imageFile || nonEmpty.length < 2) return;

			// Unlike commitEdit/nudgeRegion/applyOverride, this waits for
			// enrichment *before* mutating state: a fragment's bbox is derived
			// from the caller's measured widths, which were measured against the
			// region's current (possibly still-pending, soon-to-change) font —
			// splitting first and re-measuring later would mean either doing the
			// split twice or leaving fragments sized for the wrong font.
			let ready: Region;
			try {
				ready = await waitForEnrichedRegion(regionId);
			} catch (err) {
				set({ renderError: err instanceof Error ? err.message : "could not determine this region's exact style" });
				return;
			}

			pushHistory();

			const FRAGMENT_GAP_PX = 2; // see docs/pipeline-tuning.md: server crop padding is 3px per side, so touching bboxes can double-process a shared seam without a small gap
			const [rx, ry, , rh] = ready.bbox;
			let cursorX = rx;
			const newFragmentRegions: Region[] = nonEmpty.map((fragment) => {
				const width = Math.max(1, fragment.widthPx);
				const bbox: [number, number, number, number] = [cursorX, ry, width, rh];
				cursorX += width + FRAGMENT_GAP_PX;
				return {
					...ready,
					...fragment.overrides,
					id: crypto.randomUUID(),
					text: fragment.text,
					bbox,
					// The source region's per-character OCR boxes don't correspond
					// to this fragment's substring/geometry — drop them rather than
					// show misleading marks in the debug overlay (see Canvas.tsx's
					// debugMode rendering of region.chars).
					chars: [],
					// Left-align every fragment regardless of the source region's
					// alignment — center/right anchor text relative to the
					// fragment's own bbox width server-side, which would drift
					// adjacent fragments apart (see docs/pipeline-tuning.md).
					alignment: 'left',
					// null, not ready.xOffset: the source region's fitted text
					// anchor was calibrated for its own (wider) bbox. pendingEditFor
					// falls back to a region's own bbox[0] when xOffset is null —
					// exactly "start drawing at this fragment's own left edge",
					// which is what a left-aligned single-line fragment needs.
					xOffset: null,
					background: flattenBackgroundForFragment(ready.background, bbox, ready.bbox),
					styleOverridden: fragment.overrides != null ? true : ready.styleOverridden,
				};
			});

			set({
				regions: get().regions.flatMap((r) => (r.id === regionId ? newFragmentRegions : [r])),
				editingRegionId: null,
				overridePanelRegionId: null,
				editingSelection: null,
			});

			// Every fragment needs its own edit entry — even one that kept the
			// source region's exact style — because the fragments' combined
			// bboxes are replacing the single original bbox area; leaving one
			// fragment un-edited would leave that slice showing stale pixels
			// from the pre-split single-box render.
			const nextEdits = { ...get().edits };
			delete nextEdits[regionId];
			for (const fragment of newFragmentRegions) {
				nextEdits[fragment.id] = pendingEditFor(fragment, fragment.text);
			}
			await postRender(nextEdits);
		},
		undo: async () => {
			const state = get();
			const previous = state.past[state.past.length - 1];
			if (!previous) return;
			const currentSnapshot: HistorySnapshot = { regions: state.regions, edits: state.edits };
			set({
				regions: previous.regions,
				past: state.past.slice(0, -1),
				future: [currentSnapshot, ...state.future].slice(0, MAX_UNDO_STEPS),
				editingRegionId: null,
				overridePanelRegionId: null,
				editingSelection: null,
				renderError: null,
			});
			await postRender(previous.edits);
		},
		redo: async () => {
			const state = get();
			const next = state.future[0];
			if (!next) return;
			const currentSnapshot: HistorySnapshot = { regions: state.regions, edits: state.edits };
			set({
				regions: next.regions,
				past: [...state.past, currentSnapshot].slice(-MAX_UNDO_STEPS),
				future: state.future.slice(1),
				editingRegionId: null,
				overridePanelRegionId: null,
				editingSelection: null,
				renderError: null,
			});
			await postRender(next.edits);
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
				editingSelection: null,
				edits: {},
				past: [],
				future: [],
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
