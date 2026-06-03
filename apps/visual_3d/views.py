from __future__ import annotations

import json
import secrets
from datetime import datetime
from decimal import Decimal

from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.http import require_POST

from apps.caneca_de_garagem.models import CustomizationRequest
from apps.market_core.models import MarketplaceOrder, MarketplaceOrderItem, MarketplaceProduct, MarketplaceVendor


def demo(request):
    return render(request, "visual_3d/demo.html")


def editor_2d(request):
    return render(request, "visual_3d/editor_2d.html")


def _new_order_code() -> str:
    return f"CDG-2D-{datetime.now():%Y%m%d}-{secrets.token_hex(3).upper()}"


def _resolve_company_for_order(product: MarketplaceProduct):
    from apps.companies.models import Company

    vendor = getattr(product, "vendor", None)
    if vendor is not None and vendor.company_id:
        return Company.objects.filter(pk=vendor.company_id).first()
    return Company.objects.order_by("pk").first()


def _ensure_factory_vendor() -> MarketplaceVendor:
    vendor, _created = MarketplaceVendor.objects.get_or_create(
        slug="caneca-de-garagem-factory",
        defaults={
            "name": "Caneca de Garagem Factory",
            "status": MarketplaceVendor.Status.ACTIVE,
        },
    )
    return vendor


def _resolve_product_for_finish(product_key: str, product_label: str | None) -> MarketplaceProduct:
    slug_map = {
        "mug": "caneca-sublimacao-full-color",
        "longDrink": "long-drink-personalizado",
        "cap": "bone-personalizado",
    }
    mapped_slug = slug_map.get(product_key)
    if mapped_slug:
        product = MarketplaceProduct.objects.filter(slug=mapped_slug).select_related("vendor").first()
        if product is not None:
            return product

    placeholder_slug = "pedido-personalizacao-caneca"
    product = MarketplaceProduct.objects.filter(slug=placeholder_slug).select_related("vendor").first()
    if product is not None:
        return product

    vendor = _ensure_factory_vendor()
    safe_label = (product_label or "Solicitação de personalização").strip() or "Solicitação de personalização"
    return MarketplaceProduct.objects.create(
        vendor=vendor,
        name=safe_label,
        slug=f"{placeholder_slug}-{secrets.token_hex(4)}",
        sku=f"CANECA-GARAGEM-2D-{secrets.token_hex(4).upper()}",
        description="Item técnico para registro de solicitação vinda do editor 2D.",
        base_price=Decimal("0.00"),
        is_customizable=True,
        is_active=False,
        metadata={"internal": True, "source": "visual_3d_editor_2d_finish"},
    )


@require_POST
def editor_2d_finish(request):
    try:
        payload = json.loads(request.body.decode("utf-8") or "{}")
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({"ok": False, "error": "Payload inválido."}, status=400)

    product_key = str(payload.get("productKey") or "").strip()
    product_label = str(payload.get("productLabel") or "").strip()
    product_slug = str(payload.get("productSlug") or "").strip()
    source = str(payload.get("source") or "").strip() or "visual_3d_editor_2d"
    customizer_entrypoint_url = str(payload.get("customizerEntrypointUrl") or "").strip()
    origin_payload = str(payload.get("origin") or "").strip()
    customer_name = str(payload.get("customerName") or "").strip()
    customer_whatsapp = str(payload.get("customerWhatsapp") or "").strip()
    customer_email = str(payload.get("customerEmail") or "").strip()
    preview_data_url = str(payload.get("previewDataUrl") or "").strip()
    editable_project_json = payload.get("editableProjectJson")

    try:
        quantity = int(payload.get("quantity") or 0)
    except (TypeError, ValueError):
        quantity = 0

    if not product_key:
        return JsonResponse({"ok": False, "error": "productKey é obrigatório."}, status=400)
    if quantity < 1:
        return JsonResponse({"ok": False, "error": "Quantidade deve ser maior ou igual a 1."}, status=400)
    if not customer_name:
        return JsonResponse({"ok": False, "error": "Nome é obrigatório."}, status=400)
    if not customer_whatsapp:
        return JsonResponse({"ok": False, "error": "WhatsApp é obrigatório."}, status=400)
    if not preview_data_url.startswith("data:image/png;base64,"):
        return JsonResponse({"ok": False, "error": "previewDataUrl inválido."}, status=400)

    try:
        with transaction.atomic():
            product = _resolve_product_for_finish(product_key, product_label)
            company = _resolve_company_for_order(product)
            order_code = _new_order_code()
            resolved_origin = origin_payload or ("marketplace_customizer" if source == "caneca_product" else "visual_3d_editor_2d")
            resolved_created_from = customizer_entrypoint_url or "/visual-3d/editor-2d/"
            order_metadata = {
                "origin": resolved_origin,
                "storefront": "caneca_de_garagem",
                "channel": "visual_3d_editor_2d_finish",
                "created_from": resolved_created_from,
                "source": source,
                "productKey": product_key,
                "productLabel": product_label,
                "productSlug": product_slug,
                "product_key": product_key,
                "product_label": product_label,
                "product_slug": product_slug,
                "customizer_entrypoint": customizer_entrypoint_url,
                "customer_name": customer_name,
                "whatsapp": customer_whatsapp,
                "customer_email": customer_email,
                "previewDataUrl": preview_data_url,
                "editableProjectJson": editable_project_json,
                "quantity": quantity,
                "customer_whatsapp": customer_whatsapp,
                "preview_data_url": preview_data_url,
                "editable_project_json": editable_project_json,
            }
            order = MarketplaceOrder.objects.create(
                code=order_code,
                company=company,
                status=MarketplaceOrder.Status.PENDING,
                total_amount=Decimal("0.00"),
                notes=f"Solicitação recebida do editor 2D para {product_label or product_key}.",
                metadata=order_metadata,
            )
            item = MarketplaceOrderItem.objects.create(
                order=order,
                product=product,
                quantity=quantity,
                unit_price=Decimal("0.00"),
                vendor=product.vendor,
                metadata={
                    "channel": "visual_3d_editor_2d_finish",
                    "source": source,
                    "productSlug": product_slug,
                    "previewDataUrl": preview_data_url,
                    "editableProjectJson": editable_project_json,
                },
            )
            CustomizationRequest.objects.create(
                order_item=item,
                customer_text={
                    "customer_name": customer_name,
                    "customer_whatsapp": customer_whatsapp,
                    "customer_email": customer_email,
                    "productKey": product_key,
                    "productLabel": product_label,
                    "productSlug": product_slug,
                    "source": source,
                    "origin": resolved_origin,
                    "customizerEntrypointUrl": customizer_entrypoint_url,
                    "quantity": quantity,
                    "previewDataUrl": preview_data_url,
                    "editableProjectJson": editable_project_json,
                },
                extra_notes="Solicitação criada via editor 2D (Finalizar arte).",
            )
    except Exception as error:
        return JsonResponse({"ok": False, "error": f"Falha ao criar solicitação: {error}"}, status=400)

    return JsonResponse(
        {
            "ok": True,
            "order_id": str(order.id),
            "order_number": order.code,
            "redirect_url": f"{reverse('caneca_de_garagem:order_success')}?code={order.code}",
        }
    )
