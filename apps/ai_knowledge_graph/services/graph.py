from __future__ import annotations

from collections import defaultdict, deque
from decimal import Decimal

from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone
from django.utils.text import slugify

from apps.ai_agents_center.models import AgentAnomalyAttentionFlag, AgentRecommendation
from apps.ai_decision_engine.models import AgentDecision
from apps.integration_bus.models import IntegrationEvent
from apps.marketplace_technicians.models import TechnicianAssignment, TechnicianMatchingRecord, TechnicianProfile, TechnicianServiceRequest, TechnicianSkillAssignment
from apps.observability_center.services.observability_service import SystemEventService
from apps.smart_system.models import Asset, ContractAsset, FailureEvent, MaintenanceContract, MaintenancePlan, OperationalSite, Part, ServiceOrder, ServiceOrderChecklistResponse, ServiceQuote, StockMovement

from ..models import GraphEdge, GraphNode, GraphProjectionRun


def _normalize_reference(value) -> str:
    return str(value) if value else ""


class GraphProjectionService:
    @classmethod
    def _node(cls, *, company, site=None, node_type, source_type, source_id, label, attributes=None, strength=1):
        node, created = GraphNode.objects.update_or_create(
            company=company,
            node_type=node_type,
            source_type=source_type,
            source_id=_normalize_reference(source_id),
            defaults={
                "site": site,
                "label": label[:255],
                "attributes": attributes or {},
                "strength": strength,
            },
        )
        if created:
            SystemEventService.log_system_event(
                event_type="graph.node.created",
                source_module="ai_knowledge_graph",
                message=f"No {node_type} criado no knowledge graph.",
                entity_type="graph_node",
                entity_id=str(node.public_id),
                company=company,
                site=site,
                payload={"node_type": node_type, "source_type": source_type, "source_id": _normalize_reference(source_id)},
            )
        return node

    @classmethod
    def _edge(cls, *, company, site=None, edge_type, from_node, to_node, weight=1, attributes=None):
        edge, created = GraphEdge.objects.update_or_create(
            company=company,
            edge_type=edge_type,
            from_node=from_node,
            to_node=to_node,
            defaults={
                "site": site,
                "weight": Decimal(str(weight)),
                "attributes": attributes or {},
            },
        )
        if created:
            SystemEventService.log_system_event(
                event_type="graph.edge.created",
                source_module="ai_knowledge_graph",
                message=f"Relacao {edge_type} criada no knowledge graph.",
                entity_type="graph_edge",
                entity_id=str(edge.public_id),
                company=company,
                site=site,
                payload={"edge_type": edge_type, "from": str(from_node.public_id), "to": str(to_node.public_id)},
            )
        return edge

    @classmethod
    def _company_scope(cls, *, company, site=None):
        assets = Asset.objects.filter(operational_site__maintenance_client__company=company)
        if site is not None:
            assets = assets.filter(operational_site=site)
        return {
            "sites": OperationalSite.objects.filter(maintenance_client__company=company, **({"id": site.id} if site else {})),
            "assets": assets.select_related("operational_site", "category", "operational_site__maintenance_client"),
            "failures": FailureEvent.objects.filter(asset__operational_site__maintenance_client__company=company, **({"asset__operational_site": site} if site else {})).select_related("asset", "service_order", "asset__category", "asset__operational_site"),
            "orders": ServiceOrder.objects.filter(client__company=company, **({"operational_site": site} if site else {})).select_related("asset", "assigned_to", "operational_site", "maintenance_plan", "maintenance_contract"),
            "plans": MaintenancePlan.objects.filter(company=company, **({"operational_site": site} if site else {})).select_related("asset", "operational_site", "checklist"),
            "contract_assets": ContractAsset.objects.filter(contract__company=company, **({"contract__operational_site": site} if site else {})).select_related("contract", "asset", "asset__category"),
            "quotes": ServiceQuote.objects.filter(company=company, **({"operational_site": site} if site else {})).select_related("asset", "work_order"),
            "parts": Part.objects.filter(company=company, **({"operational_site": site} if site else {})).select_related("operational_site"),
            "stock_movements": StockMovement.objects.filter(company=company, **({"operational_site": site} if site else {})).select_related("part", "service_order", "service_order__asset"),
            "recommendations": AgentRecommendation.objects.filter(
            company=company,
            **({"site": site} if site else {}),
            ).select_related("company", "site", "agent_run", "agent_run__agent"),
            "decisions": AgentDecision.objects.filter(company=company, **({"site": site} if site else {})).select_related("agent_action_proposal", "policy_applied"),
            "anomalies": AgentAnomalyAttentionFlag.objects.filter(company=company, **({"site": site} if site else {})).select_related("asset", "site", "contract", "part", "technician"),
            "requests": TechnicianServiceRequest.objects.filter(requester_company=company, **({"related_site": site} if site else {})).select_related("related_site", "related_asset", "related_service_order"),
            "assignments": TechnicianAssignment.objects.filter(technician_service_request__requester_company=company, **({"technician_service_request__related_site": site} if site else {})).select_related("technician_profile", "technician_service_request"),
        }

    @classmethod
    @transaction.atomic
    def project_company_graph(cls, *, company, site=None, projection_type=GraphProjectionRun.ProjectionType.FULL, trigger_event=None):
        run = GraphProjectionRun.objects.create(
            projection_type=projection_type,
            company=company,
            site=site,
            status=GraphProjectionRun.Status.RUNNING,
            metadata={"trigger_event": str(getattr(trigger_event, "public_id", ""))},
        )
        SystemEventService.log_system_event(
            event_type="graph.projection.started",
            source_module="ai_knowledge_graph",
            message="Projecao do knowledge graph iniciada.",
            entity_type="graph_projection_run",
            entity_id=str(run.public_id),
            company=company,
            site=site,
            payload={"projection_type": projection_type},
        )
        scope = cls._company_scope(company=company, site=site)
        stats = defaultdict(int)

        company_node = cls._node(
            company=company,
            site=site,
            node_type=GraphNode.NodeType.COMPANY,
            source_type="companies.company",
            source_id=company.public_id,
            label=company.name,
            attributes={"status": company.status, "slug": company.slug},
        )
        stats["nodes"] += 1

        site_nodes = {}
        for operational_site in scope["sites"]:
            site_node = cls._node(
                company=company,
                site=operational_site,
                node_type=GraphNode.NodeType.SITE,
                source_type="smart_system.operationalsite",
                source_id=operational_site.public_id,
                label=operational_site.name,
                attributes={"code": operational_site.code, "city": operational_site.city, "state": operational_site.state},
            )
            site_nodes[operational_site.id] = site_node
            cls._edge(company=company, site=operational_site, edge_type=GraphEdge.EdgeType.COMPANY_OWNS_SITE, from_node=company_node, to_node=site_node, weight=1)
            stats["nodes"] += 1
            stats["edges"] += 1

        category_nodes = {}
        asset_nodes = {}
        technician_nodes = {}

        for asset in scope["assets"]:
            asset_site_node = site_nodes.get(asset.operational_site_id)
            category_node = category_nodes.setdefault(
                asset.category_id,
                cls._node(
                    company=company,
                    site=asset.operational_site,
                    node_type=GraphNode.NodeType.ASSET_CATEGORY,
                    source_type="smart_system.assetcategory",
                    source_id=asset.category.public_id,
                    label=asset.category.name,
                    attributes={"slug": asset.category.slug},
                ),
            )
            asset_node = cls._node(
                company=company,
                site=asset.operational_site,
                node_type=GraphNode.NodeType.ASSET,
                source_type="smart_system.asset",
                source_id=asset.public_id,
                label=f"{asset.asset_tag} - {asset.name}",
                attributes={"asset_tag": asset.asset_tag, "status": asset.status, "criticality": asset.criticality},
                strength=4 if asset.criticality in {"high", "critical"} else 2,
            )
            asset_nodes[asset.id] = asset_node
            cls._edge(company=company, site=asset.operational_site, edge_type=GraphEdge.EdgeType.ASSET_LOCATED_AT_SITE, from_node=asset_node, to_node=asset_site_node, weight=1)
            cls._edge(company=company, site=asset.operational_site, edge_type=GraphEdge.EdgeType.ASSET_BELONGS_TO_CATEGORY, from_node=asset_node, to_node=category_node, weight=1)
            stats["nodes"] += 2
            stats["edges"] += 2

        for contract_asset in scope["contract_assets"]:
            contract = contract_asset.contract
            contract_node = cls._node(
                company=company,
                site=contract.operational_site,
                node_type=GraphNode.NodeType.CONTRACT,
                source_type="smart_system.maintenancecontract",
                source_id=contract.public_id,
                label=contract.contract_number,
                attributes={"status": contract.status, "contract_value": str(contract.contract_value)},
                strength=3,
            )
            asset_node = asset_nodes.get(contract_asset.asset_id)
            if asset_node:
                cls._edge(company=company, site=contract.operational_site, edge_type=GraphEdge.EdgeType.CONTRACT_COVERS_ASSET, from_node=contract_node, to_node=asset_node, weight=2)
                cls._edge(company=company, site=contract.operational_site, edge_type=GraphEdge.EdgeType.COMPANY_HAS_CONTRACT, from_node=company_node, to_node=contract_node, weight=1)
                stats["nodes"] += 1
                stats["edges"] += 2

        for failure in scope["failures"]:
            asset_node = asset_nodes.get(failure.asset_id)
            if asset_node is None:
                continue
            failure_node = cls._node(
                company=company,
                site=failure.asset.operational_site,
                node_type=GraphNode.NodeType.FAILURE_EVENT,
                source_type="smart_system.failureevent",
                source_id=failure.public_id,
                label=f"Falha: {failure.asset.name}",
                attributes={"severity": failure.severity, "status": failure.status, "symptom": failure.symptom},
                strength=4 if failure.severity in {"high", "critical"} else 2,
            )
            cls._edge(company=company, site=failure.asset.operational_site, edge_type=GraphEdge.EdgeType.ASSET_HAS_FAILURE, from_node=asset_node, to_node=failure_node, weight=2)
            if failure.symptom:
                mode_node = cls._node(
                    company=company,
                    site=failure.asset.operational_site,
                    node_type=GraphNode.NodeType.FAILURE_MODE,
                    source_type="derived.failure_mode",
                    source_id=slugify(failure.symptom)[:120],
                    label=failure.symptom[:255],
                    attributes={"source": "failure.symptom"},
                )
                cls._edge(company=company, site=failure.asset.operational_site, edge_type=GraphEdge.EdgeType.FAILURE_HAS_MODE, from_node=failure_node, to_node=mode_node, weight=2)
                stats["nodes"] += 1
                stats["edges"] += 1
            cause_text = failure.root_cause or failure.probable_cause
            if cause_text:
                cause_node = cls._node(
                    company=company,
                    site=failure.asset.operational_site,
                    node_type=GraphNode.NodeType.RCA_CAUSE,
                    source_type="derived.rca_cause",
                    source_id=slugify(cause_text)[:120],
                    label=cause_text[:255],
                    attributes={"source": "failure.cause"},
                )
                cls._edge(company=company, site=failure.asset.operational_site, edge_type=GraphEdge.EdgeType.FAILURE_HAS_CAUSE, from_node=failure_node, to_node=cause_node, weight=2)
                stats["nodes"] += 1
                stats["edges"] += 1
            stats["nodes"] += 1
            stats["edges"] += 1

        for plan in scope["plans"]:
            if not plan.asset_id:
                continue
            asset_node = asset_nodes.get(plan.asset_id)
            if asset_node is None:
                continue
            plan_node = cls._node(
                company=company,
                site=plan.operational_site,
                node_type=GraphNode.NodeType.PREVENTIVE_PLAN,
                source_type="smart_system.maintenanceplan",
                source_id=plan.public_id,
                label=plan.name,
                attributes={"frequency_type": plan.frequency_type, "next_due_date": str(plan.next_due_date)},
            )
            cls._edge(company=company, site=plan.operational_site, edge_type=GraphEdge.EdgeType.PREVENTIVE_TARGETS_ASSET, from_node=plan_node, to_node=asset_node, weight=1)
            if plan.checklist_id:
                checklist_node = cls._node(
                    company=company,
                    site=plan.operational_site,
                    node_type=GraphNode.NodeType.CHECKLIST,
                    source_type="smart_system.checklist",
                    source_id=plan.checklist.public_id,
                    label=plan.checklist.name,
                    attributes={},
                )
                cls._edge(company=company, site=plan.operational_site, edge_type=GraphEdge.EdgeType.CHECKLIST_USED_IN_WORK_ORDER, from_node=checklist_node, to_node=plan_node, weight=1)
                stats["nodes"] += 1
                stats["edges"] += 1
            stats["nodes"] += 1
            stats["edges"] += 1

        category_technician_counter = defaultdict(int)
        for order in scope["orders"]:
            order_node = cls._node(
                company=company,
                site=order.operational_site,
                node_type=GraphNode.NodeType.WORK_ORDER,
                source_type="smart_system.serviceorder",
                source_id=order.public_id,
                label=order.order_number,
                attributes={"status": order.status, "priority": order.priority, "maintenance_type": order.maintenance_type},
                strength=3 if order.priority in {"high", "urgent"} else 1,
            )
            stats["nodes"] += 1
            asset_node = asset_nodes.get(order.asset_id)
            if asset_node:
                cls._edge(company=company, site=order.operational_site, edge_type=GraphEdge.EdgeType.WORK_ORDER_TARGETS_ASSET, from_node=order_node, to_node=asset_node, weight=2)
                stats["edges"] += 1
            if order.assigned_to_id:
                tech_node = technician_nodes.setdefault(
                    order.assigned_to_id,
                    cls._node(
                        company=company,
                        site=order.operational_site,
                        node_type=GraphNode.NodeType.TECHNICIAN,
                        source_type="users.user",
                        source_id=order.assigned_to_id,
                        label=getattr(order.assigned_to, "display_name", None) or order.assigned_to.get_full_name() or order.assigned_to.email,
                        attributes={"email": order.assigned_to.email},
                        strength=2,
                    ),
                )
                cls._edge(company=company, site=order.operational_site, edge_type=GraphEdge.EdgeType.TECHNICIAN_EXECUTED_WORK_ORDER, from_node=tech_node, to_node=order_node, weight=2 if order.status == "completed" else 1)
                stats["nodes"] += 1
                stats["edges"] += 1
                if order.asset_id and order.asset.category_id:
                    category_technician_counter[(order.assigned_to_id, order.asset.category_id)] += 1
            if order.maintenance_plan_id and order.maintenance_plan.checklist_id:
                checklist_node = cls._node(
                    company=company,
                    site=order.operational_site,
                    node_type=GraphNode.NodeType.CHECKLIST,
                    source_type="smart_system.checklist",
                    source_id=order.maintenance_plan.checklist.public_id,
                    label=order.maintenance_plan.checklist.name,
                    attributes={},
                )
                cls._edge(company=company, site=order.operational_site, edge_type=GraphEdge.EdgeType.CHECKLIST_USED_IN_WORK_ORDER, from_node=checklist_node, to_node=order_node, weight=1)
                stats["nodes"] += 1
                stats["edges"] += 1

        for response in ServiceOrderChecklistResponse.objects.filter(service_order__client__company=company, **({"service_order__operational_site": site} if site else {})).select_related("checklist_item", "service_order", "service_order__operational_site"):
            if response.response_boolean is not False:
                continue
            item_node = cls._node(
                company=company,
                site=response.service_order.operational_site,
                node_type=GraphNode.NodeType.CHECKLIST_ITEM,
                source_type="smart_system.checklistitem",
                source_id=response.checklist_item.public_id,
                label=response.checklist_item.title,
                attributes={"item_type": response.checklist_item.item_type},
            )
            order_node = cls._node(
                company=company,
                site=response.service_order.operational_site,
                node_type=GraphNode.NodeType.WORK_ORDER,
                source_type="smart_system.serviceorder",
                source_id=response.service_order.public_id,
                label=response.service_order.order_number,
                attributes={"status": response.service_order.status, "priority": response.service_order.priority},
            )
            cls._edge(company=company, site=response.service_order.operational_site, edge_type=GraphEdge.EdgeType.CHECKLIST_ITEM_FLAGGED_ISSUE, from_node=item_node, to_node=order_node, weight=2, attributes={"response": "nok"})
            stats["nodes"] += 2
            stats["edges"] += 1

        for quote in scope["quotes"]:
            quote_node = cls._node(
                company=company,
                site=quote.operational_site,
                node_type=GraphNode.NodeType.QUOTE,
                source_type="smart_system.servicequote",
                source_id=quote.public_id,
                label=quote.quote_number,
                attributes={"status": quote.status, "total_value": str(quote.total_value)},
            )
            work_order_node = cls._node(
                company=company,
                site=quote.operational_site,
                node_type=GraphNode.NodeType.WORK_ORDER,
                source_type="smart_system.serviceorder",
                source_id=quote.work_order.public_id,
                label=quote.work_order.order_number,
                attributes={"status": quote.work_order.status, "priority": quote.work_order.priority},
            )
            cls._edge(company=company, site=quote.operational_site, edge_type=GraphEdge.EdgeType.SIMILAR_CONTEXT, from_node=quote_node, to_node=work_order_node, weight=1, attributes={"reason": "quote_for_work_order"})
            stats["nodes"] += 2
            stats["edges"] += 1

        for part in scope["parts"]:
            part_node = cls._node(
                company=company,
                site=part.operational_site,
                node_type=GraphNode.NodeType.PART,
                source_type="smart_system.part",
                source_id=part.public_id,
                label=f"{part.code} - {part.name}",
                attributes={"stock": str(part.current_stock), "minimum_stock": str(part.minimum_stock)},
            )
            stats["nodes"] += 1
            for link in part.asset_links.select_related("asset")[:10]:
                asset_node = asset_nodes.get(link.asset_id)
                if asset_node:
                    cls._edge(company=company, site=part.operational_site, edge_type=GraphEdge.EdgeType.PART_RELATED_TO_ASSET, from_node=part_node, to_node=asset_node, weight=link.quantity_recommended or 1)
                    stats["edges"] += 1

        for movement in scope["stock_movements"]:
            if not movement.service_order_id:
                continue
            part_node = cls._node(
                company=company,
                site=movement.operational_site,
                node_type=GraphNode.NodeType.PART,
                source_type="smart_system.part",
                source_id=movement.part.public_id,
                label=f"{movement.part.code} - {movement.part.name}",
                attributes={"stock": str(movement.part.current_stock)},
            )
            order_node = cls._node(
                company=company,
                site=movement.operational_site,
                node_type=GraphNode.NodeType.WORK_ORDER,
                source_type="smart_system.serviceorder",
                source_id=movement.service_order.public_id,
                label=movement.service_order.order_number,
                attributes={"status": movement.service_order.status, "priority": movement.service_order.priority},
            )
            cls._edge(company=company, site=movement.operational_site, edge_type=GraphEdge.EdgeType.PART_USED_IN_WORK_ORDER, from_node=part_node, to_node=order_node, weight=movement.quantity, attributes={"movement_type": movement.movement_type})
            stats["nodes"] += 2
            stats["edges"] += 1

        for technician in TechnicianProfile.objects.filter(Q(company=company) | Q(company__isnull=True), is_active=True).select_related("user", "company"):
            tech_node = technician_nodes.setdefault(
                technician.user_id,
                cls._node(
                    company=company,
                    site=site,
                    node_type=GraphNode.NodeType.TECHNICIAN,
                    source_type="marketplace_technicians.technicianprofile",
                    source_id=technician.public_id,
                    label=technician.display_name,
                    attributes={"rating_average": str(technician.rating_average), "completed_jobs_count": technician.completed_jobs_count},
                    strength=2,
                ),
            )
            stats["nodes"] += 1
            for assignment in TechnicianSkillAssignment.objects.filter(technician_profile=technician).select_related("skill"):
                skill_node = cls._node(
                    company=company,
                    site=site,
                    node_type=GraphNode.NodeType.SKILL,
                    source_type="marketplace_technicians.technicianskill",
                    source_id=assignment.skill.public_id,
                    label=assignment.skill.name,
                    attributes={"slug": assignment.skill.slug},
                )
                cls._edge(company=company, site=site, edge_type=GraphEdge.EdgeType.TECHNICIAN_HAS_SKILL, from_node=tech_node, to_node=skill_node, weight=assignment.years_experience or 1, attributes={"proficiency": assignment.proficiency_level})
                stats["nodes"] += 1
                stats["edges"] += 1

        for (technician_user_id, category_id), weight in category_technician_counter.items():
            tech_node = technician_nodes.get(technician_user_id)
            category_node = category_nodes.get(category_id)
            if tech_node and category_node:
                cls._edge(company=company, site=site, edge_type=GraphEdge.EdgeType.TECHNICIAN_BEST_FIT_FOR_CATEGORY, from_node=tech_node, to_node=category_node, weight=weight)
                stats["edges"] += 1

        for recommendation in scope["recommendations"]:
            recommendation_node = cls._node(
                company=company,
                site=recommendation.site,
                node_type=GraphNode.NodeType.RECOMMENDATION,
                source_type="ai_agents_center.agentrecommendation",
                source_id=recommendation.public_id,
                label=recommendation.title,
                attributes={"severity": recommendation.severity, "priority": recommendation.priority, "status": recommendation.status},
                strength=3 if recommendation.severity in {"high", "critical"} else 1,
            )
            target_node = asset_nodes.get(recommendation.asset_id) or site_nodes.get(recommendation.site_id)
            if target_node:
                cls._edge(company=company, site=recommendation.site, edge_type=GraphEdge.EdgeType.RECOMMENDATION_TARGETS_ASSET, from_node=recommendation_node, to_node=target_node, weight=2)
                stats["edges"] += 1
            stats["nodes"] += 1

        for decision in scope["decisions"]:
            decision_node = cls._node(
                company=company,
                site=decision.site,
                node_type=GraphNode.NodeType.DECISION,
                source_type="ai_decision_engine.agentdecision",
                source_id=decision.public_id,
                label=decision.normalized_action_type,
                attributes={"risk_level": decision.risk_level, "status": decision.decision_status},
                strength=3 if decision.risk_level in {"high", "critical"} else 1,
            )
            target_node = None
            if decision.target_entity == "asset":
                target_node = GraphQueryService.node_for_entity(company=company, entity_type="asset", entity_public_id=decision.target_entity_id)
            elif decision.site_id:
                target_node = site_nodes.get(decision.site_id)
            if target_node:
                cls._edge(company=company, site=decision.site, edge_type=GraphEdge.EdgeType.DECISION_ACTS_ON_ENTITY, from_node=decision_node, to_node=target_node, weight=2)
                stats["edges"] += 1
            stats["nodes"] += 1

        for anomaly in scope["anomalies"]:
            anomaly_node = cls._node(
                company=company,
                site=anomaly.site,
                node_type=GraphNode.NodeType.ANOMALY,
                source_type="ai_agents_center.agentanomalyattentionflag",
                source_id=anomaly.public_id,
                label=anomaly.display_label,
                attributes={"focus_type": anomaly.focus_type, "risk_level": anomaly.risk_level},
                strength=3 if anomaly.risk_level in {"high", "critical"} else 1,
            )
            target_node = None
            if anomaly.asset_id:
                target_node = asset_nodes.get(anomaly.asset_id)
            elif anomaly.site_id:
                target_node = site_nodes.get(anomaly.site_id)
            elif anomaly.contract_id:
                target_node = GraphQueryService.node_for_entity(company=company, entity_type="contract", entity_public_id=anomaly.contract.public_id)
            if target_node:
                cls._edge(company=company, site=anomaly.site, edge_type=GraphEdge.EdgeType.ANOMALY_DETECTED_ON_ENTITY, from_node=anomaly_node, to_node=target_node, weight=2)
                stats["edges"] += 1
            stats["nodes"] += 1

        request_nodes = {}
        for request in scope["requests"]:
            request_node = cls._node(
                company=company,
                site=request.related_site,
                node_type=GraphNode.NodeType.SERVICE_REQUEST,
                source_type="marketplace_technicians.technicianservicerequest",
                source_id=request.public_id,
                label=request.title,
                attributes={"status": request.status, "priority": request.priority, "service_type": request.service_type},
                strength=2 if request.priority in {"high", "urgent"} else 1,
            )
            request_nodes[request.id] = request_node
            if request.related_site_id and request.related_site_id in site_nodes:
                cls._edge(company=company, site=request.related_site, edge_type=GraphEdge.EdgeType.SERVICE_REQUEST_LINKED_TO_SITE, from_node=request_node, to_node=site_nodes[request.related_site_id], weight=1)
                stats["edges"] += 1
            if request.related_asset_id and request.related_asset_id in asset_nodes:
                cls._edge(company=company, site=request.related_site, edge_type=GraphEdge.EdgeType.SERVICE_REQUEST_TARGETS_ASSET, from_node=request_node, to_node=asset_nodes[request.related_asset_id], weight=1)
                stats["edges"] += 1
            stats["nodes"] += 1

        for assignment in scope["assignments"]:
            request_node = request_nodes.get(assignment.technician_service_request_id)
            technician_node = GraphQueryService.node_for_entity(company=company, entity_type="technician", entity_public_id=assignment.technician_profile.public_id) or technician_nodes.get(assignment.technician_profile.user_id)
            assignment_node = cls._node(
                company=company,
                site=assignment.technician_service_request.related_site,
                node_type=GraphNode.NodeType.ASSIGNMENT,
                source_type="marketplace_technicians.technicianassignment",
                source_id=assignment.public_id,
                label=f"Assignment {assignment.public_id}",
                attributes={"status": assignment.assignment_status},
            )
            if request_node and technician_node:
                cls._edge(company=company, site=assignment.technician_service_request.related_site, edge_type=GraphEdge.EdgeType.ASSIGNMENT_ALLOCATES_TECHNICIAN, from_node=assignment_node, to_node=technician_node, weight=2)
                cls._edge(company=company, site=assignment.technician_service_request.related_site, edge_type=GraphEdge.EdgeType.SIMILAR_CONTEXT, from_node=assignment_node, to_node=request_node, weight=1, attributes={"reason": "assignment_for_request"})
                stats["edges"] += 2
            stats["nodes"] += 1

        run.status = GraphProjectionRun.Status.COMPLETED
        run.summary = f"{stats['nodes']} nodes and {stats['edges']} edges processed."
        run.finished_at = timezone.now()
        run.save(update_fields=["status", "summary", "finished_at", "updated_at"])
        SystemEventService.log_system_event(
            event_type="graph.projection.completed",
            source_module="ai_knowledge_graph",
            message="Projecao do knowledge graph concluida.",
            entity_type="graph_projection_run",
            entity_id=str(run.public_id),
            company=company,
            site=site,
            payload={"projection_type": projection_type, "stats": dict(stats)},
        )
        return run

    @classmethod
    def project_from_event(cls, *, integration_event: IntegrationEvent):
        company = integration_event.company
        if company is None and integration_event.site_id:
            company = integration_event.site.maintenance_client.company
        if company is None:
            return None
        return cls.project_company_graph(
            company=company,
            site=integration_event.site,
            projection_type=GraphProjectionRun.ProjectionType.EVENT_REFRESH,
            trigger_event=integration_event,
        )


