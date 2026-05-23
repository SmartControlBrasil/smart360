"""Telas Admin Shell para a Biblioteca de Imagens."""

import json

from django.contrib import messages
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views import View
from django.views.generic import DetailView
from django.views.generic.edit import FormView
from django.views.generic.list import ListView

from apps.admin_shell.views import ShellContextMixin
from apps.media_library.forms import MediaAssetForm
from apps.media_library.models import MediaAsset


class MediaLibraryBaseMixin(ShellContextMixin):
    permission_domain = "dashboard"
    permission_action = "view"
    enforce_billing_access = True

    def get_breadcrumbs(self, tail_label=None, tail_url=None, route_kwargs=None):
        crumbs = [
            {"label": "Dashboard", "url": "admin-shell:dashboard"},
            {"label": "Biblioteca de imagens", "url": "admin-shell:media-image-list"},
        ]
        if tail_label:
            if tail_url:
                crumbs.append({"label": tail_label, "url": tail_url, "route_kwargs": route_kwargs})
            else:
                crumbs.append({"label": tail_label, "url": None})
        return crumbs


class MediaAssetListView(MediaLibraryBaseMixin, ListView):
    template_name = "admin_shell/media_library/media_image_list.html"
    context_object_name = "media_assets"
    paginate_by = 24

    def get_queryset(self):
        qs = MediaAsset.objects.all().select_related("uploaded_by")

        status = self.request.GET.get("status") or "active"
        if status == "inactive":
            qs = qs.filter(is_active=False)
        elif status == "active":
            qs = qs.filter(is_active=True)
        # "all" → sem filtro extra

        q = (self.request.GET.get("q") or "").strip()
        if q:
            qs = qs.filter(Q(title__icontains=q) | Q(alt_text__icontains=q))

        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page_title"] = "Biblioteca de imagens"
        ctx["page_description"] = "Upload, pré-visualização e gestão de imagens reutilizáveis para conteúdo interno."
        ctx["breadcrumbs"] = self.get_breadcrumbs()
        ctx["search_q"] = self.request.GET.get("q") or ""
        ctx["filter_status"] = self.request.GET.get("status") or "active"
        ctx["page_actions"] = [
            {
                "label": "Enviar imagem",
                "route_name": "admin-shell:media-image-upload",
                "permission_domain": "dashboard",
                "permission_action": "create",
            },
        ]
        return ctx


class MediaAssetCreateView(MediaLibraryBaseMixin, FormView):
    template_name = "admin_shell/media_library/media_image_form.html"
    form_class = MediaAssetForm
    permission_domain = "dashboard"
    permission_action = "create"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page_title"] = "Enviar imagem"
        ctx["page_description"] = "Envie apenas JPG, PNG ou WEBP (máximo 5 MB)."
        ctx["breadcrumbs"] = self.get_breadcrumbs("Enviar", None)
        ctx["form_heading"] = "Nova imagem"
        ctx["submit_label"] = "Salvar imagem"
        return ctx

    def form_valid(self, form):
        asset = form.save(commit=False)
        user = getattr(self.request, "user", None)
        if user and user.is_authenticated:
            asset.uploaded_by = user
        asset.save()
        messages.success(self.request, "Imagem enviada com sucesso.")
        return redirect(reverse("admin-shell:media-image-detail", kwargs={"pk": asset.pk}))


class MediaAssetDetailView(MediaLibraryBaseMixin, DetailView):
    model = MediaAsset
    template_name = "admin_shell/media_library/media_image_detail.html"
    context_object_name = "asset"
    pk_url_kwarg = "pk"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        obj = self.object
        ctx["page_title"] = obj.title
        ctx["page_description"] = "Detalhes do arquivo cadastrado."
        ctx["breadcrumbs"] = self.get_breadcrumbs()
        ctx["breadcrumbs"].append({"label": obj.title, "url": None})
        if obj.image:
            ctx["absolute_image_url"] = self.request.build_absolute_uri(obj.image.url)
        ctx["formatted_size"] = obj.human_file_size()
        if obj.metadata:
            ctx["metadata_json"] = json.dumps(obj.metadata, indent=2, ensure_ascii=False)
        ctx["page_actions"] = [
            {
                "label": "Editar",
                "route_name": "admin-shell:media-image-edit",
                "route_kwargs": {"pk": obj.pk},
                "permission_domain": "dashboard",
                "permission_action": "update",
            },
            {
                "label": "Voltar para lista",
                "route_name": "admin-shell:media-image-list",
                "permission_domain": "dashboard",
                "permission_action": "view",
            },
        ]
        ctx["deactivate_action"] = {
            "label": "Desativar imagem",
            "method": "post",
            "action_url": reverse("admin-shell:media-image-deactivate", kwargs={"pk": obj.pk}),
            "permission_domain": "dashboard",
            "permission_action": "update",
        }
        return ctx


class MediaAssetUpdateView(MediaLibraryBaseMixin, FormView):
    template_name = "admin_shell/media_library/media_image_form.html"
    form_class = MediaAssetForm
    permission_domain = "dashboard"
    permission_action = "update"

    def dispatch(self, request, *args, **kwargs):
        self.object = get_object_or_404(MediaAsset, pk=kwargs["pk"])
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["instance"] = self.object
        return kwargs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page_title"] = "Editar imagem"
        ctx["page_description"] = self.object.title
        crumbs = [
            {"label": "Dashboard", "url": "admin-shell:dashboard"},
            {"label": "Biblioteca de imagens", "url": "admin-shell:media-image-list"},
            {
                "label": self.object.title[:60],
                "url": "admin-shell:media-image-detail",
                "route_kwargs": {"pk": self.object.pk},
            },
            {"label": "Editar", "url": None},
        ]
        ctx["breadcrumbs"] = crumbs
        ctx["form_heading"] = "Editar imagem"
        ctx["submit_label"] = "Salvar alterações"
        ctx["asset"] = self.object
        return ctx

    def form_valid(self, form):
        asset = form.save()
        messages.success(self.request, "Imagem atualizada com sucesso.")
        return redirect(reverse("admin-shell:media-image-detail", kwargs={"pk": asset.pk}))


class MediaAssetDeactivateView(MediaLibraryBaseMixin, View):
    permission_domain = "dashboard"
    permission_action = "update"

    def post(self, request, pk):
        asset = get_object_or_404(MediaAsset, pk=pk)
        asset.is_active = False
        asset.save()
        messages.success(request, "Imagem desativada. Ela deixa de aparecer na listagem padrão.")
        return redirect(reverse("admin-shell:media-image-detail", kwargs={"pk": asset.pk}))
