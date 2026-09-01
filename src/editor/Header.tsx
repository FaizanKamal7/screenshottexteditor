import { useEditorStore } from './store';

export function Header() {
	const imageUrl = useEditorStore((s) => s.imageUrl);
	const reset = useEditorStore((s) => s.reset);

	return (
		<header className="flex h-12 shrink-0 items-center justify-between border-b border-hairline bg-canvas-elevated px-3">
			<a href="/" className="text-[13px] font-medium text-body hover:text-ink">
				← ScreenshotTextEditor
			</a>

			{imageUrl && (
				<div className="flex items-center gap-2">
					<button
						type="button"
						onClick={reset}
						className="rounded-sm border border-hairline bg-canvas-elevated px-2.5 py-1 text-[12px] text-body hover:text-ink"
					>
						New screenshot
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
