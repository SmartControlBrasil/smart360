from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from django.utils import timezone

from apps.ai_automation_center.models import (
    AIContextProfile,
    AITaskRequest,
    AIModelConfig,
    AITaskType,
    AutomationRule,
    PromptTemplate,
    RetrievalSourceConfig,
)
from apps.ai_automation_center.services.ai_service import AITaskService, AutomationService, PromptTemplateService
from apps.ai_agents_center.services.registry import AgentRegistryService
from apps.access_control_center.services.smart_system_access import bootstrap_smart_system_access
from apps.analytics_platform.models import (
    AnalyticsDashboard,
    AnalyticsDimension,
    AnalyticsEvent,
    AnalyticsMetric,
    AnalyticsMetricValue,
    AnalyticsSnapshot,
    AnalyticsWidget,
)
from apps.backoffice.models import (
    BackofficeAlert,
    BackofficeQueue,
    BackofficeQueueItem,
    BackofficeQuickAction,
    BackofficeTask,
    BackofficeWidget,
)
from apps.billing.models import (
    BillingAddon,
    BillingCustomer,
    BillingLedgerEntry,
    BillingPlan,
    Contract,
    CommissionStatement,
    CreditTransaction,
    CreditWallet,
    Invoice,
    InvoiceItem,
    PaymentRecord,
    Subscription,
    SubscriptionAddon,
)
from apps.configuration_center.models import FeatureFlag, ModuleConfigurationProfile, RuntimeToggle, SystemSetting
from apps.files_center.models import (
    FileAccessLog,
    FileCategory,
    FileCollection,
    FileCollectionItem,
    FileLink,
    FileVersion,
    MediaAsset,
    StoredFile,
)
from apps.global_search.models import SearchBoostRule, SearchIndexEntry, SearchQueryLog, SearchSavedFilter, SearchSynonym
from apps.integration_bus.models import EventSubscription, WorkflowDefinition
from apps.notification_center.models import (
    InAppNotification,
    NotificationBatch,
    NotificationBatchItem,
    NotificationChannel,
    NotificationDeliveryLog,
    NotificationEvent,
    NotificationMessage,
    NotificationPreference,
    NotificationTemplate,
)
from apps.reporting_center.models import (
    ExportExecution,
    ExportProfile,
    ReportArtifact,
    ReportLog,
    ReportRequest,
    ReportTemplate,
    ScheduledReport,
)
from apps.scheduling_center.models import (
    AvailabilitySlot,
    Calendar,
    CalendarEvent,
    EventParticipant,
    RecurrenceRule,
    RecurringEventLink,
    ScheduledReminder,
    SchedulingTask,
)
from .common import attach_content_file, metadata_payload


def seed_smart_system_access_control(ctx):
    ctx.section("Seeding smart_system access control")
    summary = bootstrap_smart_system_access()
    ctx.log(f"[access] domains={summary['domains']} actions={summary['actions']} roles={summary['roles']}")


def seed_ai_agents_center(ctx):
    ctx.section("Seeding ai_agents_center")
    definitions = AgentRegistryService.bootstrap_registry()
    ctx.log(f"[ai_agents_center] agents={len(definitions)}")


def seed_files_center(ctx):
    ctx.section("Seeding files_center")
    categories = [
        "Logo",
        "Image",
        "Technical Document",
        "Report",
        "Attachment",
        "Artwork",
        "Invoice Document",
    ]
    for idx, name in enumerate(categories, start=1):
        category, _ = FileCategory.objects.update_or_create(
            name=name,
            defaults={"description": f"Bootstrap category {name}", "is_active": True, "ordering": idx},
        )
        ctx.put("file_categories", name.lower().replace(" ", "_"), category)

    stored_file, _ = StoredFile.objects.get_or_create(
        original_name="smart360-demo-logo.txt",
        defaults={
            "mime_type": "text/plain",
            "category": ctx.get("file_categories", "logo"),
            "storage_backend": StoredFile.StorageBackend.LOCAL,
            "visibility": StoredFile.Visibility.INTERNAL,
            "uploaded_by": ctx.get("users", "admin@smart360.local"),
            "metadata": metadata_payload(module="files_center"),
        },
    )
    attach_content_file(stored_file, "file", "smart360-demo-logo.txt", "SMART360 demo placeholder file.")
    ctx.put("stored_files", "demo_logo", stored_file)
    FileLink.objects.update_or_create(
        stored_file=stored_file,
        related_module="companies",
        related_item_type="company",
        related_item_id=str(ctx.get("companies", "smart360-internal").id),
        relation_type="company_logo",
        defaults={"is_primary": True},
    )
    MediaAsset.objects.update_or_create(
        stored_file=stored_file,
        asset_type=MediaAsset.AssetType.PROFILE_IMAGE,
        defaults={"title": "SMART360 Demo Logo", "alt_text": "SMART360", "caption": "Bootstrap logo", "ordering": 1, "is_active": True},
    )
    FileVersion.objects.update_or_create(
        parent_file=stored_file,
        version_label="v1",
        defaults={"stored_file": stored_file, "created_by": ctx.get("users", "admin@smart360.local"), "notes": "Initial bootstrap version"},
    )
    FileAccessLog.objects.create(stored_file=stored_file, accessed_by=ctx.get("users", "admin@smart360.local"), action_type=FileAccessLog.ActionType.UPLOADED)
    collection, _ = FileCollection.objects.update_or_create(
        name="Kit Midia SMART360 Demo",
        defaults={"collection_type": FileCollection.CollectionType.BRANDING_KIT, "created_by": ctx.get("users", "admin@smart360.local"), "is_active": True},
    )
    FileCollectionItem.objects.update_or_create(collection=collection, stored_file=stored_file, defaults={"ordering": 1, "is_primary": True})


