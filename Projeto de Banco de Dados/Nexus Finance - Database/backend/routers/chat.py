import json
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from groq import BadRequestError
from services.groq_service import chat_com_tools, MODELO
from services.memory_service import (
    add_message, get_history, get_chat_name,
    criar_chat, listar_chats, excluir_chat,
    set_extrato, get_extrato,
)
from services.search_service import search
from services.csv_service import processar_csv, formatar_para_llm

router = APIRouter(prefix="", tags=["chat"])


# --- Modelos de request/response ---

class ChatRequest(BaseModel):
    chat_id: str
    message: str

class ChatResponse(BaseModel):
    response: str
    used_search: bool
    # Retornamos o nome atualizado para o frontend renomear na sidebar
    # após a primeira mensagem (quando o nome muda de "Novo chat" para o real)
    chat_name: str


# --- Ferramenta de busca enviada ao Groq ---

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "buscar_na_web",
            "description": (
                "Busca informações atualizadas na web. "
                "Use quando precisar de dados recentes, notícias ou fatos verificáveis. "
                "Para melhores resultados:\n"
                "- Prefira queries em inglês para temas técnicos ou internacionais\n"
                "- Seja específico: 'python asyncio tutorial 2024' é melhor que 'python async'\n"
                "- Para comparações, faça uma busca por item: não 'A vs B', "
                "mas 'vantagens de A' e depois 'vantagens de B'"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Query de busca específica e bem formulada, preferencialmente em inglês",
                    }
                },
                "required": ["query"],
            },
        },
    }
]

MAX_BUSCAS = 3


# --- Endpoints de gerenciamento de chats ---

@router.post("/chats")
def endpoint_criar_chat():
    """Cria um novo chat vazio e retorna seu id e nome inicial."""
    return criar_chat()


@router.get("/chats")
def endpoint_listar_chats():
    """Retorna a lista de todos os chats com id e nome."""
    return listar_chats()


@router.delete("/chats/{chat_id}")
def endpoint_excluir_chat(chat_id: str):
    """Remove o chat pelo id. Retorna erro 404 se não existir."""
    removido = excluir_chat(chat_id)
    if not removido:
        raise HTTPException(status_code=404, detail="Chat não encontrado")
    return {"ok": True}


# --- Endpoint principal de mensagem ---

@router.post("/chat", response_model=ChatResponse)
def endpoint_chat(req: ChatRequest):
    """
    Fluxo com tool use em loop:
    1. Salva mensagem do usuário no histórico do chat especificado
    2. Envia ao Groq com a ferramenta de busca disponível
    3. Enquanto o modelo pedir busca (e não exceder MAX_BUSCAS):
       - Executa cada tool call via Tavily
       - Injeta os resultados no histórico temporário
       - Faz nova chamada ao Groq com o contexto acumulado
    4. Salva resposta final e retorna ao frontend com o nome atualizado do chat
    """
    add_message(req.chat_id, "user", req.message)

    historico_loop = get_history(req.chat_id)
    # Busca o extrato do chat para injetar no contexto do Groq, se houver
    extrato = get_extrato(req.chat_id)

    try:
        resposta = chat_com_tools(historico_loop, TOOLS, extrato=extrato)
    except BadRequestError:
        # Modelo gerou tool call com formato inválido — retentar sem ferramentas
        resposta = chat_com_tools(historico_loop, [], extrato=extrato)

    used_search = False
    num_buscas = 0

    while resposta.tool_calls and num_buscas < MAX_BUSCAS:
        used_search = True
        num_buscas += 1

        historico_loop = historico_loop + [
            {
                "role": "assistant",
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in resposta.tool_calls
                ],
            }
        ]

        for tool_call in resposta.tool_calls:
            argumentos = json.loads(tool_call.function.arguments)
            query = argumentos.get("query", req.message)
            resultado_busca = search(query)
            historico_loop = historico_loop + [
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": resultado_busca,
                }
            ]

        try:
            resposta = chat_com_tools(historico_loop, TOOLS, extrato=extrato)
        except BadRequestError:
            resposta = chat_com_tools(historico_loop, [], extrato=extrato)

    texto_resposta = resposta.content or "Desculpe, não consegui formular uma resposta."
    add_message(req.chat_id, "assistant", texto_resposta)

    return ChatResponse(
        response=texto_resposta,
        used_search=used_search,
        chat_name=get_chat_name(req.chat_id),
    )


@router.post("/upload-extrato")
async def upload_extrato(
    chat_id: str = Form(...),
    arquivo: UploadFile = File(...)
):
    """
    Recebe o CSV do extrato bancário, processa e armazena no chat indicado.
    O extrato substituirá qualquer extrato anterior do mesmo chat.
    Retorna um resumo para o frontend exibir no badge e confirmar para o usuário.
    """
    if not arquivo.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Apenas arquivos .csv são aceitos.")

    conteudo_bytes = await arquivo.read()

    try:
        dados = processar_csv(conteudo_bytes, arquivo.filename)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao processar o arquivo: {str(e)}")

    # Armazena o extrato formatado no chat — substitui o anterior se houver
    extrato_formatado = formatar_para_llm(dados)
    set_extrato(chat_id, extrato_formatado)

    return {
        "success": True,
        "banco": dados["banco"],
        "periodo": dados["periodo"],
        "total_transacoes": dados["total_transacoes"],
        "total_entradas": dados["total_entradas"],
        "total_saidas": dados["total_saidas"],
        "saldo_periodo": dados["saldo_periodo"],
        "mensagem": f"Extrato do {dados['banco']} carregado! Agora você pode me perguntar sobre seus gastos.",
        "transacoes": dados["transacoes"],
    }
