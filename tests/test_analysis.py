from uuid import uuid4

import pytest

from open_job_radar.analysis import (
    CandidateProfile,
    RemoteScope,
    classify_remote_scope,
    evaluate_candidate_score,
    evaluate_hard_filters,
    evaluate_matching_signals,
)
from open_job_radar.ingestion import CanonicalJob


def job(*, location: str | None = None, is_remote: bool | None = None, description: str | None = None) -> CanonicalJob:
    return CanonicalJob(
        source_tenant_id=uuid4(),
        provider="fixture",
        provider_job_id="job-1",
        original_url="https://jobs.example.test/job-1",
        title="Engineer",
        company="Example",
        location=location,
        is_remote=is_remote,
        description=description,
    )


@pytest.mark.parametrize(
    ("location", "is_remote", "description", "expected"),
    [
        ("Remote - Brazil", True, None, RemoteScope.BRAZIL),
        ("Remote - LATAM", True, None, RemoteScope.LATAM),
        ("Remote - Americas", True, None, RemoteScope.AMERICAS),
        ("Worldwide", True, None, RemoteScope.WORLDWIDE),
        ("Remote - US", True, None, RemoteScope.US_ONLY),
        ("US", True, None, RemoteScope.US_ONLY),
        ("Remote - Europe", True, None, RemoteScope.EU_ONLY),
        ("EU", True, None, RemoteScope.EU_ONLY),
        ("New York, NY", False, None, RemoteScope.ONSITE),
        ("Remote - Americas", False, "Hybrid schedule", RemoteScope.HYBRID),
        ("Remote", True, None, RemoteScope.UNKNOWN),
    ],
)
def test_classifies_every_supported_remote_scope(
    location: str,
    is_remote: bool,
    description: str | None,
    expected: RemoteScope,
) -> None:
    assert classify_remote_scope(job(location=location, is_remote=is_remote, description=description)) is expected


def test_hybrid_precedes_geographic_and_worldwide_signals() -> None:
    posting = job(
        location="Remote - Worldwide",
        is_remote=True,
        description="Hybrid role for candidates in Brazil.",
    )

    assert classify_remote_scope(posting) is RemoteScope.HYBRID


def test_onsite_flag_precedes_geographic_remote_scope() -> None:
    posting = job(location="Brazil", is_remote=False)

    assert classify_remote_scope(posting) is RemoteScope.ONSITE


def test_specific_geographic_signals_precede_broader_signals() -> None:
    posting = job(location="Remote - LATAM (including Brazil)", is_remote=True)

    assert classify_remote_scope(posting) is RemoteScope.BRAZIL


@pytest.mark.parametrize(
    "description",
    [
        "Remote and location flexible",
        "Remote role with a global team",
        "Remote in the region to be determined",
    ],
)
def test_ambiguous_remote_wording_is_unknown(description: str) -> None:
    assert classify_remote_scope(job(location="Remote", is_remote=True, description=description)) is RemoteScope.UNKNOWN


def test_hard_filter_accepts_matching_geography_and_authorization() -> None:
    result = evaluate_hard_filters(
        CandidateProfile(country="Brazil", authorized_regions=frozenset({"Brazil"})),
        job(location="Remote - Brazil", is_remote=True),
    )

    assert result.passed is True
    assert result.remote_scope is RemoteScope.BRAZIL
    assert "accepted" in result.reason


def test_hard_filter_rejects_incompatible_geography() -> None:
    result = evaluate_hard_filters(
        CandidateProfile(country="Brazil", authorized_regions=frozenset({"Brazil"})),
        job(location="Remote - US", is_remote=True),
    )

    assert result.passed is False
    assert result.remote_scope is RemoteScope.US_ONLY
    assert "incompatible" in result.reason


def test_hard_filter_rejects_missing_authorization() -> None:
    result = evaluate_hard_filters(
        CandidateProfile(country="Brazil", authorized_regions=frozenset({"EU"})),
        job(location="Remote - Brazil", is_remote=True),
    )

    assert result.passed is False
    assert "authorization" in result.reason


