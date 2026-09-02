import type { APIRoute } from 'astro';
import { env } from 'cloudflare:workers';

export const prerender = false;

export const POST: APIRoute = async ({ request }) => {
	const serviceUrl = env.PIPELINE_SERVICE_URL;
	const sharedSecret = env.PIPELINE_SHARED_SECRET;

	if (!serviceUrl || !sharedSecret) {
		return new Response(JSON.stringify({ error: 'pipeline service not configured' }), {
			status: 500,
			headers: { 'Content-Type': 'application/json' },
		});
	}

	const formData = await request.formData();

	const upstream = await fetch(`${serviceUrl}/analyze`, {
		method: 'POST',
		headers: { 'X-Pipeline-Secret': sharedSecret },
		body: formData,
	});

	// Streamed through rather than buffered (no `await upstream.text()`): the
	// pipeline service now sends NDJSON progress lines as each detected text
	// region finishes, and buffering here would throw that progress away.
	return new Response(upstream.body, {
		status: upstream.status,
		headers: { 'Content-Type': 'application/x-ndjson' },
	});
};
