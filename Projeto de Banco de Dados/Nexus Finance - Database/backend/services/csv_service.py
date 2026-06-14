import csv
import io


# ---------------------------------------------------------------------------
# Mapeamento de categorias — mesmas categorias do app frontend
# ---------------------------------------------------------------------------
_CATEGORIAS: dict[str, list[str]] = {
    "Alimentação": [
        "MERCADO", "SUPERM", "HORTIFRUTI", "PADARIA", "ACOUGUE", "RESTAURANTE",
        "LANCHONETE", "IFOOD", "UBER EAT", "RAPPI", "BURGER", "PIZZA",
        "SUSHI", "CHURRASCO", "PANIFICA", "CAFE", "PASTEL", "SORVETE",
        "FRANGO", "PEIXARIA", "MINIMERCADO", "EMPORIO", "DELICATESSEN",
    ],
    "Transporte": [
        "POSTO ", "COMBUSTIV", "GASOLINA", "ETANOL", "SHELL", "PETROBRAS",
        "IPIRANGA", "BR DISTRIBUIDORA", "ESTACIONAM", "UBER", "99POP", "CABIFY",
        "METR", "ONIBUS", "PEDAGIO", "AUTOPECA", "OFICINA", "BORRACHARIA",
        "DETRAN", "DPVAT", "AUTOPASS", "BOM BILHETE",
    ],
    "Saúde": [
        "FARMAC", "DROGARIA", "DROGA", "ULTRAFARMA", "PACHECO", "PAGUE MENOS",
        "HOSPITAL", "CLINICA", "PLANO SAUDE", "UNIMED", "AMIL", "HAPVIDA",
        "SULAMERICA", "DENTISTA", "LABORATORIO", "EXAME", "CONSULTA", "MEDICO",
        "PSICOLOG", "NUTRI", "FISIO",
    ],
    "Educação": [
        "ESCOLA", "FACULDADE", "UNIVERSIDADE", "CURSO", "LIVRARIA",
        "UDEMY", "ALURA", "COURSERA", "DESCOMPLICA", "SARAIVA",
        "CULTURA ", "AMAZON EDUCATION",
    ],
    "Assinaturas": [
        "NETFLIX", "SPOTIFY", "AMAZON PRIME", "DISNEY", "HBO MAX", "MAX ",
        "GLOBOPLAY", "YOUTUBE", "DEEZER", "APPLE ONE", "MICROSOFT 365",
        "ASSINATURA", "SUBSCRIPTION", "PARAMOUNT", "CRUNCHYROLL",
    ],
    "Contas Fixas": [
        "ENEL", "CEMIG", "COPEL", "CPFL", "LIGHT ", "ENERGISA", "ELEKTRO",
        "SABESP", "CEDAE", "SANEPAR", "EMBASA",
        "COMGAS", "GAS NATURAL",
        "CLARO ", "VIVO ", "TIM ", "OI ", "NEXTEL",
        "NET ", "SKY ", "GVT", "EMBRATEL",
        "CONDOMIN", "IPTU", "IPVA", "LICENCIAMENTO",
    ],
    "Moradia": [
        "ALUGUEL", "IMOVEL", "IMOBILIARIA", "QUINTO ANDAR", "ZAP IMOVEIS",
    ],
    "Vestuário": [
        "RIACHUELO", "RENNER", "C&A", "MARISA", "ZARA", "H&M", "HERING",
        "LEVIS", "NIKE", "ADIDAS", "CALCADO", "SAPATO", "TENIS",
        "ROUPA", "MODA ", "VESTUARIO", "LOJAS AMERICANAS", "FOREVER 21",
    ],
    "Lazer": [
        "CINEMA", "TEATRO", "SHOW ", "HOTEL", "POUSADA",
        "AIRBNB", "BOOKING", "CVC ", "CLUBE", "PARQUE",
        "ACADEMIA", "SMARTFIT", "BLUEFIT", "CROSSFIT", "BEACH TENNIS",
        "VIAGEM", "PASSAGEM", "LATAM", "GOL ", "AZUL ",
    ],
}


def categorizar(descricao: str) -> str:
    """Mapeia a descrição da transação para uma categoria do app."""
    desc = descricao.upper()
    for categoria, palavras in _CATEGORIAS.items():
        if any(p in desc for p in palavras):
            return categoria
    return "Outros"


def normalizar_data(data_str: str) -> str:
    """Converte DD/MM/YYYY para YYYY-MM-DD. Deixa YYYY-MM-DD intacto."""
    data_str = data_str.strip()
    if "/" in data_str:
        partes = data_str.split("/")
        if len(partes) == 3:
            return f"{partes[2]}-{partes[1].zfill(2)}-{partes[0].zfill(2)}"
    return data_str


