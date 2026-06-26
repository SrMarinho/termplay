"""Generate UNO card assets for termplay web frontend.

Outputs:
  assets/cards/         — SVG card faces (54 unique types)
  assets/cards/back.svg — Card back
  assets/logo.svg       — termplay wordmark
  assets/favicon.svg    — Favicon (32x32)
  assets/canva_bulk.csv — Bulk Create CSV for polishing in Canva
"""

from __future__ import annotations

import csv
from pathlib import Path

# ── palette ──────────────────────────────────────────────────────────────────

COLORS: dict[str, tuple[str, str]] = {
    "R": ("#e63946", "#fff"),
    "G": ("#2a9d8f", "#fff"),
    "B": ("#457b9d", "#fff"),
    "Y": ("#e9c46a", "#1a1a1a"),
}
WILD_BG = "#1e2030"
WILD_STRIPES = ["#e63946", "#2a9d8f", "#457b9d", "#e9c46a"]

VALUES: dict[str, str] = {
    **{str(n): str(n) for n in range(10)},
    "skip": "⊘",
    "reverse": "⇄",
    "draw2": "+2",
    "wild": "WILD",
    "wild4": "+4",
}

COLOR_VALUES = [str(n) for n in range(10)] + ["skip", "reverse", "draw2"]
WILD_VALUES = ["wild", "wild4"]

# Card dimensions
W, H, R = 70, 100, 8          # width, height, corner-radius
CX, CY = W // 2, H // 2


# ── SVG helpers ───────────────────────────────────────────────────────────────

def _card_shell(bg: str, extra_defs: str = "") -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
        f'viewBox="0 0 {W} {H}">'
        f"<defs><clipPath id='clip'>"
        f"<rect width='{W}' height='{H}' rx='{R}'/>"
        f"</clipPath>{extra_defs}</defs>"
        f"<rect width='{W}' height='{H}' rx='{R}' fill='{bg}'/>"
    )


def _oval(fill: str, stroke: str) -> str:
    return (
        f"<ellipse cx='{CX}' cy='{CY}' rx='22' ry='32' "
        f"fill='{fill}' stroke='{stroke}' stroke-width='2'/>"
    )


def _label(text: str, color: str, size: int = 20) -> str:
    return (
        f"<text x='{CX}' y='{CY}' text-anchor='middle' dominant-baseline='central' "
        f"font-family='system-ui,sans-serif' font-weight='700' "
        f"font-size='{size}' fill='{color}'>{text}</text>"
    )


def _corner(text: str, color: str, size: int = 9) -> str:
    return (
        f"<text x='5' y='12' font-family='system-ui,sans-serif' "
        f"font-weight='700' font-size='{size}' fill='{color}'>{text}</text>"
        f"<text x='{W-5}' y='{H-4}' text-anchor='end' "
        f"font-family='system-ui,sans-serif' font-weight='700' "
        f"font-size='{size}' fill='{color}' transform='rotate(180,{W//2},{H//2})'>"
        f"{text}</text>"
    )


def _border(color: str, width: int = 3) -> str:
    return (
        f"<rect x='{width/2}' y='{width/2}' "
        f"width='{W-width}' height='{H-width}' "
        f"rx='{R-1}' fill='none' stroke='{color}' stroke-width='{width}'/>"
    )


# ── card generators ───────────────────────────────────────────────────────────

def color_card_svg(color: str, value: str) -> str:
    bg, ink = COLORS[color]
    label = VALUES[value]
    corner_label = label if len(label) <= 3 else label[:3]
    svg = _card_shell(bg)
    svg += _border("#ffffff44")
    svg += _oval("#ffffff33", "#ffffff55")
    svg += _label(label, ink)
    svg += _corner(corner_label, ink)
    svg += "</svg>"
    return svg


def wild_card_svg(value: str) -> str:
    label = VALUES[value]
    stripes = "".join(
        f"<rect x='{i*(W//4)}' y='0' width='{W//4}' height='{H}' "
        f"fill='{c}' clip-path='url(#clip)'/>"
        for i, c in enumerate(WILD_STRIPES)
    )
    svg = _card_shell(WILD_BG)
    svg += stripes
    svg += f"<rect width='{W}' height='{H}' rx='{R}' fill='#00000066'/>"
    svg += _border("#ffffff88")
    svg += _oval(WILD_BG, "#ffffff88")
    svg += _label(label, "#fff", size=14 if label == "WILD" else 20)
    svg += _corner("W", "#fff")
    svg += "</svg>"
    return svg


