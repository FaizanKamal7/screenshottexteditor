import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { useEditorStore, type Region } from './store';

// Each test uses a unique region id (a fresh counter suffix) so leftover
// enrichmentWaiters/state from one test can never bleed into another via
// the store's module-level singleton.
let idCounter = 0;
function nextId(label: string): string {
	idCounter += 1;
	return `${label}-${idCounter}`;
}

function makeRegion(id: string, overrides: Partial<Region> = {}): Region {
	return {
		id,
		text: 'Original',
		bbox: [10, 20, 100, 30],
		blockId: 'block-1',
		chars: [],
		script: 'latin',
		direction: 'ltr',
		confidence: 0.9,
		matchMargin: null,
		alphaMaskPng: null,
		fontFamily: null,
		fontWeight: null,
		fontSize: null,
		fontSizeHint: null,
		letterSpacing: 0,
		baselineY: null,
		xOffset: null,
		textColor: null,
		background: null,
		alignment: 'left',
		lineHeight: null,
		uiElement: null,
		fontCandidates: [],
		offsetX: 0,
		offsetY: 0,
		enrichmentStatus: 'pending',
		styleOverridden: false,
		...overrides,
	};
}

function enrichedFieldsFor(id: string, overrides: Partial<Region> = {}): Region {
	return makeRegion(id, {
		fontFamily: 'Roboto',
		fontWeight: 500,
		fontSize: 18,
		letterSpacing: 0.2,
		baselineY: 24,
		xOffset: 12,
		textColor: [10, 20, 30],
		background: { kind: 'flat', color: [255, 255, 255], angleDeg: null, stops: [] },
		enrichmentStatus: 'ready',
		...overrides,
	});
}

const fakeImageFile = new File(['fake'], 'shot.png', { type: 'image/png' });

beforeEach(() => {
	useEditorStore.getState().reset();
	useEditorStore.setState({ imageFile: fakeImageFile, imageUrl: 'blob:fake' });
	vi.stubGlobal(
		'fetch',
		vi.fn(async () => ({
			ok: true,
			json: async () => ({ image_png_base64: 'abc', results: [] }),
		})),
	);
});

afterEach(() => {
	vi.unstubAllGlobals();
});

describe('setRegions / detected stub', () => {
	it('starts every region as pending, not silently looking enriched', () => {
		const id = nextId('detected');
		useEditorStore.getState().setRegions([makeRegion(id)]);
		const region = useEditorStore.getState().regions.find((r) => r.id === id);
		expect(region?.enrichmentStatus).toBe('pending');
		expect(region?.fontFamily).toBeNull();
	});
});

describe('commitEdit waits for real enrichment before rendering', () => {
	it('does not call /render while the region is still pending', async () => {
		const id = nextId('commit-pending');
		useEditorStore.getState().setRegions([makeRegion(id)]);

		// commitEdit is async and awaits enrichment internally — start it but
		// don't await yet, so we can assert nothing rendered in the meantime.
		const commitPromise = useEditorStore.getState().commitEdit(id, 'Edited text');
		await Promise.resolve(); // let the optimistic-update microtask run
		await Promise.resolve();

		expect(fetch).not.toHaveBeenCalled();

		// Now the region's real enrichment arrives.
		useEditorStore.getState().upsertRegion(enrichedFieldsFor(id));
		await commitPromise;

		expect(fetch).toHaveBeenCalledTimes(1);
		const body = (fetch as unknown as ReturnType<typeof vi.fn>).mock.calls[0][1].body as FormData;
		const edits = JSON.parse(body.get('edits') as string);
		expect(edits[0].font_family).toBe('Roboto');
		expect(edits[0].font_size).toBe(18);
		expect(edits[0].text).toBe('Edited text');
	});

	it('renders immediately (no wait) when the region is already enriched', async () => {
		const id = nextId('commit-ready');
		useEditorStore.getState().setRegions([enrichedFieldsFor(id)]);

		await useEditorStore.getState().commitEdit(id, 'Edited text');

		expect(fetch).toHaveBeenCalledTimes(1);
		const body = (fetch as unknown as ReturnType<typeof vi.fn>).mock.calls[0][1].body as FormData;
		const edits = JSON.parse(body.get('edits') as string);
		expect(edits[0].font_family).toBe('Roboto');
	});

	it('never falls back to default styling for a pending region', async () => {
		// Regression test for the exact bug this change fixes: previously
		// pendingEditFor's ?? fallbacks meant an edit on an unenriched region
		// rendered with generic Inter/400/16/black instead of waiting.
		const id = nextId('commit-no-fallback');
		useEditorStore.getState().setRegions([makeRegion(id)]);

		const commitPromise = useEditorStore.getState().commitEdit(id, 'Edited text');
		await Promise.resolve();
		await Promise.resolve();
		await Promise.resolve();

		expect(fetch).not.toHaveBeenCalled();
		useEditorStore.getState().upsertRegion(enrichedFieldsFor(id, { fontFamily: 'Noto Sans', fontSize: 22 }));
		await commitPromise;

		const body = (fetch as unknown as ReturnType<typeof vi.fn>).mock.calls[0][1].body as FormData;
		const edits = JSON.parse(body.get('edits') as string);
		// Must be the real matched font, never the 'Inter'/16 fallback.
		expect(edits[0].font_family).toBe('Noto Sans');
		expect(edits[0].font_size).toBe(22);
	});
});

