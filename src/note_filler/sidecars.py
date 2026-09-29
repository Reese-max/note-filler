"""Paths for note-owned audit sidecars and legacy directory-level copies."""

from __future__ import annotations

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
