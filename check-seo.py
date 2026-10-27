#!/usr/bin/env python3
"""
Comprueba que todas las páginas HTML del sitio llevan lo básico de SEO/analítica
(GoatCounter, canonical, Open Graph, Twitter Card, JSON-LD Organization, mención
de "Madrid") y que el sitemap.xml está sincronizado con los ficheros reales.

Además: que no quede ningún marcador PENDIENTE, que cabecera/pie/Organization/?v
estén sincronizados (sincroniza.py), que cada evento esté como próximo o anterior
según su fecha (en su página y en live.html/rewind.html) y que cada Mirada esté
enlazada en el índice y en las píldoras "otras miradas" de las demás.

Uso: python check-seo.py
Sale con código 1 si algo falta, para poder usarlo antes de hacer commit/push.
"""
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import sincroniza

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
    for m in sorted(set(re.findall(r"PENDIENTE\w*", text))):
        problems.append(f"queda el marcador {m} sin rellenar")
    return problems


def check_eventos() -> list[str]:
    """Un evento pasado (3 h tras su inicio, como en agenda.html) va como anterior: sin entradas ni offers."""
    problems = []
    ahora = datetime.now(timezone.utc)
    for pagina in sorted((ROOT / "eventos").glob("*.html")):
        rel = pagina.relative_to(ROOT).as_posix()
        texto = pagina.read_text(encoding="utf-8")
        evento = next(
            (d for b in re.findall(r'<script type="application/ld\+json">(.*?)</script>', texto, re.S)
             if (d := json.loads(b)).get("@type") in ("Event", "ScreeningEvent")),
            None,
        )
        if not evento:
            problems.append(f"{rel}: no tiene JSON-LD Event/ScreeningEvent")
            continue
        pasado = datetime.fromisoformat(evento["startDate"]) + timedelta(hours=3) < ahora
        if pasado and ("Próximo evento" in texto or "offers" in evento):
            problems.append(f"{rel}: ya ha pasado; pon \"Evento anterior\" y quita el botón de entradas y el offers")
        if not pasado and "Evento anterior" in texto:
            problems.append(f"{rel}: aún no ha pasado y dice \"Evento anterior\"")

        indice = ROOT / ("rewind.html" if pagina.name.startswith("rewind-") else "live.html")
        itexto = indice.read_text(encoding="utf-8")
        enlace = itexto.find(f'href="eventos/{pagina.stem}"')
        anteriores = re.search(r'class="eyebrow">[^<]*anteriores', itexto)
        if enlace == -1:
            problems.append(f"{indice.name}: no enlaza a {rel}")
        elif pasado and (not anteriores or enlace < anteriores.start()):
            problems.append(f"{indice.name}: {pagina.stem} ya ha pasado; muévelo al bloque de anteriores")
        elif not pasado and anteriores and enlace > anteriores.start():
            problems.append(f"{indice.name}: {pagina.stem} aún no ha pasado y está en el bloque de anteriores")
    return problems


def destino(ruta: str, desde: Path) -> Path | None:
    """Fichero al que lleva un enlace interno (URL limpia sin .html, carpeta -> index.html); None si no existe."""
    base = ROOT if ruta.startswith("/") else desde.parent
    p = (base / ruta.lstrip("/")).resolve()
    for candidato in (p, p.with_name(p.name + ".html"), p / "index.html"):
        if candidato.is_file() and candidato.is_relative_to(ROOT.resolve()):
            return candidato
    return None


def check_enlaces(paginas: list[Path]) -> list[str]:
    """Enlaces internos rotos (href/src, URLs absolutas a taquillasiete.com y url() del CSS) y anclas #id que no existen."""
    problems = []
    ids = {}

    def ids_de(p: Path) -> set[str]:
        if p not in ids:
            ids[p] = set(re.findall(r'\bid="([^"]+)"', p.read_text(encoding="utf-8")))
        return ids[p]

    def revisa(valor: str, pagina: Path, rel: str) -> None:
        original = valor
        if valor.startswith("https://taquillasiete.com"):
            valor = valor.removeprefix("https://taquillasiete.com") or "/"
        elif re.match(r"([a-z]+:|//)", valor) or "${" in valor:
            return  # externo, mailto:, tel:, data:... o plantilla JS (agenda.html)
        ruta, _, ancla = valor.split("?")[0].partition("#")
        fichero = destino(ruta, pagina) if ruta else pagina
        if not fichero:
            problems.append(f"{rel}: enlace roto \"{original}\"")
        elif ancla and fichero.suffix == ".html" and ancla not in ids_de(fichero):
            problems.append(f"{rel}: el ancla \"#{ancla}\" no existe en {fichero.relative_to(ROOT.resolve()).as_posix()}")

    for pagina in paginas:
        rel = pagina.relative_to(ROOT).as_posix()
        texto = pagina.read_text(encoding="utf-8")
        valores = re.findall(r'\b(?:href|src)="([^"]*)"', texto)
        valores += re.findall(r'"(https://taquillasiete\.com[^"]*)"', texto)
        for valor in sorted(set(valores)):
            revisa(valor, pagina, rel)

    css = ROOT / "css" / "style.css"
    for valor in sorted(set(re.findall(r'url\("?([^")]+)"?\)', css.read_text(encoding="utf-8")))):
        if not valor.startswith("#"):  # url(#duotono) es un filtro SVG de la propia página
            revisa(valor, css, "css/style.css")
    return problems


def check_miradas() -> list[str]:
    problems = []
    slugs = sorted(p.stem for p in (ROOT / "miradas").glob("*.html"))
    indice = (ROOT / "la-mirada.html").read_text(encoding="utf-8")
    for slug in slugs:
        if f'href="miradas/{slug}"' not in indice:
            problems.append(f"la-mirada.html: falta la mirada {slug} en el índice")
        texto = (ROOT / "miradas" / f"{slug}.html").read_text(encoding="utf-8")
        for otra in slugs:
            if otra != slug and f'href="{otra}"' not in texto:
                problems.append(f"miradas/{slug}.html: falta la píldora \"otras miradas\" a {otra}")
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
        # URLs limpias: sin .html (GitHub Pages sirve /pagina igual que /pagina.html)
        expected_loc = "https://taquillasiete.com/" if rel == "index.html" else f"https://taquillasiete.com/{rel.removesuffix('.html')}"
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
        path = loc.removeprefix("https://taquillasiete.com/")
        name = f"{path}.html" if path else "index.html"
        if name not in known_files:
            ok = False
            print(f"[SITEMAP HUÉRFANO] {loc} no corresponde a ningún fichero HTML existente")

    redirecciones = [p for p in ROOT.glob("*.html") if 'http-equiv="refresh"' in p.read_text(encoding="utf-8")]
    otros = check_eventos() + check_miradas() + check_enlaces(html_files + redirecciones)
    if otros:
        ok = False
        print("\n[EVENTOS / MIRADAS / ENLACES]")
        for p in otros:
            print(f"   - {p}")

    desfasadas = sincroniza.desfasadas()
    if desfasadas:
        ok = False
        print("\n[DESINCRONIZADAS] cabecera, pie, Organization, ?v o FAQ distintos de la fuente — ejecuta python sincroniza.py")
        for rel, cambios in desfasadas.items():
            print(f"   - {rel}: {', '.join(cambios)}")

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
