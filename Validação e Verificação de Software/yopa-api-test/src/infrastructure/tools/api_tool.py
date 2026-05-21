"""
Search tool for a client-configured external REST API.
Issues a GET with a query param; raises TimeoutError if the API does not respond in time.
"""
import json
from typing import Any

import httpx


TOOL_DEFINITION = {
    "type": "function",
    "function": {
        "name": "search_api",
        "description": (
            "Search the external data source API for relevant information. "
            "Use this when the user asks about products, prices, policies, or any "
            "topic that may be available through the configured data source."
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


class ApiTool:

    def __init__(self, url: str, token: str | None = None, query_param: str = "q", timeout: float = _DEFAULT_TIMEOUT):
        self._url = url
        self._token = token
        self._query_param = query_param
        self._timeout = timeout

    def execute(self, query: str) -> str:
        headers = {}
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        try:
            response = httpx.get(self._url, params={self._query_param: query}, headers=headers, timeout=self._timeout)
            response.raise_for_status()
        except httpx.TimeoutException as exc:
            raise TimeoutError(f"API timeout after {self._timeout}s") from exc
        except httpx.HTTPError as exc:
            raise RuntimeError(f"API request failed: {exc}") from exc

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
