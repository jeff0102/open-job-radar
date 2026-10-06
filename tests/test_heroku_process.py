from importlib import import_module
from pathlib import Path

from fastapi import FastAPI


PROCFILE = Path(__file__).parents[1] / "Procfile"
EXPECTED_WEB_COMMAND = (
    "web: uvicorn open_job_radar.app:app --host 0.0.0.0 --port $PORT"
)


def test_heroku_web_process_uses_importable_fastapi_entrypoint() -> None:
    web_command = PROCFILE.read_text(encoding="utf-8").strip()

    assert web_command == EXPECTED_WEB_COMMAND

    module_name, app_name = "open_job_radar.app:app".split(":")
    application = getattr(import_module(module_name), app_name)

    assert isinstance(application, FastAPI)
