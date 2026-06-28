from django.db import transaction
from django.utils import timezone

from apps.observability_center.models import JobExecutionTrace, SystemEventLog
from apps.observability_center.services.observability_service import (
    JobExecutionTraceService,
    MetricCounterService,
    SystemEventService,
)

from ..models import (
    AutomationTask,
    DeadLetterEvent,
    EventDelivery,
    EventSubscription,
    IntegrationEvent,
    IntegrationLog,
    ReactiveTriggerLog,
    WorkflowDefinition,
    WorkflowExecution,
)


class IntegrationLogService:
    @staticmethod
    def log(*, source_module, message, log_level=IntegrationLog.LogLevel.INFO, target_module="", event_name="", task_name="", payload=None):
        return IntegrationLog.objects.create(
            source_module=source_module,
            target_module=target_module,
            event_name=event_name,
            task_name=task_name,
            log_level=log_level,
            message=message,
            payload=payload or {},
        )


class WorkflowService:
    @staticmethod
    def create_execution(**validated_data):
        return WorkflowExecution.objects.create(**validated_data)

    @staticmethod
    def create_pending_executions_for_event(*, event):
        workflows = WorkflowDefinition.objects.filter(trigger_event_name=event.event_name, is_active=True)
        executions = []
        for workflow in workflows:
            execution = WorkflowExecution.objects.create(
                workflow_definition=workflow,
                integration_event=event,
                status=WorkflowExecution.Status.PENDING,
            )
            executions.append(execution)
            IntegrationLogService.log(
                source_module="integration_bus",
                target_module=workflow.slug,
                event_name=event.event_name,
                message=f"Workflow '{workflow.name}' queued for event '{event.event_name}'.",
                payload={"workflow_execution_id": execution.id},
            )
        return executions

    @staticmethod
    @transaction.atomic
    def run_execution(*, execution):
        execution.status = WorkflowExecution.Status.RUNNING
        execution.started_at = execution.started_at or timezone.now()
        execution.error_message = ""
        execution.save(update_fields=["status", "started_at", "error_message", "updated_at"])

        config = execution.workflow_definition.config_json or {}
        generated_tasks = []
        for task_config in config.get("automation_tasks", []):
            task = AutomationTask.objects.create(
                task_name=task_config.get("task_name", f"{execution.workflow_definition.slug}-task"),
                task_type=task_config.get("task_type", AutomationTask.TaskType.CUSTOM),
                source_module="integration_bus",
                target_module=task_config.get("target_module", ""),
                payload=task_config.get("payload", {}),
                status=AutomationTask.Status.PENDING,
                scheduled_at=timezone.now(),
                correlation_id=execution.integration_event.correlation_id,
            )
            generated_tasks.append(task)

        execution.status = WorkflowExecution.Status.COMPLETED
        execution.completed_at = timezone.now()
        execution.output_json = {
            "generated_tasks": [task.id for task in generated_tasks],
            "subscription_targets": list(
                EventSubscription.objects.filter(
                    event_name=execution.integration_event.event_name,
                    is_active=True,
                ).values_list("target_module", flat=True)
            ),
        }
        execution.save(update_fields=["status", "completed_at", "output_json", "updated_at"])
        IntegrationLogService.log(
            source_module="integration_bus",
            event_name=execution.integration_event.event_name,
            message=f"Workflow execution {execution.id} completed.",
            payload=execution.output_json,
        )
        return execution


class IntegrationEventService:
    @staticmethod
    def record_event(**validated_data):
        event_key = validated_data.get("event_key")
        if event_key:
            event, created = IntegrationEvent.objects.get_or_create(
                event_key=event_key,
                defaults=validated_data,
            )
            if not created:
                IntegrationLogService.log(
                    source_module=event.source_module,
                    event_name=event.event_name,
                    message=f"Integration event '{event.event_name}' replay ignored.",
                    payload={"event_id": event.id, "status": event.status, "event_key": event.event_key},
                )
                return event
        else:
            event = IntegrationEvent.objects.create(**validated_data)
        IntegrationLogService.log(
            source_module=event.source_module,
            event_name=event.event_name,
            message=f"Integration event '{event.event_name}' recorded.",
            payload={"event_id": event.id, "status": event.status},
        )
        return event

    @staticmethod
    @transaction.atomic
    def publish_event(*, event):
        event.status = IntegrationEvent.Status.PUBLISHED
        event.published_at = timezone.now()
        event.error_message = ""
        event.save(update_fields=["status", "published_at", "error_message", "updated_at"])
        WorkflowService.create_pending_executions_for_event(event=event)
        IntegrationLogService.log(
            source_module=event.source_module,
            event_name=event.event_name,
            message=f"Integration event '{event.event_name}' published.",
            payload={"event_id": event.id},
        )
        return event

    @staticmethod
    def mark_processed(*, event):
        event.status = IntegrationEvent.Status.PROCESSED
        event.processed_at = timezone.now()
        event.error_message = ""
        event.save(update_fields=["status", "processed_at", "error_message", "updated_at"])
        IntegrationLogService.log(
            source_module=event.source_module,
            event_name=event.event_name,
            message=f"Integration event '{event.event_name}' marked as processed.",
            payload={"event_id": event.id},
        )
        return event

    @staticmethod
    @transaction.atomic
    def mark_failed(*, event, error_message):
        event.retry_count += 1
        event.status = IntegrationEvent.Status.FAILED
        event.error_message = error_message
        event.save(update_fields=["retry_count", "status", "error_message", "updated_at"])
        IntegrationLogService.log(
            source_module=event.source_module,
            event_name=event.event_name,
            log_level=IntegrationLog.LogLevel.ERROR,
            message=f"Integration event '{event.event_name}' failed.",
            payload={"event_id": event.id, "retry_count": event.retry_count, "error_message": error_message},
        )
        max_retries = 3
        if event.retry_count >= max_retries:
            DeadLetterEvent.objects.create(
                original_event_name=event.event_name,
                source_module=event.source_module,
                payload=event.payload,
                failure_reason=error_message,
                retry_count=event.retry_count,
            )
            event.status = IntegrationEvent.Status.DEAD_LETTER
            event.save(update_fields=["status", "updated_at"])
        return event


