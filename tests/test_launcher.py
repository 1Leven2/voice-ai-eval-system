from app.launcher import build_uvicorn_command, find_free_port


def test_build_uvicorn_command_uses_project_app_without_reload():
    command = build_uvicorn_command(8123)
    assert command[-5:] == ["app.main:app", "--host", "127.0.0.1", "--port", "8123"]
    assert command[-1] == "8123"
    assert "--reload" not in command


def test_find_free_port_returns_a_valid_port(monkeypatch):
    class FakeSocket:
        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def setsockopt(self, *_):
            return None

        def bind(self, *_):
            return None

    monkeypatch.setattr("app.launcher.socket.socket", lambda *args: FakeSocket())
    port = find_free_port(8123, attempts=3)
    assert 8123 <= port <= 8125
