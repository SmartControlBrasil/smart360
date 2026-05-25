"""Rotas públicas do marketplace curado Caneca de Garagem (HTML)."""

from __future__ import annotations

import re
import secrets
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from itertools import cycle
from typing import Sequence

from django.conf import settings
from django.db import transaction
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse

from apps.market_core.models import MarketplaceOrder, MarketplaceOrderItem, MarketplaceProduct, MarketplaceVendor

from .forms import B2BQuoteLeadForm, ContactForm, PersonalizationLeadForm
from .models import CreativeStoreProfile

FACTORY_VENDOR_SLUG = "caneca-de-garagem-factory"
FACTORY_VENDOR_NAME = "Caneca de Garagem Factory"
QUOTE_SKU_PLACEHOLDER = "CANECA-GARAGEM-QUOTE"
PLACEHOLDER_SLUG = "pedido-personalizacao-caneca"


@dataclass(frozen=True)
class CatalogProductSnapshot:
    """Visão só-leitura para templates (BD ou fallback em memória)."""

    slug: str
    name: str
    description: str
    vendor_slug: str
    vendor_name: str
    base_price: Decimal | None
    estimated_days: int
    personalization_options: list[str]
    source_db: MarketplaceProduct | None

    def price_label(self) -> str:
        if self.base_price is None or self.base_price <= Decimal("0"):
            return "Sob orçamento"
        return _format_currency_brl(self.base_price)


MOCK_PRODUCTS_SNAPSHOT = [
    CatalogProductSnapshot(
        slug="kit-presentes-personalizados",
        name="Kit de presentes curados para datas especiais",
        description=(
            "Compõe sua caixa com itens gravados ou sublimados: canecas, squeezes "
            "e brindes combinando identidade visual. Ideal para Natal, Dia das Mães e formaturas."
        ),
        vendor_slug=FACTORY_VENDOR_SLUG,
        vendor_name=FACTORY_VENDOR_NAME,
        base_price=Decimal("0"),
        estimated_days=7,
        personalization_options=["Frase gravada ou impressa", "Paleta de cores", "Nome na embalagem", "Cartão dedicatório"],
        source_db=None,
    ),
    CatalogProductSnapshot(
        slug="caneca-sublimacao-full-color",
        name="Caneca sublimática full color (exclusividade visual)",
        description=(
            "Arte fotográfica ou ilustração com cores vivas para eventos corporativos, "
            "turmas ou comunidades que querem lembrança forte e durável."
        ),
        vendor_slug=FACTORY_VENDOR_SLUG,
        vendor_name=FACTORY_VENDOR_NAME,
        base_price=Decimal("54.90"),
        estimated_days=5,
        personalization_options=[
            "Imagem frontal e verso",
            "Frase lateral",
            "Variações por nome (turma)",
        ],
        source_db=None,
    ),
    CatalogProductSnapshot(
        slug="brinde-evento-baixo-volume",
        name="Linha de brindes artesanais para eventos sob curadoria",
        description=(
            "Pequenas tiragens com acabamento cuidadoso para eventos até 200 convidados. "
            "Foco em entrega combinada entre criadores da rede."
        ),
        vendor_slug=FACTORY_VENDOR_SLUG,
        vendor_name=FACTORY_VENDOR_NAME,
        base_price=Decimal("0"),
        estimated_days=10,
        personalization_options=["Selo institucional", "Data do evento", "Papelaria complementar sob consulta"],
        source_db=None,
    ),
]

MOCK_VENDORS = [
    {"slug": FACTORY_VENDOR_SLUG, "name": FACTORY_VENDOR_NAME},
]

EXPLORE_CANECAS_NAMES = [
    "Caneca branca personalizada",
    "Caneca mágica personalizada",
    "Caneca interior colorido",
    "Caneca profissão",
    "Caneca casal",
    "Caneca pet",
]

EXPLORE_LONG_DRINK_NAMES = [
    "Copo long drink personalizado",
    "Long drink para festa",
    "Long drink corporativo",
    "Long drink casamento",
    "Long drink aniversário",
    "Long drink evento",
]

EXPLORE_CAMISETAS_NAMES = [
    "Camiseta personalizada empresa",
    "Camiseta evento",
    "Camiseta família",
    "Camiseta profissão",
    "Camiseta frase criativa",
    "Camiseta turma/escola",
]

EXPLORE_CHOPP_NAMES = [
    "Caneca de chopp personalizada",
    "Caneca de chopp para bar",
    "Caneca de chopp evento",
    "Caneca de chopp presente",
    "Caneca de chopp corporativa",
    "Kit chopp personalizado",
]

EXPLORE1_CARD_IDS = [35, 36, 37, 38, 1, 2, 3, 4, 19, 20, 21, 22, 27, 28, 29, 30]
EXPLORE2_CARD_IDS = [53, 54, 55, 56, 27, 28, 29, 30, 12, 13, 14, 15, 57, 58, 59, 60]
EXPLORE3_CARD_IDS = [53, 54, 55, 56, 27, 28, 29, 30, 12, 13, 14, 15, 57, 58, 59, 60, 15, 57]
EXPLORE4_CARD_IDS = [49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60]


@dataclass(frozen=True)
class ExploreCardVm:
    """Card de grade para páginas explore (somente dados de apresentação)."""

    display_name: str
    detail_slug: str
    creator_name: str
    price_label: str
    card_static_path: str
    avatar_static_path: str
    wow_delay: str | None
    outer_use_wow: bool
    outer_use_fl_item: bool


def _static_public(subpath_under_assets: str) -> str:
    path = subpath_under_assets.strip().lstrip("/")
    return f"caneca_de_garagem/public/assets/{path}"


def _snapshot_match_score(label_lower_tokens: Sequence[str], snap: CatalogProductSnapshot) -> int:
    hay = snap.name.lower()
    return sum(1 for tok in label_lower_tokens if tok in hay)


def _best_snapshot_for_label(label: str, snaps: Sequence[CatalogProductSnapshot]) -> CatalogProductSnapshot | None:
    tokens = [
        tok
        for tok in re.split(r"[^\wÀ-Üà-ü]+", label.lower())
        if len(tok.strip()) >= 3
    ]
    if not tokens:
        return None
    best: CatalogProductSnapshot | None = None
    best_score = -1
    pool = tuple(snaps) if snaps else tuple(MOCK_PRODUCTS_SNAPSHOT)
    for cand in pool:
        sc = _snapshot_match_score(tokens, cand)
        if sc > best_score:
            best = cand
            best_score = sc
    return best if best_score > 0 else None


def _build_explore_content_rows(
    labels: Sequence[str], card_nums: Sequence[int], snaps_override: Sequence[CatalogProductSnapshot] | None = None
) -> list[tuple[str, CatalogProductSnapshot | None, int]]:
    rows: list[tuple[str, CatalogProductSnapshot | None, int]] = []
    snaps = list(snaps_override) if snaps_override is not None else catalog_products()
    for i, n in enumerate(card_nums):
        label = labels[i % len(labels)]
        snap = _best_snapshot_for_label(label, snaps)
        rows.append((label, snap, n))
    return rows


def _vm_from_explore_rows(
    rows: Sequence[tuple[str, CatalogProductSnapshot | None, int]],
    *,
    outer_use_wow: bool,
    outer_use_fl_item: bool,
    wow_delays: Sequence[str | None] | None = None,
) -> list[ExploreCardVm]:
    vms: list[ExploreCardVm] = []
    for i, (label, snap, n_card) in enumerate(rows):
        slug = snap.slug if snap else PLACEHOLDER_SLUG
        creator = snap.vendor_name if snap else FACTORY_VENDOR_NAME
        price = snap.price_label() if snap else "Sob orçamento"
        delay: str | None = None
        if wow_delays is not None and i < len(wow_delays):
            delay = wow_delays[i]
        wow_active = bool(outer_use_wow and delay is not None)
        box_idx = (i % 7) + 1
        card_static_path = _static_public(f"images/box-item/card-item-{n_card:02d}.jpg")
        avatar_static_path = _static_public(f"images/avatar/avatar-box-{box_idx:02d}.jpg")
        vms.append(
            ExploreCardVm(
                display_name=label,
                detail_slug=slug,
                creator_name=creator,
                price_label=price,
                card_static_path=card_static_path,
                avatar_static_path=avatar_static_path,
                wow_delay=delay if wow_active else None,
                outer_use_wow=wow_active,
                outer_use_fl_item=outer_use_fl_item,
            )
        )
    return vms


