import json
from unittest.mock import Mock

import pytest

from peru_macro.cli import main
from peru_macro.pipeline import build


def test_demo_always_uses_synthetic_mode(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("DATABASE_URL", "postgresql://example")
    monkeypatch.setattr("sys.argv", ["macro", "--root", str(tmp_path), "demo"])
    sync = Mock(return_value={"status": "published"})
    monkeypatch.setattr("peru_macro.cli.sync", sync)
    main()
    assert sync.call_args.kwargs["dataset_mode"] == "synthetic"
    assert json.loads(capsys.readouterr().out)["dataset"] == "synthetic"


def test_credentials_required(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setattr("sys.argv", ["macro", "status"])
    with pytest.raises(SystemExit):
        main()


def test_build_has_isolated_schema_and_disables_telemetry(tmp_path, monkeypatch):
    import uuid

    call = Mock()
    promote = Mock()
    monkeypatch.setattr("peru_macro.pipeline.subprocess.run", call)
    monkeypatch.setattr("peru_macro.pipeline.promote", promote)
    runid = str(uuid.uuid4())
    schema = build(Mock(), "postgresql://demo:local_test@localhost:5432/macro", runid, tmp_path)
    assert schema == "build_" + runid.replace("-", "")
    assert call.call_args.kwargs["env"]["DBT_SEND_ANONYMOUS_USAGE_STATS"] == "false"
    assert call.call_args.kwargs["check"] is True
    assert call.call_args.args[0][:2] == ["dbt", "build"]
    promote.assert_called_once()
