---
name: verification
description: Perform the minimum Internal Verification required by risk and boundary complexity. When independent verification is needed, derive actual semantics and check Declared <-> Actual consistency in both directions. Keep Decision Review and External Audit separate.
---

# Verification

Judge from the diff, relevant implementation, Contracts, ownership/dependency declarations, tests, and required runtime evidence rather than from the Worker's explanation.

Internal Verification asks whether declared design and actual implementation agree. External Audit separately asks whether the declared design itself is correct for the original requirement. Do not merge those responsibilities.

## Activation

Keep the existing levels:
- `direct`: Small and eligible Medium fast-path work; the Primary or same execution context checks tests and diff.
- `independent-luna`: start `luna_verifier` only when current Routing/Harness policy requires an independent verifier.

Bidirectional tracing does not itself activate Work Packet, Impact Manifest, Integration Wave, Integrator, Handoff, or External Audit.

## Direct verification

Check only what is needed:
1. evidence supporting Acceptance;
2. diff remains within Scope;
3. no unexpected Contract semantic or Ownership change;
4. unexpected impact returns `IMPACT_MISMATCH`; a broken design premise returns `DESIGN_DELTA`.

Do not create formal Gate artifacts for an ordinary fast path.

## Independent semantic verification

Use a bounded input slice: target diff, relevant implementation, relevant Contracts and ownership/dependency declarations, tests/runtime evidence, and the relevant Manifest only when active. Worker transcript is not evidence.

First derive a temporary **Actual Semantic Surface** from implementation. Include material provider guarantees, consumer dependencies, cross-boundary data/control dependencies, state changes, protected-operation checks, and relevant rejection/failure effects. Do not persist this as a new artifact.

Then identify any Architecture-significant semantic boundary already present in implementation. Material coordination, trust/authorization decisions, cross-boundary control decisions, failure semantics, state-transition authority, and system-level invariant enforcement are strong signals. Thin wrappers, simple delegation, logging, formatting, imports, class names, or layer names alone are not.

If significance cannot be determined from evidence, return `INCONCLUSIVE` instead of guessing `DESIGN_DELTA`.

## Bidirectional trace

A semantic-boundary PASS requires:

```text
Declared -> Actual = PASS
AND
Actual -> Declared = PASS
```

Apply this to the material categories involved in the task:
- Contract: declared guarantees/fields/assumptions exist, and actual consumer dependencies are declared;
- Dependency: declared cross-boundary dependencies exist, and material actual dependencies map back to the declared model;
- Ownership: declared ownership matches actual state mutation responsibility;
- Authorization: declared protected behavior matches actual enforcement and its declared responsibility boundary;
- Rejection/failure semantics: only where requirements explicitly constrain negative-path effects.

Do not infer a semantic dependency from an import alone. Distinguish reads from writes and forwarding from semantic ownership. Do not invent new policy; verify consistency among existing declarations, implementation, and evidence.

## Verdicts

Use existing statuses only:
- `PASS`: both directions pass with sufficient evidence;
- `FAIL`: implementation violates an established declaration and can be fixed without changing that declaration;
- `DESIGN_DELTA`: the declaration itself must change to represent material actual requirements or responsibilities;
- `IMPACT_MISMATCH`: actual impact exceeds the approved impact boundary;
- `INCONCLUSIVE`: evidence or environment is insufficient.

If it is unclear whether declaration or implementation should change, return the evidence and required upstream decision rather than choosing unilaterally.

## Evidence and output

Do not add a Semantic Trace artifact or new status. Reuse existing Typed Result, Verification evidence, and Consistency Gate fields. Keep findings concise: direction, category, declared evidence, actual evidence, mismatch, and required upstream action when needed.

Do not hide `IMPACT_MISMATCH` or `DESIGN_DELTA` as an ordinary FAIL retry.

Internal Verification and External Audit remain separate. If `external_audit=recommended|required`, preserve Blind Review -> Reconciliation and do not expose the Internal Verification verdict before Blind Review.

For `direct`, return a concise judgment with test/diff evidence. For independent handoff, use the existing strict Typed Result. Only the Primary persists formal runtime records.
