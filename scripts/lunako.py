#!/usr/bin/env python3
"""Canonical LUNAKO Harness lifecycle CLI with bounded N2 legacy migration."""
from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

from lunako_contract import MANIFEST_REL, ROLE_TARGET
from lunako_core import BINDING_BODY, ConfigPlan, LunakoError, SOURCE_ROOT, ensure_source_clean, expand_bundle, guarded_target_path, load_bundle, target_root
from lunako_ownership import (
    append_binding, binding_affixes, build_manifest, file_record_map,
    inspect_legacy_registration_region, inspect_registration_region,
    plan_new_registration, plan_replace_registration, preflight_new_paths,
    remove_binding, remove_legacy_binding, remove_registration_region,
    replace_binding, replace_legacy_binding, unlink_owned,
    validate_atomic_write_path, write_atomic,
)
from lunako_state import (
    CANONICAL, CONFLICT, NONE, SUPPORTED_LEGACY, Detection,
    LEGACY_INSTALL_ROOT, LEGACY_MANIFEST_REL, LEGACY_SKILL_DIR,
    detect_state,
)


@dataclass(frozen=True)
class _Node:
    rel: str
    kind: str
    data: bytes | None = None
    link_target: str | None = None
    mode: int | None = None


@dataclass(frozen=True)
class LegacyMigrationPlan:
    manifest: dict[str, Any]
    mappings: list[dict[str, str]]
    old_records: dict[str, dict[str, Any]]
    old_only: tuple[str, ...]
    new_agents: bytes
    config_plan: ConfigPlan
    canonical_manifest: dict[str, Any]


@dataclass(frozen=True)
class LegacyUninstallPlan:
    manifest: dict[str, Any]
    records: dict[str, dict[str, Any]]
    new_agents: bytes
    remove_agents: bool
    config_bytes: bytes | None
    remove_config: bool


class OperationSnapshot:
    def __init__(self, target: Path, file_rels: set[str]) -> None:
        self.target = target
        self.files: dict[str, _Node] = {}
        self.dirs: dict[str, _Node] = {}
        for rel in sorted(file_rels):
            self.files[rel] = self._capture(rel)
            parent = PurePosixPath(rel).parent
            while str(parent) not in {"", "."}:
                rel_parent = parent.as_posix()
                self.dirs.setdefault(rel_parent, self._capture(rel_parent))
                parent = parent.parent

    def _capture(self, rel: str) -> _Node:
        path = self.target / PurePosixPath(rel)
        try:
            st = path.lstat()
        except FileNotFoundError:
            return _Node(rel, "absent")
        mode = st.st_mode & 0o7777
        if path.is_symlink():
            return _Node(rel, "symlink", link_target=os.readlink(path), mode=mode)
        if path.is_file():
            return _Node(rel, "file", data=path.read_bytes(), mode=mode)
        if path.is_dir():
            return _Node(rel, "dir", mode=mode)
        return _Node(rel, "other", mode=mode)

    @staticmethod
    def _remove(path: Path) -> None:
        if path.is_symlink() or path.is_file():
            path.unlink()
        elif path.is_dir():
            path.rmdir()
        elif path.exists():
            raise OSError(f"unsupported rollback node: {path}")

    def _restore(self, node: _Node) -> None:
        path = self.target / PurePosixPath(node.rel)
        if node.kind == "absent":
            if path.exists() or path.is_symlink():
                self._remove(path)
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists() or path.is_symlink():
            self._remove(path)
        if node.kind == "file":
            tmp = path.with_name(path.name + ".lunako-rollback")
            if tmp.exists() or tmp.is_symlink():
                self._remove(tmp)
            tmp.write_bytes(node.data or b"")
            os.replace(tmp, path)
            if node.mode is not None:
                path.chmod(node.mode)
        elif node.kind == "symlink":
            os.symlink(node.link_target or "", path)
        elif node.kind == "dir":
            path.mkdir(parents=True, exist_ok=True)
            if node.mode is not None:
                path.chmod(node.mode)
        else:
            raise OSError(f"cannot restore unsupported node kind: {node.rel}")

    def restore_and_verify(self) -> None:
        for node in self.files.values():
            self._restore(node)
        for rel, node in sorted(self.dirs.items(), key=lambda item: item[0].count("/")):
            if node.kind == "dir":
                path = self.target / PurePosixPath(rel)
                if not path.exists():
                    path.mkdir(parents=True, exist_ok=True)
                if node.mode is not None:
                    path.chmod(node.mode)
        for rel, node in sorted(self.dirs.items(), key=lambda item: item[0].count("/"), reverse=True):
            if node.kind != "absent":
                continue
            path = self.target / PurePosixPath(rel)
            if path.is_dir() and not path.is_symlink():
                try:
                    path.rmdir()
                except OSError as exc:
                    raise OSError(f"rollback left created directory non-empty: {rel}") from exc
            elif path.exists() or path.is_symlink():
                raise OSError(f"rollback ancestor mismatch: {rel}")
        bad = [rel for rel, expected in self.files.items() if self._capture(rel) != expected]
        bad += [rel + "/" for rel, expected in self.dirs.items() if self._capture(rel) != expected]
        if bad:
            raise OSError("rollback verification failed for: " + ", ".join(sorted(bad)))


