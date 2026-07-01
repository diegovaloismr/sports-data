"""Teste de integração do pipeline completo com um SheetsReader falso
(dados em memória, sem tocar o Google Sheets real) e um SQLite em memória.

Serve para validar a orquestração ponta a ponta - leitura, parsing de
turma, de-para de locais, deduplicação por CPF e gravação no banco -
com dados no mesmo formato dos exemplos reais do levantamento.
"""

from pathlib import Path

import pytest

from fca.config import ModalidadeConfig, Settings
from fca.db.models import LogErroParsing, Matricula, MatriculaDescartada
from fca.db.session import init_db, make_engine, make_session_factory
from fca.etl.pipeline import run_sync

CONFIG_DIR = Path(__file__).resolve().parents[1] / "config"

COLUNAS_BASE = {
    "Carimbo de data/hora": "",
    "NOME COMPLETO": "",
    "DATA DE NASCIMENTO": "",
    "CPF": "",
    "SEXO": "",
    "BAIRRO": "",
    "CIDADE": "João Pessoa",
    "ESTADO": "PB",
    "TELEFONE / WHATSAPP PARA CONTATO": "",
    "NOME COMPLETO 2": "",
    "TELEFONE (RESPONSÁVEL)": "",
    "E-MAIL": "",
    "A FAMÍLIA RECEBE ALGUM BENEFÍCIO SOCIAL?": "NÃO",
    "ESCOLARIDADE": "",
    "MODELO DE ENSINO ESCOLAR DO ATLETA": "",
    "TURNO QUE ESTUDA": "",
    "MARQUE A OPÇÃO DA TURMA E HORÁRIO DESEJADO": "",
}


def _linha(**overrides):
    linha = dict(COLUNAS_BASE)
    linha.update(overrides)
    linha["Termo de autorização de uso de imagem"] = "Li e concordo."
    return linha


class FakeSheetsReader:
    def __init__(self, abas_mestre: dict, matriculas: dict):
        self._abas_mestre = abas_mestre  # {(sheet_id, aba_nome): [linhas]}
        self._matriculas = matriculas  # {sheet_id: [linhas]}

    def ler_aba(self, sheet_id, aba_nome):
        return self._abas_mestre[(sheet_id, aba_nome)]

    def ler_primeira_aba(self, sheet_id):
        return self._matriculas[sheet_id]


@pytest.fixture
def settings():
    return Settings(
        service_account_file=Path("unused.json"),
        database_path=Path(":memory:"),
        sheet_id_mestre="sheet_mestre",
        aba_vagas="Vagas 2026",
        aba_locais="Locais - Contatos",
        modalidades=[
            ModalidadeConfig(slug="futebol", nome="Futebol", sheet_id="sheet_futebol"),
            ModalidadeConfig(slug="jiujitsu", nome="Jiu-jitsu", sheet_id="sheet_jiujitsu"),
            ModalidadeConfig(slug="natacao", nome="Natação", sheet_id=None),
        ],
        locais_mapping_path=CONFIG_DIR / "locais_mapping.yaml",
    )


@pytest.fixture
def reader():
    abas_mestre = {
        ("sheet_mestre", "Locais - Contatos"): [
            {
                "Modalidade": "Futebol",
                "Local": "Arena Funcionários",
                "Endereço": "Rua X, 123",
                "Horários de Atendimentos": "Seg/Qua/Sex - Tarde",
                "Professores Responsáveis / Contato": "Prof. João - (83) 90000-0000",
            },
            {
                "Modalidade": "Jiu-jitsu",
                "Local": "Ginásio Ronaldão",
                "Endereço": "Rua Y, 456",
                "Horários de Atendimentos": "Ter/Qui - Noite",
                "Professores Responsáveis / Contato": "Prof. Maria - (83) 90000-1111",
            },
        ],
        ("sheet_mestre", "Vagas 2026"): [
            {"Modalidade Esportiva": "Futebol", "Vagas Ofertadas": "200", "Vagas Preenchidas": "174", "Ocupação (%)": "87"},
            {"Modalidade Esportiva": "Jiu-jitsu", "Vagas Ofertadas": "60", "Vagas Preenchidas": "60", "Ocupação (%)": "100"},
            {"Modalidade Esportiva": "TOTAL", "Vagas Ofertadas": "260", "Vagas Preenchidas": "234", "Ocupação (%)": "90"},
        ],
    }

    matriculas = {
        "sheet_futebol": [
            _linha(
                **{
                    "Carimbo de data/hora": "26/01/2026 10:00:00",
                    "NOME COMPLETO": "Lindemberg Wellington filex da curz",
                    "CPF": "101.671.714-88",
                    "MARQUE A OPÇÃO DA TURMA E HORÁRIO DESEJADO":
                        "ARENA PH12 - FUNCIONÁRIOS: Segundas / Quartas / Sextas - Turno da Tarde",
                }
            ),
            _linha(
                **{
                    "Carimbo de data/hora": "02/04/2026 09:00:00",
                    "NOME COMPLETO": "Lindemberg Wellington Félix da cruz",
                    "CPF": "10167171488",
                    "MARQUE A OPÇÃO DA TURMA E HORÁRIO DESEJADO":
                        "ARENA PH12 - FUNCIONÁRIOS: Segundas / Quartas / Sextas - Turno da Tarde",
                }
            ),
            _linha(
                **{
                    "Carimbo de data/hora": "10/02/2026 08:00:00",
                    "NOME COMPLETO": "Outra Criança Qualquer",
                    "CPF": "139.963.024-52",
                    "MARQUE A OPÇÃO DA TURMA E HORÁRIO DESEJADO":
                        "QUADRA QUE NÃO EXISTE NO CADASTRO: Segundas - Turno da Manhã",
                }
            ),
        ],
        "sheet_jiujitsu": [
            _linha(
                **{
                    "Carimbo de data/hora": "05/03/2026 15:00:00",
                    "NOME COMPLETO": "Atleta Jiu-jitsu",
                    "CPF": "111.444.777-35",
                    "MARQUE A OPÇÃO DA TURMA E HORÁRIO DESEJADO":
                        'GINÁSIO "O RONALDÃO": Terça / Quinta - Turno da Noite (8 a 11 anos)',
                }
            ),
        ],
    }

    return FakeSheetsReader(abas_mestre, matriculas)


def test_sync_completo_com_dados_em_memoria(settings, reader):
    engine = make_engine(settings.database_path)
    init_db(engine)
    session_factory = make_session_factory(engine)

    relatorio = run_sync(settings, reader, session_factory)

    # Futebol: 3 linhas brutas, 1 duplicata (Lindemberg) -> 2 matrículas ativas.
    # Jiu-jitsu: 1 linha -> 1 matrícula ativa. Natação foi pulada (sem sheet_id).
    assert relatorio.matriculas_ativas == 3
    assert relatorio.matriculas_descartadas == 1
    assert relatorio.atletas_criados_ou_atualizados == 3

    with session_factory() as session:
        matriculas = session.query(Matricula).all()
        assert len(matriculas) == 3

        lindemberg = next(m for m in matriculas if m.atleta.cpf == "10167171488")
        assert lindemberg.atleta.nome_completo == "Lindemberg Wellington Félix da cruz"
        assert lindemberg.local.nome_oficial == "Arena Funcionários"
        assert lindemberg.dias_semana == "Segunda,Quarta,Sexta"
        assert lindemberg.turno == "Tarde"

        jiujitsu = next(m for m in matriculas if m.atleta.cpf == "11144477735")
        assert jiujitsu.local.nome_oficial == "Ginásio Ronaldão"
        assert jiujitsu.faixa_etaria_min == 8
        assert jiujitsu.faixa_etaria_max == 11

        sem_local = next(m for m in matriculas if m.atleta.cpf == "13996302452")
        assert sem_local.local_id is None
        assert sem_local.local_raw_text == "QUADRA QUE NÃO EXISTE NO CADASTRO"

        descartadas = session.query(MatriculaDescartada).all()
        assert len(descartadas) == 1
        assert descartadas[0].cpf_raw == "10167171488"
        assert descartadas[0].motivo == "duplicata_cpf_superada"

        erros = session.query(LogErroParsing).filter_by(tipo="local_nao_mapeado").all()
        assert len(erros) == 1
        assert erros[0].valor_bruto == "QUADRA QUE NÃO EXISTE NO CADASTRO"
