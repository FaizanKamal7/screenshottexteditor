import { useEditorStore } from './store';

export function Header() {
	const imageUrl = useEditorStore((s) => s.imageUrl);
	const reset = useEditorStore((s) => s.reset);
	const undo = useEditorStore((s) => s.undo);
	const redo = useEditorStore((s) => s.redo);
	const canUndo = useEditorStore((s) => s.past.length > 0);
	const canRedo = useEditorStore((s) => s.future.length > 0);

	// Every control here keeps its compact look but gets an invisible ::before that stretches the
	// tappable area to ~44px tall (the header is 48px). It has to be a pseudo-element rather than a
	// bigger box: at 320px wide there is no spare width left in this row.
	return (
		<header className="flex h-12 shrink-0 items-center justify-between gap-2 border-b border-hairline bg-canvas-elevated px-3">
			<div className="flex min-w-0 items-center gap-3">
				<a
					href="/"
					className="relative inline-flex h-5 shrink-0 items-center whitespace-nowrap text-[13px] font-medium text-body before:absolute before:-inset-y-3 before:-left-3 before:-right-5 hover:text-ink"
				>
					<span aria-hidden="true">←</span> <span className="hidden sm:inline">ScreenshotTextEditor</span>
				</a>
				{/* The page's only H1: Header renders on /app alone (EditorIsland hides it when embedded). */}
				<h1 className="min-w-0 truncate border-l border-hairline pl-3 text-[13px] font-semibold text-ink">
					Edit text in a screenshot
				</h1>
			</div>

			{imageUrl && (
				<div className="flex shrink-0 items-center gap-2">
					<button
						type="button"
						onClick={undo}
						disabled={!canUndo}
						title="Undo (Ctrl+Z)"
						className="relative rounded-sm border border-hairline bg-canvas-elevated px-2 py-1 text-[12px] text-body before:absolute before:-inset-x-1 before:-inset-y-[9px] hover:text-ink disabled:opacity-40 disabled:hover:text-body"
					>
						Undo
					</button>
					<button
						type="button"
						onClick={redo}
						disabled={!canRedo}
						title="Redo (Ctrl+Shift+Z)"
						className="relative rounded-sm border border-hairline bg-canvas-elevated px-2 py-1 text-[12px] text-body before:absolute before:-inset-x-1 before:-inset-y-[9px] hover:text-ink disabled:opacity-40 disabled:hover:text-body"
					>
						Redo
					</button>
					<button
						type="button"
						onClick={reset}
						className="relative rounded-sm border border-hairline bg-canvas-elevated px-2.5 py-1 text-[12px] text-body before:absolute before:-inset-x-1 before:-inset-y-[9px] hover:text-ink"
					>
						<span className="sm:hidden">New</span>
						<span className="hidden sm:inline">New screenshot</span>
					</button>
					<a
						href={imageUrl}
						download="edited-screenshot.png"
						className="relative rounded-sm bg-ink px-2.5 py-1 text-[12px] font-medium text-on-primary before:absolute before:-inset-x-1 before:-inset-y-[9px] hover:bg-ink/90"
					>
						Download
					</a>
				</div>
			)}
		</header>
	);
}
