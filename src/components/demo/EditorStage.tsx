import { useEffect, useRef, useState, type ReactNode, type Ref } from 'react';
import { Cursor, type DemoRefs } from './Cursor';
import type { TargetKey } from './timeline';

// Mirrors Tailwind's `lg` breakpoint (1024px) — the same cutoff the sidebar
// below uses (`hidden lg:flex`). Drives which of the two Style-panel
// placements is actually mounted; see the comment above the sidebar block
// for why this has to be a real conditional render rather than a CSS
// `hidden` class on one of two always-mounted copies.
function useIsDesktop(): boolean {
	const [isDesktop, setIsDesktop] = useState(false);
	useEffect(() => {
		const mql = window.matchMedia('(min-width: 1024px)');
		setIsDesktop(mql.matches);
		const onChange = (e: MediaQueryListEvent) => setIsDesktop(e.matches);
		mql.addEventListener('change', onChange);
		return () => mql.removeEventListener('change', onChange);
	}, []);
	return isDesktop;
}

type ActiveControl = 'size' | 'color' | 'spacing' | null;

interface EditorStageProps {
	classText: string;
	dateText: string;
	sizeUp: boolean;
	colorOn: boolean;
	spacingOn: boolean;
	classSelected: boolean;
	dateSelected: boolean;
	clicking: boolean;
	cursorVisible: boolean;
	cursorTarget: TargetKey;
	cursorDurationMs: number;
	active: ActiveControl;
	isResetting: boolean;
	downloadPulse: boolean;
}

function PlaneIcon({ className = '' }: { className?: string }) {
	return (
		<svg viewBox="0 0 16 16" className={className} fill="currentColor" aria-hidden="true">
			<path d="M14.5 1.5 1 7l4.5 1.5L7 13l2-3.5L14.5 1.5Z" />
		</svg>
	);
}

// A style-panel chip mimicking the real FontOverridePanel's alignment
// buttons (see src/editor/FontOverridePanel.tsx) — a plain div rather than
// a <button> since the whole demo is wrapped in a single <a> to /app.
function Chip({ active, children }: { active: boolean; children: ReactNode }) {
	return (
		<div
			className={`flex-1 rounded-md border px-2 py-1 text-center text-[10px] capitalize transition-colors ${
				active ? 'border-link bg-link/10 text-link' : 'border-hairline bg-canvas-elevated text-body'
			}`}
		>
			{children}
		</div>
	);
}

// One "label above value" field, matching FontOverridePanel's actual
// <label className="flex flex-col gap-1 ..."> stack (Size / Weight / Letter
// spacing all use this exact shape — label text, then the control below it).
function FieldDisplay({ label, value, refProp, active }: { label: string; value: ReactNode; refProp?: Ref<HTMLDivElement>; active?: boolean }) {
	return (
		<div className="flex flex-col gap-1 text-[10px] text-faint">
			{label}
			<div
				ref={refProp}
				className={`rounded-md border px-2 py-1.5 text-[11px] tabular-nums transition-colors ${
					active ? 'border-link bg-link/10 text-link' : 'border-hairline bg-canvas-elevated text-ink'
				}`}
			>
				{value}
			</div>
		</div>
	);
}

// Replicates FontOverridePanel in full (see
// src/editor/FontOverridePanel.tsx:149-218) — Alignment, Size, Weight,
// Letter spacing, and Text color, in the same order. `variant="inline"`
// matches how it actually appears in the real app: expanded inline under a
// LayersPanel row, on the hairline-soft background FontOverridePanel itself
// uses. `variant="floating"` is the mobile/tablet fallback, where there's
// no sidebar for it to expand into, so it floats as a small card under the
// selected field instead. Only Size, Text color, and Letter spacing are
// wired to the cursor for this loop — Alignment and Weight render as real,
// correctly-styled static fields for authenticity, they're just not part
// of this particular demonstration (a text-align shift read as an odd,
// off-putting motion; size + color read more clearly as "styling applied").
// A few preset swatches, like a real color-input's palette — makes it
// obvious the new color is coming from a picker rather than changing on
// its own. Only ink and warning are ever actually applied to the text; the
// rest are there so the popover reads as a genuine picker, not a 2-option toggle.
const COLOR_PALETTE = ['#171717', '#0761d1', '#ee0000', '#f5a623', '#7928ca'];

