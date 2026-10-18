"""Keep every test isolated from developer credentials and network access."""

import socket

import pytest


@pytest.fixture(autouse=True)
def isolated_environment(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    for key in ("TMDB_TOKEN", "TAVILY_API_KEY", "OLLAMA_URL", "MODEL"):
        monkeypatch.delenv(f"CANIWATCH_{key}", raising=False)

    def no_network(*args, **kwargs):
        pytest.fail("Tests must not make real network connections")

    monkeypatch.setattr(socket.socket, "connect", no_network)
