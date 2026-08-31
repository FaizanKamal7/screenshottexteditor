import { create } from 'zustand';

export interface Region {
	id: string;
	text: string;
	bbox: [number, number, number, number];
	blockId: string;
	script: 'latin';
	direction: 'ltr' | 'rtl';
	confidence: number | null;
}

interface EditorState {
	imageUrl: string | null;
	imageWidth: number;
	imageHeight: number;
	regions: Region[];
	selectedRegionId: string | null;
	status: 'idle' | 'analyzing' | 'error';
	errorMessage: string | null;
	setImage: (url: string, width: number, height: number) => void;
	setRegions: (regions: Region[]) => void;
	selectRegion: (id: string | null) => void;
	setStatus: (status: EditorState['status'], errorMessage?: string | null) => void;
	reset: () => void;
}

export const useEditorStore = create<EditorState>((set) => ({
	imageUrl: null,
	imageWidth: 0,
	imageHeight: 0,
	regions: [],
	selectedRegionId: null,
	status: 'idle',
	errorMessage: null,
	setImage: (url, width, height) =>
		set({ imageUrl: url, imageWidth: width, imageHeight: height, regions: [], selectedRegionId: null }),
	setRegions: (regions) => set({ regions }),
	selectRegion: (id) => set({ selectedRegionId: id }),
	setStatus: (status, errorMessage = null) => set({ status, errorMessage }),
	reset: () =>
		set({
			imageUrl: null,
			imageWidth: 0,
			imageHeight: 0,
			regions: [],
			selectedRegionId: null,
			status: 'idle',
			errorMessage: null,
		}),
}));
