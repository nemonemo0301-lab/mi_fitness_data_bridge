# PROGRESS

ネモさんのフォーク（`fork` = nemonemo0301-lab/mi_fitness_data_bridge）での作業の流れを、セッションをまたいで引き継ぐためのメモ。
最終更新: 2026-11-22（Claude Code）

> 認証情報・DB・エクスポート・ログ・実際の健康データはここに書かない。

## 最終ゴール

自分の Mi Fitness データを、手元（ローカル）で毎日確実に取得・利用できる状態を保つ。
毎朝の CSV 自動出力と、MCP 経由での問い合わせに使っている。

**優先順位（2026-11-19 ネモさんに確認済み）**：まず自分用の安定運用。余裕があれば上流（shkyyy18）に還元する。

## できたこと

上流 `origin/main`（91ea4f1、PR #21 マージ時点）からの、フォーク側での追加分：

- 2026-11-08 `9f3c4ee` **`serve --read-only`** を追加。キャッシュのみを読む MCP サーバーで、通常のサーバーを動かしたまま 2 台目のローカルクライアント（Claude Desktop など）から同じ DB に問い合わせられる。クラウド系ツールは隠したうえで拒否し、passToken も使わない。README / CHANGELOG を更新し、テストも追加した。
- 2026-11-11 `2486c10` **passToken の再読み込み**。ログインのたびに passToken がローテーションされるため、別のプロセスがログインすると、長時間動いているサーバーが失敗していた。接続前と再ログイン前に、保存されている最新のトークンを読み直すようにした。
- 2026-11-17 `63c7282` **心拍・ストレスを 1 日ずつ取得**。1 分間隔の心拍では、複数日をまとめてリクエストすると最初の日しか返らず、それ以降のデータが黙って欠けていた。
- 2026-11-19 `1659f63` **3 ツール併用ルール**を AGENTS.md に追加し、`docs/plans/_template.md` と、引き継ぎを試した `docs/plans/test-overview.md` を作った。
- 2026-11-19 `CLAUDE.md` とこの `docs/PROGRESS.md` を追加した（セッションをまたいで作業を続けるため）。
- 2026-11-19 ネモさんに「迷っていること」のうち 4 点を確認し、最終ゴールと優先順位を決めた（下の「決まったこと」）。
- 2026-11-19 CHANGELOG の `[Unreleased]` に、passToken の再読み込み（2486c10）と心拍・ストレスの 1 日ずつ取得（63c7282）の項目を追加した。これでフォークの 3 つの機能がすべて CHANGELOG に載った。テスト 382 件・ruff ともに通過。
- 2026-11-20 **上流の未マージ修正（CLI の GBK 対応）を取り込み**。設計メモ `docs/plans/2026-11-19-upstream-check.md`（Antigravity 作成）に従い、上流 `01a7f1f`（絵文字のステータスマーカーを `[OK]` / `[X]` / `[WARN]` / `[INFO]` に置換）を `cherry-pick -x`。CHANGELOG のコンフリクトは両方の項目を残して解消し、`tests/test_cli_security.py` の常に真になっていた検証を補強した。メモのステータスは `implemented`。
- 2026-11-20 `d36c40b` **GBK 対応の PR #1（フォーク内）をレビュー・マージ**。Codex が利用上限のため Antigravity が代行レビューし、判定は approve（ブロッカーなし）。`fix/cli-gbk-upstream` → `docs/agent-collab` にマージ。2026-11-22 にマージ後の `docs/agent-collab` でテスト 389 件・ruff の通過を再確認し、設計メモの PR 欄を更新した。
- 2026-11-22 **上流 PR の設計メモ** `docs/plans/2026-11-22-upstream-pr.md`（draft）を作った。上流 `main` が `6399cd0`（GBK 対応 #22 をマージ）まで進み、その内容はフォークの `0d5504f` と patch-id が一致する（GBK 対応は上流に出さなくてよい）。3 機能はそれぞれ単独で上流 `main` に載り、テストも通る（382 / 382 / 383 件、3 つ全部で 389 件）。推奨は、機能をテーマごとに 3 本の PR に分け、ドキュメントは別にすること。
- 2026-11-22 **cp932 対応の設計メモ** `docs/plans/2026-11-22-cp932-output.md`（draft）を作った。strict `cp932` では `setup` / `doctor` / `sync` のどれも最初の 1 行で落ちる。`sync` は同期を始める前に落ちるので、データが 1 件も同期されない（GBK のテストを一時的に cp932 に変えて確認）。推奨は案 A（変換できない文字だけを `\uXXXX` に置き換えて、止まらないようにする。UTF-8 と GBK では出力が変わらない）。
- 2026-11-22 ネモさんに、cp932 対応・上流のライセンス条件・PR の分け方・次に欲しいデータを確認し、下の「決まったこと」に記録した。
- 2026-11-22 毎朝の CSV 出力スクリプト `~/mi-fitness-daily/daily_export.py` を確認した（スクリプトは変更していない）。スクリプト自体は `PYTHONUTF8` を設定していない。`sync` / `export` は `subprocess` で実行し、stdout / stderr は `DEVNULL` に捨てている。CLI の出力を文字列としては見ておらず、終了コードだけを使っている（`✅` などは見ていない）。パスの食い違いについても確認し、`D:\AIWork` のチェックアウトは無いと分かった。
- 2026-11-22 **cp932 対応の案 A を実装**（作業ブランチ `fix/cli-cp932-output`、worktree `~/mi-fitness-bridge-wt-cp932`）。`main()` の最初で、strict かつ UTF-8 以外の stdout / stderr を `errors="backslashreplace"` にする。strict `cp932`（と `cp1252`）でも `setup` / `doctor` / `sync` が最後まで動き、`sync` の終了コードも変わらない。UTF-8 と GBK では出力は変わらない。テスト `tests/test_cli_cp932.py`、CHANGELOG、README（中国語・英語）に `PYTHONUTF8=1` を勧める一文を追加。設計メモは `implemented`。**フォーク内マージと上流への PR はまだ。** worktree で本体の .venv の python に PYTHONPATH=src を付けて実行し、pytest 417 件・ruff ともに通過した。
- 2026-11-22 cp932 対応が、別々のセッションで 2 回実装された（`fix/cli-cp932-output` と、Claude Code の `fix/cli-non-gbk-output`）。ネモさんの判断で `fix/cli-cp932-output` を残し、Claude Code のほうからは、サブプロセスで `PYTHONIOENCODING=cp932` を付けて `sync --help` を動かすテストだけを移した（`d4c3823`）。`fix/cli-non-gbk-output` は削除した。
- 2026-11-22 `fix/cli-cp932-output` は 08:18 に `docs/agent-collab` へ fast-forward でマージされていた（Claude Code の操作ではない。本体の checkout の reflog で確認）。そのあと Claude Code が `d4c3823`（テストとメモだけ）まで fast-forward した。`docs/agent-collab` で pytest 418 件・ruff 通過。
- 2026-11-22 **上流 PR 用のブランチを 5 本作って `fork` に push した**（`docs/plans/2026-11-22-upstream-pr.md`、ステータス `implemented`）。A `upstream/token-reload`、B `upstream/per-day-hr-stress`、C `upstream/serve-read-only`、D `upstream/cli-security-assert`、E `upstream/cli-non-gbk-output`。どれも上流 `main`（`6399cd0`）から 1 コミットで、単独で pytest と ruff が通る。PR の本文の下書きと、PR を作るリンクはメモの 8. にある。**上流への PR はまだ作っていない。**

