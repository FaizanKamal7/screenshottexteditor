import type { Translations } from '../types';

export const pt: Translations = {
	nav: {
		useCases: 'Casos de uso',
		pricing: 'Preços',
		about: 'Sobre',
		contact: 'Contato',
		openEditor: 'Abrir o editor',
		menu: 'Menu',
	},
	footer: {
		tagline: 'Um pipeline determinístico para editar texto em capturas de tela — indistinguível do original, pixel a pixel.',
		productHeading: 'Produto',
		openEditor: 'Abrir o editor',
		pricing: 'Preços',
		useCases: 'Casos de uso',
		useCasesHeading: 'Casos de uso',
		companyHeading: 'Empresa',
		about: 'Sobre',
		contact: 'Contato',
		privacy: 'Privacidade',
		terms: 'Termos',
		copyright: '© {year} ScreenshotTextEditor. Todas as exportações trazem credenciais de conteúdo incorporadas indicando que foram editadas.',
	},
	languageSwitcher: {
		ariaLabel: 'Alterar idioma',
	},
	home: {
		metaTitle: 'Editor de Texto para Capturas de Tela — Editor de Texto em Imagens com IA, Gratuito e Online',
		metaDescription:
			'Edite o texto de qualquer captura de tela ou imagem online com nosso editor de texto com IA gratuito. Ajusta fonte, tamanho, peso e cor automaticamente — sem marca d\'água, sem cadastro.',
		heroEyebrow: 'Edição de capturas de tela com precisão de pixel',
		heroTitleLine1: 'Edite o texto de uma captura de tela.',
		heroTitleLine2: 'Mantenha cada outro pixel exatamente igual.',
		heroSubtitle:
			'Clique em qualquer linha de texto de uma captura de tela, digite novamente, e a fonte, tamanho, peso e cor se ajustam automaticamente — o resto permanece idêntico, pixel a pixel.',
		ctaPrimary: 'Abrir o editor',
		ctaSecondary: 'Ver como funciona',

		diffEyebrow: 'Por que é diferente',
		diffTitle: 'Um pipeline determinístico, não um palpite gerado.',
		diffP1:
			'A maioria das ferramentas de texto em imagem se apoia em modelos generativos de imagem — ótimos em fotos e pôsteres, pouco confiáveis em texto de interface pequeno e nítido, onde cada pixel de uma letra importa. Construímos o oposto: seis etapas distintas e testáveis que detectam, medem e reproduzem a fonte real em vez de pintar algo plausível por cima.',
		diffP2:
			'Cada correspondência carrega uma pontuação de confiança. Se não conseguirmos reproduzir seu texto original com fidelidade suficiente, avisamos você — em vez de entregar uma edição que parece errada à primeira vista.',
		matchConfidenceLabel: 'Confiança da correspondência',
		matchItem1: '"Continue" — alternativa SF Pro, 17px',
		matchItem2: '"US$ 48,20" — Inter, 14px',
		matchItem3: '"Settings" — condensada, sem correspondência',
		highConfidence: 'confiança alta',
		needsReview: 'precisa de revisão',

		howEyebrow: 'Como funciona',
		howTitle: 'Detectar, corresponder, reconstruir.',
		steps: [
			{
				title: '1. Detectar',
				body: 'O OCR encontra cada trecho de texto no nível da linha, com caixas por caractere e o fator de escala da imagem — 1x, 2x ou 3x — medido a partir dos próprios glifos.',
			},
			{
				title: '2. Corresponder',
				body: 'Seu texto original é renderizado em uma lista curta de fontes prováveis para a plataforma e pontuado contra uma máscara alfa real até encontrar a fonte, tamanho, peso e espaçamento mais próximos — com a pontuação exibida, não escondida.',
			},
			{
				title: '3. Reconstruir',
				body: 'O texto antigo é apagado com um preenchimento correspondente e seu texto de substituição é renderizado na mesma linha de base e suavização, e revalidado contra o original antes de ser entregue.',
			},
		],

		builtForEyebrow: 'Feito para',
		builtForTitle: 'Localização de App Store e Play Store.',
		builtForP:
			'Oito capturas de tela, vinte idiomas — hoje isso significa reconstruir cada captura no Figma para cada idioma. Envie uma vez, entregue um CSV com as traduções e baixe um ZIP com cada idioma renderizado na fonte e no layout originais, reajustado automaticamente quando o texto traduzido for mais longo.',
		builtForCta: 'Veja como a localização funciona →',
		csvLabel: 'screenshots_de.csv',

		privacyEyebrow: 'Privacidade',
		privacyTitle: 'Suas capturas de tela não são o produto.',
		privacyP:
			'Capturas de tela costumam conter dados de conta, nomes de clientes ou números internos. Os uploads são excluídos automaticamente — uma hora por padrão — e nunca treinamos modelos com imagens de usuários. Cada exportação também carrega credenciais de conteúdo incorporadas indicando que foi editada, para que uma captura editada nunca passe silenciosamente por original.',
		privacyLink1: 'Leia a política de privacidade →',
		privacyLink2: 'Leia os termos de serviço →',

		useCasesEyebrow: 'Casos de uso',
		useCasesTitle: 'Um pipeline, qualquer captura de tela.',

		aboutToolEyebrow: 'Sobre a ferramenta',
		aboutToolTitle: 'O que é um editor de texto para capturas de tela?',
		aboutToolP1:
			'ScreenshotTextEditor é um <strong class="text-ink">editor de texto para capturas de tela</strong> criado para resolver um problema bem específico: mudar as palavras de uma captura de tela sem mudar mais nada nela. A maioria das pessoas que busca um <strong class="text-ink">editor de capturas de tela online</strong> esbarra no mesmo obstáculo — editores de fotos genéricos conseguem recortar, borrar ou anotar uma captura, mas assim que você tenta trocar uma linha de texto, a fonte fica errada, o espaçamento muda, ou o fundo atrás do texto antigo vira uma mancha. Esta ferramenta foi construída em torno de uma ideia diferente: detectar a fonte, o tamanho, o peso e a cor exatos de cada trecho de texto na imagem e depois reconstruí-lo com tanta precisão que a edição fica invisível mesmo com 400% de zoom.',
		aboutToolP2:
			'Como <strong class="text-ink">editor de texto para capturas de tela online</strong>, ele roda inteiramente no navegador — não há nada para instalar, nenhum plugin, nenhum software de design necessário. Envie uma captura de tela ou qualquer imagem com texto, clique na linha que quer mudar, digite seu texto de substituição e baixe o resultado. Por ser um <strong class="text-ink">editor de capturas de tela gratuito</strong> para imagens individuais, você pode testar todo o pipeline — detecção, correspondência de fonte e reconstrução — sem criar uma conta. É um <strong class="text-ink">editor de texto para capturas de tela online, gratuito e sem marca d\'água</strong>, então o que você exporta é exatamente o que você vê, sem nenhuma marca estampada sobre o seu trabalho.',
		aboutToolH3a: 'Editor de capturas de tela com IA, não um filtro genérico',
		aboutToolP3:
			'Chamar isso de <strong class="text-ink">editor de capturas de tela com IA</strong> não faz justiça ao que realmente acontece por baixo dos panos. Em vez de pedir a um modelo generativo de imagem que alucine um texto com aparência plausível — um atalho que costuma falhar em fontes de interface pequenas e nítidas — este pipeline de <strong class="text-ink">edição de texto com IA para capturas de tela</strong> executa seis etapas distintas e testáveis. Primeiro, o OCR detecta cada trecho de texto no nível do caractere e mede o fator de escala da imagem diretamente a partir dos glifos. Depois a ferramenta renderiza seu texto original em uma lista curta de fontes prováveis para a plataforma e pontua cada candidata contra a máscara real de pixels até encontrar a correspondência mais próxima de família tipográfica, tamanho, peso e espaçamento entre letras. Só então ela apaga o texto antigo com um preenchimento correspondente e renderiza sua substituição com a mesma linha de base e suavização. Cada correspondência carrega uma pontuação de confiança visível, então se o pipeline de <strong class="text-ink">edição de texto com IA gratuita para capturas de tela</strong> não conseguir reproduzir seu texto original com confiabilidade suficiente, ele avisa — em vez de entregar silenciosamente uma edição que parece errada.',
		aboutToolH3b: 'Mais que um editor de capturas de tela — um editor completo de texto em imagens online',
		aboutToolP4:
			'Embora tenha começado como editor de texto para capturas de tela, o mesmo pipeline funciona como um <strong class="text-ink">editor de texto em imagens online</strong> de uso geral. Qualquer PNG, JPG ou mockup de interface exportado com texto pode ser processado da mesma forma — como um <strong class="text-ink">editor de texto em imagens com IA</strong> para peças de marketing, exportações de painéis com números desatualizados, ou capturas de App Store que precisam ser localizadas para outro idioma. Por ser um <strong class="text-ink">editor de texto em imagens online e gratuito</strong>, equipes que de outra forma reconstruiriam cada captura manualmente no Figma para cada idioma podem, em vez disso, enviar uma vez, entregar um CSV de traduções e baixar cada variante de idioma renderizada na fonte e no layout originais.',
		aboutToolH3c: 'Por que as equipes escolhem este editor de texto online para capturas de tela',
		aboutToolP5Pre:
			'Seja para corrigir rapidamente um erro de digitação, ocultar o nome de um cliente antes de uma demonstração, ou gerar um lote de capturas de App Store localizadas, este <strong class="text-ink">editor de capturas de tela online</strong> foi feito para que a edição passe despercebida em vez de chamar atenção. É gratuito para testar, não exige conhecimento de design, exclui seus uploads automaticamente e nunca treina modelos com as imagens que você envia — então a única coisa que muda na sua captura de tela é o texto que você quis mudar. Saiba mais sobre',
		aboutToolP5LinkText: 'por que construímos assim',

		faqEyebrow: 'Perguntas frequentes',
		faqTitle: 'Perguntas frequentes.',
		faqs: [
			{
				question: 'Como usar um editor de texto em imagens online?',
				answer:
					'Abra o editor ScreenshotTextEditor e solte sua captura de tela ou imagem — sem necessidade de cadastro. Nosso editor de capturas de tela com IA escaneia a imagem, detecta cada trecho de texto e permite clicar em qualquer linha para reescrevê-la. Digite seu texto de substituição, e a ferramenta ajusta automaticamente a fonte, tamanho, peso, cor e suavização originais antes de reconstruir a imagem em torno do seu novo texto. Exporte como PNG ou JPG em segundos, tudo pelo navegador.',
			},
			{
				question: 'Como remover texto de uma imagem usando um editor com IA?',
				answer:
					'Selecione o trecho de texto que deseja remover e exclua seu conteúdo ou use a opção de apagar. O editor de texto em imagens com IA preenche a área atrás do texto antigo com um fundo correspondente — reconstruindo cor, textura e gradientes — para que não sobre nenhuma marca visível, borrão ou marca d\'água. Isso funciona para rótulos de interface, legendas, marcas de tempo ou qualquer camada de texto detectada na imagem.',
			},
			{
				question: 'Como funciona um editor de texto em imagens online?',
				answer:
					'Nosso editor de texto em imagens online executa um pipeline de detecção → correspondência → reconstrução. Primeiro, o OCR localiza cada trecho de texto no nível da linha e do caractere e mede o fator de escala da imagem. Em seguida, renderiza seu texto em uma lista curta de fontes prováveis e pontua cada uma contra os pixels reais até encontrar a fonte, tamanho, peso e espaçamento mais próximos. Por fim, apaga o texto original com um preenchimento correspondente e renderiza sua substituição na mesma linha de base, para que o resultado resista a uma inspeção de perto.',
			},
			{
				question: 'Como editar o texto de uma captura de tela?',
				answer:
					'Envie sua captura de tela para o editor de texto para capturas de tela, clique no texto que deseja mudar e digite o novo conteúdo. A ferramenta mantém cada outro pixel — ícones, botões, fundos e layout — exatamente como estava, reconstruindo apenas a região do texto. Funciona inteiramente online, sem software de design ou correspondência manual de fontes.',
			},
			{
				question: 'Como editar o texto de uma captura de tela no iPhone?',
				answer:
					'Tire sua captura de tela no iPhone normalmente e depois envie-a ao ScreenshotTextEditor pelo Safari ou Chrome no seu celular, ou envie primeiro para um computador via AirDrop. Como o editor de capturas de tela roda inteiramente online no navegador, não há nenhum app para instalar — abra o editor em qualquer dispositivo, selecione o texto, substitua-o e baixe a captura editada diretamente para seu iPhone ou rolo da câmera.',
			},
			{
				question: 'Editar texto em captura de tela é gratuito?',
				answer:
					'Sim. Você pode testar o editor de texto para capturas de tela online gratuitamente, sem marca d\'água, sem necessidade de conta — os uploads são processados e depois excluídos automaticamente em até uma hora. Fluxos de maior volume, como localização em massa para App Store, estão disponíveis em planos pagos, mas a edição de uma única imagem é gratuita.',
			},
			{
				question: 'É possível mudar o texto de qualquer imagem ou só de capturas de tela?',
				answer:
					'Você pode editar texto em qualquer imagem, não só em capturas de tela. O mesmo pipeline de detecção, correspondência de fonte e reconstrução funciona em mockups de interface, peças de marketing, exportações de painéis, PNGs e fotos que contenham texto — onde quer que a ferramenta detecte um trecho de texto, ela pode substituí-lo preservando a aparência original.',
			},
		],
		faqFooterPre: 'Ainda tem dúvidas?',
		faqFooterLinkText: 'Fale conosco',
		faqFooterPost: '— lemos todas as mensagens.',

		finalTitle: 'Experimente na sua própria captura de tela.',
		finalSubtitle: 'Nenhuma conta necessária para testar. Excluída automaticamente após uma hora.',
		finalCta: 'Abrir o editor',
	},
	pricing: {
		metaTitle: 'Preços — ScreenshotTextEditor',
		metaDescription:
			'Preços simples para edição de texto em capturas de tela e localização de App Store — de um teste gratuito a planos de equipe com localização em lote por CSV.',
		eyebrow: 'Preços',
		title: 'Preços simples, sem surpresas por assento.',
		subtitle:
			'Todos os planos têm o mesmo pipeline determinístico e a mesma pontuação de confiança. Planos mais altos desbloqueiam mais volume e o fluxo de localização em lote. Nenhum plano remove as credenciais de conteúdo incorporadas em uma exportação.',
		freeTier: {
			name: 'Gratuito',
			period: '',
			description: 'Teste em uma captura de tela real antes de se comprometer com qualquer coisa.',
			features: [
				'10 renderizações / mês',
				'Editor de imagem única',
				'Pontuação de confiança e substituição manual de fonte',
				'Entrada PNG e JPEG, saída PNG',
				'Uploads excluídos após 1 hora',
			],
			ctaLabel: 'Abrir o editor',
		},
		proTier: {
			name: 'Pro',
			period: '/ mês',
			description: 'Para equipes que entregam capturas localizadas com regularidade.',
			features: [
				'Edições de imagem única ilimitadas',
				'Localização em lote por CSV — envie uma vez, exporte um ZIP por idioma',
				'Pontuação de confiança e substituição manual de fonte',
				'Processamento prioritário',
				'Tudo do plano Gratuito',
			],
			ctaLabel: 'Começar com o Pro',
		},
		teamTier: {
			name: 'Equipe',
			period: '/ assento / mês',
			description: 'Tarefas em lote compartilhadas e suporte prioritário para toda a equipe.',
			features: ['Tudo do Pro, por assento', 'Tarefas de localização em lote compartilhadas', 'Suporte prioritário', 'Acesso antecipado à API'],
			ctaLabel: 'Fale conosco',
		},
		notHereYetTitle: 'O que ainda não está disponível',
		notHereYetPre:
			'Texto sobre fotos e texturas complexas, escritas CJK e RTL, texto com gradiente ou contorno, sombras projetadas, um plugin do Figma e uma API pública estão no roteiro, mas ainda não foram lançados na v1 — consulte os',
		notHereYetLinkText: 'termos',
		notHereYetPost: 'para o escopo atual.',
	},
	about: {
		metaTitle: 'Sobre — ScreenshotTextEditor',
		metaDescription:
			'Por que construímos o ScreenshotTextEditor: um pipeline determinístico de detectar-corresponder-reconstruir para editar texto em capturas de tela, em vez de um palpite generativo.',
		eyebrow: 'Sobre',
		title: 'Sobre o ScreenshotTextEditor',
		intro:
			'Construímos ferramentas para o problema específico e irritante de mudar as palavras de uma captura de tela sem mudar mais nada nela.',
		p1: 'O ScreenshotTextEditor nasceu de uma frustração bem pontual: corrigir um erro de digitação, ocultar o nome de um cliente ou localizar uma captura de App Store sempre significava reabrir um arquivo de design que já não existia, ou se contentar com uma edição "IA" generativa que errava a fonte e borrava o fundo atrás dela. Editores de fotos genéricos lidam bem com recortes e desfoques; eles falham no momento em que uma única linha de texto de interface pequeno e nítido precisa mudar e tudo ao redor precisa permanecer idêntico, pixel a pixel.',
		p2: 'Então construímos o oposto de um atalho generativo: um pipeline determinístico que detecta cada trecho de texto em uma imagem, mede sua fonte, tamanho, peso e cor reais, e reconstrói apenas essa região — verificada contra o original antes de ser entregue.',
		buildingTowardTitle: 'Para onde estamos indo',
		buildingTowardPre:
			'Hoje isso é um editor de imagem única gratuito e sem cadastro, e um fluxo de localização em lote para capturas de tela da App Store e da Play Store. Ambos rodam sobre o mesmo pipeline de detectar → corresponder → reconstruir descrito na',
		buildingTowardLinkText: 'página inicial',
		buildingTowardPost: '.',
		valuesEyebrow: 'O que nos importa',
		valuesTitle: 'Princípios por trás do pipeline.',
		values: [
			{
				title: 'Determinístico em vez de generativo',
				body: 'Construímos seis etapas distintas e testáveis em vez de pedir a um modelo generativo que alucine um texto plausível. Fontes de interface pequenas e nítidas não sobrevivem a um palpite.',
			},
			{
				title: 'Mostramos a confiança, não só o resultado',
				body: 'Cada correspondência de fonte carrega uma pontuação de confiança visível. Se não conseguirmos reproduzir seu texto com confiabilidade suficiente, dizemos isso em vez de entregar uma edição ruim.',
			},
			{
				title: 'Suas capturas de tela não são o produto',
				body: 'Os uploads são excluídos automaticamente e nunca treinamos modelos com imagens de usuários. Cada exportação carrega credenciais de conteúdo incorporadas indicando que foi editada.',
			},
		],
		ctaTitle: 'Perguntas, sugestões ou um bug para relatar?',
		ctaSubtitle: 'Lemos tudo o que chega pela página de contato.',
		ctaPrimary: 'Fale conosco',
		ctaSecondary: 'Abrir o editor',
	},
	contact: {
		metaTitle: 'Contato — ScreenshotTextEditor',
		metaDescription: 'Entre em contato com o ScreenshotTextEditor para suporte, questões de privacidade ou qualquer coisa sobre o pipeline de edição de texto em capturas de tela.',
		eyebrow: 'Contato',
		title: 'Entre em contato',
		subtitle: 'Escolha o endereço que mais combina — lemos tudo e respondemos como pessoas de verdade, não um robô de tickets.',
		supportChannel: {
			title: 'Suporte',
			body: 'Bugs, correspondências de baixa confiança ou qualquer coisa que não esteja funcionando como deveria.',
		},
		privacyChannel: {
			title: 'Privacidade',
			body: 'Dúvidas sobre o que coletamos, por quanto tempo mantemos ou um pedido de exclusão.',
		},
		legalChannel: {
			title: 'Jurídico',
			body: 'Termos de serviço, uso aceitável ou dúvidas sobre credenciais de conteúdo.',
		},
		footerNote:
			'Está relatando uma edição específica que não saiu bem? Inclua a captura de tela original e, se ainda tiver, o resultado exportado — é a forma mais rápida de reproduzirmos e corrigirmos o problema.',
	},
};
