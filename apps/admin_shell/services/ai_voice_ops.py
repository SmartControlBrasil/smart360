from __future__ import annotations

from django.db.models import Q

from apps.ai_voice_ops.models import VoiceInteraction


def get_ai_voiceops_context(*, tenant_context):
    company = tenant_context.get("company")
    site = tenant_context.get("site")
    queryset = VoiceInteraction.objects.select_related("user", "company", "site").order_by("-created_at")
    if company is not None:
        queryset = queryset.filter(company=company)
    if site is not None:
        queryset = queryset.filter(Q(site=site) | Q(site__isnull=True))
    interactions = list(queryset[:30])
    return {
        "voiceops_interactions": interactions,
        "voiceops_summary_cards": [
            {
                "label": "Interacoes",
                "value": len(interactions),
                "meta": "ultimas 30 execucoes de voz",
                "tone": "indigo",
            },
            {
                "label": "Acoes executadas",
                "value": sum(1 for item in interactions if item.action_status == VoiceInteraction.ActionStatus.EXECUTED),
                "meta": "comandos aplicados com sucesso",
                "tone": "emerald",
            },
            {
                "label": "Bloqueadas",
                "value": sum(1 for item in interactions if item.action_status == VoiceInteraction.ActionStatus.BLOCKED),
                "meta": "por escopo, policy ou contexto ausente",
                "tone": "amber",
            },
            {
                "label": "Personas ativas",
                "value": len({item.persona for item in interactions}),
                "meta": "tecnico, gestor e cliente",
                "tone": "sky",
            },
        ],
    }