# ---------------------------------------------------------------------------

def detectar_banco(conteudo: str, nome_arquivo: str) -> str:
    """Detecta o banco pelo conteúdo ou nome do arquivo."""
    nome = nome_arquivo.lower()
    conteudo_lower = conteudo.lower()

    if "nubank" in nome or "date,title,amount" in conteudo_lower:
        return "nubank_cartao"
    if "nubank" in conteudo_lower and "descrição" in conteudo_lower:
        return "nubank_conta"
    if "itaú" in conteudo_lower or "itau" in nome or "crédito(r$)" in conteudo_lower:
        return "itau"
    if "bradesco" in conteudo_lower or "bradesco" in nome:
        return "bradesco"
    if "santander" in conteudo_lower or "santander" in nome:
        return "santander"

    return "desconhecido"


def limpar_valor(valor_str: str) -> float:
    """Converte string de valor brasileiro para float."""
    if not valor_str or valor_str.strip() == "":
        return 0.0
    v = valor_str.strip().replace("R$", "").replace(" ", "")
    # Formato brasileiro: 1.250,90 → 1250.90
    if "," in v and "." in v:
        v = v.replace(".", "").replace(",", ".")
    elif "," in v:
        v = v.replace(",", ".")
    try:
        return float(v)
    except ValueError:
        return 0.0


def encontrar_linha_cabecalho(linhas: list, separador: str, colunas_esperadas: list) -> int:
    """Encontra o índice da linha onde começa a tabela de dados."""
    for i, linha in enumerate(linhas):
        partes = [p.strip().lower() for p in linha.split(separador)]
        matches = sum(1 for col in colunas_esperadas if any(col in p for p in partes))
        if matches >= 2:
            return i
    return 0


def ler_csv(conteudo: str, separador: str = ",", skip: int = 0) -> list:
    """
    Lê o CSV em uma lista de dicts usando o módulo padrão do Python.
    `skip` pula as linhas de cabeçalho antes da tabela real.
    """
    linhas = conteudo.splitlines()
    conteudo_util = "\n".join(linhas[skip:])
    reader = csv.DictReader(io.StringIO(conteudo_util), delimiter=separador)
    # Normaliza os nomes das colunas: remove espaços extras e converte para minúsculo
    rows = []
    for row in reader:
        rows.append({k.strip().lower(): v.strip() if v else "" for k, v in row.items()})
    return rows


def parsear_nubank_cartao(conteudo: str) -> list:
    """
    Fatura do Nubank: valor positivo = compra/gasto, valor negativo = pagamento/estorno.
    Invertemos o sinal para que gastos fiquem negativos (padrão do app).
    """
    rows = ler_csv(conteudo, separador=",")
    transacoes = []
    for row in rows:
        valor_raw = limpar_valor(row.get("amount", "0"))
        descricao = row.get("title", "").upper()
        if not descricao:
            continue
        # Na fatura Nubank: positivo = gasto → converte para negativo
        # negativo = pagamento/estorno → converte para positivo
        valor = -valor_raw
        transacoes.append({
            "data": row.get("date", "").strip(),
            "descricao": descricao,
            "valor": valor,
            "tipo": "debito" if valor < 0 else "credito",
        })
    return transacoes


def parsear_nubank_conta(conteudo: str) -> list:
    rows = ler_csv(conteudo, separador=",")
    transacoes = []
    for row in rows:
        valor = limpar_valor(row.get("valor", "0"))
        # O campo pode vir como "descrição" (com acento) ou "descricao"
        descricao = (row.get("descrição") or row.get("descricao") or "").upper()
        if not descricao:
            continue
        transacoes.append({
            "data": row.get("data", "").strip(),
            "descricao": descricao,
            "valor": valor,
            "tipo": "credito" if valor > 0 else "debito",
        })
    return transacoes


def parsear_itau(conteudo: str) -> list:
    linhas = conteudo.splitlines()
    skip = encontrar_linha_cabecalho(linhas, ";", ["data", "histórico", "crédito", "débito"])
    rows = ler_csv(conteudo, separador=";", skip=skip)
    transacoes = []
    for row in rows:
        data = row.get("data", "").strip()
        if not data or data.lower() == "nan":
            continue
        # Itaú separa crédito e débito em colunas distintas
        credito = limpar_valor(row.get("crédito(r$)") or row.get("credito(r$)") or "0")
        debito = limpar_valor(row.get("débito(r$)") or row.get("debito(r$)") or "0")
        if credito > 0:
            valor, tipo = credito, "credito"
        else:
            valor, tipo = -abs(debito), "debito"
        descricao = (row.get("histórico") or row.get("historico") or "").upper()
        if not descricao:
            continue
        transacoes.append({"data": data, "descricao": descricao, "valor": valor, "tipo": tipo})
    return transacoes


