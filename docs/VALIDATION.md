# Validation

This document describes the behavior directly exercised for the current LUNATIC HARNES beta package.

> **Beta (`v0.1.0-beta.1`)** — interfaces, execution policy, and supported model bindings may change before a stable release.

## What is validated

The current public validation focuses on package composition, standalone installation lifecycle, and deterministic runtime boundary checks described below.

## Package composition

The packaged runtime is defined by an explicit-positive inventory in:

```text
runtime/lunatic-runtime-bundle.json
```

The current runtime inventory contains **49 managed runtime members**. Public packaging composes that inventory with a small explicit set of public-only documentation and example files.

The projection is deterministic: the same accepted source bytes and manifests produce the same staged paths and tree digest.

Internal release, evaluation-history, and maintainer-state artifacts are excluded from the public package.

## Standalone package validation

The package validator exercises a clean projected checkout as the complete package source. The tested lifecycle does not rely on files outside that package checkout.

Run:

```bash
python3 scripts/validate_public_release.py
```

The accepted lifecycle test covers:

```text
init -> status -> sync -> status -> uninstall
```

For the tested ordinary Git target, validation checks that:

- installation uses the packaged runtime inventory;
- the managed target-path set matches the runtime inventory;
- internal non-product paths are not installed;
- existing project-owned `AGENTS.md` content is preserved while the managed binding is present;
- `status` reports the tested clean installed state;
- `sync` uses the current clean source checkout;
- clean `uninstall` removes the managed installation and restores the tested non-`.git` baseline byte-for-byte;
- validation does not modify the package source checkout.

The package/lifecycle validation is model-free and records zero model calls and zero public-repository writes.

## Runtime control checks

The package includes deterministic helpers for selected runtime closure checks, including:

- terminal Assurance state closure;
- active Impact Manifest file-scope closure;
- bounded Project Interface resolution/reconciliation;
- protected project-owned `.agents/...` write-scope configuration on the supported setup.

These helpers validate the state or boundary supplied to them. Upstream task analysis and routing remain part of the coding-agent workflow rather than being replaced by these deterministic checks.

## Real-project signal

One accepted non-trivial real-project validation run completed an actual project change end-to-end with the installed Harness, passed the project regressions used by that run, and completed its terminal Assurance closure.

This is a bounded implementation signal from the tested case.

## Current implementation boundary

The current beta is Codex-oriented. Packaged agent definitions use:

- `gpt-5.6-luna` for normal LUNA roles;
- `gpt-5.6-sol` for selected SOL roles.

Provider/model abstraction is not part of the current beta.

## Scope

The package and lifecycle results above apply to the tested package, target fixture, and supported configuration described here. They should be interpreted within that tested scope.

For installation and normal use, see the [Quick Start](../README.md#quick-start).