def _explore_tabs_long_drink(
    rows: Sequence[tuple[str, CatalogProductSnapshot | None, int]],
) -> list[dict[str, object]]:
    """Quatro panes conforme explore-2 (aba «Items» ativa)."""

    wow_cycle_row2 = tuple(["0s", "0.1s", "0.2s", "0.3s"][i % 4] for i in range(len(rows)))
    panes_raw: list[tuple[bool, bool, Sequence[str | None] | None]] = [
        (False, True, tuple(None for _ in rows)),
        (True, False, wow_cycle_row2),
        (False, False, tuple(None for _ in rows)),
        (False, False, tuple(None for _ in rows)),
    ]

    pans: list[dict[str, object]] = []
    for pane_idx, (uw, uf, dels) in enumerate(panes_raw):
        slots = _vm_from_explore_rows(rows, outer_use_wow=uw, outer_use_fl_item=uf, wow_delays=dels)
        pans.append(
            {
                "active_inner": pane_idx == 1,
                "slots": slots,
            }
        )
    return pans


def _wow_delays_explore_camisetas(card_count: int) -> tuple[str | None, ...]:
    wow_cycle = ["0s", "0.1s", "0.2s"]
    return tuple(wow_cycle[i % 3] if i < card_count - 3 else None for i in range(card_count))


def _wow_delays_explore_chopp(card_count: int) -> tuple[str, ...]:
    wow_cycle = ["0s", "0.1s", "0.2s"]
    return tuple(wow_cycle[i % 3] for i in range(card_count))


def _explore_shell(
    *,
    template: str,
    request: HttpRequest,
    title: str,
    heading: str,
    meta_description: str,
    category_key: str,
    cta_url: str,
    cta_label: str,
    **extra: object,
) -> HttpResponse:
    ctx = {
        **_shell_context(request),
        "page_title": title,
        "page_heading": heading,
        "meta_explore_description": meta_description,
        "category_key": category_key,
        "explore_category_key": category_key,
        "cta_primary_url": cta_url,
        "cta_primary_label": cta_label,
        **extra,
    }
    return render(request, template, ctx)


def _asset(path_under_public_assets: str) -> str:
    return f"caneca_de_garagem/public/assets/{path_under_public_assets.lstrip('/')}"


BANNER_IMAGES = [_asset(f"images/box-item/banner-{i:02d}.jpg") for i in range(1, 8)]
CARD_IMAGES = [_asset(f"images/box-item/card-item-{i:02d}.jpg") for i in range(1, 10)]
AVATAR_SELLERS = [_asset(f"images/avatar/avatar-{i:02d}.png") for i in range(1, 7)]
AVATAR_BOX = [_asset(f"images/avatar/avatar-box-{i:02d}.jpg") for i in range(1, 8)]
SMALL_AVATAR = [_asset(f"images/avatar/avatar-small-{i:02d}.png") for i in (1, 2, 3, 4, 1)]

# Fallback chain se JPG de catálogo não existir no deploy — imagens reais do tema quando presentes
_CDG_CATALOG_CARD_FALLBACK_TRY: tuple[str, ...] = (
    _asset("images/item-background/bg-action-1.png"),
    _asset("images/item-background/bg-line.svg"),
)
_CDG_CATALOG_AVATAR_FALLBACK = _asset("icon/Favicon.png")


def _cdg_static_exists(rel_static: str) -> bool:
    from django.contrib.staticfiles import finders

    return finders.find(rel_static) is not None


def _cdg_first_existing_static(*paths: str) -> str | None:
    for p in paths:
        if p and _cdg_static_exists(p):
            return p
    return None


def _cdg_catalog_card_visual(preferred: str) -> str:
    found = _cdg_first_existing_static(preferred, *_CDG_CATALOG_CARD_FALLBACK_TRY)
    return found if found is not None else _CDG_CATALOG_CARD_FALLBACK_TRY[-1]


def _cdg_catalog_avatar_visual(preferred: str) -> str:
    if preferred and _cdg_static_exists(preferred):
        return preferred
    fb = _cdg_first_existing_static(_CDG_CATALOG_AVATAR_FALLBACK, *_CDG_CATALOG_CARD_FALLBACK_TRY)
    return fb if fb is not None else _CDG_CATALOG_CARD_FALLBACK_TRY[-1]


COLLECTION_PREVIEW_IMAGES = [
    [
        _asset(f"images/box-item/img-collection-{a:02d}.jpg"),
        _asset(f"images/box-item/img-collection-{b:02d}.jpg"),
        _asset(f"images/box-item/img-collection-{c:02d}.jpg"),
        _asset(f"images/box-item/img-collection-{d:02d}.jpg"),
    ]
    for (a, b, c, d) in ((1, 2, 3, 4), (3, 4, 5, 6), (5, 6, 7, 8), (2, 5, 8, 9), (6, 7, 8, 9))
]


@dataclass(frozen=True)
class BlogPostVm:
    """Material de blog público definido na view (fallback estático até existir modelo)."""

    slug: str
    title: str
    category: str
    date_display: str
    author: str
    excerpt: str
    list_image_asset: str
    hero_image_asset: str
    mid_image_asset: str
    detail_pair_assets: tuple[str, str]
    tags: tuple[str, ...]
    intro_lead: str
    section1_heading: str
    section1_lead_paragraph: str
    quote_text: str
    section1_closing_paragraph: str
    section2_heading: str
    section2_opening_paragraph: str
    section2_middle_paragraph: str
    section2_closing_paragraph: str


def _blog_detail_assets(index: int) -> tuple[str, str, tuple[str, str]]:
    """Combinações de arte do template preservando proporção visual."""

    combos = (
        (1, 2, 3, 4),
        (2, 3, 4, 1),
        (3, 4, 1, 2),
        (4, 1, 2, 3),
        (1, 3, 4, 2),
        (2, 4, 1, 3),
    )
    hero, mid, pair_a, pair_b = combos[index % len(combos)]
    return (
        _asset(f"images/blog/blog-detail-{hero:02d}.png"),
        _asset(f"images/blog/blog-detail-{mid:02d}.png"),
        (
            _asset(f"images/blog/blog-detail-{pair_a:02d}.png"),
            _asset(f"images/blog/blog-detail-{pair_b:02d}.png"),
        ),
    )


