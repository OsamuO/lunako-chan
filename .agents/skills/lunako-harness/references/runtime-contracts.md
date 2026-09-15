# Runtime contracts

Read this reference only when execution, handoff, or persistent runtime records are involved. Do not require all runtime artifacts merely because work is large.

## Need-based applicability

| Mechanism | Failure mode / trigger |
|---|---|
| Routing decision | Existing Routing v5; keep Structure / Uncertainty / Risk-Assurance separate |
| Context Capsule | deliberate handoff or context isolation |
| Work Packet | benefit of separating execution responsibility exceeds cost |
| Impact Manifest | material impact uncertainty |
| Typed Result | formal handoff or independent execution result needs validation |
| Quality Evidence | required by assurance or an actually active formal Gate |
| Run Ledger | handoff, retry, or formal run accounting |
| Domain Map / Dependency Graph | semantic structure requires explicit representation; independent of coordination machinery |
| Integration Wave | material ordering, barrier, or staged-integration need |
| Integrator | composition-specific verification risk |

`harness_profile=full` is the maximum available structural envelope, not a command to activate every mechanism.

Machine-readable `artifact_policy` must not conflate structural applicability, actual need-based coordination activation, and assurance-required evidence. `worker_count` is available Worker capacity, not actual Worker or handoff count; nonzero capacity with Packet=0 / Handoff=0 is valid.

Routing v5 remains:

```text
Structure determines execution shape.
Uncertainty determines architecture escalation.
Risk determines assurance.
Risk determines assurance, not impact discovery.
```

## Active Context Capsule

Use `.luna-runtime/active-context.json` only for actual handoff or deliberate context isolation. Include only the current Goal, needed Packet, assigned Domain, active Wave if any, Contract refs, Owned paths, Acceptance, Verify, directly dependent artifacts, immediately relevant failure, and next action.

Agent boundary is not automatically ordinary Handoff. External Audit Pass 1 follows the `$external-audit` Blind Review input contract and does not require the normal Active Context Capsule.

## Domain and dependency state

Project-native Rules / State / Sources resolved through the External Project Interface remain authoritative for Provider, Consumer, Ownership, dependency, and related semantics. Use project-native Domain Map / Dependency Graph representations when available; no project-specific Harness Project State file is required. Only the Primary updates authoritative sources after authority and write scope are resolved.

## Integration Waves

Use `.luna-runtime/integration-waves.json` only when explicit ordering, barriers, or staged integration are needed. Before selecting Wave NOT_NEEDED, establish a bounded positive basis that relevant provider-consumer compatibility, migration order, state-transition order, cleanup order, or release/staging barriers do not require sequencing.

Multiple Packets, Large scope, multi-domain scope, or parallelism are not Wave triggers by themselves. Wave does not imply Integrator. When Wave is active, do not cross a dependency barrier before required closure.

## Integrator applicability

Use Integrator only for composition-specific risk. Packet count and Worker/worktree count are not composition risk. Before selecting NOT_NEEDED, inspect only the relevant results and confirm that composition creates no new shared runtime behavior, Contract interaction, shared-state invariant, build/integration invariant, provider-consumer behavior, or cross-execution obligation. If evidence is insufficient, use an existing `INCONCLUSIVE` or upstream path; do not invoke Integrator merely to prove it unnecessary.

## Typed Result / Run Ledger

A new Subagent run with formal handoff returns a result conforming to `.agents/schemas/strict-agent-result.schema.json` v2. Sequential phases or Packets executed by the same Primary do not require Typed Result or Run Ledger. Typed Result and Run Ledger use do not require a separate auxiliary validation CLI.

When Run Ledger is actually used, it is append-only.

## Packet state and evidence

Manage Packet state only when Packets are active. Compact Packet contains only the responsibility boundary; Full Packet is for execution/handoff metadata actually required. Task size does not choose Compact versus Full.

Manage Wave state only when Wave is active. Quality Evidence is driven by Assurance or an active formal Gate, not by scale alone.

## Contract impact

For Contract semantic changes, propagate only the bounded affected surface derived from current project-native Contract / Provider / Consumer / dependency information and actual impact. Manifest activation depends on impact uncertainty, not risk alone. Contract impact handling does not require a separate propagation CLI.

## Worktree isolation

Use separate worktrees only when parallel code-writing or isolation provides concrete benefit. Packet existence or Large scope does not force worktrees or handoff.

## Budgets

Set timeout, token budget, or no-progress limit only when a formal Subagent/retry boundary actually needs them. Do not guess unmeasurable values. Decision Complexity alone is not a stop condition. If execution observably cannot preserve required information, make bounded progress, satisfy Acceptance in a safe shape, or escape repeated invariant failure, use existing `needs_guidance`, `blocked`, timeout/budget, `INCONCLUSIVE`, or upstream shaping paths.