ブランチの状態：
- `feat/serve-read-only` … 上の 3 コミット（9f3c4ee〜63c7282）。`fork` に push 済みで、ローカルと一致。
- `docs/agent-collab` … `feat/serve-read-only` の上にドキュメントのコミットを積み、GBK 対応（PR #1）をマージしたもの。毎朝の CSV 出力に使っている。`fork` に push 済み。
- `fix/cli-gbk-upstream` … PR #1 でマージ済み（`fork` に push 済み）。worktree `~/mi-fitness-bridge-wt-gbk` が残っているが、もう使わないので削除してよい（ネモさんの判断待ち）。
- `fix/cli-cp932-output` … cp932 案 A の実装。`docs/agent-collab` にマージ済み（`d4c3823` まで）。worktree `~/mi-fitness-bridge-wt-cp932` が残っている。
- `upstream/*`（5 本）… 上流 PR 用。上流 `main` が基点。`fork` に push 済み。worktree `~/mi-fitness-bridge-wt-upstream`。
- 注意：本体の checkout `~/mi-fitness-bridge` は毎朝の CSV 出力が editable install で使っている。ブランチを切り替えると毎朝動くコードも変わるので、`docs/agent-collab` のままにし、ほかのブランチの作業は worktree で行う。

## 決まったこと（2026-11-19 ネモさんに確認）