def seed_analytics(ctx):
    ctx.section("Seeding analytics_platform")
    event_specs = [
        ("service_order_created", "smart_system", "service_order", str(ctx.get("service_orders", "preventive").id)),
        ("technician_assigned", "marketplace_technicians", "assignment", "1"),
        ("site_order_created", "smart_site_factory", "site_order", str(ctx.get("site_orders", "academia-exemplo-academia").id) if ctx.get("site_orders", "academia-exemplo-academia") else ""),
    ]
    for event_type, source_module, entity_type, entity_id in event_specs:
        AnalyticsEvent.objects.create(
            event_type=event_type,
            source_module=source_module,
            entity_type=entity_type,
            entity_id=entity_id,
            user=ctx.get("users", "admin@smart360.local"),
            company=ctx.get("companies", "smart360-internal"),
            payload=metadata_payload(source_module=source_module),
        )
    metrics = [
        ("total_service_orders", AnalyticsMetric.MetricType.COUNTER, "orders"),
        ("technician_jobs_completed", AnalyticsMetric.MetricType.COUNTER, "jobs"),
        ("revenue_generated", AnalyticsMetric.MetricType.CURRENCY, "BRL"),
    ]
    for name, metric_type, unit in metrics:
        metric, _ = AnalyticsMetric.objects.update_or_create(
            metric_name=name,
            defaults={"metric_type": metric_type, "unit": unit, "description": f"Bootstrap metric {name}", "is_active": True},
        )
        ctx.put("analytics_metrics", name, metric)
    dim, _ = AnalyticsDimension.objects.update_or_create(name="city", defaults={"description": "Cidade", "is_active": True})
    AnalyticsMetricValue.objects.update_or_create(
        metric=ctx.get("analytics_metrics", "total_service_orders"),
        dimension=dim,
        dimension_value="Sao Paulo",
        reference_date=timezone.now().date(),
        defaults={"value": Decimal("2"), "source_module": "smart_system"},
    )
    dashboard, _ = AnalyticsDashboard.objects.update_or_create(
        name="SMART360 Operational Dashboard",
        defaults={"description": "Bootstrap dashboard", "layout_config": {"columns": 3}, "is_active": True},
    )
    AnalyticsWidget.objects.update_or_create(
        dashboard=dashboard,
        ordering=1,
        defaults={"widget_type": AnalyticsWidget.WidgetType.METRIC_CARD, "title": "Service Orders", "metric": ctx.get("analytics_metrics", "total_service_orders"), "config_json": {"color": "blue"}, "is_active": True},
    )
    AnalyticsSnapshot.objects.update_or_create(
        snapshot_type="daily_system_state",
        snapshot_date=timezone.now().date(),
        defaults={"data_json": {"service_orders": 2, "active_leads": 3, "market_orders": 1}},
    )


