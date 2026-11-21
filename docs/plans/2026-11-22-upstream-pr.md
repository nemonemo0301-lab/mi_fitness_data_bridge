# 上流（shkyyy18）への PR の出し方・設計メモ

- 作成日: 2026-11-22
- 作成: Claude Code
- 担当: Claude Code
- ステータス: draft（ネモさんの判断が必要な点が 3 つある。下の「3.4 決めてほしいこと」）

## 1. 目的

フォーク独自の 3 機能（`serve --read-only`、passToken の再読み込み、心拍・ストレスの 1 日ずつ取得）と、ドキュメントを上流に還元する方法を決める。
PR を何本に分けるか、どのブランチから出すか、CHANGELOG をどう扱うかを決め、実装の作業手順まで落とし込む。
優先順位は「自分用の安定運用が先」なので、急がない。毎朝の CSV 出力に使っている `docs/agent-collab` は、この作業では変更しない。

## 2. 調査結果（2026-11-22 時点）

### 2.1 上流の状態

- 上流の `origin/main` は `6399cd0` まで進んだ（`fix: keep CLI status output compatible with GBK terminals (#22)`、2026-11-20）。
- **フォークで取り込んだ GBK 対応 `0d5504f` と、上流の #22 `6399cd0` は、`git patch-id --stable` が一致する**（`src` と `tests` について。もとの上流ブランチ `01a7f1f` も同じ）。つまり GBK 対応は上流に出す必要がない。上流 `main` を基準に作業ブランチを作れば、最初から入っている。
- 上流で未マージのブランチは `fix/cli-gbk-status-markers`（#22 でマージ済み）、`fix/body-muscle-mass-units`（#21 でマージ済み）、`fix/glama-tool-quality`（`origin/main` からの差分なし）。フォークの変更と競合する進行中の作業はない。
- 上流は「1 つのテーマ = 1 本の PR」で受け入れている（#17 FDS 詳細、#21 筋肉量の単位、#22 GBK）。

### 2.2 フォークのコミットを上流 `main`（6399cd0）に単独で載せた結果

一時的な worktree で `cherry-pick -n` し、pytest と ruff を流した（合成データのみ。worktree は削除済み）。上流 `main` だけの場合は 379 件。

| コミット | 内容 | 単独で載るか | pytest |
| --- | --- | --- | --- |
| `2486c10` | passToken の再読み込み | そのまま載る | 382 passed |
| `63c7282` | 心拍・ストレスを 1 日ずつ取得 | そのまま載る | 382 passed |
| `9f3c4ee` | `serve --read-only` | `CHANGELOG.md` のみ衝突（`[Unreleased]` 先頭の隣接行。上流の GBK 項目とぶつかる） | 383 passed |
| 3 つすべて | | 同上 | 389 passed、ruff 通過 |

- 3 つは互いに独立していて、どの順番で出しても成り立つ（`2486c10` と `63c7282` はどちらも `adapters/mi_fitness_cloud.py` を変えるが、別の場所）。
- `2486c10` と `63c7282` の CHANGELOG 項目は `feat/serve-read-only` には入っておらず、`docs/agent-collab` の `185291a` にしかない。上流 `main` から PR 用ブランチを作るなら、該当する 1 行をそれぞれの PR に書き足せばよい。`feat/serve-read-only` を作り直す必要はない。
- フォークにしかないテスト補強が 1 つある：`7f86cce` の `tests/test_cli_security.py`（L303 付近）。上流 #22 のあとも、上流には `assert "✅ daily_activity" not in output` が残っていて、これは常に真になる。フォークでは `[X] daily_activity: status=error` が出ることを確かめる形に直した。小さな PR として上流に出せる。

### 2.3 上流の貢献ルール（`CONTRIBUTING.md` と `.github/PULL_REQUEST_TEMPLATE.md`）

- 合成データのみを使うこと、pytest と ruff を通すこと、非公式であることの声明と MIT の帰属を残すこと。この 3 機能はどれも満たしている。
- **ライセンスの条件**：PR を出すと、(1) 貢献部分を AGPL-3.0-only で提供し、(2) メンテナー（shkyyy18）に、商用ライセンスを含む別の条件で再ライセンスする永続的な権利を与えることに同意したことになる。PR テンプレートにも同意のチェック項目がある。**これはネモさん本人が判断すること**で、ツールが代わりにチェックしてはいけない。

