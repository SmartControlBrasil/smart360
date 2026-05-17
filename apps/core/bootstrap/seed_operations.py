from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from django.utils import timezone

from apps.knowledge_engine.models import (
    CauseReference,
    EquipmentReference,
    EquipmentSymptomMap,
    FailureActionMap,
    FailureCauseMap,
    FailureReference,
    KnowledgeCategory,
    KnowledgeFeedback,
    KnowledgeLinkRule,
    KnowledgeTag,
    RecommendedAction,
    SymptomFailureMap,
    SymptomReference,
    TechnicalDocument,
    TroubleshootingArticle,
)
from apps.marketplace_analytical.models import (
    AnalyticalAssignment,
    AnalyticalMatchingRecord,
    AnalyticalProvider,
    AnalyticalReport,
    AnalyticalRequest,
    AnalyticalReview,
    AnalyticalService,
    AnalyticalServiceCapability,
    AnalyticalServiceCategory,
    AnalyticalServiceRegion,
)
from apps.marketplace_technicians.models import (
    ServiceRegion,
    TechnicianAssignment,
    TechnicianAvailability,
    TechnicianCompensationRecord,
    TechnicianMatchingRecord,
    TechnicianPortfolioItem,
    TechnicianProfile,
    TechnicianReview,
    TechnicianServiceRegion,
    TechnicianServiceRequest,
    TechnicianSkill,
    TechnicianSkillAssignment,
    TechnicianWorkReport,
)
from apps.companies.models import SiteMembership
from apps.smart_system.models import (
    Asset,
    AssetCategory,
    AssetHistoryEvent,
    Checklist,
    ChecklistItem,
    FailureEvent,
    MaintenanceClient,
    MaintenancePlan,
    OperationalSite,
    ServiceDocument,
    ServiceOrder,
    ServiceOrderChecklistResponse,
    WorkLog,
)
from apps.core.bootstrap.common import attach_content_file


