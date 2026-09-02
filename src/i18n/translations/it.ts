import type { Translations } from '../types';

export const it: Translations = {
	nav: {
		useCases: "Casi d'uso",
		pricing: 'Prezzi',
		about: 'Chi siamo',
		contact: 'Contatti',
		openEditor: "Apri l'editor",
		menu: 'Menu',
	},
	footer: {
		tagline: "Una pipeline deterministica per modificare il testo negli screenshot — indistinguibile dall'originale, pixel per pixel.",
		productHeading: 'Prodotto',
		openEditor: "Apri l'editor",
		pricing: 'Prezzi',
		useCases: "Casi d'uso",
		useCasesHeading: "Casi d'uso",
		companyHeading: 'Azienda',
		about: 'Chi siamo',
		contact: 'Contatti',
		privacy: 'Privacy',
		terms: 'Termini',
		copyright: '© {year} ScreenshotTextEditor. Ogni esportazione include credenziali di contenuto incorporate che la contrassegnano come modificata.',
	},
	languageSwitcher: {
		ariaLabel: 'Cambia lingua',
	},
	home: {
		metaTitle: 'Editor di Testo per Screenshot — Editor di Testo per Immagini con IA Gratuito Online',
		metaDescription:
			"Modifica il testo di qualsiasi screenshot o immagine online con il nostro editor di testo IA gratuito. Font, dimensione, peso e colore corrispondono automaticamente — senza watermark, senza registrazione.",
		heroEyebrow: 'Modifica di screenshot con precisione al pixel',
		heroTitleLine1: 'Modifica il testo in uno screenshot.',
		heroTitleLine2: 'Mantieni ogni altro pixel esattamente identico.',
		heroSubtitle:
			'Fai clic su qualsiasi riga di testo in uno screenshot, riscrivila, e font, dimensione, peso e colore si adattano automaticamente — tutto il resto resta identico, pixel per pixel.',
		ctaPrimary: "Apri l'editor",
		ctaSecondary: 'Guarda come funziona',

		diffEyebrow: 'Perché è diverso',
		diffTitle: 'Una pipeline deterministica, non una supposizione generata.',
		diffP1:
			"La maggior parte degli strumenti per il testo nelle immagini si affida a modelli generativi — ottimi con foto e poster, poco affidabili su testo di interfaccia piccolo e nitido, dove ogni pixel di una lettera conta. Noi abbiamo costruito il contrario: sei fasi distinte e verificabili che rilevano, misurano e riproducono il font reale invece di dipingerci sopra qualcosa di plausibile.",
		diffP2:
			"Ogni corrispondenza porta un punteggio di affidabilità. Se non riusciamo a riprodurre il tuo testo originale con sufficiente fedeltà, te lo diciamo — invece di consegnare una modifica che appare sbagliata a colpo d'occhio.",
		matchConfidenceLabel: 'Affidabilità della corrispondenza',
		matchItem1: '"Continue" — alternativa SF Pro, 17px',
		matchItem2: '"48,20 $" — Inter, 14px',
		matchItem3: '"Settings" — condensato, nessuna corrispondenza',
		highConfidence: 'affidabilità alta',
		needsReview: 'da rivedere',

		howEyebrow: 'Come funziona',
		howTitle: 'Rileva, abbina, ricostruisci.',
		steps: [
			{
				title: '1. Rileva',
				body: "L'OCR trova ogni porzione di testo a livello di riga, con riquadri per carattere e il fattore di scala dell'immagine — 1x, 2x o 3x — misurato direttamente dai glifi.",
			},
			{
				title: '2. Abbina',
				body: 'Il tuo testo originale viene renderizzato in un elenco ristretto di font probabili per la piattaforma e valutato rispetto a una maschera alfa reale finché non si trova il font, la dimensione, il peso e la spaziatura più vicini — con il punteggio mostrato, non nascosto.',
			},
			{
				title: '3. Ricostruisci',
				body: 'Il testo vecchio viene cancellato con un riempimento corrispondente e il testo sostitutivo viene renderizzato sulla stessa linea di base e con lo stesso anti-aliasing, poi riverificato rispetto all\'originale prima di essere consegnato.',
			},
		],

		builtForEyebrow: 'Pensato per',
		builtForTitle: 'La localizzazione di App Store e Play Store.',
		builtForP:
			"Otto screenshot, venti lingue — oggi questo significa ricostruire ogni screenshot in Figma per ogni lingua. Carica una volta, forniscici un CSV di traduzioni e scarica uno ZIP con ogni lingua renderizzata nel font e nel layout originali, riadattato automaticamente quando il testo tradotto è più lungo.",
		builtForCta: 'Scopri come funziona la localizzazione →',
		csvLabel: 'screenshots_de.csv',

		privacyEyebrow: 'Privacy',
		privacyTitle: 'I tuoi screenshot non sono il prodotto.',
		privacyP:
			"Gli screenshot spesso contengono dati dell'account, nomi di clienti o numeri interni. I file caricati vengono eliminati automaticamente — un'ora per impostazione predefinita — e non addestriamo mai modelli sulle immagini degli utenti. Ogni esportazione include anche credenziali di contenuto incorporate che la contrassegnano come modificata, così uno screenshot modificato non passa mai silenziosamente per originale.",
		privacyLink1: "Leggi l'informativa sulla privacy →",
		privacyLink2: 'Leggi i termini di servizio →',

		useCasesEyebrow: "Casi d'uso",
		useCasesTitle: 'Una pipeline, ogni screenshot.',

		aboutToolEyebrow: "Informazioni sullo strumento",
		aboutToolTitle: "Cos'è un editor di testo per screenshot?",
		aboutToolP1:
			'ScreenshotTextEditor è un <strong class="text-ink">editor di testo per screenshot</strong> costruito per risolvere un problema molto specifico: cambiare le parole in uno screenshot senza cambiare nient\'altro. La maggior parte delle persone che cerca un <strong class="text-ink">editor di screenshot online</strong> incontra lo stesso ostacolo — gli editor di foto generici possono ritagliare, sfocare o annotare uno screenshot, ma nel momento in cui provi a sostituire una riga di testo, il font è sbagliato, la spaziatura si sposta o lo sfondo dietro il vecchio testo diventa una macchia. Questo strumento è stato costruito attorno a un\'idea diversa: rilevare il font, la dimensione, il peso e il colore esatti di ogni porzione di testo nell\'immagine, per poi ricostruirla con una precisione tale che la modifica sia invisibile anche al 400% di zoom.',
		aboutToolP2:
			"Come <strong class=\"text-ink\">editor di testo per screenshot online</strong>, funziona interamente nel browser — non c'è nulla da installare, nessun plugin, nessun software di design richiesto. Carica uno screenshot o qualsiasi immagine con testo, fai clic sulla riga che vuoi cambiare, digita il tuo testo sostitutivo e scarica il risultato. Essendo un <strong class=\"text-ink\">editor di screenshot gratuito</strong> per immagini singole, puoi provare l'intera pipeline — rilevamento, corrispondenza dei font e ricostruzione — senza creare un account. È un <strong class=\"text-ink\">editor di testo per screenshot online, gratuito e senza watermark</strong>, quindi ciò che esporti è esattamente ciò che vedi, senza alcun logo stampato sul tuo lavoro.",
		aboutToolH3a: 'Editor di screenshot con IA, non un filtro generico',
		aboutToolP3:
			"Chiamarlo <strong class=\"text-ink\">editor di screenshot con IA</strong> non rende giustizia a ciò che accade realmente dietro le quinte. Invece di chiedere a un modello generativo di immagini di allucinare un testo dall'aspetto plausibile — una scorciatoia che tende a fallire su font di interfaccia piccoli e nitidi — questa pipeline di <strong class=\"text-ink\">modifica del testo con IA per screenshot</strong> esegue sei fasi distinte e verificabili. Prima, l'OCR rileva ogni porzione di testo a livello di carattere e misura il fattore di scala dell'immagine direttamente dai glifi. Poi lo strumento renderizza il tuo testo di partenza in un elenco ristretto di font probabili per la piattaforma e valuta ogni candidato rispetto alla maschera di pixel reale finché non trova la corrispondenza più vicina per famiglia di font, dimensione, peso e spaziatura tra le lettere. Solo a quel punto cancella il vecchio testo con un riempimento corrispondente e renderizza la sostituzione con la stessa linea di base e lo stesso anti-aliasing. Ogni corrispondenza porta un punteggio di affidabilità visibile, quindi se la pipeline di <strong class=\"text-ink\">modifica del testo con IA gratuita per screenshot</strong> non riesce a riprodurre il tuo testo originale con sufficiente affidabilità, te lo comunica — invece di consegnare silenziosamente una modifica che sembra fuori posto.",
		aboutToolH3b: 'Più di un editor di screenshot — un editor di testo per immagini online completo',
		aboutToolP4:
			'Sebbene sia nato come editor di testo per screenshot, la stessa pipeline funziona come <strong class="text-ink">editor di testo per immagini online</strong> di uso generale. Qualsiasi PNG, JPG o mockup di interfaccia esportato con del testo può essere elaborato allo stesso modo — come <strong class="text-ink">editor di testo per immagini con IA</strong> per grafiche di marketing, esportazioni di dashboard con numeri obsoleti, o screenshot di App Store da localizzare in un\'altra lingua. Essendo un <strong class="text-ink">editor di testo per immagini online e gratuito</strong>, i team che altrimenti dovrebbero ricostruire ogni screenshot a mano in Figma per ogni lingua possono invece caricarlo una volta, fornire un CSV di traduzioni e scaricare ogni variante linguistica renderizzata nel font e nel layout originali.',
		aboutToolH3c: 'Perché i team scelgono questo editor di testo online per screenshot',
		aboutToolP5Pre:
			"Che tu debba correggere rapidamente un refuso, oscurare il nome di un cliente prima di una demo o generare un lotto di screenshot localizzati per l'App Store, questo <strong class=\"text-ink\">editor di screenshot online</strong> è pensato per far sparire la modifica invece di farla notare. È gratuito da provare, non richiede competenze di design, elimina automaticamente i tuoi file caricati e non addestra mai modelli sulle immagini che carichi — quindi l'unica cosa che cambia nel tuo screenshot è il testo che volevi cambiare. Scopri di più sul",
		aboutToolP5LinkText: 'perché lo abbiamo costruito così',

		faqEyebrow: 'FAQ',
		faqTitle: 'Domande frequenti.',
		faqs: [
			{
				question: 'Come si usa un editor di testo per immagini online?',
				answer:
					"Apri l'editor ScreenshotTextEditor e trascina il tuo screenshot o immagine — nessuna registrazione richiesta. Il nostro editor di screenshot con IA analizza l'immagine, rileva ogni porzione di testo e ti permette di fare clic su qualsiasi riga per riscriverla. Digita il tuo testo sostitutivo e lo strumento adatta automaticamente font, dimensione, peso, colore e anti-aliasing originali prima di ricostruire l'immagine attorno al nuovo testo. Esportalo come PNG o JPG in pochi secondi, tutto dal browser.",
			},
			{
				question: 'Come rimuovere il testo da un\'immagine usando un editor con IA?',
				answer:
					"Seleziona la porzione di testo che vuoi rimuovere ed elimina il suo contenuto oppure usa l'opzione di cancellazione. L'editor di testo per immagini con IA riempie l'area dietro il vecchio testo con uno sfondo corrispondente — ricostruendo colore, texture e sfumature — così non resta alcuna macchia visibile, sfocatura o watermark. Funziona per etichette di interfaccia, didascalie, timestamp o qualsiasi livello di testo rilevato nell'immagine.",
			},
			{
				question: 'Come funziona un editor di testo per immagini online?',
				answer:
					"Il nostro editor di testo per immagini online esegue una pipeline di rilevamento → corrispondenza → ricostruzione. Prima, l'OCR individua ogni porzione di testo a livello di riga e carattere e misura il fattore di scala dell'immagine. Poi renderizza il tuo testo in un elenco ristretto di font probabili e valuta ciascuno rispetto ai pixel reali finché non trova il font, la dimensione, il peso e la spaziatura più vicini. Infine cancella il testo originale con un riempimento corrispondente e renderizza la sostituzione sulla stessa linea di base, così il risultato regge anche a un esame ravvicinato.",
			},
			{
				question: 'Come modificare il testo di uno screenshot?',
				answer:
					"Carica il tuo screenshot nell'editor di testo per screenshot, fai clic sul testo che vuoi cambiare e digita il nuovo contenuto. Lo strumento mantiene ogni altro pixel — icone, pulsanti, sfondi e layout — esattamente com'era, ricostruendo solo la regione di testo. Funziona interamente online, senza software di design né corrispondenza manuale dei font.",
			},
			{
				question: 'Come modificare il testo di uno screenshot su iPhone?',
				answer:
					"Fai il tuo screenshot su iPhone come al solito, poi caricalo su ScreenshotTextEditor da Safari o Chrome sul telefono, oppure inviandolo prima a un computer via AirDrop. Poiché l'editor di screenshot funziona interamente online nel browser, non c'è nessuna app da installare — apri l'editor su qualsiasi dispositivo, seleziona il testo, sostituiscilo e scarica lo screenshot modificato direttamente sul tuo iPhone o nel rullino fotografico.",
			},
			{
				question: 'Modificare il testo in uno screenshot è gratis?',
				answer:
					"Sì. Puoi provare l'editor di testo per screenshot online gratuitamente, senza watermark e senza bisogno di un account — i file caricati vengono elaborati e poi eliminati automaticamente entro un'ora. I flussi di lavoro a volume più elevato, come la localizzazione di massa per l'App Store, sono disponibili nei piani a pagamento, ma la modifica di una singola immagine è gratuita.",
			},
			{
				question: "È possibile cambiare il testo di qualsiasi immagine o solo di uno screenshot?",
				answer:
					"Puoi modificare il testo in qualsiasi immagine, non solo negli screenshot. La stessa pipeline di rilevamento, corrispondenza dei font e ricostruzione funziona su mockup di interfaccia, grafiche di marketing, esportazioni di dashboard, PNG e foto che contengono testo — ovunque lo strumento riesca a rilevare una porzione di testo, può sostituirla preservando l'aspetto originale.",
			},
		],
		faqFooterPre: 'Hai ancora domande?',
		faqFooterLinkText: 'Contattaci',
		faqFooterPost: '— leggiamo ogni messaggio.',

		finalTitle: 'Provalo sul tuo screenshot.',
		finalSubtitle: "Nessun account necessario per provarlo. Eliminato automaticamente dopo un'ora.",
		finalCta: "Apri l'editor",
	},
	pricing: {
		metaTitle: 'Prezzi — ScreenshotTextEditor',
		metaDescription:
			"Prezzi semplici per la modifica del testo negli screenshot e la localizzazione dell'App Store — da una prova gratuita a piani per team con localizzazione in batch via CSV.",
		eyebrow: 'Prezzi',
		title: 'Prezzi semplici, nessuna sorpresa per posto.',
		subtitle:
			"Ogni piano include la stessa pipeline deterministica e lo stesso punteggio di affidabilità. I piani superiori sbloccano più volume e il flusso di localizzazione in batch. Nessun piano rimuove mai le credenziali di contenuto incorporate in un'esportazione.",
		freeTier: {
			name: 'Gratuito',
			period: '',
			description: 'Provalo su uno screenshot reale prima di impegnarti in qualcosa.',
			features: [
				'10 rendering / mese',
				'Editor per immagine singola',
				'Punteggio di affidabilità e sostituzione manuale del font',
				'Ingresso PNG e JPEG, uscita PNG',
				"File caricati eliminati dopo 1 ora",
			],
			ctaLabel: "Apri l'editor",
		},
		proTier: {
			name: 'Pro',
			period: '/ mese',
			description: 'Per i team che rilasciano screenshot localizzati con regolarità.',
			features: [
				'Modifiche illimitate di immagini singole',
				'Localizzazione in batch via CSV — carica una volta, esporta uno ZIP per lingua',
				'Punteggio di affidabilità e sostituzione manuale del font',
				'Elaborazione prioritaria',
				'Tutto ciò che è incluso in Gratuito',
			],
			ctaLabel: 'Inizia con Pro',
		},
		teamTier: {
			name: 'Team',
			period: '/ posto / mese',
			description: "Lavori in batch condivisi e supporto prioritario per tutto il team.",
			features: ['Tutto ciò che è incluso in Pro, per posto', 'Lavori di localizzazione in batch condivisi', 'Supporto prioritario', "Accesso anticipato all'API"],
			ctaLabel: 'Parla con noi',
		},
		notHereYetTitle: "Cosa manca ancora",
		notHereYetPre:
			"Testo su foto e texture complesse, scritture CJK e RTL, testo con sfumature o contorni, ombre proiettate, un plugin per Figma e un'API pubblica sono tutti nella roadmap ma non ancora rilasciati nella v1 — consulta i",
		notHereYetLinkText: 'termini',
		notHereYetPost: "per l'ambito attuale.",
	},
	about: {
		metaTitle: 'Chi siamo — ScreenshotTextEditor',
		metaDescription:
			'Perché abbiamo creato ScreenshotTextEditor: una pipeline deterministica di rilevamento-corrispondenza-ricostruzione per modificare il testo negli screenshot, invece di una supposizione generativa.',
		eyebrow: 'Chi siamo',
		title: 'Informazioni su ScreenshotTextEditor',
		intro:
			"Costruiamo strumenti per il problema specifico e fastidioso di cambiare le parole in uno screenshot senza cambiare nient'altro.",
		p1: 'ScreenshotTextEditor è nato da una frustrazione ben precisa: correggere un refuso, oscurare il nome di un cliente o localizzare uno screenshot dell\'App Store significava sempre riaprire un file di design che non esisteva più, oppure accontentarsi di una modifica "IA" generativa che sbagliava il font e sfocava lo sfondo dietro di esso. Gli editor di foto generici gestiscono bene ritagli e sfocature; falliscono nel momento in cui una singola riga di testo di interfaccia piccolo e nitido deve cambiare mentre tutto il resto deve restare identico, pixel per pixel.',
		p2: "Così abbiamo costruito l'opposto di una scorciatoia generativa: una pipeline deterministica che rileva ogni porzione di testo in un'immagine, ne misura il font, la dimensione, il peso e il colore reali, e ricostruisce solo quella regione — verificata rispetto all'originale prima di essere consegnata.",
		buildingTowardTitle: 'Verso cosa stiamo lavorando',
		buildingTowardPre:
			"Oggi si tratta di un editor gratuito per immagini singole senza registrazione e di un flusso di localizzazione in batch per gli screenshot di App Store e Play Store. Entrambi funzionano sulla stessa pipeline rileva → abbina → ricostruisci descritta nella",
		buildingTowardLinkText: 'homepage',
		buildingTowardPost: '.',
		valuesEyebrow: 'Cosa ci sta a cuore',
		valuesTitle: 'I principi dietro la pipeline.',
		values: [
			{
				title: 'Deterministico, non generativo',
				body: "Abbiamo costruito sei fasi distinte e verificabili invece di chiedere a un modello generativo di allucinare un testo plausibile. I font di interfaccia piccoli e nitidi non sopravvivono a una supposizione.",
			},
			{
				title: 'Mostriamo l\'affidabilità, non solo il risultato',
				body: "Ogni corrispondenza di font porta un punteggio di affidabilità visibile. Se non riusciamo a riprodurre il tuo testo con sufficiente affidabilità, lo diciamo invece di consegnare una modifica scadente.",
			},
			{
				title: 'I tuoi screenshot non sono il prodotto',
				body: 'I file caricati vengono eliminati automaticamente e non addestriamo mai modelli sulle immagini degli utenti. Ogni esportazione include credenziali di contenuto incorporate che la contrassegnano come modificata.',
			},
		],
		ctaTitle: 'Domande, feedback o un bug da segnalare?',
		ctaSubtitle: 'Leggiamo tutto ciò che arriva tramite la pagina dei contatti.',
		ctaPrimary: 'Contattaci',
		ctaSecondary: "Apri l'editor",
	},
	contact: {
		metaTitle: 'Contatti — ScreenshotTextEditor',
		metaDescription: 'Contatta ScreenshotTextEditor per assistenza, domande sulla privacy o qualsiasi cosa riguardi la pipeline di modifica del testo negli screenshot.',
		eyebrow: 'Contatti',
		title: 'Mettiti in contatto',
		subtitle: "Scegli l'indirizzo più adatto — leggiamo tutto e rispondiamo come persone vere, non un bot di ticket.",
		supportChannel: {
			title: 'Assistenza',
			body: 'Bug, corrispondenze poco affidabili o qualsiasi cosa non funzioni come dovrebbe.',
		},
		privacyChannel: {
			title: 'Privacy',
			body: 'Domande su cosa raccogliamo, per quanto tempo lo conserviamo o una richiesta di cancellazione.',
		},
		legalChannel: {
			title: 'Legale',
			body: 'Termini di servizio, uso accettabile o domande sulle credenziali di contenuto.',
		},
		footerNote:
			"Stai segnalando una modifica specifica che non è venuta bene? Includi lo screenshot originale e, se lo hai ancora, il risultato esportato — è il modo più veloce per riprodurre e risolvere il problema.",
	},
};
