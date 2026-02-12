import pandas as pd

from core.data.data_manager import MissionDataService
from core.integrations.webhook import post_webhook


class DummyResponse:
    def __init__(self, status_code=204, payload=None, text=""):
        self.status_code = status_code
        self._payload = payload
        self.text = text

    def json(self):
        if self._payload is None:
            raise ValueError("no json")
        return self._payload


def test_append_and_send_pipeline_with_retry(monkeypatch, tmp_path):
    excel_path = tmp_path / "mission.xlsx"
    service = MissionDataService()

    assert service.append_mission(str(excel_path), {"Planet": "Earth", "Enemy Type": "Terminids", "Kills": 12})
    df = service.read_mission_log(str(excel_path), use_cache=False)
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 1

    calls = {"count": 0}

    def fake_post(*args, **kwargs):
        calls["count"] += 1
        if calls["count"] == 1:
            return DummyResponse(status_code=429, payload={"message": "rate limited"})
        return DummyResponse(status_code=204)

    monkeypatch.setattr("core.integrations.webhook.requests.post", fake_post)

    success, response, err = post_webhook(
        "https://discord.com/api/webhooks/test", json_payload={"content": "ok"}, retries=1
    )
    assert success is True
    assert response is not None
    assert err is None
    assert calls["count"] == 2