class AutomationTaskService:
    @staticmethod
    def create_task(**validated_data):
        task = AutomationTask.objects.create(**validated_data)
        IntegrationLogService.log(
            source_module=task.source_module,
            target_module=task.target_module,
            task_name=task.task_name,
            message=f"Automation task '{task.task_name}' created.",
            payload={"task_id": task.id, "status": task.status},
        )
        return task

    @staticmethod
    def transition(*, task, status, error_message=""):
        now = timezone.now()
        trace, _ = JobExecutionTrace.objects.get_or_create(
            correlation_id=task.correlation_id,
            job_name=task.task_name,
            source_module=task.source_module,
            defaults={
                "status": JobExecutionTrace.Status.STARTED,
                "payload": task.payload,
                "started_at": task.started_at or now,
            },
        )
        task.status = status
        if status == AutomationTask.Status.RUNNING and task.started_at is None:
            task.started_at = now
        if status in {AutomationTask.Status.COMPLETED, AutomationTask.Status.FAILED, AutomationTask.Status.CANCELLED}:
            task.completed_at = now
        if status == AutomationTask.Status.FAILED:
            task.retry_count += 1
            task.error_message = error_message
        else:
            task.error_message = ""
        task.save()
        if status == AutomationTask.Status.RUNNING:
            trace.started_at = task.started_at or now
            trace.status = JobExecutionTrace.Status.STARTED
            trace.payload = task.payload
            trace.save(update_fields=["started_at", "status", "payload", "updated_at"])
        elif status == AutomationTask.Status.COMPLETED:
            JobExecutionTraceService.complete_job(
                trace=trace,
                payload={"task_id": task.id, "status": status, "target_module": task.target_module},
            )
            MetricCounterService.increment_metric(
                metric_key="integration.completed_tasks_count",
                source_module="integration_bus",
            )
            SystemEventService.log_system_event(
                event_type="integration.task_completed",
                source_module="integration_bus",
                severity=SystemEventLog.Severity.INFO,
                entity_type="automation_task",
                entity_id=str(task.id),
                correlation_id=task.correlation_id,
                message=f"Automation task '{task.task_name}' completed.",
                payload={"task_id": task.id, "target_module": task.target_module},
            )
        elif status == AutomationTask.Status.FAILED:
            JobExecutionTraceService.fail_job(
                trace=trace,
                error_message=error_message or "Automation task failed.",
                payload={"task_id": task.id, "status": status, "target_module": task.target_module},
            )
            MetricCounterService.increment_metric(
                metric_key="integration.failed_tasks_count",
                source_module="integration_bus",
            )
            SystemEventService.log_system_event(
                event_type="integration.task_failed",
                source_module="integration_bus",
                severity=SystemEventLog.Severity.ERROR,
                entity_type="automation_task",
                entity_id=str(task.id),
                correlation_id=task.correlation_id,
                message=f"Automation task '{task.task_name}' failed.",
                payload={"task_id": task.id, "error_message": error_message},
            )
        IntegrationLogService.log(
            source_module=task.source_module,
            target_module=task.target_module,
            task_name=task.task_name,
            log_level=IntegrationLog.LogLevel.ERROR if status == AutomationTask.Status.FAILED else IntegrationLog.LogLevel.INFO,
            message=f"Automation task '{task.task_name}' transitioned to '{status}'.",
            payload={"task_id": task.id, "status": status, "retry_count": task.retry_count},
        )
        return task


class EventDeliveryService:
    @staticmethod
    def reprocess(*, delivery: EventDelivery):
        from .realtime_bus import RealtimeEventBus

        return RealtimeEventBus.reprocess_delivery(delivery=delivery)


class ReactiveTriggerLogService:
    @staticmethod
    def list_for_event(*, event: IntegrationEvent):
        return ReactiveTriggerLog.objects.filter(integration_event=event).order_by("-created_at")
