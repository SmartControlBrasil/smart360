from __future__ import annotations


def get_autonomous_operations_service():
    from apps.ai_autonomous_ops.services.orchestrator import AutonomousOperationsService

    return AutonomousOperationsService
