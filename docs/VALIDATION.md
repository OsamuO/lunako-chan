# Validation

This document describes the behavior directly exercised for the current LUNAKO Harness distribution candidate.

> **Status: Beta / unreleased main-line distribution candidate.** A new tag or GitHub Release is not implied by this document.

## Package composition

The canonical runtime inventory is:

```text
runtime/lunako-runtime-bundle.json
```

The N3 distribution authority freezes **50 managed runtime mappings** and their mapping fingerprint. Public projection composes that runtime inventory with an explicit-positive set of public documentation, examples, CLI modules, doctor, and standalone validation files.

Projection is built from a clean candidate Git tree, not from untracked working-tree bytes. The same validated candidate must produce the same staged path set and tree digest.

Internal evaluation, release-state, project-state, work-packet, and mutable `.luna-runtime/` material is excluded from the public package.

## Standalone public package validation

Run from a clean projected/public Git checkout:

```bash
python3 scripts/validate_public_release.py
```

The validator uses only files in that checkout plus normal system Python/Git. It does not import or read back from the development repository.

It first checks CLI/module dependency closure, including:

```text
scripts/lunako.py
scripts/lunako_core.py
scripts/lunako_ownership.py
scripts/lunako_state.py
scripts/lunako_legacy_frozen.py
scripts/lunako_contract.py
scripts/lunako_diagnostics.py
scripts/lunako_doctor.py
scripts/lunako_permission_profile.py
```

and verifies that at least the canonical CLI and doctor can start from the standalone package:

```bash
python3 scripts/lunako.py --help
python3 scripts/lunako_doctor.py --help
```

## Canonical lifecycle exercised by the public validator

The standalone validator exercises:

```text
init
→ status
→ sync
→ status
→ uninstall
```

For the tested ordinary Git target it verifies:

- canonical manifest schema 3;
- `product_id = lunako-harness`;
- `namespace_version = 1`;
- installed managed target set exactly equals the packaged runtime inventory;
- canonical `LUNAKO-HARNESS` AGENTS marker appears exactly once;
- the canonical project role-registration region is present while installed;
- tested project-owned `AGENTS.md` and `.codex/config.toml` bytes outside managed regions are preserved;
- an unrelated project sentinel is preserved;
- forbidden internal development paths are not installed;
- `sync` does not change runtime bytes without source drift;
- uninstall restores the tested non-`.git` target baseline bytes;
- the public package source checkout remains unchanged.

This is a tested user-content/byte-preservation claim. **Complete filesystem metadata preservation, including original file mode preservation, is not established.**

## Legacy compatibility validated by N1/N2

The product-level validation has established the following bounded behavior for the enumerated frozen legacy installation shapes:

- supported legacy detection;
- explicit legacy-to-canonical migration;
- direct supported-legacy uninstall;
- fail-closed rejection of drifted, mixed, unknown, or unsupported legacy states;
- read-only CONFLICT diagnostics and recovery guidance.

See [`MIGRATION.md`](MIGRATION.md) for the user-facing migration procedure.

The public standalone validator does not duplicate the complete L1A/L1B/L2 migration matrix; full migration conformance remains a separate development validation concern.

## Permission helper boundary

The packaged permission helper requires the tested clean canonical ownership state before emitting a profile. Validation covers refusal when managed canonical bytes drift or required ownership records are removed.

This is a bounded ownership guard, not a general proof of every possible filesystem mutation.

## Rollback boundary

Tested N2 evidence covers injected filesystem/write (`OSError`) failure paths during migration and supported legacy uninstall, with restoration of the tested pre-operation snapshot.

The accepted wording is:

```text
ESTABLISHED_FOR_TESTED_INJECTED_FILESYSTEM_WRITE_FAILURES
```

The project does **not** claim:

- arbitrary legacy migration;
- arbitrary exception rollback;
- crash safety;
- process-kill safety;
- power-loss safety;
- concurrent mutation safety;
- ACID transactions;
- automatic CONFLICT repair;
- complete filesystem metadata preservation.

## Runtime control checks

The package also contains deterministic helpers for selected runtime closure checks, including Assurance closure, Impact Manifest file-scope closure, Project Interface resolution/reconciliation, and clean canonical permission-profile generation.

These helpers validate their supplied state or ownership boundary. They do not replace upstream task analysis, routing, or model reasoning.

## Current implementation boundary

The current distribution is Codex-oriented. Packaged role definitions use LUNA and SOL logical role bindings. Provider/model abstraction and D3 independent read-only verifier enforcement are not established by this public distribution claim.

## Scope

All statements above are bounded to the tested package, fixtures, and lifecycle paths. They should not be generalized to arbitrary historical installations, arbitrary interruption modes, or untested filesystem metadata semantics.

For normal installation and use, see the [Quick Start](../README.md#quick-start).
