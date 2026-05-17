# Relatorios Tecnicos e PDFs do Smart System

## Visao geral

O `Smart System` agora possui uma camada documental propria para gerar relatorios tecnicos em HTML e PDF, com foco em:

- ordem de servico
- manutencao preventiva
- manutencao corretiva
- evento de falha / RCA
- ficha tecnica resumida do ativo

A funcionalidade foi implementada dentro do `admin_shell`, reaproveitando o contexto operacional ja montado para ativos, OS, preventivas, falhas, checklists, execucao tecnica e MRO.

## Arquitetura adotada

### Servico central

Arquivo:

- `apps/admin_shell/services/smart_system_reports.py`

Responsabilidades:

- montar payload documental por tipo de relatorio
- consolidar contexto tecnico da origem
- expor preview HTML
- gerar PDF com `reportlab`
- centralizar historico inicial de documentos gerados

### Views e rotas

Rotas principais:

- `/app/smart-system/reports/`
- `/app/smart-system/reports/<report_type>/<reference_code>/`
- `/app/smart-system/reports/<report_type>/<reference_code>/download/`

Tipos suportados:

- `work-order`
- `preventive`
- `corrective`
- `failure`
- `asset-summary`

### Templates

Templates criados:

- `smart_system_reports_list.html`
- `smart_system_report_preview.html`

Componentes reutilizaveis:

- `report_document_header.html`
- `report_meta_table.html`
- `report_section_fields.html`
- `report_section_table.html`
- `report_section_checklist.html`
- `report_section_list.html`
- `report_signature_block.html`
- `report_history_table.html`

## Solucao de PDF

Foi escolhida a biblioteca `reportlab` por ser uma base estavel e previsivel para geracao programatica de PDF no ecossistema Django.

Motivos da escolha:

- gera PDF real sem depender de browser headless
- permite layout controlado e legivel para uso tecnico
- e adequada para documentos operacionais estruturados
- facilita evolucao futura para assinatura, QR code e branding por empresa

Observacao:

- o preview HTML e a renderizacao PDF compartilham o mesmo payload documental, mas nao a mesma engine de layout
- nesta rodada, a prioridade foi robustez documental, nao HTML-to-PDF

## Estrutura dos relatorios

Todo relatorio possui:

- codigo unico de documento
- tipo documental
- data/hora de emissao
- cliente
- site/unidade
- localizacao
- referencia de origem
- identificacao do ativo
- secoes tecnicas organizadas
- bloco final de preparacao documental

## Integracoes prontas

### Ordem de servico

Origem:

- detalhe da OS
- execucao tecnica da OS

Conteudo:

- chamado
- diagnostico
- acao executada
- horas
- materiais
- evidencias
- checklist
- timeline

### Preventiva

Origem:

- detalhe do plano preventivo

Conteudo:

- estrategia preventiva
- recorrencia
- aderencia
- cobertura
- checklist vinculado
- anomalias
- historico

### Falha / RCA

Origem:

- detalhe do evento de falha

Conteudo:

- modo de falha
- severidade
- impacto
- diagnostico
- causa raiz
- recomendacao preventiva
- timeline

### Ficha do ativo

Origem:

- detalhe do ativo

Conteudo:

- identificacao tecnica
- indicadores de manutencao
- disponibilidade
- falhas recentes
- historico resumido

## Como adicionar novo tipo de relatorio

1. Adicionar entrada em `REPORT_TYPE_CONFIG`.
2. Implementar builder em `smart_system_reports.py`.
3. Incluir o tipo em `build_report_payload`.
4. Adicionar acao de preview/download no contexto da tela de origem.
5. Criar ou reaproveitar secoes HTML no preview.
6. Adicionar teste de preview e download.

## Limitacoes atuais

- historico de relatorios ainda e mockado e nao persistido em banco
- evidencias entram como lista textual; miniaturas e imagens embutidas ficam para fase seguinte
- nao existe envio por email nesta rodada
- nao existe assinatura tecnica ou do cliente nesta rodada

## Proximos passos recomendados

- persistir relatorios gerados no bounded context `reporting_center`
- integrar com `files_center` para arquivamento e versionamento real
- enviar PDF por email via `notification_center`
- adicionar assinatura tecnica e assinatura do cliente
- incluir fotos embutidas, QR code de validacao e branding por empresa
