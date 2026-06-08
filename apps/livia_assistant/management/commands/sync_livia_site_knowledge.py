import re

from django.core.management.base import BaseCommand
from django.test import Client
from django.urls import NoReverseMatch, reverse
from django.utils.html import strip_tags

from apps.livia_assistant.models import LiviaKnowledgeItem


PAGE_SPECS = [
    {
        "slug": "site-smart-control-home",
        "title": "Site Smart Control Brasil - Página inicial",
        "category": LiviaKnowledgeItem.Category.COMPANY,
        "priority": 45,
        "keywords": "smart control brasil automação robótica tecnologia soluções digitais engenharia",
        "route_candidates": ["institutional:home"],
    },
    {
        "slug": "site-smart-control-about",
        "title": "Site Smart Control Brasil - Sobre",
        "category": LiviaKnowledgeItem.Category.COMPANY,
        "priority": 45,
        "keywords": "sobre smart control brasil engenharia tecnologia automação soluções",
        "route_candidates": ["institutional:about", "institutional:about_alias"],
    },
    {
        "slug": "site-smart-control-contact",
        "title": "Site Smart Control Brasil - Contato",
        "category": LiviaKnowledgeItem.Category.COMPANY,
        "priority": 45,
        "keywords": "contato engenharia orçamento falar com especialista smart control brasil",
        "route_candidates": ["institutional:contact", "institutional:contact_alias"],
    },
    {
        "slug": "site-smart-control-mitsubishi",
        "title": "Site Smart Control Brasil - Mitsubishi Electric",
        "category": LiviaKnowledgeItem.Category.TECHNICAL,
        "priority": 60,
        "keywords": "mitsubishi mitsubishi electric automação industrial clp ihm inversor servo melservo melsec melfa robô industrial",
        "route_candidates": ["institutional:mitsubishi", "institutional:representada_mitsubishi_automacao"],
    },
    {
        "slug": "site-smart-control-xyron-robotics",
        "title": "Site Smart Control Brasil - Xyron Robotics",
        "category": LiviaKnowledgeItem.Category.TECHNICAL,
        "priority": 60,
        "keywords": "xyron xyron robotics robótica xyron liro neobot hygibot orbitbot buddy robôs xyron robô educacional robô de limpeza robô de segurança robô de recepção",
        "route_candidates": ["institutional:xyron-robotics", "institutional:parceiro_xyron_robotics"],
    },
]


class Command(BaseCommand):
    help = "Sincroniza conhecimento da Lívia com páginas públicas do site institucional."

    def handle(self, *args, **options):
        client = Client()
        created_count = 0
        updated_count = 0
        synced_titles = []

        for spec in PAGE_SPECS:
            path, route_name = self._resolve_route(spec["route_candidates"])
            if not path:
                self.stdout.write(
                    self.style.WARNING(
                        f"[skip] rota indisponível para '{spec['title']}' ({', '.join(spec['route_candidates'])})"
                    )
                )
                continue

            response = client.get(path)
            if response.status_code != 200:
                self.stdout.write(
                    self.style.WARNING(
                        f"[skip] rota {route_name} retornou status {response.status_code} para '{spec['title']}'"
                    )
                )
                continue

            html = response.content.decode("utf-8", errors="ignore")
            cleaned_content = self._extract_main_text(html)
            if len(cleaned_content) < 120:
                self.stdout.write(
                    self.style.WARNING(f"[skip] conteúdo muito curto em {route_name} para '{spec['title']}'")
                )
                continue

            _, created = LiviaKnowledgeItem.objects.update_or_create(
                slug=spec["slug"],
                defaults={
                    "title": spec["title"],
                    "category": spec["category"],
                    "content": cleaned_content,
                    "keywords": spec["keywords"],
                    "priority": spec["priority"],
                    "is_active": True,
                },
            )
            if created:
                created_count += 1
            else:
                updated_count += 1
            synced_titles.append(spec["title"])

        self.stdout.write(
            self.style.SUCCESS(
                f"sync_livia_site_knowledge completed: {created_count} created, {updated_count} updated."
            )
        )
        if synced_titles:
            self.stdout.write("Synchronized pages:")
            for title in synced_titles:
                self.stdout.write(f"- {title}")

    def _resolve_route(self, candidates):
        for route_name in candidates:
            try:
                return reverse(route_name), route_name
            except NoReverseMatch:
                continue
        return "", ""

    def _extract_main_text(self, html):
        # Remove blocos ruidosos e repetitivos.
        html = re.sub(r"<!--.*?-->", " ", html, flags=re.DOTALL)
        html = re.sub(r"<script\b[^>]*>.*?</script>", " ", html, flags=re.IGNORECASE | re.DOTALL)
        html = re.sub(r"<style\b[^>]*>.*?</style>", " ", html, flags=re.IGNORECASE | re.DOTALL)
        html = re.sub(r"<noscript\b[^>]*>.*?</noscript>", " ", html, flags=re.IGNORECASE | re.DOTALL)
        html = re.sub(r"<(nav|header|footer)\b[^>]*>.*?</\1>", " ", html, flags=re.IGNORECASE | re.DOTALL)

        text = strip_tags(html)
        lines = [line.strip() for line in text.splitlines()]
        lines = [line for line in lines if len(line) >= 30]

        unique_lines = []
        seen = set()
        for line in lines:
            compact = re.sub(r"\s+", " ", line)
            key = compact.lower()
            if key in seen:
                continue
            seen.add(key)
            unique_lines.append(compact)

        content = "\n".join(unique_lines)
        content = re.sub(r"[ \t]+", " ", content)
        content = re.sub(r"\n{3,}", "\n\n", content).strip()
        return content[:8000]
