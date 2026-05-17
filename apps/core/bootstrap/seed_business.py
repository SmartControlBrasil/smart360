from __future__ import annotations

from decimal import Decimal

from django.utils import timezone

from apps.caneca_de_garagem.models import (
    ArtworkAsset,
    CreativeStoreProfile,
    CustomizationRequest,
    CustomizationTemplate,
    ProductionJob,
    ProductionStep,
    ShipmentPreparation,
)
from apps.growth_engine.models import (
    Lead,
    LeadAssignment,
    LeadCampaign,
    LeadInteraction,
    LeadQualification,
    LeadSource,
    LeadTag,
)
from apps.market_core.models import MarketplaceOrder, MarketplaceOrderItem, MarketplaceProduct, MarketplaceVendor
from apps.smart_site_factory.models import (
    ConfiguratorOption,
    ConfiguratorQuestion,
    DeliveryRecord,
    Niche,
    ProductionTask,
    SiteOrder,
    SiteOrderAnswer,
    SiteProjectIntake,
    Template,
    TemplateRecommendationRule,
)
from apps.core.bootstrap.common import attach_content_file


def seed_smart_site_factory(ctx):
    ctx.section("Seeding smart_site_factory")
    niches = [
        ("dentista", "Sites para clinicas odontologicas"),
        ("petshop", "Sites para petshops com agendamento"),
        ("academia", "Sites para academias e studios"),
    ]
    for slug, description in niches:
        niche, _ = Niche.objects.update_or_create(
            slug=slug,
            defaults={"name": slug.capitalize(), "description": description, "is_active": True},
        )
        ctx.put("niches", slug, niche)

    template_specs = [
        ("dentista_pro", "Dentista Pro", "dentista", Decimal("2490.00")),
        ("petshop_premium", "Petshop Premium", "petshop", Decimal("2190.00")),
        ("academia_modern", "Academia Modern", "academia", Decimal("2590.00")),
    ]
    for slug, name, niche_slug, price in template_specs:
        template, _ = Template.objects.update_or_create(
            slug=slug,
            defaults={
                "niche": ctx.get("niches", niche_slug),
                "name": name,
                "description": f"Template bootstrap {name}",
                "version": "1.0.0",
                "template_type": Template.TemplateType.ONE_PAGE,
                "base_price": price,
                "status": Template.Status.READY,
                "is_active": True,
            },
        )
        ctx.put("site_templates", slug, template)

    question_specs = [
        ("dentista", "Seu foco principal e implantes?", "single_choice", 1, ["sim", "nao"]),
        ("petshop", "Voce oferece banho e tosa?", "single_choice", 1, ["sim", "nao"]),
        ("academia", "Sua academia oferece personal trainer?", "single_choice", 1, ["sim", "nao"]),
    ]
    for niche_slug, text, qtype, order, options in question_specs:
        question, _ = ConfiguratorQuestion.objects.update_or_create(
            niche=ctx.get("niches", niche_slug),
            text=text,
            defaults={"question_type": qtype, "order": order, "is_active": True},
        )
        for index, option_value in enumerate(options, start=1):
            option, _ = ConfiguratorOption.objects.update_or_create(
                question=question,
                value=option_value,
                defaults={"label": option_value.capitalize(), "order": index, "is_active": True},
            )
            if option_value == "sim":
                TemplateRecommendationRule.objects.update_or_create(
                    niche=ctx.get("niches", niche_slug),
                    question=question,
                    option=option,
                    recommended_template=ctx.get("site_templates", f"{niche_slug}_pro") or ctx.get("site_templates", f"{niche_slug}_premium") or ctx.get("site_templates", f"{niche_slug}_modern"),
                    defaults={"priority": 10, "is_active": True, "notes": "Bootstrap rule"},
                )

    orders = [
        ("academia-exemplo", "cliente@academia.local", "academia", "academia_modern", "in_production"),
        ("smart-control-brasil", "comercial@smart360.local", "dentista", "dentista_pro", "review"),
    ]
    for company_slug, requester_email, niche_slug, template_slug, status in orders:
        order, _ = SiteOrder.objects.update_or_create(
            company=ctx.get("companies", company_slug),
            niche=ctx.get("niches", niche_slug),
            requester=ctx.get("users", requester_email),
            defaults={
                "selected_template": ctx.get("site_templates", template_slug),
                "recommended_template": ctx.get("site_templates", template_slug),
                "status": status,
                "notes": "Bootstrap demo order",
                "final_price": ctx.get("site_templates", template_slug).base_price,
            },
        )
        ctx.put("site_orders", f"{company_slug}-{niche_slug}", order)
        SiteProjectIntake.objects.update_or_create(
            site_order=order,
            defaults={
                "company_name": order.company.name if order.company else "Empresa Demo",
                "phone": "+55 11 4000-1000",
                "whatsapp": "+55 11 98888-1111",
                "city": "Sao Paulo",
                "state": "SP",
                "business_description": "Projeto demo de site bootstrap.",
                "main_services": ["Landing page", "Formulario", "SEO basico"],
                "instagram": "https://instagram.com/demo",
                "notes": "Intake bootstrap",
            },
        )
        for question in ConfiguratorQuestion.objects.filter(niche=order.niche):
            option = question.options.filter(value="sim").first()
            SiteOrderAnswer.objects.update_or_create(
                site_order=order,
                question=question,
                defaults={"option": option, "value_text": option.label if option else ""},
            )
        for stage, assignee, idx in [
            (ProductionTask.Stage.DISCOVERY, "ops@smart360.local", 1),
            (ProductionTask.Stage.COPYWRITING, "comercial@smart360.local", 2),
            (ProductionTask.Stage.DESIGN, "engenharia@smart360.local", 3),
        ]:
            ProductionTask.objects.update_or_create(
                site_order=order,
                stage=stage,
                defaults={
                    "status": ProductionTask.Status.IN_PROGRESS if idx == 1 else ProductionTask.Status.TODO,
                    "assignee": ctx.get("users", assignee),
                    "order": idx,
                    "notes": "Bootstrap production flow",
                },
            )
        if order.status in [SiteOrder.Status.REVIEW, SiteOrder.Status.DELIVERED]:
            DeliveryRecord.objects.update_or_create(
                site_order=order,
                defaults={
                    "delivered_url": f"https://{order.company.slug}.smart360.local",
                    "acceptance_status": DeliveryRecord.AcceptanceStatus.PENDING,
                    "notes": "Bootstrap delivery record",
                },
            )


