import react from '@vitejs/plugin-react';
import { defineConfig } from 'vitest/config';

// Standalone from astro.config.mjs deliberately — the Astro/Cloudflare vite
// plugins aren't needed to unit-test src/editor's store and components, and
// pulling in the cloudflare() adapter here would require a workers runtime
// this test environment doesn't have. @vitejs/plugin-react (rather than a
// bare esbuild.jsx option) is what actually gets JSX transformed under this
// Vite version's SSR module pipeline, which vitest's jsdom environment runs
// through.
export default defineConfig({
	plugins: [react()],
	test: {
		environment: 'jsdom',
		globals: false,
		include: ['src/**/*.test.{ts,tsx}'],
	},
});