describe('multiple regions enrich independently', () => {
	it('resolving region A does not resolve or affect region B', async () => {
		const idA = nextId('multi-a');
		const idB = nextId('multi-b');
		useEditorStore.getState().setRegions([makeRegion(idA), makeRegion(idB)]);

		const commitA = useEditorStore.getState().commitEdit(idA, 'A edited');
		const commitB = useEditorStore.getState().commitEdit(idB, 'B edited');
		await Promise.resolve();
		await Promise.resolve();

		expect(fetch).not.toHaveBeenCalled();

		// Only A's enrichment arrives — A's own wait resolves and renders
		// immediately, independent of B, which must remain untouched.
		useEditorStore.getState().upsertRegion(enrichedFieldsFor(idA, { fontFamily: 'Inter' }));
		await commitA;

		expect(fetch).toHaveBeenCalledTimes(1);
		const firstBody = (fetch as unknown as ReturnType<typeof vi.fn>).mock.calls[0][1].body as FormData;
		expect(JSON.parse(firstBody.get('edits') as string)[0].region_id).toBe(idA);
		expect(useEditorStore.getState().regions.find((r) => r.id === idB)?.enrichmentStatus).toBe('pending');

		useEditorStore.getState().upsertRegion(enrichedFieldsFor(idB, { fontFamily: 'Roboto' }));
		await commitB;

		expect(fetch).toHaveBeenCalledTimes(2);
	});

	it('a stale/out-of-order enrichment for region A cannot resolve region B\'s wait', async () => {
		const idA = nextId('stale-a');
		const idB = nextId('stale-b');
		useEditorStore.getState().setRegions([makeRegion(idA), makeRegion(idB)]);

		const commitB = useEditorStore.getState().commitEdit(idB, 'B edited');
		await Promise.resolve();

		// Enrichment arrives for A only — B must remain pending.
		useEditorStore.getState().upsertRegion(enrichedFieldsFor(idA));
		await Promise.resolve();
		await Promise.resolve();

		expect(useEditorStore.getState().regions.find((r) => r.id === idB)?.enrichmentStatus).toBe('pending');
		expect(fetch).not.toHaveBeenCalled();

		useEditorStore.getState().upsertRegion(enrichedFieldsFor(idB));
		await commitB;
		expect(fetch).toHaveBeenCalledTimes(1);
		const body = (fetch as unknown as ReturnType<typeof vi.fn>).mock.calls[0][1].body as FormData;
		const edits = JSON.parse(body.get('edits') as string);
		expect(edits[0].region_id).toBe(idB);
	});
});

