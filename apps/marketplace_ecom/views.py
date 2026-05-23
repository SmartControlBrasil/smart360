import unicodedata

from django.contrib import messages
from django.http import Http404
from django.shortcuts import redirect, render
from django.views import View
from django.views.generic import TemplateView

from apps.growth_engine.models import Lead, LeadInteraction, LeadSource
from apps.marketplace_ecom.models import TechnicalProduct

from .forms import MarketplaceQuoteRequestForm


CATEGORIES = [{'title': 'Robótica e IA', 'image': 'marketplace/ecom/img/page/homepage1/gaming.png'}, {'title': 'Ar-condicionado', 'image': 'marketplace/ecom/img/page/homepage1/electric.png'}, {'title': 'Automação industrial', 'image': 'marketplace/ecom/img/page/homepage1/controller.png'}, {'title': 'Soluções prediais', 'image': 'marketplace/ecom/img/page/homepage1/electronic.png'}, {'title': 'Equipamentos profissionais', 'image': 'marketplace/ecom/img/page/homepage1/computer.png'}]

BRAND_PARTNERS = [{'name': 'LG', 'role': 'Fabricante HVAC'}, {'name': 'Carrier', 'role': 'Fabricante HVAC'}, {'name': 'Daikin', 'role': 'Fabricante HVAC'}, {'name': 'Midea', 'role': 'Fabricante HVAC'}, {'name': 'Mitsubishi Electric', 'role': 'Fabricante automação e HVAC'}, {'name': 'Xyron Robotics', 'role': 'Fabricante robótica e IA'}, {'name': 'BHP Ar Condicionado', 'role': 'Parceiro / revenda credenciada'}]