def _blog_build_posts_ordered() -> tuple[BlogPostVm, ...]:
    da = [_blog_detail_assets(i) for i in range(6)]

    row1 = BlogPostVm(
        slug="como-escolher-caneca-personalizada",
        title="Como escolher uma caneca personalizada que realmente marca o momento",
        category="Canecas personalizadas",
        date_display="Seg, 03 Fev ",
        author="Marina Antunes",
        excerpt="Do briefing à prova: critérios práticos para cor, acabamento, capacidade e embalagem em presentes físicos sob curadoria.",
        list_image_asset=_asset("images/blog/blog-grid-10.jpg"),
        hero_image_asset=da[0][0],
        mid_image_asset=da[0][1],
        detail_pair_assets=da[0][2],
        tags=("Canecas", "Sublimação", "Presentes"),
        intro_lead=(
            "Se você está montando uma lembrança para evento, empresa ou família reunida,"
            " a caneca é um dos presentes físicos mais lembrados no cotidiano. A pergunta certa não é apenas “bonita ou não”:"
            " é se a peça conta a história e aguenta o uso sem frustrar."
        ),
        section1_heading="Material, acabamento e legibilidade fazem mais diferença do que só o desenho",
        section1_lead_paragraph=(
            "Tudo começa quando alinhamos o objetivo da lembrança com o comportamento das pessoas que vão usar."
            " Canecas com boa ergonomia ganham espaço na mesa, no home office e até em estúdios de criação."
            " Arte abstrata vale o investimento apenas quando há contraste suficiente para leitura de nomes,"
            " frases institucionais e pequenas variações por colaborador."
        ),
        quote_text=(
            "“O melhor brinde é o que a pessoa pega várias vezes na semana. Se a pegada ficou só ‘para foto’,"
            " a produção ficou cara demais pelo impacto.”"
        ),
        section1_closing_paragraph=(
            "Na Caneca de Garagem combinamos tiragens flexíveis, revisão criativa antes do forno e combos com cartões ou caixas"
            " quando a ideia pede algo além da peça única."
        ),
        section2_heading="Briefing forte evita erro em cor, posição da arte e prazos de entrega",
        section2_opening_paragraph=(
            "Quanto mais cedo você define público-alvo e quantidades, mais fácil combinar tiragens inteligentes e evitar retrabalhos."
            " Pedidos bem documentados também permitem usar o mesmo arquivo para estampas relacionadas,"
            " como camisetas e squeezes combinando tema."
        ),
        section2_middle_paragraph=(
            "Quando a logística permite, consolidar entrega em pontos estratégicos reduz fretes repetidos,"
            " em especial para turmas grandes ou times com escritórios dispersos."
        ),
        section2_closing_paragraph=(
            "Se quiser algo com cara de coleção autorada, procure parceiros com portfólio consistente,"
            " provas combinadas antes da tiragem oficial e SLA claro sobre revisões — isso faz toda diferença no resultado final.",
        ),
    )

    row2 = BlogPostVm(
        slug="brindes-corporativos-baixa-tiragem",
        title="Brindes corporativos em baixa tiragem: como personalizar sem desperdiçar dinheiro",
        category="Brindes corporativos",
        date_display="Ter, 11 Fev ",
        author="Guilherme Prado",
        excerpt="Economia criativa quando o time quer impacto forte com poucas unidades.",
        list_image_asset=_asset("images/blog/blog-grid-11.jpg"),
        hero_image_asset=da[1][0],
        mid_image_asset=da[1][1],
        detail_pair_assets=da[1][2],
        tags=("Brindes", "Empresas", "Produção sob demanda"),
        intro_lead=(
            "Times com poucos colaboradores podem soar “pequenos” em volume, mas o impacto do brinde bem feito atravessa onboarding,"
            " retenção de talentos e lembrança de marca em eventos externos."
            " Produção sob demanda é o recurso mais seguro quando não dá para abrir pallets com sobra."
        ),
        section1_heading="Planeje cenários de uso: mesa executiva versus kit colaborativo",
        section1_lead_paragraph=(
            "Distribuir canetas genéricas e copos improvisados comunica menos do que combos coerentes,"
            " ainda mais quando o público é selecionado. Em baixa tiragem, cada elemento precisa estar alinhado com o discurso"
            " institucional (cores, hashtags internas ou selo comemorativo)."
        ),
        quote_text=(
            "“Em corporativo, erro de tiragem aparece rápido: excesso ocupa espaço e falta atrasa campanhas."
            " O seguro é trabalhar com lotes combinados pela curadoria.”"
        ),
        section1_closing_paragraph=(
            "Pacotes combinando caneca, squeeze ou cartão físico bem acabados permitem repetir elementos gráficos em produtos diferentes,"
            " diluindo fixos de pré-impressão e setup."
        ),
        section2_heading="Checklist rápido para fechar arquivo com tranquilidade",
        section2_opening_paragraph=(
            "Padronizar nomes nos arquivos, indicar onde nasce cada variação (nome do colaborador, sigla ou apelidos internos)"
            " e já prever arquivo de marca em vetor reduz dias de vai-e-volta com fornecedor."
        ),
        section2_middle_paragraph=(
            "Quando há múltiplos centros de entrega internos, combinamos etiquetas neutras junto ao kit para distribuição rápida"
            " sem expor dados sensíveis."
        ),
        section2_closing_paragraph=(
            "Se o evento marca um marco institucional, vale reservar unidades extras de reposição,"
            " sem transformar compra gigante.",
        ),
    )

    row3 = BlogPostVm(
        slug="arte-aprovacao-producao-personalizados",
        title="Da arte à produção: por que aprovar o layout evita retrabalho",
        category="Produção sob demanda",
        date_display="Seg, 17 Fev ",
        author="Laura Silveira",
        excerpt="Ciclos curtos funcionam quando a assinatura de arte fecha antes da primeira prova física.",
        list_image_asset=_asset("images/blog/blog-grid-12.jpg"),
        hero_image_asset=da[2][0],
        mid_image_asset=da[2][1],
        detail_pair_assets=da[2][2],
        tags=("Arte final", "Produção sob demanda"),
        intro_lead=(
            "Cada projeto personalizado vive dois momentos: o arquivo digital criativo e a peça física que viaja até as mãos do cliente."
            " Quando esse meio campo não é combinado — margens seguras, cor realista na prova, posição das variações —"
            " o retrabalho come caro.",
        ),
        section1_heading="Revisões não são frescura; são seguro jurídico e de marca",
        section1_lead_paragraph=(
            "Logos, ilustrações licenciadas e fontes institucionais precisam de versão oficial aprovada."
            " Produção física corrige pouca coisa depois da primeira impressão, então a etapa pré-forno existe para descobrir inconsistências antes."
        ),
        quote_text=(
            "“Se o layout foi aprovado por escrito, todo mundo entende o que vai sair das máquinas."
            " Surpresas desagradáveis ficam onde devem ficar — fora do chão de fábrica.”"
        ),
        section1_closing_paragraph=(
            "Documentar cor com referências claras ou prova física reduz atrito entre cliente, criador responsável pela arte e produtor técnico."
        ),
        section2_heading="Versões paralelas bem nomeadas diminuem erro humano na linha",
        section2_opening_paragraph=(
            "Arquivos `_vFINAL_FINAL` só confundem. Numere versões objetivas,"
            " anote decisões rápidas no corpo do e-mail e mantenha link para o arquivo mestre sempre na mesma pasta compartilhada."
        ),
        section2_middle_paragraph=(
            "Fluxos paralelos também ajudam: enquanto a arte principal consolida marca, placeholders com nomes"
            " permitem já medir proporção em mocks sem travar comunicação institucional."
        ),
        section2_closing_paragraph=(
            "Quanto mais cedo a Caneca recebe arquivo fechado, mais fácil encaixar no calendário de estamparia e despacho conjunto,"
            " mesmo em datas cheias.",
        ),
    )

    row4 = BlogPostVm(
        slug="presentes-personalizados-datas-comemorativas",
        title="Presentes personalizados para datas comemorativas: ideias para vender e surpreender",
        category="Presentes criativos",
        date_display="Qua, 26 Fev ",
        author="Thiago Menezes",
        excerpt="Temas festivos funcionam quando contam histórias e permitem combos com embalagens sensoriais.",
        list_image_asset=_asset("images/blog/blog-grid-13.jpg"),
        hero_image_asset=da[3][0],
        mid_image_asset=da[3][1],
        detail_pair_assets=da[3][2],
        tags=("Presentes", "Canecas", "Sublimação"),
        intro_lead=(
            "Datas comemorativas comprimem decisões: o público já chega querendo símbolo de afeto rápido, mas espera qualidade de loja física premium."
            " Personalizar é um jeito sincero de dizer que não foi presente comprado aleatoriamente.",

        ),
        section1_heading="Comece pela narrativa antes de definir SKU",
        section1_lead_paragraph=(
            "Natal pode significar retratos em família, frases divertidas sobre “panelinha”,"
            " ou kits que misturam caneca artesanal com papelaria levemente aromática." 
            " O segredo está em propor narrativa coesa, não apenas estampa descolada sobre base branca."
        ),
        quote_text=(
            "“Quem vende ideia bem contada faz upsell honesto:"
            " embalar com laço e cartão combinando paleta aumenta valor percebido sem inflar tiragem gigante.”"
        ),
        section1_closing_paragraph=(
            "Variações de nome em planilhas simples já permitem tiragens inteligentes de escolas, turmas e clubes,"
            " sempre com checklist de grafia antes de enviar arquivo."
        ),
        section2_heading="Preveja coleções paralelas quando o calendário aperta entrega física",
        section2_opening_paragraph=(
            "Dois layouts base com pequenas trocas (cor do fundo ou selo opcional)"
            " destravam SKU sem multiplicar burocracia com fornecedor parceiro."
        ),
        section2_middle_paragraph=(
            "Quando há logística combinada pela Caneca, rodamos janelas de produção próximas"
            " mantendo SLA visível até o momento do despacho final."
        ),
        section2_closing_paragraph=(
            "Mercados regionais também respondem a histórias locais,"
            " seja cidade do interior com motivo folklórico, seja time amador querendo edição especial limitada.",

        ),
    )

    row5 = BlogPostVm(
        slug="camisetas-personalizadas-eventos",
        title="Camisetas personalizadas para eventos, equipes e comunidades",
        category="Camisetas",
        date_display="Qui, 06 Mar ",
        author="Felipe Duarte",
        excerpt="Harmonização de malha, gravação técnica e calendário alinhado com calor e conforto de uso.",
        list_image_asset=_asset("images/blog/blog-grid-14.jpg"),
        hero_image_asset=da[4][0],
        mid_image_asset=da[4][1],
        detail_pair_assets=da[4][2],
        tags=("Camisetas", "Empresas", "Presentes"),
        intro_lead=(
            "Mesmo com eventos cada vez mais híbridos, a camisa continua símbolo físico forte de comunidade,"
            " seja corrida escolar ou squad de produto comemorando métricas."
            " Produção física bem feita garante foto bonita também fora das redes sociais.",
        ),
        section1_heading="Escolha de malha pesa tanto quanto a estampa frontal",
        section1_lead_paragraph=(
            "Fibras diferentes respondem diferente ao calor, ao cheiro residual de tintas e até ao encolhimento pós-lavagem."
            " Pensar público antes de arte evita dor de cabeça com reposição porque o tamanho não vestiu bem."
        ),
        quote_text=(
            "“Comunidades percebem se a peça ficou apenas ‘marketing’."
            " Quando vale caminhar quilômetros com conforto, o investimento se paga.”"
        ),
        section1_closing_paragraph=(
            "Variações de tamanhos com placeholders simples e grade fechada com antecedência garantem tiragem econômica."
        ),
        section2_heading="Cronograma físico sempre conversa com data do evento e ensaios gerais",
        section2_opening_paragraph=(
            "Combinar despacho antes de ensaios ou warmups internos garante foto coletiva já com uniformização real,"
            " inclusive em cenários externos com clima diferente.",
        ),
        section2_middle_paragraph=(
            "Quando faz sentido mesclar outros brindes, camisetas combinam bem com squeezes,"
            " viseiras ou cartões físicos já no mesmo fluxo produtivo curado pela Caneca."
        ),
        section2_closing_paragraph=(
            "Equipes grandes podem receber dois conjuntos criativos (corporativo leve versus versão bem-humorada),"
            " mantendo marca padronizada e diversão sem sair da identidade institucional."
        ),

    )

    row6 = BlogPostVm(
        slug="marketplace-curado-criadores",
        title="Marketplace curado: por que trabalhamos com criadores e parceiros selecionados",
        category="Criadores e parceiros",
        date_display="Seg, 17 Mar ",
        author="Helena Ramos",
        excerpt="Seleção não é ego: é garantir qualidade física repetível quando o arquivo digital segue até a ponta produtiva.",
        list_image_asset=_asset("images/blog/blog-grid-15.jpg"),
        hero_image_asset=da[5][0],
        mid_image_asset=da[5][1],
        detail_pair_assets=da[5][2],
        tags=("Marketplace criativo", "Empresas", "Brindes"),
        intro_lead=(
            "Somos obsessivos pela experiência do presente físico porque ele precisa funcionar mesmo sem filtro,"
            " longe das telas. Por isso a curadoria de parceiros acompanha amostragem, feedback de clientes reais,"
            " e monitoramento técnico de estamparias parceiras."
        ),
        section1_heading="Rede física combinada permite experimentos sem dispersar marca",
        section1_lead_paragraph=(
            "Trabalhar com grupos já alinhados a processos revisados permite combinar coleções paralelas,"
            " sem que cada pedido reinvente SLA do zero ou confunda expectativa de cliente final."
        ),
        quote_text=(
            "“Curadoria é filtro técnico: mostramos apenas o que aguentamos replicar,"
            " sem surpresas indesejadas na entrega física.”"
        ),
        section1_closing_paragraph=(
            "Ao priorizar relacionamentos próximos, também conseguimos antecipar gargalo de tiragem alta em datas estratégicas.",
        ),
        section2_heading="Cliente final percebe acabamento, não apenas desenho",
        section2_opening_paragraph=(
            "Detalhe de borda bem fechada, cor consistente mesmo em tiragens diferentes do mesmo SKU,"
            " ou embalagem que proteja brinde até o momento da entrega pessoal somam reputação,"
            " mesmo que redes sociais mostrem apenas o arquivo digital."
        ),
        section2_middle_paragraph=(
            "Quando projeto precisa atravessar regiões, parceiros alinhados com rotas combinadas pela Caneca preservam SLA"
            " visível até o momento do código de rastreio físico consolidado.",

        ),
        section2_closing_paragraph=(
            "Novos criadores em avaliação sempre passam por provas físicas antes de irem ao catálogo público."
            " Mantemos esse rigor porque acreditamos que brinde mal produzido derruba toda coleção paralela bem planejada."
        ),
    )

    return (row1, row2, row3, row4, row5, row6)


