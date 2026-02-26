# STJ Scraper

Web scraper para coleta de dados processuais do Superior Tribunal de Justiça (STJ),
desenvolvido como desafio técnico para a vaga de **Data Acquisition Engineer Pleno — JusBrasil**.

---

## Descrição

O scraper acessa o portal público do STJ em `https://processo.stj.jus.br/` e coleta:

- Número do processo
- Classe processual (ex: Recurso Especial, Agravo Interno)
- Assunto
- Partes do processo (nome e tipo — ex: Requerente, Requerido)
- Lista completa de movimentações (data + descrição)

Os dados coletados são:
- Validados com **Pydantic v2** antes de qualquer persistência
- Salvos em **SQLite** via **SQLAlchemy 2** com upsert (evita duplicações)
- Exportados como **JSON** em `data/<numero>.json`
- Registrados em **log** estruturado (terminal + arquivo `logs/scraper.log`)

---

## Estrutura do Projeto

```
stj-scraper/
├── src/
│   └── stj_scraper/
│       ├── __init__.py
│       ├── client.py      # Sessão HTTP, headers de navegador, retry com backoff
│       ├── scraper.py     # Lógica de coleta, parsing e exportação JSON
│       ├── models.py      # Modelos Pydantic (Processo, Parte, Movimentacao)
│       ├── database.py    # SQLite + SQLAlchemy — tabelas e upsert
│       └── logger.py      # Configuração centralizada de logs
├── tests/
│   ├── test_models.py     # Validação dos modelos Pydantic
│   ├── test_database.py   # Upsert e deduplicação (banco em memória)
│   └── test_scraper.py    # Parsing com mock do cliente HTTP
├── data/                  # JSONs gerados em execução (gitignored)
├── logs/                  # scraper.log gerado em execução (gitignored)
├── pyproject.toml
├── Makefile
└── README.md
```

---

## Stack

| Componente     | Ferramenta                                                  |
|----------------|-------------------------------------------------------------|
| HTTP Client    | `httpx` — HTTP/2, sessão persistente, API moderna           |
| Validação      | `pydantic` v2 — validação automática de tipos e formatos    |
| Banco de dados | `sqlalchemy` 2 + `sqlite3` nativo                           |
| Logging        | `logging` nativo — dois handlers (terminal + arquivo)       |
| Testes         | `pytest` + `pytest-mock`                                    |
| Linting        | `ruff`                                                      |
| Dependências   | `uv` + `pyproject.toml`                                     |
| Ambiente       | `pyenv` + `.python-version`                                 |

---

## Pré-requisitos

- Python 3.11+
- [`uv`](https://docs.astral.sh/uv/) instalado

---

## Instalação

```bash
# Clonar o repositório
git clone <url-do-repo> stj-scraper
cd stj-scraper

# Criar ambiente virtual e instalar dependências
uv venv
uv sync --extra dev
```

---

## Uso

### Coletar um processo

```bash
make run PROCESSO=12345
```

Equivalente a:

```bash
uv run python -m stj_scraper.scraper --numero 12345
```

O comando:
1. Busca o processo no STJ via requisição HTTP direta ao endpoint XHR
2. Valida os dados com Pydantic
3. Salva no banco SQLite (`data/stj.db`) com upsert
4. Exporta JSON em `data/<numero>.json`

### Rodar os testes

```bash
make test
```

### Verificar qualidade de código

```bash
make lint      # ruff check
make format    # ruff format
```

### Limpar artefatos gerados

```bash
make clean
```

---

## Decisões Técnicas

### Por que httpx e não requests?

`httpx` tem API praticamente idêntica ao `requests`, suporta HTTP/2 nativamente e mantém
sessão persistente com cookies — essencial para não ser bloqueado pelo WAF do STJ.

### Por que não usar scraping de HTML (BeautifulSoup)?

O portal do STJ é uma **SPA (Single Page Application)**. O HTML inicial está vazio —
os dados só aparecem após o JavaScript executar chamadas XHR assíncronas. Capturar
esses dados via browser real (Playwright/Selenium) adicionaria complexidade desnecessária.
A solução adotada intercepta as chamadas XHR diretamente, replicando as requisições HTTP
que o browser faz, obtendo os dados em JSON de forma mais simples e robusta.

### Por que não usar Scrapy?

Scrapy é otimizado para crawling de HTML estático em escala. Para uma SPA com XHR,
precisaria de `scrapy-playwright`, adicionando complexidade desnecessária. `httpx` direto
demonstra maior domínio técnico dos fundamentos de HTTP.

### Retry com backoff exponencial

O cliente implementa até 3 tentativas com espera de 1s, 2s e 4s entre elas, cobrindo
instabilidades comuns do serviço (timeout, 503).

### Upsert no banco

A função `salvar_processo` verifica pelo número do processo: se já existe, atualiza
os dados e reinicia as coleções de partes e movimentações (evita duplicação); se não
existe, insere. Isso torna o scraper idempotente — pode ser executado múltiplas vezes
para o mesmo processo sem criar registros duplicados.

### Injeção de dependência no Scraper

`STJScraper` recebe `STJClient` no construtor em vez de instanciá-lo internamente.
Isso permite substituir o cliente por um mock nos testes sem precisar de monkeypatch
na classe inteira.

---

## Testes

13 testes cobrindo os três módulos principais:

| Arquivo              | Cenários cobertos                                            |
|----------------------|--------------------------------------------------------------|
| `test_models.py`     | Validação de dados válidos, datas inválidas, campos ausentes |
| `test_database.py`   | Inserção, upsert sem duplicação, atualização de dados        |
| `test_scraper.py`    | Parsing correto, payload vazio, campo ausente gera warning   |

O banco de dados nos testes usa sempre `sqlite:///:memory:` com `StaticPool` —
nunca toca o banco real em `data/stj.db`.

---

## Fluxo de Dados

```
STJ (servidor)
    → httpx (requisição HTTP com headers de navegador)
        → JSON bruto
            → Pydantic (valida e estrutura os dados)
                → objeto Processo
                    ├── SQLite via SQLAlchemy (upsert)
                    └── JSON em data/<numero>.json
```