def seed_billing(ctx):
    ctx.section("Seeding billing")
    plan_specs = [
        (
            "starter",
            "Starter",
            BillingPlan.BillingInterval.MONTHLY,
            Decimal("297.00"),
            Decimal("297.00"),
            Decimal("2970.00"),
            5,
            50,
            1,
            60,
            ["smart_system", "reports"],
        ),
        (
            "professional",
            "Professional",
            BillingPlan.BillingInterval.MONTHLY,
            Decimal("990.00"),
            Decimal("990.00"),
            Decimal("9900.00"),
            25,
            400,
            8,
            800,
            ["smart_system", "reports", "preventives", "inventory", "checklists"],
        ),
        (
            "enterprise",
            "Enterprise",
            BillingPlan.BillingInterval.YEARLY,
            Decimal("1490.00"),
            Decimal("1490.00"),
            Decimal("14900.00"),
            0,
            0,
            0,
            0,
            ["smart_system", "reports", "preventives", "inventory", "checklists", "observability"],
        ),
    ]
    for slug, name, interval, price_amount, monthly, yearly, user_limit, asset_limit, site_limit, work_order_limit, features in plan_specs:
        plan, _ = BillingPlan.objects.update_or_create(
            slug=slug,
            defaults={
                "name": name,
                "description": f"Bootstrap plan {name}",
                "billing_interval": interval,
                "price_amount": price_amount,
                "price_monthly": monthly,
                "price_yearly": yearly,
                "currency": "BRL",
                "trial_days": 7,
                "user_limit": user_limit,
                "asset_limit": asset_limit,
                "site_limit": site_limit,
                "work_order_limit": work_order_limit,
                "enabled_features": features,
                "status": BillingPlan.Status.ACTIVE,
                "is_active": True,
            },
        )
        ctx.put("billing_plans", slug, plan)
    addon, _ = BillingAddon.objects.update_or_create(
        slug="priority-support",
        defaults={"name": "Priority Support", "description": "Bootstrap addon", "addon_type": BillingAddon.AddonType.SUPPORT, "price_amount": Decimal("59.00"), "currency": "BRL", "is_active": True},
    )
    customer, _ = BillingCustomer.objects.update_or_create(
        company=ctx.get("companies", "academia-exemplo"),
        defaults={
            "user": ctx.get("users", "cliente@academia.local"),
            "customer_type": BillingCustomer.CustomerType.COMPANY,
            "billing_email": "financeiro@academia.local",
            "legal_name": "Academia Exemplo Fitness LTDA",
            "trade_name": "Academia Exemplo",
            "status": BillingCustomer.Status.ACTIVE,
            "metadata": metadata_payload(module="billing"),
        },
    )
    contract, _ = Contract.objects.update_or_create(
        company=ctx.get("companies", "academia-exemplo"),
        plan=ctx.get("billing_plans", "professional"),
        defaults={
            "billing_customer": customer,
            "start_date": timezone.localdate(),
            "renewal_date": timezone.localdate() + timedelta(days=30),
            "billing_periodicity": Contract.BillingPeriodicity.MONTHLY,
            "contracted_amount": Decimal("990.00"),
            "status": Contract.Status.ACTIVE,
            "sales_owner": ctx.get("users", "comercial@smart360.local"),
            "notes": "Contrato bootstrap Smart System Professional",
            "metadata": metadata_payload(module="billing", source="bootstrap"),
        },
    )
    ctx.put("billing_contracts", "academia-exemplo", contract)
    subscription, _ = Subscription.objects.update_or_create(
        billing_customer=customer,
        plan=ctx.get("billing_plans", "professional"),
        defaults={
            "company": ctx.get("companies", "academia-exemplo"),
            "contract": contract,
            "status": Subscription.Status.ACTIVE,
            "current_period_start": timezone.now(),
            "current_period_end": timezone.now() + timedelta(days=30),
            "next_billing_at": timezone.now() + timedelta(days=30),
            "amount": Decimal("990.00"),
            "billing_method": "pix_manual",
            "trial_ends_at": timezone.now() + timedelta(days=7),
            "auto_renew": True,
        },
    )
    SubscriptionAddon.objects.update_or_create(subscription=subscription, addon=addon, defaults={"quantity": 1, "status": SubscriptionAddon.Status.ACTIVE})
    invoice, _ = Invoice.objects.update_or_create(
        billing_customer=customer,
        subscription=subscription,
        status=Invoice.Status.OPEN,
        defaults={
            "company": ctx.get("companies", "academia-exemplo"),
            "contract": contract,
            "subtotal_amount": Decimal("990.00"),
            "discount_amount": Decimal("0.00"),
            "tax_amount": Decimal("0.00"),
            "currency": "BRL",
            "due_at": timezone.now() + timedelta(days=7),
            "payment_method": "pix",
            "external_reference": "boot-invoice-001",
            "notes": "Invoice bootstrap",
        },
    )
    InvoiceItem.objects.update_or_create(
        invoice=invoice,
        description="Smart System Pro - mensalidade",
        defaults={"item_type": InvoiceItem.ItemType.PLAN, "reference_type": "plan", "reference_id": str(subscription.plan.id), "quantity": Decimal("1.00"), "unit_amount": Decimal("990.00")},
    )
    PaymentRecord.objects.update_or_create(
        invoice=invoice,
        provider_reference="bootstrap-payment-1",
        defaults={"provider": "internal-demo", "payment_method": PaymentRecord.PaymentMethod.PIX, "status": PaymentRecord.Status.PENDING, "amount": invoice.total_amount, "currency": "BRL"},
    )
    wallet, _ = CreditWallet.objects.update_or_create(
        billing_customer=customer,
        wallet_type=CreditWallet.WalletType.LEAD_CREDITS,
        defaults={"balance": Decimal("50.00"), "currency": "BRL", "is_active": True},
    )
    CreditTransaction.objects.update_or_create(
        wallet=wallet,
        transaction_type=CreditTransaction.TransactionType.CREDIT_ADDED,
        description="Carga inicial bootstrap",
        defaults={"amount": Decimal("50.00"), "balance_after": Decimal("50.00"), "reference_type": "bootstrap", "reference_id": "credits-001"},
    )
    BillingLedgerEntry.objects.update_or_create(
        billing_customer=customer,
        entry_type=BillingLedgerEntry.EntryType.INVOICE_CREATED,
        reference_type="invoice",
        reference_id=str(invoice.id),
        defaults={"amount": invoice.total_amount, "currency": "BRL", "description": "Lancamento bootstrap", "occurred_at": timezone.now()},
    )
    CommissionStatement.objects.update_or_create(
        related_company=ctx.get("companies", "caneca-de-garagem"),
        statement_type=CommissionStatement.StatementType.MARKETPLACE,
        period_start=timezone.now().date(),
        defaults={"gross_amount": Decimal("300.00"), "fee_amount": Decimal("30.00"), "net_amount": Decimal("270.00"), "currency": "BRL", "status": CommissionStatement.Status.PENDING, "notes": "Statement bootstrap"},
    )
    subscription_event_name = "service_order_completed"
    EventSubscription.objects.update_or_create(
        event_name=subscription_event_name,
        target_module="analytics_platform",
        handler_name="register_service_order_completed_metric",
        defaults={"is_active": True, "execution_mode": EventSubscription.ExecutionMode.ASYNC, "retry_policy": {"max_retries": 3}},
    )
    WorkflowDefinition.objects.update_or_create(
        slug="service-order-completed-to-analytics",
        defaults={"name": "Service Order Completed To Analytics", "description": "Workflow bootstrap", "trigger_event_name": subscription_event_name, "workflow_type": WorkflowDefinition.WorkflowType.EVENT_DRIVEN, "config_json": {"target_module": "analytics_platform"}, "is_active": True},
    )


