# Pecas, Estoque e Sobressalentes (MRO)

O modulo de MRO do `Smart System` foi implementado no `admin_shell` como primeira camada de gestao de pecas, sobressalentes e movimentacao de estoque de manutencao.

## Superficies entregues

- Lista de pecas com KPIs, filtros e estados de estoque
- Detalhe da peca com resumo de saldo, historico, ativos associados e consumo em OS
- Tela de movimentacao com entradas, saídas e ajustes operacionais
- Integracao visual com o modo tecnico de execucao da OS

## Estrutura de dados

Os mocks ficam em [smart_system_parts.py](/home/marcelo/Projetos/smart360/apps/admin_shell/services/smart_system_parts.py) e cobrem:

- cadastro da peca
- estoque atual e limites
- localizacao
- historico de movimentacoes
- vinculo com ativos
- consumo em ordens de servico

## Integracao com OS

O modo tecnico de execucao da OS agora pode mostrar materiais com codigo de peca e link direto para a ficha MRO do item.

Isso prepara o fluxo futuro para:

- baixa real de estoque
- reserva de material
- consumo por tecnico
- conciliacao com almoxarifado

## Proximos passos

- persistencia real de entradas, saídas e ajustes
- fornecedores e compras
- estoque multi-local
- previsao de consumo
- integracao ERP