def seed_smart_system(ctx):
    ctx.section("Seeding smart_system")
    client, _ = MaintenanceClient.objects.update_or_create(
        display_name="Academia Exemplo",
        defaults={
            "company": ctx.get("companies", "academia-exemplo"),
            "legal_name": "Academia Exemplo Fitness LTDA",
            "document_number": "12.345.678/0001-90",
            "contact_name": "Cliente Academia",
            "contact_email": "cliente@academia.local",
            "contact_phone": "+55 11 4000-2000",
            "is_active": True,
            "notes": "Cliente bootstrap",
        },
    )
    ctx.put("maintenance_clients", "academia", client)
    site, _ = OperationalSite.objects.update_or_create(
        maintenance_client=client,
        name="Unidade Centro",
        defaults={
            "code": "CTR-001",
            "address_line": "Rua Central, 100",
            "city": "Sao Paulo",
            "state": "SP",
            "zip_code": "01000-000",
            "contact_name": "Gerente Centro",
            "contact_phone": "+55 11 4000-2001",
            "is_active": True,
        },
    )
    ctx.put("sites", "academia-centro", site)
    north_site, _ = OperationalSite.objects.update_or_create(
        maintenance_client=client,
        name="Unidade Norte",
        defaults={
            "code": "NRT-002",
            "address_line": "Avenida Norte, 220",
            "city": "Guarulhos",
            "state": "SP",
            "zip_code": "07000-000",
            "contact_name": "Gerente Norte",
            "contact_phone": "+55 11 4000-2002",
            "is_active": True,
        },
    )
    ctx.put("sites", "academia-norte", north_site)

    panobianco_client, _ = MaintenanceClient.objects.update_or_create(
        display_name="Panobianco",
        defaults={
            "company": ctx.get("companies", "panobianco"),
            "legal_name": "Panobianco Operacoes Fitness LTDA",
            "document_number": "23.456.789/0001-10",
            "contact_name": "Operacoes Panobianco",
            "contact_email": "ops@panobianco.local",
            "contact_phone": "+55 11 4000-3000",
            "is_active": True,
            "notes": "Cliente multisite bootstrap",
        },
    )
    ctx.put("maintenance_clients", "panobianco", panobianco_client)
    panobianco_cumbica, _ = OperationalSite.objects.update_or_create(
        maintenance_client=panobianco_client,
        name="Panobianco Cumbica",
        defaults={
            "code": "PAN-CMB",
            "address_line": "Rodovia Helio Smidt, 500",
            "city": "Guarulhos",
            "state": "SP",
            "zip_code": "07190-100",
            "contact_name": "Supervisor Cumbica",
            "contact_phone": "+55 11 4000-3001",
            "is_active": True,
        },
    )
    ctx.put("sites", "panobianco-cumbica", panobianco_cumbica)
    panobianco_centro, _ = OperationalSite.objects.update_or_create(
        maintenance_client=panobianco_client,
        name="Panobianco Centro",
        defaults={
            "code": "PAN-CTR",
            "address_line": "Rua Central, 845",
            "city": "Sao Paulo",
            "state": "SP",
            "zip_code": "01010-100",
            "contact_name": "Supervisor Centro",
            "contact_phone": "+55 11 4000-3002",
            "is_active": True,
        },
    )
    ctx.put("sites", "panobianco-centro", panobianco_centro)

    industrial_client, _ = MaintenanceClient.objects.update_or_create(
        display_name="Cliente Demo Industrial",
        defaults={
            "company": ctx.get("companies", "smart-control-brasil"),
            "legal_name": "Cliente Demo Industrial LTDA",
            "document_number": "44.555.666/0001-88",
            "contact_name": "Gerencia Industrial",
            "contact_email": "industrial@cliente-demo.local",
            "contact_phone": "+55 11 4000-4000",
            "is_active": True,
            "notes": "Cliente industrial bootstrap",
        },
    )
    ctx.put("maintenance_clients", "industrial", industrial_client)
    demo_plant_a, _ = OperationalSite.objects.update_or_create(
        maintenance_client=industrial_client,
        name="Demo Plant A",
        defaults={
            "code": "DPA-001",
            "address_line": "Avenida Industrial, 1000",
            "city": "Maua",
            "state": "SP",
            "zip_code": "09300-100",
            "contact_name": "Coordenador Plant A",
            "contact_phone": "+55 11 4000-4001",
            "is_active": True,
        },
    )
    ctx.put("sites", "demo-plant-a", demo_plant_a)
    demo_plant_b, _ = OperationalSite.objects.update_or_create(
        maintenance_client=industrial_client,
        name="Demo Plant B",
        defaults={
            "code": "DPB-002",
            "address_line": "Avenida Industrial, 2000",
            "city": "Santo Andre",
            "state": "SP",
            "zip_code": "09100-200",
            "contact_name": "Coordenador Plant B",
            "contact_phone": "+55 11 4000-4002",
            "is_active": True,
        },
    )
    ctx.put("sites", "demo-plant-b", demo_plant_b)
    category, _ = AssetCategory.objects.update_or_create(
        name="Esteiras",
        defaults={"description": "Equipamentos cardiovasculares", "is_active": True},
    )
    ctx.put("asset_categories", "esteiras", category)
    asset, _ = Asset.objects.update_or_create(
        asset_tag="EST-RT250-001",
        defaults={
            "operational_site": site,
            "category": category,
            "name": "Esteira RT250",
            "manufacturer": "RunnerTech",
            "model": "RT250",
            "serial_number": "RT250-SN-001",
            "status": Asset.Status.OPERATING,
            "criticality": Asset.Criticality.HIGH,
            "is_active": True,
            "notes": "Ativo bootstrap principal",
        },
    )
    ctx.put("assets", "esteira_rt250", asset)
    secondary_asset_specs = [
        ("HVAC-ACADEMIA-02", "HVAC Academia 02", north_site, category, Asset.Criticality.MEDIUM),
        ("CHILLER-UNID-A", "Chiller Unidade A", panobianco_cumbica, category, Asset.Criticality.HIGH),
        ("COMP-AR-01", "Compressor de Ar 01", demo_plant_a, category, Asset.Criticality.HIGH),
    ]
    for asset_tag, name, scoped_site, scoped_category, criticality in secondary_asset_specs:
        extra_asset, _ = Asset.objects.update_or_create(
            asset_tag=asset_tag,
            defaults={
                "operational_site": scoped_site,
                "category": scoped_category,
                "name": name,
                "manufacturer": "SMART360",
                "model": "Bootstrap",
                "serial_number": f"{asset_tag}-SN",
                "status": Asset.Status.OPERATING,
                "criticality": criticality,
                "is_active": True,
                "notes": "Ativo multisite bootstrap",
            },
        )
        ctx.put("assets", asset_tag.lower().replace("-", "_"), extra_asset)
    checklist, _ = Checklist.objects.update_or_create(
        name="Checklist Preventiva Esteira RT250",
        defaults={"description": "Inspecao basica preventiva", "is_active": True},
    )
    for idx, title in enumerate(["Verificar correia", "Testar painel", "Limpar motor"], start=1):
        ChecklistItem.objects.update_or_create(
            checklist=checklist,
            title=title,
            defaults={"item_type": ChecklistItem.ItemType.BOOLEAN, "ordering": idx, "is_required": True, "is_active": True},
        )
    plan, _ = MaintenancePlan.objects.update_or_create(
        asset=asset,
        name="Preventiva Mensal Esteira",
        defaults={
            "description": "Preventiva mensal da esteira RT250",
            "frequency_type": MaintenancePlan.FrequencyType.MONTHLY,
            "frequency_value": 1,
            "estimated_duration_minutes": 90,
            "checklist": checklist,
            "is_active": True,
            "next_due_date": timezone.now().date(),
        },
    )
    ctx.put("maintenance_plans", "esteira_monthly", plan)
    preventive, _ = ServiceOrder.objects.update_or_create(
        order_number="SO-DEMO-001",
        defaults={
            "client": client,
            "operational_site": site,
            "asset": asset,
            "maintenance_plan": plan,
            "maintenance_type": ServiceOrder.MaintenanceType.PREVENTIVE,
            "priority": ServiceOrder.Priority.MEDIUM,
            "status": ServiceOrder.Status.SCHEDULED,
            "source": ServiceOrder.Source.PLAN,
            "title": "Preventiva mensal da Esteira RT250",
            "description": "OS preventiva criada pelo bootstrap.",
            "scheduled_start": timezone.now(),
            "scheduled_end": timezone.now() + timedelta(hours=2),
            "requested_by": "Sistema",
            "assigned_to": ctx.get("users", "engenharia@smart360.local"),
            "created_by": ctx.get("users", "admin@smart360.local"),
        },
    )
    corrective, _ = ServiceOrder.objects.update_or_create(
        order_number="SO-DEMO-002",
        defaults={
            "client": client,
            "operational_site": site,
            "asset": asset,
            "maintenance_type": ServiceOrder.MaintenanceType.CORRECTIVE,
            "priority": ServiceOrder.Priority.HIGH,
            "status": ServiceOrder.Status.IN_PROGRESS,
            "source": ServiceOrder.Source.FAILURE,
            "title": "Correção de falha de partida",
            "description": "Motor nao parte ao ligar.",
            "requested_by": "Gerente Unidade Centro",
            "assigned_to": ctx.get("users", "engenharia@smart360.local"),
            "created_by": ctx.get("users", "ops@smart360.local"),
        },
    )
    ctx.put("service_orders", "preventive", preventive)
    ctx.put("service_orders", "corrective", corrective)
    for item in checklist.items.all():
        ServiceOrderChecklistResponse.objects.update_or_create(
            service_order=preventive,
            checklist_item=item,
            defaults={"response_boolean": True, "notes": "Bootstrap response"},
        )
    failure, _ = FailureEvent.objects.update_or_create(
        asset=asset,
        service_order=corrective,
        symptom="Motor nao parte",
        defaults={
            "probable_cause": "Capacitor comprometido",
            "root_cause": "Capacitor de partida defeituoso",
            "severity": FailureEvent.Severity.HIGH,
            "downtime_minutes": 120,
            "status": FailureEvent.Status.ANALYZING,
            "notes": "Falha bootstrap",
        },
    )
    for event_type, title, related_so, related_failure in [
        (AssetHistoryEvent.EventType.SERVICE_ORDER_CREATED, "OS preventiva criada", preventive, None),
        (AssetHistoryEvent.EventType.FAILURE_REPORTED, "Falha reportada", corrective, failure),
    ]:
        AssetHistoryEvent.objects.update_or_create(
            asset=asset,
            title=title,
            defaults={
                "event_type": event_type,
                "description": "Historico bootstrap",
                "related_service_order": related_so,
                "related_failure_event": related_failure,
                "created_by": ctx.get("users", "engenharia@smart360.local"),
            },
        )
    WorkLog.objects.update_or_create(
        service_order=corrective,
        user=ctx.get("users", "engenharia@smart360.local"),
        defaults={
            "started_at": timezone.now() - timedelta(hours=1),
            "ended_at": timezone.now(),
            "labor_minutes": 60,
            "notes": "Diagnostico inicial bootstrap",
        },
    )
    document = ServiceDocument(
        service_order=corrective,
        document_type=ServiceDocument.DocumentType.REPORT,
        title="Relatorio inicial da OS corretiva",
        uploaded_by=ctx.get("users", "engenharia@smart360.local"),
    )
    attach_content_file(document, "file", "os-corretiva-relatorio.txt", "Relatorio tecnico bootstrap da OS corretiva.")

    site_membership_specs = [
        ("ops@smart360.local", "academia-exemplo", "academia-centro", True),
        ("ops@smart360.local", "panobianco", "panobianco-cumbica", False),
        ("engenharia@smart360.local", "academia-exemplo", "academia-centro", True),
        ("engenharia@smart360.local", "academia-exemplo", "academia-norte", False),
        ("engenharia@smart360.local", "panobianco", "panobianco-centro", False),
        ("engenharia@smart360.local", "smart-control-brasil", "demo-plant-a", False),
        ("cliente@academia.local", "academia-exemplo", "academia-centro", True),
    ]
    for user_email, company_slug, site_key, is_primary in site_membership_specs:
        SiteMembership.objects.update_or_create(
            user=ctx.get("users", user_email),
            site=ctx.get("sites", site_key),
            defaults={
                "company": ctx.get("companies", company_slug),
                "status": SiteMembership.Status.ACTIVE,
                "is_primary": is_primary,
                "metadata": {"source": "bootstrap"},
            },
        )


