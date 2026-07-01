from pathlib import Path

from fca.etl.locais_mapping import LocaisMapping

CONFIG_PATH = Path(__file__).resolve().parents[1] / "config" / "locais_mapping.yaml"


def test_resolve_alias_futebol():
    mapping = LocaisMapping.from_yaml(CONFIG_PATH)
    assert mapping.resolver("futebol", "ARENA PH12 - FUNCIONÁRIOS") == "Arena Funcionários"


def test_resolve_alias_jiujitsu_local_ja_sem_aspas():
    mapping = LocaisMapping.from_yaml(CONFIG_PATH)
    assert mapping.resolver("jiujitsu", "GINÁSIO O RONALDÃO") == "Ginásio Ronaldão"


def test_resolve_ignora_espacos_e_caixa():
    mapping = LocaisMapping.from_yaml(CONFIG_PATH)
    assert mapping.resolver("jiujitsu", "  ginásio o ronaldão  ") == "Ginásio Ronaldão"


def test_resolve_alias_nao_mapeado_retorna_none():
    mapping = LocaisMapping.from_yaml(CONFIG_PATH)
    assert mapping.resolver("natacao", "LOCAL QUE NÃO EXISTE") is None


def test_resolve_modalidade_sem_aliases_cadastrados():
    mapping = LocaisMapping.from_yaml(CONFIG_PATH)
    assert mapping.resolver("tenis", "QUALQUER COISA") is None
