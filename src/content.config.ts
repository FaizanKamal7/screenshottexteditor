import { defineCollection } from 'astro:content';
import { glob } from 'astro/loaders';
import { z } from 'zod';

const useCases = defineCollection({
	loader: glob({ pattern: '**/*.md', base: './src/content/use-cases' }),
	schema: z.object({
		title: z.string(),
		metaDescription: z.string(),
		platform: z.enum(['ios', 'android', 'web', 'general']),
		// Last meaningful content change (YYYY-MM-DD); feeds the sitemap's <lastmod>.
		updated: z.coerce.date(),
		eyebrow: z.string(),
		heroHeadline: z.string(),
		heroSubhead: z.string(),
		painPoints: z.array(z.string()),
		related: z.array(z.string()),
	}),
});

export const collections = { useCases };
