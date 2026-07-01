"""Normalização e validação de CPF.

Regra do projeto: o CPF normalizado (só dígitos) é a chave usada para
identificar um atleta e para deduplicar matrículas. Formatação de
origem (pontos, traços, espaços) nunca deve ser usada em comparações.
"""

from __future__ import annotations

import re

_NON_DIGIT = re.compile(r"\D+")


def normalize_cpf(raw: str | None) -> str:
    """Remove tudo que não for dígito. Não valida o CPF, só normaliza.

    >>> normalize_cpf("101.671.714-88")
    '10167171488'
    >>> normalize_cpf("10167171488")
    '10167171488'
    """
    if not raw:
        return ""
    return _NON_DIGIT.sub("", raw)


def is_cpf_valido(cpf_normalizado: str) -> bool:
    """Valida os dígitos verificadores do CPF (algoritmo oficial da Receita).

    Usado só para sinalizar qualidade de dado (log_erros_parsing), nunca
    para descartar um atleta - CPF "inválido" ainda precisa aparecer no
    sistema para o assessor corrigir manualmente.
    """
    cpf = cpf_normalizado
    if len(cpf) != 11 or cpf == cpf[0] * 11:
        return False

    def _digito_verificador(parcial: str) -> str:
        pesos = range(len(parcial) + 1, 1, -1)
        soma = sum(int(d) * p for d, p in zip(parcial, pesos))
        resto = (soma * 10) % 11
        return "0" if resto == 10 else str(resto)

    dv1 = _digito_verificador(cpf[:9])
    dv2 = _digito_verificador(cpf[:9] + dv1)
    return cpf[-2:] == dv1 + dv2
