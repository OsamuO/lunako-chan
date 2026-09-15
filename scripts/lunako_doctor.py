#!/usr/bin/env python3
"""Fail-closed Codex runtime-readiness and installation doctor for LUNAKO."""
from __future__ import annotations

import argparse
import json
import os
import select
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from lunako_contract import EXPECTED_REGISTRATIONS
from lunako_core import load_bundle, target_root
from lunako_diagnostics import conflict_diagnostics
from lunako_state import CANONICAL, CONFLICT, detect_state

TESTED_CODEX_VERSION = "codex-cli 0.152.0"
NATIVE_AUTHORITY = "codex app-server config/read(includeLayers=true)"
TESTED_RUNTIME_PROFILE_LIMITATION = "subagent_permission_profile_inherits_parent_turn"
READY = "READY"
BLOCKED_PROJECT_CONFIG_INACTIVE = "BLOCKED_PROJECT_CONFIG_INACTIVE"
BLOCKED_ROLE_REGISTRATION = "BLOCKED_ROLE_REGISTRATION"
BLOCKED_MULTI_AGENT_DISABLED = "BLOCKED_MULTI_AGENT_DISABLED"
UNKNOWN = "UNKNOWN"

class DoctorError(RuntimeError):
    pass


def _codex_version(codex_bin: str) -> tuple[str | None, str | None]:
    try:
        proc = subprocess.run([codex_bin, "--version"], text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False, timeout=8)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return None, str(exc)
    if proc.returncode != 0:
        return None, proc.stdout.strip() or f"codex --version exited {proc.returncode}"
    return proc.stdout.strip(), None


def _config_read(target: Path, codex_bin: str) -> tuple[dict[str, Any] | None, str | None]:
    try:
        proc = subprocess.Popen([codex_bin, "app-server", "--stdio"], cwd=target, env=os.environ.copy(), stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1)
    except OSError as exc:
        return None, f"app_server_start_failed: {exc}"
    assert proc.stdin and proc.stdout

    def send(obj: dict[str, Any]) -> None:
        proc.stdin.write(json.dumps(obj) + "\n")
        proc.stdin.flush()

    def wait_id(want: int, timeout: float = 8.0) -> dict[str, Any] | None:
        end = time.time() + timeout
        while time.time() < end:
            try:
                ready, _, _ = select.select([proc.stdout], [], [], max(0.0, end - time.time()))
            except (OSError, ValueError):
                return None
            if not ready:
                return None
            line = proc.stdout.readline()
            if not line:
                return None
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if obj.get("id") == want:
                return obj
        return None

    try:
        send({"jsonrpc":"2.0","id":1,"method":"initialize","params":{"clientInfo":{"name":"lunako-doctor","version":"1"},"capabilities":{"experimentalApi":True}}})
        init = wait_id(1)
        if not init or "result" not in init:
            return None, "initialize_failed"
        send({"jsonrpc":"2.0","method":"initialized","params":{}})
        send({"jsonrpc":"2.0","id":2,"method":"config/read","params":{"cwd":str(target),"includeLayers":True}})
        response = wait_id(2)
        if not response:
            return None, "config_read_no_response"
        if "error" in response:
            return None, "config_read_error: " + json.dumps(response["error"], sort_keys=True)
        result = response.get("result")
        if not isinstance(result, dict):
            return None, "config_read_result_not_object"
        return result, None
    except (OSError, BrokenPipeError) as exc:
        return None, f"app_server_io_failed: {exc}"
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=2)
        except subprocess.TimeoutExpired:
            proc.kill()


def _project_layers(result: dict[str, Any], target: Path) -> list[dict[str, Any]] | None:
    layers = result.get("layers")
    if not isinstance(layers, list):
        return None
    expected = (target / ".codex").resolve()
    matched: list[dict[str, Any]] = []
    for layer in layers:
        if not isinstance(layer, dict):
            continue
        name = layer.get("name")
        if not isinstance(name, dict) or name.get("type") != "project":
            continue
        folder = name.get("dotCodexFolder")
        if isinstance(folder, str) and Path(folder).resolve() == expected:
            matched.append(layer)
    return matched


def _effective_config_path(target: Path, value: str) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = target / ".codex" / path
    return path.resolve(strict=False)


