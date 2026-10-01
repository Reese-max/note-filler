"""Paths and identity rules for note-owned audit sidecars.

Authoritative evidence for a corrected note is filed under that note's output
name (``<output>.delivery_manifest.json`` / ``<output>.binding_report.json``).
The historical directory-level names remain as a clearly non-authoritative
"latest output" convenience copy.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

DELIVERY_MANIFEST_NAME = "delivery_manifest.json"
BINDING_REPORT_NAME = "binding_report.json"


def delivery_manifest_path(output_path: Path) -> Path:
    output_path = Path(output_path)
    return output_path.with_name(f"{output_path.name}.{DELIVERY_MANIFEST_NAME}")


def binding_report_path(output_path: Path) -> Path:
    output_path = Path(output_path)
    return output_path.with_name(f"{output_path.name}.{BINDING_REPORT_NAME}")


def is_receipt_file_name(name: str) -> bool:
    """Only real receipt names count; ``mydelivery_manifest.json`` does not."""
    return name == DELIVERY_MANIFEST_NAME or name.endswith(f".{DELIVERY_MANIFEST_NAME}")


def same_recorded_path(left: str | None, right: str | None) -> bool:
    """Compare two recorded identities, tolerating legacy relative paths.

    Two absolute identities compare as resolved paths. Two relative identities
    were recorded from some working directory this code cannot know, so they
    match only when they are identical strings, and never match an absolute
    identity: an unprovable match must keep existing evidence rather than
    replace it.
    """
    if not left or not right:
        return False
    left_path = Path(left)
    right_path = Path(right)
    if left_path.is_absolute() != right_path.is_absolute():
        return False
    if left_path.is_absolute():
        try:
            return left_path.resolve() == right_path.resolve()
        except OSError:
            return False
    return left == right


def migrate_legacy_sidecars(dest_dir: Path) -> list[Path]:
    """Promote a pre-upgrade directory-level pair to the note's own paths.

    A legacy output whose only evidence is the shared pair keeps it once a
    later note writes the next pair into the same directory.
    """
    dest_dir = Path(dest_dir)
    migrated: list[Path] = []
    legacy_receipt_path = dest_dir / DELIVERY_MANIFEST_NAME
    legacy_report_path = dest_dir / BINDING_REPORT_NAME
    try:
        legacy = json.loads(legacy_receipt_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return migrated
    if not isinstance(legacy, dict):
        return migrated
    output = receipt_output_identity(legacy)
    if not output:
        return migrated
    output_name = Path(output).name
    if output_name in ("", ".", "..") or "/" in output_name or "\\" in output_name:
        logger.warning("legacy_receipt_output_unusable path=%s output=%r", legacy_receipt_path, output)
        return migrated
    # A copy whose output no longer exists proves nothing: promoting it would
    # publish authoritative evidence for a note that is gone and would reserve
    # its output name forever.
    if not (dest_dir / output_name).exists():
        return migrated
    owned_receipt = delivery_manifest_path(dest_dir / output_name)
    if not owned_receipt.exists():
        receipt = dict(legacy)
        receipt.update({"authoritative": True, "sidecar_scope": "output"})
        receipt.pop("sidecar_for_output", None)
        owned_receipt.write_text(
            json.dumps(receipt, ensure_ascii=False, indent=2),
            encoding="utf-8",
            newline="\n",
        )
        migrated.append(owned_receipt)
    owned_report = binding_report_path(dest_dir / output_name)
    if not owned_report.exists() and legacy_report_path.is_file():
        owned_report.write_bytes(legacy_report_path.read_bytes())
        migrated.append(owned_report)
    return migrated


def output_path_for_receipt(manifest_path: Path) -> Path | None:
    """The output a note-owned receipt is filed under, or None for a legacy copy."""
    name = Path(manifest_path).name
    suffix = f".{DELIVERY_MANIFEST_NAME}"
    if not name.endswith(suffix):
        return None
    return Path(manifest_path).with_name(name[: -len(suffix)])


def resolve_delivery_manifest_path(output_path: Path) -> Path:
    """Prefer the note-owned receipt; accept an older directory-level receipt."""
    owned = delivery_manifest_path(output_path)
    return owned if owned.is_file() else Path(output_path).parent / DELIVERY_MANIFEST_NAME


def resolve_binding_report_path(output_path: Path, receipt: dict | None = None) -> Path:
    """Resolve the binding report for an output.

    The note-owned report wins. The directory-level copy is accepted only for a
    receipt written before per-note reports existed: a receipt that states its
    own report identity (``binding_report_content_hash`` present, empty when the
    note has none) must never borrow another note's report.
    """
    output_path = Path(output_path)
    owned = binding_report_path(output_path)
    if owned.is_file():
        return owned
    if receipt is not None and "binding_report_content_hash" in receipt:
        return owned
    return output_path.parent / BINDING_REPORT_NAME


def resolve_manifest_for_update(manifest_path: Path) -> Path:
    """Route a legacy latest-only path to its authoritative note receipt."""
    manifest_path = Path(manifest_path)
    if manifest_path.name != DELIVERY_MANIFEST_NAME or not manifest_path.is_file():
        return manifest_path
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, ValueError, AttributeError):
        return manifest_path
    if not isinstance(data, dict):
        return manifest_path
    output = receipt_output_identity(data)
    if output is None:
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
        and receipt_output_identity(authoritative) == output
        and receipt_input_identity(authoritative) == receipt_input_identity(data)
    ):
        return owned
    return manifest_path


def receipt_output_identity(manifest: dict) -> str | None:
    """Recorded output of a receipt, preferring the canonical identity."""
    for key in ("output_canonical_path", "output_path"):
        value = manifest.get(key)
        if isinstance(value, str) and value:
            return value
    return None


def receipt_input_identity(manifest: dict) -> str | None:
    """Recorded input of a receipt, preferring the canonical identity."""
    for key in ("input_canonical_path", "input_path"):
        value = manifest.get(key)
        if isinstance(value, str) and value:
            return value
    return None


def receipt_matches_output(manifest: dict, output_path: Path) -> bool:
    """Whether a receipt is the evidence filed under ``output_path``.

    A note-owned receipt is named after its output, so that filename is the
    binding: a receipt whose recorded output names a *different* note is never
    evidence for this output, while a note whose output directory was moved or
    archived keeps resolving to its own receipt. Content hashes and the
    receipt's own probes still verify the artifacts themselves.
    """
    output_path = Path(output_path)
    recorded = receipt_output_identity(manifest)
    return recorded is not None and Path(recorded).name == output_path.name


def receipt_conflicts_with_note(manifest: dict, manifest_path: Path) -> bool:
    """Whether a receipt speaks for an output other than the note it is filed under."""
    manifest_path = Path(manifest_path)
    recorded = receipt_output_identity(manifest)
    if recorded is None:
        return False
    owned_output = output_path_for_receipt(manifest_path)
    if owned_output is not None:
        return not receipt_matches_output(manifest, owned_output)
    # A directory-level copy carries no filename binding of its own; its
    # declared output may legitimately sit in an archived layout.
    return Path(recorded).name in ("", ".", "..")


def output_identity_key(manifest_path: Path, manifest: dict) -> str:
    """Deduplication key for the delivery a receipt records.

    Absolute identities compare as paths. A relative identity is only
    meaningful together with the receipt's own directory, so two receipts in
    different directories never collapse into a single note.
    """
    manifest_path = Path(manifest_path)
    recorded = receipt_output_identity(manifest)
    if recorded is None:
        return f"input:{receipt_input_identity(manifest) or manifest_path}"
    recorded_path = Path(recorded)
    if not recorded_path.is_absolute():
        recorded_path = manifest_path.parent / recorded_path.name
    try:
        return f"output:{recorded_path.resolve()}"
    except OSError:
        return f"output:{recorded_path.absolute()}"


def may_write_latest_copy(legacy_path: Path, receipt: dict) -> bool:
    """A failure receipt must not erase another note's latest delivery copy."""
    if receipt.get("status") == "delivered":
        return True
    try:
        latest = json.loads(Path(legacy_path).read_text(encoding="utf-8"))
    except FileNotFoundError:
        return True
    except (OSError, ValueError):
        logger.warning("latest_copy_unreadable path=%s action=preserved", legacy_path)
        return False
    if not isinstance(latest, dict):
        logger.warning("latest_copy_malformed path=%s action=preserved", legacy_path)
        return False
    return same_recorded_path(
        receipt_input_identity(latest), receipt_input_identity(receipt)
    )


def write_manifest_and_latest(manifest_path: Path, data: dict) -> None:
    """Write the authoritative receipt and refresh its matching latest copy.

    The latest copy is created when it is absent and refreshed only while it
    still names this output; a copy pointing at another note's delivery is left
    untouched so one note's update cannot repoint another note's evidence.
    """
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
    manifest_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
        newline="\n",
    )
    if not authoritative:
        return
    legacy = manifest_path.parent / DELIVERY_MANIFEST_NAME
    try:
        latest = json.loads(legacy.read_text(encoding="utf-8"))
    except FileNotFoundError:
        latest = None
    except (OSError, ValueError):
        logger.warning("latest_copy_unreadable path=%s action=preserved", legacy)
        return
    if latest is not None and not same_recorded_path(
        receipt_output_identity(latest), receipt_output_identity(data)
    ):
        return
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
