# Atlas PoC - Test Status

Data: 2026-06-21

## Resultado

- `manage.py check`: pendente de confirmação nesta rodada.
- `apps/atlas_agent`: sem testes automatizados no momento.
- `apps/ai_agents_center/tests/test_atlas_importer.py`: validar isoladamente.
- `apps/ai_agents_center/tests/test_atlas_opportunities.py`: validar isoladamente.
- Suíte ampla `apps/ai_agents_center`: falha atualmente com erros pré-existentes/estruturais em permissões, serialização UUID, briefing, marketplace, scheduling e profitability.

## Falhas observadas na suíte ampla

- PermissionError: No matching allow permission.
- TypeError: Object of type UUID is not JSON serializable.
- NameError: name 'period' is not defined.
- StockMovement() got unexpected keyword argument.
- AttributeError: The parameter 'company' is unknown.
- TechnicianProfile.DoesNotExist.
- ValidationError com valor "AI-01".

## Decisão

O commit do Atlas PoC deve ser validado por testes isolados do Atlas/importer e compileall da PoC, sem bloquear por falhas amplas não relacionadas diretamente ao Atlas.
