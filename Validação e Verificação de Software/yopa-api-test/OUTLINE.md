# OUTLINE da documentação .docx

Use este sumário para escrever o documento Word do trabalho. Cada item
abaixo vira uma seção no .docx. As tabelas estão prontas para copiar.

---

## Capa

- Título: **Ferramentas Automatizadas de Verificação de Software — pytest**
- Disciplina, professor(a), nome do aluno, turma, data
- Logotipo UNIALFA

## 1. Introdução

- Contexto da disciplina
- Linguagem escolhida: Python (justificativa: stack do projeto cobaia)
- Projeto cobaia: AI-ChatBot (API conversacional do produto Yopa)
- Estado do projeto: VERSION 0.1.0, branch `development`, commit `dc66b9f`
- Natureza do produto: **NÃO é Web nem Desktop**, é uma ferramenta
  abstraída de chatbot consumida via HTTP REST

## 2. Levantamento de ferramentas de teste em Python

Tabela com as principais (referência ampla, antes de afunilar):

| Ferramenta | Finalidade | Tipo de aplicação | Nível |
|---|---|---|---|
| pytest | Framework principal | Web/API/Desktop/CLI | Iniciante a avançado |
| unittest (stdlib) | Framework nativo | Mesmo escopo | Iniciante |
| unittest.mock | Mock/spy/patch | Qualquer | Iniciante |
| fakeredis | Redis em memória | Apps com Redis | Intermediário |
| Starlette TestClient / httpx | Cliente HTTP em memória | Web/API | Intermediário |
| Hypothesis | Property-based testing | Qualquer | Avançado |
| Schemathesis | Fuzz baseado em OpenAPI | API REST | Avançado |
| pytest-cov | Cobertura | Qualquer | Iniciante |
| Locust | Carga | Web/API | Intermediário |
| Selenium / Playwright | UI no navegador | Web | Intermediário+ |
| Robot Framework | Keyword-driven | Web/API/Desktop | Intermediário |
| Behave | BDD (Gherkin) | Web/API | Intermediário |

## 3. Tipos de teste suportados (matriz)

| Ferramenta | Unit | Integração | Sistema | Regressão | Mock |
|---|:-:|:-:|:-:|:-:|:-:|
| pytest | SIM | SIM | SIM | SIM | via plugins |
| unittest.mock | — | — | — | — | SIM |
| fakeredis | — | SIM | SIM | SIM | SIM |
| Starlette TestClient | — | SIM | SIM | SIM | — |
| Schemathesis | — | SIM | SIM | SIM | — |
| Hypothesis | SIM | SIM | — | SIM | — |
| Locust | — | — | SIM (carga) | SIM | — |

## 4. Ferramenta escolhida: pytest

### 4.1. Visão geral

- O que é: framework principal de testes Python
- Para que: descoberta automática, execução, fixtures, parametrização
- Como funciona (conceito): `def test_*()`, `assert`, fixtures componíveis

### 4.2. Benefícios

- Sintaxe mínima — sem `class TestX(unittest.TestCase)` obrigatório
- Fixtures componíveis (versus `setUp`/`tearDown` rígidos)
- Plugins (cov, mock, xdist, asyncio, qt, schemathesis...)
- Padrão de mercado
- Reaproveita tudo do unittest (é superset)

### 4.3. Pontos fracos

- Curva de aprendizado das fixtures avançadas
- Plugins exigem leitura cuidadosa de docs
- Assert rewriting pode confundir debug em casos extremos
- Descoberta automática pode pegar arquivos não intencionais

### 4.4. Aplicação do pytest em diferentes tipos de software

| Cenário | Como pytest se aplica | Exemplo |
|---|---|---|
| Aplicação Web (frontend) | pytest + Selenium/Playwright para automação de UI | Carrinho de e-commerce |
| Aplicação Desktop | pytest + pytest-qt (PyQt) ou subprocess (CLI) | App em PyQt, script CLI |
| API / serviço backend (NOSSO CASO) | pytest nativo via TestClient cobre 100% | AI-ChatBot (este trabalho) |

### 4.5. Integração com pipeline (CI/CD)

