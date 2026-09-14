---
name: design-feedback
description: Return implementation facts that conflict with the current design or Contract as a Design Delta. Use this when assumptions fail or an interface change may be required.
---

# Design Feedback

Do not silently absorb unexpected facts inside a Worker. Separate observation from proposal and return the issue to the Primary.

## Design Delta

```markdown
## DD-000: short name

### Observation
Confirmed fact and evidence.

### Expected
What the current Architecture or Contract expected.

### Delta
Difference between expected and actual behavior.

### Impact
Affected modules, Contracts, Packets, data, or users.

### Proposal
Recommended change and useful alternatives.

### Confidence
confirmed | probable | hypothesis
```

## Handling

1. A Subagent returns the Design Delta through `design_delta` in `strict-agent-result.schema.json` v2 and does not edit shared state.
2. The Primary records Observation and evidence only in resolved project-native State / Sources when persistence is useful. If no writable persistent State exists, keep it in the current execution result.
3. Resolve task-relevant Provider, Consumer, Ownership, dependency, and Integration Obligation information from project-native authority and actual code. Do not assume a fixed Harness file layout.
4. When a Contract changes, propagate only the bounded affected surface and close any required Manifest, Gate, reverification, or Wave under existing control semantics.
5. Limited deltas return to LUNA planning/design handling. Material boundary, broad Contract, or major technical-decision deltas may be evaluated through `$model-escalation` under existing uncertainty rules.
6. Only the Primary updates authoritative project-native Architecture / Contract / Decision / State sources after authority and write scope are resolved.

Do not confuse Observation with Confidence. Never change a Contract from hypothesis alone.
