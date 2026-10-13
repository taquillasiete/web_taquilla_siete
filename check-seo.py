#!/usr/bin/env python3
"""
Comprueba que todas las páginas HTML del sitio llevan lo básico de SEO/analítica
(GoatCounter, canonical, Open Graph, Twitter Card, JSON-LD Organization, mención
de "Madrid") y que el sitemap.xml está sincronizado con los ficheros reales.

Uso: python check-seo.py
Sale con código 1 si algo falta, para poder usarlo antes de hacer commit/push.
"""
import re
import sys
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).parent
SKIP = {"_template.html", "plantilla.html"}
MAX_IMAGE_BYTES = 300_000
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}

CHECKS = [
    ("GoatCounter", r'data-goatcounter="https://taquillasiete\.goatcounter\.com/count"'),
    ("Canonical", r'<link rel="canonical" href="https://taquillasiete\.com/[^"]*">'),
    ("Open Graph (og:title)", r'<meta property="og:title"'),
    ("Open Graph (og:description)", r'<meta property="og:description"'),
    ("Open Graph (og:image)", r'<meta property="og:image"'),
    ("Twitter Card", r'<meta name="twitter:card"'),
    ("JSON-LD Organization", r'"@type":\s*"Organization"'),
]

def check_file(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    problems = []
    for label, pattern in CHECKS:
        if not re.search(pattern, text):
            problems.append(f"falta {label}")
    if "Madrid" not in text:
        problems.append('no menciona "Madrid" en el contenido')
    for m in re.finditer(r"<img\b[^>]*>", text):
        if "alt=" not in m.group(0):
            problems.append(f"imagen sin alt: {m.group(0)[:60]}...")
    return problems

def main() -> int:
    # Las páginas de redirección (meta refresh, p. ej. criticas.html) no son contenido real
    # Incluye subcarpetas (miradas/, eventos/, actualidad/...), sin carpetas ocultas como .git
    html_files = sorted(
        p for p in ROOT.rglob("*.html")
        if p.name not in SKIP
        and not any(part.startswith(".") for part in p.relative_to(ROOT).parts)
        and 'http-equiv="refresh"' not in p.read_text(encoding="utf-8")
    )
    sitemap_text = (ROOT / "sitemap.xml").read_text(encoding="utf-8") if (ROOT / "sitemap.xml").exists() else ""
    sitemap_locs = set(re.findall(r"<loc>(.*?)</loc>", sitemap_text))

    ok = True
    print(f"Revisando {len(html_files)} páginas HTML...\n")

    for f in html_files:
        problems = check_file(f)

        rel = f.relative_to(ROOT).as_posix()
        expected_loc = "https://taquillasiete.com/" if rel == "index.html" else f"https://taquillasiete.com/{rel}"
        if f'<link rel="canonical" href="{expected_loc}">' not in f.read_text(encoding="utf-8"):
            problems.append(f"el canonical no coincide con su URL ({expected_loc})")
        oculta = '<meta name="robots" content="noindex">' in f.read_text(encoding="utf-8")
        if oculta and expected_loc in sitemap_locs:
            problems.append("es una página oculta (noindex) y no debe estar en sitemap.xml")
        elif not oculta and expected_loc not in sitemap_locs:
            problems.append(f"no está en sitemap.xml (falta {expected_loc})")

        if problems:
            ok = False
            print(f"[FALTA ALGO] {rel}")
            for p in problems:
                print(f"   - {p}")
        else:
            print(f"[OK] {rel}" + ("  (oculta: noindex, fuera del sitemap)" if oculta else ""))

    known_files = {f.relative_to(ROOT).as_posix() for f in html_files} | {"index.html"}
    for loc in sitemap_locs:
        name = loc.removeprefix("https://taquillasiete.com/") or "index.html"
        if name not in known_files:
            ok = False
            print(f"[SITEMAP HUÉRFANO] {loc} no corresponde a ningún fichero HTML existente")

    heavy_images = [
        p for p in (ROOT / "assets").rglob("*")
        if p.suffix.lower() in IMAGE_EXTENSIONS and p.stat().st_size > MAX_IMAGE_BYTES
    ]
    if heavy_images:
        ok = False
        print("\n[IMÁGENES PESADAS] (afectan a la velocidad de carga y al SEO)")
        for p in sorted(heavy_images):
            kb = p.stat().st_size // 1024
            print(f"   - {p.relative_to(ROOT)} ({kb} KB) — comprime a WebP, p. ej. con Pillow o squoosh.app")

    print()
    if ok:
        print("Todo en orden.")
        return 0
    else:
        print("Hay cosas pendientes — revisa la lista de arriba antes de hacer commit/push.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
