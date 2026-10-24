from datetime import date
from unittest.mock import Mock

import pytest
import requests

from peru_macro.client import bronze, fetch, source_url
from peru_macro.contracts import catalog


def test_immutable_bronze_detects_corruption(tmp_path):
    sha, path, _ = bronze(tmp_path, catalog()[0], b'{"periods":[]}')
    assert path.stem == sha
    assert bronze(tmp_path, catalog()[0], b'{"periods":[]}')[0] == sha
    path.write_bytes(b"changed")
    with pytest.raises(ValueError, match="corrupted"):
        bronze(tmp_path, catalog()[0], b'{"periods":[]}')


def response(status):
    obj = Mock()
    obj.__enter__ = Mock(return_value=obj)
    obj.__exit__ = Mock(return_value=False)
    obj.iter_content.return_value = [b"{}"]
    if status >= 400:
        obj.raise_for_status.side_effect = requests.HTTPError(response=Mock(status_code=status))
    return obj


@pytest.mark.parametrize("status,expected", [(404, 1), (403, 1), (429, 3), (500, 3)])
def test_http_retry_boundaries(status, expected, monkeypatch):
    getter = Mock(side_effect=lambda *args, **kwargs: response(status))
    monkeypatch.setattr("peru_macro.client.requests.get", getter)
    monkeypatch.setattr("peru_macro.client.time.sleep", Mock())
    with pytest.raises(requests.HTTPError):
        fetch("https://example.test")
    assert getter.call_count == expected


def test_success_and_size_limit(monkeypatch):
    monkeypatch.setattr("peru_macro.client.requests.get", Mock(return_value=response(200)))
    assert fetch("https://example.test") == b"{}"
    monkeypatch.setattr("peru_macro.client.MAX_BYTES", 1)
    with pytest.raises(ValueError, match="size budget"):
        fetch("https://example.test")


def test_frequency_is_not_inferred_from_code_suffix():
    daily = catalog()[-1]
    assert daily["code"] == "PD12301MD"
    assert "/2024-01-01/2024-01-31/" in source_url(daily, date(2024, 1, 1), date(2024, 1, 31))