def seed_growth(ctx):
    ctx.section("Seeding growth_engine")
    sources = [
        ("Google Ads", LeadSource.SourceType.PAID),
        ("Instagram Organic", LeadSource.SourceType.SOCIAL),
        ("Indicacao Parceiro", LeadSource.SourceType.PARTNER),
    ]
    for name, source_type in sources:
        source, _ = LeadSource.objects.update_or_create(
            name=name,
            defaults={"source_type": source_type, "description": f"Bootstrap source {name}", "is_active": True},
        )
        ctx.put("lead_sources", name, source)

    for tag_name, slug in [("hot", "hot"), ("site-factory", "site-factory"), ("smart-system", "smart-system")]:
        tag, _ = LeadTag.objects.update_or_create(name=tag_name, defaults={"slug": slug})
        ctx.put("lead_tags", slug, tag)

    campaign, _ = LeadCampaign.objects.update_or_create(
        name="Campanha Academias SP",
        defaults={
            "objective": "Captar leads para Smart Site Factory e Smart System",
            "channel": LeadCampaign.Channel.GOOGLE,
            "status": LeadCampaign.Status.ACTIVE,
            "description": "Campanha bootstrap",
        },
    )
    ctx.put("lead_campaigns", "academias", campaign)

    lead_specs = [
        ("Academia Exemplo Guarulhos", "Marina", "lead-academia@demo.local", "Guarulhos", "SP", "academia", "Google Ads", 88, Lead.Status.QUALIFIED),
        ("Clinica Maua", "Carlos", "lead-clinica@demo.local", "Maua", "SP", "dentista", "Instagram Organic", 64, Lead.Status.CONTACTED),
        ("Laboratorio Campinas", "Luciana", "lead-lab@demo.local", "Campinas", "SP", "petshop", "Indicacao Parceiro", 45, Lead.Status.NEW),
    ]
    for company_name, contact_name, email, city, state, niche_slug, source_name, score, status in lead_specs:
        lead, _ = Lead.objects.update_or_create(
            email=email,
            defaults={
                "company_name": company_name,
                "contact_name": contact_name,
                "phone": "+55 11 3333-0000",
                "whatsapp": "+55 11 98888-2222",
                "city": city,
                "state": state,
                "niche": ctx.get("niches", niche_slug),
                "source": ctx.get("lead_sources", source_name),
                "campaign": campaign,
                "status": status,
                "score": score,
                "notes": "Lead bootstrap",
                "assigned_to": ctx.get("users", "comercial@smart360.local"),
                "created_by": ctx.get("users", "admin@smart360.local"),
            },
        )
        lead.tags.set([ctx.get("lead_tags", "hot")] if score >= 80 else [ctx.get("lead_tags", "site-factory")])
        LeadInteraction.objects.get_or_create(
            lead=lead,
            interaction_type=LeadInteraction.InteractionType.WHATSAPP,
            summary="Primeiro contato bootstrap via WhatsApp.",
            defaults={
                "channel": LeadInteraction.Channel.WHATSAPP,
                "owner": ctx.get("users", "comercial@smart360.local"),
            },
        )
        LeadQualification.objects.update_or_create(
            lead=lead,
            defaults={"criteria": {"budget": "ok", "timing": "30_days"}, "calculated_score": score, "notes": "Bootstrap qualification"},
        )
        LeadAssignment.objects.update_or_create(
            lead=lead,
            user=ctx.get("users", "comercial@smart360.local"),
            defaults={"status": LeadAssignment.AssignmentStatus.ACTIVE},
        )
        ctx.put("leads", email, lead)


