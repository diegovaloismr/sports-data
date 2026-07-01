"""Resolve o de-para de locais (config/locais_mapping.yaml).

Liga o nome do local como ele sai do parser de turma (`turma_parser.py`)
ao nome oficial cadastrado na aba "Locais - Contatos" da planilha mestre.
O YAML é a fonte editável pelo usuário; esse módulo só lê e resolve.
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml


def _normaliza(texto: str) -> str:
    return re.sub(r"\s+", " ", texto.strip().upper())


class LocaisMapping:
    def __init__(self, aliases_por_modalidade: dict[str, dict[str, str]]):
        # modalidade_slug -> {alias_normalizado: nome_oficial}
        self._aliases = aliases_por_modalidade

    @classmethod
    def from_yaml(cls, path: str | Path) -> "LocaisMapping":
        with open(path, encoding="utf-8") as f:
            bruto = yaml.safe_load(f) or {}

        aliases: dict[str, dict[str, str]] = {}
        for slug, config in (bruto.get("modalidades") or {}).items():
            mapa_modalidade: dict[str, str] = {}
            for entrada in config.get("aliases") or []:
                mapa_modalidade[_normaliza(entrada["alias"])] = entrada["oficial"]
            aliases[slug] = mapa_modalidade
        return cls(aliases)

    def resolver(self, modalidade_slug: str, local_raw: str) -> str | None:
        """Retorna o nome oficial do local, ou None se não houver mapeamento.

        Também trata o caso em que `local_raw` já é exatamente o nome
        oficial (nenhum alias necessário).
        """
        mapa_modalidade = self._aliases.get(modalidade_slug, {})
        chave = _normaliza(local_raw)
        if chave in mapa_modalidade:
            return mapa_modalidade[chave]
        # já pode ser o nome oficial - resolução final de igualdade exata
        # contra os nomes oficiais fica a cargo de quem carregou os locais
        # da planilha mestre (pipeline.py), que tem a lista completa.
        return None