function StylePanel({
	variant,
	size,
	weight,
	letterSpacing,
	colorHex,
	colorOn,
	activeControl,
	sizeRef,
	colorRef,
	spacingRef,
}: {
	variant: 'inline' | 'floating';
	size: number;
	weight: number;
	letterSpacing: number;
	colorHex: string;
	colorOn: boolean;
	activeControl: ActiveControl;
	sizeRef?: Ref<HTMLDivElement>;
	colorRef?: Ref<HTMLDivElement>;
	spacingRef?: Ref<HTMLDivElement>;
}) {
	const pickedHex = colorOn ? '#0761d1' : '#171717';
	return (
		<div
			className={
				variant === 'floating'
					? 'flex flex-col gap-2.5 rounded-lg border border-hairline bg-canvas-elevated/95 px-3 py-2.5 shadow-md backdrop-blur-sm'
					: 'flex flex-col gap-2.5 bg-hairline-soft/50 px-3.5 py-3'
			}
		>
			<p className="text-[11px] font-semibold tracking-tight text-ink">Style</p>

			<div className="flex flex-col gap-1">
				<p className="text-[10px] text-faint">Alignment</p>
				<p className="text-[9px] font-normal leading-snug text-faint">
					When replacement text needs more room, the box grows toward this side.
				</p>
				<div className="flex gap-1">
					<Chip active={true}>left</Chip>
					<Chip active={false}>center</Chip>
					<Chip active={false}>right</Chip>
				</div>
			</div>

			<FieldDisplay label="Size (px)" value={size} refProp={sizeRef} active={activeControl === 'size'} />
			<FieldDisplay label="Weight" value={weight} />
			<FieldDisplay label="Letter spacing (px)" value={letterSpacing.toFixed(1)} refProp={spacingRef} active={activeControl === 'spacing'} />

			<div className="flex flex-col gap-1 text-[10px] text-faint">
				Text color
				<div
					ref={colorRef}
					className={`h-8 w-full rounded-md border transition-colors ${activeControl === 'color' ? 'border-link ring-2 ring-link/30' : 'border-hairline'}`}
					style={{ backgroundColor: colorHex }}
				/>
				{/* The picker itself — expands open only while this control is being
				    demonstrated, so the color change visibly comes from picking a
				    swatch rather than happening on its own. */}
				<div
					className="overflow-hidden transition-[max-height,opacity,margin] duration-200 ease-out"
					style={{ maxHeight: activeControl === 'color' ? 40 : 0, opacity: activeControl === 'color' ? 1 : 0, marginTop: activeControl === 'color' ? 6 : 0 }}
				>
					<div className="flex items-center gap-1.5 rounded-md border border-hairline bg-canvas p-1.5">
						{COLOR_PALETTE.map((hex) => (
							<span
								key={hex}
								className={`h-4 w-4 shrink-0 rounded-full border border-hairline-soft transition-shadow ${
									hex === pickedHex ? 'ring-2 ring-link ring-offset-1' : ''
								}`}
								style={{ backgroundColor: hex }}
							/>
						))}
					</div>
				</div>
			</div>
		</div>
	);
}