BLOG_SIDEBAR_CATEGORIES: tuple[tuple[str, str], ...] = (
    ("Canecas personalizadas", "(312)"),
    ("Brindes corporativos", "(148)"),
    ("Camisetas", "(203)"),
    ("Produção sob demanda", "(96)"),
    ("Criadores e parceiros", "(174)"),
    ("Presentes criativos", "(228)"),
)

BLOG_SIDEBAR_TAGS: tuple[str, ...] = (
    "Canecas",
    "Sublimação",
    "Brindes",
    "Empresas",
    "Presentes",
    "Camisetas",
    "Arte final",
    "Produção sob demanda",
    "Marketplace criativo",
)


BLOG_POSTS_ORDERED: tuple[BlogPostVm, ...] = _blog_build_posts_ordered()


def blog_list(request: HttpRequest) -> HttpResponse:
    patched: list[dict[str, object]] = []
    for i, post in enumerate(BLOG_POSTS_ORDERED):
        patched.append(
            {
                "post": post,
                "card_image": post.list_image_asset,
                "avatar_asset": AVATAR_BOX[i % len(AVATAR_BOX)],
            }
        )

    dup_meta = (
        (BLOG_POSTS_ORDERED[0], _asset("images/blog/blog-grid-16.jpg")),
        (BLOG_POSTS_ORDERED[1], _asset("images/blog/blog-grid-17.jpg")),
    )
    for j, (post, img) in enumerate(dup_meta):
        patched.append(
            {
                "post": post,
                "card_image": img,
                "avatar_asset": AVATAR_BOX[(len(BLOG_POSTS_ORDERED) + j) % len(AVATAR_BOX)],
            }
        )

    sidebar_feature = BLOG_POSTS_ORDERED[0]
    sidebar_rest = list(BLOG_POSTS_ORDERED[1:4])

    ctx = {
        **_shell_context(request),
        "blog_grid_cards": patched,
        "blog_sidebar_featured": sidebar_feature,
        "blog_sidebar_small_posts": sidebar_rest,
        "blog_sidebar_categories": BLOG_SIDEBAR_CATEGORIES,
        "blog_sidebar_tags": BLOG_SIDEBAR_TAGS,
    }
    return render(request, "caneca_de_garagem/blog_list.html", ctx)


def blog_detail(request: HttpRequest, slug: str) -> HttpResponse:
    post_map = {p.slug: idx for idx, p in enumerate(BLOG_POSTS_ORDERED)}
    if slug not in post_map:
        raise Http404("Post não encontrado.")
    ix = post_map[slug]
    post = BLOG_POSTS_ORDERED[ix]
    prev_post = BLOG_POSTS_ORDERED[ix - 1] if ix > 0 else None
    next_post = BLOG_POSTS_ORDERED[ix + 1] if ix + 1 < len(BLOG_POSTS_ORDERED) else None
    alternatives = [p for p in BLOG_POSTS_ORDERED if p.slug != slug]
    sidebar_pool = alternatives if alternatives else list(BLOG_POSTS_ORDERED)
    sidebar_main = sidebar_pool[0]
    sidebar_small = sidebar_pool[1:4]

    ctx = {
        **_shell_context(request),
        "post": post,
        "prev_post": prev_post,
        "next_post": next_post,
        "blog_sidebar_featured": sidebar_main,
        "blog_sidebar_small_posts": sidebar_small,
        "blog_sidebar_categories": BLOG_SIDEBAR_CATEGORIES,
        "blog_sidebar_tags": BLOG_SIDEBAR_TAGS,
    }
    return render(request, "caneca_de_garagem/blog_detail.html", ctx)


def _cycle_pad(snaps: list[CatalogProductSnapshot], n: int) -> list[CatalogProductSnapshot]:
    base = list(snaps or MOCK_PRODUCTS_SNAPSHOT)
    if len(base) >= n:
        return base[:n]
    cyc = cycle(base)
    return [next(cyc) for _ in range(n)]


def _collection_labels() -> list[str]:
    return [
        "Coleções de presentes",
        "Linha corporativa",
        "Temas especiais",
        "Kits com identidade",
        "Edições combinadas parceiros",
    ]


def _format_currency_brl(value: Decimal) -> str:
    quant = value.quantize(Decimal("0.01"))
    return f"R$ {quant:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _whatsapp_digits() -> str:
    raw = getattr(settings, "CANECA_DE_GARAGEM_WHATSAPP", "").strip()
    return "".join(c for c in raw if c.isdigit())


def _default_personalization_options() -> list[str]:
    return [
        "Nome ou apelidos",
        "Logotipo institucional",
        "Paleta ou referência visual",
        "Frase especial / hashtags",
        "Variações por item (lista de nomes)",
    ]


def _lead_time_days_for_product(product: MarketplaceProduct) -> int:
    vendor = getattr(product, "vendor", None)
    if vendor is None:
        return 5
    profile = CreativeStoreProfile.objects.filter(vendor=vendor).first()
    if profile is not None and getattr(profile, "lead_time_days", None):
        return int(profile.lead_time_days)
    meta_days = None
    if isinstance(product.metadata, dict):
        raw = product.metadata.get("estimated_production_days")
        if isinstance(raw, int):
            meta_days = raw
        elif isinstance(raw, str) and raw.isdigit():
            meta_days = int(raw)
    return meta_days or 7


