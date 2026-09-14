# LUNATIC HARNES

**Shape the task before you scale the model.**

[English](README.md)

> **ステータス: Beta (`v0.1.0-beta.1`)**
>
> LUNATIC HARNESは現在パブリックBetaです。stable releaseまでにインターフェース、実行ポリシー、対応モデル構成などが変更される可能性があります。

## LUNATIC HARNESとは

LUNATIC HARNESは、**Codex向けのcoding-agent harness**です。

難しい仕事に対して、すぐに強いモデルや多数のagentへ切り替えるのではなく、**モデルを強くする前に、仕事そのものを解きやすい形へ整える**ことを中心に設計されています。

基本思想は次の4つです。

```text
Structure determines execution shape.
Uncertainty determines architecture escalation.
Risk determines assurance.
Risk determines assurance, not impact discovery.
```

タスクの構造、アーキテクチャ上の不確実性、変更の影響、実際のリスクを分けて扱い、必要な支援だけを有効化します。

## 何をするHarnessなのか

LUNATIC HARNESは、coding agentの実行を次のような観点で支援します。

- **Task Shaping** — 仕事を扱いやすい実行単位へ整える
- **Architecture Escalation** — 未解決のアーキテクチャ上の不確実性がある場合に強いモデルを使う
- **Need-Based Coordination** — Work Packet、Impact Manifest、Integration Wave、Integrator、Handoffなどを必要な場合だけ使う
- **Impact Discovery** — 変更がどこへ影響するかを確認する
- **Assurance / Verification** — リスクと選択されたobligationに応じて確認する
- **Challenge** — 重要な前提が残っている場合に、早すぎる設計確定を防ぐ
- **Completion checks** — 選択された確認事項が閉じているかを作業終了時に確認する

目的はHarnessそのものを使うことではなく、projectの仕事を構造化されたexecution policyの下で完了することです。

## どんな場合に向いているか

例えば、次のようなcoding-agent作業を想定しています。

- 強いモデルへ切り替える前にタスク構造を整理したい
- 必要な場合だけarchitecture escalationしたい
- 大きいという理由だけで不要なcoordinationを増やしたくない
- project固有のルールやsource authorityを保ちたい
- implementation、architecture change、migration、cross-boundary workを一定の実行方針で扱いたい

## 現在の対応範囲

現在のBetaは**Codex-oriented**です。

packaged agent definitionsでは、通常のLUNA rolesに`gpt-5.6-luna`、一部のSOL rolesに`gpt-5.6-sol`を使用します。

Beta期間中は、インターフェース、実行ポリシー、対応モデル構成などが変更される可能性があります。

実際に確認しているpackage / lifecycleの範囲は、英語版の[`docs/VALIDATION.md`](docs/VALIDATION.md)を参照してください。

## Quick Start

必要なもの:

- Git
- Python 3
- cleanなLUNATIC HARNES source checkout
- Git repositoryのrootとなるtarget project

公開packageをcloneして検証します。

```bash
git clone https://github.com/OsamuO/lunatic-harnes.git
cd lunatic-harnes
python3 scripts/validate_public_release.py
```

既存のGit projectへinstallします。

```bash
python3 scripts/lunatic.py init /path/to/your/project
python3 scripts/lunatic.py status /path/to/your/project
```

### Sync

```bash
python3 scripts/lunatic.py sync /path/to/your/project
```

`sync`は現在のcleanなLUNATIC HARNES source checkoutからruntime filesを同期します。GitHubから自動的にupdateを取得する機能ではありません。

### Uninstall

```bash
python3 scripts/lunatic.py uninstall /path/to/your/project
```

clean installationでは、managed runtime files、install manifest、managed `AGENTS.md` blockを削除し、project-owned contentを保持します。

## インストール後

特別なLUNATIC HARNES専用プロンプトを毎回入力することは前提にしていません。通常どおりcoding agentへ仕事を依頼します。

target repositoryへinstallされたbindingとHarness policyによって、必要に応じてtask shaping、architecture escalation、coordination、impact reasoning、verification、assuranceなどが使われます。

## Minimal Example

[`examples/minimal-project/`](examples/minimal-project/)に小さな導入例があります。

## Validation

public packageは、deterministic package compositionと次のinstallation lifecycleについてmodel-free validationを行っています。

```text
init -> status -> sync -> status -> uninstall
```

詳細は[`docs/VALIDATION.md`](docs/VALIDATION.md)を参照してください。

## Feedback

LUNATIC HARNESはBetaとして公開し、実際のproject利用から改善していきます。

問題や気づいた点があれば、GitHub Issuesを利用してください。feedbackは任意です。公開したくないproject情報を共有する必要はありません。

## License

Apache License 2.0. 詳しくは[`LICENSE`](LICENSE)を参照してください。

---

この日本語READMEはオンボーディング用です。LUNATIC HARNESの正式な仕様・runtime・validation documentsでは英語を基準とします。

**Canonical project language: English**
