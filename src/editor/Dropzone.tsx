import { useCallback, useRef, useState, type DragEvent } from 'react';
import { useEditorStore, type Region } from './store';

interface AnalyzeRegion {
	id: string;
	text: string;
	bbox: [number, number, number, number];
	block_id: string;
	script: 'latin';
	direction: 'ltr' | 'rtl';
	confidence: number | null;
}

interface AnalyzeResponse {
	image_width: number;
	image_height: number;
	regions: AnalyzeRegion[];
}

function toRegion(region: AnalyzeRegion): Region {
	return {
		id: region.id,
		text: region.text,
		bbox: region.bbox,
		blockId: region.block_id,
		script: region.script,
		direction: region.direction,
		confidence: region.confidence,
	};
}

export function Dropzone() {
	const setImage = useEditorStore((s) => s.setImage);
	const setRegions = useEditorStore((s) => s.setRegions);
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

			setImage(url, dimensions.width, dimensions.height);
			setStatus('analyzing');

			try {
				const formData = new FormData();
				formData.set('file', file);
				const response = await fetch('/api/analyze', { method: 'POST', body: formData });
				if (!response.ok) {
					throw new Error(`analyze failed with status ${response.status}`);
				}
				const data = (await response.json()) as AnalyzeResponse;
				setRegions(data.regions.map(toRegion));
				setStatus('idle');
			} catch (err) {
				setStatus('error', err instanceof Error ? err.message : 'analyze failed');
			}
		},
		[setImage, setRegions, setStatus],
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
			{status === 'analyzing' && <p className="text-link text-xs">Analyzing…</p>}
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
