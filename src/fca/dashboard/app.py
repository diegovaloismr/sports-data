"""Dashboard (Camada 2) - visão geral das 8 modalidades da FCA.

Rodar com: streamlit run src/fca/dashboard/app.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from fca.config import load_settings
from fca.dashboard import theme
from fca.dashboard.data import ModalidadeOverview, carregar_overview_modalidades, carregar_resumo_geral
from fca.db.session import make_engine, make_session_factory

st.set_page_config(page_title="FCA - Visão Geral", layout="wide")


@st.cache_resource
def _session_factory():
    settings = load_settings()
    engine = make_engine(settings.database_path)
    return make_session_factory(engine)


def _grafico_ocupacao(overview: list[ModalidadeOverview]) -> go.Figure:
    ordenado = sorted(overview, key=lambda m: m.ocupacao_pct or 0)
    fig = go.Figure(
        go.Bar(
            x=[m.ocupacao_pct or 0 for m in ordenado],
            y=[m.nome for m in ordenado],
            orientation="h",
            marker_color=[theme.cor_modalidade(m.slug) for m in ordenado],
            text=[f"{m.ocupacao_pct:.0f}%" if m.ocupacao_pct is not None else "—" for m in ordenado],
            textposition="outside",
            hovertemplate="%{y}: %{x:.1f}%<extra></extra>",
        )
    )
    fig.update_layout(
        **theme.LAYOUT_BASE,
        title="Ocupação por modalidade (vagas preenchidas ÷ ofertadas)",
        xaxis=dict(title="Ocupação (%)", gridcolor=theme.GRADE, range=[0, max(105, *(m.ocupacao_pct or 0 for m in ordenado) or [0]) + 10]),
        yaxis=dict(title=None),
        height=380,
        showlegend=False,
    )
    return fig


def _grafico_vagas(overview: list[ModalidadeOverview]) -> go.Figure:
    ordenado = sorted(overview, key=lambda m: m.vagas_ofertadas, reverse=True)
    nomes = [m.nome for m in ordenado]

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=[m.vagas_ofertadas for m in ordenado],
            y=nomes,
            orientation="h",
            marker_color=theme.BARRA_FUNDO,
            name="Vagas ofertadas",
            hovertemplate="%{y} - ofertadas: %{x}<extra></extra>",
        )
    )
    fig.add_trace(
        go.Bar(
            x=[m.vagas_preenchidas for m in ordenado],
            y=nomes,
            orientation="h",
            marker_color=[theme.cor_modalidade(m.slug) for m in ordenado],
            name="Vagas preenchidas",
            text=[str(m.vagas_preenchidas) for m in ordenado],
            textposition="outside",
            hovertemplate="%{y} - preenchidas: %{x}<extra></extra>",
        )
    )
    fig.update_layout(
        **theme.LAYOUT_BASE,
        title="Vagas ofertadas vs. preenchidas",
        barmode="overlay",
        xaxis=dict(title="Nº de vagas", gridcolor=theme.GRADE),
        yaxis=dict(title=None),
        height=380,
        legend=dict(orientation="h", y=-0.15),
    )
    return fig


def _cor_status(ok: bool) -> str:
    return theme.STATUS_BOM if ok else theme.STATUS_ATENCAO


def main() -> None:
    st.title("Fundação Campeões do Amanhã")
    st.caption("Visão geral das matrículas ativas por modalidade (dado tratado - Camada 1)")

    session_factory = _session_factory()
    with session_factory() as session:
        resumo = carregar_resumo_geral(session)
        overview = carregar_overview_modalidades(session)

    # --- KPIs gerais -----------------------------------------------------
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Matrículas ativas", f"{resumo.total_matriculas_ativas:,}".replace(",", "."))
    col2.metric("Vagas ofertadas", f"{resumo.total_vagas_ofertadas:,}".replace(",", "."))
    col3.metric("Ocupação média", f"{resumo.ocupacao_media_pct:.1f}%" if resumo.ocupacao_media_pct is not None else "—")
    col4.metric("Duplicatas resolvidas", resumo.duplicatas_resolvidas, help="Matrículas superadas por reenvio de formulário (histórico)")
    col5.metric(
        "Avisos de qualidade" + ("" if resumo.avisos_pendentes else " ✓"),
        resumo.avisos_pendentes,
        help="Locais não mapeados, CPF ausente/inválido, campo de turma não reconhecido",
    )

    st.divider()

    # --- Comparativo entre modalidades ------------------------------------
    col_esq, col_dir = st.columns(2)
    with col_esq:
        st.plotly_chart(_grafico_ocupacao(overview), use_container_width=True)
    with col_dir:
        st.plotly_chart(_grafico_vagas(overview), use_container_width=True)

    st.divider()

    # --- Tabela (view alternativa, acessibilidade) ------------------------
    st.subheader("Detalhamento por modalidade")
    df = pd.DataFrame(
        [
            {
                "Modalidade": m.nome,
                "Vagas ofertadas": m.vagas_ofertadas,
                "Vagas preenchidas": m.vagas_preenchidas,
                "Ocupação (%)": m.ocupacao_pct,
            }
            for m in overview
        ]
    )
    st.dataframe(df, use_container_width=True, hide_index=True)


if __name__ == "__main__":
    main()