def _snapshot_from_product_row(product: MarketplaceProduct) -> CatalogProductSnapshot:
    vendor = product.vendor
    meta_opts = ()
    if isinstance(product.metadata, dict):
        opts = product.metadata.get("personalization_options")
        if isinstance(opts, list):
            meta_opts = tuple(str(x) for x in opts)
    options = list(meta_opts) if meta_opts else _default_personalization_options()
    return CatalogProductSnapshot(
        slug=product.slug,
        name=product.name,
        description=product.description or "Produto personalizado curado pela equipe.",
        vendor_slug=vendor.slug,
        vendor_name=vendor.name,
        base_price=product.base_price,
        estimated_days=_lead_time_days_for_product(product),
        personalization_options=options,
        source_db=product,
    )


def catalog_products(include_inactive_db: bool = False) -> list[CatalogProductSnapshot]:
    qs = (
        MarketplaceProduct.objects.filter(is_active=True)
        .exclude(slug=PLACEHOLDER_SLUG)
        .select_related("vendor")
    )
    qs = qs.filter(vendor__status=MarketplaceVendor.Status.ACTIVE)
    if not include_inactive_db and qs.exists():
        return [_snapshot_from_product_row(p) for p in qs.order_by("name")]
    return list(MOCK_PRODUCTS_SNAPSHOT)


def catalog_vendor_dicts(product_snapshots: list[CatalogProductSnapshot]) -> list[dict[str, str]]:
    qs = MarketplaceVendor.objects.filter(status=MarketplaceVendor.Status.ACTIVE).order_by("name")
    if qs.exists():
        return [{"slug": v.slug, "name": v.name} for v in qs]
    seen: dict[str, str] = {}
    for snap in product_snapshots:
        seen.setdefault(snap.vendor_slug, snap.vendor_name)
    extra = [{"slug": s["slug"], "name": s["name"]} for s in MOCK_VENDORS if s["slug"] not in seen]
    return [{"slug": k, "name": v} for k, v in seen.items()] + extra


def get_product_snapshot(slug: str) -> CatalogProductSnapshot:
    if slug == PLACEHOLDER_SLUG:
        raise Http404("Produto interno.")

    row = MarketplaceProduct.objects.filter(slug=slug, is_active=True).select_related("vendor").first()
    if row and row.vendor.status == MarketplaceVendor.Status.ACTIVE:
        return _snapshot_from_product_row(row)
    for snap in MOCK_PRODUCTS_SNAPSHOT:
        if snap.slug == slug:
            return snap
    raise Http404("Produto não encontrado")


def ensure_factory_vendor() -> MarketplaceVendor:
    vendor, _ = MarketplaceVendor.objects.get_or_create(
        slug=FACTORY_VENDOR_SLUG,
        defaults={"name": FACTORY_VENDOR_NAME, "status": MarketplaceVendor.Status.ACTIVE},
    )
    return vendor


def ensure_quote_placeholder_product(factory: MarketplaceVendor) -> MarketplaceProduct:
    product, _created = MarketplaceProduct.objects.get_or_create(
        slug=PLACEHOLDER_SLUG,
        defaults={
            "vendor": factory,
            "sku": QUOTE_SKU_PLACEHOLDER,
            "name": "Solicitação de personalização (curadoria)",
            "description": (
                "Item técnico usado apenas para registrar pedidos de curadoria e orçamentos "
                "sem pagamento online no MVP público."
            ),
            "base_price": Decimal("0.00"),
            "is_customizable": True,
            "is_active": False,
            "metadata": {"internal": True, "purpose": "public_lead_placeholder"},
        },
    )
    return product


def _new_order_code() -> str:
    return f"CDG-{datetime.now():%Y%m%d}-{secrets.token_hex(3).upper()}"


def _flat_lead_payload(cleaned: dict, *, channel: str) -> dict[str, object]:
    return {
        "channel": channel,
        "customer_name": cleaned.get("customer_name"),
        "whatsapp": cleaned.get("whatsapp"),
        "email": cleaned.get("email"),
        "quantity": cleaned.get("quantity"),
        "message_or_phrase": cleaned.get("message_or_phrase"),
        "observations": cleaned.get("observations") or cleaned.get("message"),
        "usage_type": cleaned.get("usage_type"),
        "artwork_need": cleaned.get("artwork_need"),
        "organization_name": cleaned.get("organization_name"),
        "job_title_or_area": cleaned.get("job_title_or_area"),
        "subject": cleaned.get("subject"),
    }


def _save_personalization_lead(snapshot: CatalogProductSnapshot, cleaned: dict) -> str:
    factory = ensure_factory_vendor()
    placeholder = ensure_quote_placeholder_product(factory)

    qty = int(cleaned["quantity"])
    target = snapshot.source_db
    line_product = placeholder
    unit_price = Decimal("0")
    total = Decimal("0")
    if target is not None:
        line_product = target
        unit_price = target.base_price or Decimal("0")
        total = unit_price * qty

    payload = _flat_lead_payload(cleaned, channel="personalization")
    payload.update(
        {
            "product_slug": snapshot.slug,
            "product_label": snapshot.name,
            "partner_slug": snapshot.vendor_slug,
            "partner_label": snapshot.vendor_name,
            "pricing_display": snapshot.price_label(),
        }
    )

    with transaction.atomic():
        code = _new_order_code()
        order = MarketplaceOrder.objects.create(
            code=code,
            status=MarketplaceOrder.Status.PENDING,
            total_amount=total,
            notes=(
                f"Lead público · {snapshot.name}\n"
                f"Parceiro: {snapshot.vendor_name}\n"
                f"Cliente: {cleaned['customer_name']} ({cleaned['email']})\n"
                + (payload.get("message_or_phrase") or "")
            ),
            metadata=payload,
        )
        MarketplaceOrderItem.objects.create(
            order=order,
            product=line_product,
            quantity=qty,
            unit_price=unit_price or Decimal("0"),
            vendor=line_product.vendor,
            metadata={
                "presentation_product_slug": snapshot.slug,
                "presentation_product_name": snapshot.name,
            },
        )

    return code


def _save_b2b_lead(cleaned: dict) -> str:
    factory = ensure_factory_vendor()
    placeholder = ensure_quote_placeholder_product(factory)

    qty = int(cleaned["quantity"])
    payload = _flat_lead_payload(cleaned, channel="b2b_quote")

    notes = (
        f"Pedido corporativo · {cleaned['organization_name']}\n"
        f"Responsável: {cleaned['customer_name']} — {cleaned['email']} / {cleaned['whatsapp']}\n"
    )

    with transaction.atomic():
        code = _new_order_code()
        order = MarketplaceOrder.objects.create(
            code=code,
            status=MarketplaceOrder.Status.PENDING,
            total_amount=Decimal("0"),
            notes=notes,
            metadata=payload,
        )
        MarketplaceOrderItem.objects.create(
            order=order,
            product=placeholder,
            quantity=max(qty, 1),
            unit_price=Decimal("0"),
            vendor=factory,
            metadata={"b2b": True},
        )

    return code


def _save_contact_lead(cleaned: dict) -> str:
    payload = {
        "channel": "contact",
        "customer_name": cleaned["customer_name"],
        "email": cleaned["email"],
        "whatsapp": cleaned.get("whatsapp"),
        "subject": cleaned["subject"],
        "message": cleaned["message"],
    }
    notes = (
        f"Contato site · {payload['subject']}\n{payload['customer_name']} ({payload['email']})\n\n{payload['message']}"
    )
    code = _new_order_code()
    with transaction.atomic():
        MarketplaceOrder.objects.create(
            code=code,
            status=MarketplaceOrder.Status.PENDING,
            total_amount=Decimal("0"),
            notes=notes,
            metadata=payload,
        )
    return code


def _whatsapp_url_for_payload(message_lines: list[str]) -> str | None:
    digits = _whatsapp_digits()
    if not digits:
        return None
    from urllib.parse import quote

    body = quote("\n".join(message_lines))
    return f"https://wa.me/{digits}?text={body}"


def _shell_context(request: HttpRequest) -> dict[str, object]:
    _ = request
    digits = _whatsapp_digits()
    whatsapp_quick_url = f"https://wa.me/{digits}" if digits else None
    plist = catalog_products()
    primary = plist[0] if plist else MOCK_PRODUCTS_SNAPSHOT[0]
    return {
        "whatsapp_digits_present": bool(digits),
        "whatsapp_quick_url": whatsapp_quick_url,
        "primary_product_slug": primary.slug,
        "layout_mode": "default",
        "catalog_product_count": len(plist),
    }


