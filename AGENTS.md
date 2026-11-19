# AGENTS.md — 小米设备数据导出skill（mi_fitness_data_bridge）

> 本文件在原有 9 行工作规则基础上扩展。原有规则仍然有效，保留在「既有工作规则」一节。

## 项目定位

本地优先（local-first）的小米运动健康（Mi Fitness）数据桥接工具：通过非官方/实验性的小米云端适配器读取**用户本人**的健康数据，落本地 SQLite，导出 JSON/CSV 或暴露为 MCP 查询工具。明确不做医疗建议、托管账号访问、多用户云服务。

## 技术栈

- Python ≥ 3.11，hatchling 构建，src 布局 `src/mi_fitness_mcp/`
- 依赖：`mcp>=1.12,<2.0`、`pydantic>=2`、`httpx>=0.27`、`platformdirs`、`keyring>=25`（CLI 用 argparse 实现，无 click/rich）
- 测试：pytest + pytest-asyncio + respx（HTTP mock）；lint：ruff（line-length 100，select E/F/I/N/W/UP/B/C4/SIM，忽略 E501）

## 常用命令

```bash
pip install -e '.[dev]'
python -m pytest -q -p no:cacheprovider
python -m ruff check src tests
```

## 既有工作规则（原文保留）

- Read `PROJECT_GUIDE.md` and `README.md` before work.
- Use `D:\AIWork\projects\mi_fitness_data_bridge` as the stable path.
- Keep credentials, databases, exports, logs, caches, and personal health data out of Git.
- Do not duplicate this connector inside downstream projects.
- Preserve the experimental/unofficial status and upstream MIT attribution.
- Run `python -m pytest -q -p no:cacheprovider` after changes.

## Text encoding

- Pure Python project: pass `encoding="utf-8"` on every text file read/write and explicit `encoding` on `subprocess` text capture; user health data may contain Chinese.
- Export convention: JSON is UTF-8, CSV is `utf-8-sig` (BOM, so Excel opens Chinese correctly); SQLite stores text natively.

## 本仓库 agent 的搜索范围与要求

- 只允许改动本仓库；**严禁读取、复制、传输任何真实凭证与健康数据**：passToken、SQLite 库、导出文件、日志均不得入库、不得进报告、不得上传到任何第三方（.gitignore 已覆盖 `.env*`、`*.db`、`exports/`、`logs/` 等，不得绕过）。
- 适配器（`adapters/mi_fitness_cloud.py`）只访问用户本人有权访问的账号；任何测试/调试一律用合成数据（`examples/synthetic_demo.py`）或 respx mock，不得对真实小米端点发起探测性请求。
- 保持非官方/实验性定位声明与上游 MIT 归属（THIRD_PARTY_NOTICES.md），不得在 README/文档中弱化这些声明。
- `setup` 只走交互式（getpass 不回显）；`--user-id` / `--pass-token` 命令行旗标已于 2026-08-17 移除（会进 shell 历史），不得在文档/脚本中重新引入。

## 升级建议有效性 / 采纳规则（本仓定制）

1. 凡涉及凭证处理、隐私数据流、MCP 工具暴露面的建议：默认从严，凡扩大凭证/数据暴露面的（如托管代理、共享 token、公网部署）一律**记录不做**（SECURITY.md 已明确超出安全模型）。
2. 适配器协议变更（登录、加密、分页）：必须用 respx mock 补测试，禁止以真实账号请求作为验证手段。
3. 任何引入遥测/上报/联网分析的建议：一律**记录不做**（local-first 定位）。
4. 上游 API 变动导致的修复：属"立即做"（工具会实际失效），修复后同步 README 的实验性声明和 KNOWN_REGIONS。
5. 导出格式/查询能力增强：有效即可排期做，但导出内容不得包含 passToken 等凭证字段。

## 升级建议 backlog

（暂无。近期问题已修复；后续发现按全局规则 `github-project-evaluation/docs/agent-collab-rules.md` 收录。）

## 3ツール併用ルール（Antigravity CLI / Claude Code / Codex）

> 2026-11-19 追加。上の既存ルール（認証情報・健康データの扱い、テスト必須など）はどのツールにも同じく適用する。

### 役割分担

| ツール | 担当 | 主な使い方 |
| --- | --- | --- |
| Antigravity CLI (`agy`) | リポジトリ全体の広域調査、設計ドキュメント作成（plan モード）、大規模リファクタリング、Google Cloud / Workspace 連携 | `agy --mode plan` で調査・設計し、結果を `docs/plans/` に書き出す |
| Claude Code (`claude`) | コアロジックの自律実装、テスト駆動デバッグ | `docs/plans/` の設計メモを読んで実装し、`python -m pytest -q -p no:cacheprovider` が通るまで直す |
| Codex (`codex`) | GitHub PR 単位の実装・レビュー・並列タスク | 1 PR = 1 タスクで切り出し、PR の作成・レビュー・並列作業を担当 |

### バトンパス（引き継ぎ）の流れ

1. **Antigravity**：調査・設計を `docs/plans/YYYY-MM-DD-<slug>.md` に `docs/plans/_template.md` の形式で書く。ステータスは `ready-for-implementation` にする。
2. **Claude Code**：`ready-for-implementation` の設計メモを読んで実装し、テストを通す。終わったら同じメモの「実装ログ」に結果を書き、ステータスを `implemented` にする。
3. **Codex**：実装を PR にまとめてレビューする。指摘や分割した並列タスクはメモの「レビュー・PR」に書き、マージ後にステータスを `done` にする。

### 共通の約束

- 引き継ぎは必ず `docs/plans/` のファイル経由で行い、口頭（チャット）だけで済ませない。
- 1 つのメモを同時に複数ツールで編集しない。担当中のツール名をメモの「担当」に書く。
- 設計メモにも、認証情報（passToken など）・SQLite・エクスポート・ログ・実際の健康データを貼らない。例は合成データのみ。
- どのツールも変更後は `python -m pytest -q -p no:cacheprovider` と `python -m ruff check src tests` を実行する。
