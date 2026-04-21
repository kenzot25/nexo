import pytest


def test_create_mcp_server_when_dependency_available(tmp_path):
    pytest.importorskip("mcp")

    from nexo.serve import create_mcp_server

    server = create_mcp_server("nexo-out/graph.json")

    assert server is not None