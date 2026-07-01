"""Orquestra um sync completo: lê as 9 planilhas, trata e grava no SQLite.

Depende de `SheetsReader` (protocolo definido em `sheets_client.py`) em vez
de gspread diretamente, então esse módulo é testável de ponta a ponta com
um reader falso (dados em memória) - sem precisar de credenciais reais.
`scripts/sync.py` é quem injeta o `GspreadSheetsReader` de verdade.
"""

from __future__ import annotations

import datetime as dt
import re
from dataclasses import dataclass, field

from sqlalchemy.orm import Session, sessionmaker

from fca.config import Settings
from fca.db.models import (
    Atleta,
    Local,
    LogErroParsing,
    Matricula,
    MatriculaDescartada,
    Modalidade,
    Vaga,
)
from fca.etl.cpf import normalize_cpf
from fca.etl.dedup import deduplicar_por_cpf
from fca.etl.locais_mapping import LocaisMapping
from fca.etl.sheets_client import SheetsReader
from fca.etl.turma_parser import parse_turma

# Nomes de coluna das 8 planilhas de matrícula (schema confirmado - 18 colunas).
COL_CARIMBO = "Carimbo de data/hora"
COL_NOME = "NOME COMPLETO"
COL_NASCIMENTO = "DATA DE NASCIMENTO"
COL_CPF = "CPF"
COL_SEXO = "SEXO"
COL_BAIRRO = "BAIRRO"
COL_CIDADE = "CIDADE"
COL_ESTADO = "ESTADO"
COL_TELEFONE = "TELEFONE / WHATSAPP PARA CONTATO"
COL_NOME_RESPONSAVEL = "NOME COMPLETO 2"
COL_TELEFONE_RESPONSAVEL = "TELEFONE (RESPONSÁVEL)"
COL_EMAIL = "E-MAIL"
COL_BENEFICIO = "A FAMÍLIA RECEBE ALGUM BENEFÍCIO SOCIAL?"
COL_ESCOLARIDADE = "ESCOLARIDADE"
COL_MODELO_ENSINO = "MODELO DE ENSINO ESCOLAR DO ATLETA"
COL_TURNO_ESTUDO = "TURNO QUE ESTUDA"
COL_TURMA = "MARQUE A OPÇÃO DA TURMA E HORÁRIO DESEJADO"

_COLUNAS_CONHECIDAS = {
    COL_CARIMBO, COL_NOME, COL_NASCIMENTO, COL_CPF, COL_SEXO, COL_BAIRRO,
    COL_CIDADE, COL_ESTADO, COL_TELEFONE, COL_NOME_RESPONSAVEL,
    COL_TELEFONE_RESPONSAVEL, COL_EMAIL, COL_BENEFICIO, COL_ESCOLARIDADE,
    COL_MODELO_ENSINO, COL_TURNO_ESTUDO, COL_TURMA,
}

# Nomes de coluna da planilha mestre.
MASTER_VAGAS_MODALIDADE = "Modalidade Esportiva"
MASTER_VAGAS_OFERTADAS = "Vagas Ofertadas"
MASTER_VAGAS_PREENCHIDAS = "Vagas Preenchidas"
MASTER_VAGAS_OCUPACAO = "Ocupação (%)"

MASTER_LOCAIS_MODALIDADE = "Modalidade"
MASTER_LOCAIS_LOCAL = "Local"
MASTER_LOCAIS_ENDERECO = "Endereço"
MASTER_LOCAIS_HORARIOS = "Horários de Atendimentos"
MASTER_LOCAIS_PROFESSORES = "Professores Responsáveis / Contato"

_FORMATOS_CARIMBO = ("%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M", "%Y-%m-%d %H:%M:%S")


@dataclass
class RelatorioSync:
    atletas_criados_ou_atualizados: int = 0
    matriculas_ativas: int = 0
    matriculas_descartadas: int = 0
    erros_parsing: int = 0
    avisos: list[str] = field(default_factory=list)


def _normaliza_nome(texto: str) -> str:
    return re.sub(r"\s+", " ", (texto or "").strip().upper())


