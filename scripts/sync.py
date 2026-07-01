#!/usr/bin/env python3
"""CLI de sincronização: lê as 9 planilhas do Google Sheets e atualiza o
SQLite local (`data/fca.db`).

Uso:
    python scripts/sync.py init-db     # cria as tabelas (primeira vez)
    python scripts/sync.py sync        # roda a sincronização completa
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from fca.config import load_settings  # noqa: E402
from fca.db.session import init_db, make_engine, make_session_factory  # noqa: E402
from fca.etl.pipeline import run_sync  # noqa: E402
from fca.etl.sheets_client import GspreadSheetsReader  # noqa: E402


def cmd_init_db(args: argparse.Namespace) -> None:
    settings = load_settings()
    engine = make_engine(settings.database_path)
    init_db(engine)
    print(f"Banco inicializado em {settings.database_path}")


def cmd_sync(args: argparse.Namespace) -> None:
    settings = load_settings()

    if not settings.service_account_file.exists():
        print(
            f"ERRO: arquivo de credenciais não encontrado em {settings.service_account_file}.\n"
            "Configure FCA_GOOGLE_SERVICE_ACCOUNT_FILE no .env (veja .env.example)."
        )
        raise SystemExit(1)

    sem_sheet_id = (
        [m.nome for m in settings.modalidades if not m.sheet_id]
        + ([] if settings.sheet_id_vagas else ["Planilha Vagas"])
        + ([] if settings.sheet_id_locais else ["Planilha Locais"])
    )
    if sem_sheet_id:
        print(f"Aviso: sem Sheet ID configurado para: {', '.join(sem_sheet_id)}. Serão pulados nesta sincronização.")

    engine = make_engine(settings.database_path)
    init_db(engine)
    session_factory = make_session_factory(engine)
    reader = GspreadSheetsReader(settings.service_account_file)

    relatorio = run_sync(settings, reader, session_factory)

    print("Sincronização concluída:")
    print(f"  Atletas criados/atualizados : {relatorio.atletas_criados_ou_atualizados}")
    print(f"  Matrículas ativas           : {relatorio.matriculas_ativas}")
    print(f"  Matrículas descartadas (dup): {relatorio.matriculas_descartadas}")
    print(f"  Avisos de parsing/mapeamento: {relatorio.erros_parsing}")
    for aviso in relatorio.avisos:
        print(f"  - {aviso}")
    if relatorio.erros_parsing:
        print(
            "\nHá registros com local não mapeado, CPF ausente/inválido ou campo de turma "
            "não reconhecido. Consulte a tabela log_erros_parsing para os detalhes."
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="comando", required=True)

    subparsers.add_parser("init-db", help="Cria as tabelas do banco (primeira vez)").set_defaults(func=cmd_init_db)
    subparsers.add_parser("sync", help="Sincroniza os dados a partir do Google Sheets").set_defaults(func=cmd_sync)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
