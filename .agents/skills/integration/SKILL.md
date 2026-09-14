---
name: integration
description: Perform Integration only when combining individually passing results introduces composition-specific risk. Do not activate it from Packet count, scale, cross-domain scope, or Wave existence alone.
---

# Integration

The Integrator prevents the failure mode where individual results pass in isolation but the composed system behavior fails. Its purpose is **composition verification**.

## Activation

NEEDED only when there is composition-specific risk, for example:
- independently produced changes expose shared behavior, Contract, state, build, or runtime invariants that can only be verified after composition;
- cross-boundary behavior cannot be verified within an individual execution unit;
- a real Integration Obligation spans multiple results;
- provider and consumer changed separately and Contract behavior is only testable after combination;
- runtime behavior is observable only after merge/composition.

NOT a trigger by itself:
- multiple Packets;
- multiple Workers or worktrees;
- Large or multi-domain scope;
- cross-domain work;
- Wave existence;
- existence of a `G-xxx` convention.

**Packet count != composition risk.**  
**Worker/worktree count != composition risk.**

If one coherent execution can verify the cross-boundary behavior, or independently produced changes introduce no composition-specific invariant, an Integrator is unnecessary.

## Bounded composition precheck

Before selecting `NOT_NEEDED`, inspect only the relevant result boundaries and establish a positive basis that composition creates no new shared runtime behavior, Contract interaction, shared-state invariant, build/integration invariant, provider-consumer behavior, or cross-execution Integration Obligation.

Individual test PASS, absence of independent results, or absence of an explicit `G-xxx` marker is insufficient by itself. If material composition uncertainty remains, select Integrator NEEDED or return `INCONCLUSIVE` / upstream. Do not invoke an Integrator merely to decide that an Integrator is unnecessary.

Wave and Integrator are independent. A Wave may be needed for ordering/barriers while Integrator remains NOT_NEEDED when separate composition verification adds no value.

## Preconditions when activated

Confirm that the relevant results passed the required Verification level and that active Manifest/Gate/Contract evidence has no unresolved Design Delta or Impact Mismatch. Check Wave barrier state only when a Wave is active.

## Integration obligations

Use only task-relevant obligations resolved from project-native Rules / State / Sources. Project-specific conventions such as `G-xxx` may be used when present, but their existence alone does not activate Integration.

## Verification surface

Inspect only the boundaries needed for composition:
1. Contract version and semantics;
2. Ownership / Provider / Consumer;
3. dependencies among composed results;
4. relevant Integration Obligations;
5. runtime/integration tests that require composition;
6. merge/worktree conflicts or other composition-specific failures.

Distinguish `FAIL | IMPACT_MISMATCH | DESIGN_DELTA | INCONCLUSIVE`.

The Integrator does not merge or mutate shared state. It returns integration evidence and proposed updates to the Primary.