### 2.4 ドキュメントを上流に出すときの問題

2026-11-19 に「ドキュメント（3 ツール併用ルール・CLAUDE.md・PROGRESS.md）も上流に出す」と決めた。ただし、中身を見ると、そのままでは出せないものが多い。

| ファイル | 問題 |
| --- | --- |
| `docs/PROGRESS.md` | このフォークの作業記録そのもの（ネモさん、毎朝の CSV 出力、フォークのブランチ状態）。上流には意味がない |
| `CLAUDE.md` | 「やってはいけないこと」に、個人の出力先（Documents\health）、`health/nari`、`fork` 以外に push しないこと、が入っている。上流用には書き直しが必要 |
| `AGENTS.md` の「3ツール併用ルール」 | 日本語で書かれているが、上流の `AGENTS.md` は中国語（ほかのドキュメントは英語）。また、ネモさんが使っている 3 ツールの組み合わせが前提になっている |
| `docs/plans/_template.md` | 汎用的なので出しやすい（同じく言語の問題はある） |
| `docs/plans/2026-11-19-upstream-check.md`、`test-overview.md`、このメモ | フォークの作業記録。上流には出さない |

## 3. 設計方針

### 3.1 PR の分け方（推奨）

**機能はテーマごとに分けて 3 本、ドキュメントは別にする。**

1. PR-A：passToken の再読み込み（`2486c10`）。バグ修正で、長時間動いているサーバーが実際に失敗する問題。
2. PR-B：心拍・ストレスを 1 日ずつ取得（`63c7282`）。バグ修正で、データが黙って欠ける問題。
3. PR-C：`serve --read-only`（`9f3c4ee`）。新機能で、README も変わる。
4. （任意）PR-D：`tests/test_cli_security.py` の、常に真になる検証の補強（`7f86cce` のテスト部分だけ）。
5. ドキュメントの PR は、3.3 の判断のあとで決める。

出す順番は A → B → C（バグ修正が先、変更の小さいものが先）。どれも単独で通ることを確かめてあるので、上流がどれかを断っても、ほかには影響しない。

### 3.2 ブランチの作り方

- PR ごとに、最新の `origin/main` から作業ブランチを作る（例：`upstream/token-reload`、`upstream/per-day-hr-stress`、`upstream/serve-read-only`、`upstream/cli-security-assert`）。
- `git cherry-pick -x <コミット>` で取り込み、`CHANGELOG.md` の `[Unreleased]` にその PR の 1 項目だけを書き足す。項目の文面は `docs/agent-collab` の CHANGELOG からそのまま使う。
- push 先は `fork` だけ。上流への PR は、フォークのブランチから `shkyyy18/mi_fitness_data_bridge` の `main` に向けて作る。
- PR を作ること自体は外部への公開になるので、**ネモさんの了承を得てから行う**（ライセンス同意のチェックもネモさんがする）。この環境には `gh` が入っていないので、PR はブラウザで作るか、`gh` を入れてから作る。
- PR の本文は上流のテンプレート（Summary / Validation / Data and security / Licensing / Compatibility）に合わせ、英語で書く（上流の README.en.md・CHANGELOG・コミットメッセージに合わせる）。

### 3.3 ドキュメント PR の扱い（推奨）

- `docs/PROGRESS.md`、`CLAUDE.md`（いまの内容のまま）、フォークの設計メモは上流に出さない。
- 出すなら、汎用的な部分だけにする：`docs/plans/_template.md` と、AGENTS.md の 3 ツール併用ルールから個人の事情を除いたもの。上流の書き方に合わせて英語（または中国語）に訳す。
- 機能 PR が受け入れられ、上流がこうした進め方に興味を示してからでも遅くない。機能 PR とは混ぜない（上流がレビューしにくくなるため）。

### 3.4 決めてほしいこと（ネモさん）