def _manifest_records(target: Path, manifest_rel: str) -> set[str]:
    path = target / PurePosixPath(manifest_rel)
    if not path.is_file():
        return set()
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return set()
    out: set[str] = set()
    for record in value.get("managed_files", []) if isinstance(value, dict) else []:
        if isinstance(record, dict) and isinstance(record.get("target_path"), str):
            out.add(record["target_path"])
    return out


def _transaction_paths(target: Path, bundle: dict[str, Any]) -> set[str]:
    rels = {"AGENTS.md", MANIFEST_REL, LEGACY_MANIFEST_REL, ROLE_TARGET}
    for mapping in expand_bundle(bundle):
        rels.add(mapping["target"])
    rels |= _manifest_records(target, MANIFEST_REL)
    rels |= _manifest_records(target, LEGACY_MANIFEST_REL)
    extras: set[str] = set()
    for rel in rels:
        p = PurePosixPath(rel)
        extras.add((p.parent / (p.name + ".lunako-tmp")).as_posix())
        extras.add((p.parent / (p.name + ".lunako-rollback")).as_posix())
    return rels | extras


def _run_transaction(operation: str, target: Path, bundle: dict[str, Any], fn: Any) -> int:
    try:
        snapshot = OperationSnapshot(target, _transaction_paths(target, bundle))
    except OSError as exc:
        raise LunakoError(f"{operation} transaction snapshot failed before mutation: {exc}") from exc
    try:
        return fn()
    except OSError as exc:
        try:
            snapshot.restore_and_verify()
        except OSError as rollback_exc:
            raise LunakoError(f"{operation} filesystem failure; rollback verification FAILED: {rollback_exc}") from rollback_exc
        raise LunakoError(f"{operation} filesystem failure; rollback=PASS; original_error={exc}") from exc


def _print_detection(prefix: str, detection: Detection) -> None:
    print(f"{prefix}: {detection.state}")
    print(f"state={detection.state}")
    print(f"subtype={detection.subtype}")
    for problem in detection.problems:
        print(f"- {problem}")


def command_status(target: Path, bundle: dict[str, Any]) -> int:
    detection = detect_state(target, bundle)
    _print_detection("LUNAKO STATUS", detection)
    if detection.state == CANONICAL:
        print("status=CLEAN")
        return 0
    if detection.state == NONE:
        print("status=NOT_INSTALLED")
        return 1
    return 2


