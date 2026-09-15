#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

try:
    import tomllib
except ModuleNotFoundError:
    tomllib = None  # type: ignore[assignment]

from lunako_contract import (
    AGENTS_BEGIN, AGENTS_END, BUNDLE_NAME, MANIFEST_REL, PRODUCT_ID,
    NAMESPACE_VERSION, REGION_ID, REGION_SOURCE_CONTRACT, ROLE_BEGIN, ROLE_END,
    ROLE_TARGET, SKILL_DIR, EXPECTED_REGISTRATIONS, ContractError,
    read_canonical_manifest, require_supported_tuple,
)
from lunako_legacy_frozen import diagnostic_subtype, match_frozen_legacy_manifest

NONE = "NONE"
CANONICAL = "CANONICAL"
SUPPORTED_LEGACY = "SUPPORTED_LEGACY"
CONFLICT = "CONFLICT"

LEGACY_MANIFEST_REL = ".lunatic-harnes/install-manifest.json"
LEGACY_INSTALL_ROOT = ".lunatic-harnes"
LEGACY_AGENTS_BEGIN = "<!-- LUNATIC-HARNES:BEGIN -->"
LEGACY_AGENTS_END = "<!-- LUNATIC-HARNES:END -->"
LEGACY_ROLE_BEGIN = "# LUNATIC-HARNES:BEGIN PROJECT-ROLE-REGISTRATION"
LEGACY_ROLE_END = "# LUNATIC-HARNES:END PROJECT-ROLE-REGISTRATION"
LEGACY_SKILL_DIR = ".agents/skills/luna-harness"
LEGACY_BUNDLE_NAME = "lunatic-harnes-runtime"

LEGACY_MANAGED_TARGETS = frozenset({
    ".agents/project-interface/SPECIFICATION.md",
    ".agents/schemas/agent-result.schema.json",
    ".agents/schemas/architecture-gates.schema.json",
    ".agents/schemas/consistency-gate.schema.json",
    ".agents/schemas/context-capsule.schema.json",
    ".agents/schemas/contract-impact.schema.json",
    ".agents/schemas/dependency-graph.schema.json",
    ".agents/schemas/domain-map.schema.json",
    ".agents/schemas/external-audit.schema.json",
    ".agents/schemas/impact-manifest.schema.json",
    ".agents/schemas/integration-waves.schema.json",
    ".agents/schemas/packet-states.schema.json",
    ".agents/schemas/quality-evidence.schema.json",
    ".agents/schemas/routing-decision.schema.json",
    ".agents/schemas/run-record.schema.json",
    ".agents/schemas/strict-agent-result.schema.json",
    ".agents/schemas/strict-run-record.schema.json",
    ".agents/schemas/worktrees.schema.json",
    ".agents/skills/design-feedback/SKILL.md",
    ".agents/skills/design-feedback/agents/openai.yaml",
    ".agents/skills/external-audit/SKILL.md",
    ".agents/skills/integration/SKILL.md",
    ".agents/skills/integration/agents/openai.yaml",
    ".agents/skills/low-token-mode/SKILL.md",
    ".agents/skills/low-token-mode/agents/openai.yaml",
    ".agents/skills/luna-harness/SKILL.md",
    ".agents/skills/luna-harness/agents/openai.yaml",
    ".agents/skills/luna-harness/references/runtime-contracts.md",
    ".agents/skills/model-escalation/SKILL.md",
    ".agents/skills/model-escalation/agents/openai.yaml",
    ".agents/skills/task-decomposition/SKILL.md",
    ".agents/skills/task-decomposition/agents/openai.yaml",
    ".agents/skills/verification/SKILL.md",
    ".agents/skills/verification/agents/openai.yaml",
    ".agents/skills/work-packet/SKILL.md",
    ".agents/skills/work-packet/agents/openai.yaml",
    ".codex/agents/luna-decomposer.toml",
    ".codex/agents/luna-integrator.toml",
    ".codex/agents/luna-planner.toml",
    ".codex/agents/luna-verifier.toml",
    ".codex/agents/luna-worker.toml",
    ".codex/agents/sol-architect.toml",
    ".codex/agents/sol-decision-reviewer.toml",
    ".codex/agents/sol-reviewer.toml",
    "scripts/check_assurance_done_gate.py",
    "scripts/check_impact_closure.py",
    "scripts/lunatic_permission_profile.py",
    "scripts/project_interface_reconciliation.py",
    "scripts/project_interface_resolver.py",
})

