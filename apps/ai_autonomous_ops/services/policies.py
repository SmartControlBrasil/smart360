from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from apps.ai_autonomous_ops.models import AutonomousModeConfig
from apps.ai_decision_engine.models import AgentDecision

from .catalog import BLOCKED_ACTIONS, ELIGIBLE_ACTIONS


@dataclass(frozen=True)
class SafetyEnvelopeResult:
    allowed: bool
    reason: str
    config: AutonomousModeConfig | None
    requires_simulation: bool
    threshold: Decimal
    policy_payload: dict


class AutonomousPolicyService:
    RISK_ORDER = {"low": 1, "medium": 2, "high": 3, "critical": 4}
    CONFIDENCE_MAP = {"low": Decimal("0.60"), "medium": Decimal("0.78"), "high": Decimal("0.92")}

    @classmethod
    def resolve_config(cls, *, company=None):
        config = AutonomousModeConfig.objects.filter(company=company).order_by("-updated_at").first()
        if config is None:
            config = AutonomousModeConfig.objects.filter(company__isnull=True).order_by("-updated_at").first()
        return config

    @classmethod
    def compute_confidence_score(cls, *, decision: AgentDecision, simulation_run=None):
        base = Decimal("0.70")
        if decision.normalized_action_type in ELIGIBLE_ACTIONS:
            base = Decimal(str(ELIGIBLE_ACTIONS[decision.normalized_action_type].default_threshold))
        if decision.risk_level == "low":
            base += Decimal("0.10")
        if simulation_run and hasattr(simulation_run, "result"):
            base = max(base, cls.CONFIDENCE_MAP.get(simulation_run.result.confidence_level, Decimal("0.75")))
        return min(base, Decimal("0.99"))

    @classmethod
    def evaluate_safety_envelope(cls, *, decision: AgentDecision, simulation_run=None):
        config = cls.resolve_config(company=decision.company)
        if config is None:
            return SafetyEnvelopeResult(False, "Nenhuma configuracao de autonomia encontrada.", None, False, Decimal("0"), {})
        if not config.is_enabled or config.mode_level <= 1:
            return SafetyEnvelopeResult(False, "Modo autonomo desabilitado para este tenant.", config, False, Decimal("0"), {})
        if config.kill_switch_enabled:
            return SafetyEnvelopeResult(False, "Kill switch de autonomia ativo.", config, False, Decimal("0"), {})
        if decision.normalized_action_type in BLOCKED_ACTIONS:
            return SafetyEnvelopeResult(False, "Action type explicitamente bloqueado para autoexecucao.", config, False, Decimal("0"), {})
        if decision.normalized_action_type not in config.allowed_action_types and decision.normalized_action_type not in ELIGIBLE_ACTIONS:
            return SafetyEnvelopeResult(False, "Action type fora do catalogo elegivel.", config, False, Decimal("0"), {})
        if decision.normalized_action_type in config.blocked_action_types:
            return SafetyEnvelopeResult(False, "Action type bloqueado no tenant.", config, False, Decimal("0"), {})
        max_risk = cls.RISK_ORDER.get(config.max_risk_level, 0)
        action_risk = cls.RISK_ORDER.get(decision.risk_level, 99)
        if action_risk > max_risk:
            return SafetyEnvelopeResult(False, "Risco acima do envelope permitido.", config, False, Decimal("0"), {})
        if config.mode_level <= 2 and action_risk > cls.RISK_ORDER["low"]:
            return SafetyEnvelopeResult(False, "Mode level atual nao permite risco acima de low.", config, False, Decimal("0"), {})
        rule = ELIGIBLE_ACTIONS.get(decision.normalized_action_type)
        requires_simulation = decision.normalized_action_type in config.requires_simulation_for or bool(rule and rule.requires_simulation)
        threshold = Decimal(str((config.confidence_threshold_overrides or {}).get(decision.normalized_action_type, config.confidence_threshold_default)))
        return SafetyEnvelopeResult(
            allowed=True,
            reason="Action candidate dentro do safety envelope inicial.",
            config=config,
            requires_simulation=requires_simulation,
            threshold=threshold,
            policy_payload={
                "mode_level": config.mode_level,
                "max_risk_level": config.max_risk_level,
                "kill_switch_enabled": config.kill_switch_enabled,
                "requires_simulation": requires_simulation,
            },
        )

