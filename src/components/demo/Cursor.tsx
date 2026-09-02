import { useLayoutEffect, useState, type RefObject } from 'react';
import type { TargetKey } from './timeline';

export interface DemoRefs {
	stage: RefObject<HTMLDivElement | null>;
	start: RefObject<HTMLElement | null>;
	class: RefObject<HTMLElement | null>;
	size: RefObject<HTMLElement | null>;
	color: RefObject<HTMLElement | null>;
	spacing: RefObject<HTMLElement | null>;
	date: RefObject<HTMLElement | null>;
	away: RefObject<HTMLElement | null>;
}

interface CursorProps {
	refs: DemoRefs;
	target: TargetKey;
	durationMs: number;
	visible: boolean;
	clicking: boolean;
}

// Reads the real target element's position out of the DOM (relative to the
// stage) and lets a CSS transition carry the pointer there — the same path
// a real cursor takes, and it stays correct across every breakpoint without
// hardcoded coordinates.
export function Cursor({ refs, target, durationMs, visible, clicking }: CursorProps) {
	const [pos, setPos] = useState({ x: 0, y: 0 });

	useLayoutEffect(() => {
		const stageEl = refs.stage.current;
		const targetEl = refs[target]?.current;
		if (!stageEl || !targetEl) return;

		const update = () => {
			const stageRect = stageEl.getBoundingClientRect();
			const targetRect = targetEl.getBoundingClientRect();
			setPos({
				x: targetRect.left - stageRect.left + targetRect.width * 0.35,
				y: targetRect.top - stageRect.top + targetRect.height * 0.5,
			});
		};

		update();
		const observer = new ResizeObserver(update);
		observer.observe(stageEl);
		return () => observer.disconnect();
		// eslint-disable-next-line react-hooks/exhaustive-deps
	}, [target]);

	const clickedOnce = useRippleKey(clicking);

	return (
		<div
			aria-hidden="true"
			className="pointer-events-none absolute left-0 top-0 z-30"
			style={{
				transform: `translate(${pos.x}px, ${pos.y}px)`,
				opacity: visible ? 1 : 0,
				transition: `transform ${durationMs}ms cubic-bezier(0.4, 0, 0.2, 1), opacity 200ms ease-out`,
			}}
		>
			{clicking && (
				<span
					key={clickedOnce}
					className="editor-demo-ripple absolute left-[3px] top-[3px] h-3 w-3 rounded-full bg-link"
				/>
			)}
			<svg
				viewBox="0 0 20 20"
				className={`relative h-5 w-5 drop-shadow-[0_1px_3px_rgba(0,0,0,0.35)] transition-transform duration-150 ${clicking ? 'scale-90' : 'scale-100'}`}
				style={{ transformOrigin: '4px 3px' }}
			>
				<path
					d="M4 2.5 L4 16.5 L7.6 13.2 L9.9 18 L12.3 16.9 L10 12.1 L15 12 Z"
					fill="white"
					stroke="#171717"
					strokeWidth="1.1"
					strokeLinejoin="round"
				/>
			</svg>
		</div>
	);
}

// Bumps a key each time `clicking` turns on, forcing the ripple span to
// remount so its CSS animation replays every click rather than only once.
// Uses the "adjust state during render" pattern instead of mutating a ref
// in the render body, which would double-fire under strict/concurrent mode.
function useRippleKey(clicking: boolean): number {
	const [key, setKey] = useState(0);
	const [prevClicking, setPrevClicking] = useState(clicking);
	if (clicking !== prevClicking) {
		setPrevClicking(clicking);
		if (clicking) setKey((k) => k + 1);
	}
	return key;
}
