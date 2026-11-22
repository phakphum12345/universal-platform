from pathlib import Path

import pytest

from universal_platform.engineering import cad_generator_server


def test_windows_default_data_directory_uses_local_app_data(tmp_path):
    result = cad_generator_server.resolve_data_directory(
        local_app_data=tmp_path / "Local",
        home=tmp_path,
        windows=True,
    )

    assert result == (tmp_path / "Local" / "UniversalPlatform" / "CADGenerator").resolve()


def test_non_windows_default_data_directory_uses_xdg_data_home(tmp_path):
    result = cad_generator_server.resolve_data_directory(
        xdg_data_home=tmp_path / "xdg",
        home=tmp_path,
        windows=False,
    )

    assert result == (tmp_path / "xdg" / "UniversalPlatform" / "CADGenerator").resolve()


def test_explicit_data_directory_overrides_platform_defaults(tmp_path):
    selected = tmp_path / "custom-data"
    result = cad_generator_server.resolve_data_directory(
        selected,
        local_app_data=tmp_path / "ignored",
        windows=True,
    )

    assert result == selected.resolve()


def test_local_server_binds_loopback_with_dynamic_port_and_persistent_stores(tmp_path):
    server, token, generated, data_path = cad_generator_server.create_local_server(tmp_path)

    try:
        assert server.server_address[0] == "127.0.0.1"
        assert server.server_port > 0
        assert len(token.encode("utf-8")) >= 32
        assert generated is True
        assert data_path == tmp_path.resolve()
        assert (data_path / "feature-history.sqlite3").is_file()
        assert (data_path / "feature-artifacts.sqlite3").is_file()
        assert (data_path / "cad-api-audit.sqlite3").is_file()
    finally:
        server.server_close()


def test_local_server_rejects_short_tokens_and_invalid_ports(tmp_path):
    with pytest.raises(ValueError, match="32 UTF-8 bytes"):
        cad_generator_server.create_local_server(tmp_path / "short", bearer_token="short")
    with pytest.raises(ValueError, match="port"):
        cad_generator_server.create_local_server(tmp_path / "port", port=65536)
    with pytest.raises(ValueError, match="port"):
        cad_generator_server.create_local_server(tmp_path / "bool-port", port=True)


def test_main_prints_generated_token_once_and_closes_server(monkeypatch, tmp_path, capsys):
    token = "generated-test-token-with-at-least-32-bytes"
    state = {"closed": False}

    class FakeServer:
        server_port = 54321

        def serve_forever(self, *, poll_interval):
            assert poll_interval == 0.5
            raise KeyboardInterrupt

        def server_close(self):
            state["closed"] = True

    server = FakeServer()

    def fake_create_local_server(data_directory, *, port, bearer_token):
        assert Path(data_directory) == tmp_path.resolve()
        assert port == 0
        assert bearer_token is None
        return server, token, True, tmp_path.resolve()

    monkeypatch.delenv("UP_CAD_BEARER_TOKEN", raising=False)
    monkeypatch.setattr(cad_generator_server, "create_local_server", fake_create_local_server)

    assert cad_generator_server.main(["--data-dir", str(tmp_path)]) == 0
    output = capsys.readouterr().out
    assert "http://127.0.0.1:54321/control-center" in output
    assert token in output
    assert state["closed"] is True


def test_main_never_echoes_an_environment_supplied_token(monkeypatch, tmp_path, capsys):
    token = "environment-secret-token-with-at-least-32-bytes"
    state = {"closed": False}

    class FakeServer:
        server_port = 54322

        def serve_forever(self, *, poll_interval):
            raise KeyboardInterrupt

        def server_close(self):
            state["closed"] = True

    def fake_create_local_server(data_directory, *, port, bearer_token):
        assert bearer_token == token
        return FakeServer(), token, False, tmp_path.resolve()

    monkeypatch.setenv("UP_CAD_BEARER_TOKEN", token)
    monkeypatch.setattr(cad_generator_server, "create_local_server", fake_create_local_server)

    assert cad_generator_server.main(["--data-dir", str(tmp_path)]) == 0
    output = capsys.readouterr().out
    assert token not in output
    assert "value not echoed" in output
    assert state["closed"] is True
