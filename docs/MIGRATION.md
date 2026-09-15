# Migrating a supported legacy Beta installation

LUNAKO Harness can migrate only the explicitly enumerated historical Beta installation shapes that match the frozen legacy payload and ownership contracts validated by the project.

The migration boundary is intentionally narrow:

```text
exact supported legacy shape
→ SUPPORTED_LEGACY
→ explicit migrate or direct uninstall

unknown / drifted / mixed old installation
→ CONFLICT
→ no automatic repair
```

`source_repo` and `source_commit` are provenance only. Support is determined by the exact frozen payload and ownership evidence, not by a repository or commit string alone.

## Check the installation first

Run:

```bash
python3 scripts/lunako.py status /path/to/your/project
```

A supported historical installation reports `SUPPORTED_LEGACY` with a diagnostic subtype. If the installation reports `CONFLICT`, do not delete or rewrite files based on guesswork.

## Migrate to the canonical LUNAKO namespace

For `SUPPORTED_LEGACY`:

```bash
python3 scripts/lunako.py migrate /path/to/your/project
python3 scripts/lunako.py status /path/to/your/project
```

The tested successful transition is:

```text
SUPPORTED_LEGACY
→ migrate
→ CANONICAL / CLEAN
```

The migration replaces the supported legacy Harness-owned material with the canonical LUNAKO installation and writes the canonical ownership manifest at:

```text
.lunako-harness/install-manifest.json
```

The canonical Harness skill is:

```text
.agents/skills/lunako-harness/
```

For the tested legacy families, project-owned `AGENTS.md` and `.codex/config.toml` bytes outside the owned managed regions are preserved. Complete filesystem metadata preservation is not claimed.

## Remove a supported legacy installation instead

If you do not want to migrate, a `SUPPORTED_LEGACY` installation can be removed directly:

```bash
python3 scripts/lunako.py uninstall /path/to/your/project
```

Direct legacy uninstall removes only ownership attributable to one of the enumerated supported legacy shapes under the tested contracts. It does not silently create a canonical installation.

## CONFLICT recovery guidance

Examples of states that intentionally fail closed include:

- both canonical and legacy manifests present;
- legacy manifest with canonical residue;
- canonical manifest with legacy managed markers;
- modified managed legacy payload even when its manifest is rewritten to be self-consistent;
- unsupported or unknown legacy ownership shape.

Use the doctor for read-only diagnostics:

```bash
python3 scripts/lunako_doctor.py /path/to/your/project
```

When the state is `CONFLICT`:

1. do not delete, rewrite, or infer ownership automatically;
2. restore one coherent known state from version control, backup, or other authoritative frozen evidence;
3. rerun `lunako.py status` and the doctor;
4. retry migration or uninstall only after the installation classifies cleanly as a supported state.

LUNAKO does not provide an automatic CONFLICT repair engine.

## Rollback boundary

The tested rollback evidence covers injected filesystem/write (`OSError`) failure paths during migration and supported legacy uninstall.

It does **not** establish:

- arbitrary exception rollback;
- crash safety;
- process-kill safety;
- power-loss safety;
- concurrent mutation safety;
- ACID transactions.

See [`VALIDATION.md`](VALIDATION.md) for the complete tested public claim boundary.
