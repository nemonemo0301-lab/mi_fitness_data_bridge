"""A passToken rotated by another local process is picked up before login. Synthetic only."""

import asyncio

import respx

from mi_fitness_mcp.adapters import mi_fitness_cloud as cloud

LOGIN = "https://account.xiaomi.com/pass/serviceLogin?_json=true&sid=miothealth"


def adapter():
    return cloud.MiFitnessCloudAdapter(user_id="synthetic-user", pass_token="synthetic-old")


def test_adopts_rotated_token_for_same_account(monkeypatch):
    monkeypatch.setattr(cloud, "load_mi_fitness_token", lambda: ("synthetic-user", "synthetic-new"))
    a = adapter()
    a._adopt_stored_token()
    assert a.pass_token == "synthetic-new"


def test_ignores_other_account_or_missing_token(monkeypatch):
    for stored in [("synthetic-other", "synthetic-new"), ("synthetic-user", None), (None, None)]:
        monkeypatch.setattr(cloud, "load_mi_fitness_token", lambda stored=stored: stored)
        a = adapter()
        a._adopt_stored_token()
        assert a.pass_token == "synthetic-old"


def test_connect_logs_in_with_stored_token(monkeypatch):
    monkeypatch.setattr(cloud, "load_mi_fitness_token", lambda: ("synthetic-user", "synthetic-new"))
    a = adapter()

    async def run():
        with respx.mock(assert_all_called=False) as mock:
            route = mock.get(LOGIN).respond(200, text="&&&START&&&{}")
            connected = await a.connect()
            await a.close()
            return connected, route

    connected, route = asyncio.run(run())
    assert connected is False  # synthetic login payload is incomplete
    cookie = route.calls.last.request.headers["Cookie"]
    assert "passToken=synthetic-new" in cookie
    assert "synthetic-old" not in cookie
