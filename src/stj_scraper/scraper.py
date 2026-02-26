"""Lógica de coleta e parsing de processos do STJ."""

import argparse
from datetime import datetime
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup

from stj_scraper.client import STJClient
from stj_scraper.database import salvar_processo
from stj_scraper.logger import get_logger
from stj_scraper.models import Movimentacao, Parte, Processo

logger = get_logger(__name__)

_BASE_URL = "https://processo.stj.jus.br/processo/pesquisa/"
_PARAMS_FIXOS: dict[str, str] = {
    "tipoPesquisa": "tipoPesquisaNumeroRegistro",
    "totalRegistrosPorPagina": "40",
    "aplicacao": "processos.ea",
}

_DATA_DIR = Path("data")


class STJScraper:
    """Scraper de processos do STJ."""

    def __init__(self, client: STJClient) -> None:
        """Inicializa o scraper com um cliente HTTP injetado."""
        self._client = client

    def buscar_processo(self, numero: str) -> Processo:
        """Coleta e retorna os dados completos de um processo pelo número.

        Faz GET na URL de pesquisa com os params fixos mais o número do
        processo, salva o HTML bruto em cache e retorna um objeto Processo
        populado com os dados extraídos.
        """
        logger.info("Iniciando coleta do processo %s", numero)

        params: dict[str, str] = {**_PARAMS_FIXOS, "termo": numero}
        response = self._client.get(_BASE_URL, params=params)
        html: str = response.text

        _DATA_DIR.mkdir(parents=True, exist_ok=True)
        (_DATA_DIR / f"{numero}.html").write_text(html, encoding="utf-8")

        dados = self._parse_html(html)

        partes = [Parte(**p) for p in dados["partes"]]
        movimentacoes = [Movimentacao(**m) for m in dados["movimentacoes"]]

        processo = Processo(
            numero=numero,
            classe=dados["classe"],
            assunto=dados["assunto"],
            partes=partes,
            movimentacoes=movimentacoes,
        )

        logger.info(
            "Processo %s coletado — %d parte(s), %d movimentação(ões).",
            numero,
            len(partes),
            len(movimentacoes),
        )

        return processo

    # ------------------------------------------------------------------
    # Métodos privados de parsing
    # ------------------------------------------------------------------

    def _parse_html(self, html: str) -> dict[str, Any]:
        """Extrai dados processuais do HTML retornado pelo STJ.

        Retorna dict com chaves: classe, assunto, partes, movimentacoes.
        Campos não encontrados retornam string vazia ou lista vazia.
        """
        soup = BeautifulSoup(html, "lxml")

        if not soup.find(id=True):
            logger.warning(
                "HTML sem conteúdo estruturado — processo possivelmente não encontrado."
            )

        classe = self._extrair_texto(soup, "idSpanClasseDescricao", "classe")
        assunto = self._extrair_texto(soup, "idProcessoDetalheAssuntos", "assunto")
        partes = self._extrair_partes(soup)
        movimentacoes = self._extrair_movimentacoes(soup)

        return {
            "classe": classe,
            "assunto": assunto,
            "partes": partes,
            "movimentacoes": movimentacoes,
        }

    def _extrair_texto(self, soup: BeautifulSoup, element_id: str, campo: str) -> str:
        """Extrai o texto de um elemento pelo id.

        Loga warning e retorna string vazia se o elemento não for encontrado.
        """
        tag = soup.find(id=element_id)
        if tag is None:
            logger.warning(
                "Campo '%s' não encontrado no HTML (id='%s').", campo, element_id
            )
            return ""
        return tag.get_text(strip=True)

    def _extrair_partes(self, soup: BeautifulSoup) -> list[dict[str, str]]:
        """Extrai a lista de partes do bloco de detalhes do processo.

        Cada entrada é um div.classDivLinhaDetalhes com:
          - span.classSpanDetalhesLabel → tipo (ex: "IMPETRANTE:")
          - span.classSpanDetalhesTexto → nome

        Loga warning e retorna lista vazia se o bloco não for encontrado.
        """
        container = soup.find(id="idDetalhesPartesAdvogadosProcuradores")
        if container is None:
            logger.warning(
                "Bloco de partes não encontrado no HTML "
                "(id='idDetalhesPartesAdvogadosProcuradores')."
            )
            return []

        partes: list[dict[str, str]] = []
        for div in container.find_all("div", class_="classDivLinhaDetalhes"):
            label = div.find("span", class_="classSpanDetalhesLabel")
            texto = div.find("span", class_="classSpanDetalhesTexto")
            if label and texto:
                partes.append(
                    {
                        "tipo": label.get_text(strip=True).rstrip(":"),
                        "nome": texto.get_text(strip=True),
                    }
                )
        return partes

    def _extrair_movimentacoes(self, soup: BeautifulSoup) -> list[dict[str, str]]:
        """Extrai a lista de movimentações do bloco de fases do processo.

        Cada entrada é um div.classDivFaseLinha com:
          - span.classSpanFaseData    → data no formato DD/MM/YYYY
          - span.classSpanFaseTexto   → descrição (ignora o span do código CNJ interno)

        Loga warning e retorna lista vazia se o bloco não for encontrado.
        Entradas com data em formato inesperado são ignoradas com warning.
        """
        container = soup.find(id="idDivFases")
        if container is None:
            logger.warning(
                "Bloco de fases não encontrado no HTML (id='idDivFases')."
            )
            return []

        movimentacoes: list[dict[str, str]] = []
        for div in container.find_all("div", class_="classDivFaseLinha"):
            data_span = div.find("span", class_="classSpanFaseData")
            texto_span = div.find("span", class_="classSpanFaseTexto")
            if not data_span or not texto_span:
                continue

            data_str = data_span.get_text(strip=True)
            try:
                data_iso = datetime.strptime(data_str, "%d/%m/%Y").date().isoformat()
            except ValueError:
                logger.warning(
                    "Data com formato inesperado: %r — entrada ignorada.", data_str
                )
                continue

            # Remove o span do código CNJ antes de extrair o texto da descrição
            cnj = texto_span.find("span", class_="clsFaseCodigoConselhoNacionalJustica")
            if cnj:
                cnj.decompose()
            descricao = texto_span.get_text(strip=True)

            movimentacoes.append({"data": data_iso, "descricao": descricao})

        return movimentacoes


# ---------------------------------------------------------------------------
# Ponto de entrada CLI
# ---------------------------------------------------------------------------


def _parse_args() -> argparse.Namespace:
    """Parseia argumentos da linha de comando."""
    parser = argparse.ArgumentParser(description="Coleta processo do STJ")
    parser.add_argument(
        "--numero", required=True, help="Número do processo (ex: 202501505469)"
    )
    return parser.parse_args()


def main() -> None:
    """Ponto de entrada principal do scraper."""
    args = _parse_args()

    with STJClient() as client:
        scraper = STJScraper(client)
        processo = scraper.buscar_processo(args.numero)
        salvar_processo(processo)


if __name__ == "__main__":
    main()
