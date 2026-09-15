#!/usr/bin/env python3
"""Build fail-closed Codex permission-profile overrides for clean canonical LUNAKO installs."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path, PurePosixPath
from typing import Any

try:
    import tomllib
except ModuleNotFoundError:
    tomllib = None  # type: ignore[assignment]

from lunako_contract import (
    AGENTS_BEGIN, AGENTS_END, DEFAULT_PERMISSION_PROFILE, EXPECTED_REGISTRATIONS,
    INSTALL_ROOT, REGION_ID, REGION_SOURCE_CONTRACT, ROLE_BEGIN, ROLE_END,
    ROLE_TARGET, SKILL_DIR, ContractError, read_canonical_manifest,
)

PROFILE_NAME_RE = re.compile(r"^[A-Za-z0-9_-]+$")
RESERVED_HARNESS_PATHS = (
    PurePosixPath(SKILL_DIR),
    PurePosixPath(".agents/work-packets"),
    PurePosixPath(".agents/project-interface"),
    PurePosixPath(".agents/schemas"),
)
EXPECTED_MANAGED_TARGETS = frozenset({
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
    ".agents/skills/lunako-harness/SKILL.md",
    ".agents/skills/lunako-harness/agents/openai.yaml",
    ".agents/skills/lunako-harness/references/runtime-contracts.md",
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
    "scripts/lunako_contract.py",
    "scripts/lunako_permission_profile.py",
    "scripts/project_interface_reconciliation.py",
    "scripts/project_interface_resolver.py",
})

class PermissionProfileError(RuntimeError):
    pass


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git_root(path: Path) -> Path:
    target = path.expanduser().resolve()
    proc = subprocess.run(["git", "-C", str(target), "rev-parse", "--show-toplevel"], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    if proc.returncode != 0:
        raise PermissionProfileError("target must be inside a Git repository")
    root = Path(proc.stdout.strip()).resolve()
    if root != target:
        raise PermissionProfileError(f"target must be the Git repository root: {root}")
    return root


def normalize_rel(value: str) -> PurePosixPath:
    if not value or any(ch in value for ch in ("\\", "\x00", "\n", "\r")):
        raise PermissionProfileError(f"unsafe write scope: {value!r}")
    path = PurePosixPath(value)
    if path.is_absolute() or not path.parts or path == PurePosixPath(".") or ".." in path.parts:
        raise PermissionProfileError(f"unsafe write scope: {value}")
    if path.parts[0] != ".agents" or len(path.parts) < 2:
        raise PermissionProfileError("protected write scopes must be an explicit project-owned subtree under .agents/")
    return path


def _safe_managed_path(target: Path, rel: str) -> Path:
    path = PurePosixPath(rel)
    if path.is_absolute() or not path.parts or ".." in path.parts:
        raise PermissionProfileError(f"unsafe managed target path in manifest: {rel}")
    current = target
    for index, part in enumerate(path.parts):
        current = current / part
        if current.is_symlink():
            raise PermissionProfileError(f"managed ownership traverses symlink: {rel}")
        if index < len(path.parts) - 1 and current.exists() and not current.is_dir():
            raise PermissionProfileError(f"managed ownership traverses non-directory: {rel}")
    return current


def _single_span(text: str, begin: str, end: str, label: str) -> tuple[int, int]:
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
    if len(starts) != 1 or len(ends) != 1 or ends[0] < starts[0]:
        raise PermissionProfileError(f"{label} managed markers missing, malformed, or duplicated")
    return starts[0], ends[0] + len(end)


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


def _single_region(text: str) -> tuple[int, int]:
    starts = _marker_line_offsets(text, ROLE_BEGIN)
    ends = _marker_line_offsets(text, ROLE_END)
    if len(starts) != 1 or len(ends) != 1 or ends[0][0] < starts[0][0]:
        raise PermissionProfileError("canonical role-registration markers missing, malformed, or duplicated")
    return starts[0][0], ends[0][1]


def _clean_canonical_ownership(target: Path, manifest: dict[str, Any]) -> list[PurePosixPath]:
    records: dict[str, dict[str, Any]] = {}
    items = manifest.get("managed_files")
    if not isinstance(items, list):
        raise PermissionProfileError("clean CANONICAL ownership required: managed_files missing")
    for item in items:
        if not isinstance(item, dict):
            raise PermissionProfileError("clean CANONICAL ownership required: invalid managed file record")
        rel = item.get("target_path")
        expected = item.get("installed_sha256")
        if not isinstance(rel, str) or not rel or rel in records:
            raise PermissionProfileError("clean CANONICAL ownership required: invalid/duplicate managed target")
        if not isinstance(expected, str) or len(expected) != 64:
            raise PermissionProfileError(f"clean CANONICAL ownership required: invalid hash for {rel}")
        records[rel] = item
    if set(records) != set(EXPECTED_MANAGED_TARGETS):
        raise PermissionProfileError("clean CANONICAL ownership required: managed target set differs from canonical contract")
    managed: list[PurePosixPath] = []
    for rel, item in records.items():
        path = _safe_managed_path(target, rel)
        if not path.is_file():
            raise PermissionProfileError(f"clean CANONICAL ownership required: managed file missing: {rel}")
        if _sha(path.read_bytes()) != item.get("installed_sha256"):
            raise PermissionProfileError(f"clean CANONICAL ownership required: managed file modified: {rel}")
        managed.append(PurePosixPath(rel))

    agents = _safe_managed_path(target, "AGENTS.md")
    if not agents.is_file():
        raise PermissionProfileError("clean CANONICAL ownership required: AGENTS.md missing")
    text = agents.read_text(encoding="utf-8")
    start, end = _single_span(text, AGENTS_BEGIN, AGENTS_END, "AGENTS.md")
    if _sha(text[start:end].encode()) != manifest.get("managed_agents_block_sha256"):
        raise PermissionProfileError("clean CANONICAL ownership required: AGENTS managed block modified")
    prefix = manifest.get("agents_binding_prefix", "")
    suffix = manifest.get("agents_binding_suffix", "")
    if not isinstance(prefix, str) or not isinstance(suffix, str):
        raise PermissionProfileError("clean CANONICAL ownership required: AGENTS affix metadata invalid")
    ss, se = start, end
    if prefix:
        if start < len(prefix) or text[start-len(prefix):start] != prefix:
            raise PermissionProfileError("clean CANONICAL ownership required: AGENTS prefix modified")
        ss -= len(prefix)
    if suffix:
        if text[end:end+len(suffix)] != suffix:
            raise PermissionProfileError("clean CANONICAL ownership required: AGENTS suffix modified")
        se += len(suffix)
    if _sha(text[ss:se].encode()) != manifest.get("managed_agents_segment_sha256"):
        raise PermissionProfileError("clean CANONICAL ownership required: AGENTS segment modified")

    regions = manifest.get("managed_regions")
    if not isinstance(regions, list):
        raise PermissionProfileError("clean CANONICAL ownership required: managed_regions missing")
    matches = [r for r in regions if isinstance(r, dict) and r.get("region_id") == REGION_ID]
    if len(matches) != 1:
        raise PermissionProfileError("clean CANONICAL ownership required: exact role-registration region missing")
    record = matches[0]
    if record.get("target_path") != ROLE_TARGET or record.get("ownership") != "managed-terminal-region" or record.get("placement") != "terminal":
        raise PermissionProfileError("clean CANONICAL ownership required: role-registration ownership mismatch")
    if record.get("begin_marker") != ROLE_BEGIN or record.get("end_marker") != ROLE_END or record.get("source_contract") != REGION_SOURCE_CONTRACT:
        raise PermissionProfileError("clean CANONICAL ownership required: role-registration contract mismatch")
    expected_regs = [{"role": role, "config_file": config} for role, config in EXPECTED_REGISTRATIONS]
    if record.get("installed_registrations") != expected_regs:
        raise PermissionProfileError("clean CANONICAL ownership required: registration snapshot mismatch")

    config = _safe_managed_path(target, ROLE_TARGET)
    if not config.is_file():
        raise PermissionProfileError("clean CANONICAL ownership required: .codex/config.toml missing")
    config_text = config.read_text(encoding="utf-8")
    rs, re = _single_region(config_text)
    rprefix = record.get("segment_prefix", "")
    rsuffix = record.get("segment_suffix", "")
    if not isinstance(rprefix, str) or not isinstance(rsuffix, str):
        raise PermissionProfileError("clean CANONICAL ownership required: role-registration affix metadata invalid")
    ss2, se2 = rs, re
    if rprefix:
        if rs < len(rprefix) or config_text[rs-len(rprefix):rs] != rprefix:
            raise PermissionProfileError("clean CANONICAL ownership required: role-registration prefix modified")
        ss2 -= len(rprefix)
    if rsuffix:
        if config_text[re:re+len(rsuffix)] != rsuffix:
            raise PermissionProfileError("clean CANONICAL ownership required: role-registration suffix modified")
        se2 += len(rsuffix)
    if _sha(config_text[rs:re].encode()) != record.get("managed_region_sha256"):
        raise PermissionProfileError("clean CANONICAL ownership required: role-registration region modified")
    if _sha(config_text[ss2:se2].encode()) != record.get("managed_segment_sha256"):
        raise PermissionProfileError("clean CANONICAL ownership required: role-registration segment modified")
    if any(line.strip() and not line.strip().startswith("#") for line in config_text[se2:].splitlines()):
        raise PermissionProfileError("clean CANONICAL ownership required: non-comment TOML follows terminal managed region")
    if tomllib is None:
        raise PermissionProfileError("Python 3.11+ tomllib is required")
    try:
        parsed = tomllib.loads(config_text)
    except (tomllib.TOMLDecodeError, ValueError) as exc:
        raise PermissionProfileError(f"clean CANONICAL ownership required: invalid .codex/config.toml: {exc}") from exc
    agents_table = parsed.get("agents")
    if not isinstance(agents_table, dict):
        raise PermissionProfileError("clean CANONICAL ownership required: agents table missing")
    for item in expected_regs:
        value = agents_table.get(item["role"])
        if not isinstance(value, dict) or value.get("config_file") != item["config_file"]:
            raise PermissionProfileError(f"clean CANONICAL ownership required: registration mismatch: {item['role']}")
    return managed


def is_prefix(parent: PurePosixPath, child: PurePosixPath) -> bool:
    return len(parent.parts) <= len(child.parts) and child.parts[:len(parent.parts)] == parent.parts


def overlaps(left: PurePosixPath, right: PurePosixPath) -> bool:
    return is_prefix(left, right) or is_prefix(right, left)


def validate_scope(target: Path, scope: PurePosixPath, managed: list[PurePosixPath]) -> None:
    for reserved in RESERVED_HARNESS_PATHS:
        if overlaps(scope, reserved):
            raise PermissionProfileError(f"write scope overlaps Harness-owned runtime path: {reserved}")
    for rel in managed:
        if overlaps(scope, rel):
            raise PermissionProfileError(f"write scope overlaps Harness-managed asset: {rel}")
    lexical = target / scope.as_posix()
    if not lexical.exists() or not lexical.is_dir():
        raise PermissionProfileError(f"write scope must be an existing directory: {scope.as_posix()}")
    current = target
    for part in scope.parts:
        current = current / part
        if current.is_symlink():
            raise PermissionProfileError(f"write scope traverses a symlink: {scope.as_posix()}")
    resolved = lexical.resolve()
    try:
        resolved.relative_to(target)
    except ValueError as exc:
        raise PermissionProfileError(f"write scope escapes target repository: {scope.as_posix()}") from exc


def toml_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def build_overrides(profile_name: str, scopes: list[PurePosixPath]) -> list[str]:
    if not PROFILE_NAME_RE.fullmatch(profile_name):
        raise PermissionProfileError("profile name may contain only letters, digits, underscore, and hyphen")
    rules: list[tuple[str, str]] = [
        (".agents", "read"),
        (".git", "read"),
        (".codex", "read"),
        (INSTALL_ROOT, "read"),
    ]
    rules.extend((scope.as_posix(), "write") for scope in scopes)
    filesystem_rules = ",".join(f"{toml_string(path)}={toml_string(access)}" for path, access in rules)
    profile_value = "{" + f"extends={toml_string(':workspace')},filesystem={{\":workspace_roots\"={{{filesystem_rules}}}}},network={{enabled=false}}" + "}"
    return [f"default_permissions={toml_string(profile_name)}", f"permissions.{profile_name}={profile_value}"]


def plan(target_arg: str, write_scopes: list[str], profile_name: str) -> dict[str, Any]:
    target = git_root(Path(target_arg))
    try:
        manifest = read_canonical_manifest(target)
    except ContractError as exc:
        raise PermissionProfileError(str(exc)) from exc
    managed = _clean_canonical_ownership(target, manifest)
    scopes = sorted({normalize_rel(value) for value in write_scopes}, key=lambda p: p.as_posix())
    if not scopes:
        raise PermissionProfileError("at least one --write-scope is required")
    for index, left in enumerate(scopes):
        validate_scope(target, left, managed)
        for right in scopes[index+1:]:
            if overlaps(left, right):
                raise PermissionProfileError(f"overlapping write scopes are not allowed: {left.as_posix()} / {right.as_posix()}")
    overrides = build_overrides(profile_name, scopes)
    if any("sandbox_mode" in item or "sandbox_workspace_write" in item for item in overrides):
        raise PermissionProfileError("legacy sandbox settings must not be emitted with permission profiles")
    return {
        "profile_name": profile_name,
        "target": str(target),
        "write_scopes": [path.as_posix() for path in scopes],
        "config_overrides": overrides,
        "network": "disabled",
        "manifest_schema": manifest.get("schema_version"),
        "product_id": manifest.get("product_id"),
        "namespace_version": manifest.get("namespace_version"),
        "ownership_state": "CANONICAL_CLEAN",
        "model_calls": 0,
        "sol_calls": 0,
    }


def main() -> int:
    parser = argparse.ArgumentParser(prog="lunako_permission_profile.py")
    parser.add_argument("--target", required=True)
    parser.add_argument("--write-scope", action="append", default=[])
    parser.add_argument("--profile-name", default=DEFAULT_PERMISSION_PROFILE)
    parser.add_argument("--format", choices=("json", "lines"), default="json")
    args = parser.parse_args()
    try:
        result = plan(args.target, args.write_scope, args.profile_name)
    except PermissionProfileError as exc:
        print(f"LUNAKO PERMISSION PROFILE: REFUSED: {exc}")
        print("model_calls=0")
        print("sol_calls=0")
        return 2
    if args.format == "lines":
        for item in result["config_overrides"]:
            print(item)
    else:
        print(json.dumps(result, sort_keys=True, separators=(",", ":"), ensure_ascii=False))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
