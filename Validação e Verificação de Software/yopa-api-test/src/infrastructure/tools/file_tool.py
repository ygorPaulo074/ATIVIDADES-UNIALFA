"""
Search tool over the agent's indexed knowledge base files.
Runs a simple relevance search (keyword matching) over the in-memory records.
"""
from typing import Any


TOOL_DEFINITION = {
    "type": "function",
    "function": {
        "name": "search_knowledge_base",
        "description": (
            "Search the agent's knowledge base for relevant information. "
            "Use this when the user asks about products, prices, policies, or any "
            "topic that may be in the indexed documents."
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


class FileTool:

    def __init__(self, all_records: list[dict[str, Any]]):
        self._records = all_records

    def search(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        if not self._records:
            return []
        keywords = set(query.lower().split())
        scored = []
        for record in self._records:
            text = " ".join(str(v) for v in record.values()).lower()
            score = sum(1 for kw in keywords if kw in text)
            if score > 0:
                scored.append((score, record))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [r for _, r in scored[:top_k]]

    def format_results(self, results: list[dict[str, Any]]) -> str:
        if not results:
            return "No relevant information found in the knowledge base."
        lines = []
        for i, record in enumerate(results, 1):
            row = " | ".join(f"{k}: {v}" for k, v in record.items() if v not in (None, ""))
            lines.append(f"{i}. {row}")
        return "\n".join(lines)

    def execute(self, query: str) -> str:
        return self.format_results(self.search(query))