1. **ライセンスの条件**（2.3）に同意するか。同意しないなら、PR の前に Issue で相談するのが上流の決まり。
2. **ドキュメント PR**：上の 3.3 のとおり、汎用部分だけにする・訳す・後回しにする、でよいか。それとも、2026-11-19 の決定どおり、まとめて出したいか。
3. **PR-D**（テスト補強）も出すか。

### 3.5 選ばなかった案

- **機能 3 つを 1 本の PR にまとめる**：上流は 1 テーマ 1 本で受け入れている。また、1 つに直してほしい点があると、残りも止まってしまう。
- **`feat/serve-read-only` からそのまま PR を出す**：このブランチの基点は古い上流 `main`（`91ea4f1`）で、3 つのテーマが混ざっている。CHANGELOG の 2 項目も入っていない。
- **`docs/agent-collab` から出す**：ドキュメントと GBK 対応（上流にもう入っている）が混ざる。また、毎朝の CSV 出力に使っているブランチなので、PR のために書き換えたくない。

### 3.6 フォーク側への影響

- この作業では `docs/agent-collab` と `feat/serve-read-only` を変更しない。毎朝の CSV 出力には影響しない。
- 参考：`docs/agent-collab` に上流 `main`（6399cd0）をマージした場合の衝突は、`CHANGELOG.md` だけだった（`git merge-tree` で確認。実際のマージはしていない）。フォークを上流に追従させるかどうかは、「フォークの main」の質問と合わせて決める。

## 4. 実装タスク（Claude Code 向け）

3.4 の 1 にネモさんが同意してから始める。

- [ ] `git fetch origin` で上流 `main` の最新を確認し、2.1 の前提（GBK 対応が上流に入っている、競合する作業がない）が変わっていないか見る
- [ ] PR-A：`origin/main` から `upstream/token-reload` を作り、`cherry-pick -x 2486c10`、CHANGELOG に 1 項目を足す（対象：`src/mi_fitness_mcp/adapters/mi_fitness_cloud.py`、`tests/conftest.py`、`tests/test_token_reload.py`、`CHANGELOG.md`）
- [ ] PR-B：同じ手順で `upstream/per-day-hr-stress`（`cherry-pick -x 63c7282`。対象：`adapters/mi_fitness_cloud.py`、`tests/test_adapter_time_guard.py`、`tests/test_per_day_fetch.py`、`CHANGELOG.md`）
- [ ] PR-C：同じ手順で `upstream/serve-read-only`（`cherry-pick -x 9f3c4ee`。CHANGELOG の衝突は、上流の GBK 項目とフォークの項目を両方残して解消する）
- [ ] （3.4 の 3 で出すと決めた場合）PR-D：`upstream/cli-security-assert`（`7f86cce` のうち `tests/test_cli_security.py` の部分だけ）
- [ ] 各ブランチで pytest と ruff を通してから `fork` に push する。PR の本文の下書きをこのメモの 8. に書く
- [ ] PR の作成は、ネモさんが行う（または了承を得てから行う）

## 5. テスト方針

- 新しいテストは追加しない。それぞれのコミットにすでにあるテスト（`tests/test_token_reload.py`、`tests/test_per_day_fetch.py`、`tests/test_read_only_serve.py`）を、上流 `main` の上で流す。
- 使うデータは合成データと respx のモック、モンキーパッチだけ。

## 6. 受け入れ条件

- [ ] それぞれの PR 用ブランチで `python -m pytest -q -p no:cacheprovider` が通る
- [ ] それぞれの PR 用ブランチで `python -m ruff check src tests` が通る
- [ ] それぞれの PR の差分が、そのテーマのファイルと CHANGELOG の 1 項目だけになっている
- [ ] 認証情報・健康データ・個人の出力先などがファイルや PR 本文に含まれていない
- [ ] 非公式であることの声明と MIT の帰属が変わっていない

## 7. 実装ログ（Claude Code が記入）

- 2026-11-22 調査のみ（このメモの作成）。2.2 の確認は、一時的な worktree で行い、作業後に削除した。ブランチの作成と push はまだしていない。

## 8. レビュー・PR（Codex が記入）

- PR: 
- 指摘・並列タスク: 
