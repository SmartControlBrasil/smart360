from django.core.management.base import BaseCommand

from apps.livia_assistant.models import LiviaKnowledgeItem


KNOWLEDGE_ITEMS = [
    {
        "title": "Manutenção industrial",
        "slug": "manutencao-industrial",
        "category": LiviaKnowledgeItem.Category.SERVICES,
        "priority": 90,
        "keywords": "manutenção industrial maquinas equipamentos preventiva corretiva fabrica produção",
        "content": "A Smart Control Brasil apoia empresas com manutenção industrial preventiva e corretiva, diagnóstico de falhas, organização de rotinas técnicas e apoio à continuidade operacional.",
    },
    {
        "title": "Automação industrial",
        "slug": "automacao-industrial",
        "category": LiviaKnowledgeItem.Category.SERVICES,
        "priority": 85,
        "keywords": "automação industrial clp plc ihm sensores comandos eletricos processos",
        "content": "A frente de automação industrial atende demandas de melhoria de processos, comandos elétricos, integração de equipamentos e apoio técnico para tornar operações mais seguras e controláveis.",
    },
    {
        "title": "Ar-condicionado para empresas e academias",
        "slug": "ar-condicionado-empresas-academias",
        "category": LiviaKnowledgeItem.Category.SERVICES,
        "priority": 84,
        "keywords": "ar-condicionado climatização empresas academias split manutenção limpeza instalação",
        "content": "A Smart Control Brasil atende ar-condicionado em ambientes corporativos, comerciais e academias, com foco em manutenção, diagnóstico, conforto térmico e operação adequada dos equipamentos.",
    },
    {
        "title": "PMOC",
        "slug": "pmoc",
        "category": LiviaKnowledgeItem.Category.TECHNICAL,
        "priority": 88,
        "keywords": "pmoc plano manutenção operação controle ar condicionado climatização legislação",
        "content": "O PMOC organiza plano de manutenção, operação e controle para sistemas de climatização. A Smart Control Brasil pode apoiar empresas na estruturação e execução de rotinas relacionadas ao PMOC.",
    },
    {
        "title": "Câmaras climáticas",
        "slug": "camaras-climaticas",
        "category": LiviaKnowledgeItem.Category.SERVICES,
        "priority": 82,
        "keywords": "câmara climática camara climatica temperatura umidade laboratório ensaio manutenção",
        "content": "A Smart Control Brasil atua em diagnóstico e manutenção de câmaras climáticas, considerando controle de temperatura, umidade, estabilidade operacional e criticidade do equipamento no processo do cliente.",
    },
    {
        "title": "Equipamentos de academia",
        "slug": "equipamentos-de-academia",
        "category": LiviaKnowledgeItem.Category.SERVICES,
        "priority": 80,
        "keywords": "academia esteira bike elíptico musculação equipamentos manutenção preventiva corretiva",
        "content": "A Smart Control Brasil atende equipamentos de academia com manutenção preventiva e corretiva, ajudando a reduzir paradas, melhorar disponibilidade e organizar rotinas de cuidado técnico.",
    },
    {
        "title": "Contratos de manutenção",
        "slug": "contratos-de-manutencao",
        "category": LiviaKnowledgeItem.Category.PROCESS,
        "priority": 78,
        "keywords": "contrato manutenção preventiva recorrente sla atendimento mensal plano",
        "content": "Contratos de manutenção podem ser avaliados para clientes que precisam de acompanhamento recorrente, previsibilidade técnica e melhor controle de visitas, ativos e prioridades de atendimento.",
    },
    {
        "title": "Smart360",
        "slug": "smart360",
        "category": LiviaKnowledgeItem.Category.SMART360,
        "priority": 76,
        "keywords": "smart360 sistema ordens de serviço dashboard ativos gestão implantação assistida piloto",
        "content": "O Smart360 é uma iniciativa em evolução para apoiar gestão de ordens de serviço, ativos, indicadores e operação técnica, com abordagem de pré-lançamento, projeto piloto e implantação assistida quando fizer sentido.",
    },
    {
        "title": "Política de preços",
        "slug": "politica-de-precos",
        "category": LiviaKnowledgeItem.Category.PRICING_POLICY,
        "priority": 95,
        "keywords": "preço valor orçamento cotação visita prazo proposta cobrança",
        "content": "A Lívia não deve informar valores, prazos fechados ou condições comerciais finais sem avaliação humana. Pedidos de orçamento devem priorizar coleta de dados para diagnóstico inicial.",
    },
    {
        "title": "Segurança em risco técnico",
        "slug": "seguranca-risco-tecnico",
        "category": LiviaKnowledgeItem.Category.SAFETY,
        "priority": 100,
        "keywords": "cheiro de queimado risco elétrico vazamento gás superaquecimento emergência urgente estrutural parada segura",
        "content": "Em situações com cheiro de queimado, risco elétrico, vazamento de gás, superaquecimento ou risco estrutural, a orientação deve ser interromper o uso com segurança e acionar atendimento humano qualificado.",
    },
    {
        "title": "Xyron Robotics - Visão geral",
        "slug": "xyron-robotics-visao-geral",
        "category": LiviaKnowledgeItem.Category.TECHNICAL,
        "priority": 93,
        "keywords": "xyron xyron robotics o que é xyron o que e xyron quem é a xyron quem e a xyron empresa xyron robótica xyron robotica xyron robos xyron catálogo xyron catalogo xyron soluções xyron smart control xyron",
        "content": "A Xyron Robotics é uma empresa de tecnologia robótica com soluções voltadas para educação, recepção, atendimento, segurança, limpeza, saúde, entrega, inspeção e operação autônoma. A Smart Control Brasil atua conectando essas soluções a aplicações reais, apoiando diagnóstico, escolha do robô, implantação, treinamento e integração conforme o ambiente do cliente. Principais linhas: LIRO / LittleBot para educação e inclusão; NeoBot para recepção e atendimento inteligente; HygiBot / Dune Bot para limpeza autônoma; OrbitBot / Patrol Bot para segurança e patrulhamento; Buddy Bot para inspeção, segurança e áreas de difícil acesso; WaiterBot para entrega e apoio operacional; CareBot para saúde e cuidado assistivo; HostBot para recepção e eventos; MowerBot para corte de grama e áreas externas.",
    },
    {
        "title": "Xyron LIRO - Robô educacional com IA",
        "slug": "xyron-liro-littlebot",
        "category": LiviaKnowledgeItem.Category.TECHNICAL,
        "priority": 97,
        "keywords": "liro little littlebot little bot robô educacional robo educacional robô para escola robo para escola educação inclusão creche escola infantil",
        "content": "O LIRO é um robô educacional interativo da Xyron Robotics, baseado em robótica social e inteligência artificial generativa. Foi desenvolvido para integrar tecnologia avançada à prática pedagógica com segurança, intencionalidade e alinhamento ao projeto educacional da escola. Ele atua como parceiro do professor e não substitui o docente. Apoia engajamento, participação, mediação de aula, contação de histórias, musicalização, prática de idiomas, quiz e atividades gamificadas. Considera contexto educacional brasileiro com apoio à BNCC e princípios da LGPD em ambiente digital controlado. Especificações técnicas: 22,5 x 22 x 16,5 cm; 1,68 kg; Wi-Fi; bateria 5.000 mAh; carregamento DC 5V / 1.2A; autonomia de 6 horas; carregamento completo de 5 horas; Micro USB; tela LCD de 5 polegadas.",
    },
    {
        "title": "Xyron LIRO - Inclusão, APAEs e clínicas multidisciplinares",
        "slug": "xyron-liro-apae-clinicas",
        "category": LiviaKnowledgeItem.Category.TECHNICAL,
        "priority": 96,
        "keywords": "liro apae liro clínica liro clinica neurodivergente neurodivergência tea autismo tdah deficiência intelectual sindrome de down inclusão terapia fonoaudiologia terapeuta ocupacional psicopedagogia comunicação habilidades sociais desenvolvimento cognitivo desenvolvimento socioemocional clínica multidisciplinar atendimento especializado",
        "content": "O LIRO pode ser utilizado como ferramenta complementar de desenvolvimento cognitivo, social, emocional e comunicacional para pessoas neurodivergentes em APAEs, clínicas multidisciplinares e instituições de atendimento especializado. Não substitui psicólogos, fonoaudiólogos, terapeutas ocupacionais, psicopedagogos, professores ou equipe multidisciplinar; ele potencializa o trabalho técnico, ampliando engajamento e interação. Pode apoiar TEA, TDAH, deficiência intelectual, síndrome de Down e múltiplas deficiências em sessões estruturadas com acolhimento, atividade principal, atividade interativa e encerramento.",
    },
    {
        "title": "Xyron LIRO - Planos de aula e uso pedagógico",
        "slug": "xyron-liro-planos-aula-pedagogico",
        "category": LiviaKnowledgeItem.Category.TECHNICAL,
        "priority": 95,
        "keywords": "plano de aula liro liro plano de aula liro pedagogico treinamento liro bncc gamificação aula com robô aula com robo educação infantil fundamental ensino médio enem vestibular quiz batalha do conhecimento caça ao tesouro ranking de participação cultura digital competências bncc sala de aula professor",
        "content": "O LIRO pode ser aplicado em educação infantil, ensino fundamental e ensino médio para potencializar aprendizagem, engajamento e inovação pedagógica, sempre conectado ao planejamento do professor e às competências da BNCC. Exemplos incluem contação de histórias, músicas educativas, reconhecimento de cores e sentimentos na educação infantil, desafios matemáticos e leitura guiada no fundamental, além de revisões para ENEM e vestibular no ensino médio. O uso recomendado é como ferramenta de apoio pedagógico, mantendo o professor protagonista.",
    },
    {
        "title": "Xyron OrbitBot - Robô de segurança autônoma",
        "slug": "xyron-orbit-patrol-bot",
        "category": LiviaKnowledgeItem.Category.TECHNICAL,
        "priority": 96,
        "keywords": "orbit orbitbot orbit bot patrol patrol bot robô de segurança robo de segurança segurança autônoma patrulhamento ronda vigilância vigilância autônoma monitoramento câmera térmica camera termica navegação a laser patrulha 24/7 shopping galpão condomínio aeroporto hospital universidade estacionamento",
        "content": "O OrbitBot é um robô de segurança autônomo da Xyron Robotics com navegação a laser, patrulhamento inteligente e vigilância contínua para ambientes mapeados. É indicado para reduzir dependência de vigilância humana, ampliar cobertura e padronizar rotinas de patrulha. Possui rotas inteligentes, patrulha 24/7, retorno automático à base, câmera visível e imagem térmica. Especificações técnicas: 70 x 65 x 67 cm; tela 5,5 polegadas; peso 24 kg; bateria 12.800 mAh; autonomia de 10 horas; carregamento completo de 8 horas; velocidade até 1,8 km/h em navegação e até 3,2 km/h manual; imagem térmica com faixa de -5°C a 150°C; área máxima por mapa de 40.000 m².",
    },
    {
        "title": "Xyron NeoBot - Recepção e atendimento inteligente",
        "slug": "xyron-neo-bot",
        "category": LiviaKnowledgeItem.Category.TECHNICAL,
        "priority": 98,
        "keywords": "neo neobot neo bot robô de recepção robo de recepção robô recepcionista robo recepcionista recepcionista robô atendimento inteligente atendimento com ia recepção corporativa eventos visitantes varejo shopping aeroporto feira stand reconhecimento facial atendimento multilíngue chatbot físico",
        "content": "O NeoBot é um robô recepcionista inteligente da Xyron Robotics para ambientes de alto fluxo que precisam de inovação, impacto visual, automação e personalização. Combina IA integrada (como ChatGPT/DeepSeek), reconhecimento facial, navegação autônoma, comunicação multilíngue, gestão de conteúdo e apresentações interativas. Pode responder perguntas em tempo real, explicar produtos e serviços, executar roteiros comerciais e permitir chamada de vídeo unidirecional para suporte remoto. Suporta comunicação em mais de 20 idiomas. Especificações: 45 x 100 x 40 cm; tela HD 10,1 polegadas; 18 kg; bateria 20.000 mAh; autonomia 10 horas; carregamento completo aproximado de 9 horas; retorno automático à base suportado.",
    },
    {
        "title": "WaiterBot",
        "slug": "xyron-waiterbot",
        "category": LiviaKnowledgeItem.Category.TECHNICAL,
        "priority": 90,
        "keywords": "waiterbot waiter bot waiter robô garçom robo garçom entrega restaurante hotel supermercado bandeja food service",
        "content": "O WaiterBot é um robô de entrega e apoio operacional para restaurantes, hotéis, supermercados e ambientes de atendimento. Ele executa entregas em pontos definidos, retorna bandejas, navega de forma autônoma, desvia de obstáculos e retorna automaticamente à base de carregamento.",
    },
    {
        "title": "CareBot",
        "slug": "xyron-carebot",
        "category": LiviaKnowledgeItem.Category.TECHNICAL,
        "priority": 89,
        "keywords": "carebot care bot robô saúde robo saúde idosos telemedicina hospital farmácia monitoramento de saúde assistência",
        "content": "O CareBot é um robô assistivo para saúde, cuidado residencial, clínicas, hospitais, farmácias e acompanhamento de idosos. Apoia chamadas rápidas, monitoramento de indicadores fisiológicos, teleatendimento, relatórios de saúde, alertas e análise baseada em IA. Ficha técnica: dimensões 198 x 270 x 420 mm; tela de 9 polegadas com 1024 x 600 pixels; materiais ABS + PC; câmera 1920 x 1080; bateria 16.8 V / 2500 mAh; entrada 100–240 V; carregador 16.8 V / 1.5 A; rotação de cabeça de -70° a +70°; proteção IP20. Aplicações: residências, hospitais, farmácias, asilos, clínicas de reabilitação, cuidados assistivos e telemedicina.",
    },
    {
        "title": "Xyron HygiBot - Robô de limpeza autônoma",
        "slug": "xyron-hygibot-dune-bot",
        "category": LiviaKnowledgeItem.Category.TECHNICAL,
        "priority": 97,
        "keywords": "hygibot hygi bot dune dune bot duno duno bot dunobot robô de limpeza robo de limpeza limpeza autônoma limpeza shopping limpeza hospital limpeza supermercado",
        "content": "O HygiBot é um robô de limpeza inteligente da Xyron Robotics para operação em grandes áreas com eficiência, escala e continuidade. Também pode ser citado como Dune/Duno Bot em algumas conversas. Ele varre, aspira e passa pano de forma automatizada, com sensores, mapeamento a laser, programação de áreas e horários, controle por aplicativo e monitoramento em tempo real. Especificações: 50 x 60 x 58 cm; 53,8 kg; bateria 46.000 mAh; carregamento em 2 horas e meia; autonomia de 4 horas. Aplicações: shoppings, indústrias, hospitais, ginásios, hotéis, academias, supermercados e grandes áreas internas.",
    },
    {
        "title": "HostBot",
        "slug": "xyron-hostbot",
        "category": LiviaKnowledgeItem.Category.TECHNICAL,
        "priority": 87,
        "keywords": "hostbot host bot robô host robo host eventos museu galeria recepção concessionária banco",
        "content": "O HostBot é um robô host para recepção, eventos, empresas, comércios, museus, galerias, concessionárias e bancos. Possui interação em duas telas, altura semelhante à humana, desvio automático de obstáculos e conversas com inteligência artificial. Ficha técnica: tamanho 49 x 140 x 48 cm; peso 23 kg; tela principal 10,1 polegadas; extra tablet 19 polegadas; bateria 20.000 mAh; carregamento 8 horas; autonomia 10 horas. Aplicações: eventos, empresas, comércios, museus e galerias, concessionárias, bancos, recepção e feiras.",
    },
    {
        "title": "Buddy Bot",
        "slug": "xyron-buddy-bot",
        "category": LiviaKnowledgeItem.Category.TECHNICAL,
        "priority": 86,
        "keywords": "buddy budy buddy bot budy bot cão robô cao robo cachorro robô cachorro robo robô cachorro robo cachorro robô quadrúpede robo quadrupede quadrúpede quadrupede inspeção segurança patrimonial resgate obras usinas subestação",
        "content": "O Buddy Bot é um robô quadrúpede da linha Xyron, indicado para inspeção, segurança patrimonial, resgate, engenharia, obras, indústrias e áreas de difícil acesso. Por não depender de rodas, pode atuar em terrenos irregulares, patrulhar áreas externas e apoiar inspeções em ambientes hostis. No catálogo, possui tamanho de 61 x 37 x 40 cm, peso de 12 kg, autonomia de 2 horas, carregamento em 1 hora, câmera 1920 x 1080 e inclinação máxima de 40°. Para disponibilidade e pronta entrega, a Smart Control Brasil precisa confirmar estoque/configuração com a equipe comercial.",
    },
    {
        "title": "MowerBot",
        "slug": "xyron-mowerbot",
        "category": LiviaKnowledgeItem.Category.TECHNICAL,
        "priority": 85,
        "keywords": "mowerbot mower bot robô cortador de grama cortador de grama remoto terreno irregular talude praça campo esportivo área verde",
        "content": "O MowerBot é um robô cortador de grama por controle remoto para terrenos irregulares, taludes, áreas verdes, campos esportivos, praças e grandes áreas externas, aumentando segurança e produtividade no corte. Ficha técnica: tamanho 90 x 93 x 92 cm; peso 140 kg; área de corte 1500 m²/h; velocidade 4 km/h; corte 500 mm; altura de corte de 20 mm a 150 mm; inclinação 45°; combustível gasolina; autonomia aproximada 1 L/h. Aplicações: campos esportivos, praças públicas, canteiros, pistas de grama, terrenos baldios, campo de golfe, áreas verdes e taludes.",
    },
    {
        "title": "Mitsubishi Electric Automação Industrial - visão geral",
        "slug": "mitsubishi-electric-automacao-industrial",
        "category": LiviaKnowledgeItem.Category.TECHNICAL,
        "priority": 94,
        "keywords": "mitsubishi mitsubishi electric automação mitsubishi automação industrial smart control mitsubishi integrador mitsubishi",
        "content": "A Mitsubishi Electric atua em automação industrial com soluções para controle, acionamento, movimento, robótica, supervisão, medição de energia e integração. A Smart Control Brasil trabalha com aplicações envolvendo CLPs, IHMs, inversores de frequência, servos, motion control, robôs industriais, redes industriais, retrofit, diagnóstico técnico e integração de sistemas.",
    },
    {
        "title": "Mitsubishi Motors x Mitsubishi Electric",
        "slug": "mitsubishi-motors-vs-mitsubishi-electric",
        "category": LiviaKnowledgeItem.Category.FAQ,
        "priority": 97,
        "keywords": "mitsubishi motors carro carros veículo veiculo automação industrial mitsubishi electric",
        "content": "A Smart Control Brasil atende Mitsubishi Electric na área de automação industrial. Não fazemos atendimento comercial para Mitsubishi Motors ou venda de veículos. Quando o cliente perguntar sobre carros, a orientação é esclarecer esse escopo e conduzir para soluções industriais.",
    },
    {
        "title": "CLPs Mitsubishi / MELSEC",
        "slug": "mitsubishi-clp-melsec",
        "category": LiviaKnowledgeItem.Category.TECHNICAL,
        "priority": 93,
        "keywords": "clp mitsubishi melsec plc mitsubishi iq-r iq-f fx5u controlador lógico programável automação de máquina",
        "content": "Os CLPs Mitsubishi da linha MELSEC são aplicados no controle de máquinas, processos industriais, painéis automatizados, retrofit, intertravamentos, sequenciamento, aquisição de sinais e integração com IHMs, inversores, servos, redes industriais e supervisórios.",
    },
    {
        "title": "IHMs Mitsubishi",
        "slug": "mitsubishi-ihm",
        "category": LiviaKnowledgeItem.Category.TECHNICAL,
        "priority": 92,
        "keywords": "ihm mitsubishi hmi mitsubishi interface homem máquina got got2000 tela mitsubishi",
        "content": "As IHMs Mitsubishi são usadas para operação, supervisão local, telas de comando, alarmes, receitas, parâmetros e interação entre operador e máquina. Em projetos industriais, podem ser integradas a CLPs, inversores, servos e sistemas de supervisão.",
    },
    {
        "title": "Inversores Mitsubishi",
        "slug": "mitsubishi-inversores-frequencia",
        "category": LiviaKnowledgeItem.Category.TECHNICAL,
        "priority": 91,
        "keywords": "inversor mitsubishi inversor de frequência fr-f fr-a fr-e controle de motor economia de energia acionamento",
        "content": "Os inversores de frequência Mitsubishi são usados para controle de motores elétricos, economia de energia, controle de velocidade, bombas, ventiladores, esteiras, máquinas e sistemas industriais. Também são comuns em retrofits e melhorias de confiabilidade.",
    },
    {
        "title": "Servos e Motion Control Mitsubishi / MELSERVO",
        "slug": "mitsubishi-servo-motion-melservo",
        "category": LiviaKnowledgeItem.Category.TECHNICAL,
        "priority": 90,
        "keywords": "servo mitsubishi melservo motion control controle de movimento posicionamento servo motor servo drive",
        "content": "Os servos MELSERVO e soluções de motion control Mitsubishi são aplicados em máquinas que exigem precisão, sincronismo, posicionamento, controle de movimento, velocidade e repetibilidade. São comuns em máquinas especiais, embalagem, pick and place, eixos controlados e automação de alta performance.",
    },
    {
        "title": "Robôs Industriais Mitsubishi MELFA",
        "slug": "mitsubishi-robos-industriais-melfa",
        "category": LiviaKnowledgeItem.Category.TECHNICAL,
        "priority": 89,
        "keywords": "melfa robô industrial mitsubishi robo industrial scara robô vertical pick and place encaixotamento célula robotizada",
        "content": "Os robôs industriais Mitsubishi MELFA incluem soluções SCARA e robôs verticais para aplicações como pick and place, encaixotamento, montagem, movimentação, manipulação e automação de linhas. A linha pode ser integrada com CLPs, IHMs, SCADA, servos, inversores e medição de energia.",
    },
    {
        "title": "SCADA, supervisão e dados industriais",
        "slug": "mitsubishi-scada-supervisao-dados",
        "category": LiviaKnowledgeItem.Category.TECHNICAL,
        "priority": 88,
        "keywords": "scada supervisório dashboard industrial dados industriais monitoramento alarmes indicadores kpi manutenção",
        "content": "Sistemas supervisórios e dashboards industriais permitem acompanhar dados de máquinas, alarmes, produção, falhas, disponibilidade, consumo de energia e indicadores de manutenção. A Smart Control Brasil pode apoiar integração de dados industriais com automação, software e dashboards web.",
    },
    {
        "title": "Medição e gestão de energia",
        "slug": "mitsubishi-medicao-gestao-energia",
        "category": LiviaKnowledgeItem.Category.TECHNICAL,
        "priority": 87,
        "keywords": "medição de energia gerenciamento de energia multimedidor eficiência energética consumo de energia energia industrial",
        "content": "Medição de energia em ambiente industrial permite acompanhar consumo, identificar desperdícios, apoiar eficiência energética e gerar dados para tomada de decisão. Pode ser integrada a automação, dashboards e sistemas de manutenção.",
    },
    {
        "title": "Retrofit e manutenção em automação industrial",
        "slug": "mitsubishi-retrofit-manutencao-automacao",
        "category": LiviaKnowledgeItem.Category.PROCESS,
        "priority": 86,
        "keywords": "retrofit manutenção automação manutenção industrial painel automatizado diagnóstico falha confiabilidade disponibilidade tpm rcm",
        "content": "A Smart Control Brasil apoia diagnóstico, retrofit e modernização de máquinas e painéis automatizados, atuando em CLPs, IHMs, inversores, servos, sensores, redes industriais, software e documentação técnica. O objetivo é aumentar confiabilidade, disponibilidade e segurança operacional.",
    },
]


class Command(BaseCommand):
    help = "Seed initial knowledge items for Lívia Assistant."

    def handle(self, *args, **options):
        created_count = 0
        updated_count = 0
        for item in KNOWLEDGE_ITEMS:
            _, created = LiviaKnowledgeItem.objects.update_or_create(
                slug=item["slug"],
                defaults={
                    "title": item["title"],
                    "category": item["category"],
                    "content": item["content"],
                    "keywords": item["keywords"],
                    "priority": item["priority"],
                    "is_active": True,
                },
            )
            if created:
                created_count += 1
            else:
                updated_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Lívia knowledge seed completed: {created_count} created, {updated_count} updated."
            )
        )