def _command_init_mutate(target: Path, bundle: dict[str, Any]) -> int:
    mappings = expand_bundle(bundle)
    conflicts = preflight_new_paths(target, mappings)
    agents = guarded_target_path(target, "AGENTS.md", "AGENTS.md")
    agents_created = not agents.exists()
    if agents.exists() and not agents.is_file():
        conflicts.append("AGENTS.md: existing path is not a file")
        existing_agents = b""
    else:
        existing_agents = agents.read_bytes() if agents.is_file() else b""
    try:
        config_plan = plan_new_registration(target)
    except LunakoError as exc:
        conflicts.append(f"{ROLE_TARGET}: {exc}")
        config_plan = None
    if conflicts:
        print("LUNAKO INIT: CONFLICT")
        for item in conflicts:
            print(f"- {item}")
        print("no_changes=1")
        return 2
    assert config_plan is not None
    prefix, suffix = binding_affixes(existing_agents)
    for mapping in mappings:
        write_atomic(target, mapping["target"], (SOURCE_ROOT / mapping["source"]).read_bytes(), label="runtime target")
    write_atomic(target, "AGENTS.md", append_binding(existing_agents, prefix, suffix), label="AGENTS.md")
    write_atomic(target, ROLE_TARGET, config_plan.new_bytes, label="project role-registration target")
    manifest = build_manifest(bundle, mappings, agents_file_created=agents_created, prefix=prefix, suffix=suffix, config_plan=config_plan)
    write_atomic(target, MANIFEST_REL, (json.dumps(manifest, sort_keys=True, indent=2) + "\n").encode(), label="install manifest")
    print("LUNAKO INIT: PASS")
    print(f"managed_files={len(mappings)}")
    print("managed_regions=1")
    print(f"source_commit={manifest['source_commit']}")
    return 0


def command_init(target: Path, bundle: dict[str, Any]) -> int:
    ensure_source_clean()
    detection = detect_state(target, bundle)
    if detection.state == CANONICAL:
        print("LUNAKO INIT: ALREADY_INSTALLED")
        print("status=clean")
        return 0
    if detection.state == SUPPORTED_LEGACY:
        print("LUNAKO INIT: MIGRATION_REQUIRED")
        print(f"legacy_shape={detection.subtype}")
        print("no_changes=1")
        return 2
    if detection.state == CONFLICT:
        _print_detection("LUNAKO INIT: CONFLICT", detection)
        print("no_changes=1")
        return 2
    return _run_transaction("init", target, bundle, lambda: _command_init_mutate(target, bundle))


def _command_sync_mutate(target: Path, bundle: dict[str, Any], manifest: dict[str, Any]) -> int:
    mappings = expand_bundle(bundle)
    old = file_record_map(manifest)
    new = {item["target"]: item for item in mappings}
    conflicts: list[str] = []
    for rel in sorted(set(new) - set(old)):
        path = guarded_target_path(target, rel, "new runtime target")
        if path.exists() or path.is_symlink():
            conflicts.append(f"{rel}: pre-existing unowned path")
    state, region_problems = inspect_registration_region(target, manifest)
    conflicts.extend(region_problems)
    if conflicts or state is None:
        print("LUNAKO SYNC: CONFLICT")
        for item in conflicts or ["role-registration state unavailable"]:
            print(f"- {item}")
        print("no_changes=1")
        return 2
    config_plan = plan_replace_registration(state)
    for rel in sorted(set(old) - set(new), reverse=True):
        unlink_owned(target, rel, label="managed target")
    for rel, mapping in sorted(new.items()):
        write_atomic(target, rel, (SOURCE_ROOT / mapping["source"]).read_bytes(), label="runtime target")
    agents = guarded_target_path(target, "AGENTS.md", "AGENTS.md")
    write_atomic(target, "AGENTS.md", replace_binding(agents.read_bytes()), label="AGENTS.md")
    write_atomic(target, ROLE_TARGET, config_plan.new_bytes, label="project role-registration target")
    new_manifest = build_manifest(
        bundle, mappings,
        agents_file_created=bool(manifest.get("agents_file_created", False)),
        prefix=str(manifest.get("agents_binding_prefix", "")),
        suffix=str(manifest.get("agents_binding_suffix", "")),
        config_plan=config_plan,
    )
    write_atomic(target, MANIFEST_REL, (json.dumps(new_manifest, sort_keys=True, indent=2) + "\n").encode(), label="install manifest")
    print("LUNAKO SYNC: PASS")
    print(f"managed_files={len(mappings)}")
    print("managed_regions=1")
    print(f"source_commit={new_manifest['source_commit']}")
    return 0


