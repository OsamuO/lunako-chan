#!/usr/bin/env python3
"""Canonical LUNAKO Harness project installer/lifecycle for N1."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import urlsplit, urlunsplit

try:
    import tomllib
except ModuleNotFoundError:
    tomllib = None  # type: ignore[assignment]

from lunako_contract import (
    AGENTS_BEGIN, AGENTS_END, BUNDLE_NAME, BUNDLE_REL, BUNDLE_SCHEMA_VERSION,
    BUNDLE_VERSION, DISPLAY_NAME, EXPECTED_REGISTRATIONS, MANIFEST_REL,
    MANIFEST_SCHEMA_VERSION, NAMESPACE_VERSION, PRODUCT_ID, REGION_ID,
    REGION_SOURCE_CONTRACT, ROLE_BEGIN, ROLE_END, ROLE_TARGET, SKILL_REL,
    ContractError, read_runtime_bundle, require_supported_tuple,
)

SOURCE_ROOT = Path(__file__).resolve().parents[1]

BINDING_BODY = f"""{AGENTS_BEGIN}
{DISPLAY_NAME} runtime is installed for this repository.
Before non-trivial implementation, architecture, migration, or cross-boundary work, read `{SKILL_REL}` and follow it as Harness execution policy.
Treat this repository's own Rules / Task / State / Acceptance / Sources / Deliverables as project authority; installed Harness files are execution-policy/runtime assets, not project business/source authority.
Do not edit files owned by `{MANIFEST_REL}` during normal project work unless the task explicitly concerns Harness maintenance.
{AGENTS_END}"""

class LunakoError(RuntimeError):
    pass

@dataclass(frozen=True)
class ConfigPlan:
    target_path: str
    original: bytes | None
    new_bytes: bytes
    target_file_created: bool
    region: str
    prefix: str
    suffix: str
    registrations: list[dict[str, str]]

@dataclass(frozen=True)
class RegionState:
    text: str
    region_start: int
    region_end: int
    segment_start: int
    segment_end: int
    prefix: str
    suffix: str
    record: dict[str, Any]


def sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha_file(path: Path) -> str:
    return sha_bytes(path.read_bytes())


def run_git(args: list[str], cwd: Path, *, check: bool = True) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(["git", *args], cwd=cwd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    if check and proc.returncode != 0:
        raise LunakoError(f"git {' '.join(args)} failed: {proc.stderr.strip() or proc.stdout.strip()}")
    return proc


def ensure_source_clean() -> None:
    proc = run_git(["status", "--porcelain"], SOURCE_ROOT)
    if proc.stdout.strip():
        raise LunakoError("source repository must be clean for init/sync")


def source_commit() -> str:
    return run_git(["rev-parse", "HEAD"], SOURCE_ROOT).stdout.strip()


def source_repo_id() -> str:
    proc = run_git(["remote", "get-url", "origin"], SOURCE_ROOT, check=False)
    if proc.returncode != 0 or not proc.stdout.strip():
        return "local-checkout"
    raw = proc.stdout.strip()
    if raw.startswith(("/", "./", "../", "file://")) or re.match(r"^[A-Za-z]:[\\/]", raw):
        return "local-checkout"
    if "://" in raw:
        try:
            parsed = urlsplit(raw)
            if parsed.scheme not in {"http", "https", "ssh", "git"} or not parsed.hostname or not parsed.path:
                return "local-checkout"
            host = parsed.hostname
            if ":" in host and not host.startswith("["):
                host = f"[{host}]"
            port = f":{parsed.port}" if parsed.port is not None else ""
            return urlunsplit((parsed.scheme, f"{host}{port}", parsed.path, "", ""))
        except ValueError:
            return "local-checkout"
    scp = re.match(r"^(?:[^@/]+@)?(?P<host>[A-Za-z0-9.-]+):(?P<path>[^?#]+)(?:[?#].*)?$", raw)
    if scp:
        path = scp.group("path").lstrip("/")
        if path:
            return f"ssh://{scp.group('host')}/{path}"
    return "local-checkout"


def normalize_rel(value: str, label: str) -> PurePosixPath:
    p = PurePosixPath(value)
    if p.is_absolute() or not p.parts or ".." in p.parts:
        raise LunakoError(f"unsafe {label} path: {value}")
    return p


def target_root(value: str) -> Path:
    target = Path(value).expanduser().resolve()
    if not target.is_dir():
        raise LunakoError(f"target is not a directory: {target}")
    proc = run_git(["rev-parse", "--show-toplevel"], target, check=False)
    if proc.returncode != 0:
        raise LunakoError("target must be inside a Git repository")
    root = Path(proc.stdout.strip()).resolve()
    if root != target:
        raise LunakoError(f"target must be the Git repository root: {root}")
    return root


def guarded_target_path(target: Path, rel_value: str, label: str) -> Path:
    rel = normalize_rel(rel_value, label)
    root = target.resolve()
    current = root
    for index, part in enumerate(rel.parts):
        current = current / part
        if current.is_symlink():
            raise LunakoError(f"unsafe symlink in {label} path: {rel_value}")
        if index < len(rel.parts) - 1 and current.exists() and not current.is_dir():
            raise LunakoError(f"non-directory component in {label} path: {rel_value}")
    resolved = current.resolve(strict=False)
    if resolved != root and root not in resolved.parents:
        raise LunakoError(f"{label} path escapes target repository: {rel_value}")
    return current


def decode_utf8(data: bytes, label: str) -> str:
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise LunakoError(f"{label} is not UTF-8: {exc}") from exc


def parse_toml_text(text: str, label: str) -> dict[str, Any]:
    if tomllib is None:
        raise LunakoError("Python 3.11+ tomllib is required")
    try:
        value = tomllib.loads(text)
    except (tomllib.TOMLDecodeError, ValueError) as exc:
        raise LunakoError(f"{label} is not valid TOML: {exc}") from exc
    if not isinstance(value, dict):
        raise LunakoError(f"{label} must parse to a TOML document")
    return value


def forbidden(source_rel: str, prefixes: list[str]) -> bool:
    normalized = source_rel.replace("\\", "/")
    return any(normalized.startswith(prefix) for prefix in prefixes)


def expand_bundle(bundle: dict[str, Any]) -> list[dict[str, str]]:
    raw = bundle.get("file_mappings")
    if not isinstance(raw, list) or not raw:
        raise LunakoError("runtime bundle must contain explicit file_mappings")
    if bundle.get("directory_mappings"):
        raise LunakoError("runtime bundle must not use broad directory_mappings")
    prefixes = [str(x) for x in bundle.get("forbidden_source_prefixes", [])]
    out: list[dict[str, str]] = []
    seen: set[str] = set()
    for item in raw:
        if not isinstance(item, dict) or not isinstance(item.get("source"), str) or not isinstance(item.get("target"), str):
            raise LunakoError("runtime bundle contains invalid file mapping")
        source = normalize_rel(item["source"], "source").as_posix()
        target = normalize_rel(item["target"], "target").as_posix()
        if forbidden(source, prefixes):
            raise LunakoError(f"forbidden runtime source path: {source}")
        if not (SOURCE_ROOT / source).is_file():
            raise LunakoError(f"runtime source file missing: {source}")
        if target in seen:
            raise LunakoError(f"duplicate runtime target: {target}")
        seen.add(target)
        out.append({"source": source, "target": target})
    return sorted(out, key=lambda item: item["target"])


def registration_contract(bundle: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, str]]]:
    cfg = bundle.get("project_role_registration")
    if not isinstance(cfg, dict):
        raise LunakoError("runtime bundle project_role_registration must be object")
    if cfg.get("target_path") != ROLE_TARGET or cfg.get("ownership") != "managed-terminal-region" or cfg.get("placement") != "terminal":
        raise LunakoError("invalid project role-registration ownership")
    if cfg.get("begin_marker") != ROLE_BEGIN or cfg.get("end_marker") != ROLE_END:
        raise LunakoError("project role-registration marker mismatch")
    raw = cfg.get("registrations")
    expected = [{"role": role, "config_file": path} for role, path in EXPECTED_REGISTRATIONS]
    if raw != expected:
        raise LunakoError("project role-registration does not match frozen logical-role contract")
    return cfg, expected


def validate_registration_runtime_members(mappings: list[dict[str, str]], registrations: list[dict[str, str]]) -> None:
    targets = {m["target"]: m["source"] for m in mappings}
    if ROLE_TARGET in targets:
        raise LunakoError(".codex/config.toml must not be whole-file runtime member")
    for reg in registrations:
        target = (PurePosixPath(".codex") / reg["config_file"]).as_posix()
        source = targets.get(target)
        if source is None:
            raise LunakoError(f"registered role TOML is not a managed member: {target}")
        parsed = parse_toml_text((SOURCE_ROOT / source).read_text(encoding="utf-8"), source)
        if parsed.get("name") != reg["role"]:
            raise LunakoError(f"registered role identity mismatch: {reg['role']}")


def load_bundle() -> dict[str, Any]:
    try:
        bundle = read_runtime_bundle(SOURCE_ROOT)
    except ContractError as exc:
        raise LunakoError(str(exc)) from exc
    if bundle.get("membership_policy") != "explicit-positive":
        raise LunakoError("runtime bundle must declare explicit-positive membership")
    mappings = expand_bundle(bundle)
    _, registrations = registration_contract(bundle)
    validate_registration_runtime_members(mappings, registrations)
    binding = bundle.get("root_agents_binding")
    if not isinstance(binding, dict) or binding.get("begin_marker") != AGENTS_BEGIN or binding.get("end_marker") != AGENTS_END or binding.get("skill_path") != SKILL_REL:
        raise LunakoError("runtime bundle root AGENTS binding mismatch")
    if bundle.get("install_manifest_path") != MANIFEST_REL:
        raise LunakoError("runtime bundle install manifest path mismatch")
    require_supported_tuple(bundle.get("product_id"), bundle.get("namespace_version"))
    return bundle

