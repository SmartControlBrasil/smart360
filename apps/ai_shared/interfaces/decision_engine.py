from __future__ import annotations


def get_decision_orchestrator():
    from apps.ai_decision_engine.services.orchestrator import DecisionOrchestrator

    return DecisionOrchestrator


def get_decision_execution_service():
    from apps.ai_decision_engine.services.execution import DecisionExecutionService

    return DecisionExecutionService
