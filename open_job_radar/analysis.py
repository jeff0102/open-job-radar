"""Deterministic candidate-analysis primitives."""

from enum import Enum
import re
import unicodedata
from typing import Protocol


class RemoteScope(str, Enum):
    """The geographic or workplace scope supported by candidate analysis."""

    UNKNOWN = "unknown"
    BRAZIL = "brazil"
    LATAM = "latam"
    AMERICAS = "americas"
    WORLDWIDE = "worldwide"
    US_ONLY = "us-only"
    EU_ONLY = "eu-only"
    ONSITE = "onsite"
    HYBRID = "hybrid"


class _CanonicalJobFields(Protocol):
    location: str | None
    is_remote: bool | None
    title: str
    description: str | None


_ONSITE_PATTERNS = (
    r"\bon ?site\b",
    r"\bin office\b",
    r"\boffice based\b",
    r"\bon premises\b",
    r"\bfully in office\b",
)
_HYBRID_PATTERNS = (
    r"\bhybrid\b",
    r"\bpart(?:ly|ially) remote\b",
    r"\bremote and office\b",
    r"\boffice and remote\b",
    r"\bremote office\b",
)
_BRAZIL_PATTERNS = (r"\bbrazil\b", r"\bbrasil\b", r"\bsao paulo\b", r"\brio de janeiro\b")
_LATAM_PATTERNS = (r"\blatam\b", r"\blatin america\b")
_AMERICAS_PATTERNS = (
    r"\bamericas\b",
    r"\bnorth america\b",
    r"\bcanada\b",
    r"\bmexico\b",
)
_US_PATTERNS = (
    r"\bunited states\b",
    r"\busa\b",
    r"\bu s a\b",
    r"\bus only\b",
    r"\bus based\b",
    r"\b(?:remote|based) in us\b",
    r"\bremote us\b",
)
_EU_PATTERNS = (
    r"\beuropean union\b",
    r"\beurope\b",
    r"\beu only\b",
    r"\beu based\b",
    r"\b(?:remote|based) in eu\b",
    r"\bremote eu\b",
)
_WORLDWIDE_PATTERNS = (
    r"\bworldwide\b",
    r"\bwork from anywhere\b",
    r"\banywhere in the world\b",
    r"\bremote anywhere\b",
    r"\bremote globally\b",
    r"\bglobally remote\b",
    r"\blocation independent\b",
)


def classify_remote_scope(job: _CanonicalJobFields) -> RemoteScope:
    """Classify a canonical job's workplace and geographic scope.

    Explicit hybrid wording takes precedence over onsite wording, followed by
    explicit onsite evidence, geographic restrictions, and worldwide wording.
    A generic remote designation is intentionally not treated as worldwide.
    """

    text = _job_text(job)

    if _matches_any(text, _HYBRID_PATTERNS):
        return RemoteScope.HYBRID
    if _matches_any(text, _ONSITE_PATTERNS) or job.is_remote is False:
        return RemoteScope.ONSITE

    geographic_scope = _classify_geography(text, _normalize_text(job.location or ""))
    if geographic_scope is not None:
        return geographic_scope
    if _matches_any(text, _WORLDWIDE_PATTERNS):
        return RemoteScope.WORLDWIDE
    return RemoteScope.UNKNOWN


def _job_text(job: _CanonicalJobFields) -> str:
    fields = (job.location, job.title, job.description)
    normalized = " ".join(_normalize_text(field) for field in fields if field)
    return normalized.strip()


def _normalize_text(value: str) -> str:
    folded = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", " ", folded.casefold()).strip()


def _matches_any(text: str, patterns: tuple[str, ...]) -> bool:
    return any(re.search(pattern, text) for pattern in patterns)


def _classify_geography(text: str, location: str) -> RemoteScope | None:
    brazil = _matches_any(text, _BRAZIL_PATTERNS)
    latam = _matches_any(text, _LATAM_PATTERNS)
    americas = _matches_any(text, _AMERICAS_PATTERNS)
    us_only = _matches_any(text, _US_PATTERNS) or location in {"us", "u s", "usa"}
    eu_only = _matches_any(text, _EU_PATTERNS) or location in {"eu", "europe"}

    if brazil:
        return RemoteScope.BRAZIL
    if latam:
        return RemoteScope.LATAM
    if americas:
        return RemoteScope.AMERICAS
    if us_only:
        return RemoteScope.US_ONLY
    if eu_only:
        return RemoteScope.EU_ONLY
    return None


__all__ = ["RemoteScope", "classify_remote_scope"]
