from __future__ import annotations

from dataclasses import dataclass, field
from io import BytesIO
from typing import Any

from django.core.files.base import ContentFile
from django.utils import timezone


DEMO_PASSWORD = "admin123!"
BOOTSTRAP_TAG = "smart360-demo"


@dataclass
class BootstrapContext:
    stdout: Any
    demo_password: str = DEMO_PASSWORD
    verbosity: int = 1
    registry: dict[str, dict[str, Any]] = field(default_factory=dict)

    def log(self, message: str) -> None:
        if self.verbosity > 0:
            self.stdout.write(message)

    def section(self, title: str) -> None:
        self.log(f"[bootstrap] {title}")

    def put(self, bucket: str, key: str, value: Any) -> Any:
        self.registry.setdefault(bucket, {})[key] = value
        return value

    def get(self, bucket: str, key: str, default=None) -> Any:
        return self.registry.get(bucket, {}).get(key, default)


def set_password(user, password: str) -> None:
    user.set_password(password)
    user.save(update_fields=["password", "updated_at"])


def attach_content_file(instance, field_name: str, file_name: str, content: str, save: bool = True) -> None:
    file_field = getattr(instance, field_name)
    if not file_field:
        file_field.save(file_name, ContentFile(content.encode("utf-8")), save=False)
        if save:
            instance.save()


def metadata_payload(**extra) -> dict[str, Any]:
    payload = {"bootstrap_tag": BOOTSTRAP_TAG, "generated_at": timezone.now().isoformat()}
    payload.update(extra)
    return payload

