#!/usr/bin/env python3
"""Build fail-closed Codex permission-profile overrides for protected project paths.

This helper is deterministic and model-free. It never mutates the user's Codex
configuration. It only emits config overrides that callers can pass to Codex.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path, PurePosixPath
from typing import Any

MANIFEST_REL = ".lunatic-harnes/install-manifest.json"
PROFILE_NAME_DEFAULT = "lunatic-protected-write"
PROFILE_NAME_RE = re.compile(r"^[A-Za-z0-9_-]+$")

# Harness-owned runtime/state surfaces must never be reopened by this helper.
RESERVED_HARNESS_PATHS = (
    PurePosixPath(".agents/skills/luna-harness"),
    PurePosixPath(".agents/work-packets"),
    PurePosixPath(".agents/project-interface"),
    PurePosixPath(".agents/schemas"),
)


class PermissionProfileError(RuntimeError):
    pass


def git_root(path: Path) -> Path:
    target = path.expanduser().resolve()
    p = subprocess.run(
        ["git", "-C", str(target), "rev-parse", "--show-toplevel"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if p.returncode != 0:
        raise PermissionProfileError("target must be inside a Git repository")
    root = Path(p.stdout.strip()).resolve()
    if root != target:
        raise PermissionProfileError(f"target must be the Git repository root: {root}")
    return root


def normalize_rel(value: str) -> PurePosixPath:
    if not value or any(ch in value for ch in ("\\", "\x00", "\n", "\r")):
        raise PermissionProfileError(f"unsafe write scope: {value!r}")
    p = PurePosixPath(value)
    if p.is_absolute() or not p.parts or p == PurePosixPath(".") or ".." in p.parts:
        raise PermissionProfileError(f"unsafe write scope: {value}")
    if p.parts[0] != ".agents" or len(p.parts) < 2:
        raise PermissionProfileError(
            "protected write scopes must be an explicit project-owned subtree under .agents/"
        )
    return p


def is_prefix(parent: PurePosixPath, child: PurePosixPath) -> bool:
    return len(parent.parts) <= len(child.parts) and child.parts[: len(parent.parts)] == parent.parts


def overlaps(a: PurePosixPath, b: PurePosixPath) -> bool:
    return is_prefix(a, b) or is_prefix(b, a)


def load_manifest(target: Path) -> dict[str, Any]:
    path = target / MANIFEST_REL
    if not path.is_file():
        raise PermissionProfileError("Lunatic Harnes install manifest is missing")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PermissionProfileError(f"invalid install manifest: {exc}") from exc
    if value.get("schema_version") != 1 or not isinstance(value.get("managed_files"), list):
        raise PermissionProfileError("unsupported install manifest schema")
    return value


def managed_paths(manifest: dict[str, Any]) -> list[PurePosixPath]:
    out: list[PurePosixPath] = []
    for item in manifest.get("managed_files", []):
        rel = str(item.get("target_path", ""))
        if not rel:
            raise PermissionProfileError("install manifest contains an empty managed target path")
        p = PurePosixPath(rel)
        if p.is_absolute() or ".." in p.parts:
            raise PermissionProfileError(f"unsafe managed target path in manifest: {rel}")
        out.append(p)
    return out


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
    # JSON double-quoted strings are valid TOML basic strings for this controlled input.
    return json.dumps(value, ensure_ascii=False)


def build_overrides(profile_name: str, scopes: list[PurePosixPath]) -> list[str]:
    if not PROFILE_NAME_RE.fullmatch(profile_name):
        raise PermissionProfileError("profile name may contain only letters, digits, underscore, and hyphen")

    rules: list[tuple[str, str]] = [
        (".agents", "read"),
        (".git", "read"),
        (".codex", "read"),
        (".lunatic-harnes", "read"),
    ]
    rules.extend((scope.as_posix(), "write") for scope in scopes)

    filesystem_rules = ",".join(
        f"{toml_string(path)}={toml_string(access)}" for path, access in rules
    )
    profile_value = (
        "{"
        f"extends={toml_string(':workspace')},"
        f"filesystem={{\":workspace_roots\"={{{filesystem_rules}}}}},"
        "network={enabled=false}"
        "}"
    )

    return [
        f"default_permissions={toml_string(profile_name)}",
        f"permissions.{profile_name}={profile_value}",
    ]


def plan(target_arg: str, write_scopes: list[str], profile_name: str) -> dict[str, Any]:
    target = git_root(Path(target_arg))
    manifest = load_manifest(target)
    managed = managed_paths(manifest)

    scopes = sorted({normalize_rel(value) for value in write_scopes}, key=lambda p: p.as_posix())
    if not scopes:
        raise PermissionProfileError("at least one --write-scope is required")

    for i, left in enumerate(scopes):
        validate_scope(target, left, managed)
        for right in scopes[i + 1 :]:
            if overlaps(left, right):
                raise PermissionProfileError(
                    f"overlapping write scopes are not allowed: {left.as_posix()} / {right.as_posix()}"
                )

    overrides = build_overrides(profile_name, scopes)
    if any("sandbox_mode" in item or "sandbox_workspace_write" in item for item in overrides):
        raise PermissionProfileError("legacy sandbox settings must not be emitted with permission profiles")

    return {
        "profile_name": profile_name,
        "target": str(target),
        "write_scopes": [p.as_posix() for p in scopes],
        "config_overrides": overrides,
        "network": "disabled",
        "model_calls": 0,
        "sol_calls": 0,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", required=True)
    ap.add_argument("--write-scope", action="append", default=[])
    ap.add_argument("--profile-name", default=PROFILE_NAME_DEFAULT)
    ap.add_argument("--format", choices=("json", "lines"), default="json")
    args = ap.parse_args()

    try:
        result = plan(args.target, args.write_scope, args.profile_name)
    except PermissionProfileError as exc:
        print(f"LUNATIC PERMISSION PROFILE: REFUSED: {exc}")
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
