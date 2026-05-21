"""
Parte 1 — Módulo: src/infrastructure/tools/webhook_tool.py

ESCOPO
------
WebhookTool — consulta um webhook externo do cliente via HTTP POST.
Payload: {"query": "<termo>"}.
Resposta: JSON (lista ou dict) → formatada como string para a IA.

TIPOS DE TESTE
--------------
- unit         : todas as funções (httpx.post sempre mockado)
- fallback     : caminhos de erro (timeout, HTTP 5xx)
- regression   : header Authorization só quando token está configurado
"""
from unittest.mock import patch, MagicMock

import httpx
import pytest

from tests.shared.log_helper import logged

from src.infrastructure.tools.webhook_tool import WebhookTool


def _make_response(json_data=None, text=None, status_code=200):
    """Helper para construir resposta httpx mockada."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.text = text or ""
    if json_data is not None:
        resp.json.return_value = json_data
    else:
        resp.json.side_effect = Exception("no json")
    resp.raise_for_status = MagicMock()
    return resp


@pytest.mark.unit
@pytest.mark.part1
class TestWebhookToolExecute:
    """Comportamento normal — webhook responde com lista de objetos."""

    @logged
    def test_execute_returns_formatted_results(self):
        fake = _make_response(json_data=[
            {"produto": "Widget A", "preco": "10.00"},
            {"produto": "Widget B", "preco": "20.00"},
        ])
        with patch("httpx.post", return_value=fake):
            tool = WebhookTool(url="https://x.example/webhook", token="tok")
            result = tool.execute("widget")
        assert "Widget A" in result
        assert "Widget B" in result

    @logged
    def test_post_called_with_query_payload(self):
        fake = _make_response(json_data=[])
        with patch("httpx.post", return_value=fake) as mock_post:
            tool = WebhookTool(url="https://x.example/webhook")
            tool.execute("meu termo")
        kwargs = mock_post.call_args.kwargs
        assert kwargs["json"] == {"query": "meu termo"}

    @logged
    def test_authorization_header_present_when_token_set(self):
        fake = _make_response(json_data=[])
        with patch("httpx.post", return_value=fake) as mock_post:
            tool = WebhookTool(url="https://x.example/webhook", token="abc123")
            tool.execute("q")
        headers = mock_post.call_args.kwargs["headers"]
        assert headers["Authorization"] == "Bearer abc123"

    @logged
    def test_empty_results_returns_no_results_message(self):
        fake = _make_response(json_data=[])
        with patch("httpx.post", return_value=fake):
            tool = WebhookTool(url="https://x.example/webhook")
            result = tool.execute("nada")
        assert "No results found." == result

    @logged
    def test_dict_with_results_key_extracts_list(self):
        """Resposta {results: [...]} deve ser tratada como lista."""
        fake = _make_response(json_data={"results": [{"a": 1}, {"a": 2}]})
        with patch("httpx.post", return_value=fake):
            tool = WebhookTool(url="https://x.example/webhook")
            result = tool.execute("q")
        assert "1." in result and "2." in result


@pytest.mark.unit
@pytest.mark.regression
@pytest.mark.part1
class TestWebhookToolAuthOmission:
    """Sem token, NÃO pode haver header Authorization no POST."""

    @logged
    def test_no_authorization_header_when_token_absent(self):
        fake = _make_response(json_data=[])
        with patch("httpx.post", return_value=fake) as mock_post:
            tool = WebhookTool(url="https://x.example/webhook")
            tool.execute("q")
        headers = mock_post.call_args.kwargs["headers"]
        assert "Authorization" not in headers


@pytest.mark.fallback
@pytest.mark.part1
class TestWebhookToolErrors:
    """Caminhos de erro — timeout e HTTP error."""

    @logged
    def test_timeout_raises_timeout_error(self):
        with patch("httpx.post", side_effect=httpx.TimeoutException("timeout")):
            tool = WebhookTool(url="https://x.example/webhook")
            with pytest.raises(TimeoutError):
                tool.execute("q")

    @logged
    def test_http_error_raises_runtime_error(self):
        with patch("httpx.post", side_effect=httpx.HTTPError("500 erro")):
            tool = WebhookTool(url="https://x.example/webhook")
            with pytest.raises(RuntimeError):
                tool.execute("q")
