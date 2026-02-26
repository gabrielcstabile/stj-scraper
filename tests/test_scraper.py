"""Testes para o STJScraper — usa mock do STJClient."""

from unittest.mock import MagicMock

from stj_scraper.client import STJClient
from stj_scraper.models import Processo
from stj_scraper.scraper import STJScraper

_HTML_VALIDO = """
<html><body>
  <span id="idSpanClasseDescricao">Recurso Especial</span>
  <span id="idProcessoDetalheAssuntos">Direito Civil</span>
  <div id="idDetalhesPartesAdvogadosProcuradores">
    <div class="classDivLinhaDetalhes">
      <span class="classSpanDetalhesLabel">Requerente:</span>
      <span class="classSpanDetalhesTexto">João Silva</span>
    </div>
    <div class="classDivLinhaDetalhes">
      <span class="classSpanDetalhesLabel">Requerido:</span>
      <span class="classSpanDetalhesTexto">Maria Souza</span>
    </div>
  </div>
  <div id="idDivFases">
    <div class="classDivFaseLinha">
      <span class="classSpanFaseData">15/01/2024</span>
      <span class="classSpanFaseTexto">Distribuído
        <span class="clsFaseCodigoConselhoNacionalJustica">(1)</span>
      </span>
    </div>
    <div class="classDivFaseLinha">
      <span class="classSpanFaseData">10/03/2024</span>
      <span class="classSpanFaseTexto">Julgado
        <span class="clsFaseCodigoConselhoNacionalJustica">(2)</span>
      </span>
    </div>
  </div>
</body></html>
"""

_HTML_VAZIO = "<html><body></body></html>"

_HTML_SEM_CLASSE = """
<html><body>
  <span id="idProcessoDetalheAssuntos">Direito Penal</span>
</body></html>
"""


def _mock_response(html: str) -> MagicMock:
    """Cria um mock de httpx.Response com HTML."""
    response = MagicMock()
    response.text = html
    return response


def test_parsing_correto(tmp_path, mocker) -> None:
    """Testa que buscar_processo retorna Processo corretamente parseado."""
    mocker.patch("stj_scraper.scraper._DATA_DIR", tmp_path)

    client = MagicMock(spec=STJClient)
    client.get.return_value = _mock_response(_HTML_VALIDO)

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
    """Testa comportamento quando o processo retorna HTML sem conteúdo relevante."""
    mocker.patch("stj_scraper.scraper._DATA_DIR", tmp_path)

    client = MagicMock(spec=STJClient)
    client.get.return_value = _mock_response(_HTML_VAZIO)

    scraper = STJScraper(client)
    processo = scraper.buscar_processo("99999")

    assert isinstance(processo, Processo)
    assert processo.numero == "99999"
    assert processo.classe == ""
    assert processo.assunto == ""
    assert processo.partes == []
    assert processo.movimentacoes == []


def test_campo_ausente_loga_warning(tmp_path, mocker) -> None:
    """Testa que campo ausente no HTML gera warning (sem lançar exceção)."""
    mocker.patch("stj_scraper.scraper._DATA_DIR", tmp_path)

    client = MagicMock(spec=STJClient)
    client.get.return_value = _mock_response(_HTML_SEM_CLASSE)

    mock_logger = mocker.patch("stj_scraper.scraper.logger")

    scraper = STJScraper(client)
    processo = scraper.buscar_processo("55555")

    assert processo.classe == ""
    mock_logger.warning.assert_called()
