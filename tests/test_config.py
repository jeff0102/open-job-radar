from open_job_radar.config import (
    DATABASE_URL_ENVIRONMENT_VARIABLE,
    get_database_url,
    load_database_config,
)


def test_load_database_config_reads_database_url_from_environment(monkeypatch) -> None:
    database_url = "postgresql://db.example/jobs"
    monkeypatch.setenv(DATABASE_URL_ENVIRONMENT_VARIABLE, database_url)

    config = load_database_config()

    assert config.database_url == database_url


def test_load_database_config_returns_none_when_database_url_is_absent(monkeypatch) -> None:
    monkeypatch.delenv(DATABASE_URL_ENVIRONMENT_VARIABLE, raising=False)

    config = load_database_config()

    assert config.database_url is None


def test_get_database_url_reads_current_process_environment(monkeypatch) -> None:
    database_url = "postgresql://db.example/jobs"
    monkeypatch.setenv(DATABASE_URL_ENVIRONMENT_VARIABLE, database_url)

    assert get_database_url() == database_url
