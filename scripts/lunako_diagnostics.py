#!/usr/bin/env python3
"""Read-only N2 diagnostics for mixed, drifted, or unknown LUNAKO installation states."""
from __future__ import annotations

import json
from pathlib import Path, PurePosixPath
from typing import Any

from lunako_contract import AGENTS_BEGIN, AGENTS_END, MANIFEST_REL, ROLE_BEGIN, ROLE_END, ROLE_TARGET, SKILL_DIR
from lunako_legacy_frozen import match_frozen_legacy_manifest
from lunako_state import (
    CONFLICT, LEGACY_AGENTS_BEGIN, LEGACY_AGENTS_END, LEGACY_INSTALL_ROOT,
    LEGACY_MANAGED_TARGETS, LEGACY_MANIFEST_REL, LEGACY_ROLE_BEGIN,
    LEGACY_ROLE_END, LEGACY_SKILL_DIR, Detection, canonical_evidence,
    legacy_evidence, validate_canonical,
)


def _text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ""


def _marker_state(path: Path, begin: str, end: str) -> dict[str, bool]:
    body = _text(path)
    return {"begin": begin in body, "end": end in body}


def _read_json(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    if not path.is_file():
        return None, None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return None, str(exc)
    if not isinstance(value, dict):
        return None, "manifest is not a JSON object"
    return value, None


def _present_paths(target: Path, rels: set[str]) -> list[str]:
    present: list[str] = []
    for rel in sorted(rels):
        path = target / PurePosixPath(rel)
        if path.exists() or path.is_symlink():
            present.append(rel)
    return present


def conflict_diagnostics(target: Path, bundle: dict[str, Any], detection: Detection) -> dict[str, Any]:
    canonical_manifest, canonical_manifest_error = _read_json(target / MANIFEST_REL)
    legacy_manifest, legacy_manifest_error = _read_json(target / LEGACY_MANIFEST_REL)

    canonical_targets = {
        str(item.get("target"))
        for item in bundle.get("file_mappings", [])
        if isinstance(item, dict) and isinstance(item.get("target"), str)
    }
    tracked_paths = canonical_targets | set(LEGACY_MANAGED_TARGETS) | {
        MANIFEST_REL, LEGACY_MANIFEST_REL, SKILL_DIR, LEGACY_SKILL_DIR,
        ".lunako-harness", LEGACY_INSTALL_ROOT, "AGENTS.md", ROLE_TARGET,
    }

    canonical_problems: list[str] = []
    if canonical_manifest is not None:
        _, canonical_problems = validate_canonical(target, bundle)
    elif canonical_manifest_error:
        canonical_problems = ["canonical manifest unreadable: " + canonical_manifest_error]

    legacy_family: str | None = None
    legacy_frozen_problems: list[str] = []
    if legacy_manifest is not None:
        legacy_family, legacy_frozen_problems = match_frozen_legacy_manifest(legacy_manifest)
    elif legacy_manifest_error:
        legacy_frozen_problems = ["legacy manifest unreadable: " + legacy_manifest_error]

    result = {
        "state": detection.state,
        "subtype": detection.subtype,
        "problems": list(detection.problems),
        "canonical_evidence_found": canonical_evidence(target),
        "legacy_evidence_found": legacy_evidence(target),
        "manifests": {
            "canonical": {"path": MANIFEST_REL, "exists": (target / MANIFEST_REL).is_file(), "read_error": canonical_manifest_error},
            "legacy": {"path": LEGACY_MANIFEST_REL, "exists": (target / LEGACY_MANIFEST_REL).is_file(), "read_error": legacy_manifest_error},
        },
        "markers": {
            "canonical_agents": _marker_state(target / "AGENTS.md", AGENTS_BEGIN, AGENTS_END),
            "legacy_agents": _marker_state(target / "AGENTS.md", LEGACY_AGENTS_BEGIN, LEGACY_AGENTS_END),
            "canonical_role": _marker_state(target / ROLE_TARGET, ROLE_BEGIN, ROLE_END),
            "legacy_role": _marker_state(target / ROLE_TARGET, LEGACY_ROLE_BEGIN, LEGACY_ROLE_END),
        },
        "managed_paths_present": _present_paths(target, tracked_paths),
        "canonical_validation": {"match": canonical_manifest is not None and not canonical_problems, "problems": canonical_problems},
        "legacy_frozen_validation": {"family": legacy_family, "match": legacy_family is not None and not legacy_frozen_problems, "problems": legacy_frozen_problems},
        "ownership_unknown": detection.state == CONFLICT,
        "recovery_guidance": [
            "Do not delete, rewrite, or infer ownership while the installation is CONFLICT.",
            "Restore the project to one coherent known state using version control, backup, or known frozen installation evidence.",
            "Then rerun lunako status and lunako doctor before any mutating lifecycle command.",
        ],
    }
    return result
