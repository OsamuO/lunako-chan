#!/usr/bin/env python3
"""Model-free standalone validator for the projected Lunatic Harnes package.

Run this from a clean public-package Git checkout. The validator uses only
files present in that checkout plus normal system Python/Git. It exercises one
ordinary target lifecycle with the packaged scripts/lunatic.py and leaves the
public source checkout unchanged.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
RUNTIME_MANIFEST = ROOT / "runtime/lunatic-runtime-bundle.json"
LUNATIC = ROOT / "scripts/lunatic.py"
MANAGED_BEGIN = "<!-- LUNATIC-HARNES:BEGIN -->"
MANAGED_END = "<!-- LUNATIC-HARNES:END -->"
EXPECTED_RUNTIME_COUNT = 49
INSTALL_MANIFEST = ".lunatic-harnes/install-manifest.json"

REQUIRED_FILES = (
    "README.md",
    "LICENSE",
    ".gitignore",
    "runtime/lunatic-runtime-bundle.json",
    "scripts/lunatic.py",
    "scripts/validate_public_release.py",
    ".agents/project-interface/SPECIFICATION.md",
    ".agents/skills/luna-harness/SKILL.md",
    ".agents/schemas/routing-decision.schema.json",
    ".codex/agents/luna-worker.toml",
    "docs/VALIDATION.md",
)
FORBIDDEN_PREFIXES = (
    ".agents/evals/",
    ".agents/release/",
    ".agents/project-state/",
    ".agents/work-packets/",
    ".luna-runtime/",
)


class ValidationError(RuntimeError):
    pass


def run(cmd: list[str], *, cwd: Path, check: bool = False) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONNOUSERSITE"] = "1"
    env["PYTHONPATH"] = ""
    proc = subprocess.run(
        cmd,
        cwd=cwd,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    if check and proc.returncode != 0:
        raise ValidationError(f"command failed ({proc.returncode}): {' '.join(cmd)}\n{proc.stdout.strip()}")
    return proc


def require(ok: bool, message: str) -> None:
    if not ok:
        raise ValidationError(message)


def safe_relative(value: str) -> bool:
    if not value or "\\" in value:
        return False
    path = PurePosixPath(value)
    return not path.is_absolute() and value != "." and ".." not in path.parts


def under_prefix(path: str, prefix: str) -> bool:
    root = prefix.rstrip("/")
    return path == root or path.startswith(root + "/")


def git(*args: str, cwd: Path = ROOT) -> str:
    proc = run(["git", *args], cwd=cwd)
    if proc.returncode != 0:
        raise ValidationError(f"git {' '.join(args)} failed: {proc.stdout.strip()}")
    return proc.stdout.strip()


def require_clean_public_source() -> str:
    top = git("rev-parse", "--show-toplevel")
    require(Path(top).resolve() == ROOT.resolve(), "validator must run from the public package Git root")
    commit = git("rev-parse", "HEAD")
    require(git("status", "--porcelain", "--untracked-files=all") == "", "public source checkout must be clean")
    return commit


def load_runtime_targets() -> set[str]:
    try:
        runtime = json.loads(RUNTIME_MANIFEST.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValidationError(f"runtime inventory parse failed: {exc}") from exc
    require(isinstance(runtime, dict), "runtime inventory must be a JSON object")
    require(runtime.get("schema_version") == 1, "unsupported runtime inventory schema")
    require(runtime.get("membership_policy") == "explicit-positive", "runtime inventory must be explicit-positive")
    require(not runtime.get("directory_mappings"), "runtime inventory must not use directory_mappings")
    mappings = runtime.get("file_mappings")
    require(isinstance(mappings, list), "runtime inventory file_mappings must be a list")

    targets: set[str] = set()
    sources: set[str] = set()
    for index, item in enumerate(mappings):
        require(isinstance(item, dict), f"runtime mapping[{index}] must be an object")
        source = item.get("source")
        target = item.get("target")
        require(isinstance(source, str) and isinstance(target, str), f"runtime mapping[{index}] source/target must be strings")
        require(safe_relative(source), f"unsafe runtime source: {source}")
        require(safe_relative(target), f"unsafe runtime target: {target}")
        require((ROOT / source).is_file(), f"runtime source missing from public package: {source}")
        require(source not in sources, f"duplicate runtime source: {source}")
        require(target not in targets, f"duplicate runtime target: {target}")
        require(not any(under_prefix(target, prefix) for prefix in FORBIDDEN_PREFIXES), f"forbidden runtime target: {target}")
        sources.add(source)
        targets.add(target)

    require(len(targets) == EXPECTED_RUNTIME_COUNT, f"runtime target count must be {EXPECTED_RUNTIME_COUNT}, got {len(targets)}")
    return targets


def validate_public_structure() -> set[str]:
    for rel in REQUIRED_FILES:
        require((ROOT / rel).is_file(), f"missing required public file: {rel}")
    example_root = ROOT / "examples/minimal-project"
    require(example_root.is_dir() and any(p.is_file() for p in example_root.rglob("*")), "minimal public example is missing")

    forbidden_hits: list[str] = []
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(ROOT).as_posix()
        if rel.startswith(".git/"):
            continue
        if any(under_prefix(rel, prefix) for prefix in FORBIDDEN_PREFIXES):
            forbidden_hits.append(rel)
    require(not forbidden_hits, f"forbidden public package paths present: {sorted(forbidden_hits)}")
    return load_runtime_targets()


def snapshot_files(root: Path) -> dict[str, bytes]:
    out: dict[str, bytes] = {}
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(root).as_posix()
        if rel == ".git" or rel.startswith(".git/"):
            continue
        out[rel] = path.read_bytes()
    return out


def file_hashes(root: Path, paths: set[str]) -> dict[str, str]:
    result: dict[str, str] = {}
    for rel in sorted(paths):
        path = root / rel
        require(path.is_file(), f"installed runtime path missing: {rel}")
        result[rel] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def parse_install_manifest(target: Path) -> dict:
    path = target / INSTALL_MANIFEST
    require(path.is_file(), "install manifest missing after init")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValidationError(f"install manifest parse failed: {exc}") from exc
    require(isinstance(value, dict), "install manifest must be an object")
    return value


def managed_target_set(manifest: dict) -> set[str]:
    managed = manifest.get("managed_files")
    require(isinstance(managed, list), "install manifest managed_files must be a list")
    targets: set[str] = set()
    for index, item in enumerate(managed):
        require(isinstance(item, dict), f"managed_files[{index}] must be an object")
        target = item.get("target_path")
        require(isinstance(target, str) and safe_relative(target), f"invalid managed target path at index {index}")
        require(target not in targets, f"duplicate managed target in install manifest: {target}")
        targets.add(target)
    return targets


def call_lunatic(command: str, target: Path) -> subprocess.CompletedProcess[str]:
    return run([sys.executable, str(LUNATIC), command, str(target)], cwd=ROOT)


def require_command(proc: subprocess.CompletedProcess[str], marker: str, label: str) -> None:
    require(proc.returncode == 0, f"{label} failed ({proc.returncode}): {proc.stdout.strip()}")
    require(marker in proc.stdout.splitlines(), f"{label} missing stable marker {marker!r}: {proc.stdout.strip()}")


def forbidden_target_paths(target: Path) -> list[str]:
    hits: list[str] = []
    for path in target.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(target).as_posix()
        if rel.startswith(".git/"):
            continue
        if any(under_prefix(rel, prefix) for prefix in FORBIDDEN_PREFIXES):
            hits.append(rel)
    return sorted(hits)


def lifecycle(runtime_targets: set[str]) -> dict[str, str | int]:
    with tempfile.TemporaryDirectory(prefix="lunatic-public-target-") as tmp:
        target = Path(tmp) / "ordinary-project"
        target.mkdir()
        git("init", "-q", cwd=target)
        git("config", "user.name", "Package Validator", cwd=target)
        git("config", "user.email", "validator" + chr(64) + "example.invalid", cwd=target)

        original_agents = b"# Ordinary Project Rules\n\nKeep project-owned rules intact.\n"
        sentinel = b"ordinary-target-sentinel\n"
        (target / "AGENTS.md").write_bytes(original_agents)
        (target / "project-sentinel.txt").write_bytes(sentinel)
        git("add", "AGENTS.md", "project-sentinel.txt", cwd=target)
        git("commit", "-q", "-m", "ordinary target baseline", cwd=target)
        baseline = snapshot_files(target)
        require(set(baseline) == {"AGENTS.md", "project-sentinel.txt"}, "ordinary target baseline fixture is not minimal")
        require(not (target / ".agents/project-state").exists(), "target fixture unexpectedly contains Harness project state")

        init = call_lunatic("init", target)
        require_command(init, "LUNATIC INIT: PASS", "init")
        install_manifest = parse_install_manifest(target)
        installed_managed = managed_target_set(install_manifest)
        require(installed_managed == runtime_targets, "installed managed target set differs from staged runtime manifest target set")
        require(len(installed_managed) == EXPECTED_RUNTIME_COUNT, "installed runtime target count mismatch")

        after_init = snapshot_files(target)
        new_paths = set(after_init) - set(baseline)
        expected_new = set(runtime_targets) | {INSTALL_MANIFEST}
        require(new_paths == expected_new, f"init created unexpected/missing files: extra={sorted(new_paths - expected_new)} missing={sorted(expected_new - new_paths)}")
        agents_after_init = (target / "AGENTS.md").read_text(encoding="utf-8")
        require(agents_after_init.count(MANAGED_BEGIN) == 1 and agents_after_init.count(MANAGED_END) == 1, "managed AGENTS block count must be exactly one")
        require("# Ordinary Project Rules" in agents_after_init and "Keep project-owned rules intact." in agents_after_init, "project-owned AGENTS content was not preserved")

        forbidden = forbidden_target_paths(target)
        require(not forbidden, f"forbidden development paths installed: {forbidden}")
        hashes_after_init = file_hashes(target, runtime_targets)

        status1 = call_lunatic("status", target)
        require_command(status1, "LUNATIC STATUS: CLEAN", "status after init")

        sync = call_lunatic("sync", target)
        require_command(sync, "LUNATIC SYNC: PASS", "sync")
        require(file_hashes(target, runtime_targets) == hashes_after_init, "sync changed managed runtime bytes without source drift")
        require((target / "project-sentinel.txt").read_bytes() == sentinel, "sync changed project-owned sentinel")

        status2 = call_lunatic("status", target)
        require_command(status2, "LUNATIC STATUS: CLEAN", "status after sync")

        uninstall = call_lunatic("uninstall", target)
        require_command(uninstall, "LUNATIC UNINSTALL: PASS", "uninstall")
        final_snapshot = snapshot_files(target)
        require(final_snapshot == baseline, "target non-.git baseline was not restored after uninstall")
        require((target / "AGENTS.md").read_bytes() == original_agents, "original AGENTS.md was not byte-restored")
        require((target / "project-sentinel.txt").read_bytes() == sentinel, "project-owned sentinel was not byte-restored")
        require(not (target / INSTALL_MANIFEST).exists(), "install manifest remains after uninstall")

        return {
            "runtime_target_count": len(runtime_targets),
            "forbidden_installed_paths": len(forbidden),
        }


def main() -> int:
    source_status_before = ""
    try:
        source_commit = require_clean_public_source()
        source_status_before = git("status", "--porcelain", "--untracked-files=all")
        runtime_targets = validate_public_structure()
        result = lifecycle(runtime_targets)
        source_status_after = git("status", "--porcelain", "--untracked-files=all")
        require(source_status_after == source_status_before == "", "public source checkout changed during validation")
    except ValidationError as exc:
        print("LUNATIC PUBLIC PACKAGE VALIDATION: FAIL")
        print(f"- {exc}")
        print("public_repo_writes=0")
        print("model_calls=0")
        print("sol_calls=0")
        return 1

    print("LUNATIC PUBLIC PACKAGE VALIDATION: PASS")
    print(f"public_source_commit={source_commit}")
    print("public_source_isolated=PASS")
    print("public_source_clean=PASS")
    print("public_structural_validation=PASS")
    print(f"runtime_target_count={result['runtime_target_count']}")
    print("runtime_target_set_exact=PASS")
    print("init=PASS")
    print("status_after_init=PASS")
    print("sync=PASS")
    print("status_after_sync=PASS")
    print("uninstall=PASS")
    print("target_restored=PASS")
    print(f"forbidden_installed_paths={result['forbidden_installed_paths']}")
    print("public_source_unchanged=PASS")
    print("public_repo_writes=0")
    print("model_calls=0")
    print("sol_calls=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
