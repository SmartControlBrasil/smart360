from __future__ import annotations


COMPANY = {
    "name": "SMART360",
    "tagline": "Automacao industrial, seguranca da informacao e software com execucao tecnica.",
    "email": "contato@smart360.com.br",
    "phone": "(11) 4000-3600",
    "location": "Sao Paulo, atendimento regional e remoto em todo o Brasil",
    "restricted_area_url": "/ecossistema/",
}


PRIMARY_PILLARS = [
    {
        "title": "Automacao industrial e infraestrutura tecnica",
        "description": (
            "Projetos, retrofit e manutencao para CLPs, camaras climaticas, refrigeracao industrial, "
            "VRF, eletronica industrial e integracao entre sistemas de campo e gestao."
        ),
        "url_name": "institutional:automacao_industrial",
        "icon": "fas fa-industry",
    },
    {
        "title": "Seguranca da informacao",
        "description": (
            "Consultoria, endurecimento de ambiente, suporte especializado e postura corporativa para "
            "operacoes que nao podem depender de improviso."
        ),
        "url_name": "institutional:seguranca_da_informacao",
        "icon": "fas fa-shield-alt",
    },
    {
        "title": "Sites, sistemas e marketing digital",
        "description": (
            "Sites profissionais, sistemas sob medida, automacao de processos, SEO tecnico, IA aplicada "
            "e presenca digital preparada para gerar oportunidades reais."
        ),
        "url_name": "institutional:sites_sistemas_marketing",
        "icon": "fas fa-laptop-code",
    },
]


SERVICE_CATALOG = [
    {
        "title": "Automacao e controle",
        "description": "CLPs, IHMs, supervisao, integracao de sensores, paines e logica de processo.",
        "icon_image": "institutional/img/service-icon/1.png",
    },
    {
        "title": "Refrigeracao industrial e VRF",
        "description": "Instalacao, diagnostico, comissionamento e manutencao tecnica em ambientes criticos.",
        "icon_image": "institutional/img/service-icon/2.png",
    },
    {
        "title": "Infraestrutura e eletronica industrial",
        "description": "Analise de falhas, reparo, melhoria de confiabilidade e continuidade operacional.",
        "icon_image": "institutional/img/service-icon/3.png",
    },
    {
        "title": "Seguranca e suporte corporativo",
        "description": "Protecao de ambiente, revisao de acessos, hardening e apoio tecnico especializado.",
        "icon_image": "institutional/img/icon/16.svg",
    },
    {
        "title": "Sites, sistemas e integracoes",
        "description": "Portais, sistemas internos, integracoes com APIs, CRM e operacao assistida por IA.",
        "icon_image": "institutional/img/icon/17.svg",
    },
    {
        "title": "SEO e growth tecnico",
        "description": "Estrutura digital orientada a captacao, autoridade tecnica e conversao comercial.",
        "icon_image": "institutional/img/icon/18.svg",
    },
]


DELIVERY_PILLARS = [
    "Levantamento tecnico com foco no ambiente real da operacao.",
    "Proposta objetiva, com escopo claro e prioridade no retorno pratico.",
    "Execucao integrada entre engenharia, seguranca e software.",
    "Documentacao, suporte e evolucao continua sem retrabalho de base.",
]


INDUSTRY_HIGHLIGHTS = [
    "Automacao industrial e integracao de sistemas",
    "CLPs, sensores, IHMs e logica de processo",
    "Camaras climaticas e refrigeracao industrial",
    "Ar-condicionado VRF e manutencao especializada",
    "Eletronica industrial e confiabilidade operacional",
    "Projetos tecnicos para ambientes criticos",
]


DIFFERENTIALS = [
    {
        "title": "Tecnica de campo + visao de negocio",
        "description": (
            "Unimos manutencao, automacao, seguranca e desenvolvimento para resolver o problema inteiro, "
            "nao apenas a ponta mais visivel."
        ),
    },
    {
        "title": "Arquitetura preparada para crescer",
        "description": (
            "Cada entrega considera futura expansao, integracoes, indicadores e modularidade desde o inicio."
        ),
    },
    {
        "title": "Postura profissional em ambientes exigentes",
        "description": (
            "Atuacao orientada a previsibilidade, documentacao, continuidade operacional e comunicacao clara."
        ),
    },
]


ARTICLE_SUMMARIES = [
    {
        "title": "Automacao industrial com menos retrabalho operacional",
        "category": "Operacao tecnica",
        "summary": (
            "Como estruturar integracao entre campo, manutencao e gestao para reduzir parada, tempo de resposta "
            "e dependencia de conhecimento informal."
        ),
    },
    {
        "title": "Seguranca da informacao para empresas que operam no mundo real",
        "category": "Seguranca",
        "summary": (
            "Boas praticas de protecao de ambiente, controle de acesso e suporte especializado para operacoes "
            "que nao podem parar por causa de falhas basicas."
        ),
    },
    {
        "title": "Sites e sistemas como ativos comerciais, nao apenas vitrines",
        "category": "Software e marketing",
        "summary": (
            "O que muda quando o site, o sistema e a automacao de processos passam a trabalhar juntos para gerar "
            "lead, acelerar atendimento e melhorar conversao."
        ),
    },
]


