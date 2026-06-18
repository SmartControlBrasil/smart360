# Auditoria CSS — Site Institucional Eitech (Smart Control Brasil)

Documento da Fase 1 (organização incremental, sem pipeline novo).  
Última atualização: junho/2026.

---

## Panorama atual

### CSS global carregado no `base.html`

Ordem fixa em `templates/institutional/eitech/base.html`:

| Arquivo | Papel aproximado | Tamanho (ref.) |
|---------|------------------|----------------|
| `plugins/bootstrap.min.css` | Grid / utilitários Bootstrap | ~192 KB |
| `plugins/aos.css` | Animações scroll (AOS) | ~28 KB |
| `plugins/fontawesome.css` | Ícones Font Awesome | ~716 KB |
| `plugins/magnific-popup.css` | Lightbox | ~8 KB |
| `plugins/mobile.css` | Menu mobile | pequeno |
| `plugins/owlcarousel.min.css` | Carrossel Owl | ~4 KB |
| `plugins/sidebar.css` | Off-canvas / sidebar | ~8 KB |
| `plugins/slick-slider.css` | Slider Slick | ~4 KB |
| `plugins/nice-select.css` | Select estilizado | ~8 KB |
| `main.css` | Tema Eitech (layout, seções, componentes) | ~336 KB |
| `scb-header.css` | Header / navegação SCB | ~7 KB |
| `scb-float-widgets.css` | WhatsApp flutuante e widgets | ~2,5 KB |
| `{% block extra_css %}` | CSS por página (SCB) | variável |

**Total estimado por request (sem compressão):** ~1,3 MB de CSS + JS/plugins no footer.

### CSS custom SCB existente (eitech)

| Arquivo | Página / uso |
|---------|----------------|
| `scb-home.css` | Home (`pages/index.html`) |
| `scb-contact.css` | Contato |
| `scb-mitsubishi.css` | Mitsubishi (`pages/mitsubishi.html`) — Fase 1 |
| `scb-engenharia.css` | Engenharia embarcada — Fase 1 |
| `scb-service.css` | Manutenção / TPM / confiabilidade — Fase 1 |
| `scb-projects.css` | Projetos — Fase 1 |
| `scb-xyron.css` | Xyron Robotics — Fase 1 |

Padrão: `{% block extra_css %}` com `<link rel="stylesheet" href="{% static '...' %}">`.

### Principais arquivos pesados conhecidos

- `static/institutional/eitech/css/plugins/fontawesome.css` — maior plugin; candidato a carga condicional (médio prazo).
- `static/institutional/eitech/css/main.css` — monolito do tema; muitas regras por variante de seção (`hero1`, `hero4`, `service1`, etc.).
- `static/institutional/css/` — legado (~520 KB); ver seção abaixo.

### Páginas com mais `style=` (antes da Fase 1)

Contagem baseline em `templates/institutional/eitech/`: **154** ocorrências em **47** arquivos.

Top páginas:

| Página | `style=` (antes) |
|--------|------------------|
| `pages/index.html` | 11 |
| `pages/mitsubishi.html` | 10 |
| `pages/service-manutencao-tpm-confiabilidade.html` | 9 |
| `pages/engenharia_embarcada.html` | 9 + bloco `<style>` |
| `pages/service-automacao-industrial-clps.html` | 8 |
| `pages/service-marketing-digital.html` | 7 |
| `pages/service-robotica-integracao.html` | 6 |
| `pages/project-details.html` | 6 |

### Páginas com blocos `<style>` (antes da Fase 1)

**6** arquivos:

| Arquivo | Situação Fase 1 |
|---------|-----------------|
| `pages/engenharia_embarcada.html` | Movido para `scb-engenharia.css` |
| `pages/projects.html` | Movido para `scb-projects.css` |
| `pages/xyron-robotics.html` | Movido para `scb-xyron.css` |
| `pages/projects-page-2.html` | Pendente Fase 2 |
| `pages/projects-page-3.html` | Pendente Fase 2 |
| `pages/service-robotica-integracao.html` | Pendente Fase 2 |

### Riscos de manutenção

1. **Duplicação tema + inline** — mesmos backgrounds (`hero-bg5.png`, `service-bg1.png`) repetidos em várias páginas hero4.
2. **Progress bars** — `main.js` anima `.bg-progress .progress-inner` lendo `data-progress`, `style.width` inline ou texto do `<span>`; remover inline sem `data-progress` quebra barras estáticas a 100%.
3. **Backgrounds com `{% static %}`** — não podem ir para CSS externo sem URL relativa (`../img/...`) ou variável CSS; caminhos relativos a partir de `css/` são seguros no deploy Django padrão.
4. **main.css monolítico** — difícil saber o que é usado; mudanças globais têm efeito colateral.
5. **Font Awesome global** — carregado em todas as páginas mesmo quando poucos ícones são usados.

---

## Classificação