def seed_marketplace_technicians(ctx):
    ctx.section("Seeding marketplace_technicians")
    skill_specs = ["Tecnico de esteira", "Tecnico de ar-condicionado", "Tecnico de automacao"]
    for name in skill_specs:
        skill, _ = TechnicianSkill.objects.update_or_create(name=name, defaults={"description": f"{name} bootstrap", "is_active": True})
        ctx.put("technician_skills", name, skill)

    for email, display_name, status in [
        ("engenharia@smart360.local", "Engenharia Team", TechnicianProfile.VerificationStatus.APPROVED),
        ("ops@smart360.local", "Ops Field", TechnicianProfile.VerificationStatus.PENDING),
    ]:
        user = ctx.get("users", email)
        profile, _ = TechnicianProfile.objects.update_or_create(
            user=user,
            defaults={
                "display_name": display_name,
                "phone": user.phone_number,
                "whatsapp": user.phone_number,
                "email": user.email,
                "bio": "Perfil tecnico bootstrap",
                "profile_type": TechnicianProfile.ProfileType.INTERNAL,
                "experience_years": 6,
                "verification_status": status,
                "marketplace_status": TechnicianProfile.MarketplaceStatus.AVAILABLE,
                "rating_average": Decimal("4.80"),
                "completed_jobs_count": 12,
                "is_active": True,
                "trust_case_reference": "trust-placeholder",
            },
        )
        ctx.put("technician_profiles", email, profile)

    region, _ = ServiceRegion.objects.update_or_create(
        name="Sao Paulo Capital",
        state="SP",
        city="Sao Paulo",
        region_type=ServiceRegion.RegionType.CITY,
        defaults={"is_active": True},
    )
    ctx.put("service_regions", "sp-capital", region)
    profile = ctx.get("technician_profiles", "engenharia@smart360.local")
    TechnicianSkillAssignment.objects.update_or_create(
        technician_profile=profile,
        skill=ctx.get("technician_skills", "Tecnico de esteira"),
        defaults={"proficiency_level": TechnicianSkillAssignment.ProficiencyLevel.SPECIALIST, "years_experience": 8},
    )
    TechnicianServiceRegion.objects.update_or_create(
        technician_profile=profile,
        service_region=region,
        defaults={"coverage_type": TechnicianServiceRegion.CoverageType.LOCAL},
    )
    TechnicianAvailability.objects.update_or_create(
        technician_profile=profile,
        weekday=TechnicianAvailability.Weekday.MONDAY,
        start_time="08:00",
        end_time="18:00",
        defaults={"is_available": True, "notes": "Janela bootstrap"},
    )
    TechnicianPortfolioItem.objects.update_or_create(
        technician_profile=profile,
        title="Reparo de esteira de alta performance",
        defaults={"description": "Portfolio bootstrap", "media_url": "https://example.com/portfolio/esteira", "is_active": True, "ordering": 1},
    )
    request, _ = TechnicianServiceRequest.objects.update_or_create(
        title="Atendimento corretivo esteira RT250",
        related_service_order=ctx.get("service_orders", "corrective"),
        defaults={
            "requester_user": ctx.get("users", "ops@smart360.local"),
            "requester_company": ctx.get("companies", "academia-exemplo"),
            "description": "Esteira nao parte e academia precisa urgencia.",
            "service_type": TechnicianServiceRequest.ServiceType.MAINTENANCE,
            "priority": TechnicianServiceRequest.Priority.HIGH,
            "requested_date": timezone.now(),
            "city": "Sao Paulo",
            "state": "SP",
            "address_line": "Rua Central, 100",
            "status": TechnicianServiceRequest.Status.ASSIGNED,
            "origin": TechnicianServiceRequest.Origin.SMART_SYSTEM,
            "related_client": ctx.get("maintenance_clients", "academia"),
            "related_site": ctx.get("sites", "academia-centro"),
            "related_asset": ctx.get("assets", "esteira_rt250"),
        },
    )
    match, _ = TechnicianMatchingRecord.objects.update_or_create(
        technician_service_request=request,
        technician_profile=profile,
        defaults={"match_score": Decimal("94.50"), "match_reason": "Skill + region", "status": TechnicianMatchingRecord.Status.ACCEPTED},
    )
    assignment, _ = TechnicianAssignment.objects.update_or_create(
        technician_service_request=request,
        technician_profile=profile,
        defaults={
            "assignment_status": TechnicianAssignment.AssignmentStatus.IN_PROGRESS,
            "accepted_at": timezone.now(),
            "started_at": timezone.now(),
            "notes": "Bootstrap technician assignment",
        },
    )
    TechnicianWorkReport.objects.update_or_create(
        technician_assignment=assignment,
        defaults={
            "summary": "Diagnostico inicial concluido",
            "execution_notes": "Capacitor de partida com desgaste.",
            "started_at": timezone.now() - timedelta(hours=1),
            "ended_at": timezone.now(),
            "labor_minutes": 60,
            "materials_used": ["Multimetro", "Capacitor 120uF"],
            "next_recommendation": "Trocar capacitor e revisar painel.",
        },
    )
    TechnicianReview.objects.update_or_create(
        technician_profile=profile,
        assignment=assignment,
        defaults={
            "reviewer_user": ctx.get("users", "cliente@academia.local"),
            "reviewer_company": ctx.get("companies", "academia-exemplo"),
            "rating": 5,
            "comment": "Atendimento tecnico excelente.",
            "status": TechnicianReview.Status.PUBLISHED,
        },
    )
    TechnicianCompensationRecord.objects.update_or_create(
        technician_assignment=assignment,
        defaults={"gross_amount": Decimal("280.00"), "platform_fee": Decimal("28.00"), "net_amount": Decimal("252.00"), "status": TechnicianCompensationRecord.Status.APPROVED},
    )


