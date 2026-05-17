from __future__ import annotations


def get_agent_coordinator():
    from apps.ai_agents_center.services.orchestrator import AgentCoordinatorService

    return AgentCoordinatorService