| Categoria | Localização | Observação |
|-----------|-------------|------------|
| **Vendor / theme CSS** | `eitech/css/plugins/*`, `main.css` | Tema Eitech comprado/adaptado |
| **SCB custom CSS** | `scb-*.css` | Regras Smart Control Brasil; prefixo `scb-` para novas regras |
| **Inline styles** | `style=""` nos templates | Meta: reduzir por página crítica |
| **Blocos `<style>`** | Dentro de templates | Meta: zero nas páginas críticas |
| **CSS legado órfão** | `static/institutional/css/` | Não referenciado pelos templates eitech atuais |
| **Outros produtos** | `marketplace/`, `caneca_de_garagem/`, `admin_shell/` | Fora do escopo institucional eitech |

---

## CSS legado institucional

A pasta `static/institutional/css/` contém arquivos de um tema institucional anterior (ex.: `style.css`, `style-purple.css`, `smart360-institutional.css`, `bootstrap.min.css`, `fontawesome.min.css`, etc.).

**Verificação:** nenhum template em `templates/institutional/eitech/` referencia `institutional/css/` (apenas `institutional/eitech/css/` e `institutional/brand/`).

**Política Fase 1:**

- **Não apagar** — pode haver referências externas, bookmarks ou rotas antigas não mapeadas.
- **Não adicionar** novas importações apontando para esse diretório.
- **Validar** em Fase 2 com busca global + `collectstatic` antes de deprecar/arquivar.

---

## Plano incremental

### Curto prazo (Fase 1 — concluída nesta entrega)

- [x] Documentar panorama (`docs/frontend/css-audit.md`)
- [x] Extrair inline da home → `scb-home.css`
- [x] Extrair blocos `<style>` das páginas críticas → `scb-*.css` dedicados
- [x] Criar `scb-mitsubishi.css`, `scb-engenharia.css`, `scb-service.css`, `scb-projects.css`, `scb-xyron.css`
- [x] Marcar legado `static/institutional/css/` como deprecado (sem remoção)

### Médio prazo (Fase 2 — não implementar agora)

- Plugins condicionais por página (Owl, Slick, Magnific apenas onde usados)
- Reduzir Font Awesome ou trocar ícones críticos por SVG inline
- Revisar `main.css` (seções não usadas, variantes duplicadas)
- Extrair inline das demais páginas de serviço (`service-automacao-industrial-clps.html`, etc.)
- Mover `<style>` de `projects-page-2/3`, `service-robotica-integracao.html`

### Longo prazo (documentado apenas)

- `ManifestStaticFilesStorage` / cache busting
- gzip / brotli no servidor ou CDN
- Bundle / minificação controlada (sem quebrar ordem de cascade)
- Tokens / design system SCB (cores, tipografia, espaçamento)

---

## Notas técnicas — backgrounds e progress bars

### Backgrounds

Imagens em `static/institutional/eitech/img/` referenciadas no CSS via caminho relativo a partir de `css/`:

```css
background-image: url(../img/all-images/bg/hero-bg1.png);
```

Funciona com `{% static %}` no HTML substituído por classes (ex.: `scb-home-hero-bg`).

### Progress bars (`main.js`)

O script em `static/institutional/eitech/js/main.js` (bloco “PROGRESS BAR AREA”):

1. Localiza `.bg-progress .progress-bar`
2. Define alvo a partir de `data-progress`, `aria-valuenow`, `style.width` ou texto do `<span>`
3. Reseta para `width: 0%` e anima no `IntersectionObserver`

**Regra segura:** manter `data-progress` ao remover `style="width: …"`; para barras a 100% com rótulo `01/02/03`, usar `data-progress="100"`.

---

## Resultado Fase 1 (jun/2026)

| Métrica | Antes | Depois |
|---------|-------|--------|
| `style=` em `templates/institutional/eitech/` | 154 | 113 |
| Arquivos com `style=` | 47 | 41 |
| Blocos `<style>` | 6 | 3 |

Páginas críticas com **zero** `style=` após Fase 1: `index`, `mitsubishi`, `engenharia_embarcada`, `service-manutencao-tpm-confiabilidade`, `projects`, `xyron-robotics`.

Blocos `<style>` restantes (Fase 2): `projects-page-2.html`, `projects-page-3.html`, `service-robotica-integracao.html`.

Validação: `manage.py check` OK; `pytest apps/institutional` — 16 passed.


Páginas com inline restante (prioridade sugerida):

- `service-automacao-industrial-clps.html`
- `service-marketing-digital.html`
- `service-robotica-integracao.html` (+ bloco `<style>`)
- `project-details.html`, `about.html`
- `projects-page-2.html`, `projects-page-3.html` (+ blocos `<style>`)
- Demais templates com 1–5 `style=` cada

---

## Fase 1.1 — Limpeza complementar

Medição inicial antes da Fase 1.1, em `templates/institutional/eitech/`:

| Métrica | Antes Fase 1.1 | Depois Fase 1.1 |
|---------|----------------|------------------|
| `style=` | 113 | 80 |
| Blocos `<style>` | 3 | 0 |

### Arquivos priorizados

