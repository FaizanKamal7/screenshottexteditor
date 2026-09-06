import { fireEvent, render, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { Dropzone } from './Dropzone';
import { useEditorStore } from './store';

// Minimal fake XMLHttpRequest that lets a test drive the NDJSON stream
// exactly like the real /api/analyze response: growing responseText via
// repeated onprogress calls, then a final onload. Captured on `window` so
// the test can reach the one instance Dropzone's handleFile creates.
class FakeXHR {
	static instances: FakeXHR[] = [];
	responseText = '';
	status = 200;
	upload = { onprogress: null as ((e: { lengthComputable: boolean; loaded: number; total: number }) => void) | null, onload: null as (() => void) | null };
	onprogress: (() => void) | null = null;
	onload: (() => void) | null = null;
	onerror: (() => void) | null = null;
	open = vi.fn();
	send = vi.fn();

	constructor() {
		FakeXHR.instances.push(this);
	}

	// Test helper: append one NDJSON line and fire the progress handler, the
	// same shape Dropzone.handleFile's xhr.onprogress reads from.
	pushLine(line: string) {
		this.responseText += line + '\n';
		this.onprogress?.();
	}

	finish(status = 200) {
		this.status = status;
		this.onload?.();
	}
}

beforeEach(() => {
	useEditorStore.getState().reset();
	FakeXHR.instances = [];
	vi.stubGlobal('XMLHttpRequest', FakeXHR as unknown as typeof XMLHttpRequest);
	vi.stubGlobal(
		'Image',
		class {
			onload: (() => void) | null = null;
			naturalWidth = 400;
			naturalHeight = 200;
			set src(_v: string) {
				// jsdom doesn't decode images — resolve synchronously as if it loaded.
				queueMicrotask(() => this.onload?.());
			}
		} as unknown as typeof Image,
	);
	if (!URL.createObjectURL) {
		URL.createObjectURL = () => 'blob:fake';
	}
});

afterEach(() => {
	vi.unstubAllGlobals();
});

function selectFile(container: HTMLElement) {
	const input = container.querySelector('input[type="file"]') as HTMLInputElement;
	const file = new File(['fake'], 'shot.png', { type: 'image/png' });
	fireEvent.change(input, { target: { files: [file] } });
}

describe('Dropzone streaming -> store', () => {
	it('"detected" makes the editor usable (status: enriching, regions pending) without waiting for "result"', async () => {
		const { container } = render(<Dropzone />);
		selectFile(container);

		await waitFor(() => expect(FakeXHR.instances.length).toBe(1));
		const xhr = FakeXHR.instances[0];
		xhr.upload.onload?.();

		xhr.pushLine(
			JSON.stringify({
				type: 'detected',
				total: 2,
				regions: [
					{
						id: 'r1',
						text: 'Hello',
						bbox: [0, 0, 10, 10],
						block_id: 'b1',
						chars: [],
						script: 'latin',
						direction: 'ltr',
						confidence: 0.9,
						alpha_mask_png: null,
						font_family: null,
						font_weight: null,
						font_size: null,
						letter_spacing: 0,
						baseline_y: null,
						x_offset: null,
						text_color: null,
						background: null,
						alignment: 'left',
						line_height: null,
						ui_element: null,
						font_candidates: [],
					},
				],
			}),
		);

		await waitFor(() => {
			expect(useEditorStore.getState().status).toBe('enriching');
		});
		const region = useEditorStore.getState().regions.find((r) => r.id === 'r1');
		expect(region).toBeDefined();
		expect(region?.enrichmentStatus).toBe('pending');
		// The final "result" message has NOT arrived yet — status must not be
		// 'idle' or 'analyzing' at this point; the editor is already usable.
		expect(useEditorStore.getState().status).not.toBe('idle');
		expect(useEditorStore.getState().status).not.toBe('analyzing');
	});

	it('final "result" reconciles every region to ready and completes the request', async () => {
		const { container } = render(<Dropzone />);
		selectFile(container);

		await waitFor(() => expect(FakeXHR.instances.length).toBe(1));
		const xhr = FakeXHR.instances[0];
		xhr.upload.onload?.();

		xhr.pushLine(JSON.stringify({ type: 'detected', total: 1, regions: [] }));
		await waitFor(() => expect(useEditorStore.getState().status).toBe('enriching'));

		xhr.pushLine(
			JSON.stringify({
				type: 'result',
				image_width: 100,
				image_height: 100,
				scale_factor: 1,
				regions: [
					{
						id: 'r1',
						text: 'Hello',
						bbox: [0, 0, 10, 10],
						block_id: 'b1',
						chars: [],
						script: 'latin',
						direction: 'ltr',
						confidence: 0.9,
						alpha_mask_png: null,
						font_family: 'Inter',
						font_weight: 400,
						font_size: 16,
						letter_spacing: 0,
						baseline_y: 8,
						x_offset: 0,
						text_color: [0, 0, 0],
						background: null,
						alignment: 'left',
						line_height: null,
						ui_element: null,
						font_candidates: [],
					},
				],
			}),
		);
		xhr.finish(200);

		await waitFor(() => expect(useEditorStore.getState().status).toBe('idle'));
		const region = useEditorStore.getState().regions.find((r) => r.id === 'r1');
		expect(region?.enrichmentStatus).toBe('ready');
		expect(region?.fontFamily).toBe('Inter');
	});

	it('a stream failure marks any still-pending region failed instead of leaving it hanging', async () => {
		const { container } = render(<Dropzone />);
		selectFile(container);

		await waitFor(() => expect(FakeXHR.instances.length).toBe(1));
		const xhr = FakeXHR.instances[0];
		xhr.upload.onload?.();

		xhr.pushLine(
			JSON.stringify({
				type: 'detected',
				total: 1,
				regions: [
					{
						id: 'r1',
						text: 'Hello',
						bbox: [0, 0, 10, 10],
						block_id: 'b1',
						chars: [],
						script: 'latin',
						direction: 'ltr',
						confidence: 0.9,
						alpha_mask_png: null,
						font_family: null,
						font_weight: null,
						font_size: null,
						letter_spacing: 0,
						baseline_y: null,
						x_offset: null,
						text_color: null,
						background: null,
						alignment: 'left',
						line_height: null,
						ui_element: null,
						font_candidates: [],
					},
				],
			}),
		);
		await waitFor(() => expect(useEditorStore.getState().status).toBe('enriching'));

		xhr.finish(500); // server error before any "region"/"result" line

		await waitFor(() => expect(useEditorStore.getState().status).toBe('error'));
		expect(useEditorStore.getState().regions.find((r) => r.id === 'r1')?.enrichmentStatus).toBe('failed');
	});
});