def seed_notification_center(ctx):
    ctx.section("Seeding notification_center")
    channels = [
        ("In App", NotificationChannel.ChannelType.IN_APP),
        ("Email", NotificationChannel.ChannelType.EMAIL),
        ("WhatsApp", NotificationChannel.ChannelType.WHATSAPP),
    ]
    for name, channel_type in channels:
        channel, _ = NotificationChannel.objects.update_or_create(
            name=name,
            defaults={"channel_type": channel_type, "description": f"Bootstrap channel {name}", "is_active": True},
        )
        ctx.put("notification_channels", channel_type, channel)
    email_template, _ = NotificationTemplate.objects.update_or_create(
        template_key="invoice_paid_email",
        defaults={
            "name": "Invoice Paid Email",
            "channel": ctx.get("notification_channels", NotificationChannel.ChannelType.EMAIL),
            "subject_template": "Pagamento confirmado",
            "body_template": "Sua fatura foi registrada com sucesso.",
            "description": "Template bootstrap",
            "is_active": True,
        },
    )
    NotificationPreference.objects.update_or_create(
        user=ctx.get("users", "admin@smart360.local"),
        event_key="invoice_paid",
        channel=ctx.get("notification_channels", NotificationChannel.ChannelType.EMAIL),
        defaults={"is_enabled": True},
    )
    event, _ = NotificationEvent.objects.update_or_create(
        event_key="service_order_created",
        source_module="smart_system",
        entity_type="service_order",
        entity_id=str(ctx.get("service_orders", "preventive").id),
        defaults={"payload": metadata_payload()},
    )
    message, _ = NotificationMessage.objects.update_or_create(
        event_key="service_order_created",
        channel=ctx.get("notification_channels", NotificationChannel.ChannelType.IN_APP),
        recipient_user=ctx.get("users", "ops@smart360.local"),
        defaults={
            "template": email_template,
            "subject_rendered": "Nova OS preventiva criada",
            "body_rendered": "A OS preventiva bootstrap foi criada.",
            "payload": metadata_payload(),
            "status": NotificationMessage.Status.DELIVERED,
            "scheduled_at": timezone.now(),
            "sent_at": timezone.now(),
            "delivered_at": timezone.now(),
        },
    )
    InAppNotification.objects.update_or_create(
        user=ctx.get("users", "ops@smart360.local"),
        title="Nova OS preventiva criada",
        defaults={"body": "Verifique a agenda operacional.", "notification_type": InAppNotification.NotificationType.ACTION_REQUIRED, "status": InAppNotification.Status.UNREAD},
    )
    NotificationDeliveryLog.objects.update_or_create(
        notification_message=message,
        channel=message.channel,
        provider_reference="notif-demo-1",
        defaults={"provider_name": "internal-demo", "delivery_status": NotificationDeliveryLog.DeliveryStatus.DELIVERED},
    )
    batch, _ = NotificationBatch.objects.update_or_create(
        batch_name="Disparo Operacional Demo",
        defaults={"batch_type": NotificationBatch.BatchType.OPERATIONAL, "description": "Batch bootstrap", "status": NotificationBatch.Status.COMPLETED, "sent_at": timezone.now()},
    )
    NotificationBatchItem.objects.update_or_create(batch=batch, notification_message=message, defaults={"status": NotificationBatchItem.Status.SENT})


