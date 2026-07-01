#!/usr/bin/env python3
"""Entrada alternativa para o dashboard - use no lugar de `streamlit run`
direto se o dashboard travar com "segmentation fault" logo ao abrir no
navegador (visto em macOS 11 + pyarrow: o Arrow tem um bug conhecido de
não ser thread-safe quando carregado pela primeira vez fora da thread
principal, e o Streamlit executa o script do app numa thread separada por
sessão). Importar o pyarrow aqui, antes do Streamlit iniciar, garante que
a inicialização nativa aconteça na thread principal - as demais threads
só reaproveitam o módulo já carregado.

Uso: python3 scripts/run_dashboard.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pyarrow  # noqa: F401  (import proposital - ver docstring acima)

from streamlit.web import cli as stcli

if __name__ == "__main__":
    app_path = Path(__file__).resolve().parents[1] / "src" / "fca" / "dashboard" / "app.py"
    sys.argv = ["streamlit", "run", str(app_path), *sys.argv[1:]]
    sys.exit(stcli.main())
