"""Parser do campo de texto livre "MARQUE A OPÇÃO DA TURMA E HORÁRIO DESEJADO".

O formato desse campo muda de modalidade para modalidade (ver exemplos no
prompt original do projeto), então o parser é organizado como uma
configuração por modalidade (`MODALIDADE_PARSERS`), não uma função única.
Hoje todas as modalidades usam o mesmo motor de extração baseado em regex
(`_parse_generico`) porque os "tokens" que aparecem no texto - local, dias
da semana, turno, faixa etária, horário - são os mesmos em todas elas, só a
ordem e a pontuação mudam, e o motor genérico já lida com isso. Se uma
modalidade nova tiver um formato realmente diferente (não só reordenado),
registre uma função própria em `MODALIDADE_PARSERS` para aquele slug.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

_DIA_PATTERNS: list[tuple[str, str]] = [
    (r"Segunda(?:s)?(?:-feira)?", "Segunda"),
    (r"Ter[çc]a(?:s)?(?:-feira)?", "Terça"),
    (r"Quarta(?:s)?(?:-feira)?", "Quarta"),
    (r"Quinta(?:s)?(?:-feira)?", "Quinta"),
    (r"Sexta(?:s)?(?:-feira)?", "Sexta"),
    (r"S[áa]bado(?:s)?", "Sábado"),
    (r"Domingo(?:s)?", "Domingo"),
]
_DIA_REGEX = re.compile("|".join(p for p, _ in _DIA_PATTERNS), re.IGNORECASE)
_DIA_CANONICO = {p: canon for p, canon in _DIA_PATTERNS}

_TURNO_REGEX = re.compile(r"Turno\s+d[ao]s?\s*(Manh[ãa]|Tarde|Noite)", re.IGNORECASE)
_PARENTESES_REGEX = re.compile(r"\(([^)]*)\)")
_FAIXA_ETARIA_REGEX = re.compile(r"(\d{1,2})\s*a\s*(\d{1,2})\s*anos", re.IGNORECASE)
_HORARIO_REGEX = re.compile(r"(\d{1,2}:\d{2})h?\s*(?:as|às|-)\s*(\d{1,2}:\d{2})h?", re.IGNORECASE)
_ASPAS_REGEX = re.compile(r'["“”]')


@dataclass
class ParsedTurma:
    local_raw: str
    dias_semana: list[str] = field(default_factory=list)
    turno: str | None = None
    faixa_etaria_min: int | None = None
    faixa_etaria_max: int | None = None
    horario_inicio: str | None = None
    horario_fim: str | None = None
    avisos: list[str] = field(default_factory=list)


def _normaliza_turno(bruto: str) -> str:
    sem_acento = bruto.strip().lower()
    if sem_acento.startswith("manh"):
        return "Manhã"
    if sem_acento.startswith("tarde"):
        return "Tarde"
    return "Noite"


def _extrai_dias(texto: str) -> list[str]:
    encontrados: list[str] = []
    for match in _DIA_REGEX.finditer(texto):
        for pattern, canon in _DIA_PATTERNS:
            if re.fullmatch(pattern, match.group(0), re.IGNORECASE):
                if canon not in encontrados:
                    encontrados.append(canon)
                break
    return encontrados


def _extrai_faixa_etaria(texto: str) -> tuple[int | None, int | None]:
    for grupo in _PARENTESES_REGEX.findall(texto):
        match = _FAIXA_ETARIA_REGEX.search(grupo)
        if match:
            return int(match.group(1)), int(match.group(2))
    return None, None


def _extrai_horario(texto: str) -> tuple[str | None, str | None]:
    match = _HORARIO_REGEX.search(texto)
    if not match:
        return None, None
    return match.group(1), match.group(2)


def _parse_generico(texto: str) -> ParsedTurma:
    texto = (texto or "").strip()
    avisos: list[str] = []

    if ":" not in texto:
        avisos.append("Nenhum ':' encontrado - não foi possível separar o local do restante do texto.")
        return ParsedTurma(local_raw=_ASPAS_REGEX.sub("", texto).strip(), avisos=avisos)

    local_bruto, resto = texto.split(":", 1)
    local_raw = _ASPAS_REGEX.sub("", local_bruto).strip()

    dias = _extrai_dias(resto)
    if not dias:
        avisos.append("Nenhum dia da semana reconhecido no texto da turma.")

    turno_match = _TURNO_REGEX.search(resto)
    turno = _normaliza_turno(turno_match.group(1)) if turno_match else None

    faixa_min, faixa_max = _extrai_faixa_etaria(resto)
    horario_inicio, horario_fim = _extrai_horario(resto)

    return ParsedTurma(
        local_raw=local_raw,
        dias_semana=dias,
        turno=turno,
        faixa_etaria_min=faixa_min,
        faixa_etaria_max=faixa_max,
        horario_inicio=horario_inicio,
        horario_fim=horario_fim,
        avisos=avisos,
    )


# Registro de parsers por modalidade (config, não código duplicado). Uma
# modalidade só precisa de entrada aqui se o formato dela não couber no
# motor genérico acima.
MODALIDADE_PARSERS: dict[str, "callable[[str], ParsedTurma]"] = {}


def parse_turma(texto: str, modalidade_slug: str) -> ParsedTurma:
    parser = MODALIDADE_PARSERS.get(modalidade_slug, _parse_generico)
    return parser(texto)