def seed_marketplace_analytical(ctx):
    ctx.section("Seeding marketplace_analytical")
    category_specs = [
        ("Analise de Vibracao", "Analise de vibracao"),
        ("Termografia", "Inspecoes termograficas"),
        ("Analise de Oleo", "Analise laboratorial de oleo"),
    ]
    for name, description in category_specs:
        category, _ = AnalyticalServiceCategory.objects.update_or_create(
            name=name,
            defaults={"description": description, "is_active": True},
        )
        ctx.put("analytical_categories", name, category)
    provider, _ = AnalyticalProvider.objects.update_or_create(
        display_name="Laboratorio Exemplo",
        defaults={
            "company": ctx.get("companies", "laboratorio-exemplo"),
            "user": ctx.get("users", "engenharia@smart360.local"),
            "legal_name": "Laboratorio Exemplo Diagnosticos LTDA",
            "contact_email": "contato@laboratorioexemplo.local",
            "contact_phone": "+55 11 4000-3000",
            "description": "Provider bootstrap de analises tecnicas.",
            "provider_type": AnalyticalProvider.ProviderType.LABORATORY,
            "verification_status": AnalyticalProvider.VerificationStatus.APPROVED,
            "marketplace_status": AnalyticalProvider.MarketplaceStatus.AVAILABLE,
            "rating_average": Decimal("4.70"),
            "completed_jobs_count": 24,
            "is_active": True,
            "trust_case_reference": "trust-placeholder",
        },
    )
    ctx.put("analytical_providers", "lab", provider)
    service, _ = AnalyticalService.objects.update_or_create(
        provider=provider,
        title="Analise de Vibracao Industrial",
        defaults={
            "category": ctx.get("analytical_categories", "Analise de Vibracao"),
            "description": "Servico bootstrap para maquinas rotativas.",
            "service_type": AnalyticalService.ServiceType.ANALYSIS,
            "delivery_type": AnalyticalService.DeliveryType.ON_SITE,
            "estimated_turnaround_days": 3,
            "price_model": AnalyticalService.PriceModel.FIXED,
            "base_price": Decimal("1800.00"),
            "currency": "BRL",
            "is_active": True,
        },
    )
    AnalyticalServiceCapability.objects.update_or_create(
        analytical_service=service,
        capability_name="Analise espectral",
        defaults={"description": "Capability bootstrap"},
    )
    AnalyticalServiceRegion.objects.update_or_create(
        analytical_service=service,
        region_name="Grande Sao Paulo",
        defaults={"state": "SP", "country": "Brazil", "coverage_type": AnalyticalServiceRegion.CoverageType.REGIONAL},
    )
    request, _ = AnalyticalRequest.objects.update_or_create(
        title="Diagnostico de vibracao da esteira RT250",
        related_service_order=ctx.get("service_orders", "corrective"),
        defaults={
            "requester_user": ctx.get("users", "engenharia@smart360.local"),
            "requester_company": ctx.get("companies", "academia-exemplo"),
            "description": "Solicitacao bootstrap para avaliacao de vibracao e falha.",
            "category": ctx.get("analytical_categories", "Analise de Vibracao"),
            "priority": AnalyticalRequest.Priority.HIGH,
            "related_asset": ctx.get("assets", "esteira_rt250"),
            "related_site": ctx.get("sites", "academia-centro"),
            "city": "Sao Paulo",
            "state": "SP",
            "status": AnalyticalRequest.Status.ASSIGNED,
            "origin": AnalyticalRequest.Origin.SMART_SYSTEM,
        },
    )
    match, _ = AnalyticalMatchingRecord.objects.update_or_create(
        analytical_request=request,
        provider=provider,
        defaults={"match_score": Decimal("91.00"), "match_reason": "Categoria + cobertura", "status": AnalyticalMatchingRecord.Status.ACCEPTED},
    )
    assignment, _ = AnalyticalAssignment.objects.update_or_create(
        analytical_request=request,
        provider=provider,
        defaults={"status": AnalyticalAssignment.Status.IN_PROGRESS, "accepted_at": timezone.now(), "started_at": timezone.now()},
    )
    report, _ = AnalyticalReport.objects.get_or_create(
        analytical_assignment=assignment,
        defaults={
            "title": "Laudo tecnico de vibracao RT250",
            "summary": "Resumo bootstrap do laudo",
            "technical_conclusion": "Desbalanceamento e desgaste em componente de partida.",
            "recommendations": "Substituir componente e monitorar vibracao.",
        },
    )
    attach_content_file(report, "report_file", "laudo-vibracao.txt", "Laudo tecnico bootstrap.")
    AnalyticalReview.objects.update_or_create(
        analytical_assignment=assignment,
        reviewer_company=ctx.get("companies", "academia-exemplo"),
        defaults={"reviewer_user": ctx.get("users", "cliente@academia.local"), "rating": 5, "comment": "Relatorio claro e objetivo."},
    )


