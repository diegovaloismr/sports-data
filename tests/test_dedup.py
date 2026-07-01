import datetime as dt

from fca.etl.cpf import normalize_cpf
from fca.etl.dedup import deduplicar_por_cpf


def test_lindemberg_mantem_registro_mais_recente():
    # Caso real do documento: mesma criança, dois envios do formulário,
    # nomes com grafia levemente diferente, mesmo CPF.
    registros = [
        {
            "cpf": normalize_cpf("101.671.714-88"),
            "nome": "Lindemberg Wellington filex da curz",
            "carimbo_data_hora": dt.datetime(2026, 1, 26),
        },
        {
            "cpf": normalize_cpf("101.671.714-88"),
            "nome": "Lindemberg Wellington Félix da cruz",
            "carimbo_data_hora": dt.datetime(2026, 4, 2),
        },
    ]

    resultado = deduplicar_por_cpf(registros)

    assert len(resultado.ativos) == 1
    assert resultado.ativos[0]["nome"] == "Lindemberg Wellington Félix da cruz"

    assert len(resultado.descartados) == 1
    assert resultado.descartados[0]["nome"] == "Lindemberg Wellington filex da curz"
    assert resultado.descartados[0]["motivo"] == "duplicata_cpf_superada"


def test_sem_duplicata_mantem_todos_ativos():
    registros = [
        {"cpf": "11111111111", "carimbo_data_hora": dt.datetime(2026, 1, 1)},
        {"cpf": "22222222222", "carimbo_data_hora": dt.datetime(2026, 1, 2)},
    ]

    resultado = deduplicar_por_cpf(registros)

    assert len(resultado.ativos) == 2
    assert resultado.descartados == []


def test_tres_reenvios_mantem_so_o_mais_recente():
    registros = [
        {"cpf": "33333333333", "carimbo_data_hora": dt.datetime(2026, 1, 1), "v": "a"},
        {"cpf": "33333333333", "carimbo_data_hora": dt.datetime(2026, 3, 1), "v": "b"},
        {"cpf": "33333333333", "carimbo_data_hora": dt.datetime(2026, 2, 1), "v": "c"},
    ]

    resultado = deduplicar_por_cpf(registros)

    assert len(resultado.ativos) == 1
    assert resultado.ativos[0]["v"] == "b"
    assert {d["v"] for d in resultado.descartados} == {"a", "c"}
