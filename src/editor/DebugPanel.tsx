import { useEditorStore } from './store';

export function DebugPanel() {
	const debugMode = useEditorStore((s) => s.debugMode);
	const toggleDebugMode = useEditorStore((s) => s.toggleDebugMode);
	const regions = useEditorStore((s) => s.regions);
	const scaleFactor = useEditorStore((s) => s.scaleFactor);
	const imageUrl = useEditorStore((s) => s.imageUrl);

	if (!imageUrl) return null;

	return (
		<div className="absolute right-4 top-4 flex max-h-[calc(100%-2rem)] w-72 flex-col gap-2 rounded-md border border-hairline bg-canvas-elevated p-3 shadow-sm">
			<button
				type="button"
				onClick={toggleDebugMode}
				className="self-start rounded-sm border border-hairline bg-canvas-elevated px-2 py-1 text-xs text-ink"
			>
				{debugMode ? 'Hide' : 'Show'} detection debug
			</button>
			{debugMode && (
				<div className="flex flex-col gap-2 overflow-y-auto">
					<p className="text-faint text-xs">Scale factor: {scaleFactor}x</p>
					{regions.map((region) => (
						<div key={region.id} className="flex flex-col gap-1 rounded-sm border border-hairline p-2">
							<p className="truncate text-xs text-body">{region.text || '(empty)'}</p>
							{region.alphaMaskPng && (
								<img
									src={`data:image/png;base64,${region.alphaMaskPng}`}
									alt={`Alpha mask for "${region.text}"`}
									className="w-full border border-hairline-soft bg-black"
								/>
							)}
							<p className="text-faint text-xs">
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
								<p className="text-faint text-xs">
									{region.alignment}, chars: {region.chars.length}
									{region.uiElement ? ', on UI element' : ''}
								</p>
							</div>
						</div>
					))}
				</div>
			)}
		</div>
	);
}
