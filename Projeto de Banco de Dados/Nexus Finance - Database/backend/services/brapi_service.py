import json
import os
import urllib.parse
import urllib.request

# Cliente mínimo da brapi.dev (cotações). Ver docs/08-brapi.md.
BRAPI_BASE = "https://brapi.dev/api"
BRAPI_TOKEN = os.getenv("BRAPI_TOKEN", "")


def fetch_quotes(symbols: list[str]) -> dict[str, float]:
    """Retorna {symbol: regularMarketPrice} para os símbolos pedidos.
    Sem token, a brapi cobre apenas PETR4, MGLU3, VALE3, ITUB4. Lança em erro de rede."""
    if not symbols:
        return {}

    url = f"{BRAPI_BASE}/quote/{','.join(symbols)}"
    if BRAPI_TOKEN:
        url += "?" + urllib.parse.urlencode({"token": BRAPI_TOKEN})

    req = urllib.request.Request(url, headers={"User-Agent": "projeto-financeiro"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read())

    quotes: dict[str, float] = {}
    for item in data.get("results", []):
        price = item.get("regularMarketPrice")
        if item.get("symbol") and price is not None:
            quotes[item["symbol"]] = price
    return quotes
