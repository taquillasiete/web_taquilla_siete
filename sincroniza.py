#!/usr/bin/env python3
"""
Copia a todas las páginas los bloques que son iguales en todo el sitio, para no
editarlos a mano página por página:
  - Cabecera (header.site-header), pie (footer.site-footer) y JSON-LD Organization:
    la fuente es _template.html. Las rutas se ajustan solas: "../" en subcarpetas,
    "/" en 404.html (se sirve en cualquier ruta) y "#ancla" en la portada.
  - ?v= de css/style.css y js/main.js: un hash del contenido del fichero, así
    cambia solo cuando cambia el fichero y nunca hay que subirlo a mano.
  - JSON-LD FAQPage de preguntas-frecuentes.html: se genera desde el texto visible
    (<summary> y .faq-respuesta) para que nunca diga algo distinto.

Uso: python sincroniza.py              -> aplica los cambios
     python sincroniza.py --comprobar  -> solo dice qué páginas están desfasadas (lo usa check-seo.py)
"""
import hashlib
import html
import json
import re
import sys
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).parent
TEMPLATE = ROOT / "_template.html"
FAQ = ROOT / "preguntas-frecuentes.html"

BLOQUES = {
    "cabecera": r'<header class="site-header">.*?</header>',
    "pie": r'<footer class="site-footer">.*?</footer>',
    "Organization": r'<script type="application/ld\+json">\n\{\n  "@context": "https://schema\.org",\n  "@type": "Organization",.*?</script>',
}
JSONLD_FAQ = r'(<script type="application/ld\+json">\n)(\{\n  "@context": "https://schema\.org",\n  "@type": "FAQPage",.*?)(</script>)'


def paginas() -> list[Path]:
    """Todas las páginas reales: sin carpetas ocultas, sin la plantilla raíz y sin redirecciones."""
    return sorted(
        p for p in ROOT.rglob("*.html")
        if p != TEMPLATE
        and not any(part.startswith(".") for part in p.relative_to(ROOT).parts)
        and 'http-equiv="refresh"' not in p.read_text(encoding="utf-8")
    )


def modo(pagina: Path) -> str:
    rel = pagina.relative_to(ROOT).as_posix()
    if rel == "404.html":
        return "absoluta"
    if rel == "index.html":
        return "portada"
    return "subcarpeta" if "/" in rel else "raiz"


def ajusta_rutas(fragmento: str, m: str) -> str:
    def ruta(match: re.Match) -> str:
        attr, v = match.group(1), match.group(2)
        if re.match(r"(https?:|//|/|#|mailto:|data:)", v):
            return match.group(0)
        if m == "portada":
            v = v.removeprefix("./") if v.startswith("./#") else v
        elif m == "subcarpeta":
            v = "../" + v.removeprefix("./")
        elif m == "absoluta":
            v = "/" + v.removeprefix("./")
        return f'{attr}="{v}"'
    return re.sub(r'\b(href|src)="([^"]*)"', ruta, fragmento)


def version(fichero: str) -> str:
    return hashlib.sha1((ROOT / fichero).read_bytes()).hexdigest()[:8]


def texto_plano(fragmento: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", fragmento))).strip()


def faq_jsonld(texto: str) -> str:
    preguntas = re.findall(r'<summary>(.*?)</summary>\s*<div class="faq-respuesta">(.*?)</div>\s*</details>', texto, re.S)
    datos = {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {"@type": "Question", "name": texto_plano(p),
             "acceptedAnswer": {"@type": "Answer", "text": texto_plano(r)}}
            for p, r in preguntas
        ],
    }
    return json.dumps(datos, ensure_ascii=False, indent=2) + "\n"


def sincroniza(pagina: Path, plantilla: str, versiones: dict[str, str]) -> tuple[str, list[str]]:
    """Devuelve el texto nuevo de la página y la lista de bloques que han cambiado."""
    texto = pagina.read_text(encoding="utf-8")
    nuevo, cambios = texto, []
    m = modo(pagina)

    for nombre, patron in BLOQUES.items():
        fuente = re.search(patron, plantilla, re.S)
        actual = re.search(patron, nuevo, re.S)
        if not fuente or not actual:
            continue  # páginas sin ese bloque (p. ej. sin cabecera) se respetan
        bloque = ajusta_rutas(fuente.group(0), m) if nombre != "Organization" else fuente.group(0)
        if actual.group(0) != bloque:
            nuevo = nuevo[:actual.start()] + bloque + nuevo[actual.end():]
            cambios.append(nombre)

    for fichero, v in versiones.items():
        con_version = re.sub(rf"({re.escape(fichero)})\?v=[^\"']*", rf"\1?v={v}", nuevo)
        if con_version != nuevo:
            nuevo = con_version
            cambios.append(f"{fichero}?v")

    if pagina == FAQ:
        con_faq = re.sub(JSONLD_FAQ, lambda x: x.group(1) + faq_jsonld(nuevo) + x.group(3), nuevo, flags=re.S)
        if con_faq != nuevo:
            nuevo = con_faq
            cambios.append("JSON-LD FAQPage")

    return nuevo, cambios


def desfasadas() -> dict[str, list[str]]:
    """Páginas (incluida la plantilla, por el ?v) cuyo contenido cambiaría al sincronizar."""
    plantilla = TEMPLATE.read_text(encoding="utf-8")
    versiones = {f: version(f) for f in ("css/style.css", "js/main.js")}
    salida = {}
    for p in [TEMPLATE, *paginas()]:
        _, cambios = sincroniza(p, plantilla, versiones)
        if cambios:
            salida[p.relative_to(ROOT).as_posix()] = cambios
    return salida


def main() -> int:
    comprobar = sys.argv[1:] == ["--comprobar"]
    pendientes = desfasadas()
    if not pendientes:
        print("Todas las páginas están sincronizadas.")
        return 0
    if comprobar:
        for rel, cambios in pendientes.items():
            print(f"[DESFASADA] {rel}: {', '.join(cambios)}")
        print("Ejecuta: python sincroniza.py")
        return 1

    plantilla = TEMPLATE.read_text(encoding="utf-8")
    versiones = {f: version(f) for f in ("css/style.css", "js/main.js")}
    for rel in pendientes:
        p = ROOT / rel
        nuevo, cambios = sincroniza(p, plantilla, versiones)
        p.write_text(nuevo, encoding="utf-8", newline="\n")
        print(f"[ACTUALIZADA] {rel}: {', '.join(cambios)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
