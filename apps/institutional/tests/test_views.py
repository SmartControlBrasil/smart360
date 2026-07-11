from html.parser import HTMLParser
from pathlib import Path
import struct
from xml.etree import ElementTree

from django.conf import settings
from django.core import mail
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse

from apps.institutional.views import XYRON_ROBOT_PAGE_TEMPLATES
from apps.marketplace_ecom.models import TechnicalProduct
from apps.marketplace_ecom.services.catalog_seed import seed_technical_catalog_from_static
from apps.institutional.xyron_robots import XYRON_ROBOTS

XYRON_HTML_DETAIL_PAGE_SEO = {
    "liro-littlebot": {
        "seo_title": "LIRO / LittleBot | Robô Educacional Xyron | Smart Control Brasil",
        "meta_description": "Robô educacional Xyron para escolas, espaços maker e projetos pedagógicos",
    },
    "neobot": {
        "seo_title": "NeoBot | Robô de Recepção e Comunicação | Smart Control Brasil",
        "meta_description": "NeoBot Xyron para recepção, orientação de visitantes, eventos, showrooms",
    },
    "buddy": {
        "seo_title": "Buddy | Robô Social e Interativo Xyron | Smart Control Brasil",
        "meta_description": "Buddy Xyron para interação, demonstrações tecnológicas, educação, eventos",
    },
    "patrol-orbit": {
        "seo_title": "Patrol / Orbit | Robô de Segurança e Ronda | Smart Control Brasil",
        "meta_description": "Robô Xyron para apoio a rondas, inspeção, presença ostensiva e monitoramento assistido",
    },
    "hygibot": {
        "seo_title": "HygiBot | Robô de Limpeza e Higienização | Smart Control Brasil",
        "meta_description": "HygiBot Xyron: robô de limpeza inteligente para grandes áreas, com varrição, aspiração, lavagem, mapeamento a laser",
    },
    "hostbot": {
        "seo_title": "HostBot | Robô de Recepção e Hospitalidade | Smart Control Brasil",
        "meta_description": "HostBot Xyron para recepção, hospitalidade, orientação de visitantes",
    },
    "waiterbot": {
        "seo_title": "WaiterBot | Robô Garçom de Apoio Operacional | Smart Control Brasil",
        "meta_description": "WaiterBot Xyron para apoio ao atendimento de salão, transporte interno de itens",
    },
    "carebot": {
        "seo_title": "CareBot | Robô de Apoio Assistido | Smart Control Brasil",
        "meta_description": "CareBot Xyron para interação, orientação e apoio assistido em clínicas, hospitais",
    },
    "mowerbot": {
        "seo_title": "MowerBot | Robô Cortador de Grama Xyron | Smart Control Brasil",
        "meta_description": "MowerBot Xyron para corte de grama, manutenção de áreas externas, jardins",
    },
}



class ImageTagParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.images = []

    def handle_starttag(self, tag, attrs):
        if tag == "img":
            self.images.append(dict(attrs))


def rendered_images(response):
    parser = ImageTagParser()
    parser.feed(response.content.decode(response.charset or "utf-8"))
    return parser.images


class ScriptTagParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.scripts = []

    def handle_starttag(self, tag, attrs):
        if tag == "script":
            attrs = dict(attrs)
            src = attrs.get("src")
            if src:
                self.scripts.append(src)


def rendered_scripts(response):
    parser = ScriptTagParser()
    parser.feed(response.content.decode(response.charset or "utf-8"))
    return parser.scripts


class LinkTagParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []

    def handle_starttag(self, tag, attrs):
        if tag == "link":
            self.links.append(dict(attrs))


def rendered_links(response):
    parser = LinkTagParser()
    parser.feed(response.content.decode(response.charset or "utf-8"))
    return parser.links


def get_png_dimensions(image_path):
    with image_path.open("rb") as image_file:
        signature = image_file.read(8)
        if signature != b"\x89PNG\r\n\x1a\n":
            raise ValueError(f"Invalid PNG signature: {image_path}")
        chunk_length = struct.unpack(">I", image_file.read(4))[0]
        chunk_type = image_file.read(4)
        if chunk_type != b"IHDR" or chunk_length != 13:
            raise ValueError(f"Invalid PNG IHDR chunk: {image_path}")
        width, height = struct.unpack(">II", image_file.read(8))
        return width, height