CONTACT_CHANNELS = [
    {
        "title": "Comercial",
        "value": COMPANY["phone"],
        "detail": "Diagnostico inicial, propostas e novos projetos.",
        "icon": "institutional/img/icon/13.svg",
        "href": "tel:+551140003600",
    },
    {
        "title": "E-mail",
        "value": COMPANY["email"],
        "detail": "Solicitacoes tecnicas, escopo e documentacao comercial.",
        "icon": "institutional/img/icon/14.svg",
        "href": "mailto:contato@smart360.com.br",
    },
    {
        "title": "Cobertura",
        "value": "Atendimento tecnico e remoto",
        "detail": COMPANY["location"],
        "icon": "institutional/img/icon/15.svg",
        "href": "#contato-direto",
    },
]


SOLUTIONS = {
    "automacao-industrial": {
        "title": "Automacao industrial e infraestrutura tecnica",
        "headline": "Controle, confiabilidade e resposta tecnica para operacoes que nao podem parar.",
        "summary": (
            "Projetamos e executamos automacao industrial com foco em disponibilidade, seguranca operacional "
            "e integracao entre campo, manutencao e gestao."
        ),
        "theme_class": "theme-industrial",
        "hero_image": "institutional/img/banner-5/1.png",
        "hero_background": "institutional/img/banner-5/5.png",
        "support_image": "institutional/img/about/21.png",
        "route_name": "institutional:automacao_industrial",
        "bullets": [
            "CLPs, IHMs, redes industriais e logica de processo.",
            "Camaras climaticas, refrigeracao industrial e utilidades.",
            "Retrofit, manutencao tecnica e eletronica industrial.",
            "Integracao com sistemas, supervisao e indicadores operacionais.",
        ],
        "capabilities": [
            "Diagnostico de falhas e gargalos em automacao e infraestrutura tecnica.",
            "Projetos para VRF, refrigeracao industrial e ambientes controlados.",
            "Padronizacao de componentes, paines e rotinas de manutencao.",
            "Integracao de dados entre operacao, assistencia tecnica e software.",
        ],
    },
    "ar-condicionado": {
        "title": "Ar-condicionado e sistemas VRF",
        "headline": "Execucao tecnica para conforto, estabilidade de ambiente e performance energetica.",
        "summary": (
            "Atuamos em sistemas VRF e infraestrutura de climatizacao com foco em diagnostico preciso, "
            "manutencao preventiva e continuidade de operacao."
        ),
        "theme_class": "theme-climate",
        "hero_image": "institutional/img/about/13.png",
        "hero_background": "institutional/img/bg/8.png",
        "support_image": "institutional/img/about/15.png",
        "route_name": "institutional:ar_condicionado",
        "bullets": [
            "Instalacao, comissionamento e manutencao em VRF.",
            "Analise de performance, carga termica e eficiencia.",
            "Atendimento para ambientes corporativos e tecnicos.",
            "Integracao com rotinas de manutencao e automacao predial.",
        ],
        "capabilities": [
            "Planos preventivos para reduzir parada e consumo desnecessario.",
            "Corretivas com leitura tecnica de causa raiz.",
            "Padronizacao de processos para equipes proprias ou terceiras.",
            "Suporte especializado para expansao e modernizacao do sistema.",
        ],
    },
    "seguranca-da-informacao": {
        "title": "Seguranca da informacao",
        "headline": "Protecao de ambiente com postura corporativa, suporte tecnico e criterio.",
        "summary": (
            "Estruturamos controles praticos de seguranca para ambientes corporativos e operacionais, "
            "sem discurso vazio e sem dependencia de solucoes desconectadas da rotina da empresa."
        ),
        "theme_class": "theme-security",
        "hero_image": "institutional/img/about/32.png",
        "hero_background": "institutional/img/banner-6/1.png",
        "support_image": "institutional/img/about/31.png",
        "route_name": "institutional:seguranca_da_informacao",
        "bullets": [
            "Revisao de acessos, ativos, riscos e exposicoes.",
            "Hardening, boas praticas e suporte tecnico especializado.",
            "Organizacao de ambiente, postura e orientacao operacional.",
            "Apoio a times internos que precisam evoluir sem travar a empresa.",
        ],
        "capabilities": [
            "Mapeamento de superficies de risco com prioridade executavel.",
            "Apoio para protecao de endpoints, contas e ambientes criticos.",
            "Rotinas e orientacoes para reduzir falhas operacionais recorrentes.",
            "Visao integrada entre tecnologia, pessoas e continuidade de negocio.",
        ],
    },
    "sites-sistemas-marketing": {
        "title": "Sites, sistemas e marketing digital",
        "headline": "Presenca digital e software sob medida para vender melhor e operar com mais clareza.",
        "summary": (
            "Construimos sites profissionais, sistemas e automacoes que conectam atendimento, operacao "
            "e estrategia comercial em uma base coerente."
        ),
        "theme_class": "theme-digital",
        "hero_image": "institutional/img/home-13/service-1.png",
        "hero_background": "institutional/img/home-13/banner.webp",
        "support_image": "institutional/img/about/22.png",
        "route_name": "institutional:sites_sistemas_marketing",
        "bullets": [
            "Sites institucionais com foco comercial e SEO tecnico.",
            "Sistemas sob medida, portais e automacao de processos.",
            "Integracoes com IA, APIs, CRM e atendimento.",
            "Marketing digital com base tecnica e leitura de conversao.",
        ],
        "capabilities": [
            "Arquitetura de site preparada para crescimento e captacao de leads.",
            "Sistemas internos para reduzir operacao manual e ruido entre equipes.",
            "Conteudo, SEO e automacao com foco em presenca comercial consistente.",
            "Integração entre marketing, atendimento e indicadores de operacao.",
        ],
    },
}
