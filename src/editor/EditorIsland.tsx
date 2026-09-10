import { useEffect } from 'react';
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

	// Ctrl/Cmd+Z to undo, Ctrl/Cmd+Shift+Z (or Ctrl+Y) to redo — skipped while
	// focus is in a text input (e.g. a region's inline editor) so it doesn't
	// fight the browser's own native undo for that field.
	useEffect(() => {
		const handleKeyDown = (e: KeyboardEvent) => {
			if (!(e.ctrlKey || e.metaKey)) return;
			if (e.key.toLowerCase() !== 'z' && e.key.toLowerCase() !== 'y') return;
			const target = e.target as HTMLElement | null;
			if (target && (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.isContentEditable)) return;

			const key = e.key.toLowerCase();
			if (key === 'y' || (key === 'z' && e.shiftKey)) {
				e.preventDefault();
				useEditorStore.getState().redo();
			} else if (key === 'z') {
				e.preventDefault();
				useEditorStore.getState().undo();
			}
		};
		window.addEventListener('keydown', handleKeyDown);
		return () => window.removeEventListener('keydown', handleKeyDown);
	}, []);

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
