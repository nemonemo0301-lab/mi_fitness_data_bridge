# 上流ブランチ `fix/cli-gbk-status-markers` 取り込み調査・設計メモ

- 作成日: 2026-11-19
- 作成: Antigravity CLI（plan モード）
- 担当: Antigravity（Codex 代行レビュー）
- ステータス: implemented

## 1. 目的

上流（`origin = shkyyy18/mi_fitness_data_bridge`）の未マージブランチ `fix/cli-gbk-status-markers`（2026-11-09, `fix: keep CLI status output compatible with GBK terminals`）について、当フォーク独自の変更との競合・安全性を精査し、(1) 取り込むべきか、(2) 理由、(3) 取り込み手順とコンフリクト見込み、(4) 日本語 Windows 端末（`cp932`）での挙動を整理して実装判断・引き継ぎ資料を作成する。

## 2. 調査結果

### 結論サマリー

- **(1) 取り込むべきか**: **取り込むべき（推奨）**。ステータスは `ready-for-implementation` とする。
- **(2) 理由**:
  1. **明確なバグ修正かつ可搬性の向上**: CLI（`setup` / `doctor` / `sync`）のステータス表示に使われている絵文字マーカー（`⚠️`, `❌`, `✅`, `ℹ️`）を ASCII マーカー（`[WARN]`, `[X]`, `[OK]`, `[INFO]`）へ置き換えることで、strict GBK 端末やリダイレクト環境での `UnicodeEncodeError` を解消できる。UTF-8 環境でもログ出力・パイプ・絵文字非対応フォントでの視認性・扱いやすさが向上し、機能的デメリットがない。
  2. **フォーク独自変更とのコード競合がゼロ**: 当フォーク独自の3機能（`serve --read-only`、`passToken` 再読み込み、心拍・ストレスの1日ずつ取得）はいずれも変更箇所と重ならず、ランタイム・テストの干渉もない。唯一のコンフリクト見込みは `CHANGELOG.md` の `## [Unreleased]` 直下の隣接行のみで、解消が容易。
  3. **セキュリティ・運用ルール適合**: 認証情報や健康データの露出面を一切広げず、対話入力（`getpass`）とマスク処理を維持している。追加テスト `tests/test_cli_gbk.py` は合成データとモンキーパッチのみを使用し、`synthetic-token` が標準出力に漏れないこと・アダプタが必ず `close()` されることも検証している。
  4. **未マージブランチである点の許容性**: 上流 `main` へ未マージのため、将来上流が内容を微修正・squash してマージした際に軽微なコンフリクトが生じる可能性はあるが、対象は4ファイルかつ単純なマーカー置換であり、将来の整合コストは極めて低い。

### 関係するファイル・モジュールと影響範囲

| 対象ファイル | 上流ブランチでの変更内容 | 当フォーク現状との差分・影響 |
| --- | --- | --- |
| `src/mi_fitness_mcp/main.py` | L38–233（`_warn_on_weak_keyring`, `cmd_setup`, `cmd_doctor`, `cmd_sync_async`）の絵文字マーカーを `[WARN]` / `[X]` / `[OK]` / `[INFO]` に置換 | 当フォークの L38–233 は上流と完全一致。フォーク独自変更の `serve --read-only` は `main()` 内の L277–283・L325–331 にあり40行以上離れているため**コンフリクトなし** |
| `src/mi_fitness_mcp/server.py` | 変更なし | フォーク独自の `serve --read-only`（`read_only_serve`, `CLOUD_TOOLS`, `main(db_path=None, read_only_mode=False)`）に影響なし |
| `src/mi_fitness_mcp/adapters/mi_fitness_cloud.py` | 変更なし | フォーク独自の `passToken` 再読み込み（`_adopt_stored_token()` L180–192）および心拍・ストレスの1日ずつ取得（`_fetch_key_per_day()` L409–422, `iter_heart_rate` L1348, `iter_stress` L1465）に影響なし。新テストは `_create_cloud_adapter` を偽装するため干渉しない |
| `CHANGELOG.md` | `## [Unreleased]` 直下（`- Correct body measurements:` の直前）に1項目追加 | 当フォークも `## [Unreleased]` 直下（L7）に `- Add \`serve --read-only\`: ...` を追加済みのため、**1ハンクの隣接行コンフリクトが発生**（両方残せば解消） |
| `tests/test_cli_security.py` | L166 の `assert "连接状态： ❌"` を `assert "连接状态： [X]"` に更新 | 当フォーク L166 と完全一致のため**コンフリクトなし**。なお L303 に `assert "\u2705 daily_activity" not in output` が残っており、置換後は常に真になる（後述の設計方針で補強を推奨） |
| `tests/test_cli_gbk.py` | 新規追加（strict `gbk` ストリームでの `doctor` / `setup` / `sync` 回帰テスト、122行） | 当フォークに未存在のため**コンフリクトなし**。`pyproject.toml` の ruff ルール（`E/F/I/N/W/UP/B/C4/SIM`, `E501` 除外）にも適合 |

