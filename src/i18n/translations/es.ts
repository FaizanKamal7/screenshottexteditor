import type { Translations } from '../types';

export const es: Translations = {
	nav: {
		useCases: 'Casos de uso',
		pricing: 'Precios',
		about: 'Nosotros',
		contact: 'Contacto',
		openEditor: 'Abrir el editor',
		menu: 'Menú',
	},
	footer: {
		tagline: 'Un flujo determinista para editar texto en capturas de pantalla — indistinguible del original, píxel a píxel.',
		productHeading: 'Producto',
		openEditor: 'Abrir el editor',
		pricing: 'Precios',
		useCases: 'Casos de uso',
		useCasesHeading: 'Casos de uso',
		companyHeading: 'Empresa',
		about: 'Nosotros',
		contact: 'Contacto',
		privacy: 'Privacidad',
		terms: 'Términos',
		copyright: '© {year} ScreenshotTextEditor. Todas las exportaciones incluyen credenciales de contenido que las marcan como editadas.',
	},
	languageSwitcher: {
		ariaLabel: 'Cambiar idioma',
	},
	home: {
		metaTitle: 'Editor de texto para capturas de pantalla — Editor de texto en imágenes con IA, gratis y online',
		metaDescription:
			'Edita el texto de cualquier captura de pantalla o imagen online con nuestro editor de texto con IA gratuito. Coincide fuente, tamaño, grosor y color — sin marca de agua, sin registro.',
		heroEyebrow: 'Edición de capturas con precisión de píxel',
		heroTitleLine1: 'Edita el texto de una captura de pantalla.',
		heroTitleLine2: 'Conserva cada otro píxel exactamente igual.',
		heroSubtitle:
			'Haz clic en cualquier línea de texto de una captura, vuelve a escribirla y su fuente, tamaño, grosor y color se ajustan automáticamente — el resto permanece idéntico píxel a píxel.',
		ctaPrimary: 'Abrir el editor',
		ctaSecondary: 'Ver cómo funciona',

		diffEyebrow: 'Por qué es diferente',
		diffTitle: 'Un flujo determinista, no una suposición generada.',
		diffP1:
			'La mayoría de las herramientas de texto en imágenes se apoyan en modelos generativos — excelentes con fotos y pósteres, poco fiables en texto de interfaz pequeño y nítido, donde cada píxel de una letra importa. Construimos lo contrario: seis etapas independientes y verificables que detectan, miden y reproducen la fuente real en lugar de pintar algo plausible encima.',
		diffP2:
			'Cada coincidencia lleva una puntuación de confianza. Si no podemos reproducir tu texto original con la fidelidad suficiente, te lo decimos — en vez de entregar una edición que se nota a simple vista.',
		matchConfidenceLabel: 'Confianza de la coincidencia',
		matchItem1: '«Continue» — alternativa SF Pro, 17px',
		matchItem2: '«$48.20» — Inter, 14px',
		matchItem3: '«Settings» — condensada, sin coincidencia',
		highConfidence: 'confianza alta',
		needsReview: 'requiere revisión',

		howEyebrow: 'Cómo funciona',
		howTitle: 'Detectar, igualar, reconstruir.',
		steps: [
			{
				title: '1. Detectar',
				body: 'El OCR encuentra cada fragmento de texto a nivel de línea, con cajas por carácter y el factor de escala de la imagen — 1x, 2x o 3x — medido a partir de los propios glifos.',
			},
			{
				title: '2. Igualar',
				body: 'Tu texto original se renderiza con una lista breve de fuentes probables según la plataforma y se puntúa contra una máscara alfa real hasta encontrar la fuente, tamaño, grosor y espaciado más cercanos — mostrando la puntuación, sin ocultarla.',
			},
			{
				title: '3. Reconstruir',
				body: 'El texto antiguo se borra con un relleno equivalente y tu texto de reemplazo se renderiza en la misma línea base y suavizado, y se vuelve a verificar contra el original antes de entregarse.',
			},
		],

		builtForEyebrow: 'Pensado para',
		builtForTitle: 'Localización de App Store y Play Store.',
		builtForP:
			'Ocho capturas, veinte idiomas — hoy eso significa reconstruir cada captura en Figma para cada idioma. Súbelas una vez, entréganos un CSV con las traducciones y descarga un ZIP con cada idioma renderizado con la fuente y el diseño originales, reajustado automáticamente cuando el texto traducido es más largo.',
		builtForCta: 'Ver cómo funciona la localización →',
		csvLabel: 'screenshots_de.csv',

		privacyEyebrow: 'Privacidad',
		privacyTitle: 'Tus capturas de pantalla no son el producto.',
		privacyP:
			'Las capturas de pantalla suelen contener datos de cuenta, nombres de clientes o cifras internas. Los archivos subidos se eliminan automáticamente — una hora por defecto — y nunca entrenamos con las imágenes de los usuarios. Cada exportación también incluye credenciales de contenido incrustadas que la marcan como editada, para que una captura editada nunca pase silenciosamente por original. Esas credenciales son metadatos invisibles, no una marca de agua visual — no se estampa nada en la imagen en sí.',
		privacyLink1: 'Leer la política de privacidad →',
		privacyLink2: 'Leer los términos del servicio →',

		useCasesEyebrow: 'Casos de uso',
		useCasesTitle: 'Un mismo flujo, cualquier captura de pantalla.',

		aboutToolEyebrow: 'Sobre la herramienta',
		aboutToolTitle: '¿Qué es un editor de texto para capturas de pantalla?',
		aboutToolP1:
			'ScreenshotTextEditor resuelve un problema muy concreto: cambiar las palabras de una captura de pantalla sin cambiar nada más de ella. Los editores de fotos genéricos manejan bien los recortes, el desenfoque y las anotaciones, pero en cuanto intentas sustituir una línea de texto, la fuente queda mal, el espaciado se desajusta o la zona detrás del texto antiguo se convierte en una mancha. Esta herramienta sigue un enfoque más específico: detecta la fuente, el tamaño, el grosor y el color exactos de cada fragmento de texto de la imagen, y luego reconstruye esa zona con tanta precisión que la edición resulta invisible incluso al 400% de zoom.',
		aboutToolP2:
			'Funciona enteramente en el navegador, así que no hay nada que instalar ni software de diseño necesario. Sube una captura o cualquier imagen con texto, haz clic en la línea que quieres cambiar, escribe tu texto de reemplazo y descarga el resultado. Las ediciones de una sola imagen son gratis de probar, sin necesidad de crear una cuenta. Las exportaciones no llevan marca de agua ni branding visibles — lo único que se añade es una etiqueta de credenciales de contenido invisible en los metadatos del archivo, descrita más abajo, que identifica la imagen como editada.',
		aboutToolH3a: '¿Por qué no un editor de IA generativa?',
		aboutToolP3:
			'La mayoría de las herramientas que se llaman a sí mismas editor de imágenes con IA se apoyan en un modelo generativo para inventar un texto de aspecto plausible — un atajo que suele fallar en fuentes de interfaz pequeñas y nítidas. Este proceso funciona de forma distinta: el OCR detecta cada fragmento de texto a nivel de carácter y mide el factor de escala de la imagen directamente a partir de los glifos. Después, la herramienta renderiza tu texto original con una lista breve de fuentes probables según la plataforma y puntúa cada candidata contra la máscara real de píxeles hasta encontrar la coincidencia más cercana en familia, tamaño, grosor y espaciado entre letras. Solo entonces borra el texto antiguo con un relleno equivalente y renderiza el reemplazo con la misma línea base y el mismo suavizado. Cada coincidencia lleva una puntuación de confianza visible, así que si el proceso no puede reproducir tu texto con la fiabilidad suficiente, te lo dice en lugar de entregar en silencio una edición que se nota.',
		aboutToolH3b: 'Funciona con algo más que capturas de pantalla',
		aboutToolP4:
			'El mismo proceso funciona con cualquier PNG o JPG que contenga texto, no solo capturas de pantalla — gráficos de marketing, exportaciones de paneles con cifras desactualizadas o capturas de App Store y Play Store que necesitan localizarse. Los equipos que de otro modo reconstruirían cada captura a mano en Figma para cada idioma pueden en su lugar subirla una vez, entregar un CSV de traducciones y descargar cada variante de idioma renderizada con la fuente y el diseño originales. Por ahora funciona mejor con fondos planos o de degradado simple y texto en escritura latina; los fondos de foto recargados y las escrituras CJK o RTL todavía no son compatibles.',
		aboutToolH3c: 'Para quién es',
		aboutToolP5Pre:
			'Ya sea para corregir una errata rápida, ocultar el nombre de un cliente antes de una demo o generar un lote de capturas de App Store localizadas, el objetivo es que la edición pase desapercibida en vez de notarse. Es gratis de probar, no requiere conocimientos de diseño, elimina tus archivos subidos automáticamente y nunca entrena con las imágenes que subes. Lee más sobre',
		aboutToolP5LinkText: 'por qué lo construimos así',

		faqEyebrow: 'Preguntas frecuentes',
		faqTitle: 'Preguntas frecuentes.',
		faqs: [
			{
				question: '¿Cómo usar un editor de texto para imágenes online?',
				answer:
					'Abre el editor de ScreenshotTextEditor y suelta tu captura o imagen — sin necesidad de registro. Nuestro editor con IA analiza la imagen, detecta cada fragmento de texto y te permite hacer clic en cualquier línea para reescribirla. Escribe tu texto de reemplazo y la herramienta ajusta automáticamente la fuente, el tamaño, el grosor, el color y el suavizado originales antes de reconstruir la imagen alrededor de tu nuevo texto. Expórtala como PNG o JPG en segundos, todo desde tu navegador.',
			},
			{
				question: '¿Cómo eliminar texto de una imagen con un editor de IA?',
				answer:
					'Selecciona el fragmento de texto que quieres eliminar y borra su contenido o usa la opción de borrado. La herramienta rellena la zona detrás del texto antiguo para que coincida con el fondo circundante — colores sólidos y degradados simples — de modo que no queda ningún parche visible ni desenfoque. Esto funciona bien con etiquetas de interfaz, subtítulos y marcas de tiempo sobre fondos planos o con degradados simples; los fondos de foto recargados y las texturas complejas todavía no son compatibles.',
			},
			{
				question: '¿Cómo funciona un editor de texto para imágenes online?',
				answer:
					'Nuestro editor de texto para imágenes online ejecuta un proceso de detección → coincidencia → reconstrucción. Primero, el OCR localiza cada fragmento de texto a nivel de línea y carácter y mide el factor de escala de la imagen. Después renderiza tu texto con una lista breve de fuentes probables y puntúa cada una contra los píxeles reales hasta encontrar la fuente, tamaño, grosor y espaciado más cercanos. Por último, borra el texto original con un relleno equivalente y renderiza tu reemplazo en la misma línea base, de modo que el resultado resiste una inspección de cerca.',
			},
			{
				question: '¿Cómo editar el texto de una captura de pantalla?',
				answer:
					'Sube tu captura al editor de texto para capturas, haz clic en el texto que quieres cambiar y escribe el nuevo contenido. La herramienta conserva cada otro píxel — iconos, botones, fondos y diseño — exactamente igual, y solo reconstruye la región de texto. Funciona completamente online, sin software de diseño ni ajuste manual de fuentes.',
			},
			{
				question: '¿Cómo editar el texto de una captura de pantalla del iPhone?',
				answer:
					'Toma tu captura en el iPhone como de costumbre y súbela a ScreenshotTextEditor desde Safari o Chrome en tu teléfono, o envíala primero a un ordenador por AirDrop. Como el editor de capturas funciona enteramente online en el navegador, no hay ninguna app que instalar — abre el editor en cualquier dispositivo, selecciona el texto, reemplázalo y descarga la captura editada directamente a tu iPhone o carrete.',
			},
			{
				question: '¿Editar texto en una captura de pantalla es gratis?',
				answer:
					'Sí. Puedes probar el editor de texto para capturas online gratis, sin marca de agua y sin necesidad de cuenta — los archivos se procesan y se eliminan automáticamente en una hora. Los flujos de mayor volumen, como la localización masiva para App Store, están disponibles en planes de pago, pero editar una sola imagen es gratuito.',
			},
			{
				question: '¿Se puede cambiar el texto de cualquier imagen o solo de capturas de pantalla?',
				answer:
					'Puedes editar texto en cualquier imagen, no solo en capturas de pantalla — el mismo proceso de detección, coincidencia de fuente y reconstrucción funciona en mockups de interfaz, gráficos de marketing y exportaciones de paneles. Por ahora funciona mejor con fondos planos o de degradado simple y texto en escritura latina; los fondos de foto recargados y las escrituras CJK o RTL están en la hoja de ruta pero aún no son compatibles.',
			},
		],
		faqFooterPre: '¿Sigues teniendo dudas?',
		faqFooterLinkText: 'Contáctanos',
		faqFooterPost: '— leemos todos los mensajes.',

		finalTitle: 'Pruébalo con tu propia captura de pantalla.',
		finalSubtitle: 'No necesitas una cuenta para probarlo. Se elimina automáticamente al cabo de una hora.',
		finalCta: 'Abrir el editor',
	},
	pricing: {
		metaTitle: 'Precios — ScreenshotTextEditor',
		metaDescription:
			'Precios sencillos para la edición de texto en capturas y la localización de App Store — desde una prueba gratuita hasta planes de equipo con localización masiva por CSV.',
		eyebrow: 'Precios',
		title: 'Precios sencillos, sin sorpresas por asiento.',
		subtitle:
			'Todos los planes incluyen el mismo proceso determinista y la misma puntuación de confianza. Los planes superiores desbloquean más volumen y el flujo de localización masiva. Ningún plan elimina las credenciales de contenido incrustadas en una exportación.',
		freeTier: {
			name: 'Gratis',
			period: '',
			description: 'Pruébalo con una captura real antes de comprometerte con nada.',
			features: [
				'10 renderizados / mes',
				'Editor de una sola imagen',
				'Puntuación de confianza y anulación manual de fuente',
				'Entrada PNG y JPEG, salida PNG',
				'Archivos eliminados después de 1 hora',
			],
			ctaLabel: 'Abrir el editor',
		},
		proTier: {
			name: 'Pro',
			period: '/ mes',
			description: 'Para equipos que publican capturas localizadas con regularidad.',
			features: [
				'Ediciones de imagen individual ilimitadas',
				'Localización masiva por CSV — sube una vez, exporta un ZIP por idioma',
				'Puntuación de confianza y anulación manual de fuente',
				'Procesamiento prioritario',
				'Todo lo del plan Gratis',
			],
			ctaLabel: 'Empezar con Pro',
		},
		teamTier: {
			name: 'Equipo',
			period: '/ asiento / mes',
			description: 'Trabajos por lotes compartidos y soporte prioritario para todo el equipo.',
			features: ['Todo lo de Pro, por asiento', 'Trabajos de localización por lotes compartidos', 'Soporte prioritario', 'Acceso anticipado a la API'],
			ctaLabel: 'Hablar con nosotros',
		},
		notHereYetTitle: 'Lo que aún no está disponible',
		notHereYetPre:
			'Texto sobre fotos y texturas complejas, escrituras CJK y RTL, texto con degradado o contorno, sombras paralelas, un plugin de Figma y una API pública están en la hoja de ruta pero aún no forman parte de la v1 — consulta los',
		notHereYetLinkText: 'términos',
		notHereYetPost: 'para conocer el alcance actual.',
	},
	about: {
		metaTitle: 'Nosotros — ScreenshotTextEditor',
		metaDescription:
			'Por qué construimos ScreenshotTextEditor: un proceso determinista de detectar-igualar-reconstruir para editar texto en capturas de pantalla, en lugar de una suposición generativa.',
		eyebrow: 'Nosotros',
		title: 'Sobre ScreenshotTextEditor',
		intro:
			'Construimos herramientas para el problema específico y molesto de cambiar las palabras de una captura de pantalla sin cambiar nada más de ella.',
		p1: 'ScreenshotTextEditor nació de una frustración concreta: corregir una errata, ocultar el nombre de un cliente o localizar una captura de App Store siempre implicaba reabrir un archivo de diseño que ya no existía, o conformarse con una edición «IA» generativa que se equivocaba de fuente y difuminaba el fondo detrás del texto. Los editores de fotos genéricos manejan bien los recortes y desenfoques; fallan en cuanto una sola línea de texto de interfaz pequeño y nítido necesita cambiar y todo lo demás debe permanecer idéntico píxel a píxel.',
		p2: 'Así que construimos lo contrario a un atajo generativo: un proceso determinista que detecta cada fragmento de texto en una imagen, mide su fuente, tamaño, grosor y color reales, y reconstruye solo esa región — verificada contra el original antes de entregarse.',
		buildingTowardTitle: 'Hacia dónde vamos',
		buildingTowardPre:
			'Hoy eso es un editor gratuito de una sola imagen sin registro y un flujo de localización masiva para capturas de App Store y Play Store. Ambos funcionan sobre el mismo proceso de detectar → igualar → reconstruir descrito en la',
		buildingTowardLinkText: 'página de inicio',
		buildingTowardPost: '.',
		valuesEyebrow: 'Lo que nos importa',
		valuesTitle: 'Principios detrás del proceso.',
		values: [
			{
				title: 'Determinista, no generativo',
				body: 'Construimos seis etapas independientes y verificables en lugar de pedirle a un modelo generativo que invente un texto plausible. Las fuentes de interfaz pequeñas y nítidas no sobreviven a una suposición.',
			},
			{
				title: 'Mostramos la confianza, no solo el resultado',
				body: 'Cada coincidencia de fuente lleva una puntuación de confianza visible. Si no podemos reproducir tu texto con la fiabilidad suficiente, te lo decimos en lugar de entregar una mala edición.',
			},
			{
				title: 'Tus capturas de pantalla no son el producto',
				body: 'Los archivos subidos se eliminan automáticamente y nunca entrenamos con las imágenes de los usuarios. Cada exportación incluye credenciales de contenido que la marcan como editada. Son metadatos invisibles, no un sello sobre la imagen — las exportaciones no llevan marca de agua visible.',
			},
		],
		ctaTitle: '¿Preguntas, comentarios o un error que reportar?',
		ctaSubtitle: 'Leemos todo lo que llega por la página de contacto.',
		ctaPrimary: 'Contáctanos',
		ctaSecondary: 'Abrir el editor',
	},
	contact: {
		metaTitle: 'Contacto — ScreenshotTextEditor',
		metaDescription: 'Ponte en contacto con ScreenshotTextEditor para soporte, preguntas de privacidad o cualquier duda sobre el proceso de edición de texto en capturas.',
		eyebrow: 'Contacto',
		title: 'Ponte en contacto',
		subtitle: 'Elige la dirección que mejor encaje — leemos todo y respondemos personas reales, no un bot de tickets.',
		supportChannel: {
			title: 'Soporte',
			body: 'Errores, coincidencias con poca confianza o cualquier cosa que no funcione como debería.',
		},
		privacyChannel: {
			title: 'Privacidad',
			body: 'Preguntas sobre qué recopilamos, cuánto tiempo lo conservamos o una solicitud de eliminación.',
		},
		legalChannel: {
			title: 'Legal',
			body: 'Términos del servicio, uso aceptable o preguntas sobre credenciales de contenido.',
		},
		footerNote:
			'¿Reportas una edición concreta que no salió bien? Incluye la captura original y, si aún la tienes, el resultado exportado — es la forma más rápida de que podamos reproducir y solucionar el problema.',
	},
};
