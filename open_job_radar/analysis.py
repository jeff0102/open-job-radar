"""Deterministic candidate-analysis primitives."""

from dataclasses import dataclass, field
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


@dataclass(frozen=True)
class CandidateProfile:
    """Candidate constraints used by deterministic hard filters."""

    country: str | None = None
    authorized_regions: frozenset[str | RemoteScope] = field(default_factory=frozenset)
    remote_only: bool = True

    def __post_init__(self) -> None:
        if self.country is not None and not self.country.strip():
            raise ValueError("country must not be blank")
        object.__setattr__(self, "authorized_regions", frozenset(self.authorized_regions))


@dataclass(frozen=True)
class HardFilterResult:
    """Explainable outcome of applying candidate hard constraints to a job."""

    passed: bool
    reason: str
    remote_scope: RemoteScope


@dataclass(frozen=True)
class MatchingSignal:
    """One positive, explainable match between a candidate and a job."""

    name: str
    reason: str


DEFAULT_SCORING_VERSION = "v1"


@dataclass(frozen=True)
class CandidateScore:
    """Explainable deterministic score for a candidate-job pair."""

    scoring_version: str
    eligible: bool
    score: int
    remote_scope: RemoteScope
    hard_filter: HardFilterResult
    signals: tuple[MatchingSignal, ...]
    explanations: tuple[str, ...]


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

_LATAM_COUNTRIES = {
    "argentina",
    "bolivia",
    "brazil",
    "brasil",
    "chile",
    "colombia",
    "costa rica",
    "cuba",
    "dominican republic",
    "ecuador",
    "el salvador",
    "guatemala",
    "honduras",
    "mexico",
    "nicaragua",
    "panama",
    "paraguay",
    "peru",
    "puerto rico",
    "uruguay",
    "venezuela",
}
_AMERICAS_COUNTRIES = _LATAM_COUNTRIES | {
    "canada",
    "united states",
    "usa",
    "us",
}
_EU_COUNTRIES = {
    "austria",
    "belgium",
    "bulgaria",
    "croatia",
    "cyprus",
    "czech republic",
    "denmark",
    "estonia",
    "finland",
    "france",
    "germany",
    "greece",
    "hungary",
    "ireland",
    "italy",
    "latvia",
    "lithuania",
    "luxembourg",
    "malta",
    "netherlands",
    "poland",
    "portugal",
    "romania",
    "slovakia",
    "slovenia",
    "spain",
    "sweden",
}


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


def evaluate_hard_filters(candidate: CandidateProfile, job: _CanonicalJobFields) -> HardFilterResult:
    """Apply non-negotiable candidate constraints without positive scoring."""

    remote_scope = classify_remote_scope(job)
    if remote_scope is RemoteScope.UNKNOWN:
        return HardFilterResult(
            passed=False,
            reason="rejected: remote scope is unknown; geographic eligibility is insufficient",
            remote_scope=remote_scope,
        )

    if candidate.remote_only and remote_scope in {RemoteScope.ONSITE, RemoteScope.HYBRID}:
        return HardFilterResult(
            passed=False,
            reason="rejected: job is not fully remote and candidate requires remote work",
            remote_scope=remote_scope,
        )

    if remote_scope in {RemoteScope.ONSITE, RemoteScope.HYBRID}:
        return HardFilterResult(
            passed=True,
            reason=f"accepted: candidate permits {remote_scope.value} work",
            remote_scope=remote_scope,
        )

    if not _geography_matches(candidate, remote_scope):
        country = candidate.country or "unknown candidate country"
        return HardFilterResult(
            passed=False,
            reason=(
                f"rejected: job scope {remote_scope.value} is incompatible with candidate country {country}"
            ),
            remote_scope=remote_scope,
        )

    if not _authorization_covers(candidate, remote_scope):
        return HardFilterResult(
            passed=False,
            reason=(
                f"rejected: candidate has no explicit work authorization for {remote_scope.value}"
            ),
            remote_scope=remote_scope,
        )

    return HardFilterResult(
        passed=True,
        reason=f"accepted: candidate geography and authorization match {remote_scope.value}",
        remote_scope=remote_scope,
    )


