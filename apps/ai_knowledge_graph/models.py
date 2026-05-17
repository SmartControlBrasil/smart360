import uuid

from django.db import models
from django.utils import timezone


class GraphNode(models.Model):
    class NodeType(models.TextChoices):
        ASSET = "asset", "Asset"
        ASSET_CATEGORY = "asset_category", "Asset Category"
        FAILURE_EVENT = "failure_event", "Failure Event"
        FAILURE_MODE = "failure_mode", "Failure Mode"
        RCA_CAUSE = "rca_cause", "RCA Cause"
        PREVENTIVE_PLAN = "preventive_plan", "Preventive Plan"
        WORK_ORDER = "work_order", "Work Order"
        CHECKLIST = "checklist", "Checklist"
        CHECKLIST_ITEM = "checklist_item", "Checklist Item"
        PART = "part", "Part"
        TECHNICIAN = "technician", "Technician"
        SKILL = "skill", "Skill"
        COMPANY = "company", "Company"
        SITE = "site", "Site"
        CONTRACT = "contract", "Contract"
        QUOTE = "quote", "Quote"
        REPORT = "report", "Report"
        RECOMMENDATION = "recommendation", "Recommendation"
        DECISION = "decision", "Decision"
        ANOMALY = "anomaly", "Anomaly"
        SERVICE_REQUEST = "service_request", "Service Request"
        ASSIGNMENT = "assignment", "Assignment"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="graph_nodes",
        null=True,
        blank=True,
    )
    site = models.ForeignKey(
        "smart_system.OperationalSite",
        on_delete=models.SET_NULL,
        related_name="graph_nodes",
        null=True,
        blank=True,
    )
    node_type = models.CharField(max_length=40, choices=NodeType.choices, db_index=True)
    source_type = models.CharField(max_length=80, db_index=True)
    source_id = models.CharField(max_length=120, db_index=True)
    label = models.CharField(max_length=255)
    attributes = models.JSONField(default=dict, blank=True)
    strength = models.DecimalField(max_digits=8, decimal_places=2, default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ai_knowledge_graph_nodes"
        ordering = ["node_type", "label"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "node_type", "source_type", "source_id"],
                name="uniq_knowledge_graph_node_source",
            ),
        ]
        indexes = [
            models.Index(fields=["company", "site", "node_type"], name="knowledge_graph_node_scope_idx"),
        ]

    def __str__(self) -> str:
        return self.label


class GraphEdge(models.Model):
    class EdgeType(models.TextChoices):
        ASSET_LOCATED_AT_SITE = "asset_located_at_site", "Asset Located At Site"
        ASSET_BELONGS_TO_CATEGORY = "asset_belongs_to_category", "Asset Belongs To Category"
        ASSET_HAS_FAILURE = "asset_has_failure", "Asset Has Failure"
        FAILURE_HAS_MODE = "failure_has_mode", "Failure Has Mode"
        FAILURE_HAS_CAUSE = "failure_has_cause", "Failure Has Cause"
        WORK_ORDER_TARGETS_ASSET = "work_order_targets_asset", "Work Order Targets Asset"
        WORK_ORDER_GENERATED_FROM_FAILURE = "work_order_generated_from_failure", "Work Order Generated From Failure"
        PREVENTIVE_TARGETS_ASSET = "preventive_targets_asset", "Preventive Targets Asset"
        CHECKLIST_USED_IN_WORK_ORDER = "checklist_used_in_work_order", "Checklist Used In Work Order"
        CHECKLIST_ITEM_FLAGGED_ISSUE = "checklist_item_flagged_issue", "Checklist Item Flagged Issue"
        PART_USED_IN_WORK_ORDER = "part_used_in_work_order", "Part Used In Work Order"
        PART_RELATED_TO_ASSET = "part_related_to_asset", "Part Related To Asset"
        TECHNICIAN_HAS_SKILL = "technician_has_skill", "Technician Has Skill"
        TECHNICIAN_EXECUTED_WORK_ORDER = "technician_executed_work_order", "Technician Executed Work Order"
        TECHNICIAN_BEST_FIT_FOR_CATEGORY = "technician_best_fit_for_category", "Technician Best Fit For Category"
        CONTRACT_COVERS_ASSET = "contract_covers_asset", "Contract Covers Asset"
        COMPANY_OWNS_SITE = "company_owns_site", "Company Owns Site"
        COMPANY_HAS_CONTRACT = "company_has_contract", "Company Has Contract"
        RECOMMENDATION_TARGETS_ASSET = "recommendation_targets_asset", "Recommendation Targets Asset"
        DECISION_ACTS_ON_ENTITY = "decision_acts_on_entity", "Decision Acts On Entity"
        ANOMALY_DETECTED_ON_ENTITY = "anomaly_detected_on_entity", "Anomaly Detected On Entity"
        ASSIGNMENT_ALLOCATES_TECHNICIAN = "assignment_allocates_technician", "Assignment Allocates Technician"
        SERVICE_REQUEST_TARGETS_ASSET = "service_request_targets_asset", "Service Request Targets Asset"
        SERVICE_REQUEST_LINKED_TO_SITE = "service_request_linked_to_site", "Service Request Linked To Site"
        SIMILAR_CONTEXT = "similar_context", "Similar Context"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="graph_edges",
        null=True,
        blank=True,
    )
    site = models.ForeignKey(
        "smart_system.OperationalSite",
        on_delete=models.SET_NULL,
        related_name="graph_edges",
        null=True,
        blank=True,
    )
    edge_type = models.CharField(max_length=60, choices=EdgeType.choices, db_index=True)
    from_node = models.ForeignKey("ai_knowledge_graph.GraphNode", on_delete=models.CASCADE, related_name="outgoing_edges")
    to_node = models.ForeignKey("ai_knowledge_graph.GraphNode", on_delete=models.CASCADE, related_name="incoming_edges")
    weight = models.DecimalField(max_digits=8, decimal_places=2, default=1)
    attributes = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ai_knowledge_graph_edges"
        ordering = ["-weight", "edge_type"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "edge_type", "from_node", "to_node"],
                name="uniq_knowledge_graph_edge",
            ),
        ]
        indexes = [
            models.Index(fields=["company", "site", "edge_type"], name="knowledge_graph_edge_scope_idx"),
        ]


class GraphProjectionRun(models.Model):
    class ProjectionType(models.TextChoices):
        FULL = "full_projection", "Full Projection"
        EVENT_REFRESH = "event_refresh", "Event Refresh"
        TARGETED = "targeted_projection", "Targeted Projection"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        RUNNING = "running", "Running"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    projection_type = models.CharField(max_length=40, choices=ProjectionType.choices, db_index=True)
    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="graph_projection_runs",
        null=True,
        blank=True,
    )
    site = models.ForeignKey(
        "smart_system.OperationalSite",
        on_delete=models.SET_NULL,
        related_name="graph_projection_runs",
        null=True,
        blank=True,
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True)
    summary = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    started_at = models.DateTimeField(default=timezone.now)
    finished_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ai_knowledge_graph_projection_runs"
        ordering = ["-created_at"]

