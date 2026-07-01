"""Testa as consultas do dashboard (data.py) contra um banco populado pelo
pipeline de teste - mesma abordagem do test_pipeline.py, sem tocar o
Google Sheets real."""

from fca.dashboard.data import carregar_overview_modalidades, carregar_resumo_geral
from fca.db.session import init_db, make_engine, make_session_factory
from fca.etl.pipeline import run_sync

from tests.test_pipeline import reader, settings  # noqa: F401  (fixtures reaproveitadas)


def test_overview_modalidades_reflete_o_sync(settings, reader):
    engine = make_engine(settings.database_path)
    init_db(engine)
    session_factory = make_session_factory(engine)
    run_sync(settings, reader, session_factory)

    with session_factory() as session:
        overview = carregar_overview_modalidades(session)
        por_slug = {m.slug: m for m in overview}

        assert por_slug["futebol"].vagas_preenchidas == 2
        assert por_slug["futebol"].nome == "Futebol"
        assert por_slug["triathlon"].vagas_preenchidas == 15  # sem sheet_id, vem da planilha
        assert por_slug["natacao"].vagas_ofertadas == 0  # sem Vaga sincronizada nesta fixture


def test_resumo_geral_agrega_indicadores(settings, reader):
    engine = make_engine(settings.database_path)
    init_db(engine)
    session_factory = make_session_factory(engine)
    run_sync(settings, reader, session_factory)

    with session_factory() as session:
        resumo = carregar_resumo_geral(session)

        assert resumo.total_matriculas_ativas == 3
        assert resumo.duplicatas_resolvidas == 1
        assert resumo.avisos_pendentes == 1  # local_nao_mapeado da fixture
        assert resumo.total_vagas_ofertadas == 280  # 200 (futebol) + 60 (jiu-jitsu) + 20 (triathlon)