- O que é CI/CD: pipeline automatizado que roda lint → testes → build → deploy a cada commit
- Bloqueia merge se testes falham; bloqueia deploy se build quebra
- Exemplo em GitHub Actions:

```yaml
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.14"
      - run: pip install -r requirements.txt
      - run: pytest --cov=src --cov-report=xml
```

## 5. Aplicação no projeto cobaia (AI-ChatBot)

### 5.1. Arquitetura DDD em camadas

```
src/
  domain/        entidades puras (sem dependências)
  application/   serviços e regras de negócio
  infrastructure/ adapters (Redis, DB, IA, NLP, ingestão, tools)
  interfaces/    fronteira HTTP (FastAPI routes, schemas, auth)
```

### 5.2. Divisão do trabalho em 2 partes

| Parte | Camadas | Responsável | Pasta |
|---|---|---|---|
| Parte 1 | application + infrastructure | Autor | `tests/part1/` |
| Parte 2 | interfaces/http | Assistente | `tests/part2/` |

### 5.3. Tipos de teste implementados

- **unit** — funções/métodos isolados
- **integration** — múltiplas unidades reais juntas
- **system** — fluxos completos pela fronteira HTTP
- **regression** — bugs conhecidos já corrigidos
- **fallback** — caminhos alternativos quando o primário falha
- **pipeline** — ordem e composição das chamadas internas (interaction testing)

### 5.4. Exemplos práticos (OBRIGATÓRIO no trabalho)

Três exemplos com explicação linha a linha:

1. **Unitário** — `tests/part1/test_security.py` (`hash_api_key`)
2. **Integração** — `tests/part2/...` (POST /chat ponta a ponta)
3. **Mock** — `tests/conftest.py` (fixture `mock_ai`)

Para cada um, explicar:
- Setup das fixtures
- Ação (Arrange-Act-Assert)
- Asserts
- Por que é desse tipo (e não outro)

## 6. Comandos de execução

```bash
pytest                                # roda tudo
pytest tests/part1/                   # só Parte 1
pytest -m unit                        # só unitários
pytest -m fallback                    # só fallback
pytest -m pipeline                    # só pipeline
pytest --cov=src --cov-report=html    # cobertura HTML
pytest -k "hmac"                      # filtra por keyword
```

## 7. Pontos fracos do pytest (texto crítico)

- Quando NÃO usar pytest puro:
  - Testes de UI no navegador (precisa Selenium/Playwright junto)
  - Testes de carga distribuída (Locust é mais adequado)
  - BDD com stakeholders não-técnicos (Behave/Cucumber falam Gherkin)

## 8. Texto argumentativo — conclusão

Argumentos para a empresa adotar pytest:

- **Custo zero** — open source, sem licença
- **Curva de adoção baixa** — sintaxe mínima
- **Padrão de mercado** — fácil contratar quem já conhece
- **Reduz custo de regressão** — bug pego em CI custa N× menos que em produção
- **Confiança em refactor** — sem testes, qualquer mudança é arriscada
- **Documentação executável** — os testes mostram o comportamento esperado

Retorno (tempo, qualidade, custo):
- Tempo: testes manuais demoram horas; pytest roda em segundos
- Qualidade: cobertura mensurável; defeitos detectados antes da produção
- Custo: nenhum custo de licença; redução de horas de QA manual

## 9. Anexo — Estado do projeto na data do trabalho

- Repositório: `ygorPaulo074/AI-ChatBot`
- Branch: `development`
- Commit: `dc66b9fa22ec495a550699da605fd5789a40b2e7` ("remove PROJECT INSIGHTS")
- VERSION: `0.1.0`
- Python: `3.14.4`
- Testes pré-existentes: 125 em 26 classes (removidos para reescrita didática)

---

## Observações finais para a escrita do .docx

- Manter linguagem técnica mas acessível — definir siglas pouco óbvias entre parênteses
- Incluir capturas de tela: output do `pytest -v`, relatório de cobertura HTML
- Imprimir os 3 exemplos obrigatórios com syntax highlighting
- Anexar o `pytest.ini` do projeto para mostrar markers customizados