def _parse_carimbo(bruto: str | None) -> dt.datetime | None:
    if not bruto:
        return None
    for formato in _FORMATOS_CARIMBO:
        try:
            return dt.datetime.strptime(bruto.strip(), formato)
        except ValueError:
            continue
    return None


def _to_int(bruto) -> int | None:
    try:
        return int(str(bruto).strip())
    except (ValueError, TypeError):
        return None


def _to_float(bruto) -> float | None:
    try:
        texto = str(bruto).strip().replace("%", "").replace(",", ".")
        return float(texto)
    except (ValueError, TypeError):
        return None


def _extrai_termo_autorizacao(linha: dict) -> str | None:
    for chave, valor in linha.items():
        if chave not in _COLUNAS_CONHECIDAS:
            return valor
    return None


def _sincroniza_modalidades(session: Session, settings: Settings) -> dict[str, Modalidade]:
    modalidade_por_slug: dict[str, Modalidade] = {}
    for m in settings.modalidades:
        modalidade = session.query(Modalidade).filter_by(slug=m.slug).one_or_none()
        if modalidade is None:
            modalidade = Modalidade(slug=m.slug, nome=m.nome)
            session.add(modalidade)
            session.flush()
        modalidade_por_slug[m.slug] = modalidade
    return modalidade_por_slug


def _sincroniza_locais_e_vagas(
    session: Session,
    settings: Settings,
    reader: SheetsReader,
    modalidade_por_slug: dict[str, Modalidade],
    relatorio: RelatorioSync,
) -> None:
    nome_para_slug = {_normaliza_nome(m.nome): m.slug for m in settings.modalidades}

    if not settings.sheet_id_locais:
        relatorio.avisos.append("FCA_SHEET_ID_LOCAIS não configurado - locais não foram sincronizados.")
    else:
        for linha in reader.ler_primeira_aba(settings.sheet_id_locais):
            slug = nome_para_slug.get(_normaliza_nome(linha.get(MASTER_LOCAIS_MODALIDADE, "")))
            nome_oficial = (linha.get(MASTER_LOCAIS_LOCAL) or "").strip()
            if slug is None or not nome_oficial:
                if slug is None:
                    relatorio.erros_parsing += 1
                    session.add(LogErroParsing(
                        tipo="modalidade_nao_reconhecida",
                        valor_bruto=linha.get(MASTER_LOCAIS_MODALIDADE),
                        detalhe="Nome de modalidade na planilha de Locais não bate com config/modalidades.yaml.",
                    ))
                continue
            modalidade = modalidade_por_slug[slug]
            local = session.query(Local).filter_by(modalidade_id=modalidade.id, nome_oficial=nome_oficial).one_or_none()
            if local is None:
                local = Local(modalidade_id=modalidade.id, nome_oficial=nome_oficial)
                session.add(local)
            local.endereco = linha.get(MASTER_LOCAIS_ENDERECO) or None
            local.horarios_atendimento = linha.get(MASTER_LOCAIS_HORARIOS) or None
            local.professores_contato = linha.get(MASTER_LOCAIS_PROFESSORES) or None
        session.flush()

    if not settings.sheet_id_vagas:
        relatorio.avisos.append("FCA_SHEET_ID_VAGAS não configurado - vagas não foram sincronizadas.")
        return

    for linha in reader.ler_primeira_aba(settings.sheet_id_vagas):
        nome_bruto = linha.get(MASTER_VAGAS_MODALIDADE, "")
        if _normaliza_nome(nome_bruto) == "TOTAL":
            continue
        slug = nome_para_slug.get(_normaliza_nome(nome_bruto))
        if slug is None:
            continue
        modalidade = modalidade_por_slug[slug]
        vaga = session.query(Vaga).filter_by(modalidade_id=modalidade.id).one_or_none()
        if vaga is None:
            vaga = Vaga(modalidade_id=modalidade.id)
            session.add(vaga)
        vaga.vagas_ofertadas = _to_int(linha.get(MASTER_VAGAS_OFERTADAS)) or 0
        vaga.vagas_preenchidas = _to_int(linha.get(MASTER_VAGAS_PREENCHIDAS)) or 0
        vaga.ocupacao_pct = _to_float(linha.get(MASTER_VAGAS_OCUPACAO))
        vaga.atualizado_em = dt.datetime.utcnow()
    session.flush()