def seed_backoffice(ctx):
    ctx.section("Seeding backoffice")
    queue, _ = BackofficeQueue.objects.update_or_create(
        slug="ordens-de-servico-abertas",
        defaults={"name": "Ordens de Servico Abertas", "queue_type": BackofficeQueue.QueueType.OPERATIONAL, "source_module": "smart_system", "description": "Fila bootstrap", "is_active": True, "ordering": 1},
    )
    BackofficeQueueItem.objects.update_or_create(
        queue=queue,
        item_type="service_order",
        item_id=str(ctx.get("service_orders", "corrective").id),
        defaults={"reference_label": ctx.get("service_orders", "corrective").order_number, "status": BackofficeQueueItem.Status.IN_PROGRESS, "priority": BackofficeQueueItem.Priority.HIGH, "assigned_to": ctx.get("users", "ops@smart360.local"), "metadata": metadata_payload()},
    )
    BackofficeAlert.objects.update_or_create(
        slug="falha-critica-esteira",
        defaults={"title": "Falha critica em esteira", "alert_type": BackofficeAlert.AlertType.OPERATIONAL, "source_module": "smart_system", "severity": BackofficeAlert.Severity.CRITICAL, "status": BackofficeAlert.Status.OPEN, "related_item_type": "failure_event", "related_item_id": "1", "summary": "Ativo em falha na unidade centro", "details": "Falha bootstrap"},
    )
    BackofficeTask.objects.update_or_create(
        title="Revisar OS corretiva RT250",
        defaults={"task_type": BackofficeTask.TaskType.REVIEW, "source_module": "smart_system", "assigned_to": ctx.get("users", "ops@smart360.local"), "status": BackofficeTask.Status.PENDING, "priority": BackofficeTask.Priority.HIGH, "due_at": timezone.now() + timedelta(days=1), "related_item_type": "service_order", "related_item_id": str(ctx.get("service_orders", "corrective").id), "notes": "Task bootstrap"},
    )
    BackofficeQuickAction.objects.update_or_create(
        slug="revisar-os",
        defaults={"name": "Revisar OS", "target_module": "smart_system", "action_type": BackofficeQuickAction.ActionType.REVIEW, "label": "Revisar OS", "route_path": "/smart-system/service-orders/", "config_json": {"source": "bootstrap"}, "is_active": True, "ordering": 1},
    )
    BackofficeWidget.objects.update_or_create(
        slug="active-service-orders-card",
        defaults={"name": "Active Service Orders Card", "widget_type": BackofficeWidget.WidgetType.METRIC_CARD, "source_module": "smart_system", "title": "Active service orders", "config_json": {"metric": "total_service_orders"}, "is_active": True, "ordering": 1},
    )


