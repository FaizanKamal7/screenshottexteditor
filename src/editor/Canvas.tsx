import { useEditorStore } from './store';

export function Canvas() {
	const imageUrl = useEditorStore((s) => s.imageUrl);
	const imageWidth = useEditorStore((s) => s.imageWidth);
	const imageHeight = useEditorStore((s) => s.imageHeight);
	const regions = useEditorStore((s) => s.regions);
	const selectedRegionId = useEditorStore((s) => s.selectedRegionId);
	const selectRegion = useEditorStore((s) => s.selectRegion);
	const debugMode = useEditorStore((s) => s.debugMode);

	if (!imageUrl) return null;

	return (
		<div className="h-full w-full overflow-auto bg-canvas p-8">
			<div className="relative inline-block" style={{ width: imageWidth, height: imageHeight }}>
				<img src={imageUrl} width={imageWidth} height={imageHeight} alt="Uploaded screenshot" className="block" />
				{regions.map((region) => {
					const [x, y, w, h] = region.bbox;
					const isSelected = region.id === selectedRegionId;
					return (
						<button
							key={region.id}
							type="button"
							onClick={() => selectRegion(region.id)}
							title={region.text}
							className={`group absolute rounded-sm border transition-colors ${
								isSelected ? 'border-link bg-link/10' : 'border-transparent hover:border-hairline hover:bg-hairline-soft/60'
							}`}
							style={{ left: x, top: y, width: w, height: h }}
						>
							{debugMode &&
								region.chars.map((charBox, index) => (
									<span
										key={index}
										className="absolute top-0 h-full border-l border-warning/70"
										style={{ left: charBox.x - x, width: charBox.w }}
									/>
								))}
						</button>
					);
				})}
			</div>
		</div>
	);
}