def command_sync(target: Path, bundle: dict[str, Any]) -> int:
    ensure_source_clean()
    detection = detect_state(target, bundle)
    if detection.state == SUPPORTED_LEGACY:
        print("LUNAKO SYNC: MIGRATION_REQUIRED")
        print(f"legacy_shape={detection.subtype}")
        print("no_changes=1")
        return 2
    if detection.state == NONE:
        raise LunakoError("not installed; run init first")
    if detection.state == CONFLICT or detection.manifest is None:
        _print_detection("LUNAKO SYNC: CONFLICT", detection)
        print("no_changes=1")
        return 2
    return _run_transaction("sync", target, bundle, lambda: _command_sync_mutate(target, bundle, detection.manifest or {}))


def _command_uninstall_mutate(target: Path, manifest: dict[str, Any]) -> int:
    records = file_record_map(manifest)
    state, problems = inspect_registration_region(target, manifest)
    if problems or state is None:
        print("LUNAKO UNINSTALL: CONFLICT")
        for item in problems or ["role-registration state unavailable"]:
            print(f"- {item}")
        print("no_changes=1")
        return 2
    config_bytes, remove_config = remove_registration_region(state)
    for rel in sorted(records, reverse=True):
        unlink_owned(target, rel, label="managed target")
    agents = guarded_target_path(target, "AGENTS.md", "AGENTS.md")
    new_agents = remove_binding(agents.read_bytes(), manifest)
    if bool(manifest.get("agents_file_created", False)) and not new_agents.strip():
        unlink_owned(target, "AGENTS.md", label="AGENTS.md")
    else:
        write_atomic(target, "AGENTS.md", new_agents, label="AGENTS.md")
    config_path = guarded_target_path(target, ROLE_TARGET, "project role-registration target")
    if remove_config:
        unlink_owned(target, ROLE_TARGET, label="project role-registration target")
    else:
        write_atomic(target, ROLE_TARGET, config_bytes, label="project role-registration target")
    unlink_owned(target, MANIFEST_REL, label="install manifest")
    install_dir = guarded_target_path(target, ".lunako-harness", "install root")
    try:
        install_dir.rmdir()
    except OSError:
        pass
    print("LUNAKO UNINSTALL: PASS")
    print(f"removed_managed_files={len(records)}")
    return 0


def _preflight_known_paths(target: Path, rels: set[str], write_rels: set[str]) -> list[str]:
    problems: list[str] = []
    for rel in sorted(rels):
        try:
            guarded_target_path(target, rel, "legacy/canonical lifecycle target")
        except LunakoError as exc:
            problems.append(str(exc))
    for rel in sorted(write_rels):
        try:
            validate_atomic_write_path(target, rel, label="legacy/canonical lifecycle target")
        except LunakoError as exc:
            problems.append(str(exc))
    return problems


