---
name: external-audit
description: Perform a SOL External Audit by inferring from the original requirement and implementation before comparing against Harness declarations. Activate only from Assurance signals, never from scale alone.
---

# External Audit

The purpose is not to repeat internal Consistency checks. It is to challenge whether the Harness itself, its design assumptions, and its tests may share the same mistake.

External Audit does not replace Internal Verification, Integration, or High-risk Decision Review. Internal Verification checks implementation against declared design. Decision Review checks an already-decided high-risk decision. External Audit asks whether the declarations themselves are correct for the original requirement.

## Trigger

Do not run by default. Use Assurance signals:
- material product/system risk such as authorization, irreversibility, migration compatibility, financial impact, or public API compatibility;
- milestone criticality, release significance, or difficult rollback;
- material shared-assumption risk across internal reviewers/artifacts;
- explicit audit request;
- test gaps may increase audit value, but a test gap alone is at most recommended.

Default policy:

```text
explicit audit request                  -> required
high product/system risk                -> required
critical milestone/release              -> required
high shared-assumption risk             -> required
material risk/milestone/shared concern  -> recommended
material/severe test gap only           -> recommended at most
none                                     -> not-needed
```

Large or multi-domain scale is not a trigger. LUNA-only execution is not a trigger by itself.

## Pass 1: Blind Review

Avoid anchoring on Harness conclusions.

Primary inputs:
- original requirement / user goal;
- original Acceptance / non-goals;
- implementation or target diff;
- tests and results;
- required external specification or platform constraint.

Do not provide internal Architecture conclusions, Impact Manifest, Consistency Gate verdict, Verifier/Integrator verdict, agent transcript, or prior design discussion before Blind Review unless they are themselves part of the original authority surface.

Independently infer only what is needed to assess the work:
1. actual domain and ownership boundaries;
2. provider/consumer semantics and Contracts;
3. trust boundaries, failure modes, and state transitions;
4. invariants required by the original requirement;
5. what tests do and do not demonstrate;
6. material omissions, hidden dependencies, unsafe defaults, unnecessary complexity, or missing negative cases.

Do not force this model to match Harness terminology.

## Pass 2: Reconciliation

After the Blind Review is fixed, compare it with the relevant internal declarations and evidence:
- Architecture;
- Contracts;
- Domain Map / Dependency Graph;
- Relevant Consistency Spine;
- active Work Packet / Impact Manifest;
- Verification / Integration evidence.

Compare the independently inferred system with the Harness-declared system. Focus on material mismatches in requirement mapping, Ownership, Contracts, consumers, test assumptions, shared blind spots, unnecessary coordination/abstraction, and relevant product/data/migration/public boundaries.

## Verdict

Reuse existing statuses:
- `PASS`: no material external contradiction;
- `FAIL`: material local defect without requiring an upstream design change;
- `DESIGN_DELTA`: Architecture, Contract, Ownership, or requirement interpretation must change upstream;
- `INCONCLUSIVE`: evidence, specification, or execution environment is insufficient.

Finding severity is `critical | major | minor | observation`.

## Output

The Auditor does not edit files. Return only:
- `verdict`;
- `blind_model`: concise independent model from Blind Review;
- `findings`: severity, evidence, impact, recommended action;
- `reconciliation`;
- `test_gaps`;
- `residual_risk`;
- `evidence_missing`.

If no material issue is found, return a concise PASS with reviewed scope and residual risk.

## Anti-anchoring rules

- Do not read Internal Verification/Integration verdicts before Blind Review.
- Do not assume Harness terminology or artifacts are correct merely because they exist.
- Treat requirement, code/diff, tests, and external specifications as primary evidence.
- Do not turn Audit into a redesign exercise; report only material requirement-driven differences.
- Do not omit material evidence-supported findings merely to simplify the result.

## Persistence

Persist Audit results only when an Audit was actually performed. Do not create Audit artifacts for unaudited tasks. On re-audit, inspect the correction diff and primary evidence rather than repeating the prior conclusion.
