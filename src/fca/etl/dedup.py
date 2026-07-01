"""Deduplicação de matrículas por CPF (reenvio de formulário).

Regra (definida no levantamento com o assessor):
  1. CPF normalizado (só dígitos) é a chave de comparação.
  2. Agrupa por CPF normalizado, dentro da mesma modalidade.
  3. Quando há mais de um registro com o mesmo CPF, mantém o de
     `carimbo_data_hora` mais recente como matrícula ativa; os demais
     viram "matrícula superada" - não são descartados do banco, só
     deixam de contar como ativos (ver MatriculaDescartada em db/models.py).
  4. Não precisa fuzzy match de nome: o CPF normalizado já resolve
     variações de maiúsculas/acentuação no nome.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class ResultadoDedup:
    ativos: list[dict[str, Any]]
    descartados: list[dict[str, Any]]


def deduplicar_por_cpf(
    registros: list[dict[str, Any]],
    *,
    cpf_key: str = "cpf",
    carimbo_key: str = "carimbo_data_hora",
) -> ResultadoDedup:
    """`registros` é a lista de linhas já normalizadas de UMA modalidade.

    Cada dict precisa ter `cpf_key` (CPF normalizado, só dígitos) e
    `carimbo_key` (datetime do envio do formulário).
    """
    por_cpf: dict[str, list[dict[str, Any]]] = {}
    for registro in registros:
        por_cpf.setdefault(registro[cpf_key], []).append(registro)

    ativos: list[dict[str, Any]] = []
    descartados: list[dict[str, Any]] = []

    for cpf, grupo in por_cpf.items():
        grupo_ordenado = sorted(grupo, key=lambda r: r[carimbo_key], reverse=True)
        vencedor, *perdedores = grupo_ordenado
        ativos.append(vencedor)
        for perdedor in perdedores:
            descartados.append(
                {
                    **perdedor,
                    "motivo": "duplicata_cpf_superada",
                    "superado_por_carimbo": vencedor[carimbo_key],
                }
            )

    return ResultadoDedup(ativos=ativos, descartados=descartados)