@dataclass(frozen=True)
class Detection:
    state: str
    subtype: str
    problems: tuple[str, ...]
    manifest: dict[str, Any] | None = None


def sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha_file(path: Path) -> str:
    return sha_bytes(path.read_bytes())


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ""


def _marker_present(path: Path, begin: str, end: str) -> bool:
    if not path.is_file():
        return False
    text = _read_text(path)
    return begin in text or end in text


def canonical_evidence(target: Path) -> list[str]:
    found: list[str] = []
    for rel in (MANIFEST_REL, SKILL_DIR):
        if (target / rel).exists() or (target / rel).is_symlink():
            found.append(rel)
    if (target / ".lunako-harness").exists() and MANIFEST_REL not in found:
        found.append(".lunako-harness/")
    if _marker_present(target / "AGENTS.md", AGENTS_BEGIN, AGENTS_END):
        found.append("canonical AGENTS marker")
    if _marker_present(target / ROLE_TARGET, ROLE_BEGIN, ROLE_END):
        found.append("canonical role marker")
    return found


def legacy_evidence(target: Path) -> list[str]:
    found: list[str] = []
    for rel in (LEGACY_MANIFEST_REL, LEGACY_SKILL_DIR):
        if (target / rel).exists() or (target / rel).is_symlink():
            found.append(rel)
    if (target / LEGACY_INSTALL_ROOT).exists() and LEGACY_MANIFEST_REL not in found:
        found.append(LEGACY_INSTALL_ROOT + "/")
    if _marker_present(target / "AGENTS.md", LEGACY_AGENTS_BEGIN, LEGACY_AGENTS_END):
        found.append("legacy AGENTS marker")
    if _marker_present(target / ROLE_TARGET, LEGACY_ROLE_BEGIN, LEGACY_ROLE_END):
        found.append("legacy role marker")
    return found


def _file_record_map(manifest: dict[str, Any]) -> tuple[dict[str, dict[str, Any]], list[str]]:
    out: dict[str, dict[str, Any]] = {}
    problems: list[str] = []
    items = manifest.get("managed_files")
    if not isinstance(items, list):
        return {}, ["managed_files missing or not a list"]
    for item in items:
        if not isinstance(item, dict):
            problems.append("invalid managed_files record")
            continue
        rel = item.get("target_path")
        if not isinstance(rel, str) or not rel:
            problems.append("managed file target_path invalid")
            continue
        p = PurePosixPath(rel)
        if p.is_absolute() or ".." in p.parts:
            problems.append(f"unsafe managed target: {rel}")
            continue
        if rel in out:
            problems.append(f"duplicate managed target: {rel}")
            continue
        out[rel] = item
    return out, problems


def _managed_file_problems(target: Path, manifest: dict[str, Any], expected_targets: set[str] | frozenset[str] | None = None) -> list[str]:
    records, problems = _file_record_map(manifest)
    if expected_targets is not None and set(records) != set(expected_targets):
        missing = sorted(set(expected_targets) - set(records))
        extra = sorted(set(records) - set(expected_targets))
        if missing:
            problems.append("managed target set missing: " + ",".join(missing))
        if extra:
            problems.append("managed target set extra: " + ",".join(extra))
    for rel, record in records.items():
        path = target / PurePosixPath(rel)
        expected = record.get("installed_sha256")
        if not isinstance(expected, str) or len(expected) != 64:
            problems.append(f"{rel}: invalid installed_sha256")
        elif not path.is_file():
            problems.append(f"{rel}: missing")
        elif sha_file(path) != expected:
            problems.append(f"{rel}: modified")
    return problems


