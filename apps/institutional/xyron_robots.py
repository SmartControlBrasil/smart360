"""Static content for Xyron Robotics institutional detail pages."""

XYRON_ROBOTS = [
    {
        "slug": "liro-littlebot",
        "name": "LIRO / LittleBot",
        "short_name": "LIRO / LittleBot",
        "subtitle": "Robô educacional com IA para experiências pedagógicas, projetos maker e interação humano-robô com mediação humana.",
        "image": "institutional/eitech/img/all-images/blog/banner-little.png",
    },
    {
        "slug": "neobot",
        "name": "NeoBot",
        "short_name": "NeoBot",
        "subtitle": "Robô de recepção e atendimento para comunicação institucional, orientação de visitantes e experiências de relacionamento.",
        "image": "institutional/eitech/img/all-images/blog/banner-neo.webp",
    },
    {
        "slug": "buddy",
        "name": "Buddy",
        "short_name": "Buddy",
        "subtitle": "Robô compacto e social para interação, demonstrações, educação, eventos e aproximação humano-robô.",
        "image": "institutional/eitech/img/all-images/blog/banner-budybot.webp",
    },
    {
        "slug": "patrol-orbit",
        "name": "Patrol / Orbit",
        "short_name": "Patrol / Orbit",
        "subtitle": "Robôs para segurança patrimonial, rondas, inspeção e monitoramento assistido em ambientes corporativos e condominiais.",
        "image": "institutional/eitech/img/all-images/blog/banner-orbitbot.webp",
    },
    {
        "slug": "hygibot",
        "name": "HygiBot",
        "short_name": "HygiBot",
        "subtitle": "Robô de limpeza e higienização para padronizar rotinas em ambientes comerciais, educacionais, hospitalares e condominiais.",
        "image": "institutional/eitech/img/all-images/blog/banner-hygibot.webp",
    },
    {
        "slug": "hostbot",
        "name": "HostBot",
        "short_name": "HostBot",
        "subtitle": "Robô host para hospitalidade, recepção, eventos, restaurantes, hotéis, clínicas e orientação de visitantes.",
        "image": "institutional/eitech/img/all-images/blog/banner-hostbot.webp",
    },
    {
        "slug": "waiterbot",
        "name": "WaiterBot",
        "short_name": "WaiterBot",
        "subtitle": "Robô de apoio ao atendimento de salão e entrega interna para restaurantes, bares, hotéis, eventos e ambientes de serviço.",
        "image": "institutional/eitech/img/all-images/blog/banner-waiterbot.webp",
    },
    {
        "slug": "carebot",
        "name": "CareBot",
        "short_name": "CareBot",
        "subtitle": "Robô de cuidado assistido para clínicas, hospitais, casas de repouso e ambientes de apoio a equipes e pacientes.",
        "image": "institutional/eitech/img/all-images/blog/banner-carebot.webp",
    },
    {
        "slug": "mowerbot",
        "name": "MowerBot",
        "short_name": "MowerBot",
        "subtitle": "Robô cortador de grama para áreas externas, condomínios, clubes, escolas, hotéis e manutenção paisagística automatizada.",
        "image": "institutional/eitech/img/all-images/blog/banner-mowerbot.webp",
    },
]



