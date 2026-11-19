# CLAUDE.md

Claude Code 向けの短い入口。詳しいルールは下の参照先にあり、ここでは重複させない。

## 参照先

- `AGENTS.md` — 技術スタック、採用ルール、3 ツール併用（Antigravity / Claude Code / Codex）のルール
- `PROJECT_GUIDE.md` — プロジェクトの範囲と作業ルール
- `README.md` / `README.en.md` — 使い方、実験的・非公式であることの声明
- `SECURITY.md` — セキュリティモデル（範囲外のもの）
- `docs/plans/_template.md` — 引き継ぎ用の設計メモのテンプレート（`docs/plans/YYYY-MM-DD-<slug>.md`）

## 目的（1 行）

本人の Mi Fitness（小米运动健康）データを非公式クラウドアダプター経由で取得し、ローカルに保存して、JSON/CSV 出力または MCP ツールとして使えるようにする。local-first。医療助言は行わない。

## データの流れ

小米クラウド（`src/mi_fitness_mcp/adapters/mi_fitness_cloud.py`、FDS 詳細データは `adapters/fds.py`）
→ `sync` → ローカル SQLite キャッシュ
→ `export`（JSON は UTF-8、CSV は utf-8-sig）／ `serve`（stdio MCP。`--read-only` はキャッシュのみを読む 2 台目のクライアント用）

認証情報（passToken）は `setup`（対話入力のみ）でキーリングに保存する。

## テスト

```bash
python -m pytest -q -p no:cacheprovider
python -m ruff check src tests
```

テストに使うのは合成データ（`examples/synthetic_demo.py`）と respx のモックだけ。小米の実際のエンドポイントにはリクエストを送らない。

## やってはいけないこと

- passToken などの認証情報、SQLite DB、エクスポート、ログ、実際の健康データをコミット・コピー・報告・アップロードしない（設計メモや PROGRESS.md に貼るのも禁止）。
- ネモさんの実際の CSV 出力先（Windows の Documents\health）は読まない。`health/nari` には絶対に触らない。
- `main` と上流 `origin`（shkyyy18）には push しない。push してよいのはフォーク `fork`（nemonemo0301-lab）の作業ブランチだけ。
- `--user-id` / `--pass-token` などの CLI フラグを復活させない。
- 非公式・実験的であることの声明と、上流の MIT 帰属（`THIRD_PARTY_NOTICES.md`）を弱めない。
- テレメトリ、ホスト型プロキシ、共有トークン、公開デプロイを追加しない。

## セッションをまたぐ流れ

- **作業を始める前に必ず `docs/PROGRESS.md` を読む。**
- **作業の最後に必ず `docs/PROGRESS.md` を更新してコミットする。**
