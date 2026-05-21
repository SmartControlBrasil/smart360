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