### (4) 日本語の Windows 端末（`cp932`）でも同じ問題が起きるか

**結論：同じ絵文字による `UnicodeEncodeError` は起きる。ただし、strict `cp932` 環境ではこの上流パッチだけでは解決しきらず、簡体字中国語メッセージによる `UnicodeEncodeError` が別途残る。**

1. **`cp932` が適用される条件（Windows + Python 3.11+）**:
   - Python 3.6 以降（PEP 528）では、対話コンソール（cmd / PowerShell / Windows Terminal）に stdout が直接接続されている場合は Windows Unicode Console API（`_WindowsConsoleIO` / UTF-8）が使われるため、通常は `UnicodeEncodeError` は発生しない（フォント次第で豆腐・文字化けになるのみ）。
   - 一方、**パイプ（`|`）・ファイルリダイレクト（`>`）・サブプロセス出力捕捉・一部 IDE／CI ランナー・`PYTHONLEGACYWINDOWSSTDIO=1`** などの環境では、`PYTHONUTF8=1` や Windows のシステム UTF-8 設定が有効でない限り ANSI コードページ（簡体字中国語 Windows は `gbk`、**日本語 Windows は `cp932`**）にフォールバックし、厳密エンコード（`errors="strict"`）で失敗する。
2. **絵文字マーカーでの失敗（GBK と同じ問題）**:
   - 本パッチが置換対象とする `⚠️`（U+26A0 + U+FE0F）、`❌`（U+274C）、`✅`（U+2705）、`ℹ️`（U+2139 + U+FE0F）はいずれも `cp932` に収録されていない。
   - したがって、strict `cp932` ストリームでも GBK とまったく同じ `UnicodeEncodeError: 'cp932' codec can't encode character ...` が発生する。この部分は本パッチで解消される。
3. **簡体字中国語メッセージでの失敗（GBK との決定的な違い）**:
   - GBK 端末では `src/mi_fitness_mcp/main.py` や `src/mi_fitness_mcp/auth/__init__.py` の簡体字中国語テキストはすべて GBK で表現できるため、絵文字を ASCII 化するだけで完治する。
   - しかし **`cp932` には簡体字固有の漢字が多数含まれていない**。たとえば以下のような文字が `cmd_setup` / `cmd_doctor` / `cmd_sync_async` および `keyring_backend_warning()` の出力に含まれる：
     - `cmd_setup`: `导`（配置向导, L82）、`须`（必须提供, L89）
     - `cmd_doctor`: `诊`（诊断, L98）、`获`/`见`/`节`（L107–108）、`载`（加载, L115, L157）、`务`（服务, L119）、`凭`（凭据, L125, L139）、`连`（连接状态, L132）、`识`（识别, L134）、`库`（数据库, L144, L148, L153, L155）、`类`（数据类型, L135）、`请`/`运`（请运行, L106 等）、`创`（创建, L155）、`败`（失败, L157）
     - `cmd_sync_async`: `载`/`务`/`凭`/`无`/`连`/`种`/`类`/`结`/`败`（L172–234）
     - `auth/__init__.py` (`keyring_backend_warning`): `无`/`确`/`凭`/`储`/`当`/`后`/`盘`/`请`/`钥`/`试`（L27–33）
   - このため、strict `cp932` ストリームでは本パッチを取り込んだ後でも、`setup` は L82（`配置向导`）、`doctor` は L98（`诊断`）、`sync` は L200 等（`种数据类型` や失敗時の `加载`/`服务` 等）で依然として `UnicodeEncodeError` が発生する。
   - なお `cmd_export`（L246–267）は英語メッセージのみ出力するため、パスに `cp932` 非対応文字を含まない限りこの問題は起きない。
