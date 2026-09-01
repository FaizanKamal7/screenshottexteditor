import { useEffect, useMemo, useRef, useState } from 'react';
import { readingOrder } from './Canvas';
import { FontOverridePanel } from './FontOverridePanel';
import { useEditorStore } from './store';
import { confidenceLevel } from './styleHelpers';

const CONFIDENCE_DOT: Record<ReturnType<typeof confidenceLevel>, string> = {
	none: 'bg-link',
	quiet: 'bg-link',
	warning: 'bg-warning',
};

export function LayersPanel() {
	const imageUrl = useEditorStore((s) => s.imageUrl);
	const regions = useEditorStore((s) => s.regions);
	const selectedRegionId = useEditorStore((s) => s.selectedRegionId);
	const status = useEditorStore((s) => s.status);
	const scaleFactor = useEditorStore((s) => s.scaleFactor);
	const debugMode = useEditorStore((s) => s.debugMode);
	const toggleDebugMode = useEditorStore((s) => s.toggleDebugMode);
	const startEditingWithStyle = useEditorStore((s) => s.startEditingWithStyle);
	const overridePanelRegionId = useEditorStore((s) => s.overridePanelRegionId);
	const closeOverridePanel = useEditorStore((s) => s.closeOverridePanel);
	const [query, setQuery] = useState('');
	const listRef = useRef<HTMLDivElement>(null);

	const isAnalyzing = status === 'uploading' || status === 'analyzing';
	const ordered = useMemo(() => readingOrder(regions), [regions]);
	const filtered = useMemo(() => {
		const q = query.trim().toLowerCase();
		if (!q) return ordered;
		return ordered.filter((region) => region.text.toLowerCase().includes(q));
	}, [ordered, query]);

	// Whatever region gets expanded — from a canvas click as much as a
	// sidebar click — scrolls into view here, so a region near the bottom of
	// a long list (or the one just clicked on canvas) is never left off-screen.
	useEffect(() => {
		if (!overridePanelRegionId) return;
		const row = listRef.current?.querySelector<HTMLElement>(`[data-region-id="${overridePanelRegionId}"]`);
		row?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
	}, [overridePanelRegionId]);

	if (!imageUrl) return null;

	return (
		<div className="flex h-full w-full flex-col">
			<div className="border-b border-hairline p-3">
				<p className="text-[13px] font-medium text-ink">
					Detected text {!isAnalyzing && <span className="text-faint">({regions.length})</span>}
				</p>
				<input
					type="search"
					value={query}
					onChange={(e) => setQuery(e.target.value)}
					placeholder="Search detected text…"
					disabled={isAnalyzing}
					className="mt-2 w-full rounded-md border border-hairline bg-canvas px-2.5 py-1.5 text-[13px] text-ink placeholder:text-faint focus:border-link focus:outline-none disabled:opacity-50"
				/>
			</div>

			<div ref={listRef} className="flex-1 overflow-y-auto p-2">
				{isAnalyzing ? (
					<div className="flex flex-col gap-2 p-1">
						{[0, 1, 2, 3].map((i) => (
							<div key={i} className="animate-pulse rounded-md border border-hairline bg-hairline-soft/60 p-2.5">
								<div className="h-3 w-3/4 rounded bg-hairline" />
								<div className="mt-2 h-2 w-1/2 rounded bg-hairline" />
							</div>
						))}
					</div>
				) : filtered.length === 0 ? (
					<p className="p-2 text-[13px] text-faint">
						{regions.length === 0 ? 'No text detected in this screenshot.' : 'No matches.'}
					</p>
				) : (
					<ul className="flex flex-col gap-1">
						{filtered.map((region) => {
							const confidence = confidenceLevel(region.confidence);
							const isSelected = region.id === selectedRegionId;
							const isExpanded = region.id === overridePanelRegionId;
							return (
								<li
									key={region.id}
									data-region-id={region.id}
									className={`relative overflow-hidden rounded-lg transition-shadow ${
										isExpanded
											? 'border border-link/25 bg-canvas-elevated shadow-[0_1px_6px_rgba(0,0,0,0.08)]'
											: 'border border-transparent'
									}`}
								>
									{isExpanded && <span className="absolute inset-y-0 left-0 w-[3px] bg-link" aria-hidden="true" />}
									<button
										type="button"
										onClick={() => (isExpanded ? closeOverridePanel() : startEditingWithStyle(region.id))}
										className={`flex w-full items-start gap-2 rounded-lg p-2.5 text-left transition-colors ${
											isExpanded ? 'pl-3.5' : isSelected ? 'bg-hairline-soft/60' : 'hover:bg-hairline-soft/60'
										}`}
									>
										<svg
											viewBox="0 0 16 16"
											className={`mt-0.5 h-3 w-3 shrink-0 transition-transform ${isExpanded ? 'rotate-90 text-link' : 'text-faint'}`}
											fill="none"
										>
											<path d="M6 4l4 4-4 4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
										</svg>
										<div className="min-w-0 flex-1">
											<div className="flex items-start justify-between gap-2">
												<p className={`truncate text-[13px] ${isExpanded ? 'font-medium text-ink' : 'text-ink'}`}>
													{region.text || '(empty)'}
												</p>
												<span
													title={`match confidence: ${region.confidence?.toFixed(2) ?? 'n/a'}`}
													className={`mt-1 h-1.5 w-1.5 shrink-0 rounded-full ${CONFIDENCE_DOT[confidence]}`}
												/>
											</div>
											<p className="mt-0.5 truncate text-[11px] text-faint">
												{region.fontFamily ?? 'no match'}
												{region.fontSize != null ? ` · ${region.fontSize.toFixed(0)}px` : ''}
											</p>
										</div>
									</button>
									{isExpanded && <FontOverridePanel />}
								</li>
							);
						})}
					</ul>
				)}
			</div>

			<div className="border-t border-hairline p-2">
				<button
					type="button"
					onClick={toggleDebugMode}
					className="w-full rounded-sm border border-hairline bg-canvas px-2 py-1.5 text-left text-[12px] text-faint hover:text-body"
				>
					{debugMode ? 'Hide' : 'Show'} detection debug
				</button>
				{debugMode && (
					<div className="mt-2 flex max-h-64 flex-col gap-2 overflow-y-auto">
						<p className="text-[11px] text-faint">Scale factor: {scaleFactor}x</p>
						{regions.map((region) => (
							<div key={region.id} className="flex flex-col gap-1 rounded-sm border border-hairline p-2">
								<p className="truncate text-[11px] text-body">{region.text || '(empty)'}</p>
								{region.alphaMaskPng && (
									<img
										src={`data:image/png;base64,${region.alphaMaskPng}`}
										alt={`Alpha mask for "${region.text}"`}
										className="w-full border border-hairline-soft bg-black"
									/>
								)}
								<p className="text-[11px] text-faint">
									{region.fontFamily ?? 'no match'} {region.fontWeight ?? ''}
									{' - '}
									{region.fontSize != null ? `${region.fontSize.toFixed(1)}px` : 'n/a'}
									{' - score: '}
									{region.confidence != null ? region.confidence.toFixed(2) : 'n/a'}
								</p>
								<div className="flex items-center gap-1">
									{region.textColor && (
										<span
											title={`text: rgb(${region.textColor.join(', ')})`}
											className="h-3 w-3 rounded-sm border border-hairline"
											style={{ backgroundColor: `rgb(${region.textColor.join(',')})` }}
										/>
									)}
									{region.background?.color && (
										<span
											title={`background: rgb(${region.background.color.join(', ')})`}
											className="h-3 w-3 rounded-sm border border-hairline"
											style={{ backgroundColor: `rgb(${region.background.color.join(',')})` }}
										/>
									)}
									<p className="text-[11px] text-faint">
										{region.alignment}, chars: {region.chars.length}
										{region.uiElement ? ', on UI element' : ''}
									</p>
								</div>
							</div>
						))}
					</div>
				)}
			</div>
		</div>
	);
}
