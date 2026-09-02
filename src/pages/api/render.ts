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

	const upstream = await fetch(`${serviceUrl}/render`, {
		method: 'POST',
		headers: { 'X-Pipeline-Secret': sharedSecret },
		body: formData,
	});

	const body = await upstream.text();

	return new Response(body, {
		status: upstream.status,
		headers: { 'Content-Type': 'application/json' },
	});
};
