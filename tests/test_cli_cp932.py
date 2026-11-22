"""Synthetic CLI checks with strict non-GBK output streams (cp932, cp1252).

Only synthetic values and monkeypatches are used; no cloud or keyring I/O.
"""
import io
import os
import subprocess
import sys
from contextlib import redirect_stdout
from pathlib import Path
from types import SimpleNamespace

import pytest

from mi_fitness_mcp import main as cli
from mi_fitness_mcp.config import Config

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
NON_GBK_ENCODINGS = ["cp932", "cp1252"]
SAMPLE_TEXT = "[OK] 配置向导 诊断 同步完成 status=ok\n"


def make_output(encoding):
    raw = io.BytesIO()
    stream = io.TextIOWrapper(raw, encoding=encoding, errors="strict", write_through=True)
    return SimpleNamespace(stream=stream, getvalue=raw.getvalue, encoding=encoding)


@pytest.fixture(params=NON_GBK_ENCODINGS)
def strict_output(request):
    output = make_output(request.param)
    cli._make_console_output_safe(output.stream)
    yield output
    output.stream.detach()


def run_cli(output, command, args):
    with redirect_stdout(output.stream):
        command(args)


def decoded(output):
    return output.getvalue().decode(output.encoding)


@pytest.fixture
def synthetic_config(monkeypatch, tmp_path):
    config_path = tmp_path / "config.json"
    config_path.write_text("{}", encoding="utf-8")
    config = Config(mode="mi_fitness_cloud", database_path=tmp_path / "synthetic.db")
    monkeypatch.setattr(cli, "get_config_path", lambda: config_path)
    monkeypatch.setattr(cli, "load_config", lambda: config)
    monkeypatch.setattr(cli, "resolve_database_path", lambda override: None)
    monkeypatch.setattr(cli, "keyring_backend_warning", lambda: "synthetic backend warning")
    monkeypatch.setattr(cli, "load_mi_fitness_token", lambda: ("synthetic-user", "synthetic-token"))
    return config


@pytest.mark.parametrize("encoding", NON_GBK_ENCODINGS)
def test_strict_non_gbk_stream_fails_without_helper(encoding):
    output = make_output(encoding)
    try:
        with pytest.raises(UnicodeEncodeError):
            output.stream.write(SAMPLE_TEXT)
    finally:
        output.stream.detach()


def test_helper_switches_errors_but_keeps_encoding(strict_output):
    assert strict_output.stream.errors == "backslashreplace"
    assert strict_output.stream.encoding == strict_output.encoding
    strict_output.stream.write(SAMPLE_TEXT)
    text = decoded(strict_output)
    assert "[OK]" in text
    assert "status=ok" in text
    assert "\\u5bfc" in text  # 导 is not representable in cp932 / cp1252


@pytest.mark.parametrize("connected", [True, False, None])
def test_doctor_strict_non_gbk_completes(monkeypatch, synthetic_config, strict_output, connected):
    closed = []

    class Adapter:
        region = "cn"

        async def connect(self):
            return connected

        def get_available_data_types(self):
            return ["daily_activity"]

        async def close(self):
            closed.append(True)

    monkeypatch.setattr(cli, "_create_cloud_adapter", lambda *args: Adapter())
    if connected is None:
        monkeypatch.setattr(cli, "load_mi_fitness_token", lambda: (None, None))
    if connected:
        run_cli(strict_output, cli.cmd_doctor, SimpleNamespace())
    else:
        with pytest.raises(SystemExit) as exc:
            run_cli(strict_output, cli.cmd_doctor, SimpleNamespace())
        assert exc.value.code == 1
    output = decoded(strict_output)
    assert "synthetic backend warning" in output
    assert "synthetic-token" not in output
    if connected is None:
        assert closed == []
    else:
        assert closed == [True]


def test_setup_strict_non_gbk_keeps_hidden_input_and_save(monkeypatch, strict_output):
    answers = iter(["synthetic-user", "cn"])
    saved = []
    monkeypatch.setattr("builtins.input", lambda prompt: next(answers))
    monkeypatch.setattr(cli.getpass, "getpass", lambda prompt: "synthetic-token")
    monkeypatch.setattr(cli, "save_mi_fitness_token", lambda *args: saved.append(args))
    monkeypatch.setattr(cli, "save_config", lambda config: None)
    monkeypatch.setattr(cli, "keyring_backend_warning", lambda: "synthetic backend warning")
    run_cli(strict_output, cli.cmd_setup, SimpleNamespace())
    output = decoded(strict_output)
    assert "[OK]" in output
    assert "synthetic-token" not in output
    assert saved == [("synthetic-user", "synthetic-token")]


