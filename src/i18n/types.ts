export interface FaqItem {
	question: string;
	answer: string;
}

export interface StepItem {
	title: string;
	body: string;
}

export interface ValueItem {
	title: string;
	body: string;
}

export interface ContactChannel {
	title: string;
	body: string;
}

export interface Translations {
	nav: {
		useCases: string;
		about: string;
		contact: string;
		openEditor: string;
		menu: string;
	};
	footer: {
		tagline: string;
		productHeading: string;
		openEditor: string;
		useCases: string;
		useCasesHeading: string;
		companyHeading: string;
		about: string;
		contact: string;
		privacy: string;
		terms: string;
		copyright: string;
	};
	languageSwitcher: {
		ariaLabel: string;
	};
	home: {
		metaTitle: string;
		metaDescription: string;
		heroEyebrow: string;
		heroTitleLine1: string;
		heroTitleLine2: string;
		heroSubtitle: string;
		ctaPrimary: string;
		ctaSecondary: string;
		heroFreeNote: string;

		diffEyebrow: string;
		diffTitle: string;
		diffP1: string;
		diffP2: string;
		matchConfidenceLabel: string;
		matchItem1: string;
		matchItem2: string;
		matchItem3: string;
		highConfidence: string;
		needsReview: string;

		howEyebrow: string;
		howTitle: string;
		steps: [StepItem, StepItem, StepItem];

		builtForEyebrow: string;
		builtForTitle: string;
		builtForP: string;
		builtForCta: string;
		csvLabel: string;

		privacyEyebrow: string;
		privacyTitle: string;
		privacyP: string;
		privacyLink1: string;
		privacyLink2: string;

		useCasesEyebrow: string;
		useCasesTitle: string;

		aboutToolEyebrow: string;
		aboutToolTitle: string;
		aboutToolP1: string;
		aboutToolP2: string;
		aboutToolH3a: string;
		aboutToolP3: string;
		aboutToolH3b: string;
		aboutToolP4: string;
		aboutToolH3c: string;
		aboutToolP5Pre: string;
		aboutToolP5LinkText: string;

		faqEyebrow: string;
		faqTitle: string;
		faqs: [FaqItem, FaqItem, FaqItem, FaqItem, FaqItem, FaqItem, FaqItem];
		faqFooterPre: string;
		faqFooterLinkText: string;
		faqFooterPost: string;

		finalTitle: string;
		finalSubtitle: string;
		finalCta: string;
	};
	about: {
		metaTitle: string;
		metaDescription: string;
		eyebrow: string;
		title: string;
		intro: string;
		p1: string;
		p2: string;
		buildingTowardTitle: string;
		buildingTowardPre: string;
		buildingTowardLinkText: string;
		buildingTowardPost: string;
		valuesEyebrow: string;
		valuesTitle: string;
		values: [ValueItem, ValueItem, ValueItem];
		howEyebrow: string;
		howTitle: string;
		howSteps: [StepItem, StepItem, StepItem];
		audienceTitle: string;
		audienceBody: string;
		ctaTitle: string;
		ctaSubtitle: string;
		ctaPrimary: string;
		ctaSecondary: string;
	};
	contact: {
		metaTitle: string;
		metaDescription: string;
		eyebrow: string;
		title: string;
		subtitle: string;
		supportChannel: ContactChannel;
		privacyChannel: ContactChannel;
		legalChannel: ContactChannel;
		includeEyebrow: string;
		includeTitle: string;
		includeItems: [ValueItem, ValueItem, ValueItem];
		faqEyebrow: string;
		faqTitle: string;
		faqs: [FaqItem, FaqItem, FaqItem];
		footerNote: string;
	};
}
