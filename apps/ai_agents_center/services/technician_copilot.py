from __future__ import annotations

from django.db import transaction
from django.urls import reverse
from django.utils import timezone

from apps.ai_agents_center.models import (
    AgentRecommendation,
    TechnicianCopilotConfiguration,
    TechnicianCopilotMessage,
    TechnicianCopilotSession,
)
from apps.observability_center.services.observability_service import SystemEventService
from apps.smart_system.models import ServiceOrder
from shared_kernel.observability.context import get_request_id


class TechnicianCopilotService:
    DEFAULT_SUGGESTIONS = [
        "O que ja deu problema nesse equipamento?",
        "Qual o proximo passo aqui?",
        "Esse checklist NOK significa o que?",
        "Como descrevo esse problema na OS?",
        "Que peca pode estar causando isso?",
    ]

    INTENT_KEYWORDS = {
        "history_summary": ["ja deu problema", "historico", "falhas", "parecido", "aconteceu"],
        "diagnostic_hint": ["erro", "causa", "pode ser", "diagnostico", "verificar", "falha"],
        "execution_guidance": ["proximo passo", "como fazer", "orientar", "execucao", "o que verificar antes"],
        "checklist_interpretation": ["checklist", "nok", "item", "significa"],
        "documentation_help": ["como descrevo", "reescreva", "descreva", "registro", "os"],
        "parts_suggestion": ["peca", "componente", "trocar", "substituir", "material"],
    }

    @classmethod
    def get_configuration(cls, *, company=None):
        configuration = None
        if company is not None:
            configuration = TechnicianCopilotConfiguration.objects.filter(company=company).first()
        if configuration is None:
            configuration = TechnicianCopilotConfiguration.objects.filter(company__isnull=True).first()
        return configuration

    @classmethod
    def classify_intent(cls, query: str) -> str:
        normalized = (query or "").strip().lower()
        for intent, keywords in cls.INTENT_KEYWORDS.items():
            if any(keyword in normalized for keyword in keywords):
                return intent
        return "execution_guidance"

    @classmethod
    def get_or_create_session(cls, *, user, company=None, site=None, service_order=None):
        queryset = TechnicianCopilotSession.objects.filter(user=user, company=company, site=site, service_order=service_order)
        session = queryset.order_by("-last_activity_at").first()
        if session is not None:
            return session
        return TechnicianCopilotSession.objects.create(
            user=user,
            company=company,
            site=site,
            service_order=service_order,
            status=TechnicianCopilotSession.Status.ACTIVE,
            current_context={},
        )

    @classmethod
    def resolve_context(cls, *, service_payload, offline=False):
        service = service_payload["service"]
        execution = service_payload["execution"]
        checklist = execution.get("checklist_execution") or {}
        maintenance_recommendations = service_payload.get("maintenance_recommendations", [])
        recommended_parts = service_payload.get("recommended_parts", [])
        return {
            "order_code": service["code"],
            "asset_code": service["asset_code"],
            "asset_name": service.get("asset_name") or service["asset_code"],
            "site": service["site"],
            "client": service["client"],
            "priority": service["priority"],
            "status": service["status"],
            "offline": offline,
            "recent_failures": execution.get("recent_failures", []),
            "recent_asset_history": execution.get("recent_asset_history", []),
            "checklist_nok_count": checklist.get("nok_count", 0),
            "checklist_pending_count": checklist.get("pending_count", 0),
            "materials": execution.get("materials", []),
            "diagnosis": execution.get("diagnosis", {}),
            "executed_action": execution.get("executed_action", {}),
            "finalization": execution.get("finalization", {}),
            "maintenance_recommendations": maintenance_recommendations,
            "recommended_parts": recommended_parts,
        }

    @classmethod
    def _history_response(cls, context):
        failures = context["recent_failures"]
        history = context["recent_asset_history"]
        summary = (
            f"{context['asset_code']} teve {len(failures)} falhas recentes relevantes."
            if failures
            else f"Nao ha falhas recentes registradas para {context['asset_code']} no contexto carregado."
        )
        bullets = [item["summary"] for item in failures[:3]] or [item["description"] for item in history[:3]] or ["Sem recorrencia relevante carregada."]
        return {
            "response_type": "history_summary",
            "summary": summary,
            "bullets": bullets[:3],
            "actions": [
                {"label": "Ver historico completo", "href": reverse("admin-shell:technician-app-history")},
                {"label": "Abrir execucao", "href": reverse("admin-shell:technician-app-service-execution", kwargs={"order_code": context["order_code"]})},
            ],
        }

    @classmethod
    def _diagnostic_response(cls, query, context):
        diagnosis = context["diagnosis"]
        failures = context["recent_failures"]
        recommendations = context["maintenance_recommendations"]
        hypotheses = []
        if diagnosis.get("components"):
            hypotheses.append(f"Componentes envolvidos: {diagnosis['components']}.")
        if diagnosis.get("technical_diagnosis"):
            hypotheses.append(f"Diagnostico atual: {diagnosis['technical_diagnosis']}.")
        for failure in failures[:2]:
            hypotheses.append(f"Falha similar: {failure['summary']}.")
        for recommendation in recommendations[:2]:
            hypotheses.append(recommendation["summary"])
        if not hypotheses:
            hypotheses.append("Comece validando alimentacao, conexoes, condicao do componente e sinais do checklist.")
        steps = [
            "Confirme o sintoma em teste funcional curto.",
            "Valide conexoes, alimentacao e sinais do componente suspeito.",
            "Compare com a ultima falha similar registrada antes de substituir a peca.",
        ]
        return {
            "response_type": "diagnostic_hint",
            "summary": f"Hipoteses mais provaveis para {context['asset_code']} com base no atendimento atual.",
            "bullets": hypotheses[:4],
            "steps": steps,
            "actions": [
                {"label": "Abrir checklist", "href": reverse("admin-shell:technician-app-service-execution", kwargs={"order_code": context["order_code"]})},
            ],
        }

    @classmethod
    def _checklist_response(cls, context):
        nok_count = context["checklist_nok_count"]
        pending_count = context["checklist_pending_count"]
        recommendations = context["maintenance_recommendations"]
        bullets = []
        if nok_count:
            bullets.append(f"Ha {nok_count} item(ns) NOK. Priorize causa comum antes de fechar a OS.")
        if pending_count:
            bullets.append(f"Ainda restam {pending_count} item(ns) pendentes no checklist.")
        for recommendation in recommendations[:2]:
            bullets.append(recommendation["suggested_action"] or recommendation["summary"])
        if not bullets:
            bullets.append("Checklist sem NOK relevante no contexto local.")
        return {
            "response_type": "checklist_interpretation",
            "summary": "Leitura pratica do checklist atual para o atendimento.",
            "bullets": bullets[:4],
            "steps": [
                "Registre observacao objetiva em cada item NOK.",
                "Relacione o NOK ao sintoma principal da OS.",
                "Se o NOK indicar risco de retorno, destaque isso na recomendacao final.",
            ],
            "actions": [
                {"label": "Registrar observacao", "href": reverse("admin-shell:technician-app-service-execution", kwargs={"order_code": context["order_code"]})},
            ],
        }

    @classmethod
    def _documentation_response(cls, query, context):
        source = query.split(":", 1)[1].strip() if ":" in query else ""
        diagnosis = context["diagnosis"].get("technical_diagnosis", "")
        rewritten = source or diagnosis or "Falha operacional identificada durante teste funcional."
        rewritten = rewritten.replace("nao girava direito", "apresentava rotacao irregular e perda de torque")
        rewritten = rewritten.replace("motor", "conjunto motriz")
        summary = "Sugestao de texto tecnico para registro da OS."
        bullets = [
            f"Problema: {rewritten}.",
            "Acao: registrar teste executado, componente inspecionado e resultado obtido.",
            "Conclusao: indicar se houve normalizacao, contingencia ou dependencia de peca.",
        ]
        return {
            "response_type": "documentation_help",
            "summary": summary,
            "bullets": bullets,
            "actions": [
                {"label": "Preencher OS", "href": reverse("admin-shell:technician-app-service-execution", kwargs={"order_code": context["order_code"]})},
            ],
        }

    @classmethod
    def _parts_response(cls, context):
        materials = context["materials"]
        recommended_parts = context["recommended_parts"]
        bullets = []
        for part in recommended_parts[:3]:
            bullets.append(f"{part['code']} - {part['name']}: {part['reason']}")
        for material in materials[:2]:
            bullets.append(f"Historico local: {material['code']} - {material['name']}.")
        if not bullets:
            bullets.append("Sem peca clara no contexto local. Valide componente suspeito antes de solicitar troca.")
        return {
            "response_type": "parts_suggestion",
            "summary": "Pecas e componentes relacionados ao sintoma atual.",
            "bullets": bullets[:4],
            "steps": [
                "Compare a falha atual com a ultima troca registrada.",
                "Confirme codigo e aplicacao antes de reservar material.",
            ],
            "actions": [
                {"label": "Revisar materiais", "href": reverse("admin-shell:technician-app-service-execution", kwargs={"order_code": context["order_code"]})},
            ],
        }

    @classmethod
    def _execution_response(cls, context):
        diagnosis = context["diagnosis"]
        action = context["executed_action"]
        bullets = []
        if diagnosis.get("technical_diagnosis"):
            bullets.append(f"Diagnostico atual: {diagnosis['technical_diagnosis']}.")
        if action.get("intervention"):
            bullets.append(f"Acao em curso: {action['intervention']}.")
        if context["maintenance_recommendations"]:
            bullets.append(context["maintenance_recommendations"][0]["summary"])
        if not bullets:
            bullets.append("Siga teste funcional, checklist, diagnostico e registro tecnico antes do fechamento.")
        return {
            "response_type": "execution_guidance",
            "summary": "Proxima orientacao pratica para continuar o atendimento.",
            "bullets": bullets[:3],
            "steps": [
                "Confirme sintoma e condicao operacional do ativo.",
                "Registre diagnostico tecnico objetivo.",
                "Valide resultado apos ajuste ou substituicao.",
                "Atualize recomendacao final se houver retorno necessario.",
            ],
            "actions": [
                {"label": "Continuar execucao", "href": reverse("admin-shell:technician-app-service-execution", kwargs={"order_code": context["order_code"]})},
            ],
        }

    @classmethod
    def compose_response(cls, *, query, context):
        intent = cls.classify_intent(query)
        if intent == "history_summary":
            response = cls._history_response(context)
        elif intent == "diagnostic_hint":
            response = cls._diagnostic_response(query, context)
        elif intent == "checklist_interpretation":
            response = cls._checklist_response(context)
        elif intent == "documentation_help":
            response = cls._documentation_response(query, context)
        elif intent == "parts_suggestion":
            response = cls._parts_response(context)
        else:
            response = cls._execution_response(context)
        response["intent"] = intent
        response["offline"] = context["offline"]
        response["quick_suggestions"] = cls.get_suggestions(context=context)
        return response

    @classmethod
    def get_suggestions(cls, *, context):
        suggestions = list(cls.DEFAULT_SUGGESTIONS)
        if context.get("checklist_nok_count"):
            suggestions.insert(0, "Esse checklist NOK significa o que?")
        if context.get("recent_failures"):
            suggestions.insert(0, "Ja aconteceu algo parecido antes?")
        return list(dict.fromkeys(suggestions))[:6]

    @classmethod
    def build_bootstrap(cls, *, service_payload):
        context = cls.resolve_context(service_payload=service_payload, offline=False)
        return {
            "context": context,
            "suggestions": cls.get_suggestions(context=context),
            "recommended_parts": context["recommended_parts"],
            "maintenance_recommendations": context["maintenance_recommendations"],
        }

    @classmethod
    @transaction.atomic
    def handle_query(cls, *, user, company=None, site=None, service_order=None, service_payload=None, query="", offline=False):
        session = cls.get_or_create_session(user=user, company=company, site=site, service_order=service_order)
        context = cls.resolve_context(service_payload=service_payload, offline=offline)
        request_id = get_request_id()
        SystemEventService.log_system_event(
            event_type="copilot.tech.query.received",
            source_module="ai_agents_center",
            message="Technician copilot query received.",
            entity_type="service_order",
            entity_id=context["order_code"],
            user=user,
            company=company,
            site=site,
            payload={"request_id": request_id, "query": query, "offline": offline},
        )
        SystemEventService.log_system_event(
            event_type="copilot.tech.context.loaded",
            source_module="ai_agents_center",
            message="Technician copilot context loaded.",
            entity_type="service_order",
            entity_id=context["order_code"],
            user=user,
            company=company,
            site=site,
            payload={"request_id": request_id, "asset_code": context["asset_code"], "offline": offline},
        )
        response = cls.compose_response(query=query, context=context)
        TechnicianCopilotMessage.objects.create(
            session=session,
            role=TechnicianCopilotMessage.Role.USER,
            content=query,
            detected_intent=response["intent"],
            was_offline=offline,
            context_snapshot=context,
        )
        TechnicianCopilotMessage.objects.create(
            session=session,
            role=TechnicianCopilotMessage.Role.ASSISTANT,
            content=response["summary"],
            detected_intent=response["intent"],
            was_offline=offline,
            context_snapshot=context,
            structured_payload=response,
        )
        session.current_context = context
        session.last_intent = response["intent"]
        session.status = TechnicianCopilotSession.Status.OFFLINE if offline else TechnicianCopilotSession.Status.ACTIVE
        session.message_count = session.messages.count()
        session.save(update_fields=["current_context", "last_intent", "status", "message_count", "last_activity_at", "updated_at"])
        SystemEventService.log_system_event(
            event_type="copilot.tech.response.generated",
            source_module="ai_agents_center",
            message="Technician copilot response generated.",
            entity_type="service_order",
            entity_id=context["order_code"],
            user=user,
            company=company,
            site=site,
            payload={"request_id": request_id, "intent": response["intent"], "offline": offline},
        )
        if offline:
            SystemEventService.log_system_event(
                event_type="copilot.tech.offline.mode",
                source_module="ai_agents_center",
                message="Technician copilot offline fallback used.",
                entity_type="service_order",
                entity_id=context["order_code"],
                user=user,
                company=company,
                site=site,
                payload={"request_id": request_id},
            )
        return {"session": session, "context": context, "response": response}

    @classmethod
    def sync_local_session(cls, *, user, company=None, site=None, service_order=None, payload=None):
        payload = payload or {}
        session = cls.get_or_create_session(user=user, company=company, site=site, service_order=service_order)
        synced_count = 0
        for item in payload.get("messages", []):
            TechnicianCopilotMessage.objects.create(
                session=session,
                role=item.get("role", TechnicianCopilotMessage.Role.USER),
                content=item.get("content", ""),
                detected_intent=item.get("intent", ""),
                was_offline=True,
                context_snapshot=payload.get("context", {}),
                structured_payload=item.get("structured_payload", {}),
            )
            synced_count += 1
        session.current_context = payload.get("context", session.current_context)
        session.status = TechnicianCopilotSession.Status.ACTIVE
        session.message_count = session.messages.count()
        session.save(update_fields=["current_context", "status", "message_count", "last_activity_at", "updated_at"])
        SystemEventService.log_system_event(
            event_type="copilot.tech.sync.completed",
            source_module="ai_agents_center",
            message="Technician copilot offline session synced.",
            entity_type="service_order",
            entity_id=getattr(service_order, "order_number", ""),
            user=user,
            company=company,
            site=site,
            payload={"messages_synced": synced_count},
        )
        return {"session": session, "messages_synced": synced_count}

    @classmethod
    def maintenance_recommendations_for_asset(cls, *, company=None, site=None, asset_public_id=""):
        queryset = AgentRecommendation.objects.select_related("agent_run", "agent_run__agent").filter(
            agent_run__agent__slug="maintenance-agent",
            entity_type="asset",
            entity_id=asset_public_id,
        )
        if company is not None:
            queryset = queryset.filter(company=company)
        if site is not None:
            queryset = queryset.filter(site=site)
        recommendations = []
        for recommendation in queryset.order_by("-attention_score", "-created_at")[:4]:
            recommendations.append(
                {
                    "public_id": str(recommendation.public_id),
                    "title": recommendation.title,
                    "summary": recommendation.summary,
                    "suggested_action": recommendation.suggested_action,
                    "attention_score": recommendation.attention_score,
                    "severity": recommendation.severity,
                }
            )
        return recommendations