- `pages/projects-page-2.html`
- `pages/projects-page-3.html`
- `pages/service-robotica-integracao.html`
- `pages/service-automacao-industrial-clps.html`
- `pages/service-marketing-digital.html`
- `pages/project-details.html`
- `partials/header.html`, `partials/footer.html`, `partials/breadcrumb.html`

### Estratégia aplicada

- Reaproveitado `scb-projects.css` para páginas de projetos e detalhes de projeto.
- Reaproveitado `scb-service.css` para páginas de serviço, backgrounds, barras de progresso, sidebar branca e regra específica do header sticky da página de robótica.
- Reaproveitado `scb-header.css` para estilos globais seguros dos partials (`header`, `footer` e `breadcrumb`).
- Removidos os três blocos `<style>` restantes, substituindo-os por `{% block extra_css %}` com CSS externo dedicado.
- Preservados `data-progress` ou adicionados `data-progress="100"` nas barras onde o `width: 100%` inline foi movido para classe.
- Evitados estilos ligados a estado dinâmico ou integrações quando havia risco.

### Pendências após a Fase 1.1

Arquivos ainda com maior incidência de `style=`:

- `pages/projects/smart360.html` — 6 ocorrências, incluindo progress bars e backgrounds de projeto.
- `pages/service-inteligencia-artificial.html` — 5 ocorrências, principalmente backgrounds.
- `pages/service-diagnostico-ia-dados-automacao.html` — 5 ocorrências, principalmente backgrounds.
- `pages/about.html` — 5 ocorrências, incluindo progress bars animadas.
- Páginas individuais em `pages/projects/` — em geral 3 ocorrências cada, com padrão repetido de hero, sidebar e seção relacionada.
- `pages/contact.html` mantém `display:none` no honeypot e espaçamento de mensagens; revisar com cuidado para não quebrar validação/formulário.

### Recomendação objetiva para Fase 2

Criar classes compartilhadas para o padrão das páginas individuais de projeto (`hero`, `case-sider-widget-area`, `case-inner-area`) e aplicar em lote controlado. Em seguida, atacar `service-inteligencia-artificial.html`, `service-diagnostico-ia-dados-automacao.html` e `about.html`, mantendo atenção especial às progress bars animadas e a estilos usados como estado inicial de JavaScript.


---

## Fase 1.2 — Classes compartilhadas

Medição inicial antes da Fase 1.2, em `templates/institutional/eitech/`:

| Métrica | Antes Fase 1.2 | Depois Fase 1.2 |
|---------|----------------|------------------|
| `style=` | 80 | 24 |
| Blocos `<style>` | 0 | 0 |

### Arquivos alterados

- `templates/institutional/eitech/pages/projects/*.html`
- `templates/institutional/eitech/pages/service-inteligencia-artificial.html`
- `templates/institutional/eitech/pages/service-diagnostico-ia-dados-automacao.html`
- `templates/institutional/eitech/pages/about.html`
- `templates/institutional/eitech/pages/contact.html`
- `static/institutional/eitech/css/scb-projects.css`
- `static/institutional/eitech/css/scb-service.css`
- `static/institutional/eitech/css/scb-contact.css`
- `static/institutional/eitech/css/scb-about.css`

### Classes compartilhadas criadas ou consolidadas

Projetos (`scb-projects.css`):

- `scb-project-hero`
- `scb-project-widget-reset`
- `scb-project-section-bg`

Serviços (`scb-service.css`):

- `scb-service-hero-primary-bg`
- `scb-service-hero6-section-bg`
- Reuso de `scb-service-hero-robotica-bg`, `scb-service-about-robotica-bg`, `scb-service-section-service-bg` e `scb-service-section-cta-bg`

Sobre (`scb-about.css`):

- `scb-about-hero-bg`
- `scb-about-section-bg`

Contato (`scb-contact.css`):

- `scb-contact-hero-bg`
- `scb-contact-form-messages`

### Inline styles mantidos de propósito

- `pages/contact.html`: `style="display:none"` no campo honeypot `website`, mantido para não alterar comportamento de validação/anti-spam nem UX do formulário.
- Demais `style=` restantes estão fora do foco seguro desta fase: páginas `service-details.html`, `blog-details.html`, `team.html`, `services.html`, `mitsubishi_antiga.html`, páginas de blog e `faq.html`.

### Pendências após a Fase 1.2

Arquivos com maior incidência restante:

- `pages/service-details.html` — 3 ocorrências.
- `pages/blog-details.html` — 3 ocorrências.
- `pages/team.html`, `pages/services.html`, `pages/mitsubishi_antiga.html` — 2 ocorrências cada.
- Páginas de blog e `faq.html` — 1 ocorrência cada, em geral background de hero.

### Recomendação objetiva para Fase 2

Criar classes compartilhadas para páginas de blog/detalhe (`inner-page-hero`, widgets com `padding: 0 !important` e seções com `service-bg1.png`) e aplicar em lote pequeno. Depois revisar `service-details.html`, `blog-details.html`, `team.html` e `services.html`, mantendo `contact.html` por último por conter elementos sensíveis de formulário.
