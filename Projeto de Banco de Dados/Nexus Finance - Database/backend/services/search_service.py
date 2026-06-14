import os
from tavily import TavilyClient
from dotenv import load_dotenv

load_dotenv()

# Instancia o cliente Tavily uma única vez ao carregar o módulo
cliente = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))


def _formatar_resultados(resultado: dict) -> str:
    """
    Formata o dicionário bruto retornado pelo Tavily em texto estruturado.
    Headers em maiúsculo e fontes numeradas ajudam o modelo a segmentar
    e referenciar o contexto com mais precisão.
    """
    texto = f"RESPOSTA SINTETIZADA DO TAVILY:\n{resultado.get('answer', 'N/A')}\n\n"
    texto += "FONTES ENCONTRADAS:\n"

    for i, item in enumerate(resultado.get("results", []), 1):
        titulo = item.get("title", "Sem título")
        url = item.get("url", "")
        conteudo = item.get("content", "")
        texto += f"\n[Fonte {i}] {titulo}\nURL: {url}\n{conteudo}\n"

    return texto


def search(query: str) -> str:
    """
    Realiza uma busca na web usando o Tavily e retorna os resultados
    formatados como texto simples para ser injetado no contexto do modelo.
    - search_depth="advanced": rastreia as páginas com mais profundidade
    - include_answer=True: Tavily sintetiza uma resposta antes dos links, enriquecendo o contexto
    - max_results=7 mantém a cobertura sem ultrapassar o contexto do modelo
    """
    resultado = cliente.search(
        query=query,
        max_results=7,
        search_depth="advanced",
        include_answer=True,
    )

    if not resultado.get("results"):
        return "Nenhum resultado encontrado na busca."

    return _formatar_resultados(resultado)
