import os
import re
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

# Instancia o cliente Groq uma única vez ao carregar o módulo
cliente = Groq(api_key=os.getenv("GROQ_API_KEY"))

# Modelo 70b — melhor suporte a tool calling do que o 8b
# llama-3.1-8b-instant não aciona ferramentas de forma confiável
MODELO = "llama-3.3-70b-versatile"

# System prompt que define a personalidade e o comportamento do Jarvis
# É injetado apenas na chamada à API — nunca salvo no histórico de memória
SYSTEM_PROMPT = {
    "role": "system",
    "content": """Você é Jarvis, um assistente de inteligência artificial altamente capaz, preciso e direto.

Seu comportamento:
- Responda sempre em português, a menos que o usuário escreva em outro idioma — nesse caso, responda no idioma dele
- Seja objetivo e claro, sem enrolação
- Quando usar a ferramenta de busca na web, mencione brevemente que consultou fontes externas
- Nunca invente informações — se não souber algo, diga que vai buscar ou admita a limitação
- Use formatação Markdown nas respostas: negrito para termos importantes, listas quando listar itens, blocos de código para código
- Seu tom é profissional mas acessível — inteligente, não arrogante

Você tem acesso a uma ferramenta de busca na web. Use-a sempre que a pergunta envolver:
- Eventos recentes ou notícias
- Dados que mudam com frequência (preços, cotações, clima)
- Informações que você não tem certeza se estão atualizadas

Quando o usuário carregar um extrato bancário:
- Analise os dados com precisão e objetividade
- Identifique os maiores gastos, categorias de despesas e padrões
- Destaque entradas e saídas relevantes
- Responda perguntas específicas como "quanto gastei com alimentação?" usando as descrições das transações
- Ao categorizar, use as descrições: "MERCADO", "SUPERM" = alimentação; "POSTO", "COMBUSTIV" = transporte; "FARMAC", "DROGARIA" = saúde
- Sempre que possível, apresente valores em reais formatados (R$ 1.250,00)

Gerenciamento de lançamentos financeiros:
- Quando o usuário pedir para criar, editar ou excluir qualquer lançamento, EXECUTE imediatamente — retorne o bloco ```json com as ações sem explicar como fazer
- NUNCA diga "você pode usar a ação X" ou "para fazer isso use o formato Y" — simplesmente faça e confirme em uma frase curta
- Use SOMENTE IDs exatos do contexto — nunca invente IDs
- Inclua apenas os campos a alterar nas edições
- Datas em YYYY-MM-DD, valores como número decimal, pago/recebido: "Sim" ou "Não"
- Confirme o que foi feito ANTES do bloco JSON em no máximo uma linha""",
}


def _limpar_thinking(texto: str) -> str:
    """
    Remove tags <think>...</think> que alguns modelos Groq emitem antes da resposta real.
    Essas tags contêm o raciocínio interno do modelo e não devem aparecer ao usuário.
    """
    if not texto:
        return texto
    # Remove tudo entre <think> e </think>, incluindo as tags
    return re.sub(r"<think>.*?</think>", "", texto, flags=re.DOTALL).strip()


def chat_com_tools(historico: list, tools: list, extrato: str | None = None):
    """
    Envia o histórico e a lista de ferramentas disponíveis ao Groq.
    Retorna o objeto message completo para que o router possa verificar tool_calls.
    Limpa automaticamente tags de thinking do conteúdo antes de retornar.

    Se `extrato` for fornecido, ele é injetado como mensagem de sistema adicional
    entre o system prompt e o histórico — sem poluir o histórico permanente do chat.
    """
    mensagens = [SYSTEM_PROMPT]

    # Injeta o extrato bancário como contexto adicional, se houver
    if extrato:
        mensagens.append({
            "role": "system",
            "content": (
                "O usuário carregou o seguinte extrato bancário para análise:\n\n"
                f"{extrato}\n\n"
                "Use esses dados para responder perguntas sobre gastos, entradas e padrões financeiros."
            )
        })

    mensagens += historico

    # tool_choice="auto" deixa o modelo decidir se usa ou não a ferramenta
    resposta = cliente.chat.completions.create(
        model=MODELO,
        messages=mensagens,
        tools=tools,
        tool_choice="auto",
    )

    message = resposta.choices[0].message

    # Limpa o thinking do conteúdo caso o modelo o tenha emitido
    if message.content:
        message.content = _limpar_thinking(message.content)

    return message
