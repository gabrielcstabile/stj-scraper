"""Camada de persistência SQLite via SQLAlchemy — tabelas e upsert."""

from datetime import date

from sqlalchemy import (
    Date,
    Engine,
    ForeignKey,
    Integer,
    String,
    Text,
    create_engine,
    select,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship

from stj_scraper.logger import get_logger
from stj_scraper.models import Processo

logger = get_logger(__name__)

_DB_URL = "sqlite:///data/stj.db"


class Base(DeclarativeBase):
    """Base declarativa do SQLAlchemy."""


class ProcessoORM(Base):
    """Tabela de processos."""

    __tablename__ = "processos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    numero: Mapped[str] = mapped_column(String, unique=True, nullable=False, index=True)
    classe: Mapped[str] = mapped_column(String, nullable=False)
    assunto: Mapped[str] = mapped_column(Text, nullable=False)

    partes: Mapped[list["ParteORM"]] = relationship(
        "ParteORM", back_populates="processo", cascade="all, delete-orphan"
    )
    movimentacoes: Mapped[list["MovimentacaoORM"]] = relationship(
        "MovimentacaoORM", back_populates="processo", cascade="all, delete-orphan"
    )


class ParteORM(Base):
    """Tabela de partes processuais."""

    __tablename__ = "partes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    processo_id: Mapped[int] = mapped_column(ForeignKey("processos.id"), nullable=False)
    nome: Mapped[str] = mapped_column(String, nullable=False)
    tipo: Mapped[str] = mapped_column(String, nullable=False)

    processo: Mapped[ProcessoORM] = relationship("ProcessoORM", back_populates="partes")


class MovimentacaoORM(Base):
    """Tabela de movimentações processuais."""

    __tablename__ = "movimentacoes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    processo_id: Mapped[int] = mapped_column(ForeignKey("processos.id"), nullable=False)
    data: Mapped[date] = mapped_column(Date, nullable=False)
    descricao: Mapped[str] = mapped_column(Text, nullable=False)

    processo: Mapped[ProcessoORM] = relationship(
        "ProcessoORM", back_populates="movimentacoes"
    )


def init_db(db_url: str = _DB_URL) -> Engine:
    """Cria as tabelas no banco se não existirem e retorna a engine."""
    engine = create_engine(db_url)
    Base.metadata.create_all(engine)
    return engine


def salvar_processo(
    processo: Processo,
    db_url: str = _DB_URL,
    engine: Engine | None = None,
) -> None:
    """Faz upsert completo do processo: insere ou atualiza pelo número."""
    try:
        if engine is None:
            engine = create_engine(db_url)
        Base.metadata.create_all(engine)

        with Session(engine) as session:
            stmt = select(ProcessoORM).where(ProcessoORM.numero == processo.numero)
            existing = session.scalar(stmt)

            if existing:
                logger.debug("Processo %s já existe — atualizando.", processo.numero)
                existing.classe = processo.classe
                existing.assunto = processo.assunto
                # Limpa filhos para reinserir (upsert das coleções)
                existing.partes.clear()
                existing.movimentacoes.clear()
                orm_processo = existing
            else:
                orm_processo = ProcessoORM(
                    numero=processo.numero,
                    classe=processo.classe,
                    assunto=processo.assunto,
                )
                session.add(orm_processo)

            for parte in processo.partes:
                orm_processo.partes.append(
                    ParteORM(nome=parte.nome, tipo=parte.tipo)
                )

            for mov in processo.movimentacoes:
                orm_processo.movimentacoes.append(
                    MovimentacaoORM(data=mov.data, descricao=mov.descricao)
                )

            session.commit()
            logger.info("Processo %s salvo com sucesso.", processo.numero)

    except Exception as exc:
        logger.critical("Erro de banco ao salvar processo %s: %s", processo.numero, exc)
        raise