def test_hard_filter_rejects_unknown_scope_instead_of_assuming_worldwide() -> None:
    result = evaluate_hard_filters(
        CandidateProfile(country="Brazil", authorized_regions=frozenset({"worldwide"})),
        job(location="Remote", is_remote=True),
    )

    assert result.passed is False
    assert result.remote_scope is RemoteScope.UNKNOWN
    assert "unknown" in result.reason
    assert "insufficient" in result.reason


def test_hard_filter_rejects_onsite_job_for_remote_only_candidate() -> None:
    result = evaluate_hard_filters(
        CandidateProfile(country="Brazil", authorized_regions=frozenset({"Brazil"})),
        job(location="Sao Paulo", is_remote=False),
    )

    assert result.passed is False
    assert result.remote_scope is RemoteScope.ONSITE
    assert "requires remote work" in result.reason


def test_matching_signals_explain_each_positive_match() -> None:
    signals = evaluate_matching_signals(
        CandidateProfile(country="Brazil", authorized_regions=frozenset({"Brazil"})),
        job(location="Remote - Brazil", is_remote=True),
    )

    assert [signal.name for signal in signals] == [
        "remote_preference",
        "geography",
        "authorization",
    ]
    assert all(signal.reason for signal in signals)
    assert "brazil" in signals[0].reason
    assert "candidate country Brazil" in signals[1].reason
    assert "authorization" in signals[2].reason


def test_matching_signals_omit_non_matching_profile_evidence() -> None:
    signals = evaluate_matching_signals(
        CandidateProfile(country="United States", remote_only=False),
        job(location="Remote - Brazil", is_remote=True),
    )

    assert signals == ()


def test_matching_signals_omit_evidence_for_missing_scope_data() -> None:
    signals = evaluate_matching_signals(
        CandidateProfile(
            country="Brazil",
            authorized_regions=frozenset({"worldwide"}),
        ),
        job(location="Remote", is_remote=True),
    )

    assert signals == ()


def test_matching_signals_respect_conflicting_onsite_evidence() -> None:
    signals = evaluate_matching_signals(
        CandidateProfile(country="Brazil", authorized_regions=frozenset({"Brazil"})),
        job(
            location="Brazil",
            is_remote=False,
            description="Hybrid schedule with remote flexibility",
        ),
    )

    assert signals == ()


def test_candidate_score_combines_positive_signals_with_version_and_explanations() -> None:
    result = evaluate_candidate_score(
        CandidateProfile(country="Brazil", authorized_regions=frozenset({"Brazil"})),
        job(location="Remote - Brazil", is_remote=True),
    )

    assert result.scoring_version == "v1"
    assert result.eligible is True
    assert result.remote_scope is RemoteScope.BRAZIL
    assert result.score == 3
    assert [signal.name for signal in result.signals] == [
        "remote_preference",
        "geography",
        "authorization",
    ]
    assert all(signal.name in explanation for signal, explanation in zip(result.signals, result.explanations))
    assert all(signal.reason in result.explanations[index] for index, signal in enumerate(result.signals))


def test_candidate_score_is_the_number_of_positive_matching_signals() -> None:
    result = evaluate_candidate_score(
        CandidateProfile(country="Brazil", authorized_regions=frozenset({"Brazil"}), remote_only=False),
        job(location="Remote - Brazil", is_remote=True),
    )

    assert result.eligible is True
    assert result.score == len(result.signals) == 2
    assert [signal.name for signal in result.signals] == ["geography", "authorization"]


def test_candidate_score_rejects_before_applying_positive_signals() -> None:
    result = evaluate_candidate_score(
        CandidateProfile(country="Brazil", authorized_regions=frozenset({"EU"})),
        job(location="Remote - Brazil", is_remote=True),
    )

    assert result.scoring_version == "v1"
    assert result.eligible is False
    assert result.score == 0
    assert result.signals == ()
    assert result.explanations == (result.hard_filter.reason,)


def test_candidate_score_preserves_specific_remote_scope() -> None:
    result = evaluate_candidate_score(
        CandidateProfile(country="Brazil", authorized_regions=frozenset({"LATAM"})),
        job(location="Remote - LATAM", is_remote=True),
    )

    assert result.eligible is True
    assert result.remote_scope is RemoteScope.LATAM
    assert "latam" in result.explanations[0]
