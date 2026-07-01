"""Paleta de cores do dashboard.

Valores padrão do design system usado nesta entrega (validados com
`node scripts/validate_palette.js` - CVD ΔE mínimo 24.2, acima do alvo de
12). Para aplicar a identidade visual da FCA depois, troque só os hex
abaixo - o resto do dashboard referencia por papel (slot/status), não por
valor bruto.
"""

from __future__ import annotations

# Uma cor fixa por modalidade - a ordem é a identidade, nunca reordenada
# por valor/ranking (senão a cor de uma modalidade mudaria a cada sync).
CORES_MODALIDADE: dict[str, str] = {
    "natacao": "#2a78d6",     # azul
    "futebol": "#1baf7a",     # água
    "basquete": "#eda100",    # amarelo
    "ginastica": "#008300",   # verde
    "voleibol": "#4a3aa7",    # violeta
    "jiujitsu": "#e34948",    # vermelho
    "tenis": "#e87ba4",       # magenta
    "triathlon": "#eb6834",   # laranja
}

# Status (fixo, nunca usado para identidade de série).
STATUS_BOM = "#0ca30c"
STATUS_ATENCAO = "#fab219"
STATUS_GRAVE = "#ec835a"
STATUS_CRITICO = "#d03b3b"

# Cromia do gráfico (superfície clara).
SUPERFICIE = "#fcfcfb"
TINTA_PRIMARIA = "#0b0b0b"
TINTA_SECUNDARIA = "#52514e"
TINTA_MUTED = "#898781"
GRADE = "#e1e0d9"
BARRA_FUNDO = "#e1e0d9"  # trilho neutro p/ gráficos "ofertado vs preenchido"


def cor_modalidade(slug: str) -> str:
    return CORES_MODALIDADE.get(slug, TINTA_MUTED)


LAYOUT_BASE = {
    "paper_bgcolor": SUPERFICIE,
    "plot_bgcolor": SUPERFICIE,
    "font": {"color": TINTA_PRIMARIA, "family": "system-ui, -apple-system, 'Segoe UI', sans-serif"},
    "margin": {"l": 8, "r": 24, "t": 32, "b": 8},
}
