# yopa-api-test

> **Snapshot acadêmico do projeto AI-ChatBot. NÃO é o estado atual do sistema.**

## 1. Contexto

Este diretório contém uma cópia congelada do projeto **AI-ChatBot** (API
conversacional), usada como base para o trabalho da
disciplina **Ferramentas Automatizadas de Verificação de Software** da
**UNIALFA**.

O objetivo acadêmico é demonstrar a aplicação do framework **pytest** em
diferentes tipos de teste — unitário, integração, sistema, regressão,
mock, fallback e pipeline/interação — sobre um código real em
desenvolvimento.

- O código em `src/` aqui **NÃO reflete necessariamente o estado atual**
  do AI-ChatBot. É uma fotografia tirada na data de cópia 17/05/2026.
- Para o código em desenvolvimento, consultar o repositório principal:
  `ygorPaulo074/yopa-api` no GitHub.

## 2. Estado do projeto no momento da cópia

| Campo | Valor |
|---|---|
| Data da cópia | 2026-05-17 |
| Branch original | `development` |
| Último commit | `dc66b9f` — *remove PROJECT INSIGHTS* (2026-05-10) |
| Hash completo | `dc66b9fa22ec495a550699da605fd5789a40b2e7` |
| VERSION | `0.1.0` |
| Python | `3.14.4` |
| Working tree | limpo (sem alterações pendentes) |
| Testes originais | 125 testes em 26 classes (removidos nesta cópia) |

## 3. Diferenças em relação ao AI-ChatBot original

1. **Pasta `tests/` original foi removida** e será reescrita do zero para
   fins didáticos. As classes existentes serviram como referência (ver
   `OUTLINE.md` e o documento `trabalho-faculdade-pytest.txt` em
   `/home/pygor/projetos/`).
2. **`pytest-cov` adicionado** ao `requirements-base.txt` para gerar
   relatórios de cobertura.
3. **`pytest.ini` adicionado** com markers customizados (`unit`,
   `integration`, `system`, `regression`, `fallback`, `pipeline`,
   `part1`, `part2`).
4. **Diretórios `data/`, `venv/`, `.env`, `.git/` não foram copiados**.
   São gerados localmente no setup.

## 4. Divisão do trabalho

| Parte | Responsável | Camadas | Pasta |
|---|---|---|---|
| Parte 1 | Paulo Ygor | `application/` + `infrastructure/` | `tests/part1/` |
| Parte 2 | Aysha | `interfaces/http/` | `tests/part2/` |

Detalhes em `OUTLINE.md` e em `trabalho-faculdade-pytest.txt`.

## 5. Setup local

Opção A — venv própria (recomendado quando publicado):

```bash
cd /home/pygor/projetos/yopa-api-test
python3.14 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Opção B — reaproveitar venv do AI-ChatBot (caso esteja na mesma máquina
de desenvolvimento, evita re-download de litellm/spacy/presidio):

```bash
cd /home/pygor/projetos/yopa-api-test
ln -s /home/pygor/projetos/AI-ChatBot/venv venv
venv/bin/pip install pytest-cov   # único pacote extra
```

## 6. Executando os testes

```bash
# Tudo
pytest

# Apenas Parte 1 (application + infrastructure)
pytest tests/part1/

# Apenas Parte 2 (interfaces/http)
pytest tests/part2/

# Por tipo de teste (markers)
pytest -m unit
pytest -m integration
pytest -m system
pytest -m regression
pytest -m fallback
pytest -m pipeline

# Por palavra-chave
pytest -k "hmac"
pytest -k "pipeline"

# Cobertura HTML (relatório em htmlcov/index.html)
pytest --cov=src --cov-report=html

# Cobertura no terminal
pytest --cov=src --cov-report=term-missing
```

## 7. Estrutura de testes

```
tests/
├── conftest.py         fixtures compartilhadas (client, agent, mock_ai, fakeredis)
├── shared/
│   └── factories.py    helpers para construir payloads
├── part1/              testes da Parte 1 (autor)
│   ├── test_security.py
│   ├── test_context_builder.py
│   ├── test_chat_service.py
│   ├── test_escalation_service.py
│   ├── test_cache_client.py
│   ├── test_persistence_drivers.py
│   ├── test_sql_tool.py
│   ├── test_webhook_tool.py
│   └── test_file_extractor.py
└── part2/              testes da Parte 2 (assistente — ainda vazio)
```

## 8. Logs de execução

Cada rodada de `pytest` gera um arquivo em `logs/` no formato
`test_run_YYYYMMDD_HHMMSS.log`. O arquivo contém:

- Marcações `SESSION` no início e fim da rodada
- Para cada teste: `START`, `PASS`/`FAIL`/`SKIP`, duração em ms
- Mensagens manuais via `log_event(level, message)` (importável de
  `tests.shared.log_helper`)

Duas formas de gerar log:

1. **Decorator `@logged`** — aplicado em cada função de teste dos
   esqueletos da Parte 1. Registra entrada, saída, duração e exceção.
2. **Hooks pytest** — definidos em `tests/conftest.py`
   (`pytest_sessionstart`, `pytest_sessionfinish`, `pytest_runtest_logreport`).
   Garantem log mesmo para testes sem decorator.

## 9. Licença

Código do AI-ChatBot: ver licença no repositório original. Esta cópia é
para uso acadêmico, sem fins comerciais.