4. **日本語 Windows 環境での現実的な対策**:
   - 本パッチを取り込んだうえで、日本語 Windows でパイプ／リダイレクト／サブプロセス実行を行う場合は `PYTHONUTF8=1`（または `PYTHONIOENCODING=utf-8`）を指定する運用が確実。
   - コード側で strict `cp932` へ完全対応する（CLI メッセージの英語化／i18n や stdout の `errors="replace"` 再構成など）場合は、上流との差分が大きくなるため本タスクとは別の設計タスクとして扱うべき。

### 参考にした資料・上流の情報

- 上流ブランチ: `origin/fix/cli-gbk-status-markers`（2026-11-09, `fix: keep CLI status output compatible with GBK terminals`）
- リポジトリ内参照ファイル: `AGENTS.md`, `PROJECT_GUIDE.md`, `README.md`, `CHANGELOG.md`, `pyproject.toml`, `src/mi_fitness_mcp/main.py`, `src/mi_fitness_mcp/server.py`, `src/mi_fitness_mcp/adapters/mi_fitness_cloud.py`, `src/mi_fitness_mcp/auth/__init__.py`, `tests/test_cli_security.py`

## 3. 設計方針

### 変更内容の概要

1. 上流ブランチ `fix/cli-gbk-status-markers` の変更（4ファイル）を、未マージブランチの履歴を直接 `merge` するのではなく、**作業ブランチ上で `git cherry-pick`（またはパッチ適用）により取り込む**。
2. `CHANGELOG.md` の `## [Unreleased]` 直下で発生する1ハンクの隣接行コンフリクトは、フォーク独自の `- Add \`serve --read-only\`: ...` と上流の `- Use ASCII status markers in setup, doctor and sync ...` の**両方を残して解消**する。
3. 補強変更（任意・推奨）: `tests/test_cli_security.py` L303 の `assert "\u2705 daily_activity" not in output` は、`✅` が `[OK]` に変わった後に常に真となって回帰検知力を失うため、`assert "[OK] daily_activity" not in output` へ更新（または併記）する。

### (3) 取り込む場合の手順とコンフリクトの見込み

#### コンフリクトの見込み

| ファイル | コンフリクト見込み | 解消方法 |
| --- | --- | --- |
| `src/mi_fitness_mcp/main.py` | **なし**（自動適用可能） | そのまま適用 |
| `tests/test_cli_security.py` | **なし**（自動適用可能） | そのまま適用（L303 の補強のみ任意で手動追記） |
| `tests/test_cli_gbk.py` | **なし**（新規ファイル） | そのまま追加 |
| `CHANGELOG.md` | **あり（軽微・1ハンク）** | `## [Unreleased]` 直下に `serve --read-only` と `ASCII status markers` の両項目を並べて残す |

#### 具体的な手順

1. 最新の `main` から作業ブランチを作成し、上流ブランチを取得する：
   - `git checkout -b fix/import-cli-gbk-status-markers`
   - `git fetch origin fix/cli-gbk-status-markers`
2. 未マージブランチのコミットを `git cherry-pick`（または差分パッチ適用）で取り込む：
   - `git cherry-pick origin/fix/cli-gbk-status-markers`
   - ※ `CHANGELOG.md` のみコンフリクトする見込み。両方の箇条書きを残して `git add CHANGELOG.md && git cherry-pick --continue` する。
3. `tests/test_cli_security.py` L303 を確認し、`assert "[OK] daily_activity" not in output` を追加または置換して、エラー時に成功マーカーが出ないことの回帰検証を維持する。
4. 全テストと lint を実行し、フォーク独自機能（`serve --read-only` 等）の既存テストを含めすべて通ることを確認する。

### 選ばなかった案と理由

- **案 A: `git merge origin/fix/cli-gbk-status-markers` で直接マージする**
  - 選ばなかった理由: 対象ブランチは上流 `main` に未マージであり、将来上流が rebase / squash してマージした場合に不要なマージ履歴が残る。`cherry-pick` の方が履歴が簡潔で管理しやすい。
- **案 B: 上流 `main` マージまで見送る（取り込まない）**
  - 選ばなかった理由: 変更が極めて小さく競合リスクもほぼない一方で、CLI 出力の可搬性向上と合成テスト追加の実益がすぐ得られるため。
