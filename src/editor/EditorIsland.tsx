import { Canvas } from './Canvas';
import { Dropzone } from './Dropzone';
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

	return (
		<div
			className={
				embedded
					? 'relative flex h-[560px] w-full flex-col overflow-hidden rounded-lg border border-hairline bg-canvas shadow-sm sm:h-[640px]'
					: 'relative flex h-dvh w-full flex-col bg-canvas'
			}
		>
			{!embedded && <Header />}

			{imageUrl ? (
				<div className="relative flex min-h-0 flex-1 flex-col overflow-hidden md:flex-row">
					<div className="min-h-0 min-w-0 flex-[3] md:flex-1">
						<Canvas embedded={embedded} />
					</div>
					<aside className="min-h-0 flex-[2] overflow-y-auto border-t border-hairline bg-canvas-elevated md:w-72 md:flex-none md:border-l md:border-t-0">
						<LayersPanel />
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
