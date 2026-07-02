from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from .xyron_robots import XYRON_ROBOTS

class StaticViewSitemap(Sitemap):
    priority = 0.8
    changefreq = 'weekly'

    def items(self):
        return [
            'institutional:home',
            'institutional:about',
            'institutional:services',
            'institutional:service_details',
            'institutional:service_marketing_digital',
            'institutional:service_automacao_industrial_clps',
            'institutional:service_inteligencia_artificial',
            'institutional:service_sistemas_web_aplicativos',
            'institutional:service_robotica_integracao',
            'institutional:service_manutencao_tpm_confiabilidade',
            'institutional:engenharia_embarcada',
            'institutional:refrigeracao',
            'institutional:service_diagnostico_ia_dados_automacao',
            'institutional:xyron_robotics',
            *[("institutional:xyron_robot_detail", robot["slug"]) for robot in XYRON_ROBOTS],
            'institutional:blog',
            'institutional:contact',
            'institutional:team',
            'institutional:projects',
            'institutional:supervisao_dados_industriais',
            'institutional:diagnostico_industrial_engenharia_solucao',
            'institutional:automacao_industrial_clps_ihms',
            'institutional:manutencao_retrofit_confiabilidade',
            'institutional:inversores_eficiencia_energetica',
            'institutional:servoacionamentos_motion_control',
            'institutional:supervisorio_scada_dados_industriais',
            'institutional:robotica_celulas_automatizadas',
            'institutional:gerenciamento_energia_utilidades',
            'institutional:paineis_eletricos_baixa_tensao',
            'institutional:integracao_chao_fabrica_dados_industriais',
            'institutional:seguranca_maquinas_continuidade_operacional',
            'institutional:tecnologia_embarcada_solucoes_customizadas',
            'institutional:faq',
        ]

    def location(self, item):
        if isinstance(item, tuple):
            route_name, slug = item
            return reverse(route_name, args=[slug])
        return reverse(item)
