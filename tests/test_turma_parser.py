from fca.etl.turma_parser import parse_turma


def test_futebol_dias_e_turno_sem_faixa_nem_horario():
    r = parse_turma("ESTÁDIO DA GRAÇA: Segundas / Quartas / Sextas - Turno da Tarde", "futebol")
    assert r.local_raw == "ESTÁDIO DA GRAÇA"
    assert r.dias_semana == ["Segunda", "Quarta", "Sexta"]
    assert r.turno == "Tarde"
    assert r.faixa_etaria_min is None
    assert r.horario_inicio is None


def test_voleibol_com_faixa_etaria_e_horario():
    r = parse_turma(
        "GINÁSIO DO NEUSA: Segundas / Quartas / Sextas - Turno da Tarde "
        "(Iniciante - 9 a 11 anos) - 15:30 as 16:30",
        "voleibol",
    )
    assert r.local_raw == "GINÁSIO DO NEUSA"
    assert r.dias_semana == ["Segunda", "Quarta", "Sexta"]
    assert r.turno == "Tarde"
    assert (r.faixa_etaria_min, r.faixa_etaria_max) == (9, 11)
    assert (r.horario_inicio, r.horario_fim) == ("15:30", "16:30")


def test_jiujitsu_remove_aspas_do_local():
    r = parse_turma('GINÁSIO "O RONALDÃO": Terça / Quinta - Turno da Noite (8 a 11 anos)', "jiujitsu")
    assert r.local_raw == "GINÁSIO O RONALDÃO"
    assert r.dias_semana == ["Terça", "Quinta"]
    assert r.turno == "Noite"
    assert (r.faixa_etaria_min, r.faixa_etaria_max) == (8, 11)


def test_natacao_um_dia_so():
    r = parse_turma("CENTRO ADMINISTRATIVO MUNICIPAL: Sextas - Turno da Tarde", "natacao")
    assert r.local_raw == "CENTRO ADMINISTRATIVO MUNICIPAL"
    assert r.dias_semana == ["Sexta"]
    assert r.turno == "Tarde"


def test_tenis_com_segundo_dois_pontos_no_texto():
    r = parse_turma("CENTRO TENÍSTICO PARAIBANO: Terça / Quinta / Sexta: 14:00h as 15:00h", "tenis")
    assert r.local_raw == "CENTRO TENÍSTICO PARAIBANO"
    assert r.dias_semana == ["Terça", "Quinta", "Sexta"]
    assert (r.horario_inicio, r.horario_fim) == ("14:00", "15:00")
    assert r.turno is None


def test_triathlon_turma_unica_sem_turno():
    r = parse_turma("TURMA ÚNICA: Segundas / Quartas / Sábados", "triathlon")
    assert r.local_raw == "TURMA ÚNICA"
    assert r.dias_semana == ["Segunda", "Quarta", "Sábado"]
    assert r.turno is None


def test_texto_sem_dois_pontos_gera_aviso():
    r = parse_turma("texto mal formatado sem separador", "futebol")
    assert r.avisos
