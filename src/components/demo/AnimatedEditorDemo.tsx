import { useEffect, useRef, useState } from 'react';
import { EditorStage } from './EditorStage';
import { useDemoTimeline } from './useDemoTimeline';
import {
	activeControl,
	CLASS_EDITED,
	CLASS_ORIGINAL,
	DATE_EDITED,
	DATE_ORIGINAL,
	isClassSelected,
	isClicking,
	isColorOn,
	isCursorVisible,
	isDateSelected,
	isSizeUp,
	isSpacingOn,
	type StepId,
} from './timeline';

const DELETE_INTERVAL_MS = 45;
const TYPE_INTERVAL_MS = 65;
const PAUSE_BETWEEN_MS = 180;

// Schedules the delete-then-type keystrokes for one field's edit step. A
// single bounded chain of timeouts, cleared whenever the step changes or the
// component unmounts — not scattered across the app, confined to the one
// phase of the timeline it belongs to.
function runTypewriter(setText: (text: string) => void, from: string, to: string): () => void {
	const timeouts: number[] = [];
	let t = 0;
	const schedule = (fn: () => void, delay: number) => {
		t += delay;
		timeouts.push(window.setTimeout(fn, t));
	};

	for (let i = from.length - 1; i >= 0; i--) {
		schedule(() => setText(from.slice(0, i)), DELETE_INTERVAL_MS);
	}
	t += PAUSE_BETWEEN_MS;
	for (let i = 1; i <= to.length; i++) {
		schedule(() => setText(to.slice(0, i)), TYPE_INTERVAL_MS);
	}

	return () => timeouts.forEach((id) => window.clearTimeout(id));
}

export function AnimatedEditorDemo() {
	const { step, isStatic, setHovered } = useDemoTimeline();
	const [classText, setClassText] = useState(isStatic ? CLASS_EDITED : CLASS_ORIGINAL);
	const [dateText, setDateText] = useState(isStatic ? DATE_EDITED : DATE_ORIGINAL);
	const [isResetting, setIsResetting] = useState(false);
	const prevStepIdRef = useRef<StepId>(step.id);

	useEffect(() => {
		const prev = prevStepIdRef.current;
		prevStepIdRef.current = step.id;

		if (isStatic) {
			setClassText(CLASS_EDITED);
			setDateText(DATE_EDITED);
			return;
		}

		if (step.id === 'editClass' && prev !== 'editClass') {
			return runTypewriter(setClassText, CLASS_ORIGINAL, CLASS_EDITED);
		}

		if (step.id === 'editDate' && prev !== 'editDate') {
			return runTypewriter(setDateText, DATE_ORIGINAL, DATE_EDITED);
		}

		if (step.id === 'idle' && prev !== 'idle') {
			setIsResetting(true);
			const revert = window.setTimeout(() => {
				setClassText(CLASS_ORIGINAL);
				setDateText(DATE_ORIGINAL);
			}, 160);
			const settle = window.setTimeout(() => setIsResetting(false), 320);
			return () => {
				window.clearTimeout(revert);
				window.clearTimeout(settle);
			};
		}
	}, [step.id, isStatic]);

	return (
		<a
			href="/app"
			aria-label="Open the screenshot text editor"
			className="group block w-full max-w-4xl focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-link focus-visible:ring-offset-2"
			onMouseEnter={() => setHovered(true)}
			onMouseLeave={() => setHovered(false)}
		>
			<div className="transition-transform duration-300 group-hover:-translate-y-0.5">
				<EditorStage
					classText={classText}
					dateText={dateText}
					sizeUp={isSizeUp(step.id)}
					colorOn={isColorOn(step.id)}
					spacingOn={isSpacingOn(step.id)}
					classSelected={isClassSelected(step.id)}
					dateSelected={isDateSelected(step.id)}
					clicking={isClicking(step.id)}
					cursorVisible={isCursorVisible(step.id) && !isStatic}
					cursorTarget={step.target}
					cursorDurationMs={step.duration}
					active={activeControl(step.id)}
					isResetting={isResetting}
					downloadPulse={step.id === 'result' && !isStatic}
				/>
			</div>
		</a>
	);
}
