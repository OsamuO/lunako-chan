---
name: work-packet
description: Create a Work Packet only when separating execution responsibility has clear value. Do not activate it automatically from scale, risk, or another coordination mechanism.
---

# Work Packet

A Work Packet is an **execution responsibility boundary**. Use one only when separation prevents responsibility mixing or materially improves delegation, retry, checkpointing, parallelism, or decision shaping enough to justify coordination cost.

Only the Primary may persist Packets under `.agents/work-packets/` and update their state. Having no Packet is valid at any task size.

## Activation

NEEDED when separation materially improves one or more of:
- independent Goal or Acceptance;
- non-overlapping Owned paths;
- delegation, parallelism, independent retry, or checkpointing;
- actual reduction in Decision Complexity.

NOT a trigger by itself:
- Large, multi-domain, or 0→1 work;
- file count or LOC;
- high risk;
- Architecture Gate;
- `harness_profile=full`;
- `Decision Complexity=high` without demonstrated split benefit.

Packetize only when split benefit exceeds coordination and handoff cost.

Packet, Manifest, Wave, Integrator, and Handoff are independent controls. A Packet does not imply any of the others, and packetless Manifest/Wave flows are valid.

## Required content

A Compact Packet contains the responsibility boundary needed for execution:
- Status and dependencies;
- Owned paths;
- current Contract refs;
- Impact Manifest ref or `none`;
- Verification level;
- GOAL, CONTEXT, SCOPE, CONTRACT, ACCEPTANCE, VERIFY, and ESCALATE IF.

Use Full metadata only when execution actually needs fields such as assigned agent, worktree, run identity, attempts, branch/base/result commit, execution budget, or formal handoff. Task size alone does not select Full.

For a new run with formal handoff, OUTPUT conforms to `.agents/schemas/strict-agent-result.schema.json` v2. Direct execution or sequential work by the same Primary does not require a Typed Result.

## Context and handoff

CONTEXT includes only the Goal, directly relevant Contracts, Relevant Spine, Impact Manifest when needed, Acceptance, and directly dependent artifacts. Do not copy the full conversation, full Project State, or full Ledger.

Use Handoff only for a concrete benefit such as parallelism, worktree isolation, specialist execution, independent verification, deliberate context isolation, or retry isolation. Packet existence or lifecycle stage change is insufficient. External Audit uses its own Blind Review input contract rather than ordinary Handoff context.

## Impact Manifest

Work Packet controls execution responsibility; Impact Manifest controls impact uncertainty. Use a Manifest when material uncertainty remains around Contract semantics, Ownership, consumers, cross-domain effects, expected touches/effects, or Forbidden Effects. Scale, Packet count, risk, and verification level are not Manifest triggers by themselves.

When a Manifest is active, Expected Touches, Allowed Effects, Forbidden Effects, Expected Consumers, and Integration Obligations define the impact boundary. Work that requires effects outside that boundary returns as an `IMPACT_MISMATCH` candidate.

## Quality conditions

- The responsibility boundary is understandable from the Packet alone.
- No implicit out-of-scope Contract or Architecture change.
- Contract refs are current.
- ACCEPTANCE and VERIFY are observable and reproducible.
- Packetization benefit exceeds coordination cost.
- Parallel code-writing uses separate worktrees with non-overlapping Owned paths.

## State updates

Only the Primary updates Packet state. Do not introduce Packet state into packetless execution.

- `ready -> in-progress`: execution started
- `in-progress -> blocked`: external condition prevents progress
- `in-progress -> needs-redesign`: Design Delta
- `verified|integrated -> needs-reverification`: dependent Contract or Impact Rule changed
- `in-progress -> verified`: required verification passed
- `verified -> integrated`: required composition verification passed