def evaluate_matching_signals(
    candidate: CandidateProfile,
    job: _CanonicalJobFields,
) -> tuple[MatchingSignal, ...]:
    """Return positive candidate-job matches in a stable, explainable order.

    This function reports evidence only; it does not decide eligibility or
    invoke the hard-filter evaluation. Callers should apply hard filters
    separately before using these signals for an eligible job.
    """

    remote_scope = classify_remote_scope(job)
    signals: list[MatchingSignal] = []

    if candidate.remote_only and remote_scope not in {
        RemoteScope.UNKNOWN,
        RemoteScope.ONSITE,
        RemoteScope.HYBRID,
    }:
        signals.append(
            MatchingSignal(
                name="remote_preference",
                reason=(
                    f"job has a {remote_scope.value} remote scope matching "
                    "the candidate's remote-only preference"
                ),
            )
        )

    if _geography_matches(candidate, remote_scope):
        country = candidate.country or "the candidate"
        signals.append(
            MatchingSignal(
                name="geography",
                reason=(
                    f"job scope {remote_scope.value} includes candidate country "
                    f"{country}"
                ),
            )
        )

    geographic_scopes = {
        RemoteScope.BRAZIL,
        RemoteScope.LATAM,
        RemoteScope.AMERICAS,
        RemoteScope.WORLDWIDE,
        RemoteScope.US_ONLY,
        RemoteScope.EU_ONLY,
    }
    if remote_scope in geographic_scopes and _authorization_covers(candidate, remote_scope):
        signals.append(
            MatchingSignal(
                name="authorization",
                reason=(
                    f"candidate authorization covers the job's {remote_scope.value} scope"
                ),
            )
        )

    return tuple(signals)


def evaluate_candidate_score(
    candidate: CandidateProfile,
    job: _CanonicalJobFields,
    *,
    scoring_version: str = DEFAULT_SCORING_VERSION,
) -> CandidateScore:
    """Return a versioned score while keeping eligibility separate from ranking."""

    if not scoring_version.strip():
        raise ValueError("scoring_version must not be blank")

    hard_filter = evaluate_hard_filters(candidate, job)
    if not hard_filter.passed:
        return CandidateScore(
            scoring_version=scoring_version,
            eligible=False,
            score=0,
            remote_scope=hard_filter.remote_scope,
            hard_filter=hard_filter,
            signals=(),
            explanations=(hard_filter.reason,),
        )

    signals = evaluate_matching_signals(candidate, job)
    explanations = tuple(f"{signal.name}: {signal.reason}" for signal in signals)
    return CandidateScore(
        scoring_version=scoring_version,
        eligible=True,
        score=len(signals),
        remote_scope=hard_filter.remote_scope,
        hard_filter=hard_filter,
        signals=signals,
        explanations=explanations,
    )


def _geography_matches(candidate: CandidateProfile, remote_scope: RemoteScope) -> bool:
    if remote_scope is RemoteScope.WORLDWIDE:
        return True
    if candidate.country is None:
        return False

    country = _normalize_text(candidate.country)
    if remote_scope is RemoteScope.BRAZIL:
        return country in {"brazil", "brasil"}
    if remote_scope is RemoteScope.LATAM:
        return country in _LATAM_COUNTRIES
    if remote_scope is RemoteScope.AMERICAS:
        return country in _AMERICAS_COUNTRIES
    if remote_scope is RemoteScope.US_ONLY:
        return country in {"united states", "usa", "us"}
    if remote_scope is RemoteScope.EU_ONLY:
        return country in _EU_COUNTRIES
    return False


def _authorization_covers(candidate: CandidateProfile, remote_scope: RemoteScope) -> bool:
    authorizations = {
        _normalize_text(region.value if isinstance(region, RemoteScope) else region)
        for region in candidate.authorized_regions
    }
    if {"worldwide", "anywhere", "global"} & authorizations:
        return True

    if candidate.country is not None:
        country = _normalize_text(candidate.country)
        if country in authorizations:
            return True
        if remote_scope is RemoteScope.LATAM and country in authorizations:
            return True

    region_names = {
        RemoteScope.BRAZIL: {"brazil", "brasil"},
        RemoteScope.LATAM: {"latam", "latin america"},
        RemoteScope.AMERICAS: {"americas", "north america"},
        RemoteScope.US_ONLY: {"us", "usa", "united states", "us only"},
        RemoteScope.EU_ONLY: {"eu", "europe", "european union", "eu only"},
        RemoteScope.WORLDWIDE: set(),
    }
    return bool(region_names.get(remote_scope, set()) & authorizations)


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


__all__ = [
    "CandidateProfile",
    "CandidateScore",
    "DEFAULT_SCORING_VERSION",
    "HardFilterResult",
    "MatchingSignal",
    "RemoteScope",
    "classify_remote_scope",
    "evaluate_candidate_score",
    "evaluate_hard_filters",
    "evaluate_matching_signals",
]
