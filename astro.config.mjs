// @ts-check
import cloudflare from '@astrojs/cloudflare';
import react from '@astrojs/react';
import tailwindcss from '@tailwindcss/vite';
import { defineConfig } from 'astro/config';

// https://astro.build/config
export default defineConfig({
	site: 'https://screenshottexteditor.com',
	output: 'server',
	adapter: cloudflare(),
	integrations: [
		react(),
		{
			name: 'client-afterload-directive',
			hooks: {
				'astro:config:setup': ({ addClientDirective }) => {
					addClientDirective({
						name: 'afterload',
						entrypoint: './src/directives/afterload.ts',
					});
				},
			},
		},
	],
	vite: {
		plugins: [tailwindcss()],
	},
});
