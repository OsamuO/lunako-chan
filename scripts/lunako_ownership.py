#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from lunako_contract import (
    AGENTS_BEGIN, AGENTS_END, BUNDLE_NAME, BUNDLE_VERSION, EXPECTED_REGISTRATIONS,
    MANIFEST_REL, MANIFEST_SCHEMA_VERSION, NAMESPACE_VERSION, PRODUCT_ID,
    REGION_ID, REGION_SOURCE_CONTRACT, ROLE_BEGIN, ROLE_END, ROLE_TARGET,
)
from lunako_core import BINDING_BODY, ConfigPlan, LunakoError, RegionState, decode_utf8, guarded_target_path, parse_toml_text, sha_bytes, sha_file, source_commit, source_repo_id

LEGACY_AGENTS_BEGIN = "<!-- LUNATIC-HARNES:BEGIN -->"
LEGACY_AGENTS_END = "<!-- LUNATIC-HARNES:END -->"
LEGACY_ROLE_BEGIN = "# LUNATIC-HARNES:BEGIN PROJECT-ROLE-REGISTRATION"
LEGACY_ROLE_END = "# LUNATIC-HARNES:END PROJECT-ROLE-REGISTRATION"

_FAULT_FIRED = False
_REMOVE_FAULT_FIRED = False


def _find_block(text: str, begin: str = AGENTS_BEGIN, end: str = AGENTS_END) -> tuple[int, int] | None:
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
        raise LunakoError("AGENTS.md contains malformed or duplicate managed markers")
    return starts[0], ends[0] + len(end)


def binding_affixes(existing: bytes) -> tuple[str, str]:
    text = decode_utf8(existing, "AGENTS.md")
    if not text:
        return "", "\n"
    return ("" if text.endswith("\n\n") else ("\n" if text.endswith("\n") else "\n\n")), "\n"


def append_binding(existing: bytes, prefix: str, suffix: str) -> bytes:
    text = decode_utf8(existing, "AGENTS.md")
    if _find_block(text) is not None:
        raise LunakoError("AGENTS.md already contains an unowned LUNAKO managed block")
    return (text + prefix + BINDING_BODY + suffix).encode()


def _replace_binding_with_markers(existing: bytes, begin: str, end: str, replacement: str) -> bytes:
    text = decode_utf8(existing, "AGENTS.md")
    span = _find_block(text, begin, end)
    if span is None:
        raise LunakoError("AGENTS.md managed block is missing")
    return (text[:span[0]] + replacement + text[span[1]:]).encode()


def replace_binding(existing: bytes) -> bytes:
    return _replace_binding_with_markers(existing, AGENTS_BEGIN, AGENTS_END, BINDING_BODY)


def replace_legacy_binding(existing: bytes) -> bytes:
    return _replace_binding_with_markers(existing, LEGACY_AGENTS_BEGIN, LEGACY_AGENTS_END, BINDING_BODY)


def _remove_binding_with_markers(existing: bytes, manifest: dict[str, Any], begin: str, end_marker: str) -> bytes:
    text = decode_utf8(existing, "AGENTS.md")
    span = _find_block(text, begin, end_marker)
    if span is None:
        raise LunakoError("AGENTS.md managed block is missing")
    prefix = str(manifest.get("agents_binding_prefix", ""))
    suffix = str(manifest.get("agents_binding_suffix", ""))
    start, end = span
    if prefix:
        if start < len(prefix) or text[start-len(prefix):start] != prefix:
            raise LunakoError("AGENTS.md managed binding prefix modified")
        start -= len(prefix)
    if suffix:
        if text[end:end+len(suffix)] != suffix:
            raise LunakoError("AGENTS.md managed binding suffix modified")
        end += len(suffix)
    return (text[:start] + text[end:]).encode()


def remove_binding(existing: bytes, manifest: dict[str, Any]) -> bytes:
    return _remove_binding_with_markers(existing, manifest, AGENTS_BEGIN, AGENTS_END)


def remove_legacy_binding(existing: bytes, manifest: dict[str, Any]) -> bytes:
    return _remove_binding_with_markers(existing, manifest, LEGACY_AGENTS_BEGIN, LEGACY_AGENTS_END)