- **案 C: ついでに `main.py` の簡体字メッセージをすべて英語化して `cp932` に完全対応する**
  - 選ばなかった理由: 上流との差分が `main.py` 全体に広がり、今後の上流追従コストが大きく上がる。必要であれば別タスクとして独立に設計すべき。

## 4. 実装タスク（Claude Code 向け）

- [x] 作業ブランチを作成し、`origin/fix/cli-gbk-status-markers` の変更を `cherry-pick`（またはパッチ適用）で取り込む（対象ファイル: `src/mi_fitness_mcp/main.py`, `tests/test_cli_gbk.py`, `tests/test_cli_security.py`, `CHANGELOG.md`）
- [x] `CHANGELOG.md` の `## [Unreleased]` 直下のコンフリクトを解消し、`serve --read-only` の項目と ASCII ステータスマーカーの項目の両方を保持する
- [x] `tests/test_cli_security.py` L303 の `assert "\u2705 daily_activity" not in output` を確認し、`assert "[OK] daily_activity" not in output` で失敗時に成功マーカーが出力されないことを引き続き検証できるように更新する
- [x] テストと lint を実行し、結果を本メモの「7. 実装ログ」に記入してステータスを `implemented` に更新する

## 5. テスト方針

- 追加するテスト: `tests/test_cli_gbk.py`（上流差分そのまま：`doctor` / `setup` / `sync` を strict `gbk` ストリームで実行し、成功・部分成功・失敗・認証情報欠落・接続失敗・トークン非出力・アダプタ `close()` を検証）
- 変更するテスト: `tests/test_cli_security.py`（L166 の `[X]` 検証、および L303 の `[OK] daily_activity` 非出力検証）
- 既存テストの回帰確認: フォーク独自機能（`serve --read-only`、`passToken` 再読み込み、心拍・ストレスの1日ずつ取得）を含む全テストスイート
- 使うデータ：合成データ（`examples/synthetic_demo.py` や `SimpleNamespace` / `monkeypatch`）または `respx` のモックのみ。実アカウント・実クラウド・実キーリングへのアクセスは一切行わない

## 6. 受け入れ条件

- [x] `python -m pytest -q -p no:cacheprovider` が通る
- [x] `python -m ruff check src tests` が通る
- [x] `src/mi_fitness_mcp/main.py` の `serve --read-only` オプション、`adapters/mi_fitness_cloud.py` の `passToken` 再読み込みおよび心拍・ストレス1日ずつ取得に変更・退行がない
- [x] 認証情報・健康データがファイルに含まれていない

## 7. 実装ログ（Claude Code が記入）

- 2026-11-20 Claude Code
- 作業ブランチ: 既存の `fix/cli-gbk-upstream`（`docs/agent-collab` の e70dea2 の上。メモの手順 1 にある「`main` から作成」ではなく、フォーク独自の 3 機能を含むこのブランチに積んだ。フォーク独自機能との組み合わせをテストで確かめるため）。
- `git cherry-pick -x 01a7f1f` → `323cdea`（author は上流の Alan のまま、committer は nemoto wataru）。
  - 予想どおり `CHANGELOG.md` の `## [Unreleased]` 直下だけがコンフリクト。既存の書式（項目間に空行）に合わせ、`serve --read-only` → ASCII ステータスマーカーの順で両方残した。
  - `main.py` / `tests/test_cli_gbk.py` / `tests/test_cli_security.py` L166 は自動適用。`main.py` の差分に `serve` / `--read-only` 関連の行は含まれないことを確認した。
- 補強（別コミット）: `tests/test_cli_security.py` の `test_sync_*`（失敗時）で、置換後は常に真になる `"✅ daily_activity" not in output` を `"[OK] daily_activity" not in output` に置き換え、あわせて失敗マーカーが実際に出ることを確かめる `"[X] daily_activity: status=error" in output` を追加した。
- テスト結果（`.venv/bin/python`）:
  - `pytest -q -p no:cacheprovider` → **389 passed**（うち `tests/test_cli_gbk.py` + `tests/test_cli_security.py` で 23 passed）
  - `ruff check src tests` → All checks passed!
- 使ったのは合成データ・モンキーパッチのみ。実アカウント・認証情報・健康データ・実キーリングには触れていない。push はしていない。
- 残課題（メモ 2. (4) のとおり、本タスクの範囲外）: strict `cp932` ではまだ簡体字メッセージで `UnicodeEncodeError` が起こりうる。当面は `PYTHONUTF8=1` で運用。

