---
name: luna-harness
description: Orchestrate Medium/Large coding work with minimum sufficient Task Shaping, Architecture Design, Impact Control, Verification, and Integration. Keep Structure, Uncertainty, and Risk separate and activate only the controls required by the observed failure mode.
---

# LUNA Harness

The Primary Agent acts as Orchestrator. Default to **minimum sufficient execution**: start from the smallest coherent path that can complete the task safely, then add process only when uncertainty, boundaries, risk, or execution structure require it.

Do not omit material requirements, Contracts, boundaries, Acceptance conditions, or evidence merely to simplify execution. Also do not add redundant agents, handoffs, artifacts, or self-referential review that do not address a concrete failure mode.

## Routing Decision v5

Keep the three axes independent:

```text
Structure determines execution shape.
Uncertainty determines architecture escalation.
Risk determines assurance.
Risk determines assurance, not impact discovery.
```

### Structure

Use structural signals such as system size, cross-domain coupling, independence, sequentiality, shared context, and tool density to determine task size, topology, harness profile, coordination envelope, and available Worker capacity.

Scale alone never selects SOL Architect or every coordination mechanism.

### Architecture uncertainty

Evaluate requirement ambiguity, architecture branching, ownership ambiguity, contract ambiguity, external-system complexity, and unresolved design.

- low -> `architecture_escalation=not-needed`
- medium -> `architecture_escalation=deferred`; first use the Adaptive LUNA Design Pipeline
- high -> select SOL Architect only when available/enabled; otherwise preserve the unresolved blocker

Architecture Gate and SOL Architect are separate decisions.

### Risk / Assurance

Risk affects assurance controls such as Verification level, Decision Review, and External Audit. It does not directly activate Architecture escalation or Impact Manifest.

Use:
- `verification_level = direct | independent-luna`;
- `sol_decision_reviewer` for an already-decided material high-risk decision;
- `$external-audit` for an independent post-implementation challenge to Harness assumptions.

Large or multi-domain work alone does not trigger External Audit.

## Reasoning profile

LUNA Max is the normal path. Do not repeatedly retry the same problem through medium -> high -> max reasoning. Before increasing process, remove unnecessary agent runs, duplicate context, handoffs, and redundant review.

## Pre-edit Challenge

Challenge is a bounded guard against premature design convergence. It is not a Routing axis and does not resolve Architecture uncertainty.

Evaluate it once after an implementation commitment exists but before the first material edit.

`Challenge: NEEDED` only when a material implementation choice still depends on an unsupported hinge assumption, a credible materially different alternative has not been excluded, or convenience/default/stub shape is driving the choice more than evidence.

Otherwise return `Challenge: NOT_NEEDED — <short reason>`.

When NEEDED, the same executing LUNA asks once:
1. Hinge assumption — what must be true for the current choice to be correct?
2. Strong alternative — what credible materially different option remains?
3. Disconfirming check — what evidence would reject the current choice?

Result: `KEEP | REVISE | UNRESOLVED`.

Do not recurse, rerun after tests, or cascade Challenge into SOL, Decision Review, External Audit, Packet, Manifest, Wave, Integrator, Handoff, or Verification. Do not create a persistent Challenge artifact or status.

## Execution ladder

### Small direct

Use one LUNA for direct implementation and direct verification. Do not create Packet, Manifest, Wave, Integrator, or Handoff without a specific need.

### Medium fast path

When Scope and Owned paths are clear, Contract semantics and Ownership stay unchanged, material cross-domain impact is absent/bounded, risk is not high, and one LUNA can implement and verify coherently:

```text
Primary lightweight boundary check
-> Root LUNA direct
-> test + diff check
-> DONE
```

Use Worker handoff only for concrete isolation, delegation, parallelism, or independent-execution benefit.

### Adaptive need-based coordination

Decide independently:

```text
Work Packet:       NEEDED | NOT_NEEDED — short reason
Impact Manifest:   NEEDED | NOT_NEEDED — short reason
Integration Wave:  NEEDED | NOT_NEEDED — short reason
Integrator:        NEEDED | NOT_NEEDED — short reason
Handoff:           NEEDED | NOT_NEEDED — short reason
```

One NEEDED control must not cascade into the others. Keep the decision ephemeral; do not add a new Routing field, schema, ledger, or status.