def binding_hashes(prefix: str, suffix: str) -> tuple[str, str]:
    return sha_bytes(BINDING_BODY.encode()), sha_bytes((prefix + BINDING_BODY + suffix).encode())


def _marker_offsets(text: str, marker: str) -> list[tuple[int, int]]:
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
    starts = _marker_offsets(text, begin)
    ends = _marker_offsets(text, end)
    if not starts and not ends:
        return None
    if len(starts) != 1 or len(ends) != 1 or ends[0][0] < starts[0][0]:
        raise LunakoError(".codex/config.toml contains malformed or duplicate role-registration markers")
    return starts[0][0], ends[0][1]


def find_region(text: str) -> tuple[int, int] | None:
    return _find_region(text, ROLE_BEGIN, ROLE_END)


def render_registration_region() -> tuple[str, list[dict[str, str]]]:
    regs = [{"role": role, "config_file": path} for role, path in EXPECTED_REGISTRATIONS]
    lines = [ROLE_BEGIN]
    for index, item in enumerate(regs):
        if index:
            lines.append("")
        lines.extend([f"[agents.{item['role']}]", f"config_file = {json.dumps(item['config_file'])}"])
    lines.append(ROLE_END)
    return "\n".join(lines), regs


def _config_affixes(existing: bytes) -> tuple[str, str]:
    text = decode_utf8(existing, ROLE_TARGET)
    if not text:
        return "", "\n"
    return ("" if text.endswith(("\n", "\r")) else "\n"), "\n"


def _semantic_collisions(parsed: dict[str, Any]) -> list[str]:
    agents = parsed.get("agents")
    if agents is None:
        return []
    if not isinstance(agents, dict):
        return ["agents: existing value is not a table"]
    return [f"agents.{role}: pre-existing user/project role" for role, _ in EXPECTED_REGISTRATIONS if role in agents]


def plan_new_registration(target: Path) -> ConfigPlan:
    path = guarded_target_path(target, ROLE_TARGET, "project role-registration target")
    if path.exists() and not path.is_file():
        raise LunakoError(f"{ROLE_TARGET}: existing path is not a regular file")
    original = path.read_bytes() if path.is_file() else None
    existing = original or b""
    text = decode_utf8(existing, ROLE_TARGET)
    if find_region(text) is not None:
        raise LunakoError(f"{ROLE_TARGET}: pre-existing LUNAKO registration region without ownership")
    if _find_region(text, LEGACY_ROLE_BEGIN, LEGACY_ROLE_END) is not None:
        raise LunakoError(f"{ROLE_TARGET}: pre-existing legacy registration region without supported ownership")
    parsed = parse_toml_text(text, ROLE_TARGET)
    collisions = _semantic_collisions(parsed)
    if collisions:
        raise LunakoError("; ".join(collisions))
    region, regs = render_registration_region()
    prefix, suffix = _config_affixes(existing)
    candidate = text + prefix + region + suffix
    parse_toml_text(candidate, ROLE_TARGET)
    return ConfigPlan(ROLE_TARGET, original, candidate.encode(), original is None, region, prefix, suffix, regs)