def get_webp_dimensions(image_path):
    with image_path.open("rb") as image_file:
        data = image_file.read()

    if data[:4] != b"RIFF" or data[8:12] != b"WEBP":
        raise ValueError(f"Invalid WEBP file: {image_path}")

    offset = 12
    while offset + 8 <= len(data):
        chunk_type = data[offset:offset + 4]
        chunk_size = struct.unpack("<I", data[offset + 4:offset + 8])[0]
        chunk_data_start = offset + 8
        chunk_data_end = chunk_data_start + chunk_size
        chunk_data = data[chunk_data_start:chunk_data_end]

        if chunk_type == b"VP8X" and len(chunk_data) >= 10:
            width = int.from_bytes(chunk_data[4:7], "little") + 1
            height = int.from_bytes(chunk_data[7:10], "little") + 1
            return width, height

        if chunk_type == b"VP8 " and len(chunk_data) >= 10:
            if chunk_data[3:6] == b"\x9d\x01\x2a":
                width = struct.unpack("<H", chunk_data[6:8])[0] & 0x3FFF
                height = struct.unpack("<H", chunk_data[8:10])[0] & 0x3FFF
                return width, height

        if chunk_type == b"VP8L" and len(chunk_data) >= 5:
            if chunk_data[0] == 0x2F:
                bits = int.from_bytes(chunk_data[1:5], "little")
                width = (bits & 0x3FFF) + 1
                height = ((bits >> 14) & 0x3FFF) + 1
                return width, height

        offset = chunk_data_end + (chunk_size % 2)

    raise ValueError(f"Could not read WEBP dimensions: {image_path}")

TEST_MIDDLEWARE = [
    mw
    for mw in settings.MIDDLEWARE
    if mw != "shared_kernel.observability.middleware.CorrelationIdMiddleware"
]


