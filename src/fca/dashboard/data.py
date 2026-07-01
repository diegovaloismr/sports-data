"""Consultas de leitura para o dashboard (Camada 2).

Fica separado do código do Streamlit (`app.py`) de propósito: essas
funções são reutilizáveis por qualquer front-end - inclusive a futura
camada de IA que vai responder perguntas em linguagem natural sobre os
dados tratados (é o "schema de banco claro e função de query reutilizável"
citado no levantamento original).
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from fca.db.models import LogErroParsing, Matricula, MatriculaDescartada, Modalidade, Vaga


@dataclass
class ModalidadeOverview:
    slug: str
    nome: str
    vagas_ofertadas: int
    vagas_preenchidas: int
    ocupacao_pct: float | None


@dataclass
class ResumoGeral:
    total_matriculas_ativas: int
    total_vagas_ofertadas: int
    ocupacao_media_pct: float | None
    duplicatas_resolvidas: int
    avisos_pendentes: int


def carregar_overview_modalidades(session: Session) -> list[ModalidadeOverview]:
    """Uma linha por modalidade, na ordem cadastrada em config/modalidades.yaml
    (mantém a cor fixa por modalidade estável no dashboard)."""
    resultado = []
    for modalidade in session.query(Modalidade).order_by(Modalidade.id).all():
        vaga = session.query(Vaga).filter_by(modalidade_id=modalidade.id).one_or_none()
        resultado.append(
            ModalidadeOverview(
                slug=modalidade.slug,
                nome=modalidade.nome,
                vagas_ofertadas=vaga.vagas_ofertadas if vaga else 0,
                vagas_preenchidas=vaga.vagas_preenchidas if vaga else 0,
                ocupacao_pct=vaga.ocupacao_pct if vaga else None,
            )
        )
    return resultado


def carregar_resumo_geral(session: Session) -> ResumoGeral:
    overview = carregar_overview_modalidades(session)
    total_ativas = session.query(Matricula).count()
    total_ofertadas = sum(m.vagas_ofertadas for m in overview)
    total_preenchidas = sum(m.vagas_preenchidas for m in overview)
    ocupacao_media = round(total_preenchidas / total_ofertadas * 100, 1) if total_ofertadas else None

    return ResumoGeral(
        total_matriculas_ativas=total_ativas,
        total_vagas_ofertadas=total_ofertadas,
        ocupacao_media_pct=ocupacao_media,
        duplicatas_resolvidas=session.query(MatriculaDescartada).count(),
        avisos_pendentes=session.query(LogErroParsing).filter_by(resolvido=False).count(),
    )