PRODUCTS = [{'title': 'Littlebot', 'slug': 'xyron-littlebot', 'brand': 'Xyron Robotics', 'supplier': 'Smart Control Brasil', 'category': 'Robótica e IA', 'short_description': 'Robo compacto para recepcao, interacao guiada e apresentacoes em ambientes comerciais.', 'application_area': 'Atendimento, demonstracoes e educacao', 'price_label': 'Sob consulta', 'button_label': 'Solicitar orçamento', 'image': 'marketplace/ecom/img/page/homepage1/imgsp1.png', 'rating': 'Sob consulta'}, {'title': 'Orbit', 'slug': 'xyron-orbit', 'brand': 'Xyron Robotics', 'supplier': 'Smart Control Brasil', 'category': 'Robótica e IA', 'short_description': 'Plataforma robotica para circulacao, apoio operacional e experiencias interativas.', 'application_area': 'Operacao assistida e relacionamento com clientes', 'price_label': 'Sob consulta', 'button_label': 'Solicitar orçamento', 'image': 'marketplace/ecom/img/page/homepage1/imgsp2.png', 'rating': 'Sob consulta'}, {'title': 'Neo', 'slug': 'xyron-neo', 'brand': 'Xyron Robotics', 'supplier': 'Smart Control Brasil', 'category': 'Robótica e IA', 'short_description': 'Robo social para recepcao, orientacao de visitantes e apoio a equipes de atendimento.', 'application_area': 'Recepcao corporativa e eventos', 'price_label': 'Sob consulta', 'button_label': 'Solicitar orçamento', 'image': 'marketplace/ecom/img/page/homepage1/imgsp3.png', 'rating': 'Sob consulta'}, {'title': 'Waiterbot', 'slug': 'xyron-waiterbot', 'brand': 'Xyron Robotics', 'supplier': 'Smart Control Brasil', 'category': 'Robótica e IA', 'short_description': 'Robo de apoio para entrega e atendimento em restaurantes, hoteis e ambientes de servico.', 'application_area': 'Food service, hotelaria e hospitalidade', 'price_label': 'Sob consulta', 'button_label': 'Solicitar orçamento', 'image': 'marketplace/ecom/img/page/homepage1/imgsp4.png', 'rating': 'Sob consulta'}, {'title': 'Carebot', 'slug': 'xyron-carebot', 'brand': 'Xyron Robotics', 'supplier': 'Smart Control Brasil', 'category': 'Robótica e IA', 'short_description': 'Robo de suporte para cuidados, orientacao e acompanhamento em ambientes sensiveis.', 'application_area': 'Saude, cuidado e apoio assistido', 'price_label': 'Sob consulta', 'button_label': 'Solicitar orçamento', 'image': 'marketplace/ecom/img/page/homepage1/imgsp5.png', 'rating': 'Sob consulta'}, {'title': 'Hygibot', 'slug': 'xyron-hygibot', 'brand': 'Xyron Robotics', 'supplier': 'Smart Control Brasil', 'category': 'Robótica e IA', 'short_description': 'Robo voltado a higiene operacional e apoio a rotinas de limpeza profissional.', 'application_area': 'Limpeza, facilities e ambientes publicos', 'price_label': 'Sob consulta', 'button_label': 'Solicitar orçamento', 'image': 'marketplace/ecom/img/page/homepage1/imgsp6.png', 'rating': 'Sob consulta'}, {'title': 'Hostbot', 'slug': 'xyron-hostbot', 'brand': 'Xyron Robotics', 'supplier': 'Smart Control Brasil', 'category': 'Robótica e IA', 'short_description': 'Robo anfitriao para acolhimento, informacao e experiencia de visitantes.', 'application_area': 'Eventos, showrooms e recepcao', 'price_label': 'Sob consulta', 'button_label': 'Solicitar orçamento', 'image': 'marketplace/ecom/img/page/homepage1/imgsp7.png', 'rating': 'Sob consulta'}, {'title': 'Buddy', 'slug': 'xyron-buddy', 'brand': 'Xyron Robotics', 'supplier': 'Smart Control Brasil', 'category': 'Robótica e IA', 'short_description': 'Robo companion para interacao, presenca digital e experiencias educacionais.', 'application_area': 'Educacao, demonstracao e relacionamento', 'price_label': 'Sob consulta', 'button_label': 'Solicitar orçamento', 'image': 'marketplace/ecom/img/page/homepage1/electronic.png', 'rating': 'Sob consulta'}, {'title': 'Mowerbot', 'slug': 'xyron-mowerbot', 'brand': 'Xyron Robotics', 'supplier': 'Smart Control Brasil', 'category': 'Robótica e IA', 'short_description': 'Robo para apoio a manutencao de areas externas e automacao de rotinas de jardinagem.', 'application_area': 'Areas externas, condominios e facilities', 'price_label': 'Sob consulta', 'button_label': 'Solicitar orçamento', 'image': 'marketplace/ecom/img/page/homepage1/computer.png', 'rating': 'Sob consulta'}, {'title': 'Hi Wall Inverter', 'slug': 'lg-hi-wall-inverter', 'brand': 'LG', 'supplier': 'BHP Ar Condicionado', 'category': 'Ar-condicionado', 'short_description': 'Equipamento tipo hi wall inverter para climatizacao eficiente de ambientes residenciais e comerciais.', 'application_area': 'Climatizacao residencial e comercial', 'price_label': 'Sob consulta', 'button_label': 'Solicitar orçamento', 'image': 'marketplace/ecom/img/page/homepage1/imgsp1.png', 'rating': 'Sob consulta'}, {'title': 'Multi Split', 'slug': 'daikin-multi-split', 'brand': 'Daikin', 'supplier': 'BHP Ar Condicionado', 'category': 'Ar-condicionado', 'short_description': 'Solucao multi split para atender varios ambientes com uma composicao compacta e flexivel.', 'application_area': 'Projetos multiambiente', 'price_label': 'Sob consulta', 'button_label': 'Solicitar orçamento', 'image': 'marketplace/ecom/img/page/homepage1/imgsp2.png', 'rating': 'Sob consulta'}, {'title': 'Teto', 'slug': 'carrier-teto', 'brand': 'Carrier', 'supplier': 'BHP Ar Condicionado', 'category': 'Ar-condicionado', 'short_description': 'Unidade tipo teto para climatizacao de areas amplas com distribuicao de ar consistente.', 'application_area': 'Lojas, salas amplas e areas tecnicas', 'price_label': 'Sob consulta', 'button_label': 'Solicitar orçamento', 'image': 'marketplace/ecom/img/page/homepage1/imgsp3.png', 'rating': 'Sob consulta'}, {'title': 'Cassete', 'slug': 'midea-cassete', 'brand': 'Midea', 'supplier': 'BHP Ar Condicionado', 'category': 'Ar-condicionado', 'short_description': 'Sistema cassete para instalacao embutida e distribuicao uniforme em ambientes corporativos.', 'application_area': 'Escritorios, lojas e salas comerciais', 'price_label': 'Sob consulta', 'button_label': 'Solicitar orçamento', 'image': 'marketplace/ecom/img/page/homepage1/imgsp4.png', 'rating': 'Sob consulta'}, {'title': 'Duto', 'slug': 'samsung-duto', 'brand': 'Samsung', 'supplier': 'BHP Ar Condicionado', 'category': 'Ar-condicionado', 'short_description': 'Equipamento dutado para climatizacao integrada a projetos arquitetonicos e prediais.', 'application_area': 'Solucoes prediais e climatizacao central', 'price_label': 'Sob consulta', 'button_label': 'Solicitar orçamento', 'image': 'marketplace/ecom/img/page/homepage1/imgsp5.png', 'rating': 'Sob consulta'}, {'title': 'Splitão', 'slug': 'tcl-splitao', 'brand': 'TCL', 'supplier': 'BHP Ar Condicionado', 'category': 'Ar-condicionado', 'short_description': 'Sistema de maior capacidade para ambientes comerciais, tecnicos e operacoes profissionais.', 'application_area': 'Ambientes comerciais e equipamentos profissionais', 'price_label': 'Sob consulta', 'button_label': 'Solicitar orçamento', 'image': 'marketplace/ecom/img/page/homepage1/imgsp6.png', 'rating': 'Sob consulta'}, {'title': 'Cortina de Ar', 'slug': 'elgin-cortina-de-ar', 'brand': 'Elgin', 'supplier': 'BHP Ar Condicionado', 'category': 'Soluções prediais', 'short_description': 'Cortina de ar para separacao termica, conforto e apoio a eficiencia energetica.', 'application_area': 'Portas comerciais, recepcoes e acessos', 'price_label': 'Sob consulta', 'button_label': 'Solicitar orçamento', 'image': 'marketplace/ecom/img/page/homepage1/imgsp7.png', 'rating': 'Sob consulta'}, {'title': 'Fancolete Hidronico', 'slug': 'fujitsu-fancolete-hidronico', 'brand': 'Fujitsu', 'supplier': 'BHP Ar Condicionado', 'category': 'Soluções prediais', 'short_description': 'Fancolete hidronico para climatizacao predial integrada a sistemas de agua gelada.', 'application_area': 'Climatizacao predial e sistemas hidronicos', 'price_label': 'Sob consulta', 'button_label': 'Solicitar orçamento', 'image': 'marketplace/ecom/img/page/homepage1/electronic.png', 'rating': 'Sob consulta'}, {'title': 'Sistemas de Climatização', 'slug': 'mitsubishi-electric-sistemas-de-climatizacao', 'brand': 'Mitsubishi Electric', 'supplier': 'Smart Control Brasil', 'category': 'Ar-condicionado', 'short_description': 'Solucoes de climatizacao para projetos corporativos, comerciais e prediais.', 'application_area': 'Climatizacao profissional', 'price_label': 'Sob consulta', 'button_label': 'Solicitar orçamento', 'image': 'marketplace/ecom/img/page/homepage1/computer.png', 'rating': 'Sob consulta'}, {'title': 'Automação Predial', 'slug': 'mitsubishi-electric-automacao-predial', 'brand': 'Mitsubishi Electric', 'supplier': 'Smart Control Brasil', 'category': 'Soluções prediais', 'short_description': 'Solucoes para controle, integracao e eficiencia operacional de edificios.', 'application_area': 'Edificios comerciais e infraestrutura predial', 'price_label': 'Sob consulta', 'button_label': 'Solicitar orçamento', 'image': 'marketplace/ecom/img/page/homepage1/imgsp1.png', 'rating': 'Sob consulta'}, {'title': 'Inversores de Frequência', 'slug': 'mitsubishi-electric-inversores-de-frequencia', 'brand': 'Mitsubishi Electric', 'supplier': 'Smart Control Brasil', 'category': 'Automação industrial', 'short_description': 'Inversores para controle de motores, eficiencia energetica e automacao de processos.', 'application_area': 'Motores, bombas, ventiladores e maquinas', 'price_label': 'Sob consulta', 'button_label': 'Solicitar orçamento', 'image': 'marketplace/ecom/img/page/homepage1/imgsp2.png', 'rating': 'Sob consulta'}, {'title': 'Automação Industrial', 'slug': 'mitsubishi-electric-automacao-industrial', 'brand': 'Mitsubishi Electric', 'supplier': 'Smart Control Brasil', 'category': 'Automação industrial', 'short_description': 'Solucoes de controle e integracao para processos industriais e linhas produtivas.', 'application_area': 'Industria, maquinas e processos', 'price_label': 'Sob consulta', 'button_label': 'Solicitar orçamento', 'image': 'marketplace/ecom/img/page/homepage1/imgsp3.png', 'rating': 'Sob consulta'}, {'title': 'Sistemas Visuais', 'slug': 'mitsubishi-electric-sistemas-visuais', 'brand': 'Mitsubishi Electric', 'supplier': 'Smart Control Brasil', 'category': 'Equipamentos profissionais', 'short_description': 'Sistemas visuais profissionais para monitoramento, operacao e comunicacao.', 'application_area': 'Operacao, supervisao e ambientes corporativos', 'price_label': 'Sob consulta', 'button_label': 'Solicitar orçamento', 'image': 'marketplace/ecom/img/page/homepage1/imgsp4.png', 'rating': 'Sob consulta'}]