@override_settings(MIDDLEWARE=TEST_MIDDLEWARE)
class InstitutionalRoutesTests(SimpleTestCase):
    # Middleware de observabilidade grava traces no banco durante requests ao client.
    databases = {"default"}

    def assert_script_once(self, scripts, needle):
        matches = [src for src in scripts if needle in src]
        self.assertEqual(len(matches), 1, f"Expected exactly one script matching {needle!r}; found {matches}")

    def assert_script_absent(self, scripts, needle):
        matches = [src for src in scripts if needle in src]
        self.assertEqual(matches, [], f"Expected no script matching {needle!r}; found {matches}")

    def assert_scripts_unique(self, scripts):
        duplicates = sorted({src for src in scripts if scripts.count(src) > 1})
        self.assertEqual(duplicates, [])

    def assert_script_order(self, scripts, first, second):
        first_index = next(i for i, src in enumerate(scripts) if first in src)
        second_index = next(i for i, src in enumerate(scripts) if second in src)
        self.assertLess(first_index, second_index)

    def test_global_javascript_plugins_replace_bundle(self):
        response = self.client.get(reverse("institutional:about"))

        self.assertEqual(response.status_code, 200)
        scripts = rendered_scripts(response)

        self.assert_script_absent(scripts, "plugins.bundle.min.js")
        for script in [
            "plugins/jquery-3-7-1.min.js",
            "plugins/bootstrap.min.js",
            "plugins/aos.js",
            "plugins/mobilemenu.js",
            "plugins/sidebar.js",
            "plugins/gsap.min.js",
            "plugins/ScrollTrigger.min.js",
            "plugins/Splitetext.js",
            "main.min.js",
        ]:
            self.assert_script_once(scripts, script)

        self.assert_script_order(scripts, "plugins/jquery-3-7-1.min.js", "plugins/bootstrap.min.js")
        self.assert_script_order(scripts, "plugins/jquery-3-7-1.min.js", "plugins/aos.js")
        self.assert_script_order(scripts, "plugins/bootstrap.min.js", "main.min.js")
        self.assert_script_order(scripts, "plugins/Splitetext.js", "main.min.js")
        self.assert_scripts_unique(scripts)

    def test_home_loads_carousel_gallery_and_counter_plugins_before_main(self):
        response = self.client.get(reverse("institutional:home"))

        self.assertEqual(response.status_code, 200)
        scripts = rendered_scripts(response)

        for script in [
            "plugins/waypoints.js",
            "plugins/counter.js",
            "plugins/circle-progress.js",
            "plugins/owlcarousel.min.js",
            "plugins/slick-slider.js",
        ]:
            self.assert_script_once(scripts, script)
            self.assert_script_order(scripts, script, "main.min.js")
        self.assert_script_absent(scripts, "plugins.bundle.min.js")
        self.assert_scripts_unique(scripts)

    def test_contact_loads_nice_select_before_main(self):
        response = self.client.get(reverse("institutional:contact"))

        self.assertEqual(response.status_code, 200)
        scripts = rendered_scripts(response)

        self.assert_script_once(scripts, "plugins/nice-select.js")
        self.assert_script_order(scripts, "plugins/nice-select.js", "main.min.js")
        self.assert_scripts_unique(scripts)

    def test_blog_details_loads_magnific_popup_before_main(self):
        response = self.client.get(reverse("institutional:blog_details"))

        self.assertEqual(response.status_code, 200)
        scripts = rendered_scripts(response)

        self.assert_script_once(scripts, "plugins/magnific-popup.js")
        self.assert_script_order(scripts, "plugins/magnific-popup.js", "main.min.js")
        self.assert_scripts_unique(scripts)

    def test_common_page_does_not_load_page_specific_plugins(self):
        response = self.client.get(reverse("institutional:about"))

        self.assertEqual(response.status_code, 200)
        scripts = rendered_scripts(response)

        for script in [
            "plugins/owlcarousel.min.js",
            "plugins/slick-slider.js",
            "plugins/nice-select.js",
            "plugins/magnific-popup.js",
        ]:
            self.assert_script_absent(scripts, script)
        self.assert_scripts_unique(scripts)

    def test_service_slider_pages_load_only_owl_before_main(self):
        for route_name in [
            "institutional:service_sistemas_web_aplicativos",
            "institutional:service_inteligencia_artificial",
        ]:
            with self.subTest(route_name=route_name):
                response = self.client.get(reverse(route_name))

                self.assertEqual(response.status_code, 200)
                scripts = rendered_scripts(response)

                self.assert_script_once(scripts, "plugins/owlcarousel.min.js")
                self.assert_script_order(scripts, "plugins/owlcarousel.min.js", "main.min.js")
                self.assert_script_absent(scripts, "plugins/slick-slider.js")
                self.assert_script_absent(scripts, "plugins/nice-select.js")
                self.assert_script_absent(scripts, "plugins/magnific-popup.js")
                self.assert_scripts_unique(scripts)
    def test_public_pages_render(self):
        route_names = [
            "institutional:home",
            "institutional:about",
            "institutional:services",
            "institutional:blog",
            "institutional:contact",
            "institutional:engenharia_embarcada",
            "institutional:representada_mitsubishi_automacao",
            "institutional:service_manutencao_tpm_confiabilidade",
            "institutional:service_automacao_industrial_clps",
            "institutional:service_robotica_integracao",
            "institutional:parceiro_xyron_robotics",
            "institutional:xyron_robotics",
            "institutional:xyron_liro_littlebot",
            "institutional:seguranca_da_informacao",
            "institutional:sites_sistemas_marketing",
        ]

        for route_name in route_names:
            with self.subTest(route_name=route_name):
                response = self.client.get(reverse(route_name))
                self.assertEqual(response.status_code, 200)

    def test_home_uses_index_template_and_institutional_content(self):
        response = self.client.get(reverse("institutional:home"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "institutional/eitech/pages/index.html")
        self.assertContains(response, "Smart Control Brasil")
        self.assertNotContains(response, "em construção", status_code=200)
        self.assertNotContains(response, "coming soon", status_code=200)

    def test_home_rendered_images_have_width_and_height(self):
        response = self.client.get(reverse("institutional:home"))

        self.assertEqual(response.status_code, 200)
        images = rendered_images(response)
        missing_width = [image.get("src", "") for image in images if not image.get("width")]
        missing_height = [image.get("src", "") for image in images if not image.get("height")]

        self.assertEqual(missing_width, [])
        self.assertEqual(missing_height, [])

    def test_header_and_footer_logos_have_dimensions(self):
        response = self.client.get(reverse("institutional:home"))

        images = rendered_images(response)
        header_logo = next(
            image for image in images if "logo-cores-03.webp" in image.get("src", "")
        )
        footer_logo = next(
            image for image in images if "logo-cores-04.webp" in image.get("src", "")
        )

        self.assertEqual(header_logo["width"], "192")
        self.assertEqual(header_logo["height"], "80")
        self.assertNotIn("loading", header_logo)
        self.assertEqual(footer_logo["width"], "192")
        self.assertEqual(footer_logo["height"], "80")

    def test_priority_hero_images_do_not_use_lazy_loading(self):
        response = self.client.get(reverse("institutional:home"))

        images = rendered_images(response)
        hero_visual = next(
            image for image in images if "all-images/hero/image214.webp" in image.get("src", "")
        )
        hero_priority_element = next(
            image for image in images if image.get("fetchpriority") == "high"
        )

        self.assertEqual(hero_visual["width"], "381")
        self.assertEqual(hero_visual["height"], "571")
        self.assertNotIn("loading", hero_visual)
        self.assertNotIn("loading", hero_priority_element)

    def test_home_lcp_contract_and_hero_background_assets(self):
        home_response = self.client.get(reverse("institutional:home"))
        about_response = self.client.get(reverse("institutional:about"))

        self.assertEqual(home_response.status_code, 200)
        self.assertEqual(about_response.status_code, 200)

        home_html = home_response.content.decode(home_response.charset or "utf-8")
        self.assertIn("hero-bg1.webp", home_html)
        self.assertNotIn(
            'hero1-section-area" style="background-image: url(/static/institutional/eitech/img/all-images/bg/hero-bg1.png)',
            home_html,
        )

        images = rendered_images(home_response)
        elements4 = next(
            image for image in images if "institutional/eitech/img/elements/elements4.png" in image.get("src", "")
        )
        hero_visual = next(
            image for image in images if "institutional/eitech/img/all-images/hero/image214.webp" in image.get("src", "")
        )

        self.assertNotEqual(elements4.get("fetchpriority"), "high")
        self.assertEqual(hero_visual.get("fetchpriority"), "high")
        self.assertEqual(hero_visual.get("decoding"), "async")
        self.assertNotEqual(hero_visual.get("loading"), "lazy")

        home_links = rendered_links(home_response)
        about_links = rendered_links(about_response)
        hero_preload_links = [
            link
            for link in home_links
            if link.get("rel") == "preload"
            and "institutional/eitech/img/all-images/hero/image214.webp" in link.get("href", "")
        ]
        hero_preload_links_other_page = [
            link
            for link in about_links
            if link.get("rel") == "preload"
            and "institutional/eitech/img/all-images/hero/image214.webp" in link.get("href", "")
        ]
        self.assertEqual(len(hero_preload_links), 1)
        self.assertEqual(hero_preload_links_other_page, [])

        static_root = Path(settings.BASE_DIR) / "static"
        hero_png_path = static_root / "institutional/eitech/img/all-images/bg/hero-bg1.png"
        hero_webp_path = static_root / "institutional/eitech/img/all-images/bg/hero-bg1.webp"

        self.assertTrue(hero_png_path.exists())
        self.assertTrue(hero_webp_path.exists())
        self.assertEqual(get_webp_dimensions(hero_webp_path), (1440, 730))
        self.assertEqual(get_png_dimensions(hero_png_path), (1440, 730))

    def test_xyron_robotics_page_uses_partner_template(self):
        response = self.client.get(reverse("institutional:parceiro_xyron_robotics"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response, "institutional/eitech/pages/xyron-robotics.html"
        )
        self.assertContains(response, "institutional/eitech/css/scb-xyron.css")
        self.assertContains(response, "Xyron Robotics no Brasil | Robôs para Educação, Segurança, Limpeza e Atendimento")
        self.assertContains(response, "Conheça a linha Xyron Robotics com a Smart Control Brasil: robôs para educação, recepção, segurança, limpeza, atendimento, cuidado assistido e áreas externas.")
        self.assertContains(response, "CollectionPage")
        self.assertContains(response, 'class="xyron-page xyron-overview-page"')
        self.assertContains(response, 'xyron-dark-section')
        self.assertContains(response, 'xyron-robot-showcase')
        self.assertContains(response, 'xyron-robot-row')
        self.assertContains(response, "Linha Xyron Robotics")
        self.assertContains(response, "<h1", count=1)
        self.assertContains(response, "Saber mais")
        self.assertContains(response, "Como a Smart Control Brasil conduz projetos com robôs Xyron")
        self.assertNotContains(response, "Ficha técnica e recursos")
        self.assertNotContains(response, "Capacidade da bateria")
        self.assertNotContains(response, "Solução personalizada")

    def test_xyron_robotics_solutions_url_renders_vitrine(self):
        response = self.client.get(reverse("institutional:xyron_robotics"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "institutional/eitech/pages/xyron-robotics.html")
        self.assertContains(response, "Linha Xyron Robotics")

    def test_xyron_robotics_page_links_to_all_robot_details(self):
        response = self.client.get(reverse("institutional:parceiro_xyron_robotics"))

        self.assertEqual(response.status_code, 200)
        for robot in XYRON_ROBOTS:
            with self.subTest(robot=robot["slug"]):
                self.assertContains(
                    response,
                    reverse("institutional:xyron_robot_detail", args=[robot["slug"]]),
                )
        self.assertContains(response, "MowerBot")

    def test_all_xyron_robot_detail_pages_render(self):
        for robot in XYRON_ROBOTS:
            with self.subTest(robot=robot["slug"]):
                response = self.client.get(
                    reverse("institutional:xyron_robot_detail", args=[robot["slug"]])
                )

                expected_template = XYRON_ROBOT_PAGE_TEMPLATES[robot["slug"]]
                self.assertEqual(response.status_code, 200)
                self.assertTemplateUsed(response, expected_template)
                self.assertContains(response, robot["name"])
                html_page_seo = XYRON_HTML_DETAIL_PAGE_SEO[robot["slug"]]
                self.assertContains(response, html_page_seo["seo_title"])
                self.assertContains(response, html_page_seo["meta_description"])
                self.assertContains(response, f"<h1>{robot['name']}</h1>", html=True)
                self.assertContains(response, "<h1", count=1)
                self.assertContains(response, "Product")
                self.assertContains(response, "Xyron Robotics")
                self.assertContains(response, "Robôs Xyron")
                self.assertContains(response, "Ver mais robôs Xyron")
                self.assertContains(response, "Funções principais")
                self.assertContains(response, "Ficha técnica e recursos")
                self.assertContains(response, "Aplicações e benefícios")
                self.assertContains(response, "Cuidados comerciais")
                self.assertContains(response, "Perguntas frequentes")
                self.assertContains(response, "institutional/eitech/css/scb-xyron.css")
                self.assertContains(response, reverse("institutional:contact"))
                self.assertContains(response, reverse("institutional:xyron_robotics"))
                self.assertNotContains(response, "hero3-section-area")

    def test_xyron_robot_sidebar_excludes_current_robot(self):
        expected_count = len(XYRON_ROBOTS) - 1

        for robot in XYRON_ROBOTS:
            with self.subTest(robot=robot["slug"]):
                response = self.client.get(
                    reverse("institutional:xyron_robot_detail", args=[robot["slug"]])
                )

                sidebar_robots = response.context["sidebar_robots"]
                sidebar_slugs = [item["slug"] for item in sidebar_robots]
                self.assertEqual(len(sidebar_robots), expected_count)
                self.assertNotIn(robot["slug"], sidebar_slugs)
                self.assertContains(response, 'data-robot-slug="', count=expected_count)

    def test_xyron_robot_detail_sidebar_does_not_link_to_current_page(self):
        for robot in XYRON_ROBOTS:
            with self.subTest(robot=robot["slug"]):
                response = self.client.get(
                    reverse("institutional:xyron_robot_detail", args=[robot["slug"]])
                )

                current_url = reverse("institutional:xyron_robot_detail", args=[robot["slug"]])
                sidebar_slugs = [item["slug"] for item in response.context["sidebar_robots"]]
                related_slugs = [item["slug"] for item in response.context["related_robots"]]
                self.assertNotIn(robot["slug"], sidebar_slugs)
                self.assertNotIn(robot["slug"], related_slugs)
                self.assertNotContains(response, f'href="{current_url}"')

    def test_sitemap_includes_xyron_overview_and_robot_pages(self):
        response = self.client.get("/sitemap.xml")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse("institutional:xyron_robotics"))
        for robot in XYRON_ROBOTS:
            with self.subTest(robot=robot["slug"]):
                self.assertContains(
                    response,
                    reverse("institutional:xyron_robot_detail", args=[robot["slug"]]),
                )

    def test_clps_project_route_renders_without_template_error(self):
        response = self.client.get(reverse("institutional:automacao_industrial_clps_ihms"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response,
            "institutional/eitech/pages/projects/automacao-industrial-clps.html",
        )
        self.assertContains(
            response,
            "Automação Industrial com CLPs, IHMs e Integração de Máquinas",
        )
        self.assertContains(response, "Solicitar diagnóstico")

    @override_settings(LIVIA_ASSISTANT_ENABLED=True)
    def test_livia_enabled_disables_hostgator_bubblechat(self):
        response = self.client.get(reverse("institutional:home"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "whatsapp-floating-button")
        self.assertContains(response, "livia-chat-widget")
        self.assertNotContains(response, "agent-factory-chat.hostgator.io")

    @override_settings(LIVIA_ASSISTANT_ENABLED=False)
    def test_livia_disabled_keeps_hostgator_bubblechat_fallback(self):
        response = self.client.get(reverse("institutional:home"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "whatsapp-floating-button")
        self.assertNotContains(response, "livia-chat-widget")
        self.assertContains(response, "agent-factory-chat.hostgator.io")

    def test_sitemap_includes_week1_public_routes(self):
        response = self.client.get("/sitemap.xml")

        self.assertEqual(response.status_code, 200)
        expected_routes = [
            "institutional:representada_mitsubishi_automacao",
            "institutional:blog_page_2",
            "institutional:blog_robotica_escolas_empresas_cidades",
            "institutional:blog_dados_operacionais_empresa_inteligente",
            "institutional:projects_page_2",
            "institutional:projects_page_3",
            "institutional:automacao_industrial_clps_ihms",
        ]
        for route_name in expected_routes:
            with self.subTest(route_name=route_name):
                self.assertContains(response, reverse(route_name))

    def test_xyron_hygibot_enriched_catalog_content(self):
        response = self.client.get(
            reverse("institutional:xyron_robot_detail", args=["hygibot"])
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "institutional/eitech/pages/xyron/hygibot.html")
        self.assertContains(response, "Limpeza inteligente para grandes áreas")
        self.assertContains(response, "Por que o HygiBot é diferente")
        self.assertContains(response, "Antes e depois na operação")
        self.assertContains(response, "Como a Smart Control Brasil implanta")
        self.assertContains(response, "46.000 mAh")
        self.assertContains(response, "Mapeamento a laser")
        self.assertContains(response, "até 4 horas")
        self.assertContains(response, "Lavar, varrer, aspirar e passar pano seco")
        self.assertContains(response, "Quais funções de limpeza o HygiBot executa?")
        self.assertContains(response, "Product")
        self.assertContains(response, "limpeza inteligente para grandes áreas")

    def test_xyron_robot_detail_keeps_consultative_guardrails(self):
        checks = [
            ("liro-littlebot", "não substitui o professor"),
            ("patrol-orbit", "não é substituir completamente equipes de segurança"),
            ("hygibot", "não como substituição automática"),
            ("hostbot", "não substitui acolhimento humano"),
            ("waiterbot", "não deve ser tratado como substituto completo de garçons"),
            ("carebot", "não realiza promessa médica"),
            ("mowerbot", "corte de grama"),
        ]

        for slug, text in checks:
            with self.subTest(slug=slug):
                response = self.client.get(reverse("institutional:xyron_robot_detail", args=[slug]))

                self.assertEqual(response.status_code, 200)
                self.assertContains(response, text)

    def test_xyron_robot_detail_referenced_images_exist(self):
        from pathlib import Path

        static_root = Path(settings.BASE_DIR) / "static"
        missing = []
        for robot in XYRON_ROBOTS:
            image_paths = [robot["image"], *robot.get("secondary_images", [])]
            for image_path in image_paths:
                if not (static_root / image_path).exists():
                    missing.append((robot["slug"], image_path))

        self.assertEqual(missing, [])

    def test_xyron_robot_detail_contains_other_robot_links(self):
        response = self.client.get(
            reverse("institutional:xyron_robot_detail", args=["mowerbot"])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            reverse("institutional:xyron_robot_detail", args=["liro-littlebot"]),
        )
        self.assertContains(
            response,
            reverse("institutional:xyron_robot_detail", args=["carebot"]),
        )
        self.assertEqual(response.context["robot"]["slug"], "mowerbot")

    def test_xyron_liro_legacy_url_name_still_renders_detail(self):
        response = self.client.get(reverse("institutional:xyron_liro_littlebot"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "LIRO / LittleBot")
        self.assertContains(response, "O LIRO substitui o professor?")
        self.assertEqual(response.context["robot"]["slug"], "liro-littlebot")

    def test_unknown_xyron_robot_returns_404(self):
        response = self.client.get("/solucoes/xyron-robotics/nao-existe/")

        self.assertEqual(response.status_code, 404)

    def test_engenharia_embarcada_canonical_url(self):
        self.assertEqual(
            reverse("institutional:engenharia_embarcada"),
            "/engenharia-embarcada/",
        )

    def test_engenharia_embarcada_page_uses_new_template(self):
        response = self.client.get(reverse("institutional:engenharia_embarcada"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response, "institutional/eitech/pages/engenharia_embarcada.html"
        )
        self.assertContains(response, "Engenharia Embarcada")

    def test_legacy_refrigeracao_url_redirects_to_engenharia_embarcada(self):
        response = self.client.get("/parceiros/refrigeracao/", follow=False)

        self.assertRedirects(
            response,
            reverse("institutional:engenharia_embarcada"),
            status_code=301,
            fetch_redirect_response=False,
        )

    def test_services_canonical_url_is_solucoes(self):
        self.assertEqual(reverse("institutional:services"), "/solucoes/")

    def test_legacy_servicos_redirects_permanently_to_solucoes(self):
        rsp = self.client.get("/servicos/", follow=False)
        self.assertRedirects(
            rsp,
            reverse("institutional:services"),
            status_code=301,
            fetch_redirect_response=False,
        )

    def test_home_uses_shared_action_layout_classes(self):
        response = self.client.get(reverse("institutional:home"))

        self.assertContains(response, "scb-home-hero-actions")
        self.assertContains(response, "scb-home-final-actions")

    def test_web_systems_page_has_expected_visual_contract(self):
        response = self.client.get(
            reverse("institutional:service_sistemas_web_aplicativos")
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response,
            "institutional/eitech/pages/service-sistemas-web-aplicativos.html",
        )
        self.assertContains(response, "service-web-systems-page")
        self.assertContains(response, "institutional/eitech/css/scb-service.css")
        self.assertContains(response, "Solicitar diagnóstico")
        self.assertContains(response, "Falar com a Lívia")

    def test_maintenance_uses_shared_service_styles_only(self):
        response = self.client.get(
            reverse("institutional:service_manutencao_tpm_confiabilidade")
        )

        self.assertContains(response, "institutional/eitech/css/scb-service.css")
        self.assertNotContains(response, "scb-maintenance.css")
        self.assertContains(response, "scb-maintenance-scope-note")


@override_settings(MIDDLEWARE=TEST_MIDDLEWARE)
class SitemapRobotsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        seed_technical_catalog_from_static()
        TechnicalProduct.objects.create(
            title="Produto inativo fora do sitemap",
            slug="produto-inativo-sitemap",
            brand="Teste",
            supplier_name="Smart Control Brasil",
            category="Linha desativada",
            short_description="Produto desativado para validar exclusao do sitemap.",
            application_area="Teste",
            is_active=False,
        )

    def sitemap_response(self):
        return self.client.get(
            "/sitemap.xml",
            HTTP_HOST="www.example.test",
            secure=False,
        )

    def sitemap_locations(self):
        response = self.sitemap_response()
        root = ElementTree.fromstring(response.content)
        namespace = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        return [node.text for node in root.findall("sm:url/sm:loc", namespace)]

    def test_sitemap_response_is_google_compatible_xml(self):
        response = self.sitemap_response()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/xml")
        self.assertTrue(response.content.startswith(b"<?xml version"))

    def test_sitemap_uses_canonical_https_domain_without_duplicates(self):
        locations = self.sitemap_locations()

        self.assertEqual(len(locations), len(set(locations)))
        self.assertTrue(locations)
        for location in locations:
            with self.subTest(location=location):
                self.assertTrue(location.startswith("https://smartcontrolbrasil.com.br/"))
                self.assertNotIn("https://www.smartcontrolbrasil.com.br", location)
                self.assertNotIn("?", location)

    def test_sitemap_includes_main_public_urls(self):
        locations = set(self.sitemap_locations())
        expected_paths = [
            reverse("institutional:home"),
            reverse("institutional:about"),
            reverse("institutional:contact"),
            reverse("institutional:services"),
            reverse("institutional:representada_mitsubishi_automacao"),
            reverse("institutional:xyron_robotics"),
            reverse("institutional:xyron_robot_detail", args=["hygibot"]),
            reverse("institutional:service_automacao_industrial_clps"),
            reverse("institutional:service_manutencao_tpm_confiabilidade"),
            reverse("institutional:projects"),
            reverse("institutional:automacao_industrial_clps_ihms"),
            reverse("institutional:blog"),
            reverse("institutional:blog_paineis_eletricos_automacao"),
            reverse("marketplace_ecom:home"),
            reverse("marketplace_ecom:products"),
            reverse("marketplace_ecom:product-detail", kwargs={"slug": "mitsubishi-clp-melsec"}),
            reverse("marketplace_ecom:product-detail", kwargs={"slug": "xyron-hygibot-dune-bot"}),
        ]

        for path in expected_paths:
            with self.subTest(path=path):
                self.assertIn(f"https://smartcontrolbrasil.com.br{path}", locations)

    def test_sitemap_excludes_private_redirect_api_and_inactive_urls(self):
        locations = self.sitemap_locations()
        forbidden_fragments = [
            "/admin/",
            "/api/",
            "/login/",
            "/logout/",
            "/livia/",
            "/dashboard/",
            "/ecossistema/",
            "/field/",
            "/portal/",
            "/parceiros/refrigeracao/",
            "/produto-inativo-sitemap/",
            "/request-quote/",
        ]

        for fragment in forbidden_fragments:
            with self.subTest(fragment=fragment):
                self.assertFalse(any(fragment in location for location in locations))

    def test_sitemap_product_entries_have_lastmod(self):
        response = self.sitemap_response()
        root = ElementTree.fromstring(response.content)
        namespace = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        product_url = (
            "https://smartcontrolbrasil.com.br"
            + reverse("marketplace_ecom:product-detail", kwargs={"slug": "mitsubishi-clp-melsec"})
        )

        for url_node in root.findall("sm:url", namespace):
            loc = url_node.find("sm:loc", namespace)
            if loc is not None and loc.text == product_url:
                self.assertIsNotNone(url_node.find("sm:lastmod", namespace))
                break
        else:
            self.fail(f"Product URL not found in sitemap: {product_url}")

    def test_robots_txt_points_to_canonical_sitemap(self):
        response = self.client.get("/robots.txt")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/plain")
        self.assertContains(
            response,
            "Sitemap: https://smartcontrolbrasil.com.br/sitemap.xml",
        )
        self.assertContains(response, "Disallow: /admin/")
        self.assertContains(response, "Disallow: /api/")



@override_settings(
    MIDDLEWARE=TEST_MIDDLEWARE,
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    CONTACT_FORM_RECIPIENTS=["contato@smartcontrolbrasil.com.br"],
    CONTACT_FORM_BCC=["engenharia@smartcontrolbrasil.com.br"],
    CACHES={
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        }
    },
    CONTACT_FORM_RATE_LIMIT=5,
    CONTACT_FORM_RATE_WINDOW_SECONDS=900,
)
class ContactViewTests(SimpleTestCase):
    databases = {"default"}

    def setUp(self):
        from django.core.cache import cache

        cache.clear()
        mail.outbox.clear()
        self.url = reverse("institutional:contact")
        self.valid_data = {
            "contact_name": "Maria Silva",
            "company": "Indústria Exemplo",
            "whatsapp": "(11) 99999-9999",
            "email": "maria@example.com",
            "segment": "Indústria",
            "interest": "automacao",
            "main_problem": "Automatizar uma linha de produção",
            "message": "Precisamos avaliar escopo e prazo.",
        }

    def test_contact_get_returns_200(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)

    def test_valid_post_sends_email_and_redirects(self):
        response = self.client.post(self.url, self.valid_data)

        self.assertRedirects(
            response,
            self.url,
            fetch_redirect_response=False,
        )
        self.assertEqual(len(mail.outbox), 1)
        sent_email = mail.outbox[0]
        self.assertEqual(
            sent_email.to,
            ["contato@smartcontrolbrasil.com.br"],
        )
        self.assertEqual(sent_email.bcc, ["engenharia@smartcontrolbrasil.com.br"])
        self.assertEqual(sent_email.reply_to, ["maria@example.com"])
        self.assertIn("Nome: Maria Silva", sent_email.body)
        self.assertIn("Mensagem:\nPrecisamos avaliar escopo e prazo.", sent_email.body)

    def test_contact_get_renders_honeypot_field(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="website"')

    def test_missing_required_fields_is_blocked_as_spam_with_neutral_message(self):
        invalid_data = {**self.valid_data, "contact_name": ""}
        response = self.client.post(self.url, invalid_data)
        self.assertRedirects(response, self.url, fetch_redirect_response=False)
        self.assertEqual(len(mail.outbox), 0)

    def test_honeypot_filled_does_not_send_email(self):
        spam_data = {**self.valid_data, "website": "https://spam.example"}
        response = self.client.post(self.url, spam_data)
        self.assertRedirects(response, self.url, fetch_redirect_response=False)
        self.assertEqual(len(mail.outbox), 0)

    def test_suspicious_term_casino_does_not_send_email(self):
        spam_data = {**self.valid_data, "message": "Oferta de casino com free money imperdível"}
        response = self.client.post(self.url, spam_data)
        self.assertRedirects(response, self.url, fetch_redirect_response=False)
        self.assertEqual(len(mail.outbox), 0)

    def test_many_links_does_not_send_email(self):
        spam_data = {
            **self.valid_data,
            "message": " ".join(
                [
                    "https://a.com",
                    "https://b.com",
                    "https://c.com",
                    "https://d.com",
                    "https://e.com",
                    "https://f.com",
                ]
            ),
        }
        response = self.client.post(self.url, spam_data)
        self.assertRedirects(response, self.url, fetch_redirect_response=False)
        self.assertEqual(len(mail.outbox), 0)

    def test_short_message_does_not_send_email(self):
        spam_data = {**self.valid_data, "message": "oi"}
        response = self.client.post(self.url, spam_data)
        self.assertRedirects(response, self.url, fetch_redirect_response=False)
        self.assertEqual(len(mail.outbox), 0)

    def test_ken_carrell_spam_example_does_not_send_email(self):
        spam_data = {
            "contact_name": "Ken Carrell",
            "company": "Ken",
            "whatsapp": "737550229",
            "email": "kenp2025x@yahoo.com",
            "interest": "software",
            "message": (
                "Was just browsing smartcontrolbrasil.com.br and was impressed the layout. "
                "Nicely design and great user experience. Just had to drop a message, "
                "have a great day! we7f8sd82"
            ),
        }
        response = self.client.post(self.url, spam_data)
        self.assertRedirects(response, self.url, fetch_redirect_response=False)
        self.assertEqual(len(mail.outbox), 0)

    def test_legitimate_english_submission_sends_email(self):
        english_data = {
            "contact_name": "John Smith",
            "company": "Acme Packaging Ltd",
            "whatsapp": "+1 555 123 4567",
            "email": "john@gmail.com",
            "interest": "automacao",
            "message": (
                "We need PLC integration for our packaging line. "
                "Please send a quote and estimated timeline."
            ),
        }
        response = self.client.post(self.url, english_data)
        self.assertRedirects(response, self.url, fetch_redirect_response=False)
        self.assertEqual(len(mail.outbox), 1)

    def test_rate_limit_blocks_rapid_submissions(self):
        from django.core.cache import cache

        with override_settings(CONTACT_FORM_RATE_LIMIT=2, CONTACT_FORM_RATE_WINDOW_SECONDS=60):
            cache.clear()
            mail.outbox.clear()
            self.client.post(self.url, self.valid_data)
            self.client.post(self.url, {**self.valid_data, "email": "maria2@example.com"})
            response = self.client.post(self.url, {**self.valid_data, "email": "maria3@example.com"})
        self.assertRedirects(response, self.url, fetch_redirect_response=False)
        self.assertEqual(len(mail.outbox), 2)


class PreloaderFailSafeTests(TestCase):
    """Garante fail-safe do preloader institucional (mobile e desktop)."""

    def test_home_renders_preloader_markup(self):
        response = self.client.get(reverse("institutional:home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'class="preloader"')

    def test_main_js_has_preloader_fail_safe(self):
        main_js = (
            Path(settings.BASE_DIR) / "static/institutional/eitech/js/main.js"
        ).read_text(encoding="utf-8")
        self.assertIn("function hidePreloader", main_js)
        self.assertIn('preloader.classList.add("is-hidden")', main_js)
        self.assertIn('document.addEventListener("DOMContentLoaded", hidePreloader', main_js)
        self.assertIn('window.addEventListener("load", hidePreloader', main_js)
        self.assertIn("setTimeout(hidePreloader, PRELOADER_TIMEOUT_MS)", main_js)
        self.assertIn("PRELOADER_TIMEOUT_MS = 2500", main_js)
        self.assertIn("releasePageLock", main_js)
        self.assertNotIn('$(".preloader").fadeToggle()', main_js)

    def test_main_min_js_has_preloader_fail_safe(self):
        main_min_js = (
            Path(settings.BASE_DIR) / "static/institutional/eitech/js/main.min.js"
        ).read_text(encoding="utf-8")
        self.assertIn("hidePreloader", main_min_js)
        self.assertIn("is-hidden", main_min_js)
        self.assertIn("DOMContentLoaded", main_min_js)
        self.assertIn("2500", main_min_js)
        self.assertNotIn("fadeToggle", main_min_js)

    def test_preloader_css_has_hidden_state(self):
        main_css = (
            Path(settings.BASE_DIR) / "static/institutional/eitech/css/main.css"
        ).read_text(encoding="utf-8")
        bundle_css = (
            Path(settings.BASE_DIR)
            / "static/institutional/eitech/css/main.bundle.min.css"
        ).read_text(encoding="utf-8")
        self.assertIn(".preloader.is-hidden", main_css)
        self.assertIn("pointer-events: none", main_css)
        self.assertIn(".preloader.is-hidden", bundle_css)