def parsear_bradesco(conteudo: str) -> list:
    linhas = conteudo.splitlines()
    skip = encontrar_linha_cabecalho(linhas, ";", ["data", "histórico", "valor"])
    rows = ler_csv(conteudo, separador=";", skip=skip)
    transacoes = []
    for row in rows:
        data = row.get("data", "").strip()
        if not data or data.lower() == "nan":
            continue
        # Bradesco usa valor único com sinal
        valor_col = next((k for k in row if "valor" in k), None)
        valor = limpar_valor(row[valor_col]) if valor_col else 0.0
        descricao = (row.get("histórico") or row.get("historico") or "").upper()
        if not descricao:
            continue
        transacoes.append({
            "data": data,
            "descricao": descricao,
            "valor": valor,
            "tipo": "credito" if valor > 0 else "debito",
        })
    return transacoes


def parsear_santander(conteudo: str) -> list:
    linhas = conteudo.splitlines()
    skip = encontrar_linha_cabecalho(linhas, ";", ["data", "histórico", "valor"])
    rows = ler_csv(conteudo, separador=";", skip=skip)
    transacoes = []
    for row in rows:
        data = row.get("data", "").strip()
        if not data or data.lower() == "nan":
            continue
        valor_col = next((k for k in row if "valor" in k), None)
        valor = limpar_valor(row[valor_col]) if valor_col else 0.0
        descricao = (row.get("histórico") or row.get("historico") or "").upper()
        if not descricao:
            continue
        transacoes.append({
            "data": data,
            "descricao": descricao,
            "valor": valor,
            "tipo": "credito" if valor > 0 else "debito",
        })
    return transacoes


def processar_csv(conteudo_bytes: bytes, nome_arquivo: str) -> dict:
    """
    Função principal. Recebe os bytes do arquivo e o nome,
    detecta o banco, faz o parsing e retorna a estrutura normalizada.
    """
    # Tenta UTF-8 primeiro, depois latin-1
    try:
        conteudo = conteudo_bytes.decode("utf-8")
    except UnicodeDecodeError:
        conteudo = conteudo_bytes.decode("latin-1")

    banco = detectar_banco(conteudo, nome_arquivo)

    parsers = {
        "nubank_cartao": parsear_nubank_cartao,
        "nubank_conta":  parsear_nubank_conta,
        "itau":          parsear_itau,
        "bradesco":      parsear_bradesco,
        "santander":     parsear_santander,
    }

    if banco not in parsers:
        raise ValueError(
            "Banco não reconhecido. Certifique-se de que o arquivo é de um dos bancos "
            "suportados: Nubank, Itaú, Bradesco ou Santander."
        )

    transacoes = parsers[banco](conteudo)
    # Remove linhas com descrição vazia (rodapés ou totalizadores do CSV)
    transacoes = [t for t in transacoes if t["descricao"]]

    # Pós-processamento: normaliza datas e atribui categorias
    for t in transacoes:
        t["data"] = normalizar_data(t["data"])
        t["categoria"] = categorizar(t["descricao"])

    entradas = sum(t["valor"] for t in transacoes if t["valor"] > 0)
    saidas   = sum(t["valor"] for t in transacoes if t["valor"] < 0)

    datas = [t["data"] for t in transacoes if t["data"]]
    periodo = f"{datas[-1]} a {datas[0]}" if len(datas) >= 2 else "período desconhecido"

    return {
        "banco":            banco.replace("_", " ").title(),
        "periodo":          periodo,
        "total_transacoes": len(transacoes),
        "total_entradas":   round(entradas, 2),
        "total_saidas":     round(saidas, 2),
        "saldo_periodo":    round(entradas + saidas, 2),
        "transacoes":       transacoes,
    }


def formatar_para_llm(dados: dict) -> str:
    """
    Formata os dados do extrato para injetar no contexto do LLM.
    Usa texto corrido (não JSON) para economizar tokens do contexto.
    """
    linhas = [
        "=== EXTRATO BANCÁRIO ===",
        f"Banco: {dados['banco']}",
        f"Período: {dados['periodo']}",
        f"Total de transações: {dados['total_transacoes']}",
        f"Total entradas: R$ {dados['total_entradas']:,.2f}",
        f"Total saídas: R$ {abs(dados['total_saidas']):,.2f}",
        f"Saldo do período: R$ {dados['saldo_periodo']:,.2f}",
        "",
        "TRANSAÇÕES:",
        "Data | Descrição | Valor",
    ]
    for t in dados["transacoes"]:
        sinal = "+" if t["valor"] > 0 else ""
        linhas.append(f"{t['data']} | {t['descricao']} | {sinal}R$ {t['valor']:,.2f}")

    return "\n".join(linhas)