for _mock_entry in PRODUCTS:
    _mock_entry.setdefault("description", "")
    _mock_entry.setdefault("is_featured", False)
    _mock_entry.setdefault("featured_image_url", "")


CATALOG_FALLBACK_STATIC_IMAGE = "marketplace/ecom/img/page/homepage1/imgsp1.png"


def normalize_filter_value(value):
    normalized = unicodedata.normalize("NFKD", str(value or ""))
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii")
    return ascii_value.casefold().strip()


def product_matches_query(product, query):
    searchable_fields = [
        product["title"],
        product["brand"],
        product["supplier"],
        product["category"],
        product["application_area"],
        product["short_description"],
        product.get("description", ""),
    ]
    normalized_query = normalize_filter_value(query)
    return any(normalized_query in normalize_filter_value(value) for value in searchable_fields)


def filter_products(products, filters):
    filtered = list(products)
    if filters["q"]:
        filtered = [product for product in filtered if product_matches_query(product, filters["q"])]

    for field in ["brand", "supplier", "category"]:
        if filters[field]:
            filtered = [
                product for product in filtered
                if normalize_filter_value(product[field]) == normalize_filter_value(filters[field])
            ]

    if filters["application"]:
        filtered = [
            product for product in filtered
            if normalize_filter_value(product["application_area"]) == normalize_filter_value(filters["application"])
        ]

    return filtered