class GraphQueryService:
    @classmethod
    def _scoped_nodes(cls, *, company, site=None):
        queryset = GraphNode.objects.filter(company=company)
        if site is not None:
            queryset = queryset.filter(Q(site=site) | Q(site__isnull=True))
        return queryset

    @classmethod
    def _scoped_edges(cls, *, company, site=None):
        queryset = GraphEdge.objects.select_related("from_node", "to_node").filter(company=company)
        if site is not None:
            queryset = queryset.filter(Q(site=site) | Q(site__isnull=True))
        return queryset

    @classmethod
    def node_for_entity(cls, *, company, entity_type, entity_public_id):
        mapping = {
            "asset": GraphNode.NodeType.ASSET,
            "site": GraphNode.NodeType.SITE,
            "company": GraphNode.NodeType.COMPANY,
            "contract": GraphNode.NodeType.CONTRACT,
            "recommendation": GraphNode.NodeType.RECOMMENDATION,
            "decision": GraphNode.NodeType.DECISION,
            "technician": GraphNode.NodeType.TECHNICIAN,
            "service_request": GraphNode.NodeType.SERVICE_REQUEST,
        }
        node_type = mapping.get(entity_type, entity_type)
        return GraphNode.objects.filter(company=company, node_type=node_type, source_id=str(entity_public_id)).first()

    @classmethod
    def related_failures(cls, *, company, asset_public_id):
        asset_node = cls.node_for_entity(company=company, entity_type="asset", entity_public_id=asset_public_id)
        if asset_node is None:
            return []
        edges = cls._scoped_edges(company=company).filter(from_node=asset_node, edge_type=GraphEdge.EdgeType.ASSET_HAS_FAILURE).order_by("-weight", "-updated_at")
        return [edge.to_node for edge in edges[:10]]

    @classmethod
    def related_parts(cls, *, company, asset_public_id=None, failure_mode=None):
        queryset = cls._scoped_edges(company=company)
        if asset_public_id:
            asset_node = cls.node_for_entity(company=company, entity_type="asset", entity_public_id=asset_public_id)
            if asset_node is None:
                return []
            related_orders = queryset.filter(to_node=asset_node, edge_type=GraphEdge.EdgeType.WORK_ORDER_TARGETS_ASSET).values_list("from_node_id", flat=True)
            part_edges = queryset.filter(to_node_id__in=related_orders, edge_type=GraphEdge.EdgeType.PART_USED_IN_WORK_ORDER)
            return [edge.from_node for edge in part_edges[:10]]
        if failure_mode:
            mode_nodes = cls._scoped_nodes(company=company).filter(node_type=GraphNode.NodeType.FAILURE_MODE, label__icontains=failure_mode)
            failure_ids = queryset.filter(to_node__in=mode_nodes, edge_type=GraphEdge.EdgeType.FAILURE_HAS_MODE).values_list("from_node_id", flat=True)
            asset_ids = queryset.filter(to_node_id__in=failure_ids, edge_type=GraphEdge.EdgeType.ASSET_HAS_FAILURE).values_list("from_node_id", flat=True)
            related_orders = queryset.filter(to_node_id__in=asset_ids, edge_type=GraphEdge.EdgeType.WORK_ORDER_TARGETS_ASSET).values_list("from_node_id", flat=True)
            return [edge.from_node for edge in queryset.filter(to_node_id__in=related_orders, edge_type=GraphEdge.EdgeType.PART_USED_IN_WORK_ORDER)[:10]]
        return []

    @classmethod
    def related_technicians(cls, *, company, asset_public_id=None, category_slug=None):
        queryset = cls._scoped_edges(company=company)
        if asset_public_id:
            asset_node = cls.node_for_entity(company=company, entity_type="asset", entity_public_id=asset_public_id)
            if asset_node is None:
                return []
            order_ids = queryset.filter(to_node=asset_node, edge_type=GraphEdge.EdgeType.WORK_ORDER_TARGETS_ASSET).values_list("from_node_id", flat=True)
            tech_edges = queryset.filter(to_node_id__in=order_ids, edge_type=GraphEdge.EdgeType.TECHNICIAN_EXECUTED_WORK_ORDER)
            return [edge.from_node for edge in tech_edges[:10]]
        if category_slug:
            category_node = cls._scoped_nodes(company=company).filter(node_type=GraphNode.NodeType.ASSET_CATEGORY, attributes__slug=category_slug).first()
            if category_node is None:
                return []
            tech_edges = queryset.filter(to_node=category_node, edge_type=GraphEdge.EdgeType.TECHNICIAN_BEST_FIT_FOR_CATEGORY).order_by("-weight")
            return [edge.from_node for edge in tech_edges[:10]]
        return []

    @classmethod
    def related_work_orders(cls, *, company, asset_public_id=None, failure_mode=None):
        queryset = cls._scoped_edges(company=company)
        if asset_public_id:
            asset_node = cls.node_for_entity(company=company, entity_type="asset", entity_public_id=asset_public_id)
            return [edge.from_node for edge in queryset.filter(to_node=asset_node, edge_type=GraphEdge.EdgeType.WORK_ORDER_TARGETS_ASSET)[:10]] if asset_node else []
        if failure_mode:
            mode_nodes = cls._scoped_nodes(company=company).filter(node_type=GraphNode.NodeType.FAILURE_MODE, label__icontains=failure_mode)
            failure_ids = queryset.filter(to_node__in=mode_nodes, edge_type=GraphEdge.EdgeType.FAILURE_HAS_MODE).values_list("from_node_id", flat=True)
            asset_ids = queryset.filter(to_node_id__in=failure_ids, edge_type=GraphEdge.EdgeType.ASSET_HAS_FAILURE).values_list("from_node_id", flat=True)
            return [edge.from_node for edge in queryset.filter(to_node_id__in=asset_ids, edge_type=GraphEdge.EdgeType.WORK_ORDER_TARGETS_ASSET)[:10]]
        return []

    @classmethod
    def related_recommendations(cls, *, company, entity_type, entity_public_id):
        target_node = cls.node_for_entity(company=company, entity_type=entity_type, entity_public_id=entity_public_id)
        if target_node is None:
            return []
        edges = cls._scoped_edges(company=company).filter(to_node=target_node, edge_type=GraphEdge.EdgeType.RECOMMENDATION_TARGETS_ASSET)
        return [edge.from_node for edge in edges[:10]]

    @classmethod
    def related_decisions(cls, *, company, entity_type, entity_public_id):
        target_node = cls.node_for_entity(company=company, entity_type=entity_type, entity_public_id=entity_public_id)
        if target_node is None:
            return []
        edges = cls._scoped_edges(company=company).filter(to_node=target_node, edge_type=GraphEdge.EdgeType.DECISION_ACTS_ON_ENTITY)
        return [edge.from_node for edge in edges[:10]]

    @classmethod
    def related_sites(cls, *, company):
        company_node = cls.node_for_entity(company=company, entity_type="company", entity_public_id=company.public_id)
        if company_node is None:
            return []
        edges = cls._scoped_edges(company=company).filter(from_node=company_node, edge_type=GraphEdge.EdgeType.COMPANY_OWNS_SITE)
        return [edge.to_node for edge in edges[:20]]

    @classmethod
    def related_contracts(cls, *, company, asset_public_id=None, site_public_id=None):
        queryset = cls._scoped_edges(company=company)
        if asset_public_id:
            asset_node = cls.node_for_entity(company=company, entity_type="asset", entity_public_id=asset_public_id)
            return [edge.from_node for edge in queryset.filter(to_node=asset_node, edge_type=GraphEdge.EdgeType.CONTRACT_COVERS_ASSET)[:10]] if asset_node else []
        if site_public_id:
            site_node = cls.node_for_entity(company=company, entity_type="site", entity_public_id=site_public_id)
            if site_node is None:
                return []
            asset_ids = queryset.filter(to_node=site_node, edge_type=GraphEdge.EdgeType.ASSET_LOCATED_AT_SITE).values_list("from_node_id", flat=True)
            return [edge.from_node for edge in queryset.filter(to_node_id__in=asset_ids, edge_type=GraphEdge.EdgeType.CONTRACT_COVERS_ASSET)[:10]]
        return []

    @classmethod
    def related_anomalies(cls, *, company, entity_type, entity_public_id):
        target_node = cls.node_for_entity(company=company, entity_type=entity_type, entity_public_id=entity_public_id)
        if target_node is None:
            return []
        edges = cls._scoped_edges(company=company).filter(to_node=target_node, edge_type=GraphEdge.EdgeType.ANOMALY_DETECTED_ON_ENTITY)
        return [edge.from_node for edge in edges[:10]]

    @classmethod
    def neighbors(cls, *, company, node_public_id, edge_type=None, hops=1):
        origin = GraphNode.objects.filter(company=company, public_id=node_public_id).first()
        if origin is None:
            return []
        seen = {origin.id}
        queue = deque([(origin, 0)])
        collected = []
        while queue:
            node, depth = queue.popleft()
            if depth >= hops:
                continue
            edges = cls._scoped_edges(company=company).filter(Q(from_node=node) | Q(to_node=node))
            if edge_type:
                edges = edges.filter(edge_type=edge_type)
            for edge in edges:
                neighbor = edge.to_node if edge.from_node_id == node.id else edge.from_node
                collected.append({"edge_type": edge.edge_type, "weight": float(edge.weight), "node": neighbor})
                if neighbor.id not in seen:
                    seen.add(neighbor.id)
                    queue.append((neighbor, depth + 1))
        SystemEventService.log_system_event(
            event_type="graph.query.executed",
            source_module="ai_knowledge_graph",
            message="Consulta de vizinhanca executada.",
            entity_type=origin.node_type,
            entity_id=origin.source_id,
            company=company,
            site=origin.site,
            payload={"query_type": "neighbors", "hops": hops, "edge_type": edge_type or "", "node_public_id": str(origin.public_id)},
        )
        return collected

    @classmethod
    def explanation_path(cls, *, company, from_public_id, to_public_id, max_hops=3):
        origin = GraphNode.objects.filter(company=company, public_id=from_public_id).first()
        target = GraphNode.objects.filter(company=company, public_id=to_public_id).first()
        if origin is None or target is None:
            return []
        queue = deque([(origin, [])])
        seen = {origin.id}
        while queue:
            node, path = queue.popleft()
            if len(path) >= max_hops:
                continue
            for edge_info in cls.neighbors(company=company, node_public_id=node.public_id, hops=1):
                neighbor = edge_info["node"]
                new_path = path + [{"from": node, "to": neighbor, "edge_type": edge_info["edge_type"], "weight": edge_info["weight"]}]
                if neighbor.id == target.id:
                    return new_path
                if neighbor.id not in seen:
                    seen.add(neighbor.id)
                    queue.append((neighbor, new_path))
        return []

    @classmethod
    def entity_context(cls, *, company, entity_type, entity_public_id):
        node = cls.node_for_entity(company=company, entity_type=entity_type, entity_public_id=entity_public_id)
        if node is None:
            return {}
        neighbors = cls.neighbors(company=company, node_public_id=node.public_id, hops=2)
        by_type = defaultdict(list)
        for item in neighbors:
            by_type[item["edge_type"]].append(
                {
                    "node_public_id": str(item["node"].public_id),
                    "label": item["node"].label,
                    "node_type": item["node"].node_type,
                    "weight": item["weight"],
                }
            )
        SystemEventService.log_system_event(
            event_type="graph.query.executed",
            source_module="ai_knowledge_graph",
            message="Consulta de contexto relacional executada.",
            entity_type=entity_type,
            entity_id=str(entity_public_id),
            company=company,
            site=node.site,
            payload={"query_type": "entity_context", "node_public_id": str(node.public_id)},
        )
        SystemEventService.log_system_event(
            event_type="graph.context.resolved",
            source_module="ai_knowledge_graph",
            message="Contexto relacional resolvido.",
            entity_type=entity_type,
            entity_id=str(entity_public_id),
            company=company,
            payload={"query_type": "entity_context", "node_public_id": str(node.public_id)},
        )
        return {
            "node": node,
            "neighbors": neighbors,
            "by_relation": dict(by_type),
        }