def _inspect_registration_region(target: Path, manifest: dict[str, Any], begin: str, end: str) -> tuple[RegionState | None, list[str]]:
    regions = manifest.get("managed_regions")
    if not isinstance(regions, list):
        return None, ["manifest managed_regions missing"]
    matches = [r for r in regions if isinstance(r, dict) and r.get("region_id") == REGION_ID]
    if len(matches) != 1:
        return None, ["manifest must contain exactly one role-registration managed region"]
    record = matches[0]
    problems: list[str] = []
    if record.get("target_path") != ROLE_TARGET:
        problems.append("role-registration target mismatch")
    if record.get("ownership") != "managed-terminal-region" or record.get("placement") != "terminal":
        problems.append("role-registration ownership mismatch")
    if record.get("begin_marker") != begin or record.get("end_marker") != end:
        problems.append("role-registration marker mismatch")
    if record.get("source_contract") != REGION_SOURCE_CONTRACT:
        problems.append("role-registration source contract mismatch")
    path = guarded_target_path(target, ROLE_TARGET, "project role-registration target")
    if not path.is_file():
        return None, problems + [f"{ROLE_TARGET}: missing"]
    text = decode_utf8(path.read_bytes(), ROLE_TARGET)
    try:
        parsed = parse_toml_text(text, ROLE_TARGET)
        span = _find_region(text, begin, end)
    except LunakoError as exc:
        return None, problems + [str(exc)]
    if span is None:
        return None, problems + ["managed role-registration region missing"]
    rs, re = span
    prefix = str(record.get("segment_prefix", ""))
    suffix = str(record.get("segment_suffix", ""))
    ss, se = rs, re
    if prefix:
        if rs < len(prefix) or text[rs-len(prefix):rs] != prefix:
            problems.append("managed role-registration prefix modified")
        else:
            ss -= len(prefix)
    if suffix:
        if text[re:re+len(suffix)] != suffix:
            problems.append("managed role-registration suffix modified")
        else:
            se += len(suffix)
    if sha_bytes(text[rs:re].encode()) != record.get("managed_region_sha256"):
        problems.append("managed role-registration region modified")
    if sha_bytes(text[ss:se].encode()) != record.get("managed_segment_sha256"):
        problems.append("managed role-registration segment modified")
    if any(line.strip() and not line.strip().startswith("#") for line in text[se:].splitlines()):
        problems.append("non-comment TOML after terminal managed region")
    expected = [{"role": role, "config_file": config} for role, config in EXPECTED_REGISTRATIONS]
    if record.get("installed_registrations") != expected:
        problems.append("installed registration snapshot mismatch")
    agents = parsed.get("agents")
    if not isinstance(agents, dict):
        problems.append("agents table missing")
    else:
        for item in expected:
            value = agents.get(item["role"])
            if not isinstance(value, dict) or value.get("config_file") != item["config_file"]:
                problems.append(f"registration mismatch: {item['role']}")
    return RegionState(text, rs, re, ss, se, prefix, suffix, record), problems


def inspect_registration_region(target: Path, manifest: dict[str, Any]) -> tuple[RegionState | None, list[str]]:
    return _inspect_registration_region(target, manifest, ROLE_BEGIN, ROLE_END)


def inspect_legacy_registration_region(target: Path, manifest: dict[str, Any]) -> tuple[RegionState | None, list[str]]:
    return _inspect_registration_region(target, manifest, LEGACY_ROLE_BEGIN, LEGACY_ROLE_END)


def plan_replace_registration(state: RegionState) -> ConfigPlan:
    region, regs = render_registration_region()
    candidate = state.text[:state.region_start] + region + state.text[state.region_end:]
    parse_toml_text(candidate, ROLE_TARGET)
    segment_end = state.region_start + len(region) + len(state.suffix)
    if any(line.strip() and not line.strip().startswith("#") for line in candidate[segment_end:].splitlines()):
        raise LunakoError("non-comment TOML after terminal managed region")
    return ConfigPlan(ROLE_TARGET, state.text.encode(), candidate.encode(), bool(state.record.get("target_file_created", False)), region, state.prefix, state.suffix, regs)


def remove_registration_region(state: RegionState) -> tuple[bytes, bool]:
    before = state.text[:state.segment_start]
    tail = state.text[state.segment_end:]
    text = before + ("\n" if before and tail and not before.endswith(("\n", "\r")) and not tail.startswith(("\n", "\r")) else "") + tail
    if text:
        parse_toml_text(text, ROLE_TARGET)
    return text.encode(), bool(state.record.get("target_file_created", False)) and text == ""


def validate_atomic_write_path(target: Path, rel_value: str, *, label: str = "managed target") -> None:
    path = guarded_target_path(target, rel_value, label)
    tmp = path.with_name(path.name + ".lunako-tmp")
    if tmp.exists() or tmp.is_symlink():
        raise LunakoError(f"temporary write path already exists: {tmp.name}")


