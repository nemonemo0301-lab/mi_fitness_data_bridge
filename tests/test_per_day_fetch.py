"""High-frequency keys are fetched one day per request. Synthetic data only."""

import asyncio
import json

from mi_fitness_mcp.adapters.mi_fitness_cloud import MiFitnessCloudAdapter

DAY_START = {"2026-01-10": 1768003200, "2026-01-11": 1768089600, "2026-01-12": 1768176000}


def fake_item(key, ts):
    value = {"bpm": 70, "time": ts, "type": 0} if key == "heart_rate" else {"stress": 20, "time": ts}
    return {"key": key, "time": ts, "zone_offset": 0, "zone_name": "UTC", "value": json.dumps(value)}


def make_adapter(calls):
    adapter = MiFitnessCloudAdapter(user_id="synthetic-user", pass_token="synthetic-token")
    adapter._connected = True
    adapter._client = object()  # is_connected() only checks it is not None

    async def fake_fetch_key(key, start_date, end_date, region=None):
        calls.append((key, start_date, end_date))
        if key == "resting_heart_rate":
            return []
        # 1-minute data: 1440 records per day
        return [fake_item(key, DAY_START[start_date] + 60 * i) for i in range(1440)]

    adapter._fetch_key = fake_fetch_key
    return adapter


async def collect(agen):
    return [x async for x in agen]


def test_heart_rate_requests_one_day_at_a_time():
    calls = []
    adapter = make_adapter(calls)
    samples = asyncio.run(collect(adapter.iter_heart_rate("2026-01-10", "2026-01-12")))
    hr_calls = [c for c in calls if c[0] == "heart_rate"]
    assert hr_calls == [
        ("heart_rate", "2026-01-10", "2026-01-10"),
        ("heart_rate", "2026-01-11", "2026-01-11"),
        ("heart_rate", "2026-01-12", "2026-01-12"),
    ]
    assert len(samples) == 3 * 1440
    assert len({s.id for s in samples}) == 3 * 1440


def test_stress_requests_one_day_at_a_time():
    calls = []
    adapter = make_adapter(calls)
    samples = asyncio.run(collect(adapter.iter_stress("2026-01-11", "2026-01-12")))
    assert calls == [
        ("stress", "2026-01-11", "2026-01-11"),
        ("stress", "2026-01-12", "2026-01-12"),
    ]
    assert len(samples) == 2 * 1440


def test_single_day_range_makes_one_request():
    calls = []
    adapter = make_adapter(calls)
    asyncio.run(collect(adapter.iter_stress("2026-01-10", "2026-01-10")))
    assert calls == [("stress", "2026-01-10", "2026-01-10")]
