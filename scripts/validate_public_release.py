#!/usr/bin/env python3
"""Model-free standalone validator for the projected LUNAKO Harness package.

Run this from a clean projected/public Git checkout. The validator uses only
files in that checkout plus normal system Python/Git.
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
RUNTIME_MANIFEST = ROOT / "runtime/lunako-runtime-bundle.json"
LUNAKO = ROOT / "scripts/lunako.py"
DOCTOR = ROOT / "scripts/lunako_doctor.py"
HELPER = ROOT / "scripts/lunako_permission_profile.py"
PRODUCT_ID = "lunako-harness"
NAMESPACE_VERSION = 1
MANIFEST_SCHEMA = 3
RUNTIME_SCHEMA = 3
EXPECTED_RUNTIME_COUNT = 50
INSTALL_MANIFEST = ".lunako-harness/install-manifest.json"
AGENTS_BEGIN = "<!-- LUNAKO-HARNESS:BEGIN -->"
AGENTS_END = "<!-- LUNAKO-HARNESS:END -->"
ROLE_BEGIN = "# LUNAKO-HARNESS:BEGIN PROJECT-ROLE-REGISTRATION"
ROLE_END = "# LUNAKO-HARNESS:END PROJECT-ROLE-REGISTRATION"

REQUIRED_FILES = (
    "README.md",
    "README.ja.md",
    "LICENSE",
    ".gitignore",
    "runtime/lunako-runtime-bundle.json",
    "scripts/lunako.py",
    "scripts/lunako_core.py",
    "scripts/lunako_ownership.py",
    "scripts/lunako_state.py",
    "scripts/lunako_legacy_frozen.py",
    "scripts/lunako_contract.py",
    "scripts/lunako_diagnostics.py",
    "scripts/lunako_doctor.py",
    "scripts/lunako_permission_profile.py",
    "scripts/validate_public_release.py",
    ".agents/project-interface/SPECIFICATION.md",
    ".agents/skills/lunako-harness/SKILL.md",
    ".agents/schemas/routing-decision.schema.json",
    ".codex/agents/luna-worker.toml",
    "docs/VALIDATION.md",
    "docs/MIGRATION.md",
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
    proc = subprocess.run(cmd, cwd=cwd, env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False)
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
    require(Path(top).resolve() == ROOT.resolve(), "validator must run from the projected/public package Git root")
    commit = git("rev-parse", "HEAD")
    require(git("status", "--porcelain", "--untracked-files=all") == "", "public source checkout must be clean")
    return commit


def load_runtime_targets() -> set[str]:
    try:
        runtime = json.loads(RUNTIME_MANIFEST.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValidationError(f"runtime inventory parse failed: {exc}") from exc
    require(isinstance(runtime, dict), "runtime inventory must be a JSON object")
    require(runtime.get("schema_version") == RUNTIME_SCHEMA, "runtime inventory schema mismatch")
    require(runtime.get("bundle_name") == "lunako-harness-runtime", "runtime bundle identity mismatch")
    require(runtime.get("product_id") == PRODUCT_ID, "runtime product_id mismatch")
    require(runtime.get("namespace_version") == NAMESPACE_VERSION, "runtime namespace_version mismatch")
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
        require((ROOT / source).is_file(), f"runtime source missing from standalone package: {source}")
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


def validate_dependency_closure() -> None:
    for script, label in ((LUNAKO, "lunako CLI"), (DOCTOR, "doctor"), (HELPER, "permission helper")):
        proc = run([sys.executable, str(script), "--help"], cwd=ROOT)
        require(proc.returncode == 0, f"{label} import/start closure failed: {proc.stdout.strip()}")


def snapshot_files(root: Path) -> dict[str, bytes]:
    out: dict[str, bytes] = {}
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(root).as_posix()
        if rel.startswith(".git/"):
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
    require(value.get("schema_version") == MANIFEST_SCHEMA, "canonical manifest schema mismatch")
    require(value.get("product_id") == PRODUCT_ID, "canonical manifest product_id mismatch")
    require(value.get("namespace_version") == NAMESPACE_VERSION, "canonical manifest namespace_version mismatch")
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


def call_lunako(command: str, target: Path) -> subprocess.CompletedProcess[str]:
    return run([sys.executable, str(LUNAKO), command, str(target)], cwd=ROOT)


def require_command(proc: subprocess.CompletedProcess[str], marker: str, label: str) -> None:
    require(proc.returncode == 0, f"{label} failed ({proc.returncode}): {proc.stdout.strip()}")
    require(marker in proc.stdout, f"{label} missing marker {marker!r}: {proc.stdout.strip()}")


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
    with tempfile.TemporaryDirectory(prefix="lunako-public-target-") as tmp:
        target = Path(tmp) / "ordinary-project"
        target.mkdir()
        git("init", "-q", cwd=target)
        git("config", "user.name", "Package Validator", cwd=target)
        git("config", "user.email", "validator@example.invalid", cwd=target)

        original_agents = b"# Ordinary Project Rules\n\nKeep project-owned rules intact.\n"
        original_config = b"# ordinary user config\n[features]\nexample = true\n"
        sentinel = b"ordinary-target-sentinel\n"
        user_keep = b"keep-user-content\n"
        (target / "AGENTS.md").write_bytes(original_agents)
        (target / ".codex").mkdir()
        (target / ".codex/config.toml").write_bytes(original_config)
        (target / ".agents/user-content").mkdir(parents=True)
        (target / ".agents/user-content/keep.txt").write_bytes(user_keep)
        (target / "project-sentinel.txt").write_bytes(sentinel)
        git("add", "-A", cwd=target)
        git("commit", "-q", "-m", "ordinary target baseline", cwd=target)
        baseline = snapshot_files(target)

        init = call_lunako("init", target)
        require_command(init, "LUNAKO INIT: PASS", "init")
        install_manifest = parse_install_manifest(target)
        installed_managed = managed_target_set(install_manifest)
        require(installed_managed == runtime_targets, "installed managed target set differs from packaged runtime target set")

        after_init = snapshot_files(target)
        new_paths = set(after_init) - set(baseline)
        expected_new = set(runtime_targets) | {INSTALL_MANIFEST}
        require(new_paths == expected_new, f"init created unexpected/missing files: extra={sorted(new_paths - expected_new)} missing={sorted(expected_new - new_paths)}")

        agents_text = (target / "AGENTS.md").read_text(encoding="utf-8")
        config_text = (target / ".codex/config.toml").read_text(encoding="utf-8")
        require(agents_text.count(AGENTS_BEGIN) == 1 and agents_text.count(AGENTS_END) == 1, "canonical AGENTS marker count must be one")
        require(config_text.count(ROLE_BEGIN) == 1 and config_text.count(ROLE_END) == 1, "canonical role-registration marker count must be one")
        require("# Ordinary Project Rules" in agents_text, "project-owned AGENTS bytes missing while installed")
        require("# ordinary user config" in config_text and "example = true" in config_text, "project-owned config bytes missing while installed")
        require((target / "project-sentinel.txt").read_bytes() == sentinel, "init changed project sentinel")
        require((target / ".agents/user-content/keep.txt").read_bytes() == user_keep, "init changed unrelated user content")

        forbidden = forbidden_target_paths(target)
        require(not forbidden, f"forbidden development paths installed: {forbidden}")
        hashes_after_init = file_hashes(target, runtime_targets)

        helper = run([sys.executable, str(HELPER), "--target", str(target), "--write-scope", ".agents/user-content"], cwd=ROOT)
        require(helper.returncode == 0, f"permission helper failed on clean canonical install: {helper.stdout.strip()}")
        try:
            helper_json = json.loads(helper.stdout)
        except json.JSONDecodeError as exc:
            raise ValidationError(f"permission helper output is not JSON: {exc}") from exc
        require(helper_json.get("product_id") == PRODUCT_ID and helper_json.get("namespace_version") == NAMESPACE_VERSION, "permission helper canonical identity mismatch")

        status1 = call_lunako("status", target)
        require_command(status1, "LUNAKO STATUS: CANONICAL", "status after init")
        require("status=CLEAN" in status1.stdout, "status after init is not CLEAN")

        sync = call_lunako("sync", target)
        require_command(sync, "LUNAKO SYNC: PASS", "sync")
        require(file_hashes(target, runtime_targets) == hashes_after_init, "sync changed runtime bytes without source drift")
        require((target / "project-sentinel.txt").read_bytes() == sentinel, "sync changed project sentinel")

        status2 = call_lunako("status", target)
        require_command(status2, "LUNAKO STATUS: CANONICAL", "status after sync")
        require("status=CLEAN" in status2.stdout, "status after sync is not CLEAN")

        uninstall = call_lunako("uninstall", target)
        require_command(uninstall, "LUNAKO UNINSTALL: PASS", "uninstall")
        final_snapshot = snapshot_files(target)
        require(final_snapshot == baseline, "target non-.git baseline was not restored after uninstall")
        require((target / "AGENTS.md").read_bytes() == original_agents, "original AGENTS.md bytes were not restored")
        require((target / ".codex/config.toml").read_bytes() == original_config, "original .codex/config.toml bytes were not restored")
        require((target / "project-sentinel.txt").read_bytes() == sentinel, "project-owned sentinel was not restored")
        require((target / ".agents/user-content/keep.txt").read_bytes() == user_keep, "unrelated user content was not restored")
        require(not (target / INSTALL_MANIFEST).exists(), "install manifest remains after uninstall")

        return {"runtime_target_count": len(runtime_targets), "forbidden_installed_paths": len(forbidden)}


def main() -> int:
    source_status_before = ""
    try:
        source_commit = require_clean_public_source()
        source_status_before = git("status", "--porcelain", "--untracked-files=all")
        runtime_targets = validate_public_structure()
        validate_dependency_closure()
        result = lifecycle(runtime_targets)
        source_status_after = git("status", "--porcelain", "--untracked-files=all")
        require(source_status_after == source_status_before == "", "public source checkout changed during validation")
    except ValidationError as exc:
        print("LUNAKO PUBLIC PACKAGE VALIDATION: FAIL")
        print(f"- {exc}")
        print("public_repo_writes=0")
        print("model_calls=0")
        print("sol_calls=0")
        return 1

    print("LUNAKO PUBLIC PACKAGE VALIDATION: PASS")
    print(f"public_source_commit={source_commit}")
    print("public_source_isolated=PASS")
    print("public_source_clean=PASS")
    print("public_structural_validation=PASS")
    print("cli_dependency_closure=PASS")
    print("doctor_dependency_closure=PASS")
    print("permission_helper_dependency_closure=PASS")
    print(f"runtime_target_count={result['runtime_target_count']}")
    print("runtime_target_set_exact=PASS")
    print("canonical_manifest_v3_identity=PASS")
    print("canonical_agents_marker_once=PASS")
    print("canonical_role_region_once=PASS")
    print("init=PASS")
    print("status_after_init=PASS")
    print("sync=PASS")
    print("status_after_sync=PASS")
    print("uninstall=PASS")
    print("tested_user_bytes_preserved=PASS")
    print("target_baseline_restored=PASS")
    print(f"forbidden_installed_paths={result['forbidden_installed_paths']}")
    print("public_source_unchanged=PASS")
    print("public_repo_writes=0")
    print("model_calls=0")
    print("sol_calls=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
