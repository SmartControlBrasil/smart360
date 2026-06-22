from .models import Lead

class ScoringEngine:
    """
    Motor de Inteligência de Dados para o Atlas.
    Calcula o Lead Score (0-100), mapeia o produto ideal por segmento e valida filtros de exclusão.
    """

    def process_lead(self, lead: Lead) -> Lead:
        score = 0
        fit = "BAIXO"
        produtos = ""

        name_lower = lead.institution_name.lower()
        notes_lower = lead.notes.lower()
        
        # 1. Filtro de Exclusão Estrita (Berçário / Infantil)
        if "berçario" in name_lower or "berçário" in name_lower or "infantil" in name_lower:
            lead.lead_score = 0
            lead.approach_status = "ready_for_review"
            lead.notes = f"[REPROVADO AUTOMÁTICO] Foco infantil/berçário. {lead.notes}"
            return lead

        # 2. Mapeamento de Segmento e Produto
        if any(keyword in name_lower for keyword in ["escola", "colégio", "colegio", "apae", "educação"]):
            lead.segment = "Escola / Educação"
            produtos = "LIRO / LittleBot (BNCC)"
            fit = "ALTO"
            score += 40
        elif any(keyword in name_lower for keyword in ["limpeza", "facilities", "serviços"]):
            lead.segment = "Limpeza / Facilities"
            produtos = "Duno / HygiBot"
            fit = "MÉDIO"
            score += 20
        elif any(keyword in name_lower for keyword in ["shopping", "clínica", "clinica", "hotel", "hospital"]):
            lead.segment = "Shopping / Clínica / Hotel"
            produtos = "NeoBot / HostBot"
            fit = "ALTO"
            score += 30
        elif any(keyword in name_lower for keyword in ["segurança", "seguranca", "indústria", "industria", "fábrica"]):
            lead.segment = "Segurança / Indústria"
            produtos = "Buddy / Orbit / Patrol"
            fit = "ALTO"
            score += 30
        else:
            lead.segment = "Outros"
            produtos = "A Definir"

        # 3. Aderência Geográfica (SP e Grande SP)
        regioes_sp = ["são paulo", "sao paulo", "sp", "grande sp", "abc", "guarulhos", "osasco", "barueri", "alphaville"]
        if any(reg in lead.city.lower() for reg in regioes_sp) or any(reg in lead.region.lower() for reg in regioes_sp):
            score += 30

        # 4. Presença de Decisor (Enriquecimento Apollo)
        if lead.contact_email:
            score += 20
        if lead.decider_name:
            score += 10

        # Garante teto de 100 pontos
        lead.lead_score = min(score, 100)
        
        # Injeta as informações comerciais nas Notas para manter a estrutura da planilha intacta
        commercial_notes = f"Fit: {fit} | Produtos: {produtos}"
        if lead.notes:
            lead.notes = f"{commercial_notes} | Obs: {lead.notes}"
        else:
            lead.notes = commercial_notes

        return lead
