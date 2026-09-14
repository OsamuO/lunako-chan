#!/usr/bin/env python3
"""Model-free target repository installer/synchronizer for Lunatic Harnes."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import urlsplit, urlunsplit

SOURCE_ROOT = Path(__file__).resolve().parents[1]
BUNDLE_PATH = SOURCE_ROOT / "runtime/lunatic-runtime-bundle.json"
MANAGED_BEGIN = "<!-- LUNATIC-HARNES:BEGIN -->"
MANAGED_END = "<!-- LUNATIC-HARNES:END -->"

BINDING_BODY = """<!-- LUNATIC-HARNES:BEGIN -->
Lunatic Harnes runtime is installed for this repository.
Before non-trivial implementation, architecture, migration, or cross-boundary work, read `.agents/skills/luna-harness/SKILL.md` and follow it as Harness execution policy.
Treat this repository's own Rules / Task / State / Acceptance / Sources / Deliverables as project authority; installed Harness files are execution-policy/runtime assets, not project business/source authority.
Do not edit files owned by `.lunatic-harnes/install-manifest.json` during normal project work unless the task explicitly concerns Harness maintenance.
<!-- LUNATIC-HARNES:END -->"""


class LunaticError(RuntimeError):
    pass


def sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha_file(path: Path) -> str:
    return sha_bytes(path.read_bytes())


def run_git(args: list[str], cwd: Path, *, check: bool = True) -> subprocess.CompletedProcess[str]:
    p = subprocess.run(
        ["git", *args],
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if check and p.returncode != 0:
        raise LunaticError(f"git {' '.join(args)} failed: {p.stderr.strip() or p.stdout.strip()}")
    return p


def ensure_source_clean() -> None:
    p = run_git(["status", "--porcelain"], SOURCE_ROOT)
    if p.stdout.strip():
        raise LunaticError("source repository must be clean for init/sync")


def source_commit() -> str:
    return run_git(["rev-parse", "HEAD"], SOURCE_ROOT).stdout.strip()


def source_repo_id() -> str:
    p = run_git(["remote", "get-url", "origin"], SOURCE_ROOT, check=False)
    if p.returncode != 0 or not p.stdout.strip():
        return "local-checkout"

    raw = p.stdout.strip()
    if raw.startswith(("/", "./", "../", "file://")) or re.match(r"^[A-Za-z]:[\/]", raw):
        return "local-checkout"

    if "://" in raw:
        try:
            parsed = urlsplit(raw)
            if parsed.scheme not in {"http", "https", "ssh", "git"} or not parsed.hostname:
                return "local-checkout"
            host = parsed.hostname
            if ":" in host and not host.startswith("["):
                host = f"[{host}]"
            port = f":{parsed.port}" if parsed.port is not None else ""
            path = parsed.path or ""
            if not path:
                return "local-checkout"
            return urlunsplit((parsed.scheme, f"{host}{port}", path, "", ""))
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
        raise LunaticError(f"unsafe {label} path: {value}")
    return p


def target_root(path: str) -> Path:
    target = Path(path).expanduser().resolve()
    if not target.is_dir():
        raise LunaticError(f"target is not a directory: {target}")
    p = run_git(["rev-parse", "--show-toplevel"], target, check=False)
    if p.returncode != 0:
        raise LunaticError("target must be inside a Git repository")
    root = Path(p.stdout.strip()).resolve()
    if root != target:
        raise LunaticError(f"target must be the Git repository root: {root}")
    return root


def guarded_target_path(target: Path, rel_value: str, label: str) -> Path:
    rel = normalize_rel(rel_value, label)
    root = target.resolve()
    current = root
    parts = rel.parts
    for index, part in enumerate(parts):
        current = current / part
        if current.is_symlink():
            raise LunaticError(f"unsafe symlink in {label} path: {rel_value}")
        if index < len(parts) - 1 and current.exists() and not current.is_dir():
            raise LunaticError(f"non-directory component in {label} path: {rel_value}")
    try:
        resolved = current.resolve(strict=False)
    except OSError as exc:
        raise LunaticError(f"cannot resolve {label} path safely: {rel_value}: {exc}") from exc
    if resolved != root and root not in resolved.parents:
        raise LunaticError(f"{label} path escapes target repository: {rel_value}")
    return current


def install_manifest_rel(bundle: dict[str, Any]) -> str:
    return normalize_rel(str(bundle.get("install_manifest_path")), "install manifest").as_posix()


def load_bundle() -> dict[str, Any]:
    try:
        bundle = json.loads(BUNDLE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise LunaticError(f"invalid live runtime bundle: {exc}") from exc
    if bundle.get("schema_version") != 1:
        raise LunaticError("unsupported runtime bundle schema")
    if bundle.get("membership_policy") != "explicit-positive":
        raise LunaticError("live runtime bundle must declare explicit-positive membership")
    file_mappings = bundle.get("file_mappings")
    if not isinstance(file_mappings, list) or not file_mappings:
        raise LunaticError("live runtime bundle must contain explicit file_mappings")
    for item in file_mappings:
        if (
            not isinstance(item, dict)
            or not isinstance(item.get("source"), str)
            or not isinstance(item.get("target"), str)
        ):
            raise LunaticError("live runtime bundle contains an invalid explicit file mapping")
    if bundle.get("directory_mappings"):
        raise LunaticError("live runtime bundle must not use broad directory_mappings")
    return bundle


def forbidden(source_rel: str, prefixes: list[str]) -> bool:
    normalized = source_rel.replace("\\", "/")
    return any(normalized.startswith(prefix) for prefix in prefixes)


def tracked_files_under(source_dir: str) -> list[str]:
    p = run_git(["ls-files", "--", source_dir], SOURCE_ROOT)
    return [line.strip() for line in p.stdout.splitlines() if line.strip()]


def expand_bundle(bundle: dict[str, Any]) -> list[dict[str, str]]:
    forbidden_prefixes = [str(x) for x in bundle.get("forbidden_source_prefixes", [])]
    out: list[dict[str, str]] = []

    def add(source_rel: str, target_rel: str) -> None:
        normalize_rel(source_rel, "source")
        normalize_rel(target_rel, "target")
        if forbidden(source_rel, forbidden_prefixes):
            raise LunaticError(f"forbidden runtime source path: {source_rel}")
        src = SOURCE_ROOT / source_rel
        if not src.is_file():
            raise LunaticError(f"runtime source file missing: {source_rel}")
        out.append({"source": source_rel, "target": target_rel})

    for item in bundle.get("file_mappings", []):
        add(str(item["source"]), str(item["target"]))

    for item in bundle.get("directory_mappings", []):
        source_dir = str(item["source"]).rstrip("/")
        target_dir = str(item["target"]).rstrip("/")
        excludes = {str(x) for x in item.get("exclude", [])}
        source_base = PurePosixPath(source_dir)
        for source_rel in tracked_files_under(source_dir):
            rel = PurePosixPath(source_rel).relative_to(source_base).as_posix()
            if rel in excludes or PurePosixPath(rel).name in excludes:
                continue
            add(source_rel, (PurePosixPath(target_dir) / rel).as_posix())

    seen: dict[str, str] = {}
    for item in out:
        old = seen.get(item["target"])
        if old is not None and old != item["source"]:
            raise LunaticError(f"duplicate runtime target: {item['target']}")
        seen[item["target"]] = item["source"]
    return sorted(out, key=lambda x: x["target"])


def expected_block(bundle: dict[str, Any]) -> str:
    cfg = bundle.get("root_agents_binding", {})
    if cfg.get("begin_marker") != MANAGED_BEGIN or cfg.get("end_marker") != MANAGED_END:
        raise LunaticError("runtime bundle AGENTS markers do not match installer")
    skill_path = str(cfg.get("skill_path", ""))
    if skill_path != ".agents/skills/luna-harness/SKILL.md":
        raise LunaticError("unsupported Harness skill path")
    return BINDING_BODY


def find_block(text: str) -> tuple[int, int] | None:
    starts = []
    pos = 0
    while True:
        idx = text.find(MANAGED_BEGIN, pos)
        if idx < 0:
            break
        starts.append(idx)
        pos = idx + len(MANAGED_BEGIN)
    ends = []
    pos = 0
    while True:
        idx = text.find(MANAGED_END, pos)
        if idx < 0:
            break
        ends.append(idx)
        pos = idx + len(MANAGED_END)
    if not starts and not ends:
        return None
    if len(starts) != 1 or len(ends) != 1 or ends[0] < starts[0]:
        raise LunaticError("AGENTS.md contains malformed or duplicate Lunatic Harnes managed markers")
    return starts[0], ends[0] + len(MANAGED_END)


def binding_affixes(existing: bytes) -> tuple[str, str]:
    text = existing.decode("utf-8")
    if not text:
        return "", "\n"
    prefix = "" if text.endswith("\n\n") else ("\n" if text.endswith("\n") else "\n\n")
    return prefix, "\n"


def append_block(existing: bytes, block: str, prefix: str, suffix: str) -> bytes:
    text = existing.decode("utf-8")
    if find_block(text) is not None:
        raise LunaticError("AGENTS.md already contains a Lunatic Harnes managed block without an install manifest")
    return (text + prefix + block + suffix).encode()


def block_bytes_from_agents(path: Path) -> bytes:
    if not path.is_file():
        raise LunaticError("AGENTS.md is missing")
    text = path.read_text(encoding="utf-8")
    span = find_block(text)
    if span is None:
        raise LunaticError("AGENTS.md managed block is missing")
    return text[span[0]:span[1]].encode()


def replace_block(existing: bytes, block: str) -> bytes:
    text = existing.decode("utf-8")
    span = find_block(text)
    if span is None:
        raise LunaticError("AGENTS.md managed block is missing")
    return (text[:span[0]] + block + text[span[1]:]).encode()


def binding_segment_bytes(path: Path, manifest: dict[str, Any]) -> bytes:
    if not path.is_file():
        raise LunaticError("AGENTS.md is missing")
    text = path.read_text(encoding="utf-8")
    span = find_block(text)
    if span is None:
        raise LunaticError("AGENTS.md managed block is missing")
    prefix = str(manifest.get("agents_binding_prefix", ""))
    suffix = str(manifest.get("agents_binding_suffix", ""))
    start, end = span
    if prefix:
        if start < len(prefix) or text[start - len(prefix):start] != prefix:
            raise LunaticError("AGENTS.md managed binding prefix modified")
        start -= len(prefix)
    if suffix:
        if text[end:end + len(suffix)] != suffix:
            raise LunaticError("AGENTS.md managed binding suffix modified")
        end += len(suffix)
    return text[start:end].encode()


def remove_binding(existing: bytes, manifest: dict[str, Any]) -> bytes:
    text = existing.decode("utf-8")
    span = find_block(text)
    if span is None:
        raise LunaticError("AGENTS.md managed block is missing")
    prefix = str(manifest.get("agents_binding_prefix", ""))
    suffix = str(manifest.get("agents_binding_suffix", ""))
    start, end = span
    if prefix:
        if start < len(prefix) or text[start - len(prefix):start] != prefix:
            raise LunaticError("AGENTS.md managed binding prefix modified")
        start -= len(prefix)
    if suffix:
        if text[end:end + len(suffix)] != suffix:
            raise LunaticError("AGENTS.md managed binding suffix modified")
        end += len(suffix)
    return (text[:start] + text[end:]).encode()


def manifest_path(target: Path, bundle: dict[str, Any]) -> Path:
    return guarded_target_path(target, install_manifest_rel(bundle), "install manifest")


def read_manifest(target: Path, bundle: dict[str, Any]) -> dict[str, Any] | None:
    path = manifest_path(target, bundle)
    if not path.is_file():
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise LunaticError(f"invalid install manifest: {exc}") from exc
    if value.get("schema_version") != 1:
        raise LunaticError("unsupported install manifest schema")
    return value


def file_record_map(manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for item in manifest.get("managed_files", []):
        target_path = str(item.get("target_path", ""))
        normalize_rel(target_path, "managed target")
        if target_path in out:
            raise LunaticError(f"duplicate managed target in install manifest: {target_path}")
        out[target_path] = item
    return out


def write_atomic(target: Path, rel_value: str, data: bytes, *, label: str = "managed target") -> None:
    path = guarded_target_path(target, rel_value, label)
    path.parent.mkdir(parents=True, exist_ok=True)
    path = guarded_target_path(target, rel_value, label)
    tmp = path.with_name(path.name + ".lunatic-tmp")
    if tmp.exists() or tmp.is_symlink():
        raise LunaticError(f"temporary write path already exists: {tmp.name}")
    tmp.write_bytes(data)
    if path.is_symlink():
        tmp.unlink(missing_ok=True)
        raise LunaticError(f"unsafe symlink in {label} path: {rel_value}")
    os.replace(tmp, path)


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def build_install_manifest(
    bundle: dict[str, Any],
    mappings: list[dict[str, str]],
    block: str,
    *,
    agents_file_created: bool,
    agents_binding_prefix: str,
    agents_binding_suffix: str,
) -> dict[str, Any]:
    managed = []
    for m in mappings:
        data = (SOURCE_ROOT / m["source"]).read_bytes()
        managed.append({
            "source_path": m["source"],
            "target_path": m["target"],
            "installed_sha256": sha_bytes(data),
        })
    return {
        "schema_version": 1,
        "source_repo": source_repo_id(),
        "source_commit": source_commit(),
        "bundle_name": bundle.get("bundle_name"),
        "bundle_version": bundle.get("bundle_version"),
        "managed_files": managed,
        "managed_agents_block_sha256": sha_bytes(block.encode()),
        "managed_agents_segment_sha256": sha_bytes(
            (agents_binding_prefix + block + agents_binding_suffix).encode()
        ),
        "agents_binding_prefix": agents_binding_prefix,
        "agents_binding_suffix": agents_binding_suffix,
        "agents_file_created": agents_file_created,
        "installed_at": now_utc(),
    }


def preflight_new_paths(target: Path, mappings: list[dict[str, str]]) -> list[str]:
    conflicts: list[str] = []
    for m in mappings:
        try:
            dst = guarded_target_path(target, m["target"], "runtime target")
        except LunaticError as exc:
            conflicts.append(f"{m['target']}: {exc}")
            continue
        if dst.exists() or dst.is_symlink():
            conflicts.append(f"{m['target']}: pre-existing unowned path")
    return conflicts


def command_init(target: Path, bundle: dict[str, Any]) -> int:
    ensure_source_clean()
    existing_manifest = read_manifest(target, bundle)
    if existing_manifest is not None:
        rc = status_impl(target, bundle, existing_manifest, quiet=True)
        if rc == 0:
            print("LUNATIC INIT: ALREADY_INSTALLED")
            print("status=clean")
            return 0
        raise LunaticError("installation already exists but is not clean; run status")

    mappings = expand_bundle(bundle)
    conflicts = preflight_new_paths(target, mappings)

    agents = guarded_target_path(target, "AGENTS.md", "AGENTS.md")
    agents_created = not agents.exists()
    if agents.exists() and not agents.is_file():
        conflicts.append("AGENTS.md: existing path is not a file")
    else:
        existing_agents = agents.read_bytes() if agents.is_file() else b""
        try:
            if find_block(existing_agents.decode("utf-8")) is not None:
                conflicts.append("AGENTS.md: existing unmanaged Lunatic Harnes block")
        except (UnicodeDecodeError, LunaticError) as exc:
            conflicts.append(f"AGENTS.md: {exc}")

    if conflicts:
        print("LUNATIC INIT: CONFLICT")
        for item in conflicts:
            print(f"- {item}")
        return 2

    block = expected_block(bundle)
    existing_agents = agents.read_bytes() if agents.is_file() else b""
    prefix, suffix = binding_affixes(existing_agents)
    for m in mappings:
        write_atomic(
            target,
            m["target"],
            (SOURCE_ROOT / m["source"]).read_bytes(),
            label="runtime target",
        )

    write_atomic(
        target,
        "AGENTS.md",
        append_block(existing_agents, block, prefix, suffix),
        label="AGENTS.md",
    )

    manifest = build_install_manifest(
        bundle,
        mappings,
        block,
        agents_file_created=agents_created,
        agents_binding_prefix=prefix,
        agents_binding_suffix=suffix,
    )
    write_atomic(
        target,
        install_manifest_rel(bundle),
        (json.dumps(manifest, sort_keys=True, indent=2) + "\n").encode(),
        label="install manifest",
    )

    print("LUNATIC INIT: PASS")
    print(f"managed_files={len(mappings)}")
    print(f"source_commit={manifest['source_commit']}")
    print("model_calls=0")
    print("sol_calls=0")
    return 0


def status_impl(target: Path, bundle: dict[str, Any], manifest: dict[str, Any], *, quiet: bool = False) -> int:
    problems: list[str] = []
    records = file_record_map(manifest)
    for rel, record in sorted(records.items()):
        path = guarded_target_path(target, rel, "managed target")
        expected = str(record.get("installed_sha256", ""))
        if not path.is_file():
            problems.append(f"{rel}: missing")
        elif sha_file(path) != expected:
            problems.append(f"{rel}: modified")

    agents = guarded_target_path(target, "AGENTS.md", "AGENTS.md")
    try:
        block = block_bytes_from_agents(agents)
        if sha_bytes(block) != str(manifest.get("managed_agents_block_sha256", "")):
            problems.append("AGENTS.md: managed block modified")
        segment = binding_segment_bytes(agents, manifest)
        if sha_bytes(segment) != str(manifest.get("managed_agents_segment_sha256", "")):
            problems.append("AGENTS.md: managed binding segment modified")
    except LunaticError as exc:
        problems.append(str(exc))

    if not quiet:
        print(f"LUNATIC STATUS: {'CLEAN' if not problems else 'DRIFT'}")
        print(f"managed_files={len(records)}")
        if problems:
            for item in problems:
                print(f"- {item}")
    return 0 if not problems else 1


def command_status(target: Path, bundle: dict[str, Any]) -> int:
    manifest = read_manifest(target, bundle)
    if manifest is None:
        print("LUNATIC STATUS: NOT_INSTALLED")
        return 1
    return status_impl(target, bundle, manifest)


def current_block_matches(target: Path, manifest: dict[str, Any]) -> bool:
    try:
        agents = guarded_target_path(target, "AGENTS.md", "AGENTS.md")
        block_ok = sha_bytes(block_bytes_from_agents(agents)) == str(
            manifest.get("managed_agents_block_sha256", "")
        )
        segment_ok = sha_bytes(binding_segment_bytes(agents, manifest)) == str(
            manifest.get("managed_agents_segment_sha256", "")
        )
        return block_ok and segment_ok
    except LunaticError:
        return False


def command_sync(target: Path, bundle: dict[str, Any]) -> int:
    ensure_source_clean()
    manifest = read_manifest(target, bundle)
    if manifest is None:
        raise LunaticError("not installed; run init first")

    old = file_record_map(manifest)
    mappings = expand_bundle(bundle)
    new_by_target = {m["target"]: m for m in mappings}
    conflicts: list[str] = []

    for rel, record in old.items():
        path = guarded_target_path(target, rel, "managed target")
        if not path.is_file():
            conflicts.append(f"{rel}: managed file missing")
        elif sha_file(path) != str(record.get("installed_sha256", "")):
            conflicts.append(f"{rel}: managed file modified")

    if not current_block_matches(target, manifest):
        conflicts.append("AGENTS.md: managed block/binding missing or modified")

    for rel in new_by_target:
        if rel in old:
            continue
        path = guarded_target_path(target, rel, "new runtime target")
        if path.exists() or path.is_symlink():
            conflicts.append(f"{rel}: pre-existing unowned path")

    if conflicts:
        print("LUNATIC SYNC: CONFLICT")
        for item in conflicts:
            print(f"- {item}")
        return 2

    for rel in sorted(set(old) - set(new_by_target)):
        guarded_target_path(target, rel, "managed target").unlink()

    for rel, mapping in sorted(new_by_target.items()):
        write_atomic(
            target,
            rel,
            (SOURCE_ROOT / mapping["source"]).read_bytes(),
            label="runtime target",
        )

    block = expected_block(bundle)
    agents = guarded_target_path(target, "AGENTS.md", "AGENTS.md")
    write_atomic(
        target,
        "AGENTS.md",
        replace_block(agents.read_bytes(), block),
        label="AGENTS.md",
    )

    new_manifest = build_install_manifest(
        bundle,
        mappings,
        block,
        agents_file_created=bool(manifest.get("agents_file_created", False)),
        agents_binding_prefix=str(manifest.get("agents_binding_prefix", "")),
        agents_binding_suffix=str(manifest.get("agents_binding_suffix", "")),
    )
    write_atomic(
        target,
        install_manifest_rel(bundle),
        (json.dumps(new_manifest, sort_keys=True, indent=2) + "\n").encode(),
        label="install manifest",
    )

    print("LUNATIC SYNC: PASS")
    print(f"managed_files={len(mappings)}")
    print(f"source_commit={new_manifest['source_commit']}")
    print("model_calls=0")
    print("sol_calls=0")
    return 0


def command_uninstall(target: Path, bundle: dict[str, Any]) -> int:
    manifest = read_manifest(target, bundle)
    if manifest is None:
        print("LUNATIC UNINSTALL: NOT_INSTALLED")
        return 0

    records = file_record_map(manifest)
    conflicts: list[str] = []
    for rel, record in records.items():
        path = guarded_target_path(target, rel, "managed target")
        if not path.is_file():
            conflicts.append(f"{rel}: managed file missing")
        elif sha_file(path) != str(record.get("installed_sha256", "")):
            conflicts.append(f"{rel}: managed file modified")

    if not current_block_matches(target, manifest):
        conflicts.append("AGENTS.md: managed block/binding missing or modified")

    if conflicts:
        print("LUNATIC UNINSTALL: CONFLICT")
        for item in conflicts:
            print(f"- {item}")
        print("no_changes=1")
        return 2

    for rel in sorted(records, reverse=True):
        guarded_target_path(target, rel, "managed target").unlink()

    agents = guarded_target_path(target, "AGENTS.md", "AGENTS.md")
    new_agents = remove_binding(agents.read_bytes(), manifest)
    if bool(manifest.get("agents_file_created", False)) and not new_agents.strip():
        guarded_target_path(target, "AGENTS.md", "AGENTS.md").unlink()
    else:
        write_atomic(target, "AGENTS.md", new_agents, label="AGENTS.md")

    manifest_path(target, bundle).unlink()
    own_dir = guarded_target_path(
        target, ".lunatic-harnes", "install manifest directory"
    )
    try:
        own_dir.rmdir()
    except OSError:
        pass

    print("LUNATIC UNINSTALL: PASS")
    print(f"removed_managed_files={len(records)}")
    print("model_calls=0")
    print("sol_calls=0")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="lunatic.py")
    sub = p.add_subparsers(dest="command", required=True)
    for name in ("init", "status", "sync", "uninstall"):
        sp = sub.add_parser(name)
        sp.add_argument("target")
    return p


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
        raise LunaticError(f"unsupported command: {args.command}")
    except LunaticError as exc:
        print(f"LUNATIC ERROR: {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