describe('enrichment failure', () => {
	it('markPendingRegionsFailed rejects a waiting commitEdit instead of hanging or falling back', async () => {
		const id = nextId('failed');
		useEditorStore.getState().setRegions([makeRegion(id)]);

		const commitPromise = useEditorStore.getState().commitEdit(id, 'Edited text');
		await Promise.resolve();
		await Promise.resolve();

		useEditorStore.getState().markPendingRegionsFailed('analyze request failed');
		await commitPromise;

		expect(fetch).not.toHaveBeenCalled();
		expect(useEditorStore.getState().regions.find((r) => r.id === id)?.enrichmentStatus).toBe('failed');
		expect(useEditorStore.getState().renderError).toBeTruthy();
	});
});

describe('upsertRegion merges rather than replaces', () => {
	it('preserves an in-flight text edit and nudge offset against a late-arriving enrichment message', () => {
		const id = nextId('merge-preserve');
		useEditorStore.getState().setRegions([makeRegion(id)]);
		useEditorStore.setState((s) => ({
			regions: s.regions.map((r) => (r.id === id ? { ...r, text: 'User edited', offsetX: 5, offsetY: -3 } : r)),
		}));

		// Backend enrichment message reflects the pristine OCR text/no offset —
		// it has no idea about the user's in-flight edit/nudge.
		useEditorStore.getState().upsertRegion(enrichedFieldsFor(id, { text: 'Original', offsetX: 0, offsetY: 0 }));

		const region = useEditorStore.getState().regions.find((r) => r.id === id);
		expect(region?.text).toBe('User edited');
		expect(region?.offsetX).toBe(5);
		expect(region?.offsetY).toBe(-3);
		expect(region?.fontFamily).toBe('Roboto'); // style fields do come from the incoming message
		expect(region?.enrichmentStatus).toBe('ready');
	});

	it('preserves a user style override against a late-arriving automatic match', async () => {
		const id = nextId('merge-override');
		useEditorStore.getState().setRegions([makeRegion(id)]);

		const overridePromise = useEditorStore.getState().applyOverride(id, {
			fontFamily: 'Liberation Sans',
			fontWeight: 700,
			fontSize: 30,
			letterSpacing: 1,
			textColor: [1, 2, 3],
			alignment: 'center',
		});
		await Promise.resolve();

		// The automatic matcher's result finally arrives — with a *different*
		// font — after the user already chose their own.
		useEditorStore.getState().upsertRegion(enrichedFieldsFor(id, { fontFamily: 'Noto Sans', fontWeight: 400 }));
		await overridePromise;

		const region = useEditorStore.getState().regions.find((r) => r.id === id);
		expect(region?.fontFamily).toBe('Liberation Sans'); // user's override wins
		expect(region?.fontWeight).toBe(700);
		expect(region?.baselineY).toBe(24); // geometry still comes from the real match
		expect(fetch).toHaveBeenCalledTimes(1);
	});
});

describe('undo/redo', () => {
	it('reverts the last commitEdit and lets redo bring it back', async () => {
		const id = nextId('undo-commit');
		useEditorStore.getState().setRegions([enrichedFieldsFor(id)]);

		await useEditorStore.getState().commitEdit(id, 'Edited text');
		expect(useEditorStore.getState().regions.find((r) => r.id === id)?.text).toBe('Edited text');
		expect(fetch).toHaveBeenCalledTimes(1);

		await useEditorStore.getState().undo();
		expect(useEditorStore.getState().regions.find((r) => r.id === id)?.text).toBe('Original');
		expect(fetch).toHaveBeenCalledTimes(2);
		const undoBody = (fetch as unknown as ReturnType<typeof vi.fn>).mock.calls[1][1].body as FormData;
		expect(JSON.parse(undoBody.get('edits') as string)).toEqual([]);

		await useEditorStore.getState().redo();
		expect(useEditorStore.getState().regions.find((r) => r.id === id)?.text).toBe('Edited text');
		expect(fetch).toHaveBeenCalledTimes(3);
	});

	it('are no-ops with nothing to step to', async () => {
		const id = nextId('undo-noop');
		useEditorStore.getState().setRegions([enrichedFieldsFor(id)]);

		await useEditorStore.getState().undo();
		expect(fetch).not.toHaveBeenCalled();

		await useEditorStore.getState().redo();
		expect(fetch).not.toHaveBeenCalled();
	});

	it('a fresh edit after undo abandons the redo branch', async () => {
		const id = nextId('undo-branch');
		useEditorStore.getState().setRegions([enrichedFieldsFor(id)]);

		await useEditorStore.getState().commitEdit(id, 'First edit');
		await useEditorStore.getState().undo();
		expect(useEditorStore.getState().future.length).toBe(1);

		await useEditorStore.getState().commitEdit(id, 'Second edit');
		expect(useEditorStore.getState().future.length).toBe(0);

		await useEditorStore.getState().redo();
		expect(useEditorStore.getState().regions.find((r) => r.id === id)?.text).toBe('Second edit');
	});

	it('keeps only the last 5 steps', async () => {
		const id = nextId('undo-cap');
		useEditorStore.getState().setRegions([enrichedFieldsFor(id)]);

		for (let i = 1; i <= 6; i++) {
			await useEditorStore.getState().commitEdit(id, `Edit ${i}`);
		}

		expect(useEditorStore.getState().past.length).toBe(5);
	});
});