def write_atomic(target: Path, rel_value: str, data: bytes, *, label: str = "managed target") -> None:
    global _FAULT_FIRED
    fail_path = os.environ.get("LUNAKO_TEST_FAIL_WRITE_PATH")
    if fail_path == rel_value and not _FAULT_FIRED:
        _FAULT_FIRED = True
        raise OSError(5, f"forced lifecycle write failure at {rel_value}")
    path = guarded_target_path(target, rel_value, label)
    path.parent.mkdir(parents=True, exist_ok=True)
    path = guarded_target_path(target, rel_value, label)
    tmp = path.with_name(path.name + ".lunako-tmp")
    if tmp.exists() or tmp.is_symlink():
        raise LunakoError(f"temporary write path already exists: {tmp.name}")
    tmp.write_bytes(data)
    if path.is_symlink():
        tmp.unlink(missing_ok=True)
        raise LunakoError(f"unsafe symlink in {label} path: {rel_value}")
    os.replace(tmp, path)


def unlink_owned(target: Path, rel_value: str, *, label: str = "managed target") -> None:
    global _REMOVE_FAULT_FIRED
    fail_path = os.environ.get("LUNAKO_TEST_FAIL_REMOVE_PATH")
    if fail_path == rel_value and not _REMOVE_FAULT_FIRED:
        _REMOVE_FAULT_FIRED = True
        raise OSError(5, f"forced lifecycle removal failure at {rel_value}")
    path = guarded_target_path(target, rel_value, label)
    path.unlink()


def preflight_new_paths(target: Path, mappings: list[dict[str, str]]) -> list[str]:
    problems: list[str] = []
    for mapping in mappings:
        rel = mapping["target"]
        try:
            path = guarded_target_path(target, rel, "runtime target")
            if path.exists() or path.is_symlink():
                problems.append(f"{rel}: pre-existing unowned path")
        except LunakoError as exc:
            problems.append(str(exc))
    manifest_path = guarded_target_path(target, MANIFEST_REL, "install manifest")
    if manifest_path.exists() or manifest_path.is_symlink():
        problems.append(f"{MANIFEST_REL}: pre-existing path")
    return problems


def file_record_map(manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for item in manifest.get("managed_files", []):
        if not isinstance(item, dict) or not isinstance(item.get("target_path"), str):
            raise LunakoError("invalid managed_files record")
        rel = item["target_path"]
        if rel in result:
            raise LunakoError(f"duplicate managed target in manifest: {rel}")
        result[rel] = item
    return result


def build_manifest(bundle: dict[str, Any], mappings: list[dict[str, str]], *, agents_file_created: bool, prefix: str, suffix: str, config_plan: ConfigPlan) -> dict[str, Any]:
    block_sha, segment_sha = binding_hashes(prefix, suffix)
    root = Path(__file__).resolve().parents[1]
    files = [{"source_path": m["source"], "target_path": m["target"], "installed_sha256": sha_file(root / m["source"])} for m in mappings]
    region_segment = (config_plan.prefix + config_plan.region + config_plan.suffix).encode()
    return {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "product_id": PRODUCT_ID,
        "namespace_version": NAMESPACE_VERSION,
        "source_repo": source_repo_id(),
        "source_commit": source_commit(),
        "bundle_name": BUNDLE_NAME,
        "bundle_version": str(bundle.get("bundle_version", BUNDLE_VERSION)),
        "managed_files": files,
        "managed_agents_block_sha256": block_sha,
        "managed_agents_segment_sha256": segment_sha,
        "agents_binding_prefix": prefix,
        "agents_binding_suffix": suffix,
        "agents_file_created": agents_file_created,
        "managed_regions": [{
            "region_id": REGION_ID,
            "target_path": ROLE_TARGET,
            "ownership": "managed-terminal-region",
            "placement": "terminal",
            "begin_marker": ROLE_BEGIN,
            "end_marker": ROLE_END,
            "managed_region_sha256": sha_bytes(config_plan.region.encode()),
            "managed_segment_sha256": sha_bytes(region_segment),
            "segment_prefix": config_plan.prefix,
            "segment_suffix": config_plan.suffix,
            "target_file_created": config_plan.target_file_created,
            "source_contract": REGION_SOURCE_CONTRACT,
            "installed_registrations": config_plan.registrations,
        }],
    }