def seed_global_search(ctx):
    ctx.section("Seeding global_search")
    index_specs = [
        ("smart_system", "service_order", str(ctx.get("service_orders", "corrective").id), "SO-DEMO-002", "OS corretiva da esteira", "ordem de servico corretiva esteira rt250", "in_progress", "service_order", "/smart-system/service-orders/so-demo-002/"),
        ("growth_engine", "lead", str(ctx.get("leads", "lead-academia@demo.local").id), "Academia Exemplo Guarulhos", "Lead qualificado", "lead academia guarulhos site factory", "qualified", "lead", "/growth/leads/academia-exemplo/"),
        ("knowledge_engine", "article", "1", "Falha de partida na Esteira RT250", "Troubleshooting", "motor nao parte capacitor defeituoso", "published", "knowledge", "/knowledge/articles/falha-de-partida/"),
    ]
    for source_module, item_type, item_id, title, subtitle, search_text, status, category, url_path in index_specs:
        SearchIndexEntry.objects.update_or_create(
            source_module=source_module,
            item_type=item_type,
            item_id=item_id,
            defaults={"title": title, "subtitle": subtitle, "body_text": subtitle, "search_text": search_text, "status": status, "category": category, "url_path": url_path, "metadata": metadata_payload()},
        )
    SearchQueryLog.objects.create(query_text="esteira rt250", performed_by=ctx.get("users", "engenharia@smart360.local"), source_context="bootstrap", filters_json={"module": "smart_system"}, results_count=2)
    SearchSavedFilter.objects.update_or_create(name="OS em andamento", defaults={"owner_user": ctx.get("users", "ops@smart360.local"), "owner_company": ctx.get("companies", "smart360-internal"), "filter_config": {"source_module": "smart_system", "status": "in_progress"}, "is_active": True})
    SearchSynonym.objects.update_or_create(term="OS", synonym="ordem de servico", defaults={"is_active": True})
    SearchBoostRule.objects.update_or_create(source_module="smart_system", item_type="service_order", status="in_progress", defaults={"boost_value": 20, "is_active": True})


def seed_reporting(ctx):
    ctx.section("Seeding reporting_center")
    template, _ = ReportTemplate.objects.update_or_create(
        slug="service-orders-summary",
        defaults={"name": "Service Orders Summary", "source_module": "smart_system", "report_type": ReportTemplate.ReportType.OPERATIONAL, "description": "Resumo bootstrap de OS", "output_format_default": ReportTemplate.OutputFormat.JSON, "config_json": {"columns": ["order_number", "status", "priority"]}, "is_active": True},
    )
    export_profile, _ = ExportProfile.objects.update_or_create(
        slug="export-leads-json",
        defaults={"name": "Export Leads JSON", "source_module": "growth_engine", "export_type": ExportProfile.ExportType.LIST, "description": "Export bootstrap", "columns_config": ["company_name", "status", "score"], "filters_config": {"status": ["new", "qualified"]}, "is_active": True, "created_by": ctx.get("users", "admin@smart360.local")},
    )
    request, _ = ReportRequest.objects.update_or_create(
        template=template,
        requested_for_company=ctx.get("companies", "academia-exemplo"),
        defaults={"requested_by": ctx.get("users", "admin@smart360.local"), "source_module": "smart_system", "status": ReportRequest.Status.COMPLETED, "output_format": ReportRequest.OutputFormat.JSON, "filters_json": {"site": "Unidade Centro"}, "started_at": timezone.now(), "completed_at": timezone.now()},
    )
    artifact, _ = ReportArtifact.objects.get_or_create(
        report_request=request,
        artifact_type=ReportArtifact.ArtifactType.JSON,
        defaults={"file_name": "service-orders-summary.json", "mime_type": "application/json", "size_bytes": 128, "metadata": {"bootstrap": True}},
    )
    attach_content_file(artifact, "file", "service-orders-summary.json", '{"service_orders": 2}')
    execution, _ = ExportExecution.objects.update_or_create(
        export_profile=export_profile,
        requested_by=ctx.get("users", "admin@smart360.local"),
        defaults={"status": ExportExecution.Status.COMPLETED, "output_format": ExportExecution.OutputFormat.JSON, "filters_json": {"city": "Guarulhos"}, "started_at": timezone.now(), "completed_at": timezone.now()},
    )
    ReportLog.objects.create(source_module="smart_system", report_request=request, log_level=ReportLog.LogLevel.INFO, message="Bootstrap report generated", payload=metadata_payload())
    ScheduledReport.objects.update_or_create(
        slug="relatorio-semanal-os",
        defaults={"name": "Relatorio semanal de OS", "template": template, "owner_user": ctx.get("users", "ops@smart360.local"), "owner_company": ctx.get("companies", "smart360-internal"), "schedule_type": ScheduledReport.ScheduleType.WEEKLY, "schedule_config": {"weekday": "monday"}, "output_format": ScheduledReport.OutputFormat.JSON, "filters_json": {"status": "open"}, "is_active": True},
    )


