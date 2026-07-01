"""Schema do banco de dados local (SQLite) do sistema FCA.

Este schema é o contrato entre a Camada 1 (ETL) e as Camadas 2/3
(dashboard e relatórios), e também o que uma futura camada de IA vai
consultar. Por isso cada tabela guarda dado tratado E rastreabilidade
(de onde veio, o que foi descartado e por quê) em vez de só o resultado
final - importante tanto para confiar no dashboard quanto para auditar
decisões de deduplicação/mapeamento depois.

Visão geral das tabelas:
  - modalidades: as 8 modalidades esportivas.
  - locais: locais/turmas oficiais, vindos da aba "Locais - Contatos".
  - locais_aliases: de-para "nome como aparece na matrícula" -> local oficial.
  - vagas: vagas ofertadas/preenchidas por modalidade (aba "Vagas 2026").
  - atletas: uma linha por CPF normalizado (pessoa única).
  - matriculas: matrícula ATIVA de um atleta em uma modalidade (uma por
    combinação atleta+modalidade - é o resultado já deduplicado).
  - matriculas_descartadas: log de auditoria de todo registro bruto que
    foi superado por reenvio de formulário (não é apagado, só marcado).
  - log_erros_parsing: avisos de dados que o pipeline não conseguiu tratar
    sozinho (local não mapeado, CPF inválido, campo de turma não parseável).
"""

from __future__ import annotations

import datetime as dt

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Modalidade(Base):
    __tablename__ = "modalidades"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(30), unique=True, index=True)
    nome: Mapped[str] = mapped_column(String(50))

    locais: Mapped[list["Local"]] = relationship(back_populates="modalidade")
    vaga: Mapped["Vaga | None"] = relationship(back_populates="modalidade")


