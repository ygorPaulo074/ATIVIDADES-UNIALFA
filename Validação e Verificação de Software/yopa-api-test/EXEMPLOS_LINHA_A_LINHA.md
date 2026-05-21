# Exemplos práticos — explicação linha a linha

Material pronto para colar na documentação `.docx`. Os três exemplos
são reais, executáveis (`pytest` passa em todos) e foram escolhidos
por:

- exibir o conceito principal de cada tipo (unit, integração, mock)
- caber em uma página/slide sem perda de clareza
- usar funções e classes do projeto AI-ChatBot (estado pós-DDD)

Comando para reproduzir cada exemplo:

```bash
cd /home/pygor/projetos/yopa-api-test
venv/bin/python -m pytest tests/part1/<arquivo>::<Classe>::<teste> -v
```

---

## 1. Teste UNITÁRIO

**Arquivo:** `tests/part1/test_security.py`
**Classe::método:** `TestHashApiKey::test_hash_is_deterministic`
**Módulo testado:** `src/infrastructure/security.py`
**Função alvo:** `hash_api_key(key: str) -> str`
**Tipo:** unitário puro — função determinística, sem I/O, sem dependências externas.

### Código completo

```python
import pytest

from tests.shared.log_helper import logged

from src.infrastructure.security import hash_api_key


@pytest.mark.unit
@pytest.mark.part1
class TestHashApiKey:
    """Validar geração de hash SHA-256 a partir da api_key."""

    @logged
    def test_hash_is_deterministic(self):
        """hash_api_key(x) sempre retorna o mesmo digest para o mesmo input."""
        assert hash_api_key("abc123") == hash_api_key("abc123")
```

### Explicação por bloco

**Bloco 1 — Imports (linhas 1–5)**

- `import pytest` — framework de testes; usado para os decoradores de marker.
- `from tests.shared.log_helper import logged` — decorator próprio do projeto
  que loga `START`, `PASS`/`FAIL` e duração de cada teste em `logs/`.
- `from src.infrastructure.security import hash_api_key` — importa apenas a
  função que vamos testar. Isolamento: nada além disso.

**Bloco 2 — Markers da classe (linhas 8–9)**

- `@pytest.mark.unit` — marca a classe inteira como "teste unitário".
  Permite executar só os unitários com `pytest -m unit`.
- `@pytest.mark.part1` — sinaliza que pertence à Parte 1 do trabalho.

**Bloco 3 — Classe agrupadora (linhas 10–11)**

- `class TestHashApiKey:` — agrupa testes relacionados à mesma função.
  O nome começa com `Test` porque o pytest descobre classes assim por
  convenção (configurável em `pytest.ini`).
- Docstring documenta o que a classe valida.

**Bloco 4 — O teste em si (linhas 13–16)**

- `@logged` — registra início e fim do teste no arquivo de log da rodada.
- `def test_hash_is_deterministic(self):` — pytest descobre métodos que
  começam com `test_`. O `self` é da classe.
- A docstring explica em uma linha o invariante validado.
- `assert hash_api_key("abc123") == hash_api_key("abc123")` — o teste em
  si: chamar a função duas vezes com o mesmo input deve produzir o
  mesmo resultado. Se mudar para `hash_api_key("abc123") == hash_api_key("abd123")`,
  o teste falha — esse é o sinal de que `hash_api_key` mudou de
  comportamento (deixou de ser determinístico).

### Por que é unitário (e não integração ou sistema)

- Não toca sistema de arquivos, rede, banco, cache ou outra unidade.
- Testa **uma função pura** isoladamente.
- Roda em microssegundos, sem fixtures pesadas.

### O que aprenderíamos se este teste quebrasse

Que `hash_api_key` deixou de ser determinístico — provavelmente alguém
trocou `hashlib.sha256` por algo que injeta sal aleatório. Como o
projeto verifica a API key comparando o hash armazenado com o hash da
chave recebida (`verify_api_key`), uma função não-determinística
quebraria toda a autenticação.

---

## 2. Teste de INTEGRAÇÃO

**Arquivo:** `tests/part1/test_persistence_drivers.py`
**Classe::método:** `TestContextHistory::test_save_v2_keeps_v1_in_history`
**Módulo testado:** `src/infrastructure/persistence/drivers/local.py`
**Comportamento alvo:** o driver Local grava versões anteriores em `context/history/v{n}.json`.
**Tipo:** integração — duas unidades reais (driver + filesystem) trabalhando juntas, sem mocks.

### Código completo

