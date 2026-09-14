# LUNATIC HARNES

**Shape the task before you scale the model.**

> **Status: Beta (`v0.1.0-beta.1`)**
>
> LUNATIC HARNES is a public beta. Interfaces, execution policy, and supported model bindings may change before a stable release.

[Japanese README](README.ja.md)

## What it is

LUNATIC HARNES is a **Codex-oriented coding-agent harness** for structuring software-engineering work before increasing model capability or orchestration complexity.

Its normal path uses LUNA. Stronger-model escalation is reserved for unresolved architectural uncertainty or a specifically selected review/audit role rather than being triggered by task size alone.

```text
Structure determines execution shape.
Uncertainty determines architecture escalation.
Risk determines assurance.
Risk determines assurance, not impact discovery.
```

## Why use it

Coding-agent workflows often react to difficult work by adding more context, more agents, more process, or a stronger model. Those interventions address different failure modes.

LUNATIC HARNES separates them and activates only the mechanisms that are useful for the current task.

It is a good fit when you want to:

- shape a non-trivial coding task before escalating model capability;
- keep a lighter model on the normal execution path when the work can be made tractable through structure;
- escalate architecture selectively when meaningful uncertainty remains unresolved;
- avoid automatically turning a large task into a large multi-agent workflow;
- preserve the target repository's own rules, source authority, and acceptance criteria;
- make verification and completion obligations explicit when the task requires them.

## How it works

The Harness applies **minimum sufficient execution** and **Need-Based Activation**.

- **Task Shaping** keeps work in the largest coherent execution unit that can be handled safely.
- **Architecture Escalation** is driven by unresolved architecture uncertainty, not size alone.
- **Work Packet**, **Impact Manifest**, **Integration Wave**, **Integrator**, and **Handoff** are independent controls. One does not automatically activate the others.
- **Impact Discovery** determines what a change may affect and remains separate from Risk.
- **Verification and Assurance** scale with the obligations selected for the task.
- **Challenge** provides a bounded pre-edit check when a concrete implementation plan still depends on a material assumption.
- **Completion checks** close the controls that were actually selected.

The target project remains the authority for its own Rules, Task, State, Acceptance, Sources, and Deliverables. LUNATIC HARNES provides execution policy around that project-native information.

## Current support

The current beta is **Codex-oriented** and uses concrete agent bindings:

- `gpt-5.6-luna` for normal LUNA roles;
- `gpt-5.6-sol` for selected SOL roles.

Provider/model abstraction is not part of this beta. The package is defined by an explicit runtime inventory and is self-contained for the supported install lifecycle.

For the package and lifecycle behavior that has been directly tested, see [`docs/VALIDATION.md`](docs/VALIDATION.md).

## Quick Start

Prerequisites:

- Git;
- Python 3;
- a clean LUNATIC HARNES source checkout for `init` and `sync`;
- a target path that is the root of a Git repository.

Clone and validate the package:

```bash
git clone https://github.com/OsamuO/lunatic-harnes.git
cd lunatic-harnes
python3 scripts/validate_public_release.py
```

Install it into a Git project:

```bash
python3 scripts/lunatic.py init /path/to/your/project
python3 scripts/lunatic.py status /path/to/your/project
```

`init` installs the managed runtime and records it in:

```text
.lunatic-harnes/install-manifest.json
```

If the target already has an `AGENTS.md`, LUNATIC HARNES preserves the project-owned content and adds one managed binding block.

### Sync

```bash
python3 scripts/lunatic.py sync /path/to/your/project
```

`sync` synchronizes the target with the runtime files in the **current clean LUNATIC HARNES source checkout**. It does not pull or update from GitHub automatically. Update the source checkout first when newer source bytes are intended.

### Remove

```bash
python3 scripts/lunatic.py uninstall /path/to/your/project
```

For a clean installation, `uninstall` removes the managed runtime files, install manifest, and managed `AGENTS.md` block while preserving the project's original content.

## Using it after installation

You do not need a special LUNATIC HARNES prompt for ordinary work. Ask the coding agent to do the project task normally.

For non-trivial implementation, architecture, migration, or cross-boundary work, the managed binding directs the coding agent to the Harness policy. The Harness then decides what structure, coordination, escalation, impact reasoning, and verification are actually needed.

At a high level:

```text
project-native task
  -> resolve relevant project authority
  -> shape the work
  -> resolve architecture uncertainty
  -> activate only needed controls
  -> implement and verify
  -> close selected obligations
```

## Model-role separation

LUNATIC HARNES keeps stronger-model roles separate by purpose.

```text
sol_architect
  -> unresolved Architecture uncertainty

sol_decision_reviewer
  -> review of an already-decided consequential decision

sol_reviewer
  -> post-implementation External Audit
```

Task size alone does not select these roles.

## Minimal example

See [`examples/minimal-project/`](examples/minimal-project/) for a small onboarding walkthrough showing an existing `AGENTS.md`, managed-block insertion, status, and clean uninstall.

## Validation

The public package includes model-free validation for its package composition and tested install lifecycle.

```bash
python3 scripts/validate_public_release.py
```

A concise description of the tested scope is available in [`docs/VALIDATION.md`](docs/VALIDATION.md).

## Feedback

LUNATIC HARNES is in beta, and feedback from real project use is useful.

[GitHub Issues](https://github.com/OsamuO/lunatic-harnes/issues) are the preferred channel for installation problems, unclear documentation, unnecessary or missed Harness activation, manual recovery, task failures, and useful real-world cases.

Please share only project information you are comfortable making public. No telemetry, usage reporting, benchmark submission, or private project disclosure is required.

## License

Apache License 2.0. See [`LICENSE`](LICENSE).