def _legacy_migration_plan(target: Path, bundle: dict[str, Any], detection: Detection) -> tuple[LegacyMigrationPlan | None, list[str]]:
    if detection.manifest is None:
        return None, ["supported legacy manifest unavailable"]
    manifest = detection.manifest
    mappings = expand_bundle(bundle)
    old_records = file_record_map(manifest)
    new_map = {item["target"]: item for item in mappings}
    old_targets = set(old_records)
    new_targets = set(new_map)
    conflicts: list[str] = []

    all_rels = old_targets | new_targets | {"AGENTS.md", ROLE_TARGET, LEGACY_MANIFEST_REL, MANIFEST_REL}
    write_rels = new_targets | {"AGENTS.md", ROLE_TARGET, MANIFEST_REL}
    conflicts.extend(_preflight_known_paths(target, all_rels, write_rels))

    for rel in sorted(new_targets - old_targets):
        try:
            path = guarded_target_path(target, rel, "new canonical managed target")
            if path.exists() or path.is_symlink():
                conflicts.append(f"{rel}: pre-existing unowned path blocks migration")
        except LunakoError as exc:
            conflicts.append(str(exc))

    agents = guarded_target_path(target, "AGENTS.md", "legacy AGENTS.md")
    try:
        if not agents.is_file():
            raise LunakoError("AGENTS.md legacy managed file missing")
        new_agents = replace_legacy_binding(agents.read_bytes())
    except LunakoError as exc:
        conflicts.append(str(exc))
        new_agents = b""

    schema = manifest.get("schema_version")
    config_plan: ConfigPlan | None = None
    try:
        if schema == 1:
            config_plan = plan_new_registration(target)
        elif schema == 2:
            legacy_state, region_problems = inspect_legacy_registration_region(target, manifest)
            if region_problems or legacy_state is None:
                conflicts.extend(region_problems or ["legacy registration state unavailable"])
            else:
                config_plan = plan_replace_registration(legacy_state)
        else:
            conflicts.append(f"unsupported legacy schema at migration boundary: {schema!r}")
    except LunakoError as exc:
        conflicts.append(f"{ROLE_TARGET}: {exc}")

    if conflicts or config_plan is None:
        return None, conflicts or ["canonical role-registration plan unavailable"]

    canonical_manifest = build_manifest(
        bundle,
        mappings,
        agents_file_created=bool(manifest.get("agents_file_created", False)),
        prefix=str(manifest.get("agents_binding_prefix", "")),
        suffix=str(manifest.get("agents_binding_suffix", "")),
        config_plan=config_plan,
    )
    return LegacyMigrationPlan(
        manifest=manifest,
        mappings=mappings,
        old_records=old_records,
        old_only=tuple(sorted(old_targets - new_targets, reverse=True)),
        new_agents=new_agents,
        config_plan=config_plan,
        canonical_manifest=canonical_manifest,
    ), []


def _cleanup_legacy_dirs(target: Path) -> None:
    for rel in (
        f"{LEGACY_SKILL_DIR}/references",
        f"{LEGACY_SKILL_DIR}/agents",
        LEGACY_SKILL_DIR,
        LEGACY_INSTALL_ROOT,
    ):
        path = guarded_target_path(target, rel, "legacy directory cleanup")
        if path.is_dir():
            path.rmdir()
        elif path.exists() or path.is_symlink():
            raise OSError(f"legacy cleanup path is not an owned directory: {rel}")


def _command_migrate_mutate(target: Path, plan: LegacyMigrationPlan) -> int:
    for mapping in plan.mappings:
        write_atomic(target, mapping["target"], (SOURCE_ROOT / mapping["source"]).read_bytes(), label="canonical runtime target")
    for rel in plan.old_only:
        unlink_owned(target, rel, label="legacy managed target")
    write_atomic(target, "AGENTS.md", plan.new_agents, label="AGENTS.md")
    write_atomic(target, ROLE_TARGET, plan.config_plan.new_bytes, label="project role-registration target")
    write_atomic(target, MANIFEST_REL, (json.dumps(plan.canonical_manifest, sort_keys=True, indent=2) + "\n").encode(), label="canonical install manifest")
    unlink_owned(target, LEGACY_MANIFEST_REL, label="legacy install manifest")
    _cleanup_legacy_dirs(target)
    print("LUNAKO MIGRATE: PASS")
    print("from_state=SUPPORTED_LEGACY")
    print("to_state=CANONICAL")
    print(f"managed_files={len(plan.mappings)}")
    return 0


def command_migrate(target: Path, bundle: dict[str, Any]) -> int:
    ensure_source_clean()
    detection = detect_state(target, bundle)
    if detection.state == CANONICAL:
        print("LUNAKO MIGRATE: ALREADY_CANONICAL")
        print("no_changes=1")
        return 0
    if detection.state == NONE:
        print("LUNAKO MIGRATE: NOT_INSTALLED")
        print("no_changes=1")
        return 1
    if detection.state == CONFLICT:
        _print_detection("LUNAKO MIGRATE: CONFLICT", detection)
        print("no_changes=1")
        return 2
    plan, problems = _legacy_migration_plan(target, bundle, detection)
    if plan is None:
        print("LUNAKO MIGRATE: MIGRATION_BLOCKED")
        print(f"legacy_shape={detection.subtype}")
        for problem in problems:
            print(f"- {problem}")
        print("no_changes=1")
        return 2
    return _run_transaction("migrate", target, bundle, lambda: _command_migrate_mutate(target, plan))


