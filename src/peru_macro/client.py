"""Bounded HTTP acquisition; one series per request prevents positional misalignment."""

import hashlib
import json
import time
import uuid
from datetime import date
from pathlib import Path

import requests

BASE = "https://estadisticas.bcrp.gob.pe/estadisticas/series/api"
MAX_BYTES = 20 * 1024 * 1024


def source_url(spec: dict, start: date, end: date) -> str:
    if spec["frequency"] == "D":
        first, last = start.isoformat(), end.isoformat()
    else:
        first, last = f"{start.year}-{start.month}", f"{end.year}-{end.month}"
    return f"{BASE}/{spec['code']}/json/{first}/{last}/ing"


def fetch(url: str) -> bytes:
    for attempt in range(3):
        try:
            with requests.get(
                url,
                timeout=(10, 90),
                stream=True,
                headers={"User-Agent": "peru-macro-portfolio/0.1"},
            ) as response:
                response.raise_for_status()
                result = bytearray()
                for chunk in response.iter_content(65536):
                    result.extend(chunk)
                    if len(result) > MAX_BYTES:
                        raise ValueError("Source exceeded download size budget")
                return bytes(result)
        except requests.RequestException as exc:
            status = getattr(exc.response, "status_code", None)
            if attempt == 2 or (status and status < 500 and status != 429):
                raise
            time.sleep(2**attempt)
    raise AssertionError("unreachable")


def bronze(root: Path, spec: dict, content: bytes) -> tuple[str, Path, dict]:
    sha = hashlib.sha256(content).hexdigest()
    folder = root / "bronze" / spec["code"]
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{sha}.json"
    if path.exists():
        if hashlib.sha256(path.read_bytes()).hexdigest() != sha:
            raise ValueError("Existing Bronze source is corrupted")
    else:
        temporary = folder / f".{uuid.uuid4()}.tmp"
        try:
            temporary.write_bytes(content)
            temporary.replace(path)
        finally:
            temporary.unlink(missing_ok=True)
    # Invalid JSON is still preserved for source diagnosis.
    return sha, path, json.loads(content)


def acquire(
    root: Path, specs: list[dict], start: date, end: date, inputs: Path | None = None
) -> list[dict]:
    batch = []
    for spec in specs:
        url = source_url(spec, start, end)
        content = (inputs / f"{spec['code']}.json").read_bytes() if inputs else fetch(url)
        sha, path, payload = bronze(root, spec, content)
        batch.append(
            {
                "spec": spec,
                "sha": sha,
                "path": str(path.relative_to(root)),
                "url": url,
                "payload": payload,
            }
        )
        if inputs is None:
            time.sleep(0.25)
    return batch