def _find_exact_block(text: str, begin: str, end: str) -> tuple[int, int] | None:
    starts: list[int] = []
    pos = 0
    while True:
        idx = text.find(begin, pos)
        if idx < 0:
            break
        starts.append(idx)
        pos = idx + len(begin)
    ends: list[int] = []
    pos = 0
    while True:
        idx = text.find(end, pos)
        if idx < 0:
            break
        ends.append(idx)
        pos = idx + len(end)
    if not starts and not ends:
        return None
    if len(starts) != 1 or len(ends) != 1 or ends[0] < starts[0]:
        raise ValueError("malformed or duplicate managed markers")
    return starts[0], ends[0] + len(end)


def _agents_problems(target: Path, manifest: dict[str, Any], begin: str, end: str) -> list[str]:
    path = target / "AGENTS.md"
    if not path.is_file():
        return ["AGENTS.md missing"]
    try:
        text = path.read_text(encoding="utf-8")
        span = _find_exact_block(text, begin, end)
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        return [f"AGENTS.md invalid: {exc}"]
    if span is None:
        return ["AGENTS.md managed block missing"]
    block = text[span[0]:span[1]].encode()
    problems: list[str] = []
    if sha_bytes(block) != manifest.get("managed_agents_block_sha256"):
        problems.append("AGENTS.md managed block modified")
    prefix = manifest.get("agents_binding_prefix", "")
    suffix = manifest.get("agents_binding_suffix", "")
    if not isinstance(prefix, str) or not isinstance(suffix, str):
        return problems + ["AGENTS binding affix metadata invalid"]
    start, end_i = span
    if prefix:
        if start < len(prefix) or text[start-len(prefix):start] != prefix:
            problems.append("AGENTS binding prefix modified")
            start = span[0]
        else:
            start -= len(prefix)
    if suffix:
        if text[end_i:end_i+len(suffix)] != suffix:
            problems.append("AGENTS binding suffix modified")
        else:
            end_i += len(suffix)
    if sha_bytes(text[start:end_i].encode()) != manifest.get("managed_agents_segment_sha256"):
        problems.append("AGENTS managed segment modified")
    return problems


def _marker_line_offsets(text: str, marker: str) -> list[tuple[int, int]]:
    result: list[tuple[int, int]] = []
    offset = 0
    for line in text.splitlines(keepends=True):
        body = line.rstrip("\r\n")
        if body.strip() == marker:
            col = body.find(marker)
            result.append((offset + col, offset + col + len(marker)))
        offset += len(line)
    return result


def _find_region(text: str, begin: str, end: str) -> tuple[int, int] | None:
    starts = _marker_line_offsets(text, begin)
    ends = _marker_line_offsets(text, end)
    if not starts and not ends:
        return None
    if len(starts) != 1 or len(ends) != 1 or ends[0][0] < starts[0][0]:
        raise ValueError("malformed or duplicate role-registration markers")
    return starts[0][0], ends[0][1]


def _tail_comments_or_ws(text: str) -> bool:
    return all(not line.strip() or line.strip().startswith("#") for line in text.splitlines())


def _normalize_snapshot(value: Any) -> list[dict[str, str]]:
    if not isinstance(value, list):
        raise ValueError("installed_registrations missing")
    out: list[dict[str, str]] = []
    for item in value:
        if not isinstance(item, dict) or set(item) != {"role", "config_file"}:
            raise ValueError("invalid installed registration entry")
        role = item.get("role")
        config = item.get("config_file")
        if not isinstance(role, str) or not isinstance(config, str):
            raise ValueError("invalid installed registration values")
        out.append({"role": role, "config_file": config})
    expected = [{"role": r, "config_file": c} for r, c in EXPECTED_REGISTRATIONS]
    if out != expected:
        raise ValueError("installed registration snapshot mismatch")
    return out


