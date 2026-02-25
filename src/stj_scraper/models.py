"""Modelos Pydantic para os dados processuais do STJ."""

from datetime import date

from pydantic import BaseModel


class Movimentacao(BaseModel):
    """Representa uma movimentação processual."""

    data: date
    descricao: str


class Parte(BaseModel):
    """Representa uma parte do processo."""

    nome: str
    tipo: str


class Processo(BaseModel):
    """Representa um processo judicial do STJ."""

    numero: str
    classe: str
    assunto: str
    partes: list[Parte]
    movimentacoes: list[Movimentacao]
