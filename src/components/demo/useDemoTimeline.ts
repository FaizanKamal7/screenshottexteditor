import { useEffect, useRef, useState } from 'react';
import { STEPS, type Step } from './timeline';

interface DemoTimeline {
	step: Step;
	stepIndex: number;
	/** Increments every time the loop returns to the first step — used to key a fade-reset. */
	cycleKey: number;
	/** True when the sequence never runs at all (prefers-reduced-motion). */
	isStatic: boolean;
	paused: boolean;
	setHovered: (hovered: boolean) => void;
}

// A single chained setTimeout walks the step list — deterministic and cheap
// (one state update per step, not per frame). Pausing (tab hidden or
// hovered) simply holds at the upcoming step until resumed; resuming always
// starts that step fresh rather than resuming mid-duration, which is
// invisible in practice and avoids tracking remaining time.
export function useDemoTimeline(): DemoTimeline {
	const [stepIndex, setStepIndex] = useState(0);
	const [cycleKey, setCycleKey] = useState(0);
	const [paused, setPaused] = useState(false);
	const [isStatic, setIsStatic] = useState(false);

	const pausedRef = useRef(false);
	const hoveredRef = useRef(false);
	const hiddenRef = useRef(false);
	const timeoutRef = useRef<number | undefined>(undefined);

	useEffect(() => {
		pausedRef.current = paused;
	}, [paused]);

	const recomputePaused = () => setPaused(hoveredRef.current || hiddenRef.current);

	useEffect(() => {
		const onVisibility = () => {
			hiddenRef.current = document.hidden;
			recomputePaused();
		};
		document.addEventListener('visibilitychange', onVisibility);
		hiddenRef.current = document.hidden;
		recomputePaused();
		return () => document.removeEventListener('visibilitychange', onVisibility);
	}, []);

	useEffect(() => {
		const mql = window.matchMedia('(prefers-reduced-motion: reduce)');
		setIsStatic(mql.matches);
		const onChange = (e: MediaQueryListEvent) => setIsStatic(e.matches);
		mql.addEventListener('change', onChange);
		return () => mql.removeEventListener('change', onChange);
	}, []);

	useEffect(() => {
		if (isStatic) return;

		const runStep = (index: number) => {
			if (pausedRef.current) {
				timeoutRef.current = window.setTimeout(() => runStep(index), 200);
				return;
			}
			setStepIndex(index);
			const step = STEPS[index];
			timeoutRef.current = window.setTimeout(() => {
				const next = (index + 1) % STEPS.length;
				if (next === 0) setCycleKey((k) => k + 1);
				runStep(next);
			}, step.duration);
		};

		runStep(0);
		return () => window.clearTimeout(timeoutRef.current);
	}, [isStatic]);

	const setHovered = (hovered: boolean) => {
		hoveredRef.current = hovered;
		recomputePaused();
	};

	const step = isStatic ? STEPS[STEPS.length - 1] : STEPS[stepIndex];

	return { step, stepIndex: isStatic ? STEPS.length - 1 : stepIndex, cycleKey, isStatic, paused, setHovered };
}
