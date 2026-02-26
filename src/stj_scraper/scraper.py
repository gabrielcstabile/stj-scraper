"""Lógica de coleta e parsing de processos do STJ."""

import argparse
from pathlib import Path
from typing import Any

from stj_scraper.client import STJClient
from stj_scraper.database import salvar_processo
from stj_scraper.logger import get_logger
from stj_scraper.models import Movimentacao, Parte, Processo

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# PREENCHA ANTES DE RODAR — inspecionar DevTools do STJ
# ---------------------------------------------------------------------------
ENDPOINT_PESQUISA = "https://processo.stj.jus.br/processo/pesquisa/"
ENDPOINT_DETALHES = "https://processo.stj.jus.br/processo/deta/"
PARAM_NUMERO = "num_processo"
# ---------------------------------------------------------------------------

_DATA_DIR = Path("data")


class STJScraper:
    """Scraper de processos do STJ."""

    def __init__(self, client: STJClient) -> None:
        """Inicializa o scraper com um cliente HTTP injetado."""
        self._client = client

    def buscar_processo(self, numero: str) -> Processo:
        """Coleta e retorna os dados completos de um processo pelo número."""
        logger.info("Iniciando coleta do processo %s", numero)

        response = self._client.get(ENDPOINT_PESQUISA, params={PARAM_NUMERO: numero})
        payload = response.json()

        dados_basicos = self._extrair_dados_basicos(payload)
        partes = self._extrair_partes(payload)
        movimentacoes = self._extrair_movimentacoes(payload)

        processo = Processo(
            numero=numero,
            classe=dados_basicos["classe"],
            assunto=dados_basicos["assunto"],
            partes=partes,
            movimentacoes=movimentacoes,
        )

        logger.info(
            "Processo %s coletado com sucesso — %d parte(s), %d movimentação(ões).",
            numero,
            len(partes),
            len(movimentacoes),
        )

        self._exportar_json(processo)
        return processo

    # ------------------------------------------------------------------
    # Métodos privados de parsing
    # ------------------------------------------------------------------

    def _extrair_dados_basicos(self, payload: dict[str, Any]) -> dict[str, str]:
        """Extrai classe e assunto do payload da resposta."""
        classe = payload.get("classe")
        assunto = payload.get("assunto")

        if classe is None:
            logger.warning("Campo 'classe' ausente na resposta.")
            classe = ""
        if assunto is None:
            logger.warning("Campo 'assunto' ausente na resposta.")
            assunto = ""

        return {"classe": classe, "assunto": assunto}

    def _extrair_partes(self, payload: dict[str, Any]) -> list[Parte]:
        """Extrai a lista de partes do payload da resposta."""
        partes_raw = payload.get("partes", [])
        partes: list[Parte] = []

        for item in partes_raw:
            try:
                partes.append(Parte(nome=item["nome"], tipo=item["tipo"]))
            except (KeyError, Exception) as exc:
                logger.error("Erro ao parsear parte %s: %s", item, exc)

        return partes

    def _extrair_movimentacoes(self, payload: dict[str, Any]) -> list[Movimentacao]:
        """Extrai a lista de movimentações do payload da resposta."""
        movs_raw = payload.get("movimentacoes", [])
        movimentacoes: list[Movimentacao] = []

        for item in movs_raw:
            try:
                movimentacoes.append(
                    Movimentacao(data=item["data"], descricao=item["descricao"])
                )
            except (KeyError, Exception) as exc:
                logger.error("Erro ao parsear movimentação %s: %s", item, exc)

        return movimentacoes

    def _exportar_json(self, processo: Processo) -> None:
        """Exporta o processo como JSON em data/<numero>.json."""
        _DATA_DIR.mkdir(parents=True, exist_ok=True)
        safe_name = processo.numero.replace("/", "-")
        output_path = _DATA_DIR / f"{safe_name}.json"
        output_path.write_text(
            processo.model_dump_json(indent=2), encoding="utf-8"
        )
        logger.info("JSON exportado em %s", output_path)


# ---------------------------------------------------------------------------
# Ponto de entrada CLI
# ---------------------------------------------------------------------------

def _parse_args() -> argparse.Namespace:
    """Parseia argumentos da linha de comando."""
    parser = argparse.ArgumentParser(description="Coleta processo do STJ")
    parser.add_argument(
        "--numero", required=True, help="Número do processo (ex: 12345)"
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