def activation_report(target: Path, installation_state: str, codex_bin: str | None) -> dict[str, Any]:
    report: dict[str, Any] = {
        "installation_state": installation_state,
        "runtime_activation_state": UNKNOWN,
        "codex_version": None,
        "native_authority": NATIVE_AUTHORITY,
        "reason": None,
        "project_layer_disabled_reason": None,
        "runtime_profile_limitation": None,
    }
    if installation_state != CANONICAL:
        report["reason"] = "canonical installation is required for native readiness evaluation"
        return report
    if codex_bin is None:
        report["reason"] = "codex_executable_not_found"
        return report
    version, error = _codex_version(codex_bin)
    report["codex_version"] = version
    if error:
        report["reason"] = "codex_version_unavailable: " + error
        return report
    if version != TESTED_CODEX_VERSION:
        report["reason"] = f"untested_codex_version: expected {TESTED_CODEX_VERSION!r}"
        return report
    result, error = _config_read(target, codex_bin)
    if error or result is None:
        report["reason"] = error or "config_read_unknown_failure"
        return report
    layers = _project_layers(result, target)
    if layers is None:
        report["reason"] = "config_read_layers_missing_or_not_machine_readable"
        return report
    if not layers:
        report["runtime_activation_state"] = BLOCKED_PROJECT_CONFIG_INACTIVE
        report["reason"] = "matching_project_layer_not_reported_by_codex"
        return report
    disabled = [layer.get("disabledReason") for layer in layers if layer.get("disabledReason") is not None]
    if disabled:
        report["runtime_activation_state"] = BLOCKED_PROJECT_CONFIG_INACTIVE
        report["project_layer_disabled_reason"] = str(disabled[0])
        report["reason"] = "codex_reports_project_layer_disabled"
        return report
    config = result.get("config")
    if not isinstance(config, dict):
        report["reason"] = "effective_config_missing_or_not_machine_readable"
        return report
    agents = config.get("agents")
    if not isinstance(agents, dict):
        report["runtime_activation_state"] = BLOCKED_ROLE_REGISTRATION
        report["reason"] = "effective_agents_table_missing"
        return report
    if agents.get("enabled") is False:
        report["runtime_activation_state"] = BLOCKED_MULTI_AGENT_DISABLED
        report["reason"] = "codex_effective_agents_enabled_false"
        return report
    mismatches: list[str] = []
    for role, config_file in EXPECTED_REGISTRATIONS:
        role_cfg = agents.get(role)
        if not isinstance(role_cfg, dict):
            mismatches.append(f"{role}:missing")
            continue
        actual = role_cfg.get("config_file")
        if not isinstance(actual, str):
            mismatches.append(f"{role}:config_file_missing")
            continue
        expected = (target / ".codex" / config_file).resolve(strict=False)
        if _effective_config_path(target, actual) != expected:
            mismatches.append(f"{role}:config_file_mismatch")
    if mismatches:
        report["runtime_activation_state"] = BLOCKED_ROLE_REGISTRATION
        report["reason"] = ",".join(mismatches)
        return report
    report["runtime_activation_state"] = UNKNOWN
    report["runtime_profile_limitation"] = TESTED_RUNTIME_PROFILE_LIMITATION
    report["reason"] = "D3 read-only verifier enforcement remains NOT_ESTABLISHED on tested parent-child runtime shape"
    return report


def main() -> int:
    parser = argparse.ArgumentParser(prog="lunako_doctor.py")
    parser.add_argument("target")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--require-role")
    args = parser.parse_args()
    try:
        target = target_root(args.target)
        bundle = load_bundle()
        detection = detect_state(target, bundle)
        report = activation_report(target, detection.state, shutil.which("codex"))
        report["installation_subtype"] = detection.subtype
        report["installation_problems"] = list(detection.problems)
        if detection.state == CONFLICT:
            report["conflict_diagnostics"] = conflict_diagnostics(target, bundle, detection)
        if args.require_role:
            roles = {role for role, _ in EXPECTED_REGISTRATIONS}
            if args.require_role not in roles:
                raise DoctorError(f"required role is not in product registration contract: {args.require_role}")
            available = report["runtime_activation_state"] == READY
            report.update({"required_role":args.require_role,"required_role_availability":"AVAILABLE" if available else "UNAVAILABLE","requirement_state":"REQUIRED","fallback":"PROHIBITED","completion_state":"ALLOWED" if available else "BLOCKED"})
        if args.json:
            print(json.dumps(report, sort_keys=True, indent=2))
        else:
            print("LUNAKO DOCTOR: " + str(report["runtime_activation_state"]))
            print("INSTALLATION_STATE=" + detection.state)
            print("INSTALLATION_SUBTYPE=" + detection.subtype)
            print("RUNTIME_ACTIVATION_STATE=" + str(report["runtime_activation_state"]))
            print("CODEX_VERSION=" + str(report.get("codex_version")))
            if report.get("reason"):
                print("REASON=" + str(report["reason"]))
            if detection.state == CONFLICT:
                diagnostics = report["conflict_diagnostics"]
                print("CONFLICT_DIAGNOSTICS=" + json.dumps(diagnostics, sort_keys=True, separators=(",", ":")))
                for item in diagnostics["recovery_guidance"]:
                    print("RECOVERY_GUIDANCE=" + item)
            if report.get("runtime_profile_limitation"):
                print("RUNTIME_PROFILE_LIMITATION=" + str(report["runtime_profile_limitation"]))
            if args.require_role:
                print("REQUIRED_ROLE=" + args.require_role)
                print("REQUIRED_ROLE_AVAILABILITY=" + str(report["required_role_availability"]))
                print("FALLBACK=PROHIBITED")
                print("COMPLETION_STATE=" + str(report["completion_state"]))
        state = report["runtime_activation_state"]
        return 0 if state == READY else (1 if state in {BLOCKED_PROJECT_CONFIG_INACTIVE, BLOCKED_ROLE_REGISTRATION, BLOCKED_MULTI_AGENT_DISABLED} else 2)
    except (DoctorError, Exception) as exc:
        if isinstance(exc, KeyboardInterrupt):
            raise
        print(f"LUNAKO DOCTOR ERROR: {exc}")
        return 2

if __name__ == "__main__":
    raise SystemExit(main())
