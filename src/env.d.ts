/// <reference types="astro/client" />

interface ImportMetaEnv {
	readonly PIPELINE_SERVICE_URL: string;
	readonly PIPELINE_SHARED_SECRET: string;
}

interface ImportMeta {
	readonly env: ImportMetaEnv;
}

declare module 'cloudflare:workers' {
	interface Env {
		PIPELINE_SERVICE_URL: string;
		PIPELINE_SHARED_SECRET: string;
	}
	export const env: Env;
}
