from __future__ import annotations

from uuid import uuid4

from apps.ai_agents_center.services.client_portal_copilot import ClientPortalCopilotService
from apps.ai_agents_center.services.manager_copilot import ManagerCopilotService
from apps.ai_agents_center.services.technician_copilot import TechnicianCopilotService
from apps.ai_voice_ops.models import VoiceInteraction
from apps.ai_voice_ops.services.context import VoiceContextResolver
from apps.ai_voice_ops.services.intents import ParsedIntent
from apps.smart_system.services.offline_sync import FieldOfflineSyncService
from apps.smart_system.services.signature_service import ServiceSignatureService


class VoiceActionService:
    @classmethod
    def _build_operation_result(cls, *, result, success_summary: str, success_bullets: list[str]) -> dict:
        if result.status in {"conflict", "error"}:
            return {
                "action_status": VoiceInteraction.ActionStatus.BLOCKED if result.status == "conflict" else VoiceInteraction.ActionStatus.FAILED,
                "response_payload": {
                    "summary": result.message or "A operacao por voz foi bloqueada.",
                    "bullets": success_bullets or [],
                },
                "action_payload": result.result_payload or {"conflict_code": result.conflict_code, "snapshot_state": result.snapshot_state},
            }
        return {
            "action_status": VoiceInteraction.ActionStatus.EXECUTED,
            "response_payload": {
                "summary": success_summary,
                "bullets": success_bullets,
            },
            "action_payload": result.result_payload or {},
        }

    @classmethod
    def dispatch(
        cls,
        *,
        request,
        persona: str,
        parsed_intent: ParsedIntent,
        transcript_text: str,
        context_payload: dict,
        context_seed: dict | None = None,
        tenant_context: dict | None = None,
    ) -> dict:
        if persona == "technician":
            return cls._dispatch_technician(
                request=request,
                parsed_intent=parsed_intent,
                transcript_text=transcript_text,
                context_payload=context_payload,
                tenant_context=tenant_context or {},
            )
        if persona == "manager":
            return cls._dispatch_manager(
                request=request,
                parsed_intent=parsed_intent,
                transcript_text=transcript_text,
                context_seed=context_seed or {},
                tenant_context=tenant_context or {},
            )
        return cls._dispatch_client(
            request=request,
            parsed_intent=parsed_intent,
            transcript_text=transcript_text,
            context_seed=context_seed or {},
            tenant_context=tenant_context or {},
        )

    @classmethod
    def _dispatch_technician(cls, *, request, parsed_intent: ParsedIntent, transcript_text: str, context_payload: dict, tenant_context: dict) -> dict:
        company = tenant_context.get("company")
        site = tenant_context.get("site")
        order = VoiceContextResolver.resolve_order(request=request, entity_payload=parsed_intent.entities)
        service_payload = context_payload.get("service_payload") or {}
        if order is None and service_payload.get("service", {}).get("code"):
            order = VoiceContextResolver.resolve_order(
                request=request,
                entity_payload={"order_code": service_payload["service"]["code"]},
            )

        if parsed_intent.key in {"query_status", "query_schedule", "query_risk", "request_help"}:
            if service_payload:
                response = TechnicianCopilotService.handle_query(
                    user=request.user,
                    company=company,
                    site=site,
                    service_order=ServiceSignatureService.get_service_order(service_payload["service"]["code"]),
                    service_payload={
                        **service_payload,
                        "maintenance_recommendations": context_payload.get("technician_copilot_bootstrap", {}).get("maintenance_recommendations", []),
                        "recommended_parts": context_payload.get("technician_copilot_bootstrap", {}).get("recommended_parts", []),
                    },
                    query=transcript_text,
                    offline=False,
                )
                return {
                    "action_status": VoiceInteraction.ActionStatus.RESPONSE_ONLY,
                    "response_payload": response["response"],
                    "action_payload": {"session_public_id": str(response["session"].public_id)},
                }
            return {
                "action_status": VoiceInteraction.ActionStatus.ROUTED,
                "response_payload": {
                    "summary": "Preciso da ordem de servico ativa para orientar o atendimento por voz.",
                    "bullets": ["Abra a OS desejada no app e tente novamente."],
                },
                "action_payload": {},
            }

        if order is None:
            return {
                "action_status": VoiceInteraction.ActionStatus.BLOCKED,
                "response_payload": {
                    "summary": "Nao consegui identificar a ordem de servico desse comando de voz.",
                    "bullets": ["Informe o codigo da OS ou execute o comando dentro da tela da ordem."],
                },
                "action_payload": {"reason": "order_not_resolved"},
            }

        if parsed_intent.key == "start_work_order":
            result = FieldOfflineSyncService.process_operation(
                request=request,
                user=request.user,
                operation={
                    "action": "start_execution",
                    "operationId": f"voice-start-{uuid4()}",
                    "orderCode": order.order_number,
                    "payload": {"progress": 5},
                },
            )
            return cls._build_operation_result(
                result=result,
                success_summary=f"OS {order.order_number} iniciada com sucesso por voz.",
                success_bullets=[f"Status atual: {result.result_payload.get('service_order_status', 'em andamento')}."],
            )

        if parsed_intent.key == "complete_work_order":
            result = FieldOfflineSyncService.process_operation(
                request=request,
                user=request.user,
                operation={
                    "action": "complete_execution",
                    "operationId": f"voice-complete-{uuid4()}",
                    "orderCode": order.order_number,
                    "payload": {"finalization": {"finalNotes": transcript_text, "recommendation": transcript_text}},
                },
            )
            return cls._build_operation_result(
                result=result,
                success_summary=f"OS {order.order_number} concluida por voz.",
                success_bullets=[f"Conclusao registrada em {result.result_payload.get('completed_at', '')}."],
            )

        if parsed_intent.key == "report_issue":
            issue_summary = parsed_intent.entities.get("issue_summary") or transcript_text
            result = FieldOfflineSyncService.process_operation(
                request=request,
                user=request.user,
                operation={
                    "action": "save_execution",
                    "operationId": f"voice-issue-{uuid4()}",
                    "orderCode": order.order_number,
                    "payload": {
                        "progress": 40,
                        "diagnosis": {
                            "symptoms": issue_summary,
                            "technical_diagnosis": issue_summary,
                            "analysis": "Registro capturado via VoiceOps.",
                        },
                    },
                },
            )
            return cls._build_operation_result(
                result=result,
                success_summary=f"Problema registrado na OS {order.order_number}.",
                success_bullets=[issue_summary],
            )

        if parsed_intent.key == "add_part":
            part = VoiceContextResolver.resolve_part(
                request=request,
                company=company,
                entity_payload=parsed_intent.entities,
            )
            if part is None:
                return {
                    "action_status": VoiceInteraction.ActionStatus.BLOCKED,
                    "response_payload": {
                        "summary": "Nao encontrei a peca citada no escopo atual.",
                        "bullets": ["Fale o codigo da peca, por exemplo PRT-0001."],
                    },
                    "action_payload": {"reason": "part_not_resolved"},
                }
            quantity = float(parsed_intent.entities.get("quantity") or 1)
            result = FieldOfflineSyncService.process_operation(
                request=request,
                user=request.user,
                operation={
                    "action": "save_materials",
                    "operationId": f"voice-part-{uuid4()}",
                    "orderCode": order.order_number,
                    "payload": {
                        "progress": 55,
                        "materials": [
                            {
                                "code": part.code,
                                "name": part.name,
                                "quantity": f"{quantity:g} {part.unit}",
                                "notes": "Lancamento realizado via VoiceOps.",
                            }
                        ],
                    },
                },
            )
            return cls._build_operation_result(
                result=result,
                success_summary=f"Peca {part.code} adicionada na OS {order.order_number}.",
                success_bullets=[f"{part.name} - {quantity:g} {part.unit}."],
            )

        if parsed_intent.key == "mark_checklist_nok":
            issue_summary = parsed_intent.entities.get("issue_summary") or transcript_text
            existing = service_payload.get("execution", {}).get("checklist_execution", {}).get("items", [])
            target_item = existing[0] if existing else {"order": 1, "title": "Item de checklist"}
            result = FieldOfflineSyncService.process_operation(
                request=request,
                user=request.user,
                operation={
                    "action": "save_checklist",
                    "operationId": f"voice-nok-{uuid4()}",
                    "orderCode": order.order_number,
                    "payload": {
                        "progress": 50,
                        "checklist": {
                            "items": [
                                {
                                    "order": target_item.get("order", 1),
                                    "title": target_item.get("title", "Item de checklist"),
                                    "response": "NOK",
                                    "notes": issue_summary,
                                }
                            ]
                        },
                    },
                },
            )
            return cls._build_operation_result(
                result=result,
                success_summary=f"Checklist atualizado com NOK na OS {order.order_number}.",
                success_bullets=[issue_summary],
            )

        return {
            "action_status": VoiceInteraction.ActionStatus.ROUTED,
            "response_payload": {
                "summary": "Comando encaminhado como pedido de ajuda contextual.",
                "bullets": ["Use o copilot tecnico para aprofundar o diagnostico."],
            },
            "action_payload": {},
        }

    @classmethod
    def _dispatch_manager(cls, *, request, parsed_intent: ParsedIntent, transcript_text: str, context_seed: dict, tenant_context: dict) -> dict:
        payload = ManagerCopilotService.handle_query(
            user=request.user,
            tenant_context=tenant_context,
            query=transcript_text,
            context_seed=context_seed,
        )
        return {
            "action_status": VoiceInteraction.ActionStatus.RESPONSE_ONLY,
            "response_payload": payload["response"],
            "action_payload": {"session_public_id": str(payload["session"].public_id)},
        }

    @classmethod
    def _dispatch_client(cls, *, request, parsed_intent: ParsedIntent, transcript_text: str, context_seed: dict, tenant_context: dict) -> dict:
        permission_map = (
            tenant_context.get("permission_map")
            or context_seed.get("permission_map")
            or getattr(request, "permission_map", None)
            or {}
        )
        payload = ClientPortalCopilotService.handle_query(
            request=request,
            tenant_context=tenant_context,
            permission_map=permission_map,
            query=transcript_text,
            context_seed=context_seed,
        )
        return {
            "action_status": VoiceInteraction.ActionStatus.RESPONSE_ONLY,
            "response_payload": payload["response"],
            "action_payload": {"session_public_id": str(payload["session"].public_id)},
        }