def _resolve_local(
    slug: str,
    local_raw: str,
    locais_mapping: LocaisMapping,
    locais_oficiais: dict[str, Local],
) -> Local | None:
    if not local_raw:
        return None
    direto = locais_oficiais.get(_normaliza_nome(local_raw))
    if direto is not None:
        return direto
    nome_oficial = locais_mapping.resolver(slug, local_raw)
    if nome_oficial is not None:
        return locais_oficiais.get(_normaliza_nome(nome_oficial))
    return None


def _trata_linha_matricula(
    linha: dict,
    slug: str,
    locais_mapping: LocaisMapping,
    locais_oficiais: dict[str, Local],
    session: Session,
    modalidade: Modalidade,
    relatorio: RelatorioSync,
) -> dict | None:
    cpf = normalize_cpf(linha.get(COL_CPF))
    if not cpf:
        relatorio.erros_parsing += 1
        session.add(LogErroParsing(
            modalidade_id=modalidade.id, tipo="cpf_ausente",
            valor_bruto=linha.get(COL_NOME), detalhe="Linha sem CPF - não é possível deduplicar nem identificar o atleta.",
        ))
        return None

    carimbo = _parse_carimbo(linha.get(COL_CARIMBO))
    if carimbo is None:
        relatorio.erros_parsing += 1
        session.add(LogErroParsing(
            modalidade_id=modalidade.id, tipo="carimbo_invalido",
            valor_bruto=linha.get(COL_CARIMBO), detalhe=f"CPF {cpf}: carimbo de data/hora não reconhecido.",
        ))
        return None

    turma = parse_turma(linha.get(COL_TURMA, ""), slug)
    for aviso in turma.avisos:
        relatorio.erros_parsing += 1
        session.add(LogErroParsing(
            modalidade_id=modalidade.id, tipo="turma_nao_parseada",
            valor_bruto=linha.get(COL_TURMA), detalhe=f"CPF {cpf}: {aviso}",
        ))

    local = _resolve_local(slug, turma.local_raw, locais_mapping, locais_oficiais)
    if local is None and turma.local_raw:
        relatorio.erros_parsing += 1
        session.add(LogErroParsing(
            modalidade_id=modalidade.id, tipo="local_nao_mapeado",
            valor_bruto=turma.local_raw,
            detalhe=f"CPF {cpf}: local não encontrado em 'Locais - Contatos' nem em config/locais_mapping.yaml.",
        ))

    return {
        "cpf": cpf,
        "carimbo_data_hora": carimbo,
        "nome_completo": linha.get(COL_NOME),
        "data_nascimento": linha.get(COL_NASCIMENTO),
        "sexo": linha.get(COL_SEXO),
        "bairro": linha.get(COL_BAIRRO),
        "cidade": linha.get(COL_CIDADE),
        "estado": linha.get(COL_ESTADO),
        "telefone": linha.get(COL_TELEFONE),
        "nome_responsavel": linha.get(COL_NOME_RESPONSAVEL),
        "telefone_responsavel": linha.get(COL_TELEFONE_RESPONSAVEL),
        "email": linha.get(COL_EMAIL),
        "recebe_beneficio_social": _normaliza_nome(linha.get(COL_BENEFICIO, "")) == "SIM",
        "escolaridade": linha.get(COL_ESCOLARIDADE),
        "modelo_ensino": linha.get(COL_MODELO_ENSINO),
        "turno_estudo": linha.get(COL_TURNO_ESTUDO),
        "turma_raw_text": linha.get(COL_TURMA),
        "local_raw_text": turma.local_raw,
        "local_id": local.id if local else None,
        "dias_semana": turma.dias_semana,
        "turno": turma.turno,
        "faixa_etaria_min": turma.faixa_etaria_min,
        "faixa_etaria_max": turma.faixa_etaria_max,
        "horario_inicio": turma.horario_inicio,
        "horario_fim": turma.horario_fim,
        "termo_autorizacao_raw": _extrai_termo_autorizacao(linha),
    }


