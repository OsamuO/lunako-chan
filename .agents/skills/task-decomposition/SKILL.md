---
name: task-decomposition
description: Shape work into execution units only when separation materially clarifies Goal, Acceptance, Ownership, retry boundaries, or Decision Complexity. Do not activate coordination machinery from scale alone.
---

# Task Decomposition

The objective is not to create more Packets. Split work only when **split benefit > coordination / handoff cost**.

Keep Routing Decision v5 independent:

```text
Structure determines execution shape.
Uncertainty determines architecture escalation.
Risk determines assurance.
Risk determines assurance, not impact discovery.
```

Decision Complexity is a temporary Work Shaping heuristic, not a Routing axis.

## Independent coordination controls

Decide these independently:

```text
Work Packet:       NEEDED | NOT_NEEDED — short reason
Impact Manifest:   NEEDED | NOT_NEEDED — short reason
Integration Wave:  NEEDED | NOT_NEEDED — short reason
Integrator:        NEEDED | NOT_NEEDED — short reason
Handoff:           NEEDED | NOT_NEEDED — short reason
```

Do not persist this as a new Routing field or schema. Do not cascade one control into another.

## Decision Complexity

Consider only the non-trivial decisions that must remain coupled inside a candidate execution unit after Architecture, Contract, and Ownership are sufficiently resolved.

Use only when helpful:
- decision count;
- coupling between decisions;
- span across Contracts, Domains, Acceptance conditions, or state transitions.

Do not proxy with file count, LOC, Domain count, or system size. Do not use Decision Complexity to trigger SOL, Manifest, Wave, Integrator, Handoff, Verification, Decision Review, or External Audit.

Packetize only when splitting actually reduces decision interaction or materially improves Goal, Acceptance, Ownership, delegation, parallelism, retry, or checkpoint boundaries.

## Impact boundary precheck

Impact Manifest controls **impact uncertainty**. Before selecting `LOCAL-CLEAR`, inspect only the task-relevant expected touch, Contract refs, Provider/Consumer, Ownership, dependency information, and any material indirect-consumer mechanism.

Reconcile observed affected consumers/edges with the canonical project model:

- `MATCH`: all observed material edges are represented and the consumer set is closed/bounded;
- `MISMATCH`: observed material edge is missing -> NEEDS-MANIFEST;
- `UNBOUNDED`: material consumer surface cannot be bounded -> NEEDS-MANIFEST or an existing uncertainty path.

`LOCAL-CLEAR` requires positive evidence: MATCH, bounded consumers, unchanged Contract semantics, unchanged Ownership, no unresolved indirect-consumer uncertainty, and bounded expected effects.

Search result count zero is not evidence of zero impact. Scale and risk are not Manifest triggers.

## Wave and Integrator prechecks

Wave is needed only for material ordering/barrier concerns such as compatibility order, staged migration, state-transition order, cleanup, staging, or release barriers.

Integrator is needed only for composition-specific risk: behavior, Contracts, shared state, build/runtime invariants, or obligations that can be verified only after combining results.

**Packet count != composition risk.**  
**Worker/worktree count != composition risk.**

Do not invoke an Integrator merely to decide that Integration is unnecessary.

## Handoff and Audit

Use ordinary Handoff only for concrete execution/isolation benefit. External Audit follows its own Blind Review input contract and is not ordinary Handoff machinery.

## Adaptive LUNA Design Pipeline

Architecture Design defaults to the Adaptive LUNA Design Pipeline. Scale and SOL availability alone do not switch the route.

Default phases:
1. Requirement / Invariant;
2. Domain + Contract;
3. Dependency + Work Shaping;
4. Cross-boundary Review + Execution Shaping.

Packetize only if needed. The same Primary may complete the pipeline with Packet=0 and Handoff=0. Medium Architecture uncertainty is handled through the LUNA pipeline first; architecture escalation is reconsidered only if high uncertainty remains.

## Procedure

1. Read only target code and directly relevant project-native authority.
2. Keep Structure, Architecture uncertainty, and Risk/Assurance separate.
3. Evaluate Decision Complexity only when it helps Work Shaping.
4. Decide Packet, Manifest, Wave, Integrator, and Handoff independently.
5. Require positive evidence before NOT_NEEDED for Manifest, Wave, or Integrator.
6. Keep one coherent execution unit when safe.
7. Split only when the benefit exceeds coordination cost.
8. Return unresolved Contract, Ownership, Impact, or Architecture questions upstream rather than guessing.

The Decomposer does not edit shared state. The Primary persists only existing artifacts that are actually needed.
