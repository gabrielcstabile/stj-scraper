"""Testes para a camada de persistência — sempre usa banco em memória."""

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from stj_scraper.database import Base, ProcessoORM, salvar_processo
from stj_scraper.models import Movimentacao, Parte, Processo


def _make_engine():
    """Cria engine SQLite em memória com pool estático (conexão única compartilhada)."""
    return create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )


def _make_processo(numero: str = "00001") -> Processo:
    """Cria um processo de teste com dados mínimos."""
    return Processo(
        numero=numero,
        classe="Recurso Especial",
        assunto="Direito Civil",
        partes=[Parte(nome="João Silva", tipo="Requerente")],
        movimentacoes=[Movimentacao(data="2024-03-10", descricao="Distribuído")],
    )


def test_insercao_novo_processo() -> None:
    """Insere um processo novo e verifica que foi persistido corretamente."""
    engine = _make_engine()
    Base.metadata.create_all(engine)

    processo = _make_processo("00001")
    salvar_processo(processo, engine=engine)

    with Session(engine) as session:
        orm = session.query(ProcessoORM).filter_by(numero="00001").first()
        assert orm is not None
        assert orm.classe == "Recurso Especial"
        assert len(orm.partes) == 1
        assert len(orm.movimentacoes) == 1


def test_upsert_nao_duplica() -> None:
    """Rodar salvar_processo duas vezes com mesmo número não duplica o registro."""
    engine = _make_engine()
    Base.metadata.create_all(engine)

    processo = _make_processo("00002")
    salvar_processo(processo, engine=engine)
    salvar_processo(processo, engine=engine)

    with Session(engine) as session:
        count = session.query(ProcessoORM).filter_by(numero="00002").count()
        assert count == 1


def test_upsert_atualiza_dados() -> None:
    """Upsert com dados diferentes atualiza o registro existente."""
    engine = _make_engine()
    Base.metadata.create_all(engine)

    processo_v1 = _make_processo("00003")
    salvar_processo(processo_v1, engine=engine)

    processo_v2 = Processo(
        numero="00003",
        classe="Agravo Regimental",
        assunto="Direito Tributário",
        partes=[
            Parte(nome="Maria Souza", tipo="Requerida"),
            Parte(nome="João Silva", tipo="Requerente"),
        ],
        movimentacoes=[
            Movimentacao(data="2024-05-01", descricao="Julgado"),
        ],
    )
    salvar_processo(processo_v2, engine=engine)

    with Session(engine) as session:
        orm = session.query(ProcessoORM).filter_by(numero="00003").first()
        assert orm is not None
        assert orm.classe == "Agravo Regimental"
        assert len(orm.partes) == 2
        assert len(orm.movimentacoes) == 1
