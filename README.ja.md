# LUNAKO Harness

**Shape the task before you scale the model.**

[English](README.md)

> **ステータス: Beta / unreleased main-line distribution candidate**
>
> このREADMEは、検証済みのLUNAKO Harness distribution candidateを説明します。新しいtagやGitHub Releaseが公開済みという意味ではありません。

## LUNAKO Harnessとは

LUNAKO Harnessは、**OpenAI Codex向けのagent harness**です。coding agentが扱う問題を、現在のモデルが解きやすい形へ変形し、そのtaskに必要な補助だけを選択して有効化します。

現在の実装では、通常の実行に**GPT-5.6 Luna**を使い、architecture escalationやreviewが必要な場合に**GPT-5.6 Sol**を選択的に使います。中核となる考え方は**Task Shaping**と**selective escalation**です。model capability、context、agents、processを最初から一律に拡大するのではなく、まず仕事の形を整え、必要になった補助だけを追加します。

現在のLuna/Sol bindingsは**present implementation**を表すものであり、LUNAKO Harnessの長期的なproduct definitionそのものではありません。LUNAKO Harnessは、問題をmodel-solvableな形へ変形し、必要なsupportだけを選択するHarnessとして定義します。Luna専用製品、low-cost-model専用Harness、general-purpose multi-agent frameworkとして固定しません。

現在成立している主な機能は次のとおりです。

- **Task Shaping** — 仕事を扱いやすい実行形へ整える
- **Selective escalation** — architecture uncertaintyやreview/assurance需要に応じてのみ強いroleを使う
- **Assurance / verification** — task sizeではなく実際のobligationとriskに応じて確認する
- **Explicit ownership** — install時にmanaged file / managed regionのownershipを記録する
- **Safe lifecycle** — tested stateについて`init / status / sync / migrate / uninstall`を明示的に扱う
- **Legacy migration** — 検証済みの列挙された旧Beta installation shapeだけをLUNAKO namespaceへ移行する

基本原則:

```text
Structure determines execution shape.
Uncertainty determines architecture escalation.
Risk determines assurance.
Risk determines assurance, not impact discovery.
```

target repository自身のrules、task、source code、acceptance criteria、project-owned contentがauthorityです。LUNAKO Harnessは、その周囲にmanaged execution policyを追加します。

## 現在の実装境界

現在のdistributionはOpenAI Codexを対象としています。packaged role definitionsでは通常実行をGPT-5.6 Lunaへ、選択されたarchitecture/review roleをGPT-5.6 Solへbindingしていますが、provider/model abstractionはclaimしていません。これらのbindingは現在の実装を説明するもので、将来のLUNAKO Harnessが必ずこのmodel構成に固定されるという意味ではありません。

検証済み範囲は[`docs/VALIDATION.md`](docs/VALIDATION.md)、旧Betaからのmigrationは[`docs/MIGRATION.md`](docs/MIGRATION.md)を参照してください。

## Quick Start

必要なもの:

- Git
- Python 3
- cleanなLUNAKO Harness source checkout
- Git repository rootであるtarget project

public repositoryをcloneし、standalone packageを検証します。

```bash
git clone https://github.com/OsamuO/lunako-chan.git
cd lunako-chan
python3 scripts/validate_public_release.py
```

Git projectへinstallします。

```bash
python3 scripts/lunako.py init /path/to/your/project
python3 scripts/lunako.py status /path/to/your/project
```

canonical installationのownership manifest:

```text
.lunako-harness/install-manifest.json
```

canonical Harness skill:

```text
.agents/skills/lunako-harness/
```

### Sync

```bash
python3 scripts/lunako.py sync /path/to/your/project
```

`sync`は現在のcleanなLUNAKO Harness source checkoutにあるruntime bytesを使います。GitHubから自動updateする機能ではありません。

### Supported legacy migration

```bash
python3 scripts/lunako.py status /path/to/your/project
python3 scripts/lunako.py migrate /path/to/your/project
```

migration対象は、検証済みの列挙されたlegacy installation shapeだけです。drifted / mixed / unsupportedな旧installationは`CONFLICT`としてfail closedし、ownershipを推測した自動repairは行いません。詳細は[`docs/MIGRATION.md`](docs/MIGRATION.md)を参照してください。

### Uninstall

```bash
python3 scripts/lunako.py uninstall /path/to/your/project
```

canonical installationおよび列挙されたsupported legacy shapeについて、tested ownership contractでLUNAKOに帰属できるmaterialだけを削除します。

## インストール後

通常利用でLUNAKO専用promptを毎回入力することは前提にしていません。通常どおりcoding agentへproject taskを依頼します。

managed bindingを通じて、必要に応じてtask shaping、architecture escalation、coordination、impact reasoning、verification、assuranceを選択します。

## Minimal Example

[`examples/minimal-project/`](examples/minimal-project/)に、既存project rules、canonical managed markers、status、sync、uninstallを確認するdisposable exampleがあります。

## Validation

cleanなprojected/public checkoutから実行します。

```bash
python3 scripts/validate_public_release.py
```

standalone validatorはdevelopment repositoryへread-backせず、package内のdependency closureとtested canonical lifecycleを確認します。詳細は[`docs/VALIDATION.md`](docs/VALIDATION.md)を参照してください。

## Historical Beta

`v0.1.0-beta.1`はlegacy product namespaceを使用したhistorical public Betaです。LUNAKO Harnessはmigration documentに列挙された旧installation shapeについてのみbounded compatibilityを持ちます。任意に変更された旧installationまでsupportするという意味ではありません。

## Feedback

installation、documentation、lifecycle behaviorに関するfeedbackは`OsamuO/lunako-chan`のGitHub Issuesを利用してください。公開したくないproject情報を共有する必要はありません。

## License

Apache License 2.0. [`LICENSE`](LICENSE)を参照してください。

---

この日本語READMEはオンボーディング用です。仕様・runtime・validation documentsでは英語を基準とします。

**Canonical project language: English**
