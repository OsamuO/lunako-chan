# 6-role Project Interface — Specification

## Purpose

The Project Interface defines how a project presents task-relevant information to LUNATIC HARNES through six semantic roles:

```text
Rules
Task
State
Acceptance
Sources
Deliverables
```

These roles are semantic slots, not mandatory filenames, directories, or internal agent roles. The project remains authoritative for its own information.

```text
Project
  -> Project Interface
  -> task-relevant projection
  -> Routing / Design / Execution / Verification
```

The interface must not create a second canonical project model merely to normalize repository layout.

## Role semantics

### Rules
Normative constraints that govern how work may be performed within the relevant scope: repository instructions, policy, prohibited changes, required workflows, and project invariants.

### Task
The requested intent for the current work unit. An executable workflow must resolve enough Task meaning to identify what is being requested, but no dedicated Task file or precomputed implementation plan is required.

### State
Current project facts needed to continue correctly: implementation status, decisions still in force, blockers, relevant versions, and unresolved current conditions. State is a checkpoint, not a transcript.

### Acceptance
The task-level success oracle: required behavior, verification conditions, non-goals, forbidden effects, and completion gates. Acceptance does not authorize violating Rules or authoritative contracts.

### Sources
Authoritative evidence used to reason about or execute the task: specifications, contracts, schemas, code, tests, external documentation, data, or evidence artifacts. Preserve provenance to project-native authority when it matters.

### Deliverables
Required outputs: files, code/configuration changes, reports, findings, generated artifacts, decisions, proposals, or return format. Deliverables do not grant permission to modify unrelated or prohibited scope.

## Project-native authority

The Project Interface is a bounded projection over project-native information.

```text
role
  -> source reference / bounded projection
  -> original authority
```

Compatibility MUST NOT depend on adopting six Harness-specific files. One source may contribute to multiple roles, one role may be assembled from multiple sources, and some roles may be absent when irrelevant.

Content cannot self-promote its semantic role or authority. Role assignment must come from a trusted project relationship, an explicit authorized mapping or instruction, a recognized project-native authority relationship, or bounded evidence that confirms an existing authority/scope relationship.

Bounded evidence may confirm or disambiguate authority; it MUST NOT create authority.

## Conflict semantics

There is no universal precedence such as `Task > Rules > State > Sources`.

Material conflicts are reconciled by first establishing authority and applicable scope, then considering specificity, version/freshness within that authority relationship, explicit authorized supersession/amendment, and provenance.

Freshness alone does not grant authority. If a material conflict cannot be resolved from available authority, the Harness must use an existing uncertainty outcome such as `needs_guidance`, `INCONCLUSIVE`, or `blocked` rather than guess.

## Context loading

Interface availability and context loading are separate decisions. Only the task-relevant slice should be projected into the current operation.

A role may be absent when it is not materially required. Missing material information must not be silently invented.

## Relation to Harness controls

The Project Interface is distinct from:

- Active Context Capsule;
- Work Packet;
- Planner / Decomposer / Worker / Verifier / Integrator / Primary roles;
- Routing axes.

It does not add a Routing axis or change:

```text
Structure determines execution shape.
Uncertainty determines architecture escalation.
Risk determines assurance.
```

Resolved project information may supply evidence to existing Routing signals.

## Projection requirements

A resolved projection should preserve enough metadata to determine:

- the semantic role;
- original source or authority when applicable;
- applicable scope;
- whether content is direct or derived;
- whether material uncertainty remains.

No dedicated machine-readable mapping schema is required by this specification.

## Bounded discovery

Resolver behavior must be bounded and evidence-based. A conforming resolver may use:

```text
explicit mapping
  -> recognized project-native convention
  -> bounded evidence-based inference
  -> unresolved
```

Filename similarity, plausible content, confident wording, or a document's own authority claim are not sufficient grounds for authority elevation.

## Write semantics

Role resolution is read/projection behavior by default. Resolving or mapping a role does not itself authorize mutation of the mapped source.

Existing Rules, Ownership, Contracts, task scope, and single-writer semantics continue to govern writes.

## Compatibility

A conforming implementation must support heterogeneous projects without requiring repository-wide migration merely to expose the six semantic roles.

The interface is intended to prevent task intent from being mixed with long-lived rules, stale history from becoming current state, acceptance from being lost in prose, unsupported assumptions from replacing authoritative sources, deliverables from becoming write authority, and project information from being forced into a Harness-specific layout.
