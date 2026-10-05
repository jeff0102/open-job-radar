from uuid import uuid4

from open_job_radar.ingestion import (
    CanonicalJob,
    DjinniJobRecord,
    DjinniSourceTenantAdapter,
    SourceTenantAdapter,
    job_identity_key,
    normalize_djinni_job,
    parse_djinni_job,
)


DJINNI_PAYLOAD = {
    "id": 987654,
    "title": "Senior Python Engineer",
    "company": {"name": "Acme Labs"},
    "description": "Build reliable data services.",
    "location": "Remote - LATAM",
    "remote": True,
    "url": "https://djinni.co/jobs/987654-senior-python-engineer/",
    "apply_url": "https://acme.example/jobs/987654/apply",
    "salary": "$4,000–$6,000",
    "published_at": "2026-01-02T03:04:05Z",
}


class FixtureFetcher:
    def __init__(self, payloads: tuple[dict[str, object], ...]) -> None:
        self._payloads = payloads

    def fetch(self) -> tuple[dict[str, object], ...]:
        return self._payloads


def test_djinni_payload_maps_to_provider_record() -> None:
    record = parse_djinni_job(DJINNI_PAYLOAD)

    assert isinstance(record, DjinniJobRecord)
    assert record.external_id == "987654"
    assert record.title == "Senior Python Engineer"
    assert record.company == "Acme Labs"
    assert record.description == "Build reliable data services."
    assert record.location == "Remote - LATAM"
    assert record.is_remote is True
    assert record.original_url == (
        "https://djinni.co/jobs/987654-senior-python-engineer/"
    )
    assert record.application_url == "https://acme.example/jobs/987654/apply"
    assert record.provider_data == DJINNI_PAYLOAD


def test_djinni_adapter_satisfies_contract_and_returns_stable_records() -> None:
    source_tenant_id = uuid4()
    calls: list[tuple[str, float]] = []

    def fetcher_factory(feed_url: str, *, timeout: float) -> FixtureFetcher:
        calls.append((feed_url, timeout))
        return FixtureFetcher((DJINNI_PAYLOAD,))

    adapter = DjinniSourceTenantAdapter(
        source_tenant_id,
        "https://djinni.example.test/feed.json",
        timeout=12.5,
        fetcher_factory=fetcher_factory,
    )

    assert isinstance(adapter, SourceTenantAdapter)
    assert adapter.source_tenant_id == source_tenant_id
    first = adapter.fetch_records()
    second = adapter.fetch_records()
    assert first == second
    assert first[0].external_id == "987654"
    assert calls == [
        ("https://djinni.example.test/feed.json", 12.5),
        ("https://djinni.example.test/feed.json", 12.5),
    ]


def test_djinni_record_maps_to_canonical_job() -> None:
    source_tenant_id = uuid4()
    canonical = normalize_djinni_job(source_tenant_id, parse_djinni_job(DJINNI_PAYLOAD))

    assert isinstance(canonical, CanonicalJob)
    assert canonical.source_tenant_id == source_tenant_id
    assert canonical.provider == "djinni"
    assert canonical.provider_job_id == "987654"
    assert canonical.original_url == DJINNI_PAYLOAD["url"]
    assert canonical.application_url == DJINNI_PAYLOAD["apply_url"]
    assert canonical.title == "Senior Python Engineer"
    assert canonical.company == "Acme Labs"
    assert canonical.location == "Remote - LATAM"
    assert canonical.is_remote is True
    assert canonical.provider_data == DJINNI_PAYLOAD
    assert job_identity_key(canonical) == job_identity_key(
        normalize_djinni_job(source_tenant_id, parse_djinni_job(dict(DJINNI_PAYLOAD)))
    )


def test_djinni_job_without_explicit_id_uses_url_path() -> None:
    payload = {key: value for key, value in DJINNI_PAYLOAD.items() if key != "id"}

    assert parse_djinni_job(payload).external_id == "987654-senior-python-engineer"
