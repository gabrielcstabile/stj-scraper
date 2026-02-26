# STJ Scraper

Web scraper para coleta de dados processuais do Superior Tribunal de Justiça (STJ).

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
- Armazenados em cache como **HTML bruto** em `data/<numero>.html`
- Registrados em **log** estruturado (terminal + arquivo `logs/scraper.log`)

---

## Estrutura do Projeto

```
stj-scraper/
├── src/
│   └── stj_scraper/
│       ├── __init__.py
│       ├── client.py      # Sessão HTTP, headers de navegador, retry com backoff
│       ├── scraper.py     # Lógica de coleta, parsing HTML e persistência
│       ├── models.py      # Modelos Pydantic (Processo, Parte, Movimentacao)
│       ├── database.py    # SQLite + SQLAlchemy — tabelas e upsert
│       └── logger.py      # Configuração centralizada de logs
├── tests/
│   ├── test_models.py     # Validação dos modelos Pydantic
│   ├── test_database.py   # Upsert e deduplicação (banco em memória)
│   └── test_scraper.py    # Parsing com mock do cliente HTTP
├── data/                  # HTMLs e banco gerados em execução (gitignored)
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
| HTML Parsing   | `beautifulsoup4` + `lxml`                                   |
| Validação      | `pydantic` v2 — validação automática de tipos e formatos    |
| Banco de dados | `sqlalchemy` 2 + `sqlite3` nativo                           |
| Logging        | `logging` nativo — dois handlers (terminal + arquivo)       |
| Testes         | `pytest` + `pytest-mock`                                    |
| Linting        | `ruff`                                                      |
| Dependências   | `uv` + `pyproject.toml`                                     |

---

## Pré-requisitos

- Python 3.11+
- [`uv`](https://docs.astral.sh/uv/) instalado

---

## Instalação

```bash
git clone <url-do-repo> stj-scraper
cd stj-scraper

uv sync --extra dev
```

---

## Uso

### Coletar um processo

```bash
make run PROCESSO=<numero_do_processo>
```

Equivalente a:

```bash
uv run python -m stj_scraper.scraper --numero <numero_do_processo>
```

O comando:
1. Busca o processo no STJ via requisição HTTP GET
2. Salva o HTML bruto em `data/<numero>.html` (cache/debug)
3. Extrai os dados com BeautifulSoup e valida com Pydantic
4. Salva no banco SQLite (`data/stj.db`) com upsert

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

### httpx — cliente HTTP

`httpx` mantém sessão persistente com cookies entre requisições, suporta HTTP/2
nativamente e implementa backoff exponencial (1 s → 2 s → 4 s) com até 3 tentativas,
cobrindo timeouts e instabilidades do serviço sem intervenção manual.

### BeautifulSoup + lxml — parsing HTML

O STJ retorna o HTML completo do processo em uma única requisição GET — o conteúdo
não depende de JavaScript para renderizar. O parser `lxml` é o mais rápido disponível
no BeautifulSoup para documentos grandes, e a extração por `id` de elemento torna o
código robusto a mudanças de layout periféricas.

### Pydantic v2 — validação

Todos os dados extraídos passam por validação automática de tipos e formatos (incluindo
`date`) antes de qualquer gravação em banco ou arquivo. Erros de estrutura são detectados
cedo, na camada de domínio.

### SQLAlchemy 2 + upsert — persistência

A função `salvar_processo` verifica o número do processo antes de gravar: se já existe,
atualiza os dados e reinicia as coleções de partes e movimentações; se não existe,
insere. O scraper é idempotente — pode ser executado múltiplas vezes para o mesmo
processo sem criar registros duplicados.

### Injeção de dependência no STJScraper

`STJScraper` recebe `STJClient` no construtor em vez de instanciá-lo internamente.
Nos testes, o cliente é substituído por um `MagicMock` sem necessidade de monkeypatch
na classe inteira, mantendo os testes isolados e rápidos.

---

## Testes

13 testes cobrindo os três módulos principais:

| Arquivo              | Cenários cobertos                                            |
|----------------------|--------------------------------------------------------------|
| `test_models.py`     | Validação de dados válidos, datas inválidas, campos ausentes |
| `test_database.py`   | Inserção, upsert sem duplicação, atualização de dados        |
| `test_scraper.py`    | Parsing correto, HTML vazio, campo ausente gera warning      |

O banco de dados nos testes usa `sqlite:///:memory:` com `StaticPool` —
nunca toca o banco real em `data/stj.db`.

---

## Fluxo de Dados

```
STJ (servidor)
    → httpx (requisição HTTP com headers de navegador)
        → HTML bruto  →  data/<numero>.html (cache/debug)
            → BeautifulSoup + lxml (parse e extração)
                → Pydantic (valida e estrutura os dados)
                    → objeto Processo
                        └── SQLite via SQLAlchemy (upsert)
```


