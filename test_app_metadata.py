from app import app, get_build_info


def test_get_build_info_uses_render_commit(monkeypatch):
    monkeypatch.setenv("RENDER_GIT_COMMIT", "0123456789abcdef")

    assert get_build_info() == {
        "version": "2.0.1",
        "commit": "0123456",
    }


def test_get_build_info_has_local_fallback(monkeypatch):
    monkeypatch.delenv("RENDER_GIT_COMMIT", raising=False)

    assert get_build_info()["commit"] == "local"


def test_health_returns_release_metadata(monkeypatch):
    monkeypatch.setenv("RENDER_GIT_COMMIT", "abcdef1234567890")

    with app.test_client() as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.get_json() == {
        "status": "ok",
        "version": "2.0.1",
        "commit": "abcdef1",
    }


def test_index_displays_release_metadata(monkeypatch):
    monkeypatch.setenv("RENDER_GIT_COMMIT", "abcdef1234567890")

    with app.test_client() as client:
        response = client.get("/")

    page = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "v2.0.1" in page
    assert "build abcdef1" in page