def home(request: HttpRequest) -> HttpResponse:
    products_all = catalog_products()
    padded = _cycle_pad(products_all, 14)
    vendors = catalog_vendor_dicts(products_all)

    whatsapp_intro = [
        "Olá, vim pelo site da Caneca de Garagem 👋",
        "Quero falar sobre personalizados.",
    ]

    hero_slides: list[dict[str, object]] = []
    for i in range(7):
        p = padded[i]
        hero_slides.append({"product": p, "banner_static": BANNER_IMAGES[i % len(BANNER_IMAGES)]})

    featured_slides = [
        {"product": padded[i], "card_static": CARD_IMAGES[i % len(CARD_IMAGES)], "avatar": AVATAR_BOX[i % len(AVATAR_BOX)]}
        for i in range(8)
    ]

    seller_slots = []
    if len(vendors) >= 8:
        vv = vendors[:8]
    else:
        filler = MOCK_VENDORS * 8
        vv = list(vendors) + filler[: max(0, 8 - len(vendors))]
    if not vv:
        vv = list(MOCK_VENDORS)
    for i in range(8):
        vdict = vv[i % len(vv)]
        seller_slots.append(
            {
                "slug": str(vdict["slug"]),
                "name": str(vdict["name"]),
                "avatar": AVATAR_SELLERS[i % len(AVATAR_SELLERS)],
                "badge": padded[i].price_label(),
            }
        )

    discover_items = []
    for i in range(8):
        idx = i + 5
        p = padded[idx % len(padded)]
        discover_items.append(
            {
                "product": p,
                "card_static": CARD_IMAGES[(i + 3) % len(CARD_IMAGES)],
                "avatar": AVATAR_BOX[(i + 2) % len(AVATAR_BOX)],
                "wow_delay": f"{i * 0.1:.1f}s",
            }
        )

    partner_strip_a = []
    partner_strip_b = []
    for i in range(12):
        v = vv[i % len(vv)] if vv else MOCK_VENDORS[0]
        partner_strip_a.append(
            {"name": str(v["name"]), "avatar": SMALL_AVATAR[i % len(SMALL_AVATAR)], "slug": str(v["slug"])}
        )
    for i in range(12):
        k = i + 3
        v = vv[k % len(vv)] if vv else MOCK_VENDORS[0]
        partner_strip_b.append(
            {"name": str(v["name"]), "avatar": SMALL_AVATAR[(i + 1) % len(SMALL_AVATAR)], "slug": str(v["slug"])}
        )

    top_collections_items = []
    for i in range(len(_collection_labels())):
        vpick = vv[i % len(vv)] if vv else MOCK_VENDORS[0]
        top_collections_items.append(
            {
                "title": f"{vpick['name']}",
                "subtitle": f"@{str(vpick['slug'])[:28]}",
                "images_static": COLLECTION_PREVIEW_IMAGES[i % len(COLLECTION_PREVIEW_IMAGES)],
                "poster_static": AVATAR_SELLERS[i % len(AVATAR_SELLERS)],
                "label": _collection_labels()[i],
            }
        )

    ctx = {
        **_shell_context(request),
        "featured_products": products_all[:12],
        "vendors_preview": vendors[:10],
        "collections_intro": (
            "Coleções com curadoria de presentes criativos, sublimação premium e linhas sob medida para "
            "empresas, escolas e eventos especiais."
        ),
        "hero_slides": hero_slides,
        "featured_slides_home": featured_slides,
        "seller_slots": seller_slots,
        "discover_items_home": discover_items,
        "partner_strip_a": partner_strip_a,
        "partner_strip_b": partner_strip_b,
        "top_collections_home": top_collections_items,
    }
    return render(request, "caneca_de_garagem/home.html", ctx)


def product_list(request: HttpRequest) -> HttpResponse:
    q = (request.GET.get("q") or "").strip().lower()
    products = catalog_products()
    if q:
        products = [p for p in products if q in p.name.lower() or q in p.vendor_name.lower()]
    vendors = catalog_vendor_dicts(products)
    padded = _cycle_pad(products, 10)
    market_carousel = []
    for i in range(10):
        p = padded[i]
        pref_card = CARD_IMAGES[(i + 6) % len(CARD_IMAGES)]
        pref_avatar = AVATAR_BOX[i % len(AVATAR_BOX)]
        market_carousel.append(
            {
                "product": p,
                "price_display": p.price_label(),
                "card_static": _cdg_catalog_card_visual(pref_card),
                "avatar": _cdg_catalog_avatar_visual(pref_avatar),
            }
        )
    grid_len = max(len(products), 12) if products else 12
    grid_pad = _cycle_pad(products, grid_len)
    product_grid_visual = []
    for i in range(len(grid_pad)):
        p = grid_pad[i]
        product_grid_visual.append(
            {
                "product": p,
                "price_display": p.price_label(),
                "card_static": _cdg_catalog_card_visual(CARD_IMAGES[i % len(CARD_IMAGES)]),
                "avatar": _cdg_catalog_avatar_visual(AVATAR_BOX[(i + 2) % len(AVATAR_BOX)]),
            }
        )
    ctx = {
        **_shell_context(request),
        "layout_mode": "market",
        "products": products,
        "vendors": vendors,
        "query": q,
        "market_carousel": market_carousel,
        "product_grid_visual": product_grid_visual,
        "catalog_headline_suffix": (" — filtros públicos quando houver resultado." if q else ""),
    }
    return render(request, "caneca_de_garagem/product_list.html", ctx)


def product_detail(request: HttpRequest, slug: str) -> HttpResponse:
    snapshot = get_product_snapshot(slug)

    initial = {"product_slug": snapshot.slug, "partner_slug": snapshot.vendor_slug}

    if request.method == "POST":
        data = request.POST.copy()
        if not data.get("product_slug"):
            data["product_slug"] = snapshot.slug
        if not data.get("partner_slug"):
            data["partner_slug"] = snapshot.vendor_slug
        form = PersonalizationLeadForm(data)
    else:
        form = PersonalizationLeadForm(initial=initial)

    if request.method == "POST" and form.is_valid():
        code = _save_personalization_lead(snapshot, form.cleaned_data)
        request.session["caneca_last_order_code"] = code

        whatsapp_tail = [
            "",
            "---",
            f"Pedido: {code}",
            f"Produto: {snapshot.name}",
            "Caneca de Garagem · curadoria",
        ]

        wf = [
            form.cleaned_data["customer_name"],
            f"Mensagem: {form.cleaned_data['message_or_phrase']}",
        ] + whatsapp_tail
        whatsapp_follow = _whatsapp_url_for_payload(wf)

        request.session["caneca_whatsapp_follow"] = whatsapp_follow or ""
        return redirect(reverse("caneca_de_garagem:order_success") + f"?code={code}")

    related = [p for p in catalog_products() if p.vendor_slug == snapshot.vendor_slug and p.slug != snapshot.slug][:4]
    pool_related = related if related else catalog_products() or list(MOCK_PRODUCTS_SNAPSHOT)
    rel_visual = []
    ry = cycle(pool_related)
    for _ in range(4):
        rel_visual.append(next(ry))

    thumb_static = [_asset("images/box-item/product-01.jpg"), _asset("images/box-item/product-02.jpg"), _asset("images/box-item/product-03.jpg")]

    ctx = {
        **_shell_context(request),
        "product": snapshot,
        "form": form,
        "related_products": related,
        "detail_thumbs_static": thumb_static,
        "related_slide_items": [{"p": rel_visual[i], "card_static": CARD_IMAGES[(i + 1) % len(CARD_IMAGES)], "avatar": AVATAR_BOX[(i + 3) % len(AVATAR_BOX)]} for i in range(4)],
    }
    return render(request, "caneca_de_garagem/product_detail.html", ctx)