def unique_values(products, field):
    return sorted({product[field] for product in products})


def build_active_filters(filters):
    labels = {
        "q": "Busca",
        "brand": "Fabricante",
        "supplier": "Parceiro",
        "category": "Categoria",
        "application": "Aplicação",
    }
    return [
        {"label": labels[key], "value": value}
        for key, value in filters.items()
        if value
    ]


def technical_product_to_catalog_entry(instance: TechnicalProduct) -> dict:
    """Converte modelo persistido para o formato de catálogo usado pelos templates (dict)."""
    featured_image_url = ""
    media_asset = getattr(instance, "featured_image", None)
    if media_asset is not None:
        asset_image = getattr(media_asset, "image", None)
        if asset_image and getattr(asset_image, "name", ""):
            featured_image_url = asset_image.url

    description = instance.description or ""
    price_label = "Sob consulta"
    rating = "Sob consulta"
    button_label = "Solicitar orçamento"
    image = CATALOG_FALLBACK_STATIC_IMAGE

    return {
        "title": instance.title,
        "slug": instance.slug,
        "brand": instance.brand,
        "supplier": instance.supplier_name,
        "category": instance.category,
        "short_description": instance.short_description,
        "description": description,
        "application_area": instance.application_area,
        "price_label": price_label,
        "rating": rating,
        "button_label": button_label,
        "image": image,
        "is_featured": instance.is_featured,
        "featured_image_url": featured_image_url,
    }


def merge_catalog_products() -> list:
    queryset = TechnicalProduct.objects.filter(is_active=True).select_related("featured_image").order_by(
        "-is_featured",
        "-updated_at",
    )
    merged: list[dict] = []
    consumed_slugs: set[str] = set()

    for row in queryset:
        merged.append(technical_product_to_catalog_entry(row))
        consumed_slugs.add(row.slug)

    for mock_product in PRODUCTS:
        if mock_product["slug"] in consumed_slugs:
            continue
        merged.append(mock_product)

    return merged


