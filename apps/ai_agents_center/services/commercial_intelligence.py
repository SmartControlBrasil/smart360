from __future__ import annotations

import json
from dataclasses import dataclass, field


UNCONFIRMED = "Informacao nao confirmada."


@dataclass
class CommercialOpportunityAnalysis:
    opportunity: dict
    facts: list[str] = field(default_factory=list)
    hypotheses: list[str] = field(default_factory=list)
    missing_information: list[str] = field(default_factory=list)
    recommended_products: list[str] = field(default_factory=list)
    recommended_services: list[str] = field(default_factory=list)
    score_label: str = "Baixo Potencial"
    score_value: int = 25
    priority: str = "medium"
    severity: str = "medium"
    identified: bool = False


class CommercialIntelligenceService:
    ROBOTICS_RULES = {
        "limpeza": ["HygiBot", "Duno"],
        "higienizacao": ["HygiBot"],
        "hospital": ["HygiBot", "Duno", "HostBot"],
        "hotel": ["HostBot", "Duno", "NeoBot"],
        "seguranca": ["PatrolBot", "OrbitBot"],
        "recepcao": ["HostBot", "NeoBot"],
        "grama": ["MowerBot"],
        "jardim": ["MowerBot"],
        "logistica": ["ConnectBot", "LIRO"],
        "educacao": ["Buddy", "LittleBot", "NeoBot"],
    }
    SERVICE_RULES = {
        "falha": ["Manutencao industrial", "Confiabilidade", "TPM"],
        "parada": ["Manutencao industrial", "Confiabilidade", "TPM"],
        "retrabalho": ["Smart360", "Sistemas corporativos", "Dashboards"],
        "planilha": ["Smart360", "Sistemas Web", "Integracoes"],
        "indicador": ["Dashboards", "Smart360", "Inteligencia Artificial"],
        "automacao": ["Automacao Industrial", "CLPs", "SCADA"],
        "clp": ["CLPs", "IHMs", "SCADA"],
        "energia": ["Inversores de frequencia", "IoT Industrial", "Dashboards"],
        "rastreabilidade": ["Smart360", "Sistemas corporativos", "IoT Industrial"],
    }

    @classmethod
    def build_context(cls, *, company=None, site=None, trigger_reference="", triggered_by=None, definition=None):
        return {
            "agent_identity": "EDUARDO",
            "agent_alias": "EDU",
            "company": {
                "id": getattr(company, "id", None),
                "name": getattr(company, "name", ""),
                "slug": getattr(company, "slug", ""),
            },
            "site": {
                "id": getattr(site, "id", None),
                "name": getattr(site, "name", ""),
                "code": getattr(site, "code", ""),
            }
            if site
            else None,
            "trigger_reference": trigger_reference,
            "public_opportunity": cls.parse_trigger_reference(trigger_reference),
            "prompt_reference": "knowledge/comercial/agente_eduardo.md",
            "portfolio": definition.config.get("portfolio", {}) if definition else {},
            "compliance": {
                "lgpd": True,
                "public_or_legitimate_sources_only": True,
                "institutional_contacts_only": True,
                "do_not_invent_data": True,
            },
            "triggered_by": getattr(triggered_by, "email", ""),
        }

    @classmethod
    def parse_trigger_reference(cls, trigger_reference):
        if not trigger_reference:
            return {}
        try:
            parsed = json.loads(trigger_reference)
        except (TypeError, ValueError):
            return {"raw": trigger_reference}
        return parsed if isinstance(parsed, dict) else {"raw": trigger_reference}

    @classmethod
    def analyze(cls, *, context):
        opportunity = cls.normalize_opportunity(context.get("public_opportunity") or {})
        text = cls._analysis_text(opportunity)
        facts = cls._facts(opportunity)
        hypotheses = cls._hypotheses(opportunity)
        missing = cls._missing_information(opportunity)
        products = cls._dedupe(cls._match_rules(text, cls.ROBOTICS_RULES))
        services = cls._dedupe(cls._match_rules(text, cls.SERVICE_RULES))
        if not services and products:
            services = ["Robotica e integracao"]
        if not products and not services and opportunity.get("problems"):
            services = ["Diagnostico inicial", "Smart360"]

        identified = bool(opportunity.get("company_name") and opportunity.get("problems"))
        score_value, score_label = cls._score(opportunity, products, services, identified)
        return CommercialOpportunityAnalysis(
            opportunity=opportunity,
            facts=facts,
            hypotheses=hypotheses,
            missing_information=missing,
            recommended_products=products,
            recommended_services=services,
            score_label=score_label,
            score_value=score_value,
            priority="high" if score_value >= 75 else "medium" if score_value >= 45 else "low",
            severity="high" if score_value >= 75 else "medium",
            identified=identified,
        )

    @classmethod
    def normalize_opportunity(cls, data):
        contacts = data.get("institutional_contacts") or data.get("contatos_institucionais") or []
        if isinstance(contacts, str):
            contacts = [contacts]
        problems = data.get("problems") or data.get("problemas") or data.get("problem_identified") or data.get("problema_identificado") or []
        if isinstance(problems, str):
            problems = [problems]
        evidence = data.get("evidence") or data.get("evidencias") or []
        if isinstance(evidence, str):
            evidence = [evidence]
        return {
            "company_name": data.get("company_name") or data.get("empresa") or data.get("nome") or "",
            "segment": data.get("segment") or data.get("segmento") or "",
            "city": data.get("city") or data.get("cidade") or "",
            "state": data.get("state") or data.get("estado") or "",
            "estimated_size": data.get("estimated_size") or data.get("porte_estimado") or UNCONFIRMED,
            "website": data.get("website") or data.get("site") or "",
            "institutional_contacts": contacts,
            "digital_presence": data.get("digital_presence") or data.get("presenca_digital") or UNCONFIRMED,
            "technology_level": data.get("technology_level") or data.get("nivel_tecnologico") or UNCONFIRMED,
            "financial_capacity": data.get("financial_capacity") or data.get("capacidade_financeira") or UNCONFIRMED,
            "innovation_potential": data.get("innovation_potential") or data.get("potencial_inovacao") or UNCONFIRMED,
            "problems": problems,
            "evidence": evidence,
            "source_urls": data.get("source_urls") or data.get("fontes") or [],
            "raw": data,
        }

    @classmethod
    def build_lead_payload(cls, analysis):
        opportunity = analysis.opportunity
        notes = [
            f"Problema identificado: {'; '.join(opportunity['problems']) if opportunity['problems'] else UNCONFIRMED}",
            f"Solucao sugerida: {'; '.join(analysis.recommended_services or analysis.recommended_products) if analysis.recommended_services or analysis.recommended_products else UNCONFIRMED}",
            f"Score EDU: {analysis.score_label} ({analysis.score_value}/100)",
            f"Observacoes: fatos={analysis.facts or [UNCONFIRMED]}; hipoteses={analysis.hypotheses or [UNCONFIRMED]}",
        ]
        return {
            "company_name": opportunity["company_name"],
            "contact_name": "",
            "email": cls._first_contact(opportunity["institutional_contacts"], "@"),
            "phone": "",
            "whatsapp": "",
            "website": opportunity["website"],
            "city": opportunity["city"],
            "state": opportunity["state"],
            "status": "new",
            "notes": "\n".join(notes),
            "metadata": {
                "origin_agent": "eduardo-commercial-intelligence-agent",
                "agent_alias": "EDU",
                "segment": opportunity["segment"],
                "institutional_contacts": opportunity["institutional_contacts"],
                "problem_identified": opportunity["problems"],
                "solution_suggested": analysis.recommended_services,
                "product_recommended": analysis.recommended_products,
                "score_label": analysis.score_label,
                "score_value": analysis.score_value,
                "evidence": opportunity["evidence"],
                "source_urls": opportunity["source_urls"],
                "facts": analysis.facts,
                "hypotheses": analysis.hypotheses,
                "missing_information": analysis.missing_information,
                "compliance": "Usar apenas informacoes publicas ou disponibilizadas legitimamente.",
            },
        }

    @staticmethod
    def _first_contact(contacts, marker):
        for contact in contacts:
            if marker in contact:
                return contact
        return ""

    @staticmethod
    def _analysis_text(opportunity):
        parts = [
            opportunity.get("segment", ""),
            " ".join(opportunity.get("problems", [])),
            " ".join(opportunity.get("evidence", [])),
        ]
        return " ".join(parts).lower()

    @staticmethod
    def _dedupe(items):
        return list(dict.fromkeys(items))

    @classmethod
    def _match_rules(cls, text, rules):
        matches = []
        for keyword, recommendations in rules.items():
            if keyword in text:
                matches.extend(recommendations)
        return matches

    @staticmethod
    def _facts(opportunity):
        facts = []
        for field, label in (
            ("company_name", "Empresa"),
            ("segment", "Segmento"),
            ("city", "Cidade"),
            ("state", "Estado"),
            ("website", "Site"),
        ):
            if opportunity.get(field):
                facts.append(f"{label}: {opportunity[field]}")
        facts.extend([f"Evidencia publica: {item}" for item in opportunity.get("evidence", [])])
        return facts

    @staticmethod
    def _hypotheses(opportunity):
        hypotheses = []
        if opportunity.get("problems"):
            hypotheses.append("Ha potencial de compra se a dor identificada tiver prioridade operacional ou economica para a organizacao.")
        if opportunity.get("innovation_potential") != UNCONFIRMED:
            hypotheses.append(f"Potencial de inovacao informado: {opportunity['innovation_potential']}")
        return hypotheses

    @staticmethod
    def _missing_information(opportunity):
        missing = []
        for field, label in (
            ("company_name", "nome da empresa"),
            ("segment", "segmento"),
            ("city", "cidade"),
            ("state", "estado"),
            ("website", "site"),
        ):
            if not opportunity.get(field):
                missing.append(label)
        if not opportunity.get("problems"):
            missing.append("problema ou necessidade com evidencia")
        if not opportunity.get("institutional_contacts"):
            missing.append("contato institucional")
        return missing

    @staticmethod
    def _score(opportunity, products, services, identified):
        if not identified:
            return 25, "Baixo Potencial"
        score = 35
        score += 10 if opportunity.get("website") else 0
        score += 10 if opportunity.get("city") and opportunity.get("state") else 0
        score += 10 if opportunity.get("institutional_contacts") else 0
        score += min(len(opportunity.get("evidence", [])) * 8, 24)
        score += 10 if products else 0
        score += 8 if services else 0
        score = min(score, 100)
        if score >= 85:
            return score, "Estrategico"
        if score >= 70:
            return score, "Alto Potencial"
        if score >= 45:
            return score, "Medio Potencial"
        return score, "Baixo Potencial"

