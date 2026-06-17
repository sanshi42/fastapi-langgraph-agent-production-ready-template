"""React SPA 托管路由测试."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import main


@pytest.fixture(name="spa_client")
def fixture_spa_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    """创建只复用主 app 路由的 SPA 测试客户端."""
    frontend_dir = tmp_path / "dist"
    assets_dir = frontend_dir / "assets"
    assets_dir.mkdir(parents=True)
    (frontend_dir / "index.html").write_text('<div id="root"></div>', encoding="utf-8")
    (frontend_dir / "settings.json").write_text('{"ok": true}', encoding="utf-8")

    monkeypatch.setattr(main, "FRONTEND_DIST_DIR", frontend_dir)
    monkeypatch.setattr(main, "FRONTEND_INDEX", frontend_dir / "index.html")
    monkeypatch.setattr(main, "FRONTEND_ASSETS_DIR", assets_dir)

    return TestClient(main.app)


def test_root_serves_spa_when_frontend_is_built(spa_client: TestClient):
    """前端构建存在时根路由应返回 SPA 入口."""
    response = spa_client.get("/")

    assert response.status_code == 200
    assert response.text == '<div id="root"></div>'


def test_spa_fallback_preserves_backend_namespaces(spa_client: TestClient):
    """SPA fallback 不应吞掉 API 和文档等后端命名空间."""
    api_response = spa_client.get("/api/missing")
    health_response = spa_client.get("/health")
    metrics_response = spa_client.get("/metrics")
    settings_response = spa_client.get("/settings")

    assert api_response.status_code == 404
    assert api_response.json() == {"detail": "Not Found"}
    assert health_response.headers["content-type"].startswith("application/json")
    assert "python_gc_objects_collected_total" in metrics_response.text
    assert settings_response.status_code == 200
    assert settings_response.text == '<div id="root"></div>'