def author_list(request: HttpRequest) -> HttpResponse:
    products = catalog_products()
    vendors = catalog_vendor_dicts(products)

    enriched_list: list[dict[str, object]] = []
    for v in vendors:
        slug_val = str(v["slug"])
        snaps = [p for p in products if p.vendor_slug == slug_val]
        accent = snaps[0].price_label() if snaps else "Sob briefing"
        enriched_list.append(
            {
                "slug": slug_val,
                "name": v["name"],
                "product_sample": snaps[0].name if snaps else "Curadoria em breve.",
                "count": len(snaps),
                "accent": accent,
            }
        )
    if not enriched_list:
        enriched_list.append(
            {
                "slug": FACTORY_VENDOR_SLUG,
                "name": FACTORY_VENDOR_NAME,
                "product_sample": "Kit de presentes personalizados sob curadoria.",
                "count": len(products),
                "accent": "Sob briefing",
            }
        )

    ranking_rows: list[dict[str, object]] = []
    wow_pat = ("0s", "0.1s", "0.2s")
    for i in range(24):
        src = enriched_list[i % len(enriched_list)]
        ranking_rows.append(
            {
                "slug": src["slug"],
                "name": src["name"],
                "accent": src["accent"],
                "rank_shell_class": "tf-color" if i < 3 else "opacity-01",
                "rank_number": i + 1,
                "wow_delay": wow_pat[i % len(wow_pat)],
                "avatar_asset": AVATAR_SELLERS[i % len(AVATAR_SELLERS)],
            }
        )

    ctx = {
        **_shell_context(request),
        "vendors_enriched": enriched_list,
        "author_rank_grid": ranking_rows,
    }
    return render(request, "caneca_de_garagem/author_list.html", ctx)


def author_detail(request: HttpRequest, slug: str) -> HttpResponse:
    vendor = MarketplaceVendor.objects.filter(slug=slug, status=MarketplaceVendor.Status.ACTIVE).first()
    if vendor is None and slug != FACTORY_VENDOR_SLUG:
        raise Http404("Criador não encontrado.")

    profile = CreativeStoreProfile.objects.filter(vendor=vendor).first() if vendor else None
    fallback_name = dict(MOCK_VENDORS).get(slug, FACTORY_VENDOR_NAME)

    vendor_name = (profile.display_name if profile and profile.display_name else None) or (
        vendor.name if vendor else fallback_name
    )
    bio = (profile.bio if profile else "") or ""

    snaps = catalog_products()
    vp = [p for p in snaps if p.vendor_slug == slug]

    if not vp and slug == FACTORY_VENDOR_SLUG:
        vp = [p for p in snaps]

    others = catalog_vendor_dicts(snaps)
    filtered = [v for v in others if str(v["slug"]) != slug]
    if not filtered:
        filtered = [{"slug": str(x["slug"]), "name": str(x["name"])} for x in MOCK_VENDORS]

    accent_cycle = cycle(
        ["R$ 149,90", "Sob consulta", "R$ 79,90", "Curadoria viva", "R$ 310,90", "Sob briefing"]
    )
    style3_slots = []
    for i in range(24):
        base = dict(filtered[i % len(filtered)])
        if str(base["slug"]) == slug:
            base = dict(filtered[(i + 1) % len(filtered)])
            if str(base["slug"]) == slug:
                base = dict(filtered[(i + 2) % len(filtered)])
        avatar_num = 8 + (i % 6)
        accent = next(accent_cycle)
        wow = ["0s", "0.1s", "0.2s", "0.3s", "0.4s", "0.5s"][i % 6]
        style3_slots.append(
            {
                "slug": str(base["slug"]),
                "display_name": str(base["name"]),
                "accent": accent,
                "wow_delay": wow,
                "numeric_order": i + 1,
                "avatar_asset": _asset(f"images/avatar/avatar-{avatar_num:02d}.png"),
            }
        )

    ctx = {
        **_shell_context(request),
        "vendor_slug": slug,
        "vendor_name": vendor_name,
        "vendor_bio": (
            bio.strip()
            if bio.strip()
            else "Este parceiro faz parte da curadoria oficial da rede Caneca de Garagem."
        ),
        "vendor_products": vp,
        "partner_is_factory": slug == FACTORY_VENDOR_SLUG,
        "creator_style3_related": style3_slots,
    }
    return render(request, "caneca_de_garagem/author_detail.html", ctx)


def _market_shell_context(request: HttpRequest, *, tab: str) -> dict[str, object]:
    return {**_shell_context(request), "layout_mode": "market", "cdg_market_active_tab": tab}


def marketplace_dashboard(request: HttpRequest) -> HttpResponse:
    return render(request, "caneca_de_garagem/market.html", _market_shell_context(request, tab="market"))


def marketplace_explore(request: HttpRequest) -> HttpResponse:
    return render(request, "caneca_de_garagem/market_explore.html", _market_shell_context(request, tab="explore"))


def marketplace_active_quotes(request: HttpRequest) -> HttpResponse:
    return render(request, "caneca_de_garagem/market_active_quote.html", _market_shell_context(request, tab="bid"))


def marketplace_collections(request: HttpRequest) -> HttpResponse:
    return render(request, "caneca_de_garagem/market_collection.html", _market_shell_context(request, tab="tf-collection"))


def marketplace_favorites(request: HttpRequest) -> HttpResponse:
    return render(request, "caneca_de_garagem/market_favorite.html", _market_shell_context(request, tab="favorite"))


def marketplace_orders_area(request: HttpRequest) -> HttpResponse:
    return render(request, "caneca_de_garagem/market_orders_area.html", _market_shell_context(request, tab="wallet"))


def marketplace_history(request: HttpRequest) -> HttpResponse:
    return render(request, "caneca_de_garagem/market_history.html", _market_shell_context(request, tab="history"))


def marketplace_partner_create_product(request: HttpRequest) -> HttpResponse:
    return render(request, "caneca_de_garagem/market_create.html", _market_shell_context(request, tab="create"))




CDG_TERMS_SECTIONS_PT: tuple[str, ...] = (
    (
        "A Caneca de Garagem é uma vitrine combinando presentes físicos personalizados, sublimação técnica, curadoria de parceiros "
        "e produção nacional coordenada. Qualquer comunicação oficial começa sempre por humanos da própria operação — "
        "não vendemos coleções automatizadas sem revisão física combinada antes da tiragem."
    ),
    (
        "Todos os projetos físicos aparecem como produção sob demanda combinada caso a caso. Prazos, quantidades finais "
        "e custos aparecem somente depois da leitura de briefing, disponibilidade de matéria-prima nacional e revisão obrigatória "
        "de arte em ambiente controlado com o parceiro responsável antes do forno, serigrafia ou gravação real."
    ),
    (
        "Você declara titularidade/licença suficiente para qualquer marca, foto, lettering ou obra enviados. Conteúdo que sugira uso "
        "indevido de terceiros segue barrado até assinatura de termo próprio quando exigido. O marketplace não hospeda garantia jurídica "
        "além dessa revisão combinada antes do pedido físico."
    ),
    (
        "Cada parceiro curado trabalha dentro de suas capacidades físicas combinadas nacionalmente — sem prometer estoque fantasioso. "
        "Quando dois parceiros compartilham componentes combinados fisicamente, o cliente será avisado com prazos e responsabilidades separados."
    ),
    (
        "O acesso público permite navegar coleções combinadas até o pedido combinado físico estar documentado pela curadoria. "
        "Recursos extras assíncronos (histórico ampliado, split online, dashboards logísticos) podem ficar apenas visuais ou em breve, "
        "sem substituir o contrato combinado oficial enviado após briefing."
    ),
    (
        "Ao enviar um briefing você concorda que os dados foram preenchidos de boa-fé. Informações incompletas atrasam o retorno combinado físico "
        "e não geram SLA automático. Revisões gratuitas combinadas ficam sempre numeradas até o limite do parceiro responsável antes da tiragem."
    ),
    (
        "Ao compartilhar arquivos, você autoriza apenas o uso combinado físico relacionado aos pedidos aprovados, sem cessão ampliada de direitos "
        "autorais além dessa tiragem combinada física nacional. Fotos institucionais da peça física combinada aparecem somente mediante consentimento próprio específico."
    ),
    (
        "Ao conversar pela curadoria — e-mails, formulários públicos ou canais combinados oficialmente — você aceita comunicações operativas físicas relacionadas aos pedidos combinados até o despacho combinado físico estar concluído."
    ),
    (
        "Atualizações públicas combinadas físicas aparecem na mesma página. Em caso divergência, sempre prevalece o contrato humano combinado depois "
        "do último arquivo aprovado e registrado físico enviado por e-mail da curadoria."
    ),
)


def terms_condition(request: HttpRequest) -> HttpResponse:
    ctx = {
        **_shell_context(request),
        "cdg_terms_blocks": CDG_TERMS_SECTIONS_PT,
    }
    return render(request, "caneca_de_garagem/terms_condition.html", ctx)


def no_result(request: HttpRequest) -> HttpResponse:
    plist = catalog_products()
    padded = _cycle_pad(plist, 8)
    suggested = []
    for i in range(min(8, len(padded))):
        prod = padded[i]
        suggested.append(
            {
                "product": prod,
                "card_static": CARD_IMAGES[i % len(CARD_IMAGES)],
                "detail_url": reverse("caneca_de_garagem:product_detail", kwargs={"slug": prod.slug}),
            }
        )

    ctx = {
        **_shell_context(request),
        "suggested_product_cards": suggested,
    }
    return render(request, "caneca_de_garagem/no_result.html", ctx)


