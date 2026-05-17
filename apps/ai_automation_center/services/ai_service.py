from django.utils import timezone

from apps.ai_automation_center.models import (
    AIGeneratedArtifact,
    AITaskExecution,
    AITaskRequest,
    AutomationExecution,
    AutomationRule,
    PromptVersion,
)


class PromptTemplateService:
    @staticmethod
    def create_version_snapshot(prompt_template):
        return PromptVersion.objects.create(
            prompt_template=prompt_template,
            version_label=prompt_template.version_label,
            prompt_template_snapshot=prompt_template.prompt_template,
            expected_output_schema=prompt_template.expected_output_schema,
            created_by=prompt_template.created_by,
        )

    @staticmethod
    def render_preview(prompt_template, input_payload: dict):
        preview = prompt_template.prompt_template
        for key, value in input_payload.items():
            preview = preview.replace(f"{{{{{key}}}}}", str(value))
        return preview


class AITaskService:
    @staticmethod
    def run_task(task_request: AITaskRequest):
        task_request.status = AITaskRequest.Status.RUNNING
        task_request.started_at = timezone.now()
        task_request.save(update_fields=["status", "started_at", "updated_at"])

        prompt_snapshot = ""
        if task_request.prompt_template:
            prompt_snapshot = PromptTemplateService.render_preview(
                task_request.prompt_template,
                task_request.input_payload,
            )

        output_text = (
            f"Simulated {task_request.task_type.slug} output for "
            f"{task_request.source_module}:{task_request.source_reference_type or 'generic'}"
        )
        output_json = {
            "task_type": task_request.task_type.slug,
            "source_module": task_request.source_module,
            "source_reference_type": task_request.source_reference_type,
            "source_reference_id": task_request.source_reference_id,
            "summary": output_text,
            "input_payload": task_request.input_payload,
        }

        model_name = task_request.model_name
        if not model_name and task_request.prompt_template:
            model_name = task_request.prompt_template.model_hint

        execution = AITaskExecution.objects.create(
            task_request=task_request,
            execution_mode=AITaskExecution.ExecutionMode.SIMULATED,
            provider_name="internal-simulated",
            model_name=model_name,
            prompt_snapshot=prompt_snapshot,
            input_snapshot=task_request.input_payload,
            output_text=output_text,
            output_json=output_json,
            token_usage_input=len(str(task_request.input_payload)),
            token_usage_output=len(output_text),
            cost_estimate=0,
            status=AITaskExecution.Status.COMPLETED,
            completed_at=timezone.now(),
        )

        artifact = AIGeneratedArtifact.objects.create(
            task_execution=execution,
            artifact_type=task_request.task_type.slug,
            title=f"{task_request.task_type.name} artifact",
            content_text=output_text,
            content_json=output_json,
        )

        task_request.status = AITaskRequest.Status.COMPLETED
        task_request.completed_at = timezone.now()
        task_request.save(update_fields=["status", "completed_at", "updated_at"])
        return task_request, execution, artifact


class AutomationService:
    @staticmethod
    def run_automation(
        automation_rule: AutomationRule,
        *,
        source_reference_type: str = "",
        source_reference_id: str = "",
        integration_event_id: str = "",
        requested_by=None,
        input_payload: dict | None = None,
    ):
        execution = AutomationExecution.objects.create(
            automation_rule=automation_rule,
            source_reference_type=source_reference_type,
            source_reference_id=source_reference_id,
            integration_event_id=integration_event_id,
            status=AutomationExecution.Status.RUNNING,
        )

        task_request = AITaskRequest.objects.create(
            task_type=automation_rule.task_type,
            prompt_template=automation_rule.prompt_template,
            source_module=automation_rule.source_module,
            source_reference_type=source_reference_type,
            source_reference_id=source_reference_id,
            requested_by=requested_by,
            input_payload=input_payload or automation_rule.config_json,
            priority=automation_rule.priority,
            status=AITaskRequest.Status.QUEUED,
        )
        task_request, _, artifact = AITaskService.run_task(task_request)

        execution.status = AutomationExecution.Status.COMPLETED
        execution.completed_at = timezone.now()
        execution.output_summary = artifact.content_text[:500]
        execution.save(update_fields=["status", "completed_at", "output_summary", "updated_at"])
        return execution, task_request, artifact