@pytest.mark.parametrize("status", ["ok", "partial", "failed"])
def test_sync_strict_non_gbk_preserves_result_and_closes(
    monkeypatch, synthetic_config, strict_output, status
):
    closed = []
    calls = []

    class Adapter:
        async def connect(self):
            return True

        async def close(self):
            closed.append(True)

    class Service:
        async def sync_data_type(self, **kwargs):
            calls.append(kwargs)
            return {"status": status, "added": 0, "updated": 0, "error": "synthetic failure"}

    monkeypatch.setattr(cli, "Database", lambda path: object())
    monkeypatch.setattr(cli, "_create_cloud_adapter", lambda *args: Adapter())
    monkeypatch.setattr(cli, "SyncService", lambda *args, **kwargs: Service())
    args = SimpleNamespace(type="daily_activity", start_date=None, end_date=None)
    if status == "ok":
        run_cli(strict_output, cli.cmd_sync, args)
    else:
        with pytest.raises(SystemExit) as exc:
            run_cli(strict_output, cli.cmd_sync, args)
        assert exc.value.code == 1
    output = decoded(strict_output)
    assert len(calls) == 1
    assert "daily_activity" in output
    assert "synthetic-token" not in output
    assert closed == [True]
    if status == "ok":
        assert "[OK] daily_activity" in output
        final_line = "同步完成！".encode(strict_output.encoding, "backslashreplace")
        assert strict_output.getvalue().rstrip().endswith(final_line)
    else:
        assert "status=" + status in output


@pytest.mark.parametrize("encoding", ["utf-8", "utf8", "UTF-8", "utf-8-sig", "cp65001"])
def test_utf8_streams_are_left_strict_and_unchanged(encoding):
    plain = make_output(encoding)
    helped = make_output(encoding)
    try:
        cli._make_console_output_safe(helped.stream)
        assert helped.stream.errors == "strict"
        plain.stream.write(SAMPLE_TEXT)
        helped.stream.write(SAMPLE_TEXT)
        assert helped.getvalue() == plain.getvalue()
    finally:
        plain.stream.detach()
        helped.stream.detach()


def test_gbk_stream_output_bytes_unchanged():
    plain = make_output("gbk")
    helped = make_output("gbk")
    try:
        cli._make_console_output_safe(helped.stream)
        assert helped.stream.encoding == "gbk"
        plain.stream.write(SAMPLE_TEXT)
        helped.stream.write(SAMPLE_TEXT)
        assert helped.getvalue() == plain.getvalue()
        assert helped.getvalue() == SAMPLE_TEXT.encode("gbk")
    finally:
        plain.stream.detach()
        helped.stream.detach()


def test_non_strict_stream_is_left_alone():
    output = io.TextIOWrapper(io.BytesIO(), encoding="cp932", errors="replace")
    try:
        cli._make_console_output_safe(output)
        assert output.errors == "replace"
    finally:
        output.detach()


def test_stream_without_reconfigure_is_ignored():
    string_stream = io.StringIO()
    cli._make_console_output_safe(string_stream)
    string_stream.write(SAMPLE_TEXT)
    assert string_stream.getvalue() == SAMPLE_TEXT

    class Minimal:
        encoding = "cp932"
        errors = "strict"

        def write(self, text):
            return len(text)

    minimal = Minimal()
    cli._make_console_output_safe(minimal)
    assert minimal.errors == "strict"


def test_defaults_to_stdout_and_stderr(monkeypatch):
    out = make_output("cp932")
    err = make_output("cp1252")
    try:
        monkeypatch.setattr(cli.sys, "stdout", out.stream)
        monkeypatch.setattr(cli.sys, "stderr", err.stream)
        cli._make_console_output_safe()
        assert out.stream.errors == "backslashreplace"
        assert err.stream.errors == "backslashreplace"
    finally:
        monkeypatch.undo()
        out.stream.detach()
        err.stream.detach()


def test_main_applies_helper_before_parsing(monkeypatch):
    seen = []
    monkeypatch.setattr(cli, "_make_console_output_safe", lambda *streams: seen.append(streams))
    monkeypatch.setattr(cli.sys, "argv", ["mi-fitness-bridge", "--help"])
    with redirect_stdout(io.StringIO()), pytest.raises(SystemExit) as exc:
        cli.main()
    assert exc.value.code == 0
    assert seen == [()]


def test_help_exits_cleanly_with_cp932_stdio_in_subprocess():
    """End-to-end through the real ``main()`` with a cp932 stdout; ``--help`` needs no I/O."""
    env = {
        key: value
        for key, value in os.environ.items()
        if key not in {"PYTHONUTF8", "PYTHONIOENCODING", "PYTHONPATH"}
    }
    env.update(PYTHONIOENCODING="cp932", PYTHONUTF8="0", PYTHONPATH=str(SRC_DIR))
    result = subprocess.run(
        [sys.executable, "-c", "from mi_fitness_mcp.main import main; main()", "sync", "--help"],
        capture_output=True,
        env=env,
        timeout=60,
        check=False,
    )
    stderr = result.stderr.decode("cp932", errors="replace")
    assert result.returncode == 0, stderr
    assert "UnicodeEncodeError" not in stderr
    stdout = result.stdout.decode("cp932")
    assert "--start-date" in stdout
    assert "\\u" in stdout
