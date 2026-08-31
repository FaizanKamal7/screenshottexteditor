import { create } from 'zustand';

export interface CharBox {
	x: number;
	y: number;
	w: number;
	h: number;
}

export type RgbColor = [number, number, number];

export interface GradientStop {
	position: number;
	color: RgbColor;
}

export interface BackgroundFill {
	kind: 'flat' | 'gradient';
	color: RgbColor | null;
	angleDeg: number | null;
	stops: GradientStop[];
}

export interface UiElement {
	kind: 'button' | 'pill' | 'input' | 'unknown';
	bbox: [number, number, number, number];
	fillColor: RgbColor;
}

export interface FontCandidateScore {
	family: string;
	weight: number;
	score: number;
}

export interface Region {
	id: string;
	text: string;
	bbox: [number, number, number, number];
	blockId: string;
	chars: CharBox[];
	script: 'latin';
	direction: 'ltr' | 'rtl';
	confidence: number | null;
	alphaMaskPng: string | null;
	fontFamily: string | null;
	fontWeight: number | null;
	fontSize: number | null;
	letterSpacing: number;
	baselineY: number | null;
	textColor: RgbColor | null;
	background: BackgroundFill | null;
	alignment: 'left' | 'center' | 'right';
	lineHeight: number | null;
	uiElement: UiElement | null;
	fontCandidates: FontCandidateScore[];
}

interface EditorState {
	imageUrl: string | null;
	imageWidth: number;
	imageHeight: number;
	scaleFactor: 1 | 2 | 3;
	regions: Region[];
	selectedRegionId: string | null;
	status: 'idle' | 'analyzing' | 'error';
	errorMessage: string | null;
	debugMode: boolean;
	setImage: (url: string, width: number, height: number) => void;
	setRegions: (regions: Region[]) => void;
	setScaleFactor: (scaleFactor: 1 | 2 | 3) => void;
	selectRegion: (id: string | null) => void;
	setStatus: (status: EditorState['status'], errorMessage?: string | null) => void;
	toggleDebugMode: () => void;
	reset: () => void;
}

export const useEditorStore = create<EditorState>((set) => ({
	imageUrl: null,
	imageWidth: 0,
	imageHeight: 0,
	scaleFactor: 1,
	regions: [],
	selectedRegionId: null,
	status: 'idle',
	errorMessage: null,
	debugMode: false,
	setImage: (url, width, height) =>
		set({ imageUrl: url, imageWidth: width, imageHeight: height, regions: [], selectedRegionId: null }),
	setRegions: (regions) => set({ regions }),
	setScaleFactor: (scaleFactor) => set({ scaleFactor }),
	selectRegion: (id) => set({ selectedRegionId: id }),
	setStatus: (status, errorMessage = null) => set({ status, errorMessage }),
	toggleDebugMode: () => set((s) => ({ debugMode: !s.debugMode })),
	reset: () =>
		set({
			imageUrl: null,
			imageWidth: 0,
			imageHeight: 0,
			scaleFactor: 1,
			regions: [],
			selectedRegionId: null,
			status: 'idle',
			errorMessage: null,
			debugMode: false,
		}),
}));