def seed_marketplaces(ctx):
    ctx.section("Seeding market_core and caneca_de_garagem")
    vendor_specs = [
        ("caneca-garagem-factory", "Caneca de Garagem Factory", "caneca-de-garagem", "ops@smart360.local", True),
        ("lab-analitico-demo", "Lab Analitico Demo", "laboratorio-exemplo", "engenharia@smart360.local", False),
        ("smart-control-vendor", "Smart Control Vendor", "smart-control-brasil", "engenharia@smart360.local", False),
    ]
    for slug, name, company_slug, owner_email, accepts_internal in vendor_specs:
        vendor, _ = MarketplaceVendor.objects.update_or_create(
            slug=slug,
            defaults={
                "company": ctx.get("companies", company_slug),
                "owner": ctx.get("users", owner_email),
                "name": name,
                "status": MarketplaceVendor.Status.ACTIVE,
                "accepts_internal_production": accepts_internal,
                "metadata": {"bootstrap_tag": "smart360-demo"},
            },
        )
        ctx.put("vendors", slug, vendor)

    product_specs = [
        ("caneca-personalizada-casal", "Caneca Personalizada Casal", "CDG-CAN-001", "caneca-garagem-factory", Decimal("49.90")),
        ("camiseta-aniversario", "Camiseta Aniversario", "CDG-CAM-002", "caneca-garagem-factory", Decimal("69.90")),
        ("azulejo-personalizado", "Azulejo Personalizado", "CDG-AZU-003", "caneca-garagem-factory", Decimal("89.90")),
    ]
    for slug, name, sku, vendor_slug, price in product_specs:
        product, _ = MarketplaceProduct.objects.update_or_create(
            slug=slug,
            defaults={
                "vendor": ctx.get("vendors", vendor_slug),
                "name": name,
                "sku": sku,
                "description": f"Produto demo {name}",
                "base_price": price,
                "is_customizable": True,
                "is_active": True,
            },
        )
        ctx.put("products", slug, product)

    order, _ = MarketplaceOrder.objects.update_or_create(
        code="MKT-DEMO-001",
        defaults={
            "customer": ctx.get("users", "cliente@academia.local"),
            "company": ctx.get("companies", "academia-exemplo"),
            "status": MarketplaceOrder.Status.IN_PRODUCTION,
            "total_amount": Decimal("119.80"),
            "notes": "Pedido bootstrap caneca de garagem",
        },
    )
    ctx.put("market_orders", "demo_order", order)

    item1, _ = MarketplaceOrderItem.objects.update_or_create(
        order=order,
        product=ctx.get("products", "caneca-personalizada-casal"),
        defaults={"vendor": ctx.get("vendors", "caneca-garagem-factory"), "quantity": 1, "unit_price": Decimal("49.90")},
    )
    item2, _ = MarketplaceOrderItem.objects.update_or_create(
        order=order,
        product=ctx.get("products", "camiseta-aniversario"),
        defaults={"vendor": ctx.get("vendors", "caneca-garagem-factory"), "quantity": 1, "unit_price": Decimal("69.90")},
    )
    ctx.put("market_order_items", "item1", item1)
    ctx.put("market_order_items", "item2", item2)

    profile, _ = CreativeStoreProfile.objects.update_or_create(
        vendor=ctx.get("vendors", "caneca-garagem-factory"),
        defaults={
            "display_name": "Caneca de Garagem Factory",
            "bio": "Fabrica interna bootstrap para sublimação e personalizados.",
            "profile_type": CreativeStoreProfile.ProfileType.MIXED,
            "production_capabilities": ["sublimacao", "camisetas", "azulejos"],
            "is_internal_factory": True,
            "lead_time_days": 3,
        },
    )
    ctx.put("creative_profiles", "internal_factory", profile)

    for product_slug in ["caneca-personalizada-casal", "camiseta-aniversario", "azulejo-personalizado"]:
        template, _ = CustomizationTemplate.objects.update_or_create(
            product=ctx.get("products", product_slug),
            template_name=f"Template {product_slug}",
            defaults={
                "instructions": "Enviar nome, data e arte de referencia.",
                "allowed_text_fields": ["nome", "data", "mensagem"],
                "allowed_image_upload": True,
                "max_images": 2,
                "is_active": True,
            },
        )
        ctx.put("customization_templates", product_slug, template)

    customization_request, _ = CustomizationRequest.objects.update_or_create(
        order_item=item1,
        defaults={
            "customization_template": ctx.get("customization_templates", "caneca-personalizada-casal"),
            "customer_text": {"nome": "Marina e Leo", "mensagem": "Feliz aniversario"},
            "uploaded_assets": [{"placeholder": True, "file_name": "arte-casal.txt"}],
            "font_choice": "Montserrat",
            "color_choice": "Preto",
            "extra_notes": "Usar layout romantico.",
            "approval_status": CustomizationRequest.ApprovalStatus.APPROVED,
        },
    )
    ctx.put("customization_requests", "main", customization_request)
    if not customization_request.artwork_assets.exists():
        asset = ArtworkAsset(
            customization_request=customization_request,
            original_name="arte-casal.txt",
            asset_type=ArtworkAsset.AssetType.OTHER,
            status=ArtworkAsset.Status.VALIDATED,
        )
        attach_content_file(asset, "file", "arte-casal.txt", "Placeholder art asset for bootstrap demo.")

    production_job, _ = ProductionJob.objects.update_or_create(
        order_item=item1,
        job_type=ProductionJob.JobType.SUBLIMATION,
        defaults={
            "order": order,
            "vendor": ctx.get("vendors", "caneca-garagem-factory"),
            "internal_factory": profile,
            "status": ProductionJob.Status.IN_PROGRESS,
            "queue_position": 1,
            "assigned_to": ctx.get("users", "ops@smart360.local"),
            "due_date": timezone.now().date(),
            "notes": "Job bootstrap em execucao.",
        },
    )
    for idx, step_name in enumerate(["Preparar arte", "Sublimar", "Embalar"], start=1):
        ProductionStep.objects.update_or_create(
            production_job=production_job,
            step_name=step_name,
            defaults={"ordering": idx, "status": ProductionStep.Status.DONE if idx == 1 else ProductionStep.Status.PENDING},
        )
    ShipmentPreparation.objects.update_or_create(
        order=order,
        defaults={
            "shipping_status": ShipmentPreparation.ShippingStatus.READY,
            "carrier": "Correios",
            "tracking_code": "BR123456789",
            "notes": "Envio bootstrap pronto.",
        },
    )