def _region_problems(target: Path, manifest: dict[str, Any], begin: str, end: str) -> list[str]:
    regions = manifest.get("managed_regions")
    if not isinstance(regions, list):
        return ["managed_regions missing"]
    records = [r for r in regions if isinstance(r, dict) and r.get("region_id") == REGION_ID]
    if len(records) != 1:
        return ["exactly one role-registration managed region required"]
    record = records[0]
    problems: list[str] = []
    if record.get("target_path") != ROLE_TARGET:
        problems.append("role-registration target mismatch")
    if record.get("ownership") != "managed-terminal-region" or record.get("placement") != "terminal":
        problems.append("role-registration ownership mismatch")
    if record.get("begin_marker") != begin or record.get("end_marker") != end:
        problems.append("role-registration marker mismatch")
    if record.get("source_contract") != REGION_SOURCE_CONTRACT:
        problems.append("role-registration source_contract mismatch")
    try:
        snapshot = _normalize_snapshot(record.get("installed_registrations"))
    except ValueError as exc:
        problems.append(str(exc))
        snapshot = []

    path = target / ROLE_TARGET
    if not path.is_file():
        return problems + [".codex/config.toml missing"]
    try:
        text = path.read_text(encoding="utf-8")
        span = _find_region(text, begin, end)
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        return problems + [f".codex/config.toml invalid: {exc}"]
    if span is None:
        return problems + ["managed role-registration region missing"]
    rs, re = span
    prefix = record.get("segment_prefix", "")
    suffix = record.get("segment_suffix", "")
    if not isinstance(prefix, str) or not isinstance(suffix, str):
        return problems + ["role-registration affix metadata invalid"]
    ss, se = rs, re
    if prefix:
        if rs < len(prefix) or text[rs-len(prefix):rs] != prefix:
            problems.append("role-registration prefix modified")
        else:
            ss -= len(prefix)
    if suffix:
        if text[re:re+len(suffix)] != suffix:
            problems.append("role-registration suffix modified")
        else:
            se += len(suffix)
    region_text = text[rs:re]
    if sha_bytes(region_text.encode()) != record.get("managed_region_sha256"):
        problems.append("role-registration region modified")
    if sha_bytes(text[ss:se].encode()) != record.get("managed_segment_sha256"):
        problems.append("role-registration segment modified")
    if not _tail_comments_or_ws(text[se:]):
        problems.append("non-comment TOML after terminal managed region")
    if tomllib is None:
        problems.append("tomllib unavailable")
    else:
        try:
            parsed = tomllib.loads(text)
        except (tomllib.TOMLDecodeError, ValueError) as exc:
            problems.append(f".codex/config.toml invalid TOML: {exc}")
        else:
            agents = parsed.get("agents")
            if not isinstance(agents, dict):
                problems.append("agents table missing")
            else:
                for item in snapshot:
                    role_value = agents.get(item["role"])
                    if not isinstance(role_value, dict) or role_value.get("config_file") != item["config_file"]:
                        problems.append(f"registration mismatch: {item['role']}")
    return problems


def validate_canonical(target: Path, bundle: dict[str, Any]) -> tuple[dict[str, Any] | None, list[str]]:
    try:
        manifest = read_canonical_manifest(target, bundle)
        require_supported_tuple(manifest.get("product_id"), manifest.get("namespace_version"))
    except ContractError as exc:
        return None, [str(exc)]
    expected_targets = {
        str(item.get("target"))
        for item in bundle.get("file_mappings", [])
        if isinstance(item, dict) and isinstance(item.get("target"), str)
    }
    problems = _managed_file_problems(target, manifest, expected_targets)
    problems.extend(_agents_problems(target, manifest, AGENTS_BEGIN, AGENTS_END))
    problems.extend(_region_problems(target, manifest, ROLE_BEGIN, ROLE_END))
    if not (target / SKILL_DIR).is_dir():
        problems.append("canonical skill directory missing")
    return manifest, problems


