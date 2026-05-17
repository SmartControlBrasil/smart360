# Smart Site Factory — fluxo atual (visão resumida)

Documento operacional e comercial do módulo **Smart Site Factory** (SSF), alinhado à implementação atual no Admin Shell. Sem migrations extras para proposta comercial formal.

---

## 1. Visão geral do módulo

O **Smart Site Factory** orquestra **pedidos de sites** por nicho/configuração: criação do **SiteOrder**, **briefing** (intake), **tarefas de produção** padronizadas, **entrega** e **dashboard** operacional. A camada HTML vive sob **`dashboard/site-factory/`** (namespace `admin-shell:*`). Existem também **APIs REST** para o mesmo domínio; este texto foca no fluxo humano no shell.

---

## 2. Fluxo operacional

Sequência típica:

| Etapa | O que é |
|-------|---------|
| **Dashboard** | KPIs, gráficos (status, nichos, pacotes), últimos pedidos e tarefas pendentes; filtros GET. |
| **Pedido** | Criação (`Novo projeto`) ou abertura do detalhe do **SiteOrder**; vínculo empresa/nicho/template (pacote), preço final, metadados do cliente. |
| **Briefing** | Formulário **SiteProjectIntake** ligado ao pedido — descrição do negócio, serviços, redes, galeria, etc. |
| **Produção** | Lista de **ProductionTask** por etapas (discovery → delivery); atualização de status por tarefa. |
| **Entrega** | Registro de entrega (**DeliveryRecord**), URL entregue e aceite; pedido pode ir para status entregue conforme regras existentes. |

O serviço **`SiteOrderService`** cria o pedido, recomenda template quando necessário, define preço a partir do pacote (helper), grava **snapshot** do pacote em **`SiteOrder.metadata`**, dispara bootstrap de tarefas e datas de produção quando aplicável.

---

## 3. Fluxo comercial

| Passo | Descrição |
|-------|-----------|
| **SiteOrder** | Fonte da verdade operacional e comercial no MVP: empresa, contato em metadata, **final_price**, template selecionado/recomendado. |
| **Pacote** | Campos comerciais vêm de **`Template.metadata`** (código, tier, nome comercial, entregáveis, upsells, `list_price` opcional). Preço efetivo: **`list_price`** válido ou **`base_price`**. Snapshot em **`SiteOrder.metadata["package_snapshot"]`**. |
| **Lead / oportunidade** | POST no detalhe do pedido → **`upsert_lead_from_site_order`** (Growth Engine): cria/atualiza **Lead**, escreve metadados (incl. pacote) e referências no pedido (`lead_id`, `commercial_status`, etc.). |
| **Proposta HTML** | Rota dedicada **`orders/<pk>/proposal/`**: página para impressão/PDF pelo navegador, com dados do cliente, pacote, valores, condições simples, briefing resumido e bloco interno do pedido. |

Não há modelo **`CommercialProposal`** nem envio de e-mail automático nesta fase.

---

## 4. Principais rotas HTML

Prefixo físico: **`/dashboard/site-factory/`** (inclusão em `admin_shell`). Nomes Django (**`admin-shell:`**):

| Nome | Caminho relativo |
|------|------------------|
| `site-factory-dashboard` | `""` |
| `site-factory-orders` | `orders/` |
| `site-factory-order-new` | `orders/new/` |
| `site-factory-order-detail` | `orders/<pk>/` |
| `site-factory-order-intake` | `orders/<pk>/intake/` |
| `site-factory-order-tasks` | `orders/<pk>/tasks/` |
| `site-factory-task-status` | `orders/<pk>/tasks/<task_pk>/status/` |
| `site-factory-order-commercial` | `orders/<pk>/commercial-opportunity/` (POST) |
| `site-factory-order-proposal` | `orders/<pk>/proposal/` |

Permissões seguem o padrão do shell (**`permission_domain`** / **`permission_action`**, escopo tenant via **`get_order_queryset`**).

---

## 5. Principais serviços (`apps/smart_site_factory/services/`)

| Arquivo | Função |
|---------|--------|
| **`order_service.py`** | **`SiteOrderService`** (criação do pedido, snapshot, preço, tarefas iniciais); **`ProductionService`** / **`DeliveryService`** para marcos de produção e entrega. |
| **`recommendation_service.py`** | Recomendação de **Template** a partir do nicho e opções do configurador. |
| **`template_package.py`** | Extração do pacote a partir de **`Template.metadata`**, **`resolve_package_price`**, **`build_package_snapshot`**, resolução de pacote para UI/detalhe/dashboard. |
| **`site_factory_dashboard.py`** | Filtros, KPIs, séries para gráficos, pedidos recentes, entregas, tarefas pendentes; agregação de **pacotes comerciais** em Python quando necessário. |
| **`site_order_lead_bridge.py`** | **`upsert_lead_from_site_order`**: ponte idempotente com **Lead**, metadados comerciais do pacote. |

Auditoria de eventos relevantes pode ser registrada por **`AuditService`** onde já integrado (ex.: criação de pedido).

---

## 6. Decisões arquiteturais (MVP)

- **`Template.metadata`** = catálogo leve de **pacote comercial** (sem **`SitePackage`** dedicado por enquanto).
- **`SiteOrder.metadata`** = dados do cliente + **`package_snapshot`** + vínculos comerciais (**`lead_id`**, **`commercial_status`**, etc.).
- **Proposta** = renderização **HTML** server-side; **sem** modelo **`CommercialProposal`** e **sem** migrations novas para isso.
- **Billing** não é alterado neste fluxo documentado.

---

## 7. Próximos passos recomendados

1. **PDF gerado no backend** (ex.: WeasyPrint/wkhtmltopdf ou serviço dedicado) para proposta com layout estável e arquivo arquivável.
2. **Envio da proposta por e-mail** (template + anexo PDF ou link assinado).
3. **Modelo formal de proposta** (`CommercialProposal` ou equivalente), versionamento e aceite registrado.
4. **Integração futura com Billing** (faturamento da entrada 50% / saldo na entrega alinhado às regras do produto).
5. **`SitePackage`** (ou entidade de catálogo) **se** o JSON em **`Template.metadata`** deixar de ser suficiente para preço, SKU, lifecycle comercial ou integrações externas.

---

*Documento introdutório; detalhes de API e modelos podem aparecer em `docs/smart-site-factory.md` e no código-fonte do app.*
