#!/usr/bin/env python3
"""Deterministically check Impact Manifest file-scope closure.

This helper does not decide whether an Impact Manifest is needed. It is only a
non-bypass verification step once a Manifest is active.

Invariant:
    every actual changed file must be declared in
    expected_touches.owned_paths.

An actual file outside that set is IMPACT_MISMATCH. Declared paths that were not
ultimately touched are reported for reconciliation but do not by themselves fail
scope closure because owned_paths is an approved impact boundary, not a promise
that every path will change.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path, PurePosixPath
from typing import Iterable


class ClosureInputError(ValueError):
    pass


def normalize_repo_path(raw: str) -> str:
    value = raw.strip().replace("\\", "/")
    while value.startswith("./"):
        value = value[2:]
    if not value:
        raise ClosureInputError("empty repository path")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts:
        raise ClosureInputError(f"path must be repository-relative: {raw!r}")
    return path.as_posix()


def unique_normalized(values: Iterable[str]) -> list[str]:
    return sorted({normalize_repo_path(value) for value in values})


def load_manifest(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ClosureInputError(f"manifest not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ClosureInputError(f"manifest is not valid JSON: {exc}") from exc

    try:
        owned_paths = value["expected_touches"]["owned_paths"]
    except (KeyError, TypeError) as exc:
        raise ClosureInputError("manifest missing expected_touches.owned_paths") from exc
    if not isinstance(owned_paths, list) or not all(isinstance(item, str) for item in owned_paths):
        raise ClosureInputError("expected_touches.owned_paths must be an array of strings")
    return value


def actual_files_from_text(path: Path) -> list[str]:
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise ClosureInputError(f"actual-files input not found: {path}") from exc
    stripped = text.strip()
    if not stripped:
        return []
    if stripped.startswith("["):
        try:
            value = json.loads(stripped)
        except json.JSONDecodeError as exc:
            raise ClosureInputError(f"actual-files JSON is invalid: {exc}") from exc
        if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
            raise ClosureInputError("actual-files JSON must be an array of strings")
        return value
    return [line for line in text.splitlines() if line.strip()]


def actual_files_from_git(repo: Path, base: str, head: str | None) -> list[str]:
    cmd = ["git", "diff", "--name-only", "--diff-filter=ACMRTUXB", base]
    if head:
        cmd.append(head)
    cmd.append("--")
    try:
        out = subprocess.check_output(cmd, cwd=repo, text=True, stderr=subprocess.STDOUT)
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        detail = getattr(exc, "output", "") or str(exc)
        raise ClosureInputError(f"git diff failed: {detail.strip()}") from exc
    return [line for line in out.splitlines() if line.strip()]


def evaluate(declared: Iterable[str], actual: Iterable[str]) -> dict[str, object]:
    declared_files = unique_normalized(declared)
    actual_files = unique_normalized(actual)
    declared_set = set(declared_files)
    actual_set = set(actual_files)
    unexpected = sorted(actual_set - declared_set)
    declared_not_touched = sorted(declared_set - actual_set)

    return {
        "status": "IMPACT_MISMATCH" if unexpected else "PASS",
        "actual_to_declared": "FAIL" if unexpected else "PASS",
        "declared_to_actual": "PARTIAL" if declared_not_touched else "PASS",
        "declared_files": declared_files,
        "actual_files": actual_files,
        "unexpected_actual_files": unexpected,
        "declared_not_touched": declared_not_touched,
    }


def self_test() -> None:
    declared = [
        "docs/idempotency-contract.md",
        "docs/migration.md",
        "idempotency_service/api.py",
        "idempotency_service/dead_letter.py",
        "idempotency_service/migration.py",
        "idempotency_service/retry_worker.py",
        "idempotency_service/store.py",
    ]
    exact = evaluate(declared, declared)
    assert exact["status"] == "PASS"
    assert exact["declared_to_actual"] == "PASS"

    subset = evaluate(declared, declared[:-1])
    assert subset["status"] == "PASS"
    assert subset["declared_to_actual"] == "PARTIAL"

    e013_style = evaluate(declared, [*declared, "idempotency_service/__init__.py"])
    assert e013_style["status"] == "IMPACT_MISMATCH"
    assert e013_style["unexpected_actual_files"] == ["idempotency_service/__init__.py"]

    print("impact-closure self-test: PASS")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--actual-file", action="append", default=[])
    parser.add_argument("--actual-files-from", type=Path)
    parser.add_argument("--git-repo", type=Path, default=Path.cwd())
    parser.add_argument("--git-base")
    parser.add_argument("--git-head")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        self_test()
        return 0

    if args.manifest is None:
        parser.error("--manifest is required unless --self-test is used")

    sources = int(bool(args.actual_file)) + int(args.actual_files_from is not None) + int(args.git_base is not None)
    if sources != 1:
        parser.error("choose exactly one actual-file source: --actual-file, --actual-files-from, or --git-base")

    try:
        manifest = load_manifest(args.manifest)
        declared = manifest["expected_touches"]["owned_paths"]
        if args.actual_file:
            actual = args.actual_file
        elif args.actual_files_from is not None:
            actual = actual_files_from_text(args.actual_files_from)
        else:
            actual = actual_files_from_git(args.git_repo, args.git_base, args.git_head)
        result = evaluate(declared, actual)
    except ClosureInputError as exc:
        print(json.dumps({"status": "INVALID_INPUT", "error": str(exc)}, sort_keys=True))
        return 1

    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 2 if result["status"] == "IMPACT_MISMATCH" else 0


if __name__ == "__main__":
    raise SystemExit(main())
