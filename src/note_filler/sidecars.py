"""Paths for note-owned audit sidecars and legacy directory-level copies."""

from __future__ import annotations

import json
from pathlib import Path


DELIVERY_MANIFEST_NAME = "delivery_manifest.json"
BINDING_REPORT_NAME = "binding_report.json"


def delivery_manifest_path(output_path: Path) -> Path:
    output_path = Path(output_path)
    return output_path.with_name(f"{output_path.name}.{DELIVERY_MANIFEST_NAME}")


def binding_report_path(output_path: Path) -> Path:
    output_path = Path(output_path)
    return output_path.with_name(f"{output_path.name}.{BINDING_REPORT_NAME}")


def resolve_delivery_manifest_path(output_path: Path) -> Path:
    """Prefer the note-owned receipt; accept an older directory-level receipt."""
    owned = delivery_manifest_path(output_path)
    return owned if owned.is_file() else Path(output_path).parent / DELIVERY_MANIFEST_NAME


def resolve_binding_report_path(output_path: Path) -> Path:
    """Prefer the note-owned report; accept an older directory-level report."""
    owned = binding_report_path(output_path)
    return owned if owned.is_file() else Path(output_path).parent / BINDING_REPORT_NAME


def resolve_manifest_for_update(manifest_path: Path) -> Path:
    """Route a legacy latest-only path to its authoritative note receipt."""
    manifest_path = Path(manifest_path)
    if manifest_path.name != DELIVERY_MANIFEST_NAME or not manifest_path.is_file():
        return manifest_path
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        output = data.get("output_path")
    except (OSError, ValueError, AttributeError):
        return manifest_path
    if not isinstance(output, str) or not output:
        return manifest_path
    owned = delivery_manifest_path(manifest_path.parent / Path(output).name)
    if not owned.is_file():
        return manifest_path
    try:
        authoritative = json.loads(owned.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return manifest_path
    if (
        isinstance(authoritative, dict)
        and authoritative.get("output_path") == output
        and authoritative.get("input_path") == data.get("input_path")
    ):
        return owned
    return manifest_path


def write_manifest_and_latest(manifest_path: Path, data: dict) -> None:
    """Write the authoritative receipt and refresh its matching latest copy."""
    manifest_path = Path(manifest_path)
    authoritative = manifest_path.name != DELIVERY_MANIFEST_NAME
    data = dict(data)
    if authoritative:
        data.update({"authoritative": True, "sidecar_scope": "output"})
        data.pop("sidecar_for_output", None)
    else:
        data.update(
            {
                "authoritative": False,
                "sidecar_scope": "directory_latest",
            }
        )
        if data.get("output_path"):
            data["sidecar_for_output"] = data["output_path"]
    content = json.dumps(data, ensure_ascii=False, indent=2)
    manifest_path.write_text(content, encoding="utf-8", newline="\n")
    if not authoritative:
        return
    legacy = manifest_path.parent / DELIVERY_MANIFEST_NAME
    try:
        latest = json.loads(legacy.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return
    if isinstance(latest, dict) and latest.get("output_path") == data.get("output_path"):
        legacy_data = dict(data)
        legacy_data.update(
            {
                "authoritative": False,
                "sidecar_scope": "directory_latest",
                "sidecar_for_output": data.get("output_path"),
            }
        )
        legacy.write_text(
            json.dumps(legacy_data, ensure_ascii=False, indent=2),
            encoding="utf-8",
            newline="\n",
        )
