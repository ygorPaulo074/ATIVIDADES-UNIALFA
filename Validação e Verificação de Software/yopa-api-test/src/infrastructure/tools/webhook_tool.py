"""
Query tool via a client-registered webhook.
Issues a POST with {"query": "..."} in the body; raises TimeoutError if no response in time.
"""
import json
from typing import Any

import httpx


TOOL_DEFINITION = {
    "type": "function",
    "function": {
        "name": "search_webhook",
        "description": (
            "Query the client's registered webhook data source for relevant information. "
            "Use this when the user asks about products, orders, policies, or any "
            "topic that may be served by the configured webhook endpoint."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "The search query in natural language"}
            },
            "required": ["query"],
        },
    },
}

_DEFAULT_TIMEOUT = 5.0


class WebhookTool:

    def __init__(self, url: str, token: str | None = None, timeout: float = _DEFAULT_TIMEOUT):
        self._url = url
        self._token = token
        self._timeout = timeout

    def execute(self, query: str) -> str:
        headers = {"Content-Type": "application/json"}
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        try:
            response = httpx.post(self._url, json={"query": query}, headers=headers, timeout=self._timeout)
            response.raise_for_status()
        except httpx.TimeoutException as exc:
            raise TimeoutError(f"Webhook timeout after {self._timeout}s") from exc
        except httpx.HTTPError as exc:
            raise RuntimeError(f"Webhook request failed: {exc}") from exc

        try:
            data = response.json()
        except Exception:
            return response.text or "No results."

        return self._format(data)

    def _format(self, data: Any) -> str:
        if isinstance(data, list):
            records = data
        elif isinstance(data, dict):
            for key in ("results", "data", "items", "records"):
                if isinstance(data.get(key), list):
                    records = data[key]
                    break
            else:
                return json.dumps(data, ensure_ascii=False)
        else:
            return str(data)

        if not records:
            return "No results found."

        lines = []
        for i, record in enumerate(records[:5], 1):
            if isinstance(record, dict):
                row = " | ".join(f"{k}: {v}" for k, v in record.items() if v not in (None, ""))
            else:
                row = str(record)
            lines.append(f"{i}. {row}")
        return "\n".join(lines)
