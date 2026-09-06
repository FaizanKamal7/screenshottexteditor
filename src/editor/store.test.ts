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
		alphaMaskPng: null,
		fontFamily: null,
		fontWeight: null,
		fontSize: null,
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
