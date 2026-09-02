import type { Translations } from '../types';

export const de: Translations = {
	nav: {
		useCases: 'Anwendungsfälle',
		pricing: 'Preise',
		about: 'Über uns',
		contact: 'Kontakt',
		openEditor: 'Editor öffnen',
		menu: 'Menü',
	},
	footer: {
		tagline: 'Eine deterministische Pipeline zum Bearbeiten von Text in Screenshots — pixelgenau ununterscheidbar vom Original.',
		productHeading: 'Produkt',
		openEditor: 'Editor öffnen',
		pricing: 'Preise',
		useCases: 'Anwendungsfälle',
		useCasesHeading: 'Anwendungsfälle',
		companyHeading: 'Unternehmen',
		about: 'Über uns',
		contact: 'Kontakt',
		privacy: 'Datenschutz',
		terms: 'AGB',
		copyright: '© {year} ScreenshotTextEditor. Jeder Export enthält eingebettete Content-Credentials, die ihn als bearbeitet kennzeichnen.',
	},
	languageSwitcher: {
		ariaLabel: 'Sprache ändern',
	},
	home: {
		metaTitle: 'Screenshot-Text-Editor — Kostenloser Online-KI-Bildtext-Editor',
		metaDescription:
			'Bearbeite Text in jedem Screenshot oder Bild online mit unserem kostenlosen KI-Screenshot-Text-Editor. Schrift, Größe, Gewicht und Farbe werden automatisch angepasst — kein Wasserzeichen, keine Anmeldung nötig.',
		heroEyebrow: 'Pixelgenaue Screenshot-Bearbeitung',
		heroTitleLine1: 'Text in einem Screenshot bearbeiten.',
		heroTitleLine2: 'Jeden anderen Pixel exakt gleich lassen.',
		heroSubtitle:
			'Klicke auf eine beliebige Textzeile in einem Screenshot, tippe sie neu ein — Schrift, Größe, Gewicht und Farbe werden automatisch angepasst, alles andere bleibt pixelgenau gleich.',
		ctaPrimary: 'Editor öffnen',
		ctaSecondary: 'So funktioniert es',

		diffEyebrow: 'Warum es anders ist',
		diffTitle: 'Eine deterministische Pipeline, keine generierte Vermutung.',
		diffP1:
			'Die meisten Tools für Text in Bildern setzen auf generative Bildmodelle — großartig bei Fotos und Postern, unzuverlässig bei kleinem, scharfem UI-Text, bei dem jeder Pixel eines Buchstabens zählt. Wir haben das Gegenteil gebaut: sechs eigenständige, testbare Stufen, die die tatsächliche Schriftart erkennen, messen und reproduzieren, statt etwas Plausibles darüber zu malen.',
		diffP2:
			'Jede Übereinstimmung erhält einen Konfidenzwert. Können wir deinen Originaltext nicht zuverlässig genug reproduzieren, sagen wir es dir — statt eine Bearbeitung auszuliefern, die auf den ersten Blick falsch wirkt.',
		matchConfidenceLabel: 'Konfidenz der Übereinstimmung',
		matchItem1: '„Continue“ — SF-Pro-Ersatz, 17px',
		matchItem2: '„48,20 $“ — Inter, 14px',
		matchItem3: '„Settings“ — schmal, keine Übereinstimmung',
		highConfidence: 'hohe Konfidenz',
		needsReview: 'Prüfung nötig',

		howEyebrow: 'So funktioniert es',
		howTitle: 'Erkennen, abgleichen, neu aufbauen.',
		steps: [
			{
				title: '1. Erkennen',
				body: 'OCR findet jeden Textabschnitt auf Zeilenebene, mit Boxen pro Zeichen und dem Skalierungsfaktor des Bildes — 1x, 2x oder 3x — gemessen direkt an den Glyphen.',
			},
			{
				title: '2. Abgleichen',
				body: 'Dein Originaltext wird in einer kurzen Liste plattformtypischer Schriftarten gerendert und gegen eine echte Alphamaske bewertet, bis die nächstliegende Schriftart, Größe, Gewichtung und Laufweite gefunden ist — der Score wird angezeigt, nicht versteckt.',
			},
			{
				title: '3. Neu aufbauen',
				body: 'Der alte Text wird mit einer passenden Füllung entfernt, dein Ersatztext wird auf derselben Grundlinie und mit demselben Antialiasing gerendert und vor der Auslieferung erneut mit dem Original abgeglichen.',
			},
		],

		builtForEyebrow: 'Entwickelt für',
		builtForTitle: 'App-Store- und Play-Store-Lokalisierung.',
		builtForP:
			'Acht Screenshots, zwanzig Sprachen — heute bedeutet das, jeden Screenshot für jede Sprache in Figma neu zu bauen. Einmal hochladen, uns eine CSV mit Übersetzungen geben, und ein ZIP herunterladen, in dem jede Sprache in der Originalschrift und im Originallayout gerendert ist — bei längerem übersetztem Text automatisch neu umgebrochen.',
		builtForCta: 'So funktioniert die Lokalisierung →',
		csvLabel: 'screenshots_de.csv',

		privacyEyebrow: 'Datenschutz',
		privacyTitle: 'Deine Screenshots sind nicht das Produkt.',
		privacyP:
			'Screenshots enthalten oft Kontodaten, Kundennamen oder interne Zahlen. Hochgeladene Dateien werden automatisch gelöscht — standardmäßig nach einer Stunde — und wir trainieren nie mit Nutzerbildern. Jeder Export enthält zudem eingebettete Content-Credentials, die ihn als bearbeitet kennzeichnen, damit ein bearbeiteter Screenshot nie unbemerkt als Original durchgeht. Diese Credentials sind unsichtbare Metadaten, kein sichtbares Wasserzeichen — auf dem Bild selbst wird nichts aufgedruckt.',
		privacyLink1: 'Datenschutzerklärung lesen →',
		privacyLink2: 'Nutzungsbedingungen lesen →',

		useCasesEyebrow: 'Anwendungsfälle',
		useCasesTitle: 'Eine Pipeline, jeder Screenshot.',

		aboutToolEyebrow: 'Über das Tool',
		aboutToolTitle: 'Was ist ein Screenshot-Text-Editor?',
		aboutToolP1:
			'ScreenshotTextEditor löst ein sehr konkretes Problem: die Worte in einem Screenshot ändern, ohne sonst etwas daran zu verändern. Generische Bildbearbeiter können gut zuschneiden, unscharf machen und Anmerkungen hinzufügen, aber sobald man eine Textzeile austauschen will, stimmt die Schrift nicht, der Abstand verschiebt sich, oder der Bereich hinter dem alten Text wird zum Schmierfleck. Dieses Tool verfolgt einen engeren Ansatz: Es erkennt die exakte Schriftart, Größe, Gewichtung und Farbe jedes Textabschnitts im Bild und baut diesen Bereich dann so präzise neu auf, dass die Bearbeitung selbst bei 400 % Zoom unsichtbar ist.',
		aboutToolP2:
			'Es läuft vollständig im Browser — nichts zu installieren, keine Design-Software nötig. Lade einen Screenshot oder ein beliebiges Bild mit Text hoch, klicke auf die Zeile, die du ändern möchtest, tippe deinen Ersatztext ein und lade das Ergebnis herunter. Bearbeitungen einzelner Bilder kannst du kostenlos ausprobieren, ganz ohne Konto. Exporte tragen kein sichtbares Wasserzeichen und kein Branding — das Einzige, was hinzugefügt wird, ist ein unsichtbares Content-Credentials-Tag in den Metadaten der Datei, weiter unten beschrieben, das das Bild als bearbeitet kennzeichnet.',
		aboutToolH3a: 'Warum kein generativer KI-Editor?',
		aboutToolP3:
			'Die meisten Tools, die sich als KI-Bildeditor bezeichnen, verlassen sich auf ein generatives Modell, das plausibel aussehenden Text halluziniert — eine Abkürzung, die bei kleinen, scharfen UI-Schriften meist scheitert. Diese Pipeline funktioniert anders: OCR erkennt jeden Textabschnitt auf Zeichenebene und misst den Skalierungsfaktor des Bildes direkt an den Glyphen. Das Tool rendert deinen Ausgangstext dann in einer kurzen Liste plattformtypischer Schriftarten und bewertet jeden Kandidaten gegen die echte Pixelmaske, bis es die nächstliegende Übereinstimmung für Schriftfamilie, Größe, Gewichtung und Laufweite findet. Erst dann entfernt es den alten Text mit einer passenden Füllung und rendert den Ersatztext mit derselben Grundlinie und demselben Antialiasing. Jede Übereinstimmung trägt einen sichtbaren Konfidenzwert — kann die Pipeline deinen Text nicht zuverlässig genug reproduzieren, sagt sie es dir, statt stillschweigend eine Bearbeitung auszuliefern, die unpassend wirkt.',
		aboutToolH3b: 'Funktioniert mit mehr als nur Screenshots',
		aboutToolP4:
			'Dieselbe Pipeline funktioniert mit jedem PNG oder JPG, das Text enthält, nicht nur mit Screenshots — Marketinggrafiken, Dashboard-Exporte mit veralteten Zahlen oder App-Store- und Play-Store-Screenshots, die lokalisiert werden müssen. Teams, die sonst jeden Screenshot für jede Sprache manuell in Figma neu bauen müssten, können stattdessen einmal hochladen, eine CSV mit Übersetzungen übergeben und jede Sprachvariante in der Originalschrift und im Originallayout herunterladen. Aktuell funktioniert es am besten bei flachen Hintergründen oder einfachen Farbverläufen mit lateinischer Schrift; unruhige Fotohintergründe sowie CJK- oder RTL-Schriften werden noch nicht unterstützt.',
		aboutToolH3c: 'Für wen es gedacht ist',
		aboutToolP5Pre:
			'Ob schneller Tippfehler-Fix, das Schwärzen eines Kundennamens vor einer Demo oder ein Stapel lokalisierter App-Store-Screenshots — das Ziel ist, dass die Bearbeitung unsichtbar bleibt, statt aufzufallen. Es ist kostenlos testbar, erfordert keine Design-Erfahrung, löscht deine Uploads automatisch und trainiert nie mit den hochgeladenen Bildern. Mehr dazu, warum wir es',
		aboutToolP5LinkText: 'genau so gebaut haben',

		faqEyebrow: 'FAQ',
		faqTitle: 'Häufig gestellte Fragen.',
		faqs: [
			{
				question: 'Wie benutzt man einen Bildtext-Editor online?',
				answer:
					'Öffne den ScreenshotTextEditor und ziehe deinen Screenshot oder dein Bild hinein — keine Anmeldung nötig. Unser KI-Screenshot-Editor scannt das Bild, erkennt jeden Textabschnitt und lässt dich jede Zeile per Klick umschreiben. Tippe deinen Ersatztext ein, und das Tool passt automatisch die ursprüngliche Schriftart, Größe, Gewichtung, Farbe und das Antialiasing an, bevor es das Bild um deinen neuen Text herum neu aufbaut. Exportiere es in Sekunden als PNG oder JPG, alles direkt im Browser.',
			},
			{
				question: 'Wie entfernt man Text aus einem Bild mit einem KI-Editor?',
				answer:
					'Wähle den zu entfernenden Textabschnitt aus und lösche seinen Inhalt oder nutze die Löschfunktion. Das Tool füllt den Bereich hinter dem alten Text passend zum umgebenden Hintergrund auf — einfarbige Flächen und einfache Farbverläufe —, sodass kein sichtbarer Fleck und keine Unschärfe zurückbleiben. Das funktioniert gut für UI-Labels, Untertitel und Zeitstempel auf flachen oder einfach verlaufenden Hintergründen; unruhige Fotohintergründe und komplexe Texturen werden noch nicht unterstützt.',
			},
			{
				question: 'Wie funktioniert ein Bildtext-Editor online?',
				answer:
					'Unser Online-Bildtext-Editor läuft nach dem Prinzip Erkennung → Abgleich → Neuaufbau. Zuerst lokalisiert OCR jeden Textabschnitt auf Zeilen- und Zeichenebene und misst den Skalierungsfaktor des Bildes. Danach rendert es deinen Text in einer kurzen Liste wahrscheinlicher Schriftarten und bewertet jede gegen die echten Pixel, bis die nächstliegende Schriftart, Größe, Gewichtung und Laufweite gefunden ist. Zum Schluss entfernt es den Originaltext mit einer passenden Füllung und rendert deinen Ersatztext auf derselben Grundlinie, sodass das Ergebnis auch genauem Hinsehen standhält.',
			},
			{
				question: 'Wie bearbeitet man Text auf einem Screenshot?',
				answer:
					'Lade deinen Screenshot in den Screenshot-Text-Editor hoch, klicke auf den zu ändernden Text und tippe den neuen Inhalt. Das Tool behält jeden anderen Pixel — Symbole, Schaltflächen, Hintergründe und Layout — exakt bei und baut nur den Textbereich neu auf. Alles läuft vollständig online, ohne Design-Software oder manuellen Schriftabgleich.',
			},
			{
				question: 'Wie bearbeitet man Text auf einem iPhone-Screenshot?',
				answer:
					'Mach deinen Screenshot auf dem iPhone wie gewohnt und lade ihn dann über Safari oder Chrome auf dem Handy bei ScreenshotTextEditor hoch — oder schicke ihn zuerst per AirDrop an einen Computer. Da der Screenshot-Text-Editor vollständig online im Browser läuft, gibt es keine App zu installieren — öffne den Editor auf jedem Gerät, wähle den Text aus, ersetze ihn und lade den bearbeiteten Screenshot direkt auf dein iPhone oder in die Fotomediathek herunter.',
			},
			{
				question: 'Ist das Bearbeiten von Text in Screenshots kostenlos?',
				answer:
					'Ja. Du kannst den Screenshot-Text-Editor online kostenlos testen, ohne Wasserzeichen und ohne Konto — Uploads werden verarbeitet und danach automatisch innerhalb einer Stunde gelöscht. Workflows mit höherem Volumen wie Massen-Lokalisierung für den App Store sind in kostenpflichtigen Plänen verfügbar, aber die Bearbeitung eines einzelnen Bildes ist kostenlos.',
			},
			{
				question: 'Kann man den Text in jedem Bild ändern oder nur in Screenshots?',
				answer:
					'Du kannst Text in jedem Bild bearbeiten, nicht nur in Screenshots — dieselbe Erkennungs-, Schriftabgleich- und Neuaufbau-Pipeline funktioniert bei UI-Mockups, Marketinggrafiken und Dashboard-Exporten. Aktuell funktioniert es am besten bei flachen Hintergründen oder einfachen Farbverläufen mit lateinischer Schrift; unruhige Fotohintergründe sowie CJK- oder RTL-Schriften stehen auf der Roadmap, werden aber noch nicht unterstützt.',
			},
		],
		faqFooterPre: 'Noch Fragen?',
		faqFooterLinkText: 'Kontaktiere uns',
		faqFooterPost: '— wir lesen jede Nachricht.',

		finalTitle: 'Probier es an deinem eigenen Screenshot aus.',
		finalSubtitle: 'Kein Konto nötig, um es auszuprobieren. Wird nach einer Stunde automatisch gelöscht.',
		finalCta: 'Editor öffnen',
	},
	pricing: {
		metaTitle: 'Preise — ScreenshotTextEditor',
		metaDescription:
			'Einfache Preise für Screenshot-Textbearbeitung und App-Store-Lokalisierung — von einer kostenlosen Testversion bis zu Team-Plänen mit CSV-Stapel-Lokalisierung.',
		eyebrow: 'Preise',
		title: 'Einfache Preise, keine überraschenden Sitzplätze.',
		subtitle:
			'Jede Stufe erhält dieselbe deterministische Pipeline und Konfidenzbewertung. Höhere Stufen schalten mehr Volumen und den Stapel-Lokalisierungs-Workflow frei. Keine Stufe entfernt jemals die eingebetteten Content-Credentials eines Exports.',
		freeTier: {
			name: 'Kostenlos',
			period: '',
			description: 'Probiere es an einem echten Screenshot aus, bevor du dich festlegst.',
			features: [
				'10 Renderings / Monat',
				'Einzelbild-Editor',
				'Konfidenzbewertung & manuelle Schriftüberschreibung',
				'PNG und JPEG rein, PNG raus',
				'Uploads werden nach 1 Stunde gelöscht',
			],
			ctaLabel: 'Editor öffnen',
		},
		proTier: {
			name: 'Pro',
			period: '/ Monat',
			description: 'Für Teams, die lokalisierte Screenshots planmäßig ausliefern.',
			features: [
				'Unbegrenzte Einzelbild-Bearbeitungen',
				'CSV-Stapel-Lokalisierung — einmal hochladen, ein ZIP pro Sprache exportieren',
				'Konfidenzbewertung & manuelle Schriftüberschreibung',
				'Priorisierte Verarbeitung',
				'Alles aus Kostenlos',
			],
			ctaLabel: 'Mit Pro starten',
		},
		teamTier: {
			name: 'Team',
			period: '/ Sitz / Monat',
			description: 'Geteilte Stapeljobs und priorisierter Support für das ganze Team.',
			features: ['Alles aus Pro, pro Sitz', 'Geteilte Stapel-Lokalisierungsjobs', 'Priorisierter Support', 'Früher API-Zugang'],
			ctaLabel: 'Sprich mit uns',
		},
		notHereYetTitle: 'Was noch nicht dabei ist',
		notHereYetPre:
			'Text über Fotos und komplexen Texturen, CJK- und RTL-Schriften, Verlaufs- oder Kontur-Text, Schlagschatten, ein Figma-Plugin und eine öffentliche API stehen auf der Roadmap, sind aber in v1 noch nicht enthalten — die aktuelle Reichweite steht in den',
		notHereYetLinkText: 'AGB',
		notHereYetPost: '.',
	},
	about: {
		metaTitle: 'Über uns — ScreenshotTextEditor',
		metaDescription:
			'Warum wir ScreenshotTextEditor gebaut haben: eine deterministische Erkennen-Abgleichen-Neuaufbauen-Pipeline zum Bearbeiten von Text in Screenshots, statt einer generativen Vermutung.',
		eyebrow: 'Über uns',
		title: 'Über ScreenshotTextEditor',
		intro:
			'Wir bauen Tools für das spezielle, lästige Problem, die Worte in einem Screenshot zu ändern, ohne sonst etwas daran zu verändern.',
		p1: 'ScreenshotTextEditor entstand aus einer ganz konkreten Frustration: einen Tippfehler zu korrigieren, einen Kundennamen zu schwärzen oder einen App-Store-Screenshot zu lokalisieren bedeutete immer, eine Design-Datei neu zu öffnen, die es nicht mehr gab — oder sich mit einer generativen „KI“-Bearbeitung zufriedenzugeben, die die falsche Schrift traf und den Hintergrund dahinter verwischte. Generische Bildbearbeiter beherrschen Zuschnitte und Unschärfen gut; sie scheitern in dem Moment, in dem eine einzelne Zeile kleinen, scharfen UI-Texts sich ändern muss und alles drumherum pixelgenau gleich bleiben soll.',
		p2: 'Also bauten wir das Gegenteil einer generativen Abkürzung: eine deterministische Pipeline, die jeden Textabschnitt in einem Bild erkennt, dessen tatsächliche Schriftart, Größe, Gewichtung und Farbe misst und nur diesen Bereich neu aufbaut — vor der Auslieferung mit dem Original abgeglichen.',
		buildingTowardTitle: 'Woran wir arbeiten',
		buildingTowardPre:
			'Heute ist das ein kostenloser Einzelbild-Editor ohne Anmeldung und ein Stapel-Lokalisierungs-Workflow für App-Store- und Play-Store-Screenshots. Beide laufen über dieselbe Erkennen → Abgleichen → Neuaufbauen-Pipeline, die auf der',
		buildingTowardLinkText: 'Startseite',
		buildingTowardPost: 'beschrieben ist.',
		valuesEyebrow: 'Was uns wichtig ist',
		valuesTitle: 'Prinzipien hinter der Pipeline.',
		values: [
			{
				title: 'Deterministisch statt generativ',
				body: 'Wir haben sechs eigenständige, testbare Stufen gebaut, statt ein generatives Modell plausiblen Text halluzinieren zu lassen. Kleine, scharfe UI-Schriften überleben keine Vermutung.',
			},
			{
				title: 'Konfidenz zeigen, nicht nur das Ergebnis',
				body: 'Jede Schriftübereinstimmung trägt einen sichtbaren Konfidenzwert. Können wir deinen Text nicht zuverlässig genug reproduzieren, sagen wir es, statt eine schlechte Bearbeitung auszuliefern.',
			},
			{
				title: 'Deine Screenshots sind nicht das Produkt',
				body: 'Uploads werden automatisch gelöscht, und wir trainieren nie mit Nutzerbildern. Jeder Export enthält eingebettete Content-Credentials, die ihn als bearbeitet kennzeichnen. Das sind unsichtbare Metadaten, kein Stempel auf dem Bild — Exporte tragen kein sichtbares Wasserzeichen.',
			},
		],
		ctaTitle: 'Fragen, Feedback oder ein Bug zu melden?',
		ctaSubtitle: 'Wir lesen alles, was über die Kontaktseite eingeht.',
		ctaPrimary: 'Kontaktiere uns',
		ctaSecondary: 'Editor öffnen',
	},
	contact: {
		metaTitle: 'Kontakt — ScreenshotTextEditor',
		metaDescription: 'Kontaktiere ScreenshotTextEditor für Support, Datenschutzfragen oder alles rund um die Screenshot-Textbearbeitungs-Pipeline.',
		eyebrow: 'Kontakt',
		title: 'Kontakt aufnehmen',
		subtitle: 'Wähle die passende Adresse — wir lesen alles und antworten als echte Menschen, nicht als Ticket-Bot.',
		supportChannel: {
			title: 'Support',
			body: 'Bugs, Übereinstimmungen mit geringer Konfidenz oder alles, was nicht so funktioniert, wie es sollte.',
		},
		privacyChannel: {
			title: 'Datenschutz',
			body: 'Fragen dazu, was wir erfassen, wie lange wir es aufbewahren, oder eine Löschanfrage.',
		},
		legalChannel: {
			title: 'Rechtliches',
			body: 'Nutzungsbedingungen, zulässige Nutzung oder Fragen zu Content-Credentials.',
		},
		footerNote:
			'Meldest du eine bestimmte Bearbeitung, die nicht gut ausgesehen hat? Füge den Original-Screenshot bei und, falls noch vorhanden, das exportierte Ergebnis — so können wir das Problem am schnellsten nachvollziehen und beheben.',
	},
};