def _legacy_uninstall_plan(target: Path, detection: Detection) -> tuple[LegacyUninstallPlan | None, list[str]]:
    if detection.manifest is None:
        return None, ["supported legacy manifest unavailable"]
    manifest = detection.manifest
    records = file_record_map(manifest)
    problems = _preflight_known_paths(
        target,
        set(records) | {"AGENTS.md", ROLE_TARGET, LEGACY_MANIFEST_REL},
        {"AGENTS.md", ROLE_TARGET},
    )
    try:
        agents = guarded_target_path(target, "AGENTS.md", "legacy AGENTS.md")
        new_agents = remove_legacy_binding(agents.read_bytes(), manifest)
    except (LunakoError, OSError) as exc:
        problems.append(str(exc))
        new_agents = b""
    remove_agents = bool(manifest.get("agents_file_created", False)) and not new_agents.strip()

    config_bytes: bytes | None = None
    remove_config = False
    if manifest.get("schema_version") == 2:
        try:
            legacy_state, region_problems = inspect_legacy_registration_region(target, manifest)
            if region_problems or legacy_state is None:
                problems.extend(region_problems or ["legacy registration state unavailable"])
            else:
                config_bytes, remove_config = remove_registration_region(legacy_state)
        except LunakoError as exc:
            problems.append(str(exc))

    if problems:
        return None, problems
    return LegacyUninstallPlan(manifest, records, new_agents, remove_agents, config_bytes, remove_config), []


def _command_legacy_uninstall_mutate(target: Path, plan: LegacyUninstallPlan) -> int:
    for rel in sorted(plan.records, reverse=True):
        unlink_owned(target, rel, label="legacy managed target")
    if plan.remove_agents:
        unlink_owned(target, "AGENTS.md", label="legacy AGENTS.md")
    else:
        write_atomic(target, "AGENTS.md", plan.new_agents, label="legacy AGENTS.md")
    if plan.manifest.get("schema_version") == 2:
        if plan.remove_config:
            unlink_owned(target, ROLE_TARGET, label="legacy role-registration target")
        else:
            assert plan.config_bytes is not None
            write_atomic(target, ROLE_TARGET, plan.config_bytes, label="legacy role-registration target")
    unlink_owned(target, LEGACY_MANIFEST_REL, label="legacy install manifest")
    _cleanup_legacy_dirs(target)
    print("LUNAKO UNINSTALL: PASS")
    print("installation=SUPPORTED_LEGACY")
    print(f"removed_managed_files={len(plan.records)}")
    return 0


def command_uninstall(target: Path, bundle: dict[str, Any]) -> int:
    detection = detect_state(target, bundle)
    if detection.state == NONE:
        print("LUNAKO UNINSTALL: NOT_INSTALLED")
        return 0
    if detection.state == CONFLICT or detection.manifest is None:
        _print_detection("LUNAKO UNINSTALL: CONFLICT", detection)
        print("no_changes=1")
        return 2
    if detection.state == SUPPORTED_LEGACY:
        plan, problems = _legacy_uninstall_plan(target, detection)
        if plan is None:
            print("LUNAKO UNINSTALL: LEGACY_UNINSTALL_BLOCKED")
            for problem in problems:
                print(f"- {problem}")
            print("no_changes=1")
            return 2
        return _run_transaction("legacy-uninstall", target, bundle, lambda: _command_legacy_uninstall_mutate(target, plan))
    return _run_transaction("uninstall", target, bundle, lambda: _command_uninstall_mutate(target, detection.manifest or {}))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="lunako.py")
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("init", "status", "sync", "uninstall", "migrate"):
        cmd = sub.add_parser(name)
        cmd.add_argument("target")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        bundle = load_bundle()
        target = target_root(args.target)
        if args.command == "init":
            return command_init(target, bundle)
        if args.command == "status":
            return command_status(target, bundle)
        if args.command == "sync":
            return command_sync(target, bundle)
        if args.command == "uninstall":
            return command_uninstall(target, bundle)
        if args.command == "migrate":
            return command_migrate(target, bundle)
        raise LunakoError(f"unsupported command: {args.command}")
    except LunakoError as exc:
        print(f"LUNAKO ERROR: {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