def _read_legacy_manifest(target: Path) -> tuple[dict[str, Any] | None, list[str]]:
    path = target / LEGACY_MANIFEST_REL
    if not path.is_file():
        return None, ["legacy manifest missing"]
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return None, [f"invalid legacy manifest: {exc}"]
    if not isinstance(value, dict):
        return None, ["legacy manifest must be object"]
    return value, []


def validate_legacy(target: Path) -> tuple[dict[str, Any] | None, str, list[str]]:
    manifest, problems = _read_legacy_manifest(target)
    if manifest is None:
        return None, "UNKNOWN_LEGACY", problems

    family, frozen_problems = match_frozen_legacy_manifest(manifest)
    problems.extend(frozen_problems)
    schema = manifest.get("schema_version")
    if schema not in {1, 2}:
        return manifest, "UNKNOWN_LEGACY", problems

    # Frozen payload/ownership matching and filesystem self-consistency are
    # independent requirements. Neither is sufficient by itself.
    problems.extend(_managed_file_problems(target, manifest, LEGACY_MANAGED_TARGETS))
    problems.extend(_agents_problems(target, manifest, LEGACY_AGENTS_BEGIN, LEGACY_AGENTS_END))
    if not (target / LEGACY_SKILL_DIR).is_dir():
        problems.append("legacy skill directory missing")

    if schema == 1:
        if manifest.get("managed_regions") not in (None, []):
            problems.append("legacy v1 unexpectedly owns managed_regions")
        if _marker_present(target / ROLE_TARGET, LEGACY_ROLE_BEGIN, LEGACY_ROLE_END):
            problems.append("legacy v1 has unowned project role-registration marker")
    else:
        problems.extend(_region_problems(target, manifest, LEGACY_ROLE_BEGIN, LEGACY_ROLE_END))

    subtype = diagnostic_subtype(family, manifest) if family is not None else "UNKNOWN_LEGACY"
    return manifest, subtype, problems


def detect_state(target: Path, bundle: dict[str, Any]) -> Detection:
    canonical = canonical_evidence(target)
    legacy = legacy_evidence(target)
    canonical_manifest = (target / MANIFEST_REL).is_file()
    legacy_manifest = (target / LEGACY_MANIFEST_REL).is_file()

    if canonical_manifest and legacy_manifest:
        return Detection(CONFLICT, "MIXED_MANIFESTS", tuple(canonical + legacy))

    if canonical_manifest:
        legacy_nonshared = [x for x in legacy if x != LEGACY_MANIFEST_REL]
        if legacy_nonshared:
            return Detection(CONFLICT, "MIXED_CANONICAL_LEGACY", tuple(legacy_nonshared))
        manifest, problems = validate_canonical(target, bundle)
        if problems:
            return Detection(CONFLICT, "CANONICAL_INVALID", tuple(problems), manifest)
        return Detection(CANONICAL, "CANONICAL_V1", (), manifest)

    if legacy_manifest:
        canonical_nonmanifest = [x for x in canonical if x != MANIFEST_REL]
        if canonical_nonmanifest:
            return Detection(CONFLICT, "MIXED_LEGACY_CANONICAL", tuple(canonical_nonmanifest))
        manifest, subtype, problems = validate_legacy(target)
        if problems:
            return Detection(CONFLICT, "LEGACY_INVALID", tuple(problems), manifest)
        return Detection(SUPPORTED_LEGACY, subtype, (), manifest)

    residue = canonical + legacy
    if residue:
        return Detection(CONFLICT, "ORPHAN_OR_MIXED_EVIDENCE", tuple(residue))
    return Detection(NONE, "NO_INSTALLATION_EVIDENCE", ())
