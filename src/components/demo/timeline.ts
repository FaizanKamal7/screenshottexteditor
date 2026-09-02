// Deterministic state machine driving AnimatedEditorDemo. Each step is a
// named phase with a fixed duration (ms) and a cursor destination; the
// component derives every other visual (which field is selected, size,
// color, letter-spacing, which control is active) from the current step id
// via the pure helpers below, so there is exactly one source of truth for
// "what is happening right now." The demo edits two fields in sequence —
// Travel class (text + size + color + letter-spacing) then Date (text
// only) — to show that any detected text run can be edited, not just one.
export type StepId =
	| 'idle'
	| 'moveToClass'
	| 'selectClass'
	| 'editClass'
	| 'moveToSize'
	| 'clickSize'
	| 'moveToColor'
	| 'clickColor'
	| 'moveToSpacing'
	| 'clickSpacing'
	| 'moveToDate'
	| 'selectDate'
	| 'editDate'
	| 'deselectDate'
	| 'result';

export type TargetKey = 'start' | 'class' | 'size' | 'color' | 'spacing' | 'date' | 'away';

export interface Step {
	id: StepId;
	duration: number;
	target: TargetKey;
}

export const STEPS: Step[] = [
	{ id: 'idle', duration: 900, target: 'start' },
	{ id: 'moveToClass', duration: 800, target: 'class' },
	{ id: 'selectClass', duration: 600, target: 'class' },
	{ id: 'editClass', duration: 1700, target: 'class' },
	{ id: 'moveToSize', duration: 650, target: 'size' },
	{ id: 'clickSize', duration: 450, target: 'size' },
	{ id: 'moveToColor', duration: 650, target: 'color' },
	{ id: 'clickColor', duration: 450, target: 'color' },
	{ id: 'moveToSpacing', duration: 650, target: 'spacing' },
	{ id: 'clickSpacing', duration: 450, target: 'spacing' },
	{ id: 'moveToDate', duration: 750, target: 'date' },
	{ id: 'selectDate', duration: 550, target: 'date' },
	{ id: 'editDate', duration: 1200, target: 'date' },
	{ id: 'deselectDate', duration: 600, target: 'away' },
	{ id: 'result', duration: 1700, target: 'away' },
];

export const CLASS_ORIGINAL = 'Economy';
export const CLASS_EDITED = 'Business Class';
export const DATE_ORIGINAL = 'Oct 12';
export const DATE_EDITED = 'Oct 19';

const CLASS_SELECTED_STEPS = new Set<StepId>([
	'selectClass',
	'editClass',
	'moveToSize',
	'clickSize',
	'moveToColor',
	'clickColor',
	'moveToSpacing',
	'clickSpacing',
]);
const DATE_SELECTED_STEPS = new Set<StepId>(['selectDate', 'editDate']);
const CLICK_STEPS = new Set<StepId>(['selectClass', 'clickSize', 'clickColor', 'clickSpacing', 'selectDate']);
const SIZE_UP_FROM: StepId[] = [
	'clickSize',
	'moveToColor',
	'clickColor',
	'moveToSpacing',
	'clickSpacing',
	'moveToDate',
	'selectDate',
	'editDate',
	'deselectDate',
	'result',
];
const COLOR_ON_FROM: StepId[] = ['clickColor', 'moveToSpacing', 'clickSpacing', 'moveToDate', 'selectDate', 'editDate', 'deselectDate', 'result'];
const SPACING_ON_FROM: StepId[] = ['clickSpacing', 'moveToDate', 'selectDate', 'editDate', 'deselectDate', 'result'];

export function isClassSelected(stepId: StepId): boolean {
	return CLASS_SELECTED_STEPS.has(stepId);
}

export function isDateSelected(stepId: StepId): boolean {
	return DATE_SELECTED_STEPS.has(stepId);
}

export function isCursorVisible(stepId: StepId): boolean {
	return stepId !== 'idle' && stepId !== 'result';
}

export function isClicking(stepId: StepId): boolean {
	return CLICK_STEPS.has(stepId);
}

export function isSizeUp(stepId: StepId): boolean {
	return SIZE_UP_FROM.includes(stepId);
}

export function isColorOn(stepId: StepId): boolean {
	return COLOR_ON_FROM.includes(stepId);
}

export function isSpacingOn(stepId: StepId): boolean {
	return SPACING_ON_FROM.includes(stepId);
}

export function activeControl(stepId: StepId): 'size' | 'color' | 'spacing' | null {
	if (stepId === 'moveToSize' || stepId === 'clickSize') return 'size';
	if (stepId === 'moveToColor' || stepId === 'clickColor') return 'color';
	if (stepId === 'moveToSpacing' || stepId === 'clickSpacing') return 'spacing';
	return null;
}