- **最終ゴール**：まず自分用の安定運用。余裕があれば上流に還元する。
- **上流への PR**：`feat/serve-read-only` の 3 コミットは、まだ出していないが**出す予定**。
- **ドキュメント**（3 ツール併用ルール・CLAUDE.md・PROGRESS.md）も**上流に出す**。
- **毎朝の CSV 自動出力**（`MiFitnessDailyExport`）は **`docs/agent-collab`** のコードで動いている。→ このブランチを壊すと毎朝の出力が止まる。push の前に必ずテストを通すこと。

## 決まったこと（2026-11-22 ネモさんに確認）

- **cp932 対応**：案 A（出力できない文字だけを置き換えて止まらないようにする）で直す。
- **上流のライセンス条件**：上流（shkyyy18）の `CONTRIBUTING.md` にある条件（AGPL-3.0-only に加えて、メンテナーに商用を含む再ライセンス権を与える）に同意する。
- **PR の分け方**：機能はテーマごとに 3 本の PR に分ける（passToken の再読み込み → 心拍・ストレス → `serve --read-only` の順）。ドキュメントは別に出す。
- **次に欲しいデータ**：睡眠スコア。
- **テスト補強の PR（PR-D）**：出す。
- **ドキュメント PR**：PROGRESS.md・CLAUDE.md・フォークの設計メモは出さない。汎用的な部分（`docs/plans/_template.md` と 3 ツール併用ルール）だけを、個人の事情を除いて英語（または中国語）に訳し、機能 PR のあとで出す。
- cp932 対応は、別セッションの `fix/cli-cp932-output` を残す。

調べて分かったこと（2026-11-22）：

- **パスの食い違い**：`D:\AIWork` のチェックアウトは存在しない。実際の作業場所は WSL の `~/mi-fitness-bridge`。
- **毎朝の CSV 自動出力**：WSL の `~/mi-fitness-bridge` を editable install で使っている。修正を反映するには、そのフォルダのブランチを更新するだけでよく、再インストールは不要。
- **毎朝スクリプトの実行方法**：`~/mi-fitness-daily/daily_export.py` 自体は `PYTHONUTF8` を設定していない。`sync` / `export` の stdout / stderr は `DEVNULL` に捨てている。CLI の出力（`✅` など）を文字列としては見ておらず、終了コードだけを使っている。

## 今やっていること

- 上流 PR 用のブランチ 5 本が `fork` にある。PR はネモさんが作る（上流 PR メモの 8. のリンクから。ライセンス同意のチェックもネモさん本人が付ける）。

## 次にやること（3つまで）

1. 上流 PR を作る（**ネモさん**）。順番は A → B → C。D と E はいつでもよい。本文は上流 PR メモの 8. の下書きを貼る。作ったら PR 番号をメモの 8. に書く。
2. 睡眠スコアの取得方法を調べる（`docs/issue-14-sleep-score-investigation.md` が手がかり）。設計メモを `docs/plans/` に作る。
3. ドキュメント PR の準備：`docs/plans/_template.md` と 3 ツール併用ルールから個人の事情を除き、英語に訳す（機能 PR のあとでよい）。

## 迷っていること・ネモさんに聞きたいこと

- **残っている worktree**：`~/mi-fitness-bridge-wt-gbk`（マージ済み）と `~/mi-fitness-bridge-wt-cp932`（マージ済み）は、消してよいですか。`~/mi-fitness-bridge-wt-upstream` は上流 PR が終わるまで残します。
- **並行して動くセッション**：2026-11-22 に、cp932 対応を 2 つのセッションが同時に実装し、`docs/agent-collab` へのマージも別のセッションが行った。同じタスクを複数のツールで同時に始めないように、着手する前に `git fetch fork` で既存のブランチを確かめる。
- **フォークの main**：フォーク側の `main` を、今後どのブランチの内容に合わせていくか（ずっと作業ブランチのまま運用するのか）。
