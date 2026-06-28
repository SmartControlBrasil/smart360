from datetime import datetime, time, timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify

from apps.companies.models import Company, Membership, SiteMembership
from apps.marketplace_technicians.models import TechnicianProfile
from apps.smart_system.models import (
    Asset,
    AssetCategory,
    AssetHistoryEvent,
    FailureEvent,
    MaintenanceClient,
    OperationalSite,
    ScheduledVisit,
    ServiceOrder,
    TechnicianAvailabilityWindow,
    TechnicianSchedule,
)


SEED_KEY = "operational_pilot"
DEFAULT_COMPANY_NAME = "Empresa Piloto Smart360"
DEFAULT_SITE_NAME = "Unidade Piloto Operacional"
SITE_CODE = "OPS-PILOT-001"
ASSET_TAG_PREFIX = "OPS-PILOT"
ORDER_PREFIX = "OPS-PILOT-OS"
TECH_EMAILS = ["tecnico.piloto.1@smart360.local", "tecnico.piloto.2@smart360.local"]


class Command(BaseCommand):
    help = "Cria dados mínimos idempotentes para validar o piloto operacional dos agentes."

    def add_arguments(self, parser):
        parser.add_argument("--company-name", default=DEFAULT_COMPANY_NAME)
        parser.add_argument("--site-name", default=DEFAULT_SITE_NAME)
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Remove apenas registros identificáveis do seed operacional e encerra sem recriar os dados.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        company_name = options["company_name"]
        site_name = options["site_name"]
        company_slug = slugify(company_name) or "empresa-piloto-smart360"

        if options["reset"]:
            self._reset_seed(company_slug=company_slug, site_name=site_name)
            return

        company, _ = Company.objects.update_or_create(
            slug=company_slug,
            defaults={
                "name": company_name,
                "legal_name": company_name,
                "email": "operacional.piloto@smart360.local",
                "phone_number": "+55 11 4000-3600",
                "city": "São Paulo",
                "state": "SP",
                "status": Company.Status.ACTIVE,
                "metadata": {"seed_key": SEED_KEY, "pilot": "operational_agents"},
            },
        )
        client, _ = MaintenanceClient.objects.update_or_create(
            company=company,
            display_name=company_name,
            defaults={
                "legal_name": company_name,
                "contact_name": "Operação Piloto",
                "contact_email": "operacional.piloto@smart360.local",
                "contact_phone": "+55 11 4000-3600",
                "is_active": True,
                "notes": "Cliente criado pelo seed do piloto operacional Smart360.",
            },
        )
        site, _ = OperationalSite.objects.update_or_create(
            maintenance_client=client,
            name=site_name,
            defaults={
                "code": SITE_CODE,
                "address_line": "Av. Piloto Operacional, 630",
                "city": "São Paulo",
                "state": "SP",
                "contact_name": "Coordenação Piloto",
                "contact_phone": "+55 11 4000-3630",
                "is_active": True,
                "notes": "Unidade criada pelo seed do piloto operacional Smart360.",
            },
        )

        categories = self._seed_categories()
        assets = self._seed_assets(site=site, categories=categories)
        technicians, profiles = self._seed_technicians(company=company, site=site)
        service_orders = self._seed_service_orders(client=client, site=site, assets=assets, technicians=technicians)
        failures = self._seed_failures(assets=assets, service_orders=service_orders)
        schedules, visits = self._seed_schedule(company=company, site=site, assets=assets, technicians=technicians, profiles=profiles, service_orders=service_orders)

        self.stdout.write(self.style.SUCCESS("Seed operacional do piloto concluído."))
        self.stdout.write(f"company={company.id} {company.name}")
        self.stdout.write(f"client={client.id} {client.display_name}")
        self.stdout.write(f"site={site.id} {site.name}")
        self.stdout.write(
            "counts "
            f"assets={len(assets)} technicians={len(technicians)} "
            f"service_orders={len(service_orders)} failures={len(failures)} "
            f"schedules={len(schedules)} visits={len(visits)}"
        )

    def _seed_categories(self):
        payload = [
            ("Climatização Piloto", "climatizacao-piloto"),
            ("Energia Crítica Piloto", "energia-critica-piloto"),
            ("Utilidades Piloto", "utilidades-piloto"),
        ]
        categories = {}
        for name, slug in payload:
            category, _ = AssetCategory.objects.update_or_create(
                slug=slug,
                defaults={"name": name, "description": "Categoria criada para o seed do piloto operacional.", "is_active": True},
            )
            categories[slug] = category
        return categories

    def _seed_assets(self, *, site, categories):
        today = timezone.localdate()
        payload = [
            ("001", "Chiller principal", "climatizacao-piloto", Asset.Criticality.CRITICAL, Asset.Status.OPERATING),
            ("002", "Quadro elétrico QGBT", "energia-critica-piloto", Asset.Criticality.HIGH, Asset.Status.OPERATING),
            ("003", "Bomba de recalque 1", "utilidades-piloto", Asset.Criticality.HIGH, Asset.Status.MAINTENANCE),
            ("004", "Split sala técnica", "climatizacao-piloto", Asset.Criticality.MEDIUM, Asset.Status.OPERATING),
            ("005", "Nobreak supervisório", "energia-critica-piloto", Asset.Criticality.CRITICAL, Asset.Status.OPERATING),
        ]
        assets = []
        for suffix, name, category_slug, criticality, status in payload:
            asset, _ = Asset.objects.update_or_create(
                asset_tag=f"{ASSET_TAG_PREFIX}-{suffix}",
                defaults={
                    "operational_site": site,
                    "category": categories[category_slug],
                    "name": name,
                    "manufacturer": "Smart Control Brasil",
                    "model": f"PILOT-{suffix}",
                    "serial_number": f"SCB-PILOT-{suffix}",
                    "installation_date": today - timedelta(days=900 - int(suffix) * 30),
                    "status": status,
                    "criticality": criticality,
                    "is_active": True,
                    "notes": "Ativo criado pelo seed do piloto operacional Smart360.",
                    "metadata": {"seed_key": SEED_KEY, "pilot": "operational_agents"},
                },
            )
            assets.append(asset)
        return assets

    def _seed_technicians(self, *, company, site):
        user_model = get_user_model()
        technicians = []
        profiles = []
        names = [("Técnico", "Piloto Um"), ("Técnica", "Piloto Dois")]
        for index, email in enumerate(TECH_EMAILS, start=1):
            first_name, last_name = names[index - 1]
            user, created = user_model.objects.update_or_create(
                email=email,
                defaults={
                    "first_name": first_name,
                    "last_name": last_name,
                    "display_name": f"{first_name} {last_name}",
                    "phone_number": f"+55 11 90000-360{index}",
                    "job_title": "Técnico de Campo Piloto",
                    "department": "Operações",
                    "user_type": user_model.UserType.INTERNAL,
                    "is_active": True,
                    "is_staff": False,
                    "is_verified": True,
                },
            )
            if created:
                user.set_unusable_password()
                user.save(update_fields=["password"])
            Membership.objects.update_or_create(
                user=user,
                company=company,
                defaults={"status": Membership.Status.ACTIVE, "is_primary": index == 1, "metadata": {"seed_key": SEED_KEY}},
            )
            SiteMembership.objects.update_or_create(
                user=user,
                site=site,
                defaults={"company": company, "status": SiteMembership.Status.ACTIVE, "is_primary": index == 1, "metadata": {"seed_key": SEED_KEY}},
            )
            profile, _ = TechnicianProfile.objects.update_or_create(
                user=user,
                defaults={
                    "company": company,
                    "display_name": user.display_name,
                    "phone": user.phone_number,
                    "whatsapp": user.phone_number,
                    "email": user.email,
                    "bio": "Perfil técnico criado pelo seed do piloto operacional.",
                    "certifications": ["NR10", "PMOC", "HVAC"],
                    "profile_type": TechnicianProfile.ProfileType.INTERNAL,
                    "experience_years": 6 + index,
                    "verification_status": TechnicianProfile.VerificationStatus.APPROVED,
                    "marketplace_status": TechnicianProfile.MarketplaceStatus.AVAILABLE,
                    "is_active": True,
                    "metadata": {"seed_key": SEED_KEY, "pilot": "operational_agents"},
                },
            )
            technicians.append(user)
            profiles.append(profile)
        return technicians, profiles

    def _seed_service_orders(self, *, client, site, assets, technicians):
        now = timezone.now()
        payload = [
            ("001", assets[0], ServiceOrder.MaintenanceType.CORRECTIVE, ServiceOrder.Priority.URGENT, ServiceOrder.Status.OPEN, ServiceOrder.Source.FAILURE, "Falha intermitente no chiller principal", -6, technicians[0]),
            ("002", assets[0], ServiceOrder.MaintenanceType.INSPECTION, ServiceOrder.Priority.HIGH, ServiceOrder.Status.SCHEDULED, ServiceOrder.Source.ALERT, "Inspeção de vibração e temperatura", -2, technicians[0]),
            ("003", assets[1], ServiceOrder.MaintenanceType.PREVENTIVE, ServiceOrder.Priority.HIGH, ServiceOrder.Status.COMPLETED, ServiceOrder.Source.PLAN, "Reaperto e termografia do QGBT", -18, technicians[1]),
            ("004", assets[2], ServiceOrder.MaintenanceType.CORRECTIVE, ServiceOrder.Priority.HIGH, ServiceOrder.Status.IN_PROGRESS, ServiceOrder.Source.FAILURE, "Baixa vazão na bomba de recalque", -4, technicians[1]),
            ("005", assets[3], ServiceOrder.MaintenanceType.PREVENTIVE, ServiceOrder.Priority.MEDIUM, ServiceOrder.Status.SCHEDULED, ServiceOrder.Source.PLAN, "Limpeza preventiva split sala técnica", 1, technicians[0]),
            ("006", assets[4], ServiceOrder.MaintenanceType.INSPECTION, ServiceOrder.Priority.URGENT, ServiceOrder.Status.OPEN, ServiceOrder.Source.ALERT, "Autonomia reduzida no nobreak supervisório", -1, technicians[1]),
            ("007", assets[2], ServiceOrder.MaintenanceType.PREVENTIVE, ServiceOrder.Priority.MEDIUM, ServiceOrder.Status.COMPLETED, ServiceOrder.Source.PLAN, "Lubrificação programada da bomba", -35, technicians[0]),
            ("008", assets[0], ServiceOrder.MaintenanceType.CORRECTIVE, ServiceOrder.Priority.HIGH, ServiceOrder.Status.COMPLETED, ServiceOrder.Source.FAILURE, "Reset por alta pressão no chiller", -28, technicians[1]),
        ]
        service_orders = []
        for suffix, asset, maintenance_type, priority, status, source, title, offset_days, technician in payload:
            opened_at = now + timedelta(days=offset_days)
            scheduled_start = now + timedelta(days=max(offset_days, 1), hours=9 + int(suffix) % 4)
            completed_at = opened_at + timedelta(hours=3) if status == ServiceOrder.Status.COMPLETED else None
            service_order, _ = ServiceOrder.objects.update_or_create(
                order_number=f"{ORDER_PREFIX}-{suffix}",
                defaults={
                    "client": client,
                    "operational_site": site,
                    "asset": asset,
                    "maintenance_type": maintenance_type,
                    "priority": priority,
                    "status": status,
                    "source": source,
                    "title": title,
                    "description": "Ordem criada pelo seed do piloto operacional para validar agentes de manutenção e agenda.",
                    "scheduled_start": scheduled_start,
                    "scheduled_end": scheduled_start + timedelta(hours=2),
                    "opened_at": opened_at,
                    "started_at": opened_at + timedelta(hours=1) if status in [ServiceOrder.Status.IN_PROGRESS, ServiceOrder.Status.COMPLETED] else None,
                    "completed_at": completed_at,
                    "requested_by": "Seed operacional Smart360",
                    "assigned_to": technician,
                    "final_observations": "Atendimento concluído com observações de piloto." if completed_at else "",
                    "notes": "seed_key=operational_pilot",
                },
            )
            service_orders.append(service_order)
            AssetHistoryEvent.objects.update_or_create(
                asset=asset,
                related_service_order=service_order,
                event_type=AssetHistoryEvent.EventType.SERVICE_ORDER_CREATED,
                title=f"OS {service_order.order_number} criada",
                defaults={
                    "description": title,
                    "occurred_at": opened_at,
                },
            )
        return service_orders

    def _seed_failures(self, *, assets, service_orders):
        now = timezone.now()
        payload = [
            (assets[0], service_orders[0], "Temperatura de descarga acima do limite", "Baixo fluxo no condensador", FailureEvent.Severity.CRITICAL, 95, FailureEvent.Status.OPEN, -6),
            (assets[0], service_orders[7], "Reset recorrente por alta pressão", "Condensador sujo", FailureEvent.Severity.HIGH, 45, FailureEvent.Status.RESOLVED, -28),
            (assets[2], service_orders[3], "Vazão abaixo do nominal", "Desgaste no rotor", FailureEvent.Severity.HIGH, 120, FailureEvent.Status.ANALYZING, -4),
            (assets[4], service_orders[5], "Autonomia menor que 10 minutos", "Banco de baterias degradado", FailureEvent.Severity.CRITICAL, 0, FailureEvent.Status.MONITORED, -1),
        ]
        failures = []
        for asset, service_order, symptom, cause, severity, downtime, status, offset_days in payload:
            detected_at = now + timedelta(days=offset_days)
            failure, _ = FailureEvent.objects.update_or_create(
                asset=asset,
                service_order=service_order,
                symptom=symptom,
                defaults={
                    "detected_at": detected_at,
                    "probable_cause": cause,
                    "severity": severity,
                    "downtime_minutes": downtime,
                    "status": status,
                    "notes": "seed_key=operational_pilot",
                },
            )
            AssetHistoryEvent.objects.update_or_create(
                asset=asset,
                related_failure_event=failure,
                event_type=AssetHistoryEvent.EventType.FAILURE_REPORTED,
                title=f"Falha reportada: {symptom[:80]}",
                defaults={"description": cause, "occurred_at": detected_at},
            )
            failures.append(failure)
        return failures

    def _seed_schedule(self, *, company, site, assets, technicians, profiles, service_orders):
        target_date = timezone.localdate() + timedelta(days=1)
        schedules = []
        visits = []
        for index, technician in enumerate(technicians):
            profile = profiles[index]
            schedule, _ = TechnicianSchedule.objects.update_or_create(
                company=company,
                technician=technician,
                date=target_date,
                defaults={
                    "operational_site": site,
                    "technician_profile": profile,
                    "total_jobs": 3 if index == 0 else 2,
                    "total_estimated_duration": 300 if index == 0 else 210,
                    "total_estimated_travel": 95 if index == 0 else 70,
                    "total_conflicts": 1 if index == 0 else 0,
                    "notes": "Agenda criada pelo seed do piloto operacional.",
                    "metadata": {"seed_key": SEED_KEY, "pilot": "operational_agents"},
                },
            )
            schedules.append(schedule)
            TechnicianAvailabilityWindow.objects.update_or_create(
                company=company,
                technician=technician,
                blocked_date=target_date,
                start_time=time(8, 0),
                end_time=time(17, 30),
                defaults={
                    "operational_site": site,
                    "technician_profile": profile,
                    "is_available": True,
                    "max_daily_jobs": 4,
                    "max_daily_hours": 8,
                    "notes": "Disponibilidade criada pelo seed do piloto operacional.",
                    "metadata": {"seed_key": SEED_KEY},
                },
            )

        visit_payload = [
            ("Diagnóstico chiller crítico", assets[0], service_orders[0], technicians[0], profiles[0], schedules[0], time(8, 30), 120, ScheduledVisit.Priority.URGENT, ["critical_asset"]),
            ("Inspeção vibração chiller", assets[0], service_orders[1], technicians[0], profiles[0], schedules[0], time(10, 0), 90, ScheduledVisit.Priority.HIGH, ["overlap_risk"]),
            ("Preventiva split sala técnica", assets[3], service_orders[4], technicians[0], profiles[0], schedules[0], time(13, 0), 90, ScheduledVisit.Priority.MEDIUM, []),
            ("Correção bomba recalque", assets[2], service_orders[3], technicians[1], profiles[1], schedules[1], time(9, 0), 120, ScheduledVisit.Priority.HIGH, []),
            ("Teste autonomia nobreak", assets[4], service_orders[5], technicians[1], profiles[1], schedules[1], time(14, 0), 90, ScheduledVisit.Priority.URGENT, ["sla_risk"]),
        ]
        for order, (title, asset, service_order, technician, profile, schedule, start_time, duration, priority, flags) in enumerate(visit_payload, start=1):
            start_dt = timezone.make_aware(datetime.combine(target_date, start_time))
            visit, _ = ScheduledVisit.objects.update_or_create(
                company=company,
                scheduled_date=target_date,
                title=title,
                defaults={
                    "operational_site": site,
                    "asset": asset,
                    "work_order": service_order,
                    "technician": technician,
                    "technician_profile": profile,
                    "technician_schedule": schedule,
                    "source_type": ScheduledVisit.SourceType.WORK_ORDER,
                    "scheduled_start": start_dt,
                    "scheduled_end": start_dt + timedelta(minutes=duration),
                    "window_start": start_time,
                    "window_end": (start_dt + timedelta(minutes=duration)).time(),
                    "estimated_duration_minutes": duration,
                    "estimated_travel_minutes": 20 + order * 5,
                    "priority": priority,
                    "status": ScheduledVisit.Status.SCHEDULED,
                    "route_order": order,
                    "city": site.city,
                    "state": site.state,
                    "location_label": site.name,
                    "conflict_flags": flags,
                    "notes": "seed_key=operational_pilot",
                    "metadata": {"seed_key": SEED_KEY, "pilot": "operational_agents"},
                },
            )
            visits.append(visit)
        return schedules, visits

    def _reset_seed(self, *, company_slug, site_name):
        company = Company.objects.filter(slug=company_slug, metadata__seed_key=SEED_KEY).first()
        if company is None:
            self.stdout.write("Nenhum dado seguro de piloto encontrado para reset.")
            return
        site_ids = list(
            OperationalSite.objects.filter(maintenance_client__company=company, name=site_name).values_list("id", flat=True)
        )
        asset_ids = list(Asset.objects.filter(asset_tag__startswith=f"{ASSET_TAG_PREFIX}-").values_list("id", flat=True))
        service_order_ids = list(ServiceOrder.objects.filter(order_number__startswith=f"{ORDER_PREFIX}-").values_list("id", flat=True))

        ScheduledVisit.objects.filter(company=company, metadata__seed_key=SEED_KEY).delete()
        TechnicianSchedule.objects.filter(company=company, metadata__seed_key=SEED_KEY).delete()
        TechnicianAvailabilityWindow.objects.filter(company=company, metadata__seed_key=SEED_KEY).delete()
        AssetHistoryEvent.objects.filter(related_service_order_id__in=service_order_ids).delete()
        AssetHistoryEvent.objects.filter(asset_id__in=asset_ids, title__startswith="Falha reportada:").delete()
        FailureEvent.objects.filter(asset_id__in=asset_ids, notes__icontains="seed_key=operational_pilot").delete()
        ServiceOrder.objects.filter(id__in=service_order_ids, notes__icontains="seed_key=operational_pilot").delete()
        Asset.objects.filter(id__in=asset_ids, metadata__seed_key=SEED_KEY).delete()
        SiteMembership.objects.filter(company=company, metadata__seed_key=SEED_KEY).delete()
        Membership.objects.filter(company=company, metadata__seed_key=SEED_KEY).delete()
        TechnicianProfile.objects.filter(company=company, metadata__seed_key=SEED_KEY).delete()
        get_user_model().objects.filter(email__in=TECH_EMAILS).delete()
        OperationalSite.objects.filter(id__in=site_ids).delete()
        MaintenanceClient.objects.filter(company=company, notes__icontains="seed do piloto operacional").delete()
        company.delete()
        self.stdout.write("Dados do seed operacional removidos com segurança.")
