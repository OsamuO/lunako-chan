#!/usr/bin/env python3
"""Deterministic terminal Assurance DONE gate.

This script does not choose Routing and does not call any model. It validates the
four terminal Routing/Assurance states against the existing Routing Decision v5
schema and fails closed when a required review/audit is not completed.

It writes no repository/runtime artifact. stdout + exit status are the closure
evidence, and a PASS emits one canonical ASSURANCE_FINAL line for exact reuse in
the final completion response.
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]
ROUTING_SCHEMA = ROOT / ".agents/schemas/routing-decision.schema.json"
EXECUTOR_STATUSES = {"not-applicable", "completed", "unavailable", "not-run"}


@dataclass(frozen=True)
class TerminalAssurance:
    verification_level: str
    decision_review: str
    decision_review_executor_status: str
    external_audit: str
    external_audit_executor_status: str
    architecture_escalation: str


@dataclass(frozen=True)
class V5Enums:
    verification_level: frozenset[str]
    decision_review: frozenset[str]
    external_audit: frozenset[str]
    architecture_escalation: frozenset[str]


def _as_enum(value: object, label: str) -> frozenset[str]:
    if not isinstance(value, list) or not value or not all(isinstance(x, str) for x in value):
        raise ValueError(f"routing schema missing string enum for {label}")
    return frozenset(value)


def load_v5_enums(path: Path = ROUTING_SCHEMA) -> V5Enums:
    schema = json.loads(path.read_text(encoding="utf-8"))
    props = schema.get("properties")
    if not isinstance(props, dict):
        raise ValueError("routing schema properties missing")

    v5_then: dict | None = None
    for rule in schema.get("allOf", []):
        if not isinstance(rule, dict):
            continue
        cond = rule.get("if")
        if not isinstance(cond, dict):
            continue
        version = (((cond.get("properties") or {}).get("schema_version") or {}).get("const"))
        if version == 5:
            then = rule.get("then")
            if isinstance(then, dict):
                v5_then = then
                break
    if v5_then is None:
        raise ValueError("routing schema v5 rule missing")

    v5_props = v5_then.get("properties") or {}
    verification = ((v5_props.get("verification_level") or {}).get("enum"))
    return V5Enums(
        verification_level=_as_enum(verification, "v5 verification_level"),
        decision_review=_as_enum((props.get("decision_review") or {}).get("enum"), "decision_review"),
        external_audit=_as_enum((props.get("external_audit") or {}).get("enum"), "external_audit"),
        architecture_escalation=_as_enum(
            (props.get("architecture_escalation") or {}).get("enum"), "architecture_escalation"
        ),
    )


def _enum_error(name: str, value: str, allowed: Iterable[str]) -> str:
    return f"{name}={value!r} is invalid; allowed={','.join(sorted(allowed))}"


def evaluate(state: TerminalAssurance, enums: V5Enums) -> list[str]:
    failures: list[str] = []

    for name, value, allowed in (
        ("verification_level", state.verification_level, enums.verification_level),
        ("decision_review", state.decision_review, enums.decision_review),
        ("external_audit", state.external_audit, enums.external_audit),
        ("architecture_escalation", state.architecture_escalation, enums.architecture_escalation),
    ):
        if value not in allowed:
            failures.append(_enum_error(name, value, allowed))

    for name, status in (
        ("decision_review_executor_status", state.decision_review_executor_status),
        ("external_audit_executor_status", state.external_audit_executor_status),
    ):
        if status not in EXECUTOR_STATUSES:
            failures.append(_enum_error(name, status, EXECUTOR_STATUSES))

    # Do not derive executor rules from invalid state values.
    if state.decision_review in enums.decision_review and state.decision_review_executor_status in EXECUTOR_STATUSES:
        if state.decision_review == "not-needed":
            if state.decision_review_executor_status != "not-applicable":
                failures.append(
                    "decision_review=not-needed requires decision_review_executor_status=not-applicable"
                )
        elif state.decision_review == "recommended":
            if state.decision_review_executor_status == "not-applicable":
                failures.append(
                    "decision_review=recommended requires executor status completed|unavailable|not-run"
                )
        elif state.decision_review == "required":
            if state.decision_review_executor_status != "completed":
                failures.append(
                    "decision_review=required requires decision_review_executor_status=completed"
                )

    if state.external_audit in enums.external_audit and state.external_audit_executor_status in EXECUTOR_STATUSES:
        if state.external_audit == "not-needed":
            if state.external_audit_executor_status != "not-applicable":
                failures.append(
                    "external_audit=not-needed requires external_audit_executor_status=not-applicable"
                )
        elif state.external_audit == "recommended":
            if state.external_audit_executor_status == "not-applicable":
                failures.append(
                    "external_audit=recommended requires executor status completed|unavailable|not-run"
                )
        elif state.external_audit == "required":
            if state.external_audit_executor_status != "completed":
                failures.append(
                    "external_audit=required requires external_audit_executor_status=completed"
                )

    return failures


def canonical_final_line(state: TerminalAssurance) -> str:
    return (
        "ASSURANCE_FINAL="
        f"verification_level={state.verification_level} | "
        f"decision_review={state.decision_review}/{state.decision_review_executor_status} | "
        f"external_audit={state.external_audit}/{state.external_audit_executor_status} | "
        f"architecture_escalation={state.architecture_escalation}"
    )


def emit_pass(state: TerminalAssurance) -> None:
    print("ASSURANCE DONE GATE: PASS")
    print(f"verification_level={state.verification_level}")
    print(f"decision_review={state.decision_review}")
    print(f"decision_review_executor_status={state.decision_review_executor_status}")
    print(f"external_audit={state.external_audit}")
    print(f"external_audit_executor_status={state.external_audit_executor_status}")
    print(f"architecture_escalation={state.architecture_escalation}")
    print(canonical_final_line(state))


def emit_fail(failures: list[str]) -> None:
    print("ASSURANCE DONE GATE: FAIL")
    print("CONTROL_OBLIGATION_INCOMPLETE")
    for failure in failures:
        print(f"- {failure}")


def _state(
    verification: str = "direct",
    decision: str = "not-needed",
    decision_status: str = "not-applicable",
    audit: str = "not-needed",
    audit_status: str = "not-applicable",
    architecture: str = "not-needed",
) -> TerminalAssurance:
    return TerminalAssurance(
        verification_level=verification,
        decision_review=decision,
        decision_review_executor_status=decision_status,
        external_audit=audit,
        external_audit_executor_status=audit_status,
        architecture_escalation=architecture,
    )


def self_test() -> None:
    enums = load_v5_enums()
    assert enums.verification_level == frozenset({"direct", "independent-luna"})

    cases: list[tuple[str, TerminalAssurance, bool]] = [
        ("direct-fast-path", _state(), True),
        (
            "recommended-review-unavailable",
            _state(decision="recommended", decision_status="unavailable"),
            True,
        ),
        (
            "recommended-audit-not-run",
            _state(audit="recommended", audit_status="not-run"),
            True,
        ),
        (
            "required-review-unavailable",
            _state(decision="required", decision_status="unavailable"),
            False,
        ),
        (
            "required-audit-unavailable",
            _state(audit="required", audit_status="unavailable"),
            False,
        ),
        ("legacy-sol-audit", _state(verification="sol-audit"), False),
        (
            "not-needed-with-completed-executor",
            _state(decision_status="completed"),
            False,
        ),
        ("invalid-architecture", _state(architecture="invented"), False),
    ]

    for name, state, should_pass in cases:
        failures = evaluate(state, enums)
        if should_pass != (not failures):
            raise AssertionError(f"{name}: expected pass={should_pass}, failures={failures}")

    line = canonical_final_line(_state())
    assert line.startswith("ASSURANCE_FINAL=verification_level=direct")
    assert "decision_review=not-needed/not-applicable" in line
    assert "external_audit=not-needed/not-applicable" in line
    assert "architecture_escalation=not-needed" in line

    print("assurance-done-gate self-test: PASS")
    print(f"cases={len(cases)}")
    print("model_calls=0")
    print("sol_calls=0")
    print("artifact_writes=0")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate terminal Harness Assurance before DONE")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--verification-level")
    parser.add_argument("--decision-review")
    parser.add_argument("--decision-review-executor-status")
    parser.add_argument("--external-audit")
    parser.add_argument("--external-audit-executor-status")
    parser.add_argument("--architecture-escalation")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.self_test:
        try:
            self_test()
        except Exception as exc:  # deterministic configuration/self-test failure
            print("assurance-done-gate self-test: FAIL")
            print(f"- {exc}")
            return 1
        return 0

    required = {
        "verification_level": args.verification_level,
        "decision_review": args.decision_review,
        "decision_review_executor_status": args.decision_review_executor_status,
        "external_audit": args.external_audit,
        "external_audit_executor_status": args.external_audit_executor_status,
        "architecture_escalation": args.architecture_escalation,
    }
    missing = [name for name, value in required.items() if value is None]
    if missing:
        emit_fail([f"missing terminal state: {name}" for name in missing])
        return 2

    try:
        enums = load_v5_enums()
    except Exception as exc:
        emit_fail([f"routing schema unavailable or invalid: {exc}"])
        return 2

    state = TerminalAssurance(
        verification_level=args.verification_level,
        decision_review=args.decision_review,
        decision_review_executor_status=args.decision_review_executor_status,
        external_audit=args.external_audit,
        external_audit_executor_status=args.external_audit_executor_status,
        architecture_escalation=args.architecture_escalation,
    )
    failures = evaluate(state, enums)
    if failures:
        emit_fail(failures)
        return 2

    emit_pass(state)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