## 8. レビュー・PR（Codex が記入）

- レビュー日時・担当: 2026-11-20 Antigravity（Codex 利用上限のため代行レビュー）
- 対象差分: ブランチ `fix/cli-gbk-upstream`（`docs/agent-collab` からの差分：上流 `01a7f1f` の GBK 対応 cherry-pick ＋ `tests/test_cli_security.py` 補強）
- PR: nemonemo0301-lab/mi_fitness_data_bridge#1（`fix/cli-gbk-upstream` → `docs/agent-collab`、2026-11-20 マージ済み `d36c40b`）。マージ後の `docs/agent-collab` で 2026-11-22 に再確認: pytest 389 passed / ruff All checks passed。
- 判定: approve
- 確認結果（バグ・退行・見落とし・影響範囲）:
  - **バグ・退行**: `src/mi_fitness_mcp/main.py`（L38–230）のステータスマーカー置換のみで、終了コード・`finally` での `adapter.close()`・`getpass` による非エコー入力・`mask_account_id`・`--db` / `MI_FITNESS_DB_PATH` 解決ロジックに変更・退行なし。`CHANGELOG.md` のコンフリクト解消も書式・内容ともに適切。`tests/test_cli_security.py` L303–304 の補強により、エラー時に `[X]` が出力され `[OK]` が出力されないことが引き続き検証できている。テスト（389 passed）・ruff（All checks passed）確認済み。
  - **絵文字・非 GBK 文字の見落とし**: `src/mi_fitness_mcp/main.py` 全行および `auth/__init__.py`・`export.py` 等を確認し、CLI 出力に絵文字の残存なし。`cmd_doctor` の設定未作成分岐（L107–109）の `「」→“”` や `serve --read-only` のヘルプ文言を含め、いずれも GBK エンコード可能な文字のみ。
  - **フォーク独自機能への影響**:
    - `serve --read-only`（`main.py` L279–283・L325–331、`server.py` の `read_only_serve` / `CLOUD_TOOLS` / `main()`）: 変更箇所と非重複、影響なし。
    - `passToken` 再読み込み（`adapters/mi_fitness_cloud.py` の `_adopt_stored_token()` L180–192・L379）: 変更なし、`main.py` の `_create_cloud_adapter()` 経由の呼び出しも不変で影響なし。
    - 心拍・ストレスの 1 日ずつ取得（`adapters/mi_fitness_cloud.py` の `_fetch_key_per_day()` L409–422、`iter_heart_rate` L1348、`iter_stress` L1465）: 変更なし、`cmd_sync_async` からの呼び出し引数も不変で影響なし。
  - **毎朝の CSV 出力（`export` コマンド）への影響**: `cmd_export`（`main.py` L246–267）および `src/mi_fitness_mcp/export.py`（`utf-8-sig` 出力・数式インジェクション対策・読み取り専用接続・`FORBIDDEN_EXPORT_FIELDS` 除外）は一切未変更で影響なし。
  - **セキュリティ・ルール適合**: 認証情報・健康データの露出や実アカウント通信はなく、追加・更新テストも合成データとモンキーパッチのみ。
- 指摘・補足（いずれもブロッカーなし / non-blocking）:
  - 毎朝の自動実行スクリプト等で `mi-fitness-bridge sync` の標準出力を文字列解析している場合、マーカーが `✅`/`❌`/`⚠️` から `[OK]`/`[X]`/`[WARN]` に変わる点のみ念のため留意すること（終了コード 0/1 および `export` コマンドの出力は不変）。
  - `tests/test_cli_gbk.py` は上流 `01a7f1f` そのままの取り込みであり、`cmd_doctor` の設定ファイル未作成分岐（L104–110）や非デフォルト DB パス警告分岐（L145–150）、`cmd_setup` の必須入力欠落分岐（L88–90）は明示的には通過しないが、該当行はすべて GBK 互換文字であり上流追従性を優先して追加改変は不要。
  - 既知のスコープ外事項（本メモ 2.(4) 記載どおり）: 日本語 Windows の strict `cp932` 環境では簡体字メッセージ側で依然 `UnicodeEncodeError` が起きうるため、`PYTHONUTF8=1` での運用を継続する。
