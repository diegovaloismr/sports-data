"""Conector com o Google Sheets API.

`SheetsReader` é o contrato que o pipeline (`pipeline.py`) usa para ler
dados - isso permite testar a orquestração inteira do ETL com um reader
falso (dados em memória), sem precisar de credenciais reais. Em produção,
`GspreadSheetsReader` é a implementação real, usada pelo `scripts/sync.py`.
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol


class SheetsReader(Protocol):
    def ler_aba(self, sheet_id: str, aba_nome: str) -> list[dict]:
        """Lê uma aba específica pelo nome (usado na planilha mestre)."""

    def ler_primeira_aba(self, sheet_id: str) -> list[dict]:
        """Lê a primeira aba da planilha (usado nas planilhas de matrícula,
        que o Google Forms cria com uma única aba de respostas)."""


SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
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

    def ler_aba(self, sheet_id: str, aba_nome: str) -> list[dict]:
        planilha = self._client.open_by_key(sheet_id)
        aba = planilha.worksheet(aba_nome)
        return aba.get_all_records()

    def ler_primeira_aba(self, sheet_id: str) -> list[dict]:
        planilha = self._client.open_by_key(sheet_id)
        return planilha.sheet1.get_all_records()
