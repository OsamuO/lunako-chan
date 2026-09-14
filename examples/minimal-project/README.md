# Minimal Project Example

This example shows the public lifecycle and authority boundary without pretending to be an application benchmark or evaluation fixture.

The directory starts as an ordinary project with its own `AGENTS.md`. Lunatic Harnes should add one managed binding block while preserving those project-owned rules, report a clean installation, and remove its managed material cleanly on uninstall.

## 1. Inspect the project-owned rules

Read the example's existing `AGENTS.md` first. It belongs to the project, not to Lunatic Harnes.

```bash
cat examples/minimal-project/AGENTS.md
```

The important idea is that installation should not replace or reinterpret those existing rules.

## 2. Make a disposable Git target

From the Lunatic Harnes checkout, copy the example somewhere outside the source repository and initialize it as an ordinary Git repository:

```bash
cp -R examples/minimal-project /tmp/lunatic-minimal-project
cd /tmp/lunatic-minimal-project
git init
```

The target passed to `lunatic.py` must be the root of a Git repository. No additional Harness-specific Project State file is required.

Return to the Lunatic Harnes checkout before running the installer:

```bash
cd /path/to/lunatic-harnes
```

## 3. Install

```bash
python3 scripts/lunatic.py init /tmp/lunatic-minimal-project
```

After installation, inspect the target:

```bash
cat /tmp/lunatic-minimal-project/AGENTS.md
```

You should still see the original `# Minimal Project Rules` content, plus exactly one managed block delimited by:

```text
<!-- LUNATIC-HARNES:BEGIN -->
...
<!-- LUNATIC-HARNES:END -->
```

The runtime files installed by Lunatic Harnes are tracked in:

```text
/tmp/lunatic-minimal-project/.lunatic-harnes/install-manifest.json
```

## 4. Check status

```bash
python3 scripts/lunatic.py status /tmp/lunatic-minimal-project
```

For an unchanged installation, status should report a clean managed installation.

## 5. What happens on non-trivial coding work?

The managed `AGENTS.md` block tells the coding agent to read:

```text
.agents/skills/luna-harness/SKILL.md
```

before non-trivial implementation, architecture, migration, or cross-boundary work.

Conceptually, the installed Harness then keeps several concerns separate:

- shape the execution unit from the task and project authority;
- treat unresolved architecture uncertainty separately from task size;
- activate Work Packet / Impact Manifest / Integration Wave / Integrator / Handoff only when their specific failure modes are present;
- reason about actual impact rather than equating risk with impact discovery;
- perform the verification and assurance required by the selected obligations.

The example does not simulate a fake complex application just to trigger those mechanisms. It exists to make installation, project-rule preservation, and the execution-policy boundary visible.

## 6. Optional sync

If the Lunatic Harnes source checkout remains clean, you can synchronize the target to the runtime bytes in that checkout:

```bash
python3 scripts/lunatic.py sync /tmp/lunatic-minimal-project
```

`sync` does not fetch from GitHub. It synchronizes from the current local Lunatic Harnes source checkout.

## 7. Uninstall

```bash
python3 scripts/lunatic.py uninstall /tmp/lunatic-minimal-project
```

For a clean installation, Lunatic Harnes removes its managed runtime files, install manifest, and managed `AGENTS.md` block. The original project-owned `AGENTS.md` content remains.

The standalone package validation verifies byte-for-byte restoration of the tested ordinary-target baseline after this lifecycle.

For the tested scope of that claim, see [`../../docs/VALIDATION.md`](../../docs/VALIDATION.md).
