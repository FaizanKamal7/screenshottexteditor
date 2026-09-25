import type { ClientDirective } from 'astro';

// `client:afterload` — hydrates only after the window load event, an idle slot, and the island
// scrolling into view. `client:visible` alone fired as soon as first layout put the home-page demo
// in the mobile viewport, so React (~60 KB gzip) downloaded and ran before the hero text counted as
// painted, pushing mobile FCP/LCP back by ~0.6s. The server-rendered markup is already on screen
// and links to /app, so waiting only delays the animation, not anything the visitor can use.
const afterLoadDirective: ClientDirective = (load, _options, el) => {
	const hydrate = async () => {
		const hydrator = await load();
		await hydrator();
	};

	const hydrateWhenVisible = () => {
		const io = new IntersectionObserver((entries) => {
			if (!entries.some((entry) => entry.isIntersecting)) return;
			io.disconnect();
			hydrate();
		});
		for (const child of el.children) io.observe(child);
	};

	const afterIdle = () => {
		if ('requestIdleCallback' in window) window.requestIdleCallback(hydrateWhenVisible, { timeout: 2000 });
		else setTimeout(hydrateWhenVisible, 200);
	};

	if (document.readyState === 'complete') afterIdle();
	else window.addEventListener('load', afterIdle, { once: true });
};

export default afterLoadDirective;

declare module 'astro' {
	interface AstroClientDirectives {
		'client:afterload'?: boolean;
	}
}