class GraphInsightService:
    @classmethod
    def insights_for_entity(cls, *, company, entity_type, entity_public_id):
        context = GraphQueryService.entity_context(company=company, entity_type=entity_type, entity_public_id=entity_public_id)
        node = context.get("node")
        if not node:
            return {}
        neighbors = context["neighbors"]
        ranked = sorted(neighbors, key=lambda item: item["weight"], reverse=True)
        top_relations = [
            {
                "edge_type": item["edge_type"],
                "label": item["node"].label,
                "node_type": item["node"].node_type,
                "weight": item["weight"],
            }
            for item in ranked[:8]
        ]
        relation_counter = defaultdict(int)
        for item in neighbors:
            relation_counter[item["edge_type"]] += 1
        clusters = [{"relation_type": key, "count": value} for key, value in sorted(relation_counter.items(), key=lambda entry: entry[1], reverse=True)[:6]]
        summary = f"{node.label} se conecta a {len(neighbors)} relacoes mapeadas no grafo."
        SystemEventService.log_system_event(
            event_type="graph.insight.generated",
            source_module="ai_knowledge_graph",
            message="Graph insight gerado.",
            entity_type=node.node_type,
            entity_id=node.source_id,
            company=company,
            site=node.site,
            payload={"node_public_id": str(node.public_id)},
        )
        return {
            "node": node,
            "summary": summary,
            "top_relations": top_relations,
            "clusters": clusters,
            "context_count": len(neighbors),
        }
