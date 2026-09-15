#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

DISPLAY_NAME = "LUNAKO Harness"
PRODUCT_ID = "lunako-harness"
NAMESPACE_VERSION = 1
SUPPORTED_PRODUCT_NAMESPACES = frozenset({(PRODUCT_ID, NAMESPACE_VERSION)})

MANIFEST_SCHEMA_VERSION = 3
BUNDLE_SCHEMA_VERSION = 3
BUNDLE_VERSION = "3"
BUNDLE_NAME = "lunako-harness-runtime"

INSTALL_ROOT = ".lunako-harness"
MANIFEST_REL = ".lunako-harness/install-manifest.json"
BUNDLE_REL = "runtime/lunako-runtime-bundle.json"
SKILL_DIR = ".agents/skills/lunako-harness"
SKILL_REL = ".agents/skills/lunako-harness/SKILL.md"
CLI_REL = "scripts/lunako.py"
DOCTOR_REL = "scripts/lunako_doctor.py"
PERMISSION_HELPER_REL = "scripts/lunako_permission_profile.py"
DEFAULT_PERMISSION_PROFILE = "lunako-protected-write"

AGENTS_BEGIN = "<!-- LUNAKO-HARNESS:BEGIN -->"
AGENTS_END = "<!-- LUNAKO-HARNESS:END -->"
ROLE_BEGIN = "# LUNAKO-HARNESS:BEGIN PROJECT-ROLE-REGISTRATION"
ROLE_END = "# LUNAKO-HARNESS:END PROJECT-ROLE-REGISTRATION"
ROLE_TARGET = ".codex/config.toml"
REGION_ID = "codex-project-role-registration"
REGION_SOURCE_CONTRACT = "project_role_registration"

EXPECTED_REGISTRATIONS = (
    ("luna_planner", "agents/luna-planner.toml"),
    ("luna_decomposer", "agents/luna-decomposer.toml"),
    ("luna_worker", "agents/luna-worker.toml"),
    ("luna_verifier", "agents/luna-verifier.toml"),
    ("luna_integrator", "agents/luna-integrator.toml"),
    ("sol_architect", "agents/sol-architect.toml"),
    ("sol_reviewer", "agents/sol-reviewer.toml"),
    ("sol_decision_reviewer", "agents/sol-decision-reviewer.toml"),
)

class ContractError(RuntimeError):
    pass


def require_supported_tuple(product_id: Any, namespace_version: Any) -> tuple[str, int]:
    if not isinstance(product_id, str) or not isinstance(namespace_version, int):
        raise ContractError("product_id/namespace_version types are invalid")
    value = (product_id, namespace_version)
    if value not in SUPPORTED_PRODUCT_NAMESPACES:
        raise ContractError(f"unsupported product namespace tuple: {value!r}")
    return value


def read_json(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ContractError(f"invalid {label}: {exc}") from exc
    if not isinstance(value, dict):
        raise ContractError(f"{label} must be a JSON object")
    return value


def validate_bundle_identity(bundle: dict[str, Any]) -> None:
    if bundle.get("schema_version") != BUNDLE_SCHEMA_VERSION:
        raise ContractError("unsupported canonical runtime bundle schema")
    if bundle.get("bundle_name") != BUNDLE_NAME or str(bundle.get("bundle_version")) != BUNDLE_VERSION:
        raise ContractError("canonical runtime bundle identity/version mismatch")
    require_supported_tuple(bundle.get("product_id"), bundle.get("namespace_version"))


def read_runtime_bundle(source_root: Path) -> dict[str, Any]:
    bundle = read_json(source_root / BUNDLE_REL, "canonical runtime bundle")
    validate_bundle_identity(bundle)
    return bundle


def validate_manifest_identity(manifest: dict[str, Any], bundle: dict[str, Any] | None = None) -> None:
    if manifest.get("schema_version") != MANIFEST_SCHEMA_VERSION:
        raise ContractError("unsupported canonical install manifest schema")
    tuple_value = require_supported_tuple(manifest.get("product_id"), manifest.get("namespace_version"))
    if manifest.get("bundle_name") != BUNDLE_NAME:
        raise ContractError("canonical install manifest bundle identity mismatch")
    if bundle is not None:
        validate_bundle_identity(bundle)
        if tuple_value != (bundle.get("product_id"), bundle.get("namespace_version")):
            raise ContractError("manifest/runtime bundle product namespace disagreement")


def read_canonical_manifest(target: Path, bundle: dict[str, Any] | None = None) -> dict[str, Any]:
    path = target / MANIFEST_REL
    if not path.is_file():
        raise ContractError("canonical install manifest is missing")
    manifest = read_json(path, "canonical install manifest")
    validate_manifest_identity(manifest, bundle)
    if not isinstance(manifest.get("managed_files"), list):
        raise ContractError("canonical install manifest managed_files must be a list")
    if not isinstance(manifest.get("managed_regions"), list):
        raise ContractError("canonical install manifest managed_regions must be a list")
    return manifest
