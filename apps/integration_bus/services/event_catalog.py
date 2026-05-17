from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EventCatalogEntry:
    event_name: str
    description: str
    priority: str = "normal"


EVENT_CATALOG: dict[str, EventCatalogEntry] = {
    "assets.created": EventCatalogEntry("assets.created", "Novo ativo criado.", "normal"),
    "assets.updated": EventCatalogEntry("assets.updated", "Ativo atualizado.", "normal"),
    "assets.status_changed": EventCatalogEntry("assets.status_changed", "Status do ativo alterado.", "high"),
    "work_orders.created": EventCatalogEntry("work_orders.created", "Ordem de servico criada.", "normal"),
    "work_orders.assigned": EventCatalogEntry("work_orders.assigned", "Ordem atribuida.", "normal"),
    "work_orders.started": EventCatalogEntry("work_orders.started", "Execucao iniciada.", "normal"),
    "work_orders.completed": EventCatalogEntry("work_orders.completed", "Ordem concluida.", "normal"),
    "work_orders.reopened": EventCatalogEntry("work_orders.reopened", "Ordem reaberta.", "high"),
    "work_orders.delayed": EventCatalogEntry("work_orders.delayed", "OS em atraso.", "high"),
    "preventive.created": EventCatalogEntry("preventive.created", "Preventiva criada.", "normal"),
    "preventive.scheduled": EventCatalogEntry("preventive.scheduled", "Preventiva agendada.", "normal"),
    "preventive.completed": EventCatalogEntry("preventive.completed", "Preventiva concluida.", "normal"),
    "preventive.overdue": EventCatalogEntry("preventive.overdue", "Preventiva vencida.", "high"),
    "failures.created": EventCatalogEntry("failures.created", "Falha criada.", "critical"),
    "failures.rca_updated": EventCatalogEntry("failures.rca_updated", "RCA atualizada.", "high"),
    "checklists.started": EventCatalogEntry("checklists.started", "Checklist iniciado.", "normal"),
    "checklists.completed": EventCatalogEntry("checklists.completed", "Checklist concluido.", "normal"),
    "checklists.nok_detected": EventCatalogEntry("checklists.nok_detected", "Nao conformidade detectada.", "high"),
    "execution.started": EventCatalogEntry("execution.started", "Execucao de campo iniciada.", "normal"),
    "execution.updated": EventCatalogEntry("execution.updated", "Execucao de campo atualizada.", "normal"),
    "execution.completed": EventCatalogEntry("execution.completed", "Execucao de campo concluida.", "normal"),
    "inventory.adjusted": EventCatalogEntry("inventory.adjusted", "Estoque ajustado.", "normal"),
    "inventory.low_stock_detected": EventCatalogEntry("inventory.low_stock_detected", "Estoque baixo detectado.", "high"),
    "inventory.consumed": EventCatalogEntry("inventory.consumed", "Consumo de item registrado.", "normal"),
    "quotes.created": EventCatalogEntry("quotes.created", "Orcamento criado.", "normal"),
    "quotes.sent": EventCatalogEntry("quotes.sent", "Orcamento enviado.", "normal"),
    "quotes.approved": EventCatalogEntry("quotes.approved", "Orcamento aprovado.", "high"),
    "quotes.rejected": EventCatalogEntry("quotes.rejected", "Orcamento rejeitado.", "high"),
    "contracts.created": EventCatalogEntry("contracts.created", "Contrato criado.", "normal"),
    "contracts.activated": EventCatalogEntry("contracts.activated", "Contrato ativado.", "high"),
    "contracts.suspended": EventCatalogEntry("contracts.suspended", "Contrato suspenso.", "high"),
    "contracts.expired": EventCatalogEntry("contracts.expired", "Contrato expirado.", "high"),
    "billing.invoice_created": EventCatalogEntry("billing.invoice_created", "Fatura criada.", "normal"),
    "billing.invoice_paid": EventCatalogEntry("billing.invoice_paid", "Fatura paga.", "normal"),
    "billing.invoice_overdue": EventCatalogEntry("billing.invoice_overdue", "Fatura vencida.", "critical"),
    "marketplace.request_created": EventCatalogEntry("marketplace.request_created", "Request marketplace criado.", "high"),
    "marketplace.offer_received": EventCatalogEntry("marketplace.offer_received", "Oferta recebida.", "normal"),
    "marketplace.assignment_created": EventCatalogEntry("marketplace.assignment_created", "Assignment criado.", "high"),
    "marketplace.assignment_cancelled": EventCatalogEntry("marketplace.assignment_cancelled", "Assignment cancelado.", "high"),
    "agents.recommendation_created": EventCatalogEntry("agents.recommendation_created", "Recomendacao criada.", "high"),
    "agents.action_proposed": EventCatalogEntry("agents.action_proposed", "Acao proposta por agente.", "high"),
    "agents.anomaly_detected": EventCatalogEntry("agents.anomaly_detected", "Anomalia detectada.", "critical"),
    "decision.awaiting_approval": EventCatalogEntry("decision.awaiting_approval", "Decisao aguardando aprovacao.", "critical"),
    "decision.approved": EventCatalogEntry("decision.approved", "Decisao aprovada.", "high"),
    "decision.rejected": EventCatalogEntry("decision.rejected", "Decisao rejeitada.", "high"),
    "decision.executed": EventCatalogEntry("decision.executed", "Decisao executada.", "high"),
    "simulation.completed": EventCatalogEntry("simulation.completed", "Simulacao concluida.", "high"),
    "briefing.generated": EventCatalogEntry("briefing.generated", "Briefing gerado.", "normal"),
    "copilot.query_received": EventCatalogEntry("copilot.query_received", "Consulta ao copilot recebida.", "normal"),
    "autonomy.execution_started": EventCatalogEntry("autonomy.execution_started", "Autoexecucao iniciada.", "high"),
    "autonomy.execution_completed": EventCatalogEntry("autonomy.execution_completed", "Autoexecucao concluida.", "high"),
    "autonomy.execution_failed": EventCatalogEntry("autonomy.execution_failed", "Autoexecucao falhou.", "critical"),
}


SYSTEM_EVENT_ALIASES = {
    "contract.activated": "contracts.activated",
    "contract.suspended": "contracts.suspended",
    "contract.expired": "contracts.expired",
    "agent.maintenance.recommendation.created": "agents.recommendation_created",
    "agent.scheduling.recommendation.created": "agents.recommendation_created",
    "agent.profitability.recommendation.created": "agents.recommendation_created",
    "agent.marketplace.recommendation.created": "agents.recommendation_created",
    "agent.anomaly.pattern.detected": "agents.anomaly_detected",
    "decision.execution.succeeded": "decision.executed",
    "simulation.run.completed": "simulation.completed",
    "autonomy.execution.succeeded": "autonomy.execution_completed",
    "autonomy.execution.started": "autonomy.execution_started",
    "autonomy.execution.failed": "autonomy.execution_failed",
    "marketplace.request.created": "marketplace.request_created",
}


def normalize_event_name(event_name: str) -> str:
    return SYSTEM_EVENT_ALIASES.get(event_name, event_name)


def event_priority_for(event_name: str, fallback: str = "normal") -> str:
    normalized = normalize_event_name(event_name)
    return EVENT_CATALOG.get(normalized, EventCatalogEntry(normalized, normalized, fallback)).priority