class Local(Base):
    """Local oficial de uma modalidade, conforme aba 'Locais - Contatos'."""

    __tablename__ = "locais"
    __table_args__ = (UniqueConstraint("modalidade_id", "nome_oficial"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    modalidade_id: Mapped[int] = mapped_column(ForeignKey("modalidades.id"))
    nome_oficial: Mapped[str] = mapped_column(String(150))
    endereco: Mapped[str | None] = mapped_column(String(255))
    horarios_atendimento: Mapped[str | None] = mapped_column(Text)
    professores_contato: Mapped[str | None] = mapped_column(Text)

    modalidade: Mapped["Modalidade"] = relationship(back_populates="locais")


class LocalAlias(Base):
    """De-para: nome do local como aparece no campo livre da matrícula.

    Espelha config/locais_mapping.yaml - é recarregada a cada sync a
    partir do YAML, que é a fonte editável pelo usuário.
    """

    __tablename__ = "locais_aliases"
    __table_args__ = (UniqueConstraint("modalidade_id", "alias"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    modalidade_id: Mapped[int] = mapped_column(ForeignKey("modalidades.id"))
    alias: Mapped[str] = mapped_column(String(150))
    local_id: Mapped[int] = mapped_column(ForeignKey("locais.id"))

    local: Mapped["Local"] = relationship()


class Vaga(Base):
    """Snapshot atual de vagas ofertadas/preenchidas por modalidade."""

    __tablename__ = "vagas"

    id: Mapped[int] = mapped_column(primary_key=True)
    modalidade_id: Mapped[int] = mapped_column(ForeignKey("modalidades.id"), unique=True)
    vagas_ofertadas: Mapped[int] = mapped_column(default=0)
    vagas_preenchidas: Mapped[int] = mapped_column(default=0)
    ocupacao_pct: Mapped[float | None] = mapped_column(default=None)
    atualizado_em: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)

    modalidade: Mapped["Modalidade"] = relationship(back_populates="vaga")


class Atleta(Base):
    """Uma linha por pessoa (chave = CPF normalizado)."""

    __tablename__ = "atletas"

    id: Mapped[int] = mapped_column(primary_key=True)
    cpf: Mapped[str] = mapped_column(String(11), unique=True, index=True)
    nome_completo: Mapped[str] = mapped_column(String(150))
    data_nascimento: Mapped[str | None] = mapped_column(String(20))
    sexo: Mapped[str | None] = mapped_column(String(20))
    bairro: Mapped[str | None] = mapped_column(String(100))
    cidade: Mapped[str | None] = mapped_column(String(100))
    estado: Mapped[str | None] = mapped_column(String(10))
    telefone: Mapped[str | None] = mapped_column(String(30))
    nome_responsavel: Mapped[str | None] = mapped_column(String(150))
    telefone_responsavel: Mapped[str | None] = mapped_column(String(30))
    email: Mapped[str | None] = mapped_column(String(150))
    recebe_beneficio_social: Mapped[bool | None] = mapped_column(Boolean, default=None)
    escolaridade: Mapped[str | None] = mapped_column(String(100))
    modelo_ensino: Mapped[str | None] = mapped_column(String(100))
    turno_estudo: Mapped[str | None] = mapped_column(String(30))

    matriculas: Mapped[list["Matricula"]] = relationship(back_populates="atleta")


class Matricula(Base):
    """Matrícula ATIVA (já deduplicada) de um atleta em uma modalidade."""

    __tablename__ = "matriculas"
    __table_args__ = (UniqueConstraint("atleta_id", "modalidade_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    atleta_id: Mapped[int] = mapped_column(ForeignKey("atletas.id"))
    modalidade_id: Mapped[int] = mapped_column(ForeignKey("modalidades.id"))
    local_id: Mapped[int | None] = mapped_column(ForeignKey("locais.id"), default=None)

    turma_raw_text: Mapped[str] = mapped_column(Text)
    local_raw_text: Mapped[str | None] = mapped_column(String(150))
    dias_semana: Mapped[str | None] = mapped_column(String(100))  # ex: "Segunda,Quarta,Sexta"
    turno: Mapped[str | None] = mapped_column(String(10))  # Manhã | Tarde | Noite
    faixa_etaria_min: Mapped[int | None] = mapped_column(default=None)
    faixa_etaria_max: Mapped[int | None] = mapped_column(default=None)
    horario_inicio: Mapped[str | None] = mapped_column(String(5))  # "HH:MM"
    horario_fim: Mapped[str | None] = mapped_column(String(5))

    carimbo_data_hora: Mapped[dt.datetime] = mapped_column(DateTime)
    termo_autorizacao_raw: Mapped[str | None] = mapped_column(Text)

    atleta: Mapped["Atleta"] = relationship(back_populates="matriculas")
    modalidade: Mapped["Modalidade"] = relationship()
    local: Mapped["Local | None"] = relationship()


class MatriculaDescartada(Base):
    """Log de auditoria: todo registro bruto superado por reenvio de formulário.

    Nada é apagado do histórico - só deixa de contar como matrícula ativa.
    """

    __tablename__ = "matriculas_descartadas"

    id: Mapped[int] = mapped_column(primary_key=True)
    modalidade_id: Mapped[int] = mapped_column(ForeignKey("modalidades.id"))
    atleta_id: Mapped[int | None] = mapped_column(ForeignKey("atletas.id"), default=None)
    cpf_raw: Mapped[str | None] = mapped_column(String(20))
    nome_raw: Mapped[str | None] = mapped_column(String(150))
    carimbo_data_hora: Mapped[dt.datetime | None] = mapped_column(DateTime)
    turma_raw_text: Mapped[str | None] = mapped_column(Text)
    motivo: Mapped[str] = mapped_column(String(50))  # ex: "duplicata_cpf_superada"
    matricula_vencedora_id: Mapped[int | None] = mapped_column(ForeignKey("matriculas.id"), default=None)
    dados_brutos_json: Mapped[str | None] = mapped_column(Text)
    registrado_em: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)

    modalidade: Mapped["Modalidade"] = relationship()


class LogErroParsing(Base):
    """Avisos de dados que o pipeline não conseguiu tratar automaticamente.

    É a base dos "Indicadores de qualidade de dados" da Camada 2.
    """

    __tablename__ = "log_erros_parsing"

    id: Mapped[int] = mapped_column(primary_key=True)
    modalidade_id: Mapped[int | None] = mapped_column(ForeignKey("modalidades.id"), default=None)
    tipo: Mapped[str] = mapped_column(String(50))  # local_nao_mapeado | cpf_invalido | turma_nao_parseada
    valor_bruto: Mapped[str | None] = mapped_column(Text)
    detalhe: Mapped[str | None] = mapped_column(Text)
    resolvido: Mapped[bool] = mapped_column(Boolean, default=False)
    criado_em: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)

    modalidade: Mapped["Modalidade | None"] = relationship()