def back_svg() -> str:
    svg = _card_shell("#1b1d23")
    svg += _border("#3a3f4b", 3)
    # diagonal stripe pattern
    svg += (
        "<pattern id='p' width='10' height='10' patternUnits='userSpaceOnUse' "
        "patternTransform='rotate(45)'>"
        "<line x1='0' y1='0' x2='0' y2='10' stroke='#2a2d38' stroke-width='6'/>"
        "</pattern>"
        f"<rect width='{W}' height='{H}' rx='{R}' fill='url(#p)'/>"
    )
    svg += (
        f"<text x='{CX}' y='{CY-6}' text-anchor='middle' dominant-baseline='central' "
        f"font-family='system-ui,sans-serif' font-weight='900' font-size='13' "
        f"fill='#e9c46a' letter-spacing='1'>term</text>"
        f"<text x='{CX}' y='{CY+8}' text-anchor='middle' dominant-baseline='central' "
        f"font-family='system-ui,sans-serif' font-weight='900' font-size='13' "
        f"fill='#457b9d' letter-spacing='1'>play</text>"
    )
    svg += "</svg>"
    return svg


def logo_svg() -> str:
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" width="200" height="48" viewBox="0 0 200 48">'
        '<text x="0" y="36" font-family="system-ui,sans-serif" font-weight="900" '
        'font-size="36" fill="#e9c46a" letter-spacing="-1">term</text>'
        '<text x="88" y="36" font-family="system-ui,sans-serif" font-weight="900" '
        'font-size="36" fill="#457b9d" letter-spacing="-1">play</text>'
        "</svg>"
    )


def favicon_svg() -> str:
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 32 32">'
        '<rect width="32" height="32" rx="6" fill="#1b1d23"/>'
        '<text x="16" y="13" text-anchor="middle" dominant-baseline="central" '
        'font-family="system-ui,sans-serif" font-weight="900" font-size="11" '
        'fill="#e9c46a">tp</text>'
        '<text x="16" y="25" text-anchor="middle" dominant-baseline="central" '
        'font-family="system-ui,sans-serif" font-weight="900" font-size="9" '
        'fill="#457b9d">UNO</text>'
        "</svg>"
    )


# ── CSV for Canva Bulk Create ─────────────────────────────────────────────────

def _canva_csv_rows() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for color, (bg, ink) in COLORS.items():
        for value in COLOR_VALUES:
            rows.append({
                "CardID": f"{color}_{value}",
                "Color": color,
                "Value": value,
                "Label": VALUES[value],
                "Background": bg,
                "TextColor": ink,
                "Type": "color",
                "Width": "70",
                "Height": "100",
            })
    for value in WILD_VALUES:
        rows.append({
            "CardID": f"W_{value}",
            "Color": "W",
            "Value": value,
            "Label": VALUES[value],
            "Background": WILD_BG,
            "TextColor": "#ffffff",
            "Type": "wild",
            "Width": "70",
            "Height": "100",
        })
    return rows


# ── main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    root = Path(__file__).parent.parent / "assets"
    cards_dir = root / "cards"
    cards_dir.mkdir(parents=True, exist_ok=True)

    generated = 0

    # Color cards
    for color in COLORS:
        for value in COLOR_VALUES:
            path = cards_dir / f"{color}_{value}.svg"
            path.write_text(color_card_svg(color, value), encoding="utf-8")
            generated += 1

    # Wild cards
    for value in WILD_VALUES:
        path = cards_dir / f"W_{value}.svg"
        path.write_text(wild_card_svg(value), encoding="utf-8")
        generated += 1

    # Card back
    (cards_dir / "back.svg").write_text(back_svg(), encoding="utf-8")
    generated += 1

    # Logo + favicon
    (root / "logo.svg").write_text(logo_svg(), encoding="utf-8")
    (root / "favicon.svg").write_text(favicon_svg(), encoding="utf-8")
    generated += 2

    # Canva Bulk Create CSV
    csv_path = root / "canva_bulk.csv"
    rows = _canva_csv_rows()
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    print(f"Generated {generated} SVG assets -> {root}/")
    print(f"Canva Bulk Create CSV -> {csv_path}  ({len(rows)} cards)")
    print()
    print("Canva Bulk Create steps:")
    print("  1. Create a new design (70×100mm or 210×300px)")
    print("  2. Design one card template with placeholders:")
    print("     - Background fill -> connect to 'Background' column")
    print("     - Center label text -> connect to 'Label' column")
    print("     - Card ID (small) -> connect to 'CardID' column")
    print("  3. Apps -> Bulk Create -> upload canva_bulk.csv")
    print("  4. Map CSV columns to template elements")
    print("  5. Generate All -> Download as PNG (transparent bg if possible)")
    print("  6. Place exported PNGs into assets/cards/ replacing SVGs")
    print()
    print("To use SVG cards directly in the web client, add to style.css:")
    print("  .card { background-image: url('../assets/cards/R_7.svg'); }")


if __name__ == "__main__":
    main()