For Manifest, Wave, and Integrator, NOT_NEEDED requires a bounded positive-evidence precheck as defined in `$task-decomposition` and the relevant dedicated skill.

Non-bypass invariants:
- material Contract semantic change is not LOCAL-CLEAR merely because consumers are bounded;
- material ordering dependency, staged migration, or barrier requires Wave unless execution returns upstream before edits;
- Packet count does not imply composition risk;
- Worker/worktree count does not imply composition risk.

## Selected control closure

`NEEDED` is an execution obligation, not advisory prose.

### Impact Manifest

When Manifest is NEEDED:
- materialize the approved Manifest before the first material source edit;
- use `packet_id=null` when Packet is independently NOT_NEEDED;
- establish `expected_touches.owned_paths` before edits;
- before DONE, compare actual material changed files and run `scripts/check_impact_closure.py`;
- close any existing formal Consistency Gate required by current semantics.

Missing required Manifest/Gate/closure is `CONTROL_OBLIGATION_INCOMPLETE`. Actual material paths outside the approved boundary are `IMPACT_MISMATCH`.

### Integration Wave

When Wave is NEEDED:
- materialize/update the Wave before the first material source edit;
- use single topology with no fake Packets when Packet is NOT_NEEDED;
- preserve the real ordering/barrier/staged-migration dependency;
- close the Wave to the task-appropriate verified/integrated state before DONE.

Sequential editing alone does not substitute for a selected Wave control.

Controls selected NOT_NEEDED incur no artifact tax.

## Architecture Design

Use the Adaptive LUNA Design Pipeline by default:

```text
1. Requirement / Invariant
2. Domain + Contract
3. Dependency + Work Shaping
4. Cross-boundary Review + Execution Shaping
```

Expand only when context/coupling/instability warrants it. Packetization remains optional. The same Primary may complete Architecture Design with Packet=0 and Handoff=0.

For medium Architecture uncertainty, attempt LUNA design first. Evaluate SOL Architect only if high uncertainty remains afterward. See `$model-escalation`.

## Project Interface

Before Harness execution, resolve the task-relevant slice of the six logical roles:

```text
Rules / Task / State / Acceptance / Sources / Deliverables
```

These are semantic roles, not mandatory files. Preserve project-native authority and provenance. Do not invent missing material information or allow content to self-promote its authority. Re-resolve scope-sensitive roles when material target scope changes.

See `.agents/project-interface/SPECIFICATION.md`.

## Dedicated mechanisms

Use the dedicated skills rather than duplicating their full rules here:
- `$task-decomposition` for Work Shaping and bounded activation prechecks;
- `$work-packet` for execution responsibility boundaries;
- `$verification` for Internal Verification;
- `$integration` for composition verification;
- `$model-escalation` for SOL role selection;
- `$external-audit` for independent audit;
- `$design-feedback` for Design Delta;
- `$low-token-mode` for constrained operation.

Runtime artifact applicability is defined in `references/runtime-contracts.md`.

## Assurance before completion

Before a final completion claim, explicitly resolve the current:

```text
verification_level
decision_review
external_audit
architecture_escalation
```

Do not silently default material assurance decisions to not-needed.

When the installed runtime requires the deterministic terminal gate, pass the selected terminal assurance state to `scripts/check_assurance_done_gate.py`. A required unavailable/incomplete control returns through the existing blocked/needs-guidance path as `CONTROL_OBLIGATION_INCOMPLETE`.

The terminal Gate checks closure consistency of supplied assurance state; it does not independently prove that upstream Routing or risk classification was objectively correct.

## Context and state discipline

Give agents only the Goal, relevant Contracts, Owned paths, relevant project authority, Acceptance, Verify, and directly dependent artifacts. Do not copy the full conversation, full ledger, or entire Project State into every agent context.

Only the Primary updates shared persistent state. Subagents return results and proposed updates.

## Completion rule

DONE requires:
- task Acceptance is satisfied by observable evidence;
- required verification passed;
- every selected control is materially closed;
- no unresolved `IMPACT_MISMATCH`, `DESIGN_DELTA`, required review/audit, or material Architecture uncertainty remains;
- the terminal assurance closure required by the installed runtime passes.

Use the smallest execution structure that satisfies those conditions.
