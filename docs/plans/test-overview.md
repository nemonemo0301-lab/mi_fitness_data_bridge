# リポジトリ概要（バトンパステスト）

- 位置づけ: Mi Fitness の本人健康データを非公式・実験的なクラウド経由で取得するローカル優先のデータブリッジ（医療助言やマルチユーザー運用は対象外）。
- 主な機能: 活動・睡眠・運動・体組成・心拍・SpO₂・ストレス等をローカル SQLite へ同期し、JSON/CSV 出力、ローカル stdio MCP、Python API（`mi_fitness_mcp`）を提供。
- 技術構成: Python 3.11+（hatchling / `src/mi_fitness_mcp/`）、`mcp`・`pydantic`・`httpx`・`platformdirs`・`keyring`、CLI は `argparse`（`mi-fitness-bridge` / 互換 `mi-fitness-mcp`）。
- セキュリティ方針: `setup` は対話入力のみ（`passToken` 非表示・キーリング保存）とし、認証情報・DB・出力・ログ・実データの Git 登録や外部送信を禁止。
- 検証とライセンス: テストは合成データ（`examples/synthetic_demo.py`）と `respx` モックのみ使用し `pytest`/`ruff` で確認。現行 AGPL-3.0-only（上流 MIT 帰属を保持）。
- 開発体制: Antigravity・Claude Code・Codex の3ツール併用では `docs/plans/` の設計メモ経由で設計→実装→レビューを引き継ぐ。

ステータス: ready-for-implementation
