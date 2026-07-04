from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from .api_client import DEFAULT_MIN_SCORE


UNSAFE_ATLAS_TOKENS = {
    "",
    "...",
    "mock-token",
    "default",
    "changeme",
    "change-me",
    "atlas-token",
    "test",
    "demo",
}
DEFAULT_MAX_PROSPECTS_PER_RUN = 10
SUPPORTED_ATLAS_SOURCES = {"mock", "google_places"}


class AtlasConfigError(ValueError):
    """Raised when the standalone Atlas PoC has unsafe or incomplete configuration."""


def _as_int(value: str | None, default: int, *, name: str) -> int:
    if value in (None, ""):
        return default
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise AtlasConfigError(f"{name} precisa ser um inteiro.") from exc


def _as_bool(value: str | None, default: bool = False) -> bool:
    if value in (None, ""):
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


@dataclass(frozen=True)
class AtlasPocConfig:
    env: str = "development"
    api_base_url: str = "http://127.0.0.1:8000"
    api_token: str = ""
    company_id: int = 0
    min_score: int = DEFAULT_MIN_SCORE
    max_prospects_per_run: int = DEFAULT_MAX_PROSPECTS_PER_RUN
    source: str = "mock"
    segment: str = "escola particular"
    city: str = "Vila Mariana"
    google_places_api_key: str = ""
    apollo_api_key: str = ""
    spreadsheet_id: str = ""
    google_application_credentials: str = ""
    enable_sheets: bool = False
    enable_mailer: bool = False
    validate_only: bool = False
    csv_output_path: str = ""
    mock_csv_path: str = ""
    write_csv_output: bool = True

    @classmethod
    def from_env(cls, environ: Mapping[str, str]) -> "AtlasPocConfig":
        places_key = (environ.get("ATLAS_GOOGLE_PLACES_KEY") or environ.get("GOOGLE_PLACES_API_KEY") or "").strip()
        apollo_key = (environ.get("ATLAS_APOLLO_KEY") or environ.get("APOLLO_API_KEY") or "").strip()
        
        env = (environ.get("ATLAS_ENV") or "development").strip().lower()
        source = (environ.get("ATLAS_SOURCE") or ("google_places" if env == "production" else "mock")).strip().lower()
        
        if env == "production" and source == "google_places":
            default_score = 70
        else:
            default_score = 5
            
        min_score = _as_int(environ.get("ATLAS_MIN_SCORE"), default_score, name="ATLAS_MIN_SCORE")

        config = cls(
            env=env,
            api_base_url=(environ.get("ATLAS_API_BASE_URL") or "http://127.0.0.1:8000").strip(),
            api_token=(environ.get("ATLAS_API_TOKEN") or "").strip(),
            company_id=_as_int(environ.get("ATLAS_COMPANY_ID"), 0, name="ATLAS_COMPANY_ID"),
            min_score=min_score,
            max_prospects_per_run=_as_int(
                environ.get("ATLAS_MAX_PROSPECTS_PER_RUN"),
                DEFAULT_MAX_PROSPECTS_PER_RUN,
                name="ATLAS_MAX_PROSPECTS_PER_RUN",
            ),
            source=source,
            segment=(environ.get("ATLAS_SEGMENT") or "escola particular").strip(),
            city=(environ.get("ATLAS_CITY") or "Vila Mariana").strip(),
            google_places_api_key=places_key,
            apollo_api_key=apollo_key,
            spreadsheet_id=(environ.get("ATLAS_SPREADSHEET_ID") or "").strip(),
            google_application_credentials=(environ.get("GOOGLE_APPLICATION_CREDENTIALS") or "").strip(),
            enable_sheets=_as_bool(environ.get("ATLAS_ENABLE_SHEETS"), False),
            enable_mailer=False,
            validate_only=_as_bool(environ.get("ATLAS_VALIDATE_ONLY"), False),
            csv_output_path=(environ.get("ATLAS_CSV_OUTPUT_PATH") or "").strip(),
            mock_csv_path=(environ.get("ATLAS_MOCK_CSV_PATH") or "").strip(),
            write_csv_output=_as_bool(environ.get("ATLAS_WRITE_CSV_OUTPUT"), True),
        )
        config.validate()
        return config

    @property
    def production(self) -> bool:
        return self.env == "production"

    @property
    def mock_mode(self) -> bool:
        return self.source == "mock"

    @property
    def use_google_places(self) -> bool:
        return self.source == "google_places"

    @property
    def can_sync_api(self) -> bool:
        return bool(self.api_base_url and self.api_token and self.company_id > 0 and self.api_token not in UNSAFE_ATLAS_TOKENS)

    def validate(self) -> None:
        if self.max_prospects_per_run <= 0:
            raise AtlasConfigError("ATLAS_MAX_PROSPECTS_PER_RUN precisa ser maior que zero.")
        if self.max_prospects_per_run > 50:
            raise AtlasConfigError("ATLAS_MAX_PROSPECTS_PER_RUN excede o limite seguro de 50 prospects para o piloto.")
        if self.min_score < 0:
            raise AtlasConfigError("ATLAS_MIN_SCORE nao pode ser negativo.")
        if not self.segment:
            raise AtlasConfigError("ATLAS_SEGMENT precisa ser configurado.")
        if not self.city:
            raise AtlasConfigError("ATLAS_CITY precisa ser configurada.")
        if self.source not in SUPPORTED_ATLAS_SOURCES:
            raise AtlasConfigError("ATLAS_SOURCE invalida. Use 'mock' ou 'google_places'.")
        if self.production:
            missing = []
            if not self.api_base_url:
                missing.append("ATLAS_API_BASE_URL")
            if not self.api_token:
                missing.append("ATLAS_API_TOKEN")
            if self.company_id <= 0:
                missing.append("ATLAS_COMPANY_ID")
            if self.use_google_places and not self.google_places_api_key:
                missing.append("GOOGLE_PLACES_API_KEY")
            if missing:
                raise AtlasConfigError("Production exige: " + ", ".join(missing) + ".")
            if self.api_token in UNSAFE_ATLAS_TOKENS:
                raise AtlasConfigError("ATLAS_API_TOKEN inseguro nao pode ser usado em production.")