def seed_configuration(ctx):
    ctx.section("Seeding configuration_center")
    SystemSetting.objects.update_or_create(
        key="billing.default_currency",
        defaults={"group_name": "billing", "module_name": "billing", "description": "Moeda padrao", "value_type": SystemSetting.ValueType.STRING, "value_string": "BRL", "default_value_json": {"value": "BRL"}, "is_active": True, "is_sensitive": False},
    )
    SystemSetting.objects.update_or_create(
        key="files.max_upload_size_mb",
        defaults={"group_name": "files", "module_name": "files_center", "description": "Tamanho maximo", "value_type": SystemSetting.ValueType.NUMBER, "value_number": Decimal("15"), "default_value_json": {"value": 15}, "is_active": True},
    )
    FeatureFlag.objects.update_or_create(
        key="smart_site_factory.ai_copy_enabled",
        defaults={"module_name": "smart_site_factory", "description": "Habilita copy de IA", "flag_type": FeatureFlag.FlagType.BOOLEAN, "is_enabled": True, "rollout_percentage": 100, "config_json": {"source": "bootstrap"}, "is_active": True},
    )
    RuntimeToggle.objects.update_or_create(
        key="disable_external_notifications",
        defaults={"module_name": "notification_center", "description": "Toggle bootstrap", "is_enabled": False, "notes": "Manter desabilitado em local"},
    )
    ModuleConfigurationProfile.objects.update_or_create(
        slug="default_smart_system_profile",
        defaults={"name": "Default Smart System Profile", "module_name": "smart_system", "description": "Perfil padrao bootstrap", "config_json": {"default_priority": "medium", "auto_schedule": False}, "is_active": True},
    )


def seed_scheduling(ctx):
    ctx.section("Seeding scheduling_center")
    calendar, _ = Calendar.objects.update_or_create(
        slug="agenda-operacional",
        defaults={"name": "Agenda Operacional", "calendar_type": Calendar.CalendarType.OPERATIONAL, "description": "Agenda bootstrap de operacoes", "owner_company": ctx.get("companies", "smart360-internal"), "owner_user": ctx.get("users", "ops@smart360.local"), "is_active": True},
    )
    event, _ = CalendarEvent.objects.update_or_create(
        calendar=calendar,
        title="Preventiva Esteira RT250",
        defaults={"description": "Evento bootstrap ligado a OS preventiva", "event_type": CalendarEvent.EventType.PREVENTIVE, "status": CalendarEvent.Status.CONFIRMED, "start_at": timezone.now() + timedelta(days=1), "end_at": timezone.now() + timedelta(days=1, hours=2), "location": "Unidade Centro", "related_module": "smart_system", "related_item_type": "service_order", "related_item_id": str(ctx.get("service_orders", "preventive").id), "created_by": ctx.get("users", "ops@smart360.local"), "assigned_to": ctx.get("users", "engenharia@smart360.local"), "metadata": metadata_payload()},
    )
    EventParticipant.objects.update_or_create(
        calendar_event=event,
        user=ctx.get("users", "engenharia@smart360.local"),
        defaults={"participant_type": EventParticipant.ParticipantType.INTERNAL, "response_status": EventParticipant.ResponseStatus.ACCEPTED, "notes": "Bootstrap participant"},
    )
    rule, _ = RecurrenceRule.objects.update_or_create(
        slug="preventiva-semanal",
        defaults={"name": "Preventiva semanal", "frequency_type": RecurrenceRule.FrequencyType.WEEKLY, "interval_value": 1, "start_date": timezone.now().date(), "occurrences_limit": 4, "is_active": True, "config_json": {"weekday": "monday"}},
    )
    link, _ = RecurringEventLink.objects.update_or_create(parent_event=event, defaults={"recurrence_rule": rule, "is_active": True})
    AvailabilitySlot.objects.update_or_create(
        user=ctx.get("users", "engenharia@smart360.local"),
        calendar=calendar,
        weekday=1,
        start_time="08:00",
        end_time="18:00",
        defaults={"slot_type": AvailabilitySlot.SlotType.TECHNICIAN, "is_available": True, "notes": "Disponibilidade bootstrap"},
    )
    ScheduledReminder.objects.update_or_create(
        calendar_event=event,
        reminder_type=ScheduledReminder.ReminderType.UPCOMING_EVENT,
        channel=ScheduledReminder.Channel.IN_APP,
        remind_at=timezone.now() + timedelta(hours=20),
        defaults={"status": ScheduledReminder.Status.PENDING},
    )
    SchedulingTask.objects.update_or_create(
        title="Confirmar preventiva da esteira",
        due_at=timezone.now() + timedelta(days=1),
        defaults={"description": "Task bootstrap", "task_type": SchedulingTask.TaskType.OPERATIONAL, "priority": SchedulingTask.Priority.HIGH, "status": SchedulingTask.Status.PENDING, "assigned_to": ctx.get("users", "ops@smart360.local"), "related_module": "smart_system", "related_item_type": "service_order", "related_item_id": str(ctx.get("service_orders", "preventive").id), "created_by": ctx.get("users", "admin@smart360.local")},
    )


