from django.core.management.base import BaseCommand

from apps.technical_portal.models import ErrorCode, TechnicalArticle, TechnicalCategory


class Command(BaseCommand):
    help = "Seed inicial do Portal Técnico Smart360."

    def handle(self, *args, **options):
        categories_data = [
            ("Ar-condicionado", "ar-condicionado", "Códigos de erro, sintomas comuns e orientações iniciais.", "snowflake", 10),
            ("Lavadoras", "lavadoras", "Falhas frequentes, diagnóstico básico e possíveis causas.", "washing-machine", 20),
            ("Geladeiras", "geladeiras", "Defeitos comuns, refrigeração, sensores e partida.", "thermometer", 30),
            ("Obra civil", "obra-civil", "Dicas práticas, materiais, execução e produtividade em obra.", "hard-hat", 40),
            ("Elétrica básica", "eletrica-basica", "Segurança, medições e boas práticas.", "bolt", 50),
            ("Automação", "automacao", "CLPs, sensores, comandos e integração.", "cpu", 60),
        ]

        categories = {}
        created_categories = 0
        updated_categories = 0
        for name, slug, description, icon_name, order in categories_data:
            category, created = TechnicalCategory.objects.update_or_create(
                slug=slug,
                defaults={
                    "name": name,
                    "description": description,
                    "icon_name": icon_name,
                    "order": order,
                    "is_active": True,
                },
            )
            categories[slug] = category
            created_categories += int(created)
            updated_categories += int(not created)

        article_data = [
            ("ar-condicionado", "Primeiros passos no diagnóstico de ar-condicionado", "primeiros-passos-diagnostico-ar-condicionado", "Checklist inicial para avaliar sintomas comuns antes de uma intervenção.", "Verifique alimentação elétrica, filtros, ventilação, limpeza da condensadora e sinais de falha no compressor antes de avançar para testes específicos.", "diagnostico, compressor, filtros"),
            ("lavadoras", "Diagnóstico inicial de lavadoras", "diagnostico-inicial-lavadoras", "Pontos básicos para observar falhas frequentes em lavadoras.", "Confirme alimentação, entrada e drenagem de água, travamento da tampa e ruídos anormais antes de desmontagens complexas.", "lavadora, drenagem, segurança"),
            ("geladeiras", "Verificações básicas em geladeiras", "verificacoes-basicas-geladeiras", "Orientações iniciais para avaliar refrigeração e partida.", "Observe vedação, temperatura, ventilação, partida do compressor e acúmulo de gelo antes de trocar componentes.", "geladeira, refrigeração, compressor"),
            ("obra-civil", "Organização de frente de serviço", "organizacao-frente-servico", "Boas práticas para manter produtividade e segurança na obra.", "Planeje materiais, ferramentas, sequência de execução e limpeza do local para reduzir retrabalho e riscos.", "obra, produtividade, materiais"),
            ("eletrica-basica", "Segurança antes de medições elétricas", "seguranca-antes-medicoes-eletricas", "Cuidados essenciais antes de medir tensão, continuidade ou corrente.", "Use EPIs, confirme a categoria do instrumento, inspecione pontas de prova e bloqueie fontes quando aplicável.", "eletrica, medicao, segurança"),
            ("automacao", "Introdução ao diagnóstico de sensores", "introducao-diagnostico-sensores", "Como iniciar a análise de sensores em sistemas automatizados.", "Verifique alimentação, sinal, aterramento, configuração do CLP e integridade do cabo antes de substituir sensores.", "automacao, clp, sensores"),
        ]

        created_articles = 0
        updated_articles = 0
        for category_slug, title, slug, summary, content, tags in article_data:
            _, created = TechnicalArticle.objects.update_or_create(
                slug=slug,
                defaults={
                    "category": categories[category_slug],
                    "title": title,
                    "summary": summary,
                    "content": content,
                    "tags": tags,
                    "difficulty": TechnicalArticle.Difficulty.BASIC,
                    "is_active": True,
                },
            )
            created_articles += int(created)
            updated_articles += int(not created)

        _, error_created = ErrorCode.objects.update_or_create(
            category=categories["ar-condicionado"],
            equipment_type="Ar-condicionado split",
            code="EXEMPLO-01",
            defaults={
                "brand": "",
                "model": "",
                "title": "Exemplo genérico de falha de comunicação",
                "probable_cause": "Exemplo didático: comunicação instável entre unidades, alimentação inadequada ou conexão mal encaixada.",
                "recommended_action": "Use apenas como exemplo. Consulte o manual oficial do fabricante antes de qualquer intervenção real.",
                "safety_warning": "Desenergize o equipamento e siga normas de segurança antes de inspeções.",
                "source_note": "Registro de demonstração, não representa código oficial de fabricante.",
                "is_active": True,
            },
        )

        self.stdout.write(
            self.style.SUCCESS(
                "Portal técnico seed concluído: "
                f"categorias {created_categories} criadas/{updated_categories} atualizadas; "
                f"artigos {created_articles} criados/{updated_articles} atualizados; "
                f"códigos de erro {int(error_created)} criados/{int(not error_created)} atualizados."
            )
        )
