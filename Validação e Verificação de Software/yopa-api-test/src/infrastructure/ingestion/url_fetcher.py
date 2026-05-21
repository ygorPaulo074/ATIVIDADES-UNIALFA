"""
Fetches and extracts text content from external URLs.
Supports HTML (via BeautifulSoup) and RSS/Atom feeds (via feedparser).
Returns a list of dicts {"text": ...} in the same format as file_extractor.
"""
import httpx
from typing import Any


_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; AI-ChatBot/1.0; +https://github.com/anthropics)",
}
_TIMEOUT = 15


def fetch(url: str) -> list[dict[str, Any]]:
    with httpx.Client(follow_redirects=True, timeout=_TIMEOUT, headers=_HEADERS) as client:
        response = client.get(url)
        response.raise_for_status()

    content_type = response.headers.get("content-type", "")
    if "xml" in content_type or "rss" in content_type or "atom" in content_type:
        return _from_feed(response.text)
    return _from_html(response.text)


def _from_html(html: str) -> list[dict[str, Any]]:
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
        tag.decompose()
    records = []
    for tag in soup.find_all(["p", "h1", "h2", "h3", "h4", "li"]):
        text = tag.get_text(separator=" ", strip=True)
        if text:
            records.append({"text": text})
    return records


def _from_feed(xml: str) -> list[dict[str, Any]]:
    import feedparser
    feed = feedparser.parse(xml)
    records = []
    for entry in feed.entries:
        title = entry.get("title", "")
        summary = entry.get("summary", "")
        text = f"{title}. {summary}".strip(". ") if title or summary else None
        if text:
            records.append({"text": text})
    return records
