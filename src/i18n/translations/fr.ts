import type { Translations } from '../types';

export const fr: Translations = {
	nav: {
		useCases: "Cas d'usage",
		pricing: 'Tarifs',
		about: 'À propos',
		contact: 'Contact',
		openEditor: "Ouvrir l'éditeur",
		menu: 'Menu',
	},
	footer: {
		tagline: "Un pipeline déterministe pour modifier le texte dans des captures d'écran — indiscernable de l'original, pixel par pixel.",
		productHeading: 'Produit',
		openEditor: "Ouvrir l'éditeur",
		pricing: 'Tarifs',
		useCases: "Cas d'usage",
		useCasesHeading: "Cas d'usage",
		companyHeading: 'Entreprise',
		about: 'À propos',
		contact: 'Contact',
		privacy: 'Confidentialité',
		terms: 'Conditions',
		copyright: '© {year} ScreenshotTextEditor. Chaque export porte des identifiants de contenu intégrés indiquant qu\'il a été modifié.',
	},
	languageSwitcher: {
		ariaLabel: 'Changer de langue',
	},
	home: {
		metaTitle: "Éditeur de texte pour captures d'écran — Éditeur de texte d'image IA gratuit en ligne",
		metaDescription:
			"Modifiez le texte de n'importe quelle capture d'écran ou image en ligne avec notre éditeur de texte IA gratuit. Police, taille, graisse et couleur ajustées automatiquement — sans filigrane, sans inscription.",
		heroEyebrow: "Édition de captures d'écran au pixel près",
		heroTitleLine1: "Modifiez le texte d'une capture d'écran.",
		heroTitleLine2: 'Gardez chaque autre pixel exactement identique.',
		heroSubtitle:
			"Cliquez sur n'importe quelle ligne de texte d'une capture d'écran, retapez-la, et sa police, taille, graisse et couleur s'ajustent automatiquement — tout le reste reste identique, pixel pour pixel.",
		ctaPrimary: "Ouvrir l'éditeur",
		ctaSecondary: 'Voir comment ça marche',

		diffEyebrow: 'Pourquoi c\'est différent',
		diffTitle: 'Un pipeline déterministe, pas une supposition générée.',
		diffP1:
			"La plupart des outils de texte dans l'image s'appuient sur des modèles génératifs — excellents sur les photos et les affiches, peu fiables sur du texte d'interface petit et net où chaque pixel d'une lettre compte. Nous avons construit l'inverse : six étapes distinctes et testables qui détectent, mesurent et reproduisent la police réelle plutôt que de peindre quelque chose de plausible par-dessus.",
		diffP2:
			"Chaque correspondance porte un score de confiance. Si nous ne pouvons pas reproduire votre texte original avec une fidélité suffisante, nous vous le disons — plutôt que de livrer une modification visiblement fausse.",
		matchConfidenceLabel: 'Confiance de la correspondance',
		matchItem1: '« Continue » — repli SF Pro, 17px',
		matchItem2: '« 48,20 $ » — Inter, 14px',
		matchItem3: '« Settings » — condensée, sans correspondance',
		highConfidence: 'confiance élevée',
		needsReview: 'à vérifier',

		howEyebrow: 'Comment ça marche',
		howTitle: 'Détecter, faire correspondre, reconstruire.',
		steps: [
			{
				title: '1. Détecter',
				body: "L'OCR trouve chaque fragment de texte au niveau de la ligne, avec des zones par caractère et le facteur d'échelle de l'image — 1x, 2x ou 3x — mesuré à partir des glyphes eux-mêmes.",
			},
			{
				title: '2. Faire correspondre',
				body: "Votre texte original est rendu avec une courte liste de polices probables selon la plateforme et noté face à un masque alpha réel jusqu'à trouver la police, la taille, la graisse et l'espacement les plus proches — score affiché, pas caché.",
			},
			{
				title: '3. Reconstruire',
				body: "L'ancien texte est effacé avec un remplissage assorti et votre texte de remplacement est rendu sur la même ligne de base et le même lissage, puis revérifié par rapport à l'original avant livraison.",
			},
		],

		builtForEyebrow: 'Conçu pour',
		builtForTitle: "La localisation App Store et Play Store.",
		builtForP:
			"Huit captures, vingt langues — aujourd'hui, cela signifie reconstruire chaque capture dans Figma pour chaque langue. Importez une fois, donnez-nous un CSV de traductions, et téléchargez un ZIP avec chaque langue rendue dans la police et la mise en page d'origine, réajusté automatiquement quand le texte traduit est plus long.",
		builtForCta: 'Voir comment fonctionne la localisation →',
		csvLabel: 'screenshots_de.csv',

		privacyEyebrow: 'Confidentialité',
		privacyTitle: "Vos captures d'écran ne sont pas le produit.",
		privacyP:
			"Les captures d'écran contiennent souvent des données de compte, des noms de clients ou des chiffres internes. Les fichiers importés sont supprimés automatiquement — une heure par défaut — et nous n'entraînons jamais de modèle sur les images des utilisateurs. Chaque export porte aussi des identifiants de contenu intégrés indiquant qu'il a été modifié, afin qu'une capture modifiée ne puisse jamais passer discrètement pour un original.",
		privacyLink1: 'Lire la politique de confidentialité →',
		privacyLink2: 'Lire les conditions d\'utilisation →',

		useCasesEyebrow: "Cas d'usage",
		useCasesTitle: 'Un seul pipeline, toutes les captures.',

		aboutToolEyebrow: "À propos de l'outil",
		aboutToolTitle: "Qu'est-ce qu'un éditeur de texte pour captures d'écran ?",
		aboutToolP1:
			'ScreenshotTextEditor est un <strong class="text-ink">éditeur de texte pour captures d\'écran</strong> conçu pour résoudre un problème très précis : changer les mots d\'une capture d\'écran sans rien changer d\'autre. La plupart des personnes qui cherchent un <strong class="text-ink">éditeur de captures d\'écran en ligne</strong> se heurtent au même mur — les éditeurs de photos génériques savent recadrer, flouter ou annoter une capture, mais dès qu\'on essaie de remplacer une ligne de texte, la police est fausse, l\'espacement se décale, ou le fond derrière l\'ancien texte devient une tache. Cet outil a été conçu autour d\'une idée différente : détecter la police, la taille, la graisse et la couleur exactes de chaque fragment de texte de l\'image, puis le reconstruire avec une précision telle que la modification est invisible même à un zoom de 400 %.',
		aboutToolP2:
			"En tant qu'<strong class=\"text-ink\">éditeur de texte pour captures d'écran en ligne</strong>, il fonctionne entièrement dans le navigateur — rien à installer, aucun plugin, aucun logiciel de design requis. Importez une capture ou toute image contenant du texte, cliquez sur la ligne à modifier, tapez votre remplacement, et téléchargez le résultat. Comme c'est un <strong class=\"text-ink\">éditeur de captures gratuit</strong> pour les images uniques, vous pouvez essayer tout le pipeline — détection, correspondance de police et reconstruction — sans créer de compte. C'est un <strong class=\"text-ink\">éditeur de texte pour captures d'écran en ligne, gratuit et sans filigrane</strong>, donc ce que vous exportez est exactement ce que vous voyez, sans logo estampillé sur votre travail.",
		aboutToolH3a: "Un éditeur de captures IA, pas un filtre générique",
		aboutToolP3:
			"Parler d'<strong class=\"text-ink\">éditeur de captures d'écran IA</strong> ne rend pas justice à ce qui se passe réellement en coulisses. Plutôt que de demander à un modèle génératif d'image d'halluciner un texte à l'apparence plausible — un raccourci qui a tendance à échouer sur les polices d'interface petites et nettes — ce pipeline d'<strong class=\"text-ink\">édition de texte par IA pour captures d'écran</strong> exécute six étapes distinctes et testables. D'abord, l'OCR détecte chaque fragment de texte au niveau du caractère et mesure le facteur d'échelle de l'image directement à partir des glyphes. Ensuite, l'outil rend votre texte source dans une courte liste de polices probables selon la plateforme et note chaque candidate face au masque de pixels réel jusqu'à trouver la meilleure correspondance de famille de police, taille, graisse et espacement des lettres. Ce n'est qu'alors qu'il efface l'ancien texte avec un remplissage assorti et rend votre remplacement avec la même ligne de base et le même lissage. Chaque correspondance porte un score de confiance visible, donc si le pipeline d'<strong class=\"text-ink\">édition de texte par IA gratuite pour captures d'écran</strong> ne peut pas reproduire votre texte original avec assez de fiabilité, il vous le dit — plutôt que de livrer discrètement une modification qui sonne faux.",
		aboutToolH3b: "Plus qu'un éditeur de captures — un véritable éditeur de texte d'image en ligne",
		aboutToolP4:
			"Bien qu'il ait commencé comme éditeur de texte pour captures d'écran, le même pipeline fonctionne comme <strong class=\"text-ink\">éditeur de texte d'image en ligne</strong> généraliste. N'importe quel PNG, JPG ou maquette d'interface exportée contenant du texte peut être traité de la même façon — comme un <strong class=\"text-ink\">éditeur de texte d'image par IA</strong> pour des visuels marketing, des exports de tableaux de bord avec des chiffres obsolètes, ou des captures d'App Store à localiser dans une autre langue. Comme c'est un <strong class=\"text-ink\">éditeur de texte d'image en ligne gratuit</strong>, les équipes qui reconstruiraient sinon chaque capture à la main dans Figma pour chaque langue peuvent à la place importer une fois, fournir un CSV de traductions, et télécharger chaque variante linguistique rendue dans la police et la mise en page d'origine.",
		aboutToolH3c: "Pourquoi les équipes choisissent cet éditeur de texte en ligne pour captures d'écran",
		aboutToolP5Pre:
			"Que vous ayez besoin de corriger rapidement une coquille, de masquer le nom d'un client avant une démo, ou de produire un lot de captures d'App Store localisées, cet <strong class=\"text-ink\">éditeur de captures en ligne</strong> est conçu pour que la modification passe inaperçue plutôt que de se voir. C'est gratuit à essayer, ça ne demande aucune compétence en design, vos fichiers sont supprimés automatiquement, et aucun modèle n'est jamais entraîné sur les images que vous importez — la seule chose qui change dans votre capture est le texte que vous vouliez changer. En savoir plus sur",
		aboutToolP5LinkText: 'pourquoi nous l\'avons conçu ainsi',

		faqEyebrow: 'FAQ',
		faqTitle: 'Questions fréquentes.',
		faqs: [
			{
				question: "Comment utiliser un éditeur de texte d'image en ligne ?",
				answer:
					"Ouvrez l'éditeur ScreenshotTextEditor et déposez-y votre capture d'écran ou image — aucune inscription requise. Notre éditeur de captures IA analyse l'image, détecte chaque fragment de texte et vous permet de cliquer sur n'importe quelle ligne pour la réécrire. Tapez votre remplacement, et l'outil ajuste automatiquement la police, la taille, la graisse, la couleur et le lissage d'origine avant de reconstruire l'image autour de votre nouveau texte. Exportez-la en PNG ou JPG en quelques secondes, le tout depuis votre navigateur.",
			},
			{
				question: "Comment supprimer du texte d'une image avec un éditeur IA ?",
				answer:
					"Sélectionnez le fragment de texte à supprimer et supprimez son contenu ou utilisez l'option d'effacement. L'éditeur de texte d'image par IA remplit la zone derrière l'ancien texte avec un fond assorti — en reconstruisant couleur, texture et dégradés — de sorte qu'il ne reste aucune tache visible, flou ni filigrane. Cela fonctionne pour les libellés d'interface, les légendes, les horodatages ou toute couche de texte détectée dans l'image.",
			},
			{
				question: "Comment fonctionne un éditeur de texte d'image en ligne ?",
				answer:
					"Notre éditeur de texte d'image en ligne exécute un pipeline détection → correspondance → reconstruction. D'abord, l'OCR localise chaque fragment de texte au niveau de la ligne et du caractère et mesure le facteur d'échelle de l'image. Ensuite, il rend votre texte dans une courte liste de polices probables et note chacune face aux vrais pixels jusqu'à trouver la police, la taille, la graisse et l'espacement les plus proches. Enfin, il efface le texte original avec un remplissage assorti et rend votre remplacement sur la même ligne de base, afin que le résultat résiste à un examen rapproché.",
			},
			{
				question: "Comment modifier le texte d'une capture d'écran ?",
				answer:
					"Importez votre capture dans l'éditeur de texte pour captures d'écran, cliquez sur le texte à modifier et tapez le nouveau contenu. L'outil conserve chaque autre pixel — icônes, boutons, arrière-plans et mise en page — exactement tel quel, en ne reconstruisant que la zone de texte. Cela fonctionne entièrement en ligne, sans logiciel de design ni ajustement manuel de police.",
			},
			{
				question: "Comment modifier le texte d'une capture d'écran sur iPhone ?",
				answer:
					"Prenez votre capture sur iPhone comme d'habitude, puis importez-la dans ScreenshotTextEditor depuis Safari ou Chrome sur votre téléphone, ou envoyez-la d'abord par AirDrop vers un ordinateur. Comme l'éditeur de captures fonctionne entièrement en ligne dans le navigateur, aucune application à installer — ouvrez l'éditeur sur n'importe quel appareil, sélectionnez le texte, remplacez-le et téléchargez la capture modifiée directement sur votre iPhone ou dans votre pellicule.",
			},
			{
				question: "Modifier le texte d'une capture d'écran est-il gratuit ?",
				answer:
					"Oui. Vous pouvez essayer l'éditeur de texte pour captures d'écran en ligne gratuitement, sans filigrane, sans compte requis — les fichiers importés sont traités puis automatiquement supprimés en une heure. Les flux à plus fort volume, comme la localisation en masse pour App Store, sont disponibles sur les forfaits payants, mais la modification d'une seule image reste gratuite.",
			},
			{
				question: "Peut-on changer le texte de n'importe quelle image, ou seulement des captures d'écran ?",
				answer:
					"Vous pouvez modifier le texte de n'importe quelle image, pas seulement des captures d'écran. Le même pipeline de détection, correspondance de police et reconstruction fonctionne sur des maquettes d'interface, des visuels marketing, des exports de tableaux de bord, des PNG et des photos contenant du texte — partout où l'outil peut détecter un fragment de texte, il peut le remplacer tout en préservant l'apparence d'origine.",
			},
		],
		faqFooterPre: "Encore des questions ?",
		faqFooterLinkText: 'Contactez-nous',
		faqFooterPost: '— nous lisons chaque message.',

		finalTitle: 'Essayez-le sur votre propre capture d\'écran.',
		finalSubtitle: "Aucun compte requis pour l'essayer. Supprimée automatiquement au bout d'une heure.",
		finalCta: "Ouvrir l'éditeur",
	},
	pricing: {
		metaTitle: 'Tarifs — ScreenshotTextEditor',
		metaDescription:
			"Des tarifs simples pour l'édition de texte dans les captures d'écran et la localisation App Store — d'un essai gratuit aux forfaits d'équipe avec localisation par lot CSV.",
		eyebrow: 'Tarifs',
		title: 'Des tarifs simples, sans mauvaise surprise par poste.',
		subtitle:
			"Chaque forfait bénéficie du même pipeline déterministe et du même score de confiance. Les forfaits supérieurs débloquent plus de volume et le flux de localisation par lot. Aucun forfait ne retire les identifiants de contenu intégrés à un export.",
		freeTier: {
			name: 'Gratuit',
			period: '',
			description: "Testez-le sur une vraie capture d'écran avant de vous engager.",
			features: [
				'10 rendus / mois',
				'Éditeur pour image unique',
				'Score de confiance et remplacement manuel de police',
				'Import PNG et JPEG, export PNG',
				'Fichiers supprimés après 1 heure',
			],
			ctaLabel: "Ouvrir l'éditeur",
		},
		proTier: {
			name: 'Pro',
			period: '/ mois',
			description: "Pour les équipes qui livrent des captures localisées régulièrement.",
			features: [
				'Modifications d\'image unique illimitées',
				'Localisation par lot CSV — importez une fois, exportez un ZIP par langue',
				'Score de confiance et remplacement manuel de police',
				'Traitement prioritaire',
				'Tout ce qui est inclus dans Gratuit',
			],
			ctaLabel: 'Commencer avec Pro',
		},
		teamTier: {
			name: 'Équipe',
			period: '/ poste / mois',
			description: "Traitements par lot partagés et support prioritaire pour toute l'équipe.",
			features: ['Tout ce qui est inclus dans Pro, par poste', 'Tâches de localisation par lot partagées', 'Support prioritaire', "Accès anticipé à l'API"],
			ctaLabel: 'Nous contacter',
		},
		notHereYetTitle: "Ce qui n'est pas encore disponible",
		notHereYetPre:
			"Le texte sur photos et textures complexes, les écritures CJK et RTL, le texte en dégradé ou avec contour, les ombres portées, un plugin Figma et une API publique sont tous sur la feuille de route mais pas encore livrés en v1 — consultez les",
		notHereYetLinkText: 'conditions',
		notHereYetPost: 'pour connaître le périmètre actuel.',
	},
	about: {
		metaTitle: 'À propos — ScreenshotTextEditor',
		metaDescription:
			"Pourquoi nous avons créé ScreenshotTextEditor : un pipeline déterministe de détection-correspondance-reconstruction pour modifier le texte dans les captures d'écran, plutôt qu'une supposition générative.",
		eyebrow: 'À propos',
		title: 'À propos de ScreenshotTextEditor',
		intro:
			"Nous concevons des outils pour ce problème précis et agaçant : changer les mots d'une capture d'écran sans rien changer d'autre.",
		p1: "ScreenshotTextEditor est né d'une frustration bien précise : corriger une coquille, masquer le nom d'un client ou localiser une capture d'App Store obligeait toujours à rouvrir un fichier de design qui n'existait plus, ou à se contenter d'une modification « IA » générative qui se trompait de police et floutait le fond derrière le texte. Les éditeurs de photos génériques gèrent bien les recadrages et les flous ; ils échouent dès qu'une seule ligne de texte d'interface petit et net doit changer alors que tout le reste doit rester identique au pixel près.",
		p2: "Nous avons donc construit l'inverse d'un raccourci génératif : un pipeline déterministe qui détecte chaque fragment de texte d'une image, mesure sa police, sa taille, sa graisse et sa couleur réelles, et ne reconstruit que cette zone — vérifiée par rapport à l'original avant livraison.",
		buildingTowardTitle: 'Vers quoi nous allons',
		buildingTowardPre:
			"Aujourd'hui, cela signifie un éditeur d'image unique gratuit et sans inscription, ainsi qu'un flux de localisation par lot pour les captures App Store et Play Store. Les deux reposent sur le même pipeline détecter → faire correspondre → reconstruire décrit sur la",
		buildingTowardLinkText: "page d'accueil",
		buildingTowardPost: '.',
		valuesEyebrow: 'Ce qui compte pour nous',
		valuesTitle: 'Les principes derrière le pipeline.',
		values: [
			{
				title: 'Déterministe plutôt que génératif',
				body: "Nous avons construit six étapes distinctes et testables plutôt que de demander à un modèle génératif d'halluciner un texte plausible. Les polices d'interface petites et nettes ne survivent pas à une supposition.",
			},
			{
				title: 'Montrer la confiance, pas seulement le résultat',
				body: "Chaque correspondance de police porte un score de confiance visible. Si nous ne pouvons pas reproduire votre texte avec assez de fiabilité, nous vous le disons plutôt que de livrer une mauvaise modification.",
			},
			{
				title: "Vos captures d'écran ne sont pas le produit",
				body: "Les fichiers importés sont supprimés automatiquement et nous n'entraînons jamais de modèle sur les images des utilisateurs. Chaque export porte des identifiants de contenu intégrés indiquant qu'il a été modifié.",
			},
		],
		ctaTitle: 'Des questions, des retours, ou un bug à signaler ?',
		ctaSubtitle: 'Nous lisons tout ce qui nous arrive via la page de contact.',
		ctaPrimary: 'Nous contacter',
		ctaSecondary: "Ouvrir l'éditeur",
	},
	contact: {
		metaTitle: 'Contact — ScreenshotTextEditor',
		metaDescription:
			"Contactez ScreenshotTextEditor pour du support, des questions de confidentialité, ou toute question sur le pipeline d'édition de texte dans les captures d'écran.",
		eyebrow: 'Contact',
		title: 'Nous contacter',
		subtitle: "Choisissez l'adresse qui convient — nous lisons tout et répondons en tant que vraies personnes, pas un robot de tickets.",
		supportChannel: {
			title: 'Support',
			body: "Bugs, correspondances peu fiables, ou tout ce qui ne fonctionne pas comme il faut.",
		},
		privacyChannel: {
			title: 'Confidentialité',
			body: "Questions sur ce que nous collectons, la durée de conservation, ou une demande de suppression.",
		},
		legalChannel: {
			title: 'Juridique',
			body: "Conditions d'utilisation, usage acceptable, ou questions sur les identifiants de contenu.",
		},
		footerNote:
			"Vous signalez une modification précise qui n'a pas bien fonctionné ? Joignez la capture d'écran originale et, si vous l'avez encore, le résultat exporté — c'est le moyen le plus rapide pour nous de reproduire et corriger le problème.",
	},
};