def _upsert_atleta(session: Session, dados: dict) -> Atleta:
    atleta = session.query(Atleta).filter_by(cpf=dados["cpf"]).one_or_none()
    if atleta is None:
        atleta = Atleta(cpf=dados["cpf"], nome_completo=dados["nome_completo"])
        session.add(atleta)
        session.flush()
    for campo in (
        "nome_completo", "data_nascimento", "sexo", "bairro", "cidade", "estado",
        "telefone", "nome_responsavel", "telefone_responsavel", "email",
        "recebe_beneficio_social", "escolaridade", "modelo_ensino", "turno_estudo",
    ):
        setattr(atleta, campo, dados[campo])
    return atleta


def _sincroniza_matriculas_modalidade(
    session: Session,
    settings_modalidade,
    modalidade: Modalidade,
    reader: SheetsReader,
    locais_mapping: LocaisMapping,
    relatorio: RelatorioSync,
) -> None:
    locais_oficiais = {_normaliza_nome(l.nome_oficial): l for l in modalidade.locais}

    registros = []
    for linha in reader.ler_primeira_aba(settings_modalidade.sheet_id):
        registro = _trata_linha_matricula(
            linha, settings_modalidade.slug, locais_mapping, locais_oficiais, session, modalidade, relatorio
        )
        if registro is not None:
            registros.append(registro)

    resultado = deduplicar_por_cpf(registros)
    relatorio.matriculas_descartadas += len(resultado.descartados)

    for ativo in resultado.ativos:
        atleta = _upsert_atleta(session, ativo)
        relatorio.atletas_criados_ou_atualizados += 1

        matricula = session.query(Matricula).filter_by(atleta_id=atleta.id, modalidade_id=modalidade.id).one_or_none()
        if matricula is None:
            matricula = Matricula(atleta_id=atleta.id, modalidade_id=modalidade.id)
            session.add(matricula)

        matricula.local_id = ativo["local_id"]
        matricula.turma_raw_text = ativo["turma_raw_text"]
        matricula.local_raw_text = ativo["local_raw_text"]
        matricula.dias_semana = ",".join(ativo["dias_semana"])
        matricula.turno = ativo["turno"]
        matricula.faixa_etaria_min = ativo["faixa_etaria_min"]
        matricula.faixa_etaria_max = ativo["faixa_etaria_max"]
        matricula.horario_inicio = ativo["horario_inicio"]
        matricula.horario_fim = ativo["horario_fim"]
        matricula.carimbo_data_hora = ativo["carimbo_data_hora"]
        matricula.termo_autorizacao_raw = ativo["termo_autorizacao_raw"]
        relatorio.matriculas_ativas += 1

    for descartado in resultado.descartados:
        session.add(MatriculaDescartada(
            modalidade_id=modalidade.id,
            cpf_raw=descartado["cpf"],
            nome_raw=descartado.get("nome_completo"),
            carimbo_data_hora=descartado.get("carimbo_data_hora"),
            turma_raw_text=descartado.get("turma_raw_text"),
            motivo=descartado["motivo"],
        ))


def run_sync(settings: Settings, reader: SheetsReader, session_factory: sessionmaker[Session]) -> RelatorioSync:
    relatorio = RelatorioSync()
    with session_factory() as session:
        modalidade_por_slug = _sincroniza_modalidades(session, settings)
        _sincroniza_locais_e_vagas(session, settings, reader, modalidade_por_slug, relatorio)
        session.expire_all()  # garante que modalidade.locais reflita os locais recém-gravados

        locais_mapping = LocaisMapping.from_yaml(settings.locais_mapping_path)

        for m in settings.modalidades:
            if not m.sheet_id:
                relatorio.avisos.append(f"{m.nome}: sheet_id não configurado - modalidade pulada nesta sincronização.")
                continue
            modalidade = modalidade_por_slug[m.slug]
            _sincroniza_matriculas_modalidade(session, m, modalidade, reader, locais_mapping, relatorio)

        session.commit()
    return relatorio
