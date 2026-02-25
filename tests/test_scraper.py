"""Testes para o STJScraper — usa mock do STJClient."""

from unittest.mock import MagicMock

from stj_scraper.client import STJClient
from stj_scraper.models import Processo
from stj_scraper.scraper import STJScraper


def _mock_response(payload: dict) -> MagicMock:
    """Cria um mock de httpx.Response com payload JSON."""
    response = MagicMock()
    response.json.return_value = payload
    return response


_PAYLOAD_VALIDO = {
    "classe": "Recurso Especial",
    "assunto": "Direito Civil",
    "partes": [
        {"nome": "João Silva", "tipo": "Requerente"},
        {"nome": "Maria Souza", "tipo": "Requerido"},
    ],
    "movimentacoes": [
        {"data": "2024-01-15", "descricao": "Distribuído"},
        {"data": "2024-03-10", "descricao": "Julgado"},
    ],
}


def test_parsing_correto(tmp_path, mocker) -> None:
    """Testa que buscar_processo retorna Processo corretamente parseado."""
    mocker.patch("stj_scraper.scraper._DATA_DIR", tmp_path)

    client = MagicMock(spec=STJClient)
    client.get.return_value = _mock_response(_PAYLOAD_VALIDO)

    scraper = STJScraper(client)
    processo = scraper.buscar_processo("12345")

    assert isinstance(processo, Processo)
    assert processo.numero == "12345"
    assert processo.classe == "Recurso Especial"
    assert len(processo.partes) == 2
    assert len(processo.movimentacoes) == 2
    assert processo.partes[0].nome == "João Silva"
    assert processo.movimentacoes[1].descricao == "Julgado"


def test_processo_nao_encontrado(tmp_path, mocker) -> None:
    """Testa comportamento quando o processo retorna payload vazio."""
    mocker.patch("stj_scraper.scraper._DATA_DIR", tmp_path)

    client = MagicMock(spec=STJClient)
    client.get.return_value = _mock_response({})

    scraper = STJScraper(client)
    processo = scraper.buscar_processo("99999")

    assert isinstance(processo, Processo)
    assert processo.numero == "99999"
    assert processo.classe == ""
    assert processo.assunto == ""
    assert processo.partes == []
    assert processo.movimentacoes == []


def test_campo_ausente_loga_warning(tmp_path, mocker) -> None:
    """Testa que campo ausente no payload gera warning (sem lançar exceção)."""
    mocker.patch("stj_scraper.scraper._DATA_DIR", tmp_path)

    payload_sem_classe = {
        "assunto": "Direito Penal",
        "partes": [],
        "movimentacoes": [],
    }

    client = MagicMock(spec=STJClient)
    client.get.return_value = _mock_response(payload_sem_classe)

    mock_logger = mocker.patch("stj_scraper.scraper.logger")

    scraper = STJScraper(client)
    processo = scraper.buscar_processo("55555")

    assert processo.classe == ""
    mock_logger.warning.assert_called()