def seed_knowledge(ctx):
    ctx.section("Seeding knowledge_engine")
    cat_equipment, _ = KnowledgeCategory.objects.update_or_create(
        name="Equipamentos",
        parent=None,
        defaults={"description": "Catalogo tecnico de equipamentos", "ordering": 1, "is_active": True},
    )
    cat_failures, _ = KnowledgeCategory.objects.update_or_create(
        name="Falhas",
        parent=None,
        defaults={"description": "Base de falhas conhecidas", "ordering": 2, "is_active": True},
    )
    cat_troubleshooting, _ = KnowledgeCategory.objects.update_or_create(
        name="Troubleshooting",
        parent=None,
        defaults={"description": "Procedimentos e artigos tecnicos", "ordering": 3, "is_active": True},
    )
    equipment, _ = EquipmentReference.objects.update_or_create(
        name="Esteira RT250",
        model="RT250",
        defaults={"manufacturer": "RunnerTech", "equipment_type": "esteira", "description": "Equipamento bootstrap", "is_active": True},
    )
    symptom, _ = SymptomReference.objects.update_or_create(
        name="Motor nao parte",
        defaults={"description": "Acionamento nao inicia", "severity_level": SymptomReference.SeverityLevel.HIGH, "is_active": True},
    )
    failure, _ = FailureReference.objects.update_or_create(
        name="Capacitor defeituoso",
        defaults={"description": "Capacitor de partida danificado", "failure_code": "FAIL-CAP-001", "criticality": FailureReference.Criticality.HIGH, "is_active": True},
    )
    cause, _ = CauseReference.objects.update_or_create(
        name="Desgaste eletrico do capacitor",
        defaults={"description": "Componente perdeu capacitancia", "cause_type": CauseReference.CauseType.ELECTRICAL, "is_active": True},
    )
    action, _ = RecommendedAction.objects.update_or_create(
        title="Substituir componente",
        defaults={"description": "Trocar capacitor por equivalente homologado", "action_type": RecommendedAction.ActionType.REPLACEMENT, "priority": RecommendedAction.Priority.HIGH, "is_active": True},
    )
    article, _ = TroubleshootingArticle.objects.update_or_create(
        title="Falha de partida na Esteira RT250",
        defaults={
            "category": cat_troubleshooting,
            "summary": "Resumo bootstrap do troubleshooting",
            "content": "Inspecione alimentacao, capacitor e painel.",
            "status": TroubleshootingArticle.Status.PUBLISHED,
            "created_by": ctx.get("users", "engenharia@smart360.local"),
            "reviewed_by": ctx.get("users", "admin@smart360.local"),
            "is_active": True,
        },
    )
    document, _ = TechnicalDocument.objects.get_or_create(
        title="Manual de Servico RT250",
        defaults={
            "document_type": TechnicalDocument.DocumentType.SERVICE_MANUAL,
            "category": cat_equipment,
            "equipment_reference": equipment,
            "manufacturer": "RunnerTech",
            "version": "1.0",
            "summary": "Manual tecnico bootstrap",
            "status": TechnicalDocument.Status.PUBLISHED,
            "is_active": True,
            "created_by": ctx.get("users", "engenharia@smart360.local"),
        },
    )
    attach_content_file(document, "file", "manual-rt250.txt", "Manual tecnico bootstrap da RT250.")
    tag, _ = KnowledgeTag.objects.update_or_create(name="manutencao", defaults={"description": "Tag bootstrap"})
    EquipmentSymptomMap.objects.get_or_create(equipment_reference=equipment, symptom_reference=symptom, defaults={"confidence_level": 90, "notes": "Bootstrap relation"})
    SymptomFailureMap.objects.get_or_create(symptom_reference=symptom, failure_reference=failure, defaults={"confidence_level": 88, "notes": "Bootstrap relation"})
    FailureCauseMap.objects.get_or_create(failure_reference=failure, cause_reference=cause, defaults={"confidence_level": 92, "notes": "Bootstrap relation"})
    FailureActionMap.objects.get_or_create(failure_reference=failure, recommended_action=action, defaults={"priority": 1, "notes": "Bootstrap relation"})
    KnowledgeLinkRule.objects.get_or_create(
        source_type=KnowledgeLinkRule.ItemType.SYMPTOM,
        source_id=symptom.id,
        target_type=KnowledgeLinkRule.ItemType.FAILURE,
        target_id=failure.id,
        relation_type=KnowledgeLinkRule.RelationType.SYMPTOM_INDICATES_FAILURE,
        defaults={"notes": "Bootstrap graph edge"},
    )
    KnowledgeFeedback.objects.update_or_create(
        user=ctx.get("users", "engenharia@smart360.local"),
        item_type="article",
        item_id=str(article.id),
        defaults={"usefulness_rating": 5, "comment": "Conteudo util para diagnostico inicial."},
    )
