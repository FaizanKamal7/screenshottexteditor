import { useEffect, useRef, useState } from 'react';

// There's no real progress signal for this phase (a single opaque OCR call —
// see status: 'analyzing' in store.ts), so everything here is a time-based
// estimate against a ~60s expected duration, not literal backend progress.
const NOMINAL_MS = 60_000;
// How far past NOMINAL_MS before we stop implying a countdown and switch to
// "taking longer" copy instead.
const OVERRUN_GRACE_MS = 6_000;
// The estimate asymptotically approaches this, never reaching it on its own
// — see the exponential curve in the progress effect below. Real completion
// (phase 'completing') is what actually reaches 100.
const PROGRESS_CAP = 92;
const TICK_MS = 220;
const COMPLETE_TWEEN_MS = 550;
const MESSAGE_INTERVAL_MS = 3200;

const STAGES = [
	{ key: 'preparing', label: 'Preparing', at: 0 },
	{ key: 'analyzing', label: 'Analyzing', at: 18 },
	{ key: 'checking', label: 'Checking', at: 55 },
	{ key: 'finalizing', label: 'Finalizing', at: 82 },
] as const;

type StageKey = (typeof STAGES)[number]['key'];

const STAGE_MESSAGES: Record<StageKey, string[]> = {
	preparing: ['Preparing everything…', 'Getting your screenshot ready…'],
	analyzing: ['Analyzing the image…', 'Reading text and layout…'],
	checking: ['Running deeper checks…', 'Verifying fonts and colors…'],
	finalizing: ['Putting the results together…', 'Almost there…'],
};

// Surfaced under the rotating message as progress crosses each threshold —
// the last one is phrased as in-progress (→), the earlier ones as done (✓).
const MILESTONES = [
	{ at: 36, label: 'Initial analysis complete', done: true },
	{ at: 64, label: 'Data processed', done: true },
	{ at: 83, label: 'Running final checks', done: false },
] as const;

function stageForProgress(progress: number) {
	let current: (typeof STAGES)[number] = STAGES[0];
	for (const stage of STAGES) {
		if (progress >= stage.at) current = stage;
	}
	return current;
}

function ScanIcon() {
	return (
		<svg
			viewBox="0 0 24 24"
			fill="none"
			stroke="currentColor"
			strokeWidth="1.75"
			strokeLinecap="round"
			strokeLinejoin="round"
			className="h-4 w-4 sm:h-[18px] sm:w-[18px]"
		>
			<path d="M4 8V5a1 1 0 0 1 1-1h3" />
			<path d="M20 8V5a1 1 0 0 0-1-1h-3" />
			<path d="M4 16v3a1 1 0 0 0 1 1h3" />
			<path d="M20 16v3a1 1 0 0 1-1 1h-3" />
			<path d="M8 12h8" />
		</svg>
	);
}

function CheckIcon() {
	return (
		<svg
			viewBox="0 0 24 24"
			fill="none"
			stroke="currentColor"
			strokeWidth="2"
			strokeLinecap="round"
			strokeLinejoin="round"
			className="h-4 w-4 sm:h-[18px] sm:w-[18px]"
		>
			<path d="M5 12.5 10 17l9-10" />
		</svg>
	);
}

interface AnalyzingLoaderProps {
	// 'active': still waiting on the real request, progress is simulated.
	// 'completing': the real request just finished — tween to 100% and hold
	// a brief success state. The parent (Canvas) controls this so the exit
	// animation isn't cut off by the status flip that would otherwise unmount
	// this component immediately.
	phase: 'active' | 'completing';
	onCancel: () => void;
}

