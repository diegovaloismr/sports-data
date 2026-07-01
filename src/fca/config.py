"""Carrega configuração de src/fca (.env + config/*.yaml) em um objeto único."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import yaml
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parents[2]


@dataclass
class ModalidadeConfig:
    slug: str
    nome: str
    sheet_id: str | None
    aliases: list[str]


@dataclass
class Settings:
    service_account_file: Path
    database_path: Path
    sheet_id_vagas: str | None
    sheet_id_locais: str | None
    modalidades: list[ModalidadeConfig]
    locais_mapping_path: Path


def load_settings(base_dir: Path | None = None) -> Settings:
    base_dir = base_dir or BASE_DIR
    load_dotenv(base_dir / ".env")

    with open(base_dir / "config" / "modalidades.yaml", encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    modalidades = [
        ModalidadeConfig(
            slug=m["slug"],
            nome=m["nome"],
            sheet_id=os.getenv(m["env_sheet_id"]) or None,
            aliases=m.get("aliases") or [],
        )
        for m in raw["modalidades"]
    ]

    return Settings(
        service_account_file=Path(
            os.getenv("FCA_GOOGLE_SERVICE_ACCOUNT_FILE", "./credentials/service_account.json")
        ),
        database_path=Path(os.getenv("FCA_DATABASE_PATH", "./data/fca.db")),
        sheet_id_vagas=os.getenv(raw["planilha_vagas"]["env_sheet_id"]) or None,
        sheet_id_locais=os.getenv(raw["planilha_locais"]["env_sheet_id"]) or None,
        modalidades=modalidades,
        locais_mapping_path=base_dir / "config" / "locais_mapping.yaml",
    )
