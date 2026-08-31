import { Canvas } from './Canvas';
import { Dropzone } from './Dropzone';
import { useEditorStore } from './store';

export function EditorIsland() {
	const imageUrl = useEditorStore((s) => s.imageUrl);

	return (
		<div className="flex h-screen w-screen items-center justify-center bg-canvas">
			{imageUrl ? <Canvas /> : <Dropzone />}
		</div>
	);
}
