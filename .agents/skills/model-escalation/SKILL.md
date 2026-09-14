---
name: model-escalation
description: Keep LUNA Max as the default. Escalate to SOL Architect only when Architecture uncertainty remains unresolved after LUNA design. Keep High-risk Decision Review and External Audit in separate SOL roles.
---

# Model Escalation

Choose a model from the **type of decision currently required**, not from session boundaries, task size, topology, Architecture Gate, or risk alone.

Routing v5:

```text
Structure determines execution shape.
Uncertainty determines architecture escalation.
Risk determines assurance.
```

Do not select SOL Architect merely because work is Large, 0→1, multi-domain, hierarchical/full, high risk, or Architecture-Gated.

## SOL role separation

```text
sol_architect
  -> unresolved Architecture uncertainty

sol_decision_reviewer
  -> already-decided high-risk decision review

sol_reviewer
  -> post-implementation External Audit
```

These roles are not interchangeable.

## LUNA Max default

Use LUNA Max for ordinary implementation, tests, narrow review, stable continuation work, Impact Candidate Scan, ordinary consistency decisions, and implementation/integration after design is resolved. The Adaptive LUNA Design Pipeline is also the default Architecture Design path, including for Large work.

A new session, a previous SOL session, or a large amount of work does not by itself justify SOL.

## Architecture uncertainty

Evaluate these signals from 0 to 3:
- requirement_ambiguity;
- architecture_branching;
- ownership_ambiguity;
- contract_ambiguity;
- external_system_complexity;
- unresolved_design.

Use the maximum value:

```text
max <= 1 -> low
max == 2 -> medium
max == 3 -> high
```

### low

`architecture_escalation=not-needed`. Use the Adaptive LUNA Design Pipeline. Architecture Gate may still be required and may approve a LUNA design.

### medium

`architecture_escalation=deferred`. Attempt to resolve ambiguity with the Adaptive LUNA Design Pipeline first. Escalate only if a later route still contains a high signal such as `unresolved_design=3`.

### high

- if SOL is available and the task is not explicitly LUNA-only: `architecture_escalation=selected`;
- otherwise: `architecture_escalation=not-selected`.

Do not guess through unresolved Architecture, Ownership, or Contract ambiguity.

## SOL Architect

`sol_architect` is used only for high Architecture uncertainty that remains unresolved after LUNA design, such as material architecture branching, Ownership/Contract/external-system ambiguity, or unresolved design after feedback.

The Architect returns Architecture decisions together with Work Shaping for LUNA execution. It does not decide general model allocation, and implementation normally returns to LUNA Max afterward.

## Architecture Gate is not SOL

Architecture Gate asks whether a design requires approval before implementation. Architecture escalation asks whether LUNA can resolve the design decision. Therefore this is valid:

```text
requires_architecture_gate=true
architecture_escalation=not-needed
```

Do not couple Gate approval/evidence requirements to model selection.

## High-risk Decision Review

Decision Review is separate from Architecture escalation and uses `sol_decision_reviewer` when selected.

It reviews an already-decided material decision rather than redesigning the system. Primary signals include authorization, irreversibility, migration compatibility, financial impact, and public API compatibility. A test gap alone does not make Decision Review required.

When `decision_review=recommended|required`, keep `decision_review_executor=sol_decision_reviewer`. The reviewer returns `APPROVE | REVISE | INCONCLUSIVE` with the reviewed decision, evidence, consequence, required correction, and residual risk. It does not implement, redesign from scratch, or perform External Audit.

## SOL External Auditor

`sol_reviewer` follows `$external-audit`. It independently challenges Harness assumptions after implementation and is not activated from scale alone.

Audit starts with original requirement, Acceptance, implementation/diff, tests, and necessary external specifications. Only after the Blind Review is fixed does it reconcile against Architecture, Contracts, Manifest, and internal verdicts.

## Session restart

A session boundary is not an escalation condition. On resume, use current canonical project artifacts and inspect only whether design assumptions remain valid. If current State, active work, Contract versions, relevant invariants, and unresolved deltas remain consistent, resume with LUNA.

If Contract versions, Ownership, design assumptions, or unresolved deltas have materially changed, return to the Adaptive LUNA Design Pipeline. Evaluate SOL Architect only if high Architecture uncertainty remains.

Do not use prior conversation transcripts as authority.

## SOL unavailable / LUNA-only

The Adaptive LUNA Design Pipeline remains the default even when SOL is unavailable. If high Architecture uncertainty remains, keep `architecture_escalation=not-selected` and return the unresolved design blocker instead of guessing.

If Decision Review is required/recommended but SOL is unavailable, do not silently replace its logical executor with LUNA. Preserve the unresolved executor constraint.

If External Audit is required but SOL is unavailable, an independent LUNA may follow the same Blind Review procedure, but do not represent it as equivalent to a SOL audit.