```python
import pytest
from datetime import datetime, timezone

from tests.shared.log_helper import logged

from src.infrastructure.persistence.drivers.local import LocalDriver
from src.domain.agent import AgentContextBase, AgentContextRecord


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ctx_record(agent_id="a1", version=1, persona="Persona") -> AgentContextRecord:
    return AgentContextRecord(
        agent_id=agent_id,
        version=version,
        context=AgentContextBase(persona=persona, language="pt"),
        updated_at=_now(),
    )


@pytest.mark.integration
@pytest.mark.part1
class TestContextHistory:
    """Versionamento de contexto."""

    @logged
    def test_save_v2_keeps_v1_in_history(self):
        d = LocalDriver()
        d.save_context(_ctx_record("a1", version=1, persona="P1"))
        d.save_context(_ctx_record("a1", version=2, persona="P2"))
        history = d.load_context_history("a1")
        versions = [r.version for r in history]
        assert 1 in versions
        assert 2 in versions
```

### Explicação por bloco

**Bloco 1 — Imports (linhas 1–8)**

- `LocalDriver` — driver real de persistência (escreve JSON em disco).
- `AgentContextBase`, `AgentContextRecord` — entidades do domínio.
- Sem mocks. Sem fakes. Tudo real.

**Bloco 2 — Helpers (linhas 11–22)**

- `_now()` produz um timestamp ISO 8601 para preencher `updated_at`.
- `_ctx_record(...)` é um *factory* que monta um `AgentContextRecord`
  com defaults. Reduz boilerplate em vários testes do mesmo arquivo.

**Bloco 3 — Markers (linhas 25–26)**

- `@pytest.mark.integration` — categoriza este teste como integração.

**Bloco 4 — Setup implícito**

Antes deste teste rodar, o `conftest.py` aplica a fixture autouse
`patch_env`, que:

- Substitui o cliente Redis real por `fakeredis`.
- Aponta `settings.DATA_PATH` para um `tmp_path` (pasta temporária
  exclusiva deste teste).

Isso garante isolamento entre testes — o disco real **não** é tocado.

**Bloco 5 — O teste (linhas 30–36)**

- `d = LocalDriver()` — instancia o driver real. Ele já lê o
  `DATA_PATH` do `settings`, que aponta para `tmp_path`.
- `d.save_context(...v1...)` — grava versão 1 em
  `<tmp_path>/agents/a1/context/current.json` E em
  `<tmp_path>/agents/a1/context/history/v1.json`.
- `d.save_context(...v2...)` — grava versão 2. A versão 1 deve
  permanecer em `history/v1.json`.
- `d.load_context_history("a1")` — lê todos os arquivos `v*.json` do
  diretório e devolve a lista de `AgentContextRecord`.
- `assert 1 in versions and 2 in versions` — confirma que ambas as
  versões estão preservadas no histórico.

### Por que é integração (e não unitário ou sistema)

- Unitário seria testar `LocalDriver._write` isoladamente, mockando
  filesystem.
- Sistema seria fazer `PUT /agent/context` via TestClient e verificar
  o histórico pelo retorno HTTP.
- Aqui usamos o driver **real** + filesystem **real** (em diretório
  temporário): duas unidades integradas, mas ainda abaixo da fronteira
  HTTP. É o nível clássico de teste de integração.

### O que aprenderíamos se este teste quebrasse

Que o `save_context` não está mais preservando histórico — ou está
sobrescrevendo `history/v1.json` quando salva a v2, ou
`load_context_history` parou de ler todos os arquivos. Ambos quebram
a feature `GET /agent/context/history`, que o cliente usa para
auditar mudanças no comportamento do agente.

---

## 3. Teste com MOCK

**Arquivo:** `tests/part1/test_webhook_tool.py`
**Classe::método:** `TestWebhookToolExecute::test_post_called_with_query_payload`
**Módulo testado:** `src/infrastructure/tools/webhook_tool.py`
**Função alvo:** `WebhookTool.execute(query: str) -> str`
**Tipo:** unitário com mock — substituímos a dependência externa
(`httpx.post`) por uma resposta controlada para verificar o
**comportamento de chamada** da `WebhookTool`.

### Código completo

```python
from unittest.mock import patch, MagicMock

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
    resp.raise_for_status = MagicMock()
    return resp


@pytest.mark.unit
@pytest.mark.part1
class TestWebhookToolExecute:

    @logged
    def test_post_called_with_query_payload(self):
        fake = _make_response(json_data=[])
        with patch("httpx.post", return_value=fake) as mock_post:
            tool = WebhookTool(url="https://x.example/webhook")
            tool.execute("meu termo")
        kwargs = mock_post.call_args.kwargs
        assert kwargs["json"] == {"query": "meu termo"}
```

### Explicação por bloco

**Bloco 1 — Imports (linhas 1–7)**

- `from unittest.mock import patch, MagicMock` — a biblioteca padrão
  do Python para mocks. Não precisamos instalar nada extra.