// A miniature, hand-built recreation of the real editor chrome (see
// Header.tsx, Canvas.tsx, LayersPanel.tsx, FontOverridePanel.tsx) — not an
// iframe of the app. On desktop (lg+) the Style panel expands inline in the
// right-hand "Detected text" list under whichever row is selected, exactly
// like the real LayersPanel + FontOverridePanel do — not floating below the
// text on canvas. Below lg there's no sidebar to expand into, so it falls
// back to a small floating card under the field instead (see useIsDesktop).
// Both detected fields (Travel class and Date) open the same panel when
// selected — selecting any region opens its Style panel in the real app,
// not just the one this loop happens to demonstrate editing.
export function EditorStage({
	classText,
	dateText,
	sizeUp,
	colorOn,
	spacingOn,
	classSelected,
	dateSelected,
	clicking,
	cursorVisible,
	cursorTarget,
	cursorDurationMs,
	active,
	isResetting,
	downloadPulse,
}: EditorStageProps) {
	const isDesktop = useIsDesktop();
	const stageRef = useRef<HTMLDivElement>(null);
	const startRef = useRef<HTMLSpanElement>(null);
	const classRef = useRef<HTMLSpanElement>(null);
	const sizeRef = useRef<HTMLDivElement>(null);
	const colorRef = useRef<HTMLDivElement>(null);
	const spacingRef = useRef<HTMLDivElement>(null);
	const dateRef = useRef<HTMLSpanElement>(null);
	const awayRef = useRef<HTMLSpanElement>(null);

	const refs: DemoRefs = {
		stage: stageRef,
		start: startRef,
		class: classRef,
		size: sizeRef,
		color: colorRef,
		spacing: spacingRef,
		date: dateRef,
		away: awayRef,
	};

	const classColorHex = colorOn ? 'var(--color-link-deep)' : 'var(--color-ink)';

	return (
		// Fixed height at lg+ only: the hero pairs this with the headline in a
		// grid (see index.astro), so on desktop the card's height can't react to
		// the sidebar's Style panel expanding — that shifted the headline column
		// (items-center) and every section below it on the page. Below lg the
		// demo isn't grid-paired with anything, so it stays auto-height as
		// before. The sidebar's own scroll (min-h-0 + overflow-y-auto below)
		// is the fallback if an expanded panel ever needs more room than fits.
		<div className="relative flex w-full flex-col overflow-hidden rounded-xl border border-hairline bg-canvas shadow-[0_20px_60px_-20px_rgba(0,0,0,0.25)] lg:h-[640px]">
			<div className="flex h-11 shrink-0 items-center justify-between gap-2 border-b border-hairline bg-canvas-elevated px-3">
				<span className="flex shrink-0 items-center gap-1.5 truncate text-[12px] font-medium text-body">
					<span aria-hidden="true">←</span>
					<span className="hidden sm:inline">ScreenshotTextEditor</span>
				</span>
				<div className="flex shrink-0 items-center gap-2">
					<span className="hidden rounded-sm border border-hairline bg-canvas-elevated px-2.5 py-1 text-[11px] text-body sm:inline-block">
						New screenshot
					</span>
					<span
						className={`rounded-sm bg-ink px-2.5 py-1 text-[11px] font-medium text-on-primary transition-shadow ${
							downloadPulse ? 'editor-demo-pulse-ring' : ''
						}`}
					>
						Download
					</span>
				</div>
			</div>

			<div className="relative flex min-h-0 flex-1">
				<div ref={stageRef} className="relative flex flex-1 items-center justify-center bg-canvas p-5 sm:p-8">
					<span ref={startRef} className="absolute left-4 top-4 h-px w-px" aria-hidden="true" />
					<span ref={awayRef} className="absolute bottom-6 right-6 h-px w-px" aria-hidden="true" />

					<div className="w-full max-w-[380px] overflow-hidden rounded-lg border border-hairline bg-canvas-elevated shadow-sm">
						<div className="flex items-center justify-between border-b border-hairline-soft px-3 py-1.5 text-[10px] text-faint">
							<span>9:41</span>
							<span className="flex items-center gap-1">
								<span className="h-1.5 w-1.5 rounded-full bg-faint" />
								<span className="h-1.5 w-3 rounded-sm bg-faint" />
							</span>
						</div>

						<div className="px-4 pb-4 pt-3.5">
							<div className="flex items-center justify-between">
								<span className="flex items-center gap-1.5 text-[13px] font-semibold tracking-tight text-ink">
									<PlaneIcon className="h-3 w-3 text-link" />
									SkyWays
								</span>
								<span className="font-mono text-[10px] text-faint">7F3K9L</span>
							</div>

							<div className="mt-4 flex items-center justify-between">
								<div>
									<p className="text-[20px] font-semibold tracking-tight text-ink">NYC</p>
									<p className="text-[10px] text-faint">10:25 AM</p>
								</div>
								<div className="flex flex-1 items-center px-2">
									<span className="h-px flex-1 border-t border-dashed border-hairline" />
									<PlaneIcon className="mx-1.5 h-2.5 w-2.5 rotate-90 text-faint" />
									<span className="h-px flex-1 border-t border-dashed border-hairline" />
								</div>
								<div className="text-right">
									<p className="text-[20px] font-semibold tracking-tight text-ink">SFO</p>
									<p className="text-[10px] text-faint">1:40 PM</p>
								</div>
							</div>

							<div className="mt-4 flex items-center gap-6">
								<div>
									<p className="font-mono text-[9px] uppercase tracking-wide text-faint">Passenger</p>
									<p className="mt-0.5 text-[12px] text-ink">A. Morgan</p>
								</div>
								<div>
									<p className="font-mono text-[9px] uppercase tracking-wide text-faint">Seat</p>
									<p className="mt-0.5 text-[12px] text-ink">14A</p>
								</div>
							</div>

							{/* Field 1: Travel class — text edit + size + color + letter-spacing. */}
							<div className="mt-4">
								<p className="font-mono text-[9px] uppercase tracking-wide text-faint">Travel class</p>
								<span
									ref={classRef}
									className={`relative mt-1 inline-block rounded-sm px-1.5 py-0.5 font-semibold leading-tight tracking-tight transition-[background,box-shadow,font-size,color] duration-300 ${
										classSelected ? 'bg-canvas-elevated shadow-[0_2px_10px_rgba(0,0,0,0.16)] ring-2 ring-link/50' : 'px-0'
									} ${isResetting ? 'opacity-0' : 'opacity-100'}`}
									style={{ fontSize: sizeUp ? 26 : 22, color: classColorHex, letterSpacing: spacingOn ? '2px' : '0px' }}
								>
									{classText}
									{classSelected && (
										<span
											className="absolute -left-2 -top-2 h-3.5 w-3.5 rounded-full border border-hairline bg-canvas-elevated shadow-sm"
											aria-hidden="true"
										/>
									)}
								</span>

								{/* Mobile/tablet only — below lg there's no sidebar for the Style
								    panel to expand into (see useIsDesktop), so it floats under the
								    field instead. Height animates open on selection. */}
								{!isDesktop && (
									<div
										className="overflow-hidden transition-[max-height,opacity,margin] duration-200 ease-out"
										style={{ maxHeight: classSelected ? 420 : 0, opacity: classSelected ? 1 : 0, marginTop: classSelected ? 8 : 0 }}
									>
										<StylePanel
											variant="floating"
											size={sizeUp ? 26 : 22}
											weight={600}
											letterSpacing={spacingOn ? 2 : 0}
											colorHex={classColorHex}
											colorOn={colorOn}
											activeControl={active}
											sizeRef={sizeRef}
											colorRef={colorRef}
											spacingRef={spacingRef}
										/>
									</div>
								)}
							</div>

							{/* Field 2: Date — a second, independent detected text run, edited
							    the same way, to show any field can be selected and retyped;
							    selecting it opens the same Style panel Travel class does. */}
							<div className="mt-3.5">
								<p className="font-mono text-[9px] uppercase tracking-wide text-faint">Date</p>
								<span
									ref={dateRef}
									className={`relative mt-1 inline-block rounded-sm px-1.5 py-0.5 text-[15px] font-medium text-ink transition-[background,box-shadow] duration-200 ${
										dateSelected ? 'bg-canvas-elevated shadow-[0_2px_10px_rgba(0,0,0,0.16)] ring-2 ring-link/50' : 'px-0'
									} ${isResetting ? 'opacity-0' : 'opacity-100'}`}
								>
									{dateText}
									{dateSelected && (
										<span
											className="absolute -left-2 -top-2 h-3 w-3 rounded-full border border-hairline bg-canvas-elevated shadow-sm"
											aria-hidden="true"
										/>
									)}
								</span>

								{!isDesktop && (
									<div
										className="overflow-hidden transition-[max-height,opacity,margin] duration-200 ease-out"
										style={{ maxHeight: dateSelected ? 260 : 0, opacity: dateSelected ? 1 : 0, marginTop: dateSelected ? 8 : 0 }}
									>
										<StylePanel variant="floating" size={15} weight={500} letterSpacing={0} colorHex="var(--color-ink)" colorOn={false} activeControl={null} />
									</div>
								)}
							</div>

							<div className="relative mt-4">
								<div className="border-t border-dashed border-hairline" />
								<span className="absolute -left-6 -top-2 h-4 w-4 rounded-full bg-canvas" aria-hidden="true" />
								<span className="absolute -right-6 -top-2 h-4 w-4 rounded-full bg-canvas" aria-hidden="true" />
							</div>

							<div className="mt-3 flex items-center justify-between text-[11px] text-mute">
								<span>Gate B12</span>
								<span>Boarding 09:55 AM</span>
							</div>
						</div>
					</div>

					<Cursor refs={refs} target={cursorTarget} durationMs={cursorDurationMs} visible={cursorVisible} clicking={clicking} />
				</div>

				<aside className="hidden w-56 min-h-0 flex-none flex-col border-l border-hairline bg-canvas-elevated lg:flex">
					<div className="border-b border-hairline p-3">
						<p className="text-[12px] font-medium text-ink">
							Detected text <span className="text-faint">(3)</span>
						</p>
					</div>
					<div className="editor-demo-no-scrollbar flex-1 space-y-1 overflow-y-auto p-2">
						{/* Matches LayersPanel.tsx's expandable row exactly: a left accent
						    bar marks the expanded row, and FontOverridePanel's fields mount
						    inline beneath it — the Style panel belongs here, not floating
						    under the text on canvas. Both rows use the same pattern, since
						    selecting either region opens its panel in the real app. */}
						<div
							className={`relative overflow-hidden rounded-lg transition-shadow ${
								classSelected ? 'border border-link/25 bg-canvas-elevated shadow-[0_1px_6px_rgba(0,0,0,0.08)]' : 'border border-transparent'
							}`}
						>
							{classSelected && <span className="absolute inset-y-0 left-0 w-[3px] bg-link" aria-hidden="true" />}
							<div className={`flex items-start p-2.5 ${classSelected ? 'pl-3.5' : ''}`}>
								<div className="min-w-0 flex-1">
									<div className="flex items-start justify-between gap-2">
										<p className={`truncate text-[12px] ${classSelected ? 'font-medium text-ink' : 'text-ink'}`}>{classText}</p>
										<span className="mt-0.5 h-1.5 w-1.5 shrink-0 rounded-full bg-link" />
									</div>
									<p className="mt-0.5 truncate text-[10px] text-faint">
										Geist · 600{sizeUp || colorOn || spacingOn ? ' · edited' : ''}
									</p>
								</div>
							</div>
							{isDesktop && (
								<div
									className="overflow-hidden transition-[max-height,opacity] duration-200 ease-out"
									style={{ maxHeight: classSelected ? 420 : 0, opacity: classSelected ? 1 : 0 }}
								>
									<StylePanel
										variant="inline"
										size={sizeUp ? 26 : 22}
										weight={600}
										letterSpacing={spacingOn ? 2 : 0}
										colorHex={classColorHex}
										colorOn={colorOn}
										activeControl={active}
										sizeRef={sizeRef}
										colorRef={colorRef}
										spacingRef={spacingRef}
									/>
								</div>
							)}
						</div>

						<div
							className={`relative overflow-hidden rounded-lg transition-shadow ${
								dateSelected ? 'border border-link/25 bg-canvas-elevated shadow-[0_1px_6px_rgba(0,0,0,0.08)]' : 'border border-transparent'
							}`}
						>
							{dateSelected && <span className="absolute inset-y-0 left-0 w-[3px] bg-link" aria-hidden="true" />}
							<div className={`flex items-start p-2.5 ${dateSelected ? 'pl-3.5' : ''}`}>
								<div className="min-w-0 flex-1">
									<div className="flex items-start justify-between gap-2">
										<p className={`truncate text-[12px] ${dateSelected ? 'font-medium text-ink' : 'text-ink'}`}>{dateText}</p>
										<span className="mt-0.5 h-1.5 w-1.5 shrink-0 rounded-full bg-link" />
									</div>
									<p className="mt-0.5 truncate text-[10px] text-faint">Geist · 500</p>
								</div>
							</div>
							{isDesktop && (
								<div
									className="overflow-hidden transition-[max-height,opacity] duration-200 ease-out"
									style={{ maxHeight: dateSelected ? 280 : 0, opacity: dateSelected ? 1 : 0 }}
								>
									<StylePanel variant="inline" size={15} weight={500} letterSpacing={0} colorHex="var(--color-ink)" colorOn={false} activeControl={null} />
								</div>
							)}
						</div>

						<div className="rounded-md border border-transparent p-2">
							<div className="flex items-start justify-between gap-2">
								<p className="truncate text-[12px] text-ink">A. Morgan</p>
								<span className="mt-0.5 h-1.5 w-1.5 shrink-0 rounded-full bg-link" />
							</div>
							<p className="mt-0.5 truncate text-[10px] text-faint">Inter · 12px</p>
						</div>
					</div>
				</aside>
			</div>
		</div>
	);
}