def catalog_product_for_slug(slug: str) -> dict:
    if TechnicalProduct.objects.filter(slug=slug, is_active=False).exists():
        raise Http404("Produto nao encontrado")

    persisted = TechnicalProduct.objects.filter(slug=slug, is_active=True).select_related("featured_image").first()
    if persisted:
        return technical_product_to_catalog_entry(persisted)

    for mock_product in PRODUCTS:
        if mock_product["slug"] == slug:
            return mock_product

    raise Http404("Produto nao encontrado")


def get_products():
    """Catálogo: produtos ativos persistidos (prioridade por slug exclusivo), depois mocks como fallback."""

    return merge_catalog_products()


def get_product_or_404(slug: str):
    return catalog_product_for_slug(slug)


def get_marketplace_lead_source():
    source, _created = LeadSource.objects.get_or_create(
        name="marketplace_ecom",
        defaults={
            "source_type": LeadSource.SourceType.ORGANIC,
            "description": "Solicitações de orçamento geradas pelo marketplace visual Smart360.",
        },
    )
    return source


def create_quote_request_lead(product, form):
    data = form.cleaned_data
    lead = Lead.objects.create(
        company_name=data["company"] or data["name"],
        contact_name=data["name"],
        email=data["email"],
        phone=data["phone"],
        whatsapp=data["phone"],
        city=data["city"],
        source=get_marketplace_lead_source(),
        status=Lead.Status.NEW,
        notes=data["message"],
        metadata={
            "product_slug": product["slug"],
            "product_title": product["title"],
            "brand": product["brand"],
            "supplier": product["supplier"],
            "category": product["category"],
            "application_area": product["application_area"],
            "origin": "marketplace_ecom",
            "request_type": "quote_request",
        },
    )
    LeadInteraction.objects.create(
        lead=lead,
        interaction_type=LeadInteraction.InteractionType.NOTE,
        channel=LeadInteraction.Channel.OTHER,
        summary="Solicitação de orçamento via marketplace.",
    )
    return lead


class MarketplaceHomeView(TemplateView):
    template_name = "marketplace_ecom/home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["products"] = get_products()
        context["featured_products"] = get_products()[:8]
        context["categories"] = CATEGORIES
        context["brand_partners"] = BRAND_PARTNERS
        return context


class ProductListView(TemplateView):
    template_name = "marketplace_ecom/products.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        products = get_products()
        filters = {
            "q": self.request.GET.get("q", "").strip(),
            "brand": self.request.GET.get("brand", "").strip(),
            "supplier": self.request.GET.get("supplier", "").strip(),
            "category": self.request.GET.get("category", "").strip(),
            "application": self.request.GET.get("application", "").strip(),
        }
        filtered_products = filter_products(products, filters)

        context["products"] = filtered_products
        context["categories"] = CATEGORIES
        context["brands"] = unique_values(products, "brand")
        context["suppliers"] = unique_values(products, "supplier")
        context["available_brands"] = context["brands"]
        context["available_suppliers"] = context["suppliers"]
        context["available_categories"] = unique_values(products, "category")
        context["available_applications"] = unique_values(products, "application_area")
        context["active_filters"] = build_active_filters(filters)
        context["filters"] = filters
        context["result_count"] = len(filtered_products)
        return context


class ProductDetailView(TemplateView):
    template_name = "marketplace_ecom/product_detail.html"

    def get_context_data(self, **kwargs):
        product = get_product_or_404(self.kwargs["slug"])
        context = super().get_context_data(**kwargs)
        context["product"] = product
        context["quote_form"] = kwargs.get("quote_form") or MarketplaceQuoteRequestForm()
        context["related_products"] = [
            item for item in get_products() if item["slug"] != product["slug"] and item["category"] == product["category"]
        ][:3]
        if not context["related_products"]:
            context["related_products"] = [item for item in get_products() if item["slug"] != product["slug"]][:3]
        return context


class MarketplaceQuoteRequestView(View):
    def post(self, request, slug):
        product = get_product_or_404(slug)
        form = MarketplaceQuoteRequestForm(request.POST)
        if form.is_valid():
            create_quote_request_lead(product, form)
            messages.success(request, "Solicitação enviada. Nossa equipe comercial entrará em contato.")
            return redirect("marketplace_ecom:product-detail", slug=product["slug"])

        view = ProductDetailView()
        view.request = request
        view.kwargs = {"slug": slug}
        context = view.get_context_data(quote_form=form)
        return render(request, ProductDetailView.template_name, context, status=200)
