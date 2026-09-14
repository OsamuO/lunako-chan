---
name: low-token-mode
description: Switch to degraded low-consumption operation when model or token availability is constrained, or when the user explicitly requests lower consumption. Use one LUNA to implement, minimally verify, and checkpoint one unit at a time.
---

# Low Token Mode

Preserve project topology, Domains, Contracts, and Integration Waves while processing work sequentially with one LUNA.

## Operating rules

- If a writable project-native State checkpoint is already resolved, the Primary records low-token mode there briefly. If no dedicated State file exists, keep the mode only in current execution context; absence is not an error.
- Do not use parallel agents. Handle one execution unit at a time. Do not falsify hierarchical topology as single; only make coordination sequential.
- Avoid long planning. Materialize only the next smallest unit that can be completed.
- Read only the files and project State needed for the current step; do not use the full conversation as working memory.
- Keep Current State focused on the immediate step and do not reload the entire Run Ledger. Use `active-context.json` only when continuing an existing Large Project that already has it.
- Without subagent handoff, do not require a Typed Result. Compress results into a short checkpoint.
- Avoid broad refactors and unnecessary new abstractions; follow established project patterns.
- Run the most direct required verification for each unit before updating the checkpoint.
- Do not skip integration verification at Wave boundaries, and do not advance past a dependent Wave until required integration closure is complete.
- Record Contract or design mismatches even when small; do not silently absorb them.
- Stop when timeout, token budget, or no-progress limit is reached, preserving completed work and the blocker.

## Checkpoint format

When using a writable project-native State checkpoint, keep only the information needed to resume. A dedicated Harness Project State file is not required by the installed runtime.

```text
Mode:
low-token

Done:
Completed and verified work.

Current:
The one item currently being handled.

Known:
Confirmed facts needed on resume.

Next:
The next action.

Blocked:
Current blocker, or none.

Files:
Files relevant to the current step.
```

When resources recover, re-check unfinished work and Contracts. If a project-native State checkpoint is in use, synchronize it back to normal mode before resuming normal operation.