XYRON_ROBOT_DETAILS = {
    "liro-littlebot": {
        "summary": "Robô educacional para escolas, espaços maker e experiências de IA com mediação humana.",
        "primary_application": "Educação, robótica pedagógica e projetos maker",
        "functions": [
            "Interação educacional com estudantes e educadores",
            "Apoio a atividades pedagógicas e projetos maker",
            "Conversas assistidas e demonstrações de IA",
            "Experiências de robótica com mediação do professor",
            "Apoio a apresentações, feiras e aulas guiadas",
            "Uso consultivo em inclusão e engajamento escolar",
        ],
        "technical_specs": [
            ("Categoria", "Robô educacional/interativo"),
            ("Aplicação principal", "Experiências pedagógicas com robótica e IA"),
            ("Ambiente indicado", "Escolas, laboratórios, espaços maker e projetos educacionais"),
            ("Tipo de operação", "Uso assistido com mediação humana"),
            ("Observações", "Recursos e configuração devem ser confirmados conforme modelo e escopo do projeto"),
        ],
        "ideal_for": ["Escolas", "Espaços maker", "Projetos educacionais", "Feiras de tecnologia"],
        "commercial_notes": "A recomendação depende de objetivo pedagógico, idade do público, infraestrutura, governança de dados e rotina de uso. O LIRO não substitui o professor.",
    },
    "neobot": {
        "summary": "Robô de recepção e comunicação institucional para visitantes, eventos e showrooms.",
        "primary_application": "Recepção, atendimento inicial e orientação de visitantes",
        "functions": [
            "Recepção e boas-vindas",
            "Orientação de visitantes",
            "Comunicação institucional",
            "Apresentação de serviços e informações",
            "Apoio em eventos, feiras e showrooms",
            "Direcionamento para equipe humana quando necessário",
        ],
        "technical_specs": [
            ("Categoria", "Robô de recepção e atendimento"),
            ("Aplicação principal", "Orientação e interação com visitantes"),
            ("Ambiente indicado", "Empresas, escolas, clínicas, eventos, lojas e showrooms"),
            ("Tipo de operação", "Atendimento assistido com roteiro e supervisão"),
            ("Observações", "Recursos de idioma, conteúdo e integração variam conforme configuração e escopo"),
        ],
        "ideal_for": ["Recepções corporativas", "Eventos", "Showrooms", "Clínicas", "Escolas"],
        "commercial_notes": "A implantação deve definir jornada, mensagens, limites de atendimento e momento de transferência para equipe humana.",
    },
    "buddy": {
        "summary": "Robô compacto/social para interação, demonstração tecnológica e aproximação humano-robô.",
        "primary_application": "Interação, educação, demonstrações e eventos",
        "functions": [
            "Interação social com público",
            "Demonstração tecnológica",
            "Atendimento leve e guiado",
            "Apoio educacional e institucional",
            "Aproximação humano-robô",
            "Presença em eventos e ações de inovação",
        ],
        "technical_specs": [
            ("Categoria", "Robô social/interativo"),
            ("Aplicação principal", "Demonstração, interação e apoio educacional"),
            ("Ambiente indicado", "Escolas, eventos, empresas e ambientes controlados"),
            ("Tipo de operação", "Uso supervisionado com roteiro de interação"),
            ("Observações", "Configuração, autonomia e acessórios devem ser confirmados conforme modelo e fornecimento"),
        ],
        "ideal_for": ["Eventos", "Escolas", "Demonstrações", "Ações institucionais"],
        "commercial_notes": "O Buddy deve ser posicionado como apoio à interação e demonstração, não como solução isolada para atendimento ou segurança.",
    },
    "patrol-orbit": {
        "summary": "Robôs para rondas, inspeção e monitoramento assistido em segurança patrimonial.",
        "primary_application": "Segurança patrimonial, rondas e inspeção assistida",
        "functions": [
            "Rondas assistidas",
            "Presença ostensiva em áreas definidas",
            "Inspeção de áreas internas ou externas conforme ambiente",
            "Apoio ao monitoramento e registro operacional",
            "Integração consultiva com rotinas de segurança",
            "Apoio à padronização de rotas e critérios de alerta",
        ],
        "technical_specs": [
            ("Categoria", "Robô de patrulhamento e inspeção"),
            ("Aplicação principal", "Rondas e monitoramento assistido"),
            ("Ambiente indicado", "Condomínios, empresas, áreas corporativas, estacionamentos e ambientes mapeados"),
            ("Tipo de operação", "Rotas e protocolos definidos com a equipe de segurança"),
            ("Observações", "Sensores, integração e recursos de monitoramento devem ser confirmados conforme modelo e escopo"),
        ],
        "ideal_for": ["Condomínios", "Empresas", "Áreas amplas", "Operações com rondas"],
        "commercial_notes": "A proposta é apoiar equipes de segurança, ampliar cobertura e padronizar rondas, sem substituir integralmente vigilantes ou protocolos humanos.",
    },
    "hygibot": {
        "summary": "Robô para apoiar limpeza e higienização em áreas comerciais, institucionais e de alto fluxo.",
        "primary_application": "Limpeza, higienização e padronização de rotinas",
        "functions": [
            "Apoio a limpeza e higienização",
            "Padronização de rotinas por área",
            "Apoio em grandes áreas internas",
            "Redução de esforço operacional repetitivo",
            "Uso em ambientes comerciais e institucionais",
            "Acompanhamento com processo e supervisão definidos",
        ],
        "technical_specs": [
            ("Categoria", "Robô de limpeza/higienização"),
            ("Aplicação principal", "Rotinas de limpeza assistida"),
            ("Ambiente indicado", "Escolas, clínicas, hospitais, shoppings, condomínios e ambientes comerciais"),
            ("Tipo de operação", "Uso planejado por áreas, horários e protocolos"),
            ("Observações", "Funções, insumos, autonomia e compatibilidade com piso variam conforme modelo e ambiente"),
        ],
        "ideal_for": ["Shoppings", "Escolas", "Hospitais", "Clínicas", "Condomínios"],
        "commercial_notes": "O HygiBot apoia a equipe de limpeza e exige supervisão, protocolos e diagnóstico do espaço antes da proposta.",
    },
    "hostbot": {
        "summary": "Robô host para hospitalidade, recepção, orientação e experiências em eventos.",
        "primary_application": "Recepção, hospitalidade e orientação de visitantes",
        "functions": [
            "Recepção e hospitalidade",
            "Orientação de visitantes",
            "Atendimento inicial com roteiro definido",
            "Apoio em eventos e feiras",
            "Apresentação de informações institucionais",
            "Encaminhamento para equipe humana quando necessário",
        ],
        "technical_specs": [
            ("Categoria", "Robô host/interativo"),
            ("Aplicação principal", "Hospitalidade e recepção assistida"),
            ("Ambiente indicado", "Eventos, hotéis, restaurantes, clínicas, empresas e recepções"),
            ("Tipo de operação", "Jornada guiada com conteúdo e supervisão"),
            ("Observações", "Telas, idiomas, conteúdos e integrações devem ser confirmados conforme configuração"),
        ],
        "ideal_for": ["Eventos", "Hotéis", "Restaurantes", "Clínicas", "Recepções"],
        "commercial_notes": "O HostBot melhora a experiência de chegada e orientação, mas não substitui acolhimento humano nem atendimento especializado.",
    },
    "waiterbot": {
        "summary": "Robô de apoio ao salão para transporte interno de itens em restaurantes, hotéis e eventos.",
        "primary_application": "Apoio ao atendimento de salão e entrega interna",
        "functions": [
            "Apoio ao atendimento de salão",
            "Transporte interno de itens",
            "Apoio a garçons e equipe operacional",
            "Redução de deslocamentos repetitivos",
            "Operação em restaurantes, hotéis e eventos",
            "Melhoria de fluxo interno com rotas definidas",
        ],
        "technical_specs": [
            ("Categoria", "Robô de apoio a entregas internas"),
            ("Aplicação principal", "Transporte assistido de itens no salão"),
            ("Ambiente indicado", "Restaurantes, hotéis, bares, eventos e ambientes de serviço"),
            ("Tipo de operação", "Rotas internas com pontos de retirada e entrega"),
            ("Observações", "Capacidade, autonomia e recursos de navegação variam conforme modelo, layout e escopo"),
        ],
        "ideal_for": ["Restaurantes", "Hotéis", "Eventos", "Bares", "Food service"],
        "commercial_notes": "O WaiterBot apoia deslocamentos e entregas. Não deve ser vendido como substituto completo de garçons ou da equipe de salão.",
    },
    "carebot": {
        "summary": "Robô de cuidado assistido para interação, orientação e apoio a equipes em ambientes de saúde.",
        "primary_application": "Cuidado assistido e humanização tecnológica",
        "functions": [
            "Apoio assistido e interação",
            "Orientação em rotinas informativas",
            "Lembretes operacionais conforme escopo",
            "Apoio à equipe em fluxos definidos",
            "Humanização tecnológica",
            "Atenção a privacidade, consentimento e protocolos",
        ],
        "technical_specs": [
            ("Categoria", "Robô de cuidado assistido"),
            ("Aplicação principal", "Apoio à interação e orientação em ambientes de cuidado"),
            ("Ambiente indicado", "Clínicas, hospitais, casas de repouso e instituições de cuidado"),
            ("Tipo de operação", "Uso assistido conforme protocolos do local"),
            ("Observações", "Recursos de interação, monitoramento e integração devem ser avaliados conforme modelo, privacidade e escopo"),
        ],
        "ideal_for": ["Clínicas", "Hospitais", "Casas de repouso", "Cuidado assistido"],
        "commercial_notes": "O CareBot não realiza promessa médica e não substitui profissionais de saúde, cuidadores ou protocolos clínicos.",
    },
    "mowerbot": {
        "summary": "Robô para corte de grama e apoio à manutenção paisagística em áreas externas.",
        "primary_application": "Corte de grama e manutenção externa assistida",
        "functions": [
            "Corte de grama em áreas planejadas",
            "Apoio à manutenção paisagística",
            "Padronização de áreas externas",
            "Redução de esforço repetitivo",
            "Operação em condomínios, clubes, escolas, hotéis e áreas corporativas",
            "Apoio à produtividade de equipes externas",
        ],
        "technical_specs": [
            ("Categoria", "Robô cortador de grama"),
            ("Aplicação principal", "Corte de grama e apoio à manutenção paisagística"),
            ("Ambiente indicado", "Condomínios, clubes, escolas, hotéis, áreas corporativas, jardins e pequenas propriedades"),
            ("Tipo de operação", "Uso planejado após avaliação do terreno"),
            ("Observações", "Capacidade, inclinação, autonomia e recursos devem ser confirmados conforme modelo, terreno e escopo"),
        ],
        "ideal_for": ["Condomínios", "Clubes", "Escolas", "Hotéis", "Áreas corporativas", "Jardins"],
        "commercial_notes": "O MowerBot apoia produtividade e padronização, mas depende de avaliação do terreno, segurança e rotina de manutenção.",
    },
}

for robot in XYRON_ROBOTS:
    robot.update(XYRON_ROBOT_DETAILS.get(robot["slug"], {}))

XYRON_ROBOTS_BY_SLUG = {robot["slug"]: robot for robot in XYRON_ROBOTS}


def get_xyron_robot(slug):
    return XYRON_ROBOTS_BY_SLUG.get(slug)


def get_other_xyron_robots(slug):
    return [robot for robot in XYRON_ROBOTS if robot["slug"] != slug]


def get_featured_xyron_robots(slug, limit=3):
    return get_other_xyron_robots(slug)[:limit]
