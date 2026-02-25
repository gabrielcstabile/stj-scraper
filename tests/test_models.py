"""Testes para os modelos Pydantic."""

import pytest
from pydantic import ValidationError

from stj_scraper.models import Movimentacao, Parte, Processo


def test_movimentacao_valida() -> None:
    """Aceita data e descrição válidos."""
    mov = Movimentacao(data="2024-01-15", descricao="Petição juntada")
    assert mov.data.year == 2024
    assert mov.descricao == "Petição juntada"


def test_movimentacao_data_invalida() -> None:
    """Rejeita data em formato inválido."""
    with pytest.raises(ValidationError):
        Movimentacao(data="15/01/2024", descricao="Petição juntada")


def test_movimentacao_campo_ausente() -> None:
    """Lança ValidationError quando campo obrigatório está ausente."""
    with pytest.raises(ValidationError):
        Movimentacao(descricao="Sem data")  # type: ignore[call-arg]


def test_parte_valida() -> None:
    """Aceita nome e tipo válidos."""
    parte = Parte(nome="João Silva", tipo="Requerente")
    assert parte.nome == "João Silva"
    assert parte.tipo == "Requerente"


def test_parte_campo_ausente() -> None:
    """Lança ValidationError quando campo obrigatório está ausente."""
    with pytest.raises(ValidationError):
        Parte(nome="João Silva")  # type: ignore[call-arg]


def test_processo_valido() -> None:
    """Aceita processo com todos os campos válidos."""
    processo = Processo(
        numero="12345",
        classe="Recurso Especial",
        assunto="Direito Civil",
        partes=[Parte(nome="João", tipo="Requerente")],
        movimentacoes=[Movimentacao(data="2024-01-01", descricao="Distribuído")],
    )
    assert processo.numero == "12345"
    assert len(processo.partes) == 1
    assert len(processo.movimentacoes) == 1


def test_processo_campo_ausente() -> None:
    """Lança ValidationError quando campo obrigatório está ausente."""
    with pytest.raises(ValidationError):
        Processo(  # type: ignore[call-arg]
            numero="12345",
            classe="Recurso Especial",
            # assunto ausente
            partes=[],
            movimentacoes=[],
        )
