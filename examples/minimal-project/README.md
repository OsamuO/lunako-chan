# Minimal Project Example

This disposable example shows the LUNAKO Harness lifecycle and ownership boundary without pretending to be an application benchmark.

The directory starts as an ordinary project with its own `AGENTS.md`. LUNAKO Harness adds one managed binding block while preserving those project-owned rules, reports the canonical installation state, and removes its attributed material on uninstall.

## 1. Inspect the project-owned rules

```bash
cat examples/minimal-project/AGENTS.md
```

Those rules belong to the project, not to LUNAKO Harness.

## 2. Make a disposable Git target

From the LUNAKO Harness checkout:

```bash
cp -R examples/minimal-project /tmp/lunako-minimal-project
cd /tmp/lunako-minimal-project
git init
```

The target passed to `lunako.py` must be the root of a Git repository.

Return to the LUNAKO Harness checkout:

```bash
cd /path/to/lunako-chan
```

## 3. Install

```bash
python3 scripts/lunako.py init /tmp/lunako-minimal-project
```

The original `# Minimal Project Rules` content remains, with exactly one managed AGENTS block delimited by:

```text
<!-- LUNAKO-HARNESS:BEGIN -->
...
<!-- LUNAKO-HARNESS:END -->
```

The canonical ownership manifest is:

```text
/tmp/lunako-minimal-project/.lunako-harness/install-manifest.json
```

and the canonical Harness skill is installed under:

```text
.agents/skills/lunako-harness/
```

## 4. Check status

```bash
python3 scripts/lunako.py status /tmp/lunako-minimal-project
```

For an unchanged canonical installation, status reports `CANONICAL` with a clean status.

## 5. What happens on non-trivial coding work?

The managed AGENTS block directs the coding agent to the LUNAKO Harness skill before non-trivial implementation, architecture, migration, or cross-boundary work.

The Harness keeps concerns separate:

- shape the execution unit from the task and project authority;
- treat unresolved architecture uncertainty separately from task size;
- activate coordination only when its specific failure mode is present;
- reason about actual impact rather than equating risk with impact discovery;
- perform the verification and assurance required by selected obligations.

## 6. Optional sync

```bash
python3 scripts/lunako.py sync /tmp/lunako-minimal-project
```

`sync` uses the runtime bytes in the current clean LUNAKO Harness source checkout. It does not fetch from GitHub automatically.

## 7. Uninstall

```bash
python3 scripts/lunako.py uninstall /tmp/lunako-minimal-project
```

For the tested canonical lifecycle, LUNAKO removes its managed runtime files, install manifest, AGENTS block, and managed project role-registration region while restoring the tested project-owned bytes.

Complete filesystem metadata preservation is not claimed. See [`../../docs/VALIDATION.md`](../../docs/VALIDATION.md) for the tested boundary.