def seed_ai_automation(ctx):
    ctx.section("Seeding ai_automation_center")
    task_types = [
        ("Text Summarization", AITaskType.TaskCategory.SUMMARIZATION),
        ("Classification", AITaskType.TaskCategory.CLASSIFICATION),
        ("Technical Diagnosis Support", AITaskType.TaskCategory.DIAGNOSIS),
    ]
    for name, category in task_types:
        task_type, _ = AITaskType.objects.update_or_create(
            name=name,
            defaults={"description": f"Bootstrap task type {name}", "task_category": category, "is_active": True},
        )
        ctx.put("ai_task_types", name, task_type)
    model, _ = AIModelConfig.objects.update_or_create(
        slug="gpt-style-chat-model",
        defaults={"name": "GPT Style Chat Model", "provider_name": "provider-agnostic", "model_identifier": "demo-chat-001", "model_type": AIModelConfig.ModelType.CHAT, "config_json": {"temperature": 0.2}, "is_active": True},
    )
    context_profile, _ = AIContextProfile.objects.update_or_create(
        slug="smart_system_failure_context",
        defaults={"name": "Smart System Failure Context", "source_module": "smart_system", "description": "Contexto bootstrap para falhas", "context_schema": {"asset": "string", "symptom": "string"}, "is_active": True},
    )
    prompt, _ = PromptTemplate.objects.update_or_create(
        slug="service-order-summary-v1",
        defaults={"name": "Service Order Summary", "task_type": ctx.get("ai_task_types", "Text Summarization"), "source_module": "smart_system", "prompt_role": "assistant", "prompt_template": "Resuma a OS {{order_number}} e sugira proximos passos.", "expected_output_schema": {"summary": "string", "next_steps": "array"}, "model_hint": model.model_identifier, "version_label": "v1", "is_active": True, "created_by": ctx.get("users", "admin@smart360.local")},
    )
    if not prompt.versions.exists():
        PromptTemplateService.create_version_snapshot(prompt)
    task_request, execution, artifact = AITaskService.run_task(
        AITaskRequest.objects.create(
            task_type=ctx.get("ai_task_types", "Text Summarization"),
            prompt_template=prompt,
            context_profile=context_profile,
            source_module="smart_system",
            source_reference_type="service_order",
            source_reference_id=str(ctx.get("service_orders", "corrective").id),
            requested_by=ctx.get("users", "engenharia@smart360.local"),
            input_payload={"order_number": ctx.get("service_orders", "corrective").order_number},
            status=AITaskRequest.Status.QUEUED,
            priority=AITaskRequest.Priority.HIGH,
            model_name=model.model_identifier,
        )
    )
    artifact.is_approved = True
    artifact.approved_by = ctx.get("users", "engenharia@smart360.local")
    artifact.save()
    AutomationRule.objects.update_or_create(
        slug="ao-concluir-os-gerar-resumo",
        defaults={"name": "Ao concluir OS gerar resumo", "source_module": "smart_system", "trigger_event": "service_order_completed", "task_type": ctx.get("ai_task_types", "Text Summarization"), "prompt_template": prompt, "is_active": True, "priority": AutomationRule.Priority.MEDIUM, "config_json": {"artifact_type": "summary"}},
    )
    rule = AutomationRule.objects.get(slug="ao-concluir-os-gerar-resumo")
    AutomationService.run_automation(
        rule,
        source_reference_type="service_order",
        source_reference_id=str(ctx.get("service_orders", "corrective").id),
        integration_event_id="evt-bootstrap-001",
        requested_by=ctx.get("users", "admin@smart360.local"),
        input_payload={"order_number": ctx.get("service_orders", "corrective").order_number},
    )
    RetrievalSourceConfig.objects.update_or_create(
        slug="knowledge-engine-articles",
        defaults={"name": "Knowledge Engine Articles", "source_type": "knowledge_articles", "source_module": "knowledge_engine", "description": "Fonte bootstrap para RAG futuro", "config_json": {"enabled": True}, "is_active": True},
    )
