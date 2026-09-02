import type { Translations } from '../types';

export const en: Translations = {
	nav: {
		useCases: 'Use cases',
		pricing: 'Pricing',
		about: 'About',
		contact: 'Contact',
		openEditor: 'Open the editor',
		menu: 'Menu',
	},
	footer: {
		tagline: 'A deterministic pipeline for editing text in screenshots — pixel-indistinguishable from the original.',
		productHeading: 'Product',
		openEditor: 'Open the editor',
		pricing: 'Pricing',
		useCases: 'Use cases',
		useCasesHeading: 'Use cases',
		companyHeading: 'Company',
		about: 'About',
		contact: 'Contact',
		privacy: 'Privacy',
		terms: 'Terms',
		copyright: '© {year} ScreenshotTextEditor. All exports carry embedded content credentials marking them as edited.',
	},
	languageSwitcher: {
		ariaLabel: 'Change language',
	},
	home: {
		metaTitle: 'Screenshot Text Editor — Free Online AI Image Text Editor',
		metaDescription:
			'Edit text in any screenshot or image online with our free AI screenshot text editor. Matches font, size, weight, and color — no watermark, no signup required.',
		heroEyebrow: 'Pixel-accurate screenshot editing',
		heroTitleLine1: 'Edit text in a screenshot.',
		heroTitleLine2: 'Keep every other pixel exactly the same.',
		heroSubtitle:
			'Click any line of text in a screenshot, retype it, and match its font, size, weight, and color automatically — everything else stays pixel-for-pixel the same.',
		ctaPrimary: 'Open the editor',
		ctaSecondary: 'See it work',

		diffEyebrow: 'Why this is different',
		diffTitle: 'A deterministic pipeline, not a generated guess.',
		diffP1:
			"Most text-in-image tools lean on generative image models — great at photos and posters, unreliable on small, crisp UI text where every pixel of a letterform matters. We built the opposite: six discrete, testable stages that detect, measure, and reproduce the actual font rather than paint something plausible over it.",
		diffP2:
			"Every match carries a confidence score. If we can't reproduce your original text closely enough to trust the result, we tell you — instead of shipping an edit that looks wrong at a glance.",
		matchConfidenceLabel: 'Match confidence',
		matchItem1: '"Continue" — SF Pro fallback, 17px',
		matchItem2: '"$48.20" — Inter, 14px',
		matchItem3: '"Settings" — condensed, unmatched',
		highConfidence: 'high confidence',
		needsReview: 'needs review',

		howEyebrow: 'How it works',
		howTitle: 'Detect, match, rebuild.',
		steps: [
			{
				title: '1. Detect',
				body: 'OCR finds every text run at the line level, with per-character boxes and the image scale factor — 1x, 2x, or 3x — measured from the glyphs themselves.',
			},
			{
				title: '2. Match',
				body: 'Your original text is rendered in a short list of platform-likely fonts and scored against a real alpha mask until the closest font, size, weight, and spacing is found — with the score shown, not hidden.',
			},
			{
				title: '3. Rebuild',
				body: 'The old text is erased with a matching fill and your replacement is rendered at the same baseline and anti-aliasing, then re-verified against the original before it ships.',
			},
		],

		builtForEyebrow: 'Built for',
		builtForTitle: 'App Store & Play Store localization.',
		builtForP:
			'Eight screenshots, twenty languages — today that means rebuilding every screenshot in Figma for every locale. Upload once, hand us a CSV of translations, and download a ZIP with every language rendered in the original font and layout, reflowed automatically when translated text runs long.',
		builtForCta: 'See how localization works →',
		csvLabel: 'screenshots_de.csv',

		privacyEyebrow: 'Privacy',
		privacyTitle: "Your screenshots aren't the product.",
		privacyP:
			'Screenshots often carry account data, customer names, or internal numbers. Uploads are deleted automatically — one hour by default — and we never train on user images. Every export also carries embedded content credentials marking it as edited, so an edited screenshot never quietly passes as an original.',
		privacyLink1: 'Read the privacy policy →',
		privacyLink2: 'Read the terms of service →',

		useCasesEyebrow: 'Use cases',
		useCasesTitle: 'One pipeline, every screenshot.',

		aboutToolEyebrow: 'About the tool',
		aboutToolTitle: 'What is a screenshot text editor?',
		aboutToolP1:
			'ScreenshotTextEditor is a <strong class="text-ink">screenshot text editor</strong> built to solve one very specific problem: changing the words in a screenshot without changing anything else about it. Most people who search for a <strong class="text-ink">screenshot editor online</strong> run into the same wall — generic photo editors can crop, blur, or annotate a screenshot, but the moment you try to swap out a line of text, the font is wrong, the spacing shifts, or the background behind the old text turns into a smudge. This tool was built around a different idea: detect the exact font, size, weight, and color of every text run in the image, then rebuild it so precisely that the edit is invisible at 400% zoom.',
		aboutToolP2:
			"As a <strong class=\"text-ink\">screenshot text editor online</strong>, it runs entirely in the browser — there's nothing to install, no plugin, and no design software required. Upload a screenshot or any image with text, click the line you want to change, type your replacement, and download the result. Because it's a <strong class=\"text-ink\">free screenshot editor</strong> for single images, you can try the full pipeline — detection, font-matching, and rebuild — without creating an account. It's a <strong class=\"text-ink\">screenshot text editor online free without watermark</strong>, so what you export is exactly what you see, with no branding stamped over your work.",
		aboutToolH3a: 'AI screenshot editor, not a generic filter',
		aboutToolP3:
			"Calling this an <strong class=\"text-ink\">AI screenshot editor</strong> undersells what's actually happening under the hood. Instead of asking a generative image model to hallucinate plausible-looking text — a shortcut that tends to fall apart on small, crisp UI fonts — this <strong class=\"text-ink\">screenshot text editor AI</strong> pipeline runs six discrete, testable stages. First, OCR detects every text run at the character level and measures the image's scale factor directly from the glyphs. Then the tool renders your source text in a shortlist of platform-likely fonts and scores each candidate against the real pixel mask until it finds the closest match for font family, size, weight, and letter spacing. Only then does it erase the old text with a matching fill and render your replacement at the same baseline and anti-aliasing settings. Every match carries a visible confidence score, so if the <strong class=\"text-ink\">screenshot text editor AI free</strong> pipeline can't reproduce your original text closely enough to trust, it tells you — instead of quietly shipping an edit that looks off.",
		aboutToolH3b: 'More than a screenshot editor — a full image text editor online',
		aboutToolP4:
			'While it started as a screenshot text editor, the same pipeline works as a general-purpose <strong class="text-ink">image text editor online</strong>. Any PNG, JPG, or exported UI mockup with text can be processed the same way — as an <strong class="text-ink">AI image text editor</strong> for marketing graphics, dashboard exports with stale numbers, or App Store screenshots that need to be localized into another language. Because it\'s a <strong class="text-ink">free online image text editor</strong>, teams that would otherwise rebuild every screenshot by hand in Figma for each locale can instead upload once, hand over a CSV of translations, and download every language variant rendered in the original font and layout.',
		aboutToolH3c: 'Why teams choose this online text editor for screenshots',
		aboutToolP5Pre:
			'Whether you need a quick typo fix, a redacted customer name before a demo, or a batch of localized App Store screenshots, this <strong class="text-ink">screenshot editor online</strong> is built to make the edit disappear rather than stand out. It\'s free to try, doesn\'t require a design background, deletes your uploads automatically, and never trains on the images you upload — so the only thing that changes in your screenshot is the text you meant to change. Read more about',
		aboutToolP5LinkText: 'why we built it this way',

		faqEyebrow: 'FAQ',
		faqTitle: 'Frequently asked questions.',
		faqs: [
			{
				question: 'How to use an image text editor online?',
				answer:
					'Open the ScreenshotTextEditor editor and drop in your screenshot or image — no signup needed. Our AI screenshot editor scans the image, detects every text run, and lets you click any line to rewrite it. Type your replacement, and the tool automatically matches the original font, size, weight, color, and anti-aliasing before rebuilding the image around your new text. Export it as a PNG or JPG in seconds, all from your browser.',
			},
			{
				question: 'How to remove text from image using AI editor?',
				answer:
					'Select the text run you want to remove and either delete its contents or use the erase option. The AI image text editor fills the area behind the old text with a matching background — reconstructing color, texture, and gradients — so there is no visible patch, blur, or watermark left behind. This works for UI labels, captions, timestamps, or any text layer detected in the image.',
			},
			{
				question: 'How does an online image text editor work?',
				answer:
					'Our online image text editor runs a detection → match → rebuild pipeline. First, OCR locates every text run at the line and character level and measures the image scale factor. Next, it renders your text in a shortlist of likely fonts and scores each one against the real pixels until it finds the closest font, size, weight, and spacing. Finally, it erases the original text with a matching fill and renders your replacement at the same baseline, so the result survives close inspection.',
			},
			{
				question: 'How to edit text on a screenshot?',
				answer:
					'Upload your screenshot to the screenshot text editor, click the text you want to change, and type the new copy. The tool keeps every other pixel — icons, buttons, backgrounds, and layout — exactly as it was, only rebuilding the text region itself. It works entirely online, with no design software or manual font-matching required.',
			},
			{
				question: 'How to edit text on a screenshot iPhone?',
				answer:
					'Take your screenshot on iPhone as usual, then upload it to ScreenshotTextEditor from Safari or Chrome on your phone or by AirDropping it to a computer first. Because the screenshot text editor runs entirely online in the browser, there is no app to install — open the editor on any device, select the text, replace it, and download the edited screenshot directly to your iPhone or camera roll.',
			},
			{
				question: 'Is editing text in screenshot free?',
				answer:
					'Yes. You can try the screenshot text editor online free, without a watermark, with no account required — uploads are processed and then automatically deleted within an hour. Higher-volume workflows like bulk App Store localization are available on paid plans, but single-image editing is free to use.',
			},
			{
				question: 'Is it possible to change text of any image or just screenshot?',
				answer:
					'You can edit text in any image, not only screenshots. The same detection, font-matching, and rebuild pipeline works on UI mockups, marketing graphics, dashboard exports, PNGs, and photos that contain text — anywhere the tool can detect a text run, it can replace it while preserving the original look.',
			},
		],
		faqFooterPre: 'Still have questions?',
		faqFooterLinkText: 'Contact us',
		faqFooterPost: '— we read every message.',

		finalTitle: 'Try it on your own screenshot.',
		finalSubtitle: 'No account needed to try it. Deleted automatically after an hour.',
		finalCta: 'Open the editor',
	},
	pricing: {
		metaTitle: 'Pricing — ScreenshotTextEditor',
		metaDescription:
			'Simple pricing for screenshot text editing and App Store localization — from a free trial to team plans with batch CSV localization.',
		eyebrow: 'Pricing',
		title: 'Simple pricing, no surprise seats.',
		subtitle:
			'Every tier gets the same deterministic pipeline and confidence scoring. Higher tiers unlock volume and the batch localization workflow. No tier ever removes the embedded content credentials on an export.',
		freeTier: {
			name: 'Free',
			period: '',
			description: 'Try it on a real screenshot before you commit to anything.',
			features: [
				'10 renders / month',
				'Single-image editor',
				'Confidence scoring & manual font override',
				'PNG and JPEG in, PNG out',
				'Uploads deleted after 1 hour',
			],
			ctaLabel: 'Open the editor',
		},
		proTier: {
			name: 'Pro',
			period: '/ month',
			description: 'For teams shipping localized screenshots on a schedule.',
			features: [
				'Unlimited single-image edits',
				'CSV batch localization — upload once, export a ZIP per language',
				'Confidence scoring & manual font override',
				'Priority processing',
				'Everything in Free',
			],
			ctaLabel: 'Start with Pro',
		},
		teamTier: {
			name: 'Team',
			period: '/ seat / month',
			description: 'Shared batch jobs and priority support across a team.',
			features: ['Everything in Pro, per seat', 'Shared batch localization jobs', 'Priority support', 'Early access to the API'],
			ctaLabel: 'Talk to us',
		},
		notHereYetTitle: "What's not here yet",
		notHereYetPre:
			'Text over photos and complex textures, CJK and RTL scripts, gradient or stroked text, drop shadows, a Figma plugin, and a public API are all on the roadmap but not shipped in v1 — see the',
		notHereYetLinkText: 'terms',
		notHereYetPost: 'for the current scope.',
	},
	about: {
		metaTitle: 'About — ScreenshotTextEditor',
		metaDescription:
			'Why we built ScreenshotTextEditor: a deterministic detect-match-rebuild pipeline for editing text in screenshots, instead of a generative guess.',
		eyebrow: 'About',
		title: 'About ScreenshotTextEditor',
		intro:
			'We build tools for the specific, annoying problem of changing the words in a screenshot without changing anything else about it.',
		p1: 'ScreenshotTextEditor started from a narrow frustration: fixing a typo, redacting a customer name, or localizing an App Store screenshot always meant re-opening a design file that no longer existed, or settling for a generative "AI" edit that got the font wrong and blurred the background behind it. Generic photo editors handle crops and blurs well; they fall apart the moment a single line of small, crisp UI text needs to change and everything around it needs to stay pixel-identical.',
		p2: 'So we built the opposite of a generative shortcut: a deterministic pipeline that detects every text run in an image, measures its actual font, size, weight, and color, and rebuilds only that region — verified against the original before it ships.',
		buildingTowardTitle: "What we're building toward",
		buildingTowardPre:
			"Today that's a free, no-signup single-image editor and a batch localization workflow for App Store and Play Store screenshots. Both run on the same detect → match → rebuild pipeline described on the",
		buildingTowardLinkText: 'homepage',
		buildingTowardPost: '.',
		valuesEyebrow: 'What we care about',
		valuesTitle: 'Principles behind the pipeline.',
		values: [
			{
				title: 'Deterministic over generative',
				body: 'We built six discrete, testable stages instead of asking a generative model to hallucinate plausible text. Small, crisp UI fonts don’t survive a guess.',
			},
			{
				title: 'Show the confidence, not just the result',
				body: 'Every font match carries a visible confidence score. If we can’t reproduce your text closely enough to trust, we say so instead of shipping a bad edit.',
			},
			{
				title: 'Your screenshots aren’t the product',
				body: 'Uploads are deleted automatically and we never train on user images. Every export carries embedded content credentials marking it as edited.',
			},
		],
		ctaTitle: 'Questions, feedback, or a bug to report?',
		ctaSubtitle: 'We read everything that comes in through the contact page.',
		ctaPrimary: 'Contact us',
		ctaSecondary: 'Open the editor',
	},
	contact: {
		metaTitle: 'Contact — ScreenshotTextEditor',
		metaDescription: 'Get in touch with ScreenshotTextEditor for support, privacy questions, or anything about the screenshot text editing pipeline.',
		eyebrow: 'Contact',
		title: 'Get in touch',
		subtitle: "Pick the address that fits — we read everything and reply from a real person, not a ticket bot.",
		supportChannel: {
			title: 'Support',
			body: 'Bugs, low-confidence matches, or anything not working the way it should.',
		},
		privacyChannel: {
			title: 'Privacy',
			body: 'Questions about what we collect, how long we keep it, or a deletion request.',
		},
		legalChannel: {
			title: 'Legal',
			body: 'Terms of service, acceptable use, or content credential questions.',
		},
		footerNote:
			"Reporting a specific edit that didn't come out right? Include the original screenshot and, if you still have it, the exported result — it's the fastest way for us to reproduce and fix it.",
	},
};
