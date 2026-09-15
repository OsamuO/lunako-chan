# LUNAKO Harness

**Shape the task before you scale the model.**

> **Status: Beta / unreleased main-line distribution candidate**
>
> This documentation describes the validated LUNAKO Harness distribution candidate. It is not a claim that a new tag or GitHub Release has been published.

[日本語](README.ja.md)

## What it is

LUNAKO Harness is an **agent harness for OpenAI Codex**. It helps a **coding agent** by reshaping a problem into a form the current model can solve, then activating only the support the task needs.

The current implementation uses **GPT-5.6 Luna** for normal execution and **GPT-5.6 Sol** selectively for architecture escalation and review. Its core approach is **Task Shaping** plus **selective escalation**: rather than scaling model capability, context, agents, and process by default, LUNAKO shapes the work first and adds stronger assistance only when the task justifies it.

Current Luna/Sol bindings describe the present implementation, not the long-term product boundary. LUNAKO Harness is defined more broadly by shaping problems into model-solvable forms and selecting only the necessary support. It is not defined as a Luna-only product, a low-cost-model harness, or a general-purpose multi-agent framework.

It keeps several concerns separate instead of treating every difficult task as the same problem:

- **Task Shaping** selects a coherent execution shape for the work.
- **Selective escalation** uses stronger architecture/review roles only when the corresponding uncertainty or assurance need exists.
- **Assurance and verification** are selected from actual obligations and risk rather than task size alone.
- **Explicit ownership** records the files and managed regions owned by the installation.
- **Safe lifecycle operations** provide deterministic `init`, `status`, `sync`, `migrate`, and `uninstall` behavior for the tested states.
- **Legacy migration** supports only the explicitly enumerated historical Beta installation shapes validated by the project.

Core operating principles:

```text
Structure determines execution shape.
Uncertainty determines architecture escalation.
Risk determines assurance.
Risk determines assurance, not impact discovery.
```

The target repository remains the authority for its own rules, task, source code, acceptance criteria, and project-owned content. LUNAKO Harness adds a managed execution-policy layer around that authority.

## Current implementation boundary

The current distribution targets OpenAI Codex. Its packaged role definitions currently bind normal execution to GPT-5.6 Luna and selected architecture/review roles to GPT-5.6 Sol; provider/model abstraction is not claimed. Those bindings describe the current implementation rather than defining what LUNAKO Harness must remain in future versions.

The lifecycle and compatibility claims are intentionally bounded. See [`docs/VALIDATION.md`](docs/VALIDATION.md) for the tested scope and [`docs/MIGRATION.md`](docs/MIGRATION.md) for supported legacy migration.

## Quick Start

Prerequisites:

- Git
- Python 3
- a clean LUNAKO Harness source checkout
- a target path that is the root of a Git repository

Clone the public repository and validate the standalone package:

```bash
git clone https://github.com/OsamuO/lunako-chan.git
cd lunako-chan
python3 scripts/validate_public_release.py
```

Install into a Git project:

```bash
python3 scripts/lunako.py init /path/to/your/project
python3 scripts/lunako.py status /path/to/your/project
```

A canonical installation records ownership in:

```text
.lunako-harness/install-manifest.json
```

and binds the Harness through:

```text
.agents/skills/lunako-harness/
```

Existing project-owned `AGENTS.md` and `.codex/config.toml` content is preserved on the tested byte-preservation surface while LUNAKO-managed regions are present.

### Sync

```bash
python3 scripts/lunako.py sync /path/to/your/project
```

`sync` uses runtime files from the current clean LUNAKO Harness source checkout. It does not fetch updates from GitHub automatically.

### Migrate a supported legacy installation

```bash
python3 scripts/lunako.py status /path/to/your/project
python3 scripts/lunako.py migrate /path/to/your/project
```

Migration is available only for the enumerated frozen legacy installation shapes. Drifted, mixed, or unsupported old installations fail closed as `CONFLICT`; LUNAKO does not automatically infer ownership or repair them. See [`docs/MIGRATION.md`](docs/MIGRATION.md).

### Uninstall

```bash
python3 scripts/lunako.py uninstall /path/to/your/project
```

`uninstall` supports canonical installations and the enumerated supported legacy shapes. It removes only ownership that the lifecycle can attribute to the Harness under the tested contracts.

## Using it after installation

Ordinary use does not require a special LUNAKO prompt. Ask the coding agent to perform the project task normally.

For non-trivial implementation, architecture, migration, or cross-boundary work, the managed binding points the agent to the Harness policy. The Harness can then shape the task, resolve architecture uncertainty, activate coordination only when justified, and close selected verification/assurance obligations.

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

The currently packaged logical roles separate purposes rather than treating a stronger model as a universal fallback.

```text
sol_architect
  -> unresolved architecture uncertainty

sol_decision_reviewer
  -> review of an already-decided consequential decision

sol_reviewer
  -> post-implementation external audit
```

Task size alone does not select these roles.

## Minimal example

See [`examples/minimal-project/`](examples/minimal-project/) for a disposable onboarding walkthrough with existing project-owned rules, canonical managed markers, status, sync, and clean uninstall.

## Validation

Run the standalone package validator from a clean projected/public checkout:

```bash
python3 scripts/validate_public_release.py
```

The validator exercises the tested canonical lifecycle and checks package dependency closure without reading back from the development repository. Detailed boundaries are in [`docs/VALIDATION.md`](docs/VALIDATION.md).

## Historical Beta

`v0.1.0-beta.1` is the historical public Beta and used the legacy product namespace. LUNAKO Harness retains bounded compatibility for the enumerated legacy installation shapes described in the migration documentation. This does not mean arbitrary historical or modified installations are supported.

## Feedback

Use GitHub Issues in `OsamuO/lunako-chan` for installation problems, documentation issues, lifecycle failures, or useful real-world cases. Share only information you are comfortable making public.

## License

Apache License 2.0. See [`LICENSE`](LICENSE).