- `patch` substitui temporariamente um objeto por um mock.
- `MagicMock` é um objeto fake configurável (atributos retornam outros
  mocks por padrão, métodos podem ter `return_value` definido).

**Bloco 2 — Helper de resposta fake (linhas 10–18)**

Cria um objeto que se comporta como uma resposta `httpx`:

- `.status_code`, `.text`, `.json()` e `.raise_for_status()`.
- É reaproveitado em vários testes da mesma classe.

**Bloco 3 — Setup do teste (linhas 27–28)**

- `fake = _make_response(json_data=[])` — resposta vazia (lista vazia
  de resultados). O conteúdo não importa aqui — o foco é o que **a
  WebhookTool envia**, não o que recebe.
- `with patch("httpx.post", return_value=fake) as mock_post:` —
  durante o bloco `with`, **toda chamada** a `httpx.post` no projeto
  é desviada para o mock, que devolve `fake` sem fazer requisição
  real.

**Bloco 4 — Ação (linhas 29–30)**

- `tool = WebhookTool(url="https://x.example/webhook")` — instancia a
  tool. Note que a URL é qualquer string — não vai ser realmente
  acessada.
- `tool.execute("meu termo")` — dentro de `execute`, internamente é
  chamado `httpx.post(self._url, json={"query": query}, ...)`. Por
  causa do patch, essa chamada vira `mock_post(self._url, json={"query": "meu termo"}, ...)`.

**Bloco 5 — Asserção (linhas 31–32)**

- `mock_post.call_args.kwargs` — o `unittest.mock` registra
  automaticamente todos os argumentos passados ao mock. `call_args`
  é a última chamada; `.kwargs` é o dicionário de argumentos
  nomeados.
- `assert kwargs["json"] == {"query": "meu termo"}` — confirma que
  o payload JSON enviado tem a forma esperada (`{"query": "..."}`).
  Se a WebhookTool decidisse enviar `{"q": "..."}` ou
  `{"search": "..."}`, este teste quebraria — o que é exatamente o
  ponto: garantir o **contrato** que a tool tem com o webhook do
  cliente.

### Por que usa mock (e não chamada real)

- Chamar `httpx.post` de verdade exigiria um servidor HTTP rodando,
  rede disponível, lidar com timeout, falhas de DNS, etc.
- Os testes precisam ser **rápidos** e **determinísticos**. Mocks
  garantem isso.
- O comportamento real do `httpx` já é testado pela biblioteca
  `httpx`. Não é nosso trabalho retestá-lo.

### Quando o mock seria a escolha errada

Se o objetivo fosse validar que a WebhookTool de fato **funciona em
rede real**, isso seria um teste de integração de outro nível (e
provavelmente exigiria um servidor HTTP de teste local). Aqui o
escopo é deliberadamente isolado: testamos só a WebhookTool, sob
controle.

### O que aprenderíamos se este teste quebrasse

Que a WebhookTool mudou a forma do payload. Como o cliente do
sistema configura seu webhook esperando receber `{"query": "..."}`,
qualquer mudança aqui quebra integrações externas em produção.
Por isso este teste é fixo — protege contrato público.

---

## Apêndice — comandos úteis para a apresentação

```bash
# Rodar apenas os 3 exemplos selecionados
venv/bin/python -m pytest \
  tests/part1/test_security.py::TestHashApiKey::test_hash_is_deterministic \
  tests/part1/test_persistence_drivers.py::TestContextHistory::test_save_v2_keeps_v1_in_history \
  tests/part1/test_webhook_tool.py::TestWebhookToolExecute::test_post_called_with_query_payload \
  -v

# Rodar todos os 133 testes da Parte 1 com cobertura
venv/bin/python -m pytest tests/part1/ --cov=src --cov-report=term

# Gerar relatório HTML de cobertura para captura de tela
venv/bin/python -m pytest tests/part1/ --cov=src --cov-report=html
# (abre o arquivo htmlcov/index.html no navegador)
```

## Apêndice — checklist final para o `.docx`

- [ ] Capa com identificação UNIALFA
- [ ] Sumário automático
- [ ] Seções 1 a 9 redigidas a partir do `OUTLINE.md`
- [ ] Os três exemplos acima inseridos com formatação de código
- [ ] Captura de tela do `pytest -v` (rodar e printar)
- [ ] Captura de tela do relatório HTML de cobertura
- [ ] Apêndice com o `pytest.ini` (para mostrar markers)
- [ ] Apêndice com fragmento do log gerado em `logs/test_run_*.log`
- [ ] Texto argumentativo final (a redigir — peça se quiser rascunho)
- [ ] Referências (pytest docs, unittest.mock docs, fakeredis)
