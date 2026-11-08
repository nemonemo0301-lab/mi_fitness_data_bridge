"""Read-only serve: cache queries only, no cloud tools, no lock. Synthetic data only."""

import json
from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from mi_fitness_mcp import main as cli
from mi_fitness_mcp import server
from mi_fitness_mcp.storage import Database
from mi_fitness_mcp.storage.sync_history import SyncHistory


@pytest.fixture
def read_only_server(monkeypatch):
    monkeypatch.setattr(server, "read_only_serve", True)
    monkeypatch.setattr(server, "sync_tasks", {})
    monkeypatch.setattr(server, "sync_active", False)
    monkeypatch.setattr(server, "active_sync_id", None)


@pytest.mark.asyncio
async def test_cloud_tools_hidden_and_rejected(read_only_server):
    names = {tool.name for tool in await server.list_tools()}
    assert names.isdisjoint(server.CLOUD_TOOLS)
    assert {"query_daily_activity", "query_heart_rate", "get_sync_status"} <= names
    with pytest.raises(ValueError, match="read-only"):
        await server._dispatch_tool("sync_data", {})
    result = json.loads((await server.call_tool("sync_data", {}))[0].text)
    assert result["status"] == "error"
    assert "Read-only" in result["error"]


@pytest.mark.asyncio
async def test_cloud_tools_listed_in_normal_mode(monkeypatch):
    monkeypatch.setattr(server, "read_only_serve", False)
    names = {tool.name for tool in await server.list_tools()}
    assert names >= server.CLOUD_TOOLS


@pytest.mark.asyncio
async def test_read_only_main_skips_lock_adapter_and_pass_token(tmp_path, monkeypatch):
    db_path = tmp_path / "synthetic.db"
    owner = SyncHistory(Database(db_path), "synthetic-user")
    owner.acquire()  # the normal server already owns this database
    owner.save(
        {"sync_id": "synthetic-job", "status": "running", "created_at": "2026-01-01T00:00:00Z"}
    )
    adapter_cls = Mock()
    monkeypatch.setattr(server, "MiFitnessCloudAdapter", adapter_cls)
    # Record originals so main()'s global writes are undone after the test.
    for name in ("read_only_serve", "adapter", "sync_service", "query_service", "sync_history",
                 "db", "config"):
        monkeypatch.setattr(server, name, None if name != "read_only_serve" else False)
    monkeypatch.setattr(
        server, "load_mi_fitness_token", lambda: ("synthetic-user", "SYNTHETIC-NOT-A-TOKEN")
    )
    monkeypatch.setattr(
        server,
        "load_config",
        lambda: SimpleNamespace(mode="mi_fitness_cloud", database_path=db_path),
    )

    @asynccontextmanager
    async def streams():
        yield None, None

    seen = {}

    async def run(*args):
        seen["tools"] = {tool.name for tool in await server.list_tools()}

    monkeypatch.setattr(server, "stdio_server", streams)
    monkeypatch.setattr(server.app, "run", run)
    try:
        await server.main(db_path=db_path, read_only_mode=True)
        adapter_cls.assert_not_called()
        assert server.adapter is None and server.sync_service is None
        assert server.query_service.user_id == "synthetic-user"
        assert seen["tools"].isdisjoint(server.CLOUD_TOOLS)
        # A live job owned by the normal server must not be marked interrupted.
        assert server.sync_history.get("synthetic-job")["status"] == "running"
    finally:
        owner.close()


def test_cli_passes_read_only_flag(monkeypatch, tmp_path):
    captured = {}

    async def fake_main(db_path=None, read_only_mode=False):
        captured.update(db_path=db_path, read_only_serve=read_only_mode)

    monkeypatch.setattr(cli, "server_main", fake_main)
    monkeypatch.setattr(
        "sys.argv", ["mi-fitness-bridge", "serve", "--read-only", "--db", str(tmp_path / "x.db")]
    )
    cli.main()
    assert captured["read_only_serve"] is True
