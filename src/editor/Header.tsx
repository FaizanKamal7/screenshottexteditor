import { useEditorStore } from './store';

export function Header() {
	const imageUrl = useEditorStore((s) => s.imageUrl);
	const reset = useEditorStore((s) => s.reset);
	const undo = useEditorStore((s) => s.undo);
	const redo = useEditorStore((s) => s.redo);
	const canUndo = useEditorStore((s) => s.past.length > 0);
	const canRedo = useEditorStore((s) => s.future.length > 0);

	return (
		<header className="flex h-12 shrink-0 items-center justify-between gap-2 border-b border-hairline bg-canvas-elevated px-3">
			<a href="/" className="shrink-0 truncate text-[13px] font-medium text-body hover:text-ink">
				<span aria-hidden="true">←</span> <span className="hidden sm:inline">ScreenshotTextEditor</span>
			</a>

			{imageUrl && (
				<div className="flex shrink-0 items-center gap-2">
					<button
						type="button"
						onClick={undo}
						disabled={!canUndo}
						title="Undo (Ctrl+Z)"
						className="rounded-sm border border-hairline bg-canvas-elevated px-2 py-1 text-[12px] text-body hover:text-ink disabled:opacity-40 disabled:hover:text-body"
					>
						Undo
					</button>
					<button
						type="button"
						onClick={redo}
						disabled={!canRedo}
						title="Redo (Ctrl+Shift+Z)"
						className="rounded-sm border border-hairline bg-canvas-elevated px-2 py-1 text-[12px] text-body hover:text-ink disabled:opacity-40 disabled:hover:text-body"
					>
						Redo
					</button>
					<button
						type="button"
						onClick={reset}
						className="rounded-sm border border-hairline bg-canvas-elevated px-2.5 py-1 text-[12px] text-body hover:text-ink"
					>
						<span className="sm:hidden">New</span>
						<span className="hidden sm:inline">New screenshot</span>
					</button>
					<a
						href={imageUrl}
						download="edited-screenshot.png"
						className="rounded-sm bg-ink px-2.5 py-1 text-[12px] font-medium text-on-primary hover:bg-ink/90"
					>
						Download
					</a>
				</div>
			)}
		</header>
	);
}
