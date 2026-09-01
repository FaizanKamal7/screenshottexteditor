import { Canvas } from './Canvas';
import { Dropzone } from './Dropzone';
import { FontOverridePanel } from './FontOverridePanel';
import { Header } from './Header';
import { LayersPanel } from './LayersPanel';
import { useEditorStore } from './store';

interface EditorIslandProps {
	// Set on the demo embedded in marketing pages: bounds the editor to a
	// fixed-height card instead of the full viewport, which is what /app
	// wants, and hides the /app-only header chrome (back-link, New
	// screenshot, Download) since the marketing page already has its own
	// "Try it live" heading around the embed.
	embedded?: boolean;
}

export function EditorIsland({ embedded = false }: EditorIslandProps) {
	const imageUrl = useEditorStore((s) => s.imageUrl);
	const overridePanelRegionId = useEditorStore((s) => s.overridePanelRegionId);

	return (
		<div
			className={
				embedded
					? 'relative flex h-[640px] w-full flex-col overflow-hidden rounded-lg border border-hairline bg-canvas shadow-sm'
					: 'relative flex h-screen w-screen flex-col bg-canvas'
			}
		>
			{!embedded && <Header />}

			{imageUrl ? (
				<div className="relative flex flex-1 overflow-hidden">
					<div className="min-w-0 flex-1">
						<Canvas embedded={embedded} />
					</div>
					<aside className="w-72 shrink-0 border-l border-hairline bg-canvas-elevated">
						{overridePanelRegionId ? <FontOverridePanel /> : <LayersPanel />}
					</aside>
				</div>
			) : (
				<div className="flex flex-1 items-center justify-center p-6">
					<Dropzone />
				</div>
			)}
		</div>
	);
}
