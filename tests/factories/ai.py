from decimal import Decimal

import factory
from django.utils import timezone

from apps.ai_automation_center.models import (
    AIGeneratedArtifact,
    AITaskExecution,
    AITaskRequest,
    AITaskType,
    PromptTemplate,
)
from tests.factories.core import UserFactory


class AITaskTypeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = AITaskType

    name = factory.Sequence(lambda n: f"AI Task Type {n}")
    description = factory.Faker("sentence")
    task_category = AITaskType.TaskCategory.GENERATION
    is_active = True


class PromptTemplateFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = PromptTemplate

    name = factory.Sequence(lambda n: f"Prompt Template {n}")
    task_type = factory.SubFactory(AITaskTypeFactory)
    source_module = "smart_site_factory"
    prompt_role = "system"
    prompt_template = "Generate a concise summary for {{ company_name }}"
    expected_output_schema = factory.LazyFunction(dict)
    model_hint = "demo-model"
    version_label = "v1"
    is_active = True
    created_by = factory.SubFactory(UserFactory)


class AITaskRequestFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = AITaskRequest

    task_type = factory.SubFactory(AITaskTypeFactory)
    prompt_template = factory.SubFactory(PromptTemplateFactory)
    source_module = "growth_engine"
    source_reference_type = "lead"
    source_reference_id = "1"
    requested_by = factory.SubFactory(UserFactory)
    input_payload = factory.LazyFunction(lambda: {"text": "demo"})
    status = AITaskRequest.Status.PENDING
    priority = AITaskRequest.Priority.MEDIUM
    model_name = "demo-model"


class AITaskExecutionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = AITaskExecution

    task_request = factory.SubFactory(AITaskRequestFactory)
    execution_mode = AITaskExecution.ExecutionMode.SIMULATED
    provider_name = "demo-provider"
    model_name = "demo-model"
    prompt_snapshot = "prompt"
    input_snapshot = factory.LazyFunction(dict)
    output_text = "output"
    output_json = factory.LazyFunction(dict)
    token_usage_input = 10
    token_usage_output = 20
    cost_estimate = Decimal("0.0100")
    status = AITaskExecution.Status.COMPLETED
    started_at = factory.LazyFunction(timezone.now)
    completed_at = factory.LazyFunction(timezone.now)


class AIGeneratedArtifactFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = AIGeneratedArtifact

    task_execution = factory.SubFactory(AITaskExecutionFactory)
    artifact_type = "summary"
    title = factory.Sequence(lambda n: f"Artifact {n}")
    content_text = "generated content"
    content_json = factory.LazyFunction(dict)
    is_approved = False