FAQ_ITEMS_CONTEXT: tuple[dict[str, str], ...] = (
    {
        "q": "Como funciona um pedido totalmente personalizado?",
        "a": (
            "Você descreve a ideia, envia logos ou fotos dentro dos limites licenciados, e a curadoria alinha expectativa de cor, tiragem "
            "e prazo físico antes de qualquer cobrança. Depois você recebe prova combinada antes da tiragem oficial."
        ),
        "initial_open": "",
    },
    {
        "q": "Posso usar marcas registradas ou personagens?",
        "a": (
            "Apenas com autorização válida ou material que você mesmo detiver direitos claros para reprodução. "
            "A Caneca pode recusar peças que coloquem em risco fornecedor, cliente ou parceiros selecionados."
        ),
        "initial_open": "",
    },
    {
        "q": "Quanto tempo demora?",
        "a": (
            "Varia pela técnica (sublimação, gravação, serigrafia) e fila combinada dos parceiros. Em janelas comuns de curadoria, "
            "estimamos 5 a 14 dias corridos úteis após a arte aprovada, podendo aumentar conforme urgência física nacional."
        ),
        "initial_open": " active",
    },
    {
        "q": "Como ficam pagamento, retirada e envio?",
        "a": (
            "Nesta fase pública combinamos valores com briefing humano. Retiradas locais aparecem no recibo combinado quando existirem, "
            "e envios nacionais usam código de postagem físico assim que despachamos em parceiros alinhados."
        ),
        "initial_open": "",
    },
)


def faq(request: HttpRequest) -> HttpResponse:
    ctx = {
        **_shell_context(request),
        "faq_items": FAQ_ITEMS_CONTEXT,
    }
    return render(request, "caneca_de_garagem/faq.html", ctx)


def coming_soon(request: HttpRequest) -> HttpResponse:
    ctx = {
        **_shell_context(request),
        "cta_url": reverse("caneca_de_garagem:contact"),
    }
    return render(request, "caneca_de_garagem/coming_soon.html", ctx)


def maintenance_preview(request: HttpRequest) -> HttpResponse:
    ctx = {**_shell_context(request)}
    return render(request, "caneca_de_garagem/maintenance.html", ctx)


def not_found_preview(request: HttpRequest) -> HttpResponse:
    ctx = {**_shell_context(request)}
    return render(request, "caneca_de_garagem/404.html", ctx)


def login_preview(request: HttpRequest) -> HttpResponse:
    ctx = {**_shell_context(request)}
    return render(request, "caneca_de_garagem/login.html", ctx)


def sign_up_preview(request: HttpRequest) -> HttpResponse:
    ctx = {**_shell_context(request)}
    return render(request, "caneca_de_garagem/sign_up.html", ctx)


def b2b_quote(request: HttpRequest) -> HttpResponse:
    form = B2BQuoteLeadForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        code = _save_b2b_lead(form.cleaned_data)
        request.session["caneca_last_order_code"] = code
        whatsapp_follow = _whatsapp_url_for_payload(
            [
                f"Orçamento corporativo #{code}",
                form.cleaned_data["organization_name"],
                form.cleaned_data["customer_name"],
            ]
        )
        request.session["caneca_whatsapp_follow"] = whatsapp_follow or ""

        return redirect(reverse("caneca_de_garagem:order_success") + f"?code={code}")

    ctx = {
        **_shell_context(request),
        "form": form,
    }
    return render(request, "caneca_de_garagem/b2b_quote.html", ctx)


def explore_canecas(request: HttpRequest) -> HttpResponse:
    rows = _build_explore_content_rows(EXPLORE_CANECAS_NAMES, EXPLORE1_CARD_IDS)
    wow_delays = tuple(["0s", "0.1s", "0.2s", "0.3s"][i % 4] if i < 12 else None for i in range(len(rows)))
    slots = _vm_from_explore_rows(
        rows, outer_use_wow=True, outer_use_fl_item=True, wow_delays=wow_delays
    )
    sh = _shell_context(request)
    return _explore_shell(
        template="caneca_de_garagem/explore_canecas.html",
        request=request,
        title="Canecas personalizadas",
        heading="Canecas personalizadas",
        meta_description=(
            "Canecas brancas, mágicas, temáticas e pet-friendly com curadoria Caneca de Garagem "
            "- personalização sob coordenação humana da produção física."
        ),
        category_key="canecas",
        cta_url=reverse("caneca_de_garagem:product_detail", kwargs={"slug": str(sh["primary_product_slug"])}),
        cta_label="Solicitar personalização",
        explore_slots=slots,
    )


def explore_long_drink(request: HttpRequest) -> HttpResponse:
    rows = _build_explore_content_rows(EXPLORE_LONG_DRINK_NAMES, EXPLORE2_CARD_IDS)
    panes = _explore_tabs_long_drink(rows)
    return _explore_shell(
        template="caneca_de_garagem/explore_long_drink.html",
        request=request,
        title="Long Drink personalizado",
        heading="Long Drink personalizado",
        meta_description=(
            "Copos long drink para festas, casamentos e ações corporativas com briefing dedicado,"
            " provas combinadas e entrega física através da rede Caneca de Garagem."
        ),
        category_key="long-drink",
        cta_url=reverse("caneca_de_garagem:b2b_quote"),
        cta_label="Solicitar orçamento",
        explore_tab_panes=panes,
    )


def explore_camisetas(request: HttpRequest) -> HttpResponse:
    rows = _build_explore_content_rows(EXPLORE_CAMISETAS_NAMES, EXPLORE3_CARD_IDS)
    wow_delays = _wow_delays_explore_camisetas(len(rows))
    slots = _vm_from_explore_rows(
        rows, outer_use_wow=True, outer_use_fl_item=False, wow_delays=wow_delays
    )
    sh = _shell_context(request)
    return _explore_shell(
        template="caneca_de_garagem/explore_camisetas.html",
        request=request,
        title="Camisetas personalizadas",
        heading="Camisetas personalizadas",
        meta_description=(
            "Camisetas sob demanda para empresas, turmas de escola ou família com revisão criativa antes da impressão física."
        ),
        category_key="camisetas",
        cta_url=reverse("caneca_de_garagem:product_detail", kwargs={"slug": str(sh["primary_product_slug"])}),
        cta_label="Solicitar personalização",
        explore_slots=slots,
    )


def explore_caneca_chopp(request: HttpRequest) -> HttpResponse:
    rows = _build_explore_content_rows(EXPLORE_CHOPP_NAMES, EXPLORE4_CARD_IDS)
    wow_delays = _wow_delays_explore_chopp(len(rows))
    slots = _vm_from_explore_rows(
        rows, outer_use_wow=True, outer_use_fl_item=False, wow_delays=wow_delays
    )
    return _explore_shell(
        template="caneca_de_garagem/explore_caneca_chopp.html",
        request=request,
        title="Caneca de chopp personalizada",
        heading="Caneca de chopp personalizada",
        meta_description=(
            "Caneca de chopp para bares e eventos, kits completos sob curadoria e logística combinada pela Caneca de Garagem."
        ),
        category_key="caneca-chopp",
        cta_url=reverse("caneca_de_garagem:b2b_quote"),
        cta_label="Solicitar orçamento",
        explore_slots=slots,
    )


def about(request: HttpRequest) -> HttpResponse:
    ctx = {
        **_shell_context(request),
    }
    return render(request, "caneca_de_garagem/about.html", ctx)


def contact(request: HttpRequest) -> HttpResponse:
    form = ContactForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        code = _save_contact_lead(form.cleaned_data)
        request.session["caneca_last_order_code"] = code

        whatsapp_follow = _whatsapp_url_for_payload(
            [
                f"Contato site #{code}",
                form.cleaned_data["subject"],
                form.cleaned_data["customer_name"],
            ]
        )
        request.session["caneca_whatsapp_follow"] = whatsapp_follow or ""
        return redirect(reverse("caneca_de_garagem:order_success") + f"?code={code}")

    ctx = {
        **_shell_context(request),
        "form": form,
    }
    return render(request, "caneca_de_garagem/contact.html", ctx)


def order_success(request: HttpRequest) -> HttpResponse:
    code = request.GET.get("code") or request.session.get("caneca_last_order_code") or ""

    whatsapp_follow_raw = request.session.pop("caneca_whatsapp_follow", "")

    ctx = {
        **_shell_context(request),
        "order_code": code.strip(),
        "whatsapp_follow_url": whatsapp_follow_raw or None,
        "whatsapp_label": getattr(settings, "CANECA_DE_GARAGEM_WHATSAPP", "").strip() or None,
    }
    return render(request, "caneca_de_garagem/order_success.html", ctx)