export function AnalyzingLoader({ phase, onCancel }: AnalyzingLoaderProps) {
	const startRef = useRef(performance.now());
	const [progress, setProgress] = useState(0);
	const [isOverrunning, setIsOverrunning] = useState(false);
	const [messageIndex, setMessageIndex] = useState(0);

	useEffect(() => {
		if (phase !== 'active') return;
		const interval = setInterval(() => {
			const elapsed = performance.now() - startRef.current;
			const t = elapsed / NOMINAL_MS;
			setProgress(PROGRESS_CAP * (1 - Math.exp(-3 * t)));
			setIsOverrunning(elapsed > NOMINAL_MS + OVERRUN_GRACE_MS);
		}, TICK_MS);
		return () => clearInterval(interval);
	}, [phase]);

	useEffect(() => {
		if (phase !== 'active') return;
		const interval = setInterval(() => setMessageIndex((i) => i + 1), MESSAGE_INTERVAL_MS);
		return () => clearInterval(interval);
	}, [phase]);

	// Real completion: tween quickly from wherever the estimate landed up to
	// 100% instead of jumping, then Canvas holds this success state briefly
	// before unmounting the loader.
	useEffect(() => {
		if (phase !== 'completing') return;
		const from = progress;
		const start = performance.now();
		let frame: number;
		const step = () => {
			const t = Math.min(1, (performance.now() - start) / COMPLETE_TWEEN_MS);
			setProgress(from + (100 - from) * t);
			if (t < 1) frame = requestAnimationFrame(step);
		};
		frame = requestAnimationFrame(step);
		return () => cancelAnimationFrame(frame);
		// Only re-run on the active -> completing transition, not on every
		// progress tick the tween itself produces.
		// eslint-disable-next-line react-hooks/exhaustive-deps
	}, [phase]);

	const isDone = phase === 'completing';
	const stage = stageForProgress(progress);
	const messages = STAGE_MESSAGES[stage.key];
	const message = messages[messageIndex % messages.length];
	const milestone = [...MILESTONES].reverse().find((m) => progress >= m.at) ?? null;
	const remainingSeconds = Math.max(2, Math.round(((100 - progress) / 100) * 60));
	const isEager = progress >= 80;

	return (
		<div className="flex w-full flex-col items-center gap-4 text-center">
			<div className="relative flex h-20 w-20 items-center justify-center sm:h-24 sm:w-24">
				<span className="absolute inset-0 rounded-full border border-hairline" />
				{!isDone && (
					<span
						className={`loader-orbit-ring absolute inset-0 rounded-full border-2 border-transparent border-t-link ${
							isEager ? 'loader-orbit-ring--eager' : ''
						}`}
					/>
				)}
				<span
					className={`loader-core-pulse flex h-9 w-9 items-center justify-center rounded-full bg-link-soft text-link sm:h-10 sm:w-10 ${
						isDone ? '' : isEager ? 'loader-core-pulse--eager' : ''
					}`}
				>
					{isDone ? <CheckIcon /> : <ScanIcon />}
				</span>
			</div>

			<div className="tabular-nums text-3xl font-semibold text-ink sm:text-4xl">{Math.round(progress)}%</div>

			<div className="h-2 w-full overflow-hidden rounded-full bg-hairline">
				<div
					className="h-full rounded-full bg-link transition-[width] duration-500 ease-out"
					style={{ width: `${progress}%` }}
				/>
			</div>

			<p className="whitespace-nowrap text-xs text-faint">
				{isDone ? 'Done' : isOverrunning ? 'Taking a little longer than expected…' : `About ${remainingSeconds}s remaining`}
			</p>

			<div className="flex w-full items-center justify-between gap-1">
				{STAGES.map((s) => {
					const reached = progress >= s.at || isDone;
					const isCurrent = stage.key === s.key && !isDone;
					return (
						<div key={s.key} className="flex flex-1 flex-col items-center gap-1">
							<span className={`h-1.5 w-full rounded-full transition-colors duration-300 ${reached ? 'bg-link' : 'bg-hairline'}`} />
							<span className={`text-[10px] ${isCurrent ? 'text-link' : reached ? 'text-body' : 'text-faint'}`}>{s.label}</span>
						</div>
					);
				})}
			</div>

			<div className="flex min-h-10 flex-col items-center justify-center gap-0.5 px-2">
				<p key={isDone ? 'done' : message} className="loader-msg-fade text-[13px] text-body">
					{isDone ? "You're all set" : message}
				</p>
				{!isDone && milestone && (
					<p key={milestone.label} className="loader-msg-fade whitespace-nowrap text-[11px] text-faint">
						{milestone.done ? '✓' : '→'} {milestone.label}
					</p>
				)}
			</div>

			{!isDone && (
				<button type="button" onClick={onCancel} className="text-[11px] text-faint hover:text-error">
					Cancel
				</button>
			)}
		</div>
	);
}
