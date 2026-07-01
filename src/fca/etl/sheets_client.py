"""Conector com o Google Sheets API.

`SheetsReader` é o contrato que o pipeline (`pipeline.py`) usa para ler
dados - isso permite testar a orquestração inteira do ETL com um reader
falso (dados em memória), sem precisar de credenciais reais. Em produção,
`GspreadSheetsReader` é a implementação real, usada pelo `scripts/sync.py`.

As três planilhas têm formatos diferentes o bastante para precisar de um
método de leitura cada (confirmado nos dados reais da FCA):
  - Vagas: 4 colunas + colunas extras com cabeçalho vazio -> lida por posição.
  - Locais: título mesclado na linha 1, cabeçalho real na linha 2.
  - Matrícula: cabeçalho tem "NOME COMPLETO" duplicado (atleta e
    responsável) -> lida por posição, ignorando o texto do cabeçalho real.
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from fca.etl.columns import COLUNAS_MATRICULA_EM_ORDEM, COLUNAS_VAGAS_EM_ORDEM


class SheetsReader(Protocol):
    def ler_vagas(self, sheet_id: str) -> list[dict]:
        """Lê a planilha de Vagas (primeira aba, por posição de coluna)."""

    def ler_locais(self, sheet_id: str) -> list[dict]:
        """Lê a planilha de Modalidades/Locais (cabeçalho na linha 2)."""

    def ler_matricula(self, sheet_id: str) -> list[dict]:
        """Lê uma planilha de matrícula (primeira aba, por posição de coluna)."""


SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
]


def _linhas_por_posicao(valores: list[list[str]], colunas: list[str]) -> list[dict]:
    linhas_de_dados = valores[1:]  # descarta o cabeçalho real (não confiável)
    return [
        dict(zip(colunas, linha))
        for linha in linhas_de_dados
        if any(celula.strip() for celula in linha)
    ]


class GspreadSheetsReader:
    """Implementação real via gspread. Requer o pacote `gspread` instalado
    e um arquivo JSON de Service Account com acesso de leitura às planilhas
    (a planilha precisa estar compartilhada com o e-mail da service account).
    """

    def __init__(self, service_account_file: str | Path):
        import gspread
        from google.oauth2.service_account import Credentials

        credenciais = Credentials.from_service_account_file(str(service_account_file), scopes=SCOPES)
        self._client = gspread.authorize(credenciais)

    def ler_vagas(self, sheet_id: str) -> list[dict]:
        valores = self._client.open_by_key(sheet_id).sheet1.get_values()
        return _linhas_por_posicao(valores, COLUNAS_VAGAS_EM_ORDEM)

    def ler_locais(self, sheet_id: str) -> list[dict]:
        return self._client.open_by_key(sheet_id).sheet1.get_all_records(head=2)

    def ler_matricula(self, sheet_id: str) -> list[dict]:
        valores = self._client.open_by_key(sheet_id).sheet1.get_values()
        return _linhas_por_posicao(valores, COLUNAS_MATRICULA_EM_ORDEM)