describe('nudgeRegion waits for enrichment the same way', () => {
	it('does not render a nudge until the region is enriched', async () => {
		const id = nextId('nudge');
		useEditorStore.getState().setRegions([makeRegion(id)]);

		const nudgePromise = useEditorStore.getState().nudgeRegion(id, 4, -2);
		await Promise.resolve();
		expect(fetch).not.toHaveBeenCalled();

		useEditorStore.getState().upsertRegion(enrichedFieldsFor(id));
		await nudgePromise;

		expect(fetch).toHaveBeenCalledTimes(1);
		const region = useEditorStore.getState().regions.find((r) => r.id === id);
		expect(region?.offsetX).toBe(4);
		expect(region?.offsetY).toBe(-2);
	});
});

describe('applyStyleToSelection splits a region into independently styled fragments', () => {
	it('splits prefix/middle/suffix, styling only the middle fragment', async () => {
		const id = nextId('split-3way');
		useEditorStore.getState().setRegions([enrichedFieldsFor(id, { text: 'Hello World Test', bbox: [10, 20, 150, 30] })]);

		await useEditorStore.getState().applyStyleToSelection(id, [
			{ text: 'Hello ', widthPx: 40 },
			{
				text: 'World',
				widthPx: 50,
				overrides: { fontFamily: 'Noto Sans', fontWeight: 700, fontSize: 22, letterSpacing: 1, textColor: [9, 9, 9], alignment: 'center' },
			},
			{ text: ' Test', widthPx: 45 },
		]);

		const regions = useEditorStore.getState().regions;
		expect(regions.find((r) => r.id === id)).toBeUndefined(); // original region is gone
		expect(regions).toHaveLength(3);
		expect(regions.map((r) => r.text)).toEqual(['Hello ', 'World', ' Test']);

		// bbox: same y/h as the source region, x accumulated left-to-right with a
		// small gap between fragments so the server's crop padding can't overlap.
		expect(regions[0].bbox).toEqual([10, 20, 40, 30]);
		expect(regions[1].bbox).toEqual([10 + 40 + 2, 20, 50, 30]);
		expect(regions[2].bbox).toEqual([10 + 40 + 2 + 50 + 2, 20, 45, 30]);

		// Only the middle fragment got the override; alignment is forced left on
		// every fragment (server rendering constraint), even though the override
		// asked for 'center'.
		expect(regions[0].fontFamily).toBe('Roboto');
		expect(regions[0].styleOverridden).toBe(false);
		expect(regions[0].alignment).toBe('left');
		expect(regions[1].fontFamily).toBe('Noto Sans');
		expect(regions[1].fontWeight).toBe(700);
		expect(regions[1].styleOverridden).toBe(true);
		expect(regions[1].alignment).toBe('left');
		expect(regions[2].fontFamily).toBe('Roboto');
		expect(regions[2].styleOverridden).toBe(false);

		// Every fragment gets its own edit — even the ones that kept the
		// original style — because together they replace the single original
		// bbox area.
		expect(fetch).toHaveBeenCalledTimes(1);
		const body = (fetch as unknown as ReturnType<typeof vi.fn>).mock.calls[0][1].body as FormData;
		const edits = JSON.parse(body.get('edits') as string);
		expect(edits).toHaveLength(3);
		expect(edits.map((e: { region_id: string }) => e.region_id)).toEqual(regions.map((r) => r.id));
		expect(edits.find((e: { text: string }) => e.text === 'World').font_family).toBe('Noto Sans');
	});

	it('splits into two fragments when the selection touches an edge', async () => {
		const id = nextId('split-2way');
		useEditorStore.getState().setRegions([enrichedFieldsFor(id, { text: 'World Test', bbox: [0, 0, 100, 20] })]);

		await useEditorStore.getState().applyStyleToSelection(id, [
			{ text: '', widthPx: 0 },
			{ text: 'World', widthPx: 50, overrides: { fontFamily: 'Noto Sans', fontWeight: 700, fontSize: 22, letterSpacing: 1, textColor: [1, 2, 3], alignment: 'left' } },
			{ text: ' Test', widthPx: 45 },
		]);

		const regions = useEditorStore.getState().regions;
		expect(regions).toHaveLength(2);
		expect(regions.map((r) => r.text)).toEqual(['World', ' Test']);
	});

	it('is a no-op when the selection covers the whole region (nothing to split)', async () => {
		const id = nextId('split-noop');
		useEditorStore.getState().setRegions([enrichedFieldsFor(id, { text: 'Solo' })]);

		await useEditorStore.getState().applyStyleToSelection(id, [
			{ text: '', widthPx: 0 },
			{ text: 'Solo', widthPx: 40, overrides: { fontFamily: 'Noto Sans', fontWeight: 700, fontSize: 22, letterSpacing: 1, textColor: [1, 2, 3], alignment: 'left' } },
			{ text: '', widthPx: 0 },
		]);

		expect(fetch).not.toHaveBeenCalled();
		const regions = useEditorStore.getState().regions;
		expect(regions).toHaveLength(1);
		expect(regions[0].id).toBe(id);
	});

	it('approximates a gradient background as a flat color per fragment, sampled at its center', async () => {
		const id = nextId('split-gradient');
		useEditorStore.getState().setRegions([
			enrichedFieldsFor(id, {
				text: 'AB',
				bbox: [0, 0, 100, 20],
				background: {
					kind: 'gradient',
					color: null,
					angleDeg: 0,
					stops: [
						{ position: 0, color: [0, 0, 0] },
						{ position: 1, color: [200, 100, 0] },
					],
				},
			}),
		]);

		await useEditorStore.getState().applyStyleToSelection(id, [
			{ text: 'A', widthPx: 20, overrides: { fontFamily: 'Noto Sans', fontWeight: 700, fontSize: 22, letterSpacing: 1, textColor: [1, 2, 3], alignment: 'left' } },
			{ text: 'B', widthPx: 20 },
		]);

		const regions = useEditorStore.getState().regions;
		expect(regions).toHaveLength(2);
		for (const region of regions) {
			expect(region.background?.kind).toBe('flat');
			expect(region.background?.stops).toEqual([]);
		}
		// Fragment A sits left of fragment B, so it should sample an earlier
		// (darker) point on the gradient than fragment B.
		const [colorA, colorB] = regions.map((r) => r.background?.color?.[0] ?? 0);
		expect(colorA).toBeLessThan(colorB);
	});

	it('lets undo restore the single original region', async () => {
		const id = nextId('split-undo');
		useEditorStore.getState().setRegions([enrichedFieldsFor(id, { text: 'Hello World', bbox: [10, 20, 100, 30] })]);

		await useEditorStore.getState().applyStyleToSelection(id, [
			{ text: 'Hello ', widthPx: 40 },
			{
				text: 'World',
				widthPx: 50,
				overrides: { fontFamily: 'Noto Sans', fontWeight: 700, fontSize: 22, letterSpacing: 1, textColor: [1, 2, 3], alignment: 'left' },
			},
		]);
		expect(useEditorStore.getState().regions).toHaveLength(2);

		await useEditorStore.getState().undo();

		const regions = useEditorStore.getState().regions;
		expect(regions).toHaveLength(1);
		expect(regions[0].id).toBe(id);
		expect(regions[0].text).toBe('Hello World');
		expect(regions[0].fontFamily).toBe('Roboto');
	});
});
