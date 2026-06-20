import mimetypes
import os.path
from io import BytesIO

from django import forms
from django.utils.text import get_valid_filename

from apps.media_library.models import ALLOWED_IMAGE_EXTENSIONS, MAX_UPLOAD_BYTES, MediaAsset


class MediaAssetForm(forms.ModelForm):
    # FileField evita PIL duplo do ImageField Django (fecha o stream antes de clean_image).
    original_file = forms.FileField(
        label="Imagem",
        required=False,
        widget=forms.FileInput(
            attrs={
                "class": "form-input",
                "accept": "image/jpeg,image/png,image/webp,.jpg,.jpeg,.png,.webp",
            }
        ),
    )

    is_active = forms.TypedChoiceField(
        label="Situação da imagem",
        coerce=lambda val: val == "1",
        choices=(("1", "Ativa"), ("0", "Inativa")),
        widget=forms.Select(attrs={"class": "form-select form-input"}),
    )

    class Meta:
        model = MediaAsset
        fields = ("title", "original_file", "alt_text", "is_active")
        widgets = {
            "title": forms.TextInput(
                attrs={"class": "form-input", "placeholder": "Título para identificar a imagem", "required": True}
            ),
            "alt_text": forms.TextInput(
                attrs={"class": "form-input", "placeholder": "Descrição curta para acessibilidade (opcional)", "maxlength": 255}
            ),
        }
        labels = {
            "title": "Título",
            "original_file": "Imagem",
            "alt_text": "Texto alternativo",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._validated_suffix = ".jpg"
        if self.instance.pk is not None:
            self.initial["is_active"] = "1" if self.instance.is_active else "0"
            # Permite edição sem reenviar arquivo (ImageField já existente na instância).
            self.fields["original_file"].required = False
        else:
            self.fields["original_file"].required = True
            self.initial.setdefault("is_active", "1")

    def _ensure_allowed_image(self, upload):
        pathish = getattr(upload, "name", "") or ""
        basename = os.path.basename(pathish) if pathish else ""
        ext_has_dot = basename and "." in basename
        ext = basename.rsplit(".", 1)[-1].lower() if ext_has_dot else ""
        if ext and ext not in ALLOWED_IMAGE_EXTENSIONS:
            raise forms.ValidationError(
                "Formatos aceitos: JPG, JPEG, PNG ou WEBP. SVG, PDF ou outros não são aceitos nesta etapa.",
                code="unsupported_format",
            )
        ctype_header = getattr(upload, "content_type", None) or ""
        guess_source = basename if basename else pathish or ""
        guess = (mimetypes.guess_type(guess_source)[0] or "").lower()
        sniff = ctype_header.lower().split(";")[0].strip() if ctype_header else ""
        # Browsers/clients pode enviar text/plain ou application/octet-stream em multipart;
        # formato real é garantido pela extensão + Pillow (evita 400 falsos nos testes e em alguns IE).
        acceptable = {
            "",
            "application/octet-stream",
            "image/jpeg",
            "image/png",
            "image/webp",
            "image/pjpeg",
            "text/plain",
        }
        if sniff and sniff not in acceptable:
            raise forms.ValidationError(
                "O tipo do arquivo parece não ser uma imagem suportada. Use JPG, PNG ou WEBP.",
                code="bad_mime",
            )
        _ = guess  # reservado para evoluções de validação

        upload.seek(0)
        raw = upload.read()
        upload.seek(0)

        if len(raw) > MAX_UPLOAD_BYTES:
            raise forms.ValidationError(
                "O arquivo excede o limite máximo de 5 MB.",
                code="file_too_large",
            )

        try:
            from PIL import Image

            probe = BytesIO(raw)
            img = Image.open(probe)
            try:
                img.verify()
            finally:
                img.close()

            probe2 = BytesIO(raw)
            img2 = Image.open(probe2)
            try:
                fmt = (img2.format or "").upper()
            finally:
                img2.close()
            if fmt not in {"JPEG", "PNG", "WEBP"}:
                raise forms.ValidationError(
                    "A imagem precisa ser JPEG, PNG ou WEBP válido.", code="pil_format"
                )
            suffix_map = {"JPEG": ".jpg", "PNG": ".png", "WEBP": ".webp"}
            self._validated_suffix = suffix_map[fmt]
            if fmt == "JPEG" and ext:
                normalized = "jpeg" if ext == "jpg" else ext
                if normalized not in {"jpeg", "jpg"}:
                    raise forms.ValidationError(
                        "A extensão do arquivo não confere com o conteúdo (JPEG esperado use .jpg ou .jpeg).",
                        code="mime_ext_mismatch",
                    )
            if fmt == "PNG" and ext and ext != "png":
                raise forms.ValidationError(
                    "A extensão do arquivo não confere com o conteúdo (PNG espera .png).",
                    code="mime_ext_mismatch",
                )
            if fmt == "WEBP" and ext and ext != "webp":
                raise forms.ValidationError(
                    "A extensão do arquivo não confere com o conteúdo (WEBP espera .webp).",
                    code="mime_ext_mismatch",
                )
        except forms.ValidationError:
            raise
        except Exception:
            raise forms.ValidationError("Não foi possível ler a imagem. Verifique se o arquivo não está corrompido.") from None

    def clean_original_file(self):
        image = self.cleaned_data.get("original_file")
        # ModelForm multipart: novo upload ausente preserva arquivo existente
        if image in (None, False):
            if not getattr(self.instance, "pk", None):
                raise forms.ValidationError("Selecione uma imagem para enviar.")
            inst_img = getattr(self.instance, "original_file", None)
            if inst_img:
                return inst_img
            raise forms.ValidationError("Selecione uma imagem para enviar.")
        self._ensure_allowed_image(image)
        basename = os.path.basename(getattr(image, "name", "") or "")
        if not basename or "." not in basename:
            slug_base = (self.cleaned_data.get("title") or "media").strip() or "media"
            slug = get_valid_filename(slug_base)[:80] or "media"
            image.name = f"{slug}{self._validated_suffix}"
        return image
