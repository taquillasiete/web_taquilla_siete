#!/usr/bin/env python3
"""
Pone en cada <url> del sitemap.xml su <lastmod>: la fecha del último commit que
tocó esa página, o la de hoy si tiene cambios aún sin comitear. Google usa
<lastmod> para decidir qué volver a rastrear antes.

Uso: python actualiza-sitemap.py   (antes de hacer commit)
"""
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).parent
SITEMAP = ROOT / "sitemap.xml"
BASE = "https://taquillasiete.com/"


def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, encoding="utf-8", check=True).stdout.strip()


def cambio_real(diff: str) -> bool:
    """False si el diff solo cambia el ?v= del CSS/JS (sincroniza.py lo toca en todas las páginas a la vez)."""
    quita = lambda signo: sorted(
        re.sub(r"\?v=[^\"']*", "", l[1:]).strip() for l in diff.splitlines()
        if l.startswith(signo) and not l.startswith(signo * 3)
    )
    return quita("-") != quita("+")


def lastmod(rel: str) -> str:
    estado = git("status", "--porcelain", "--", rel)
    if estado.startswith("??") or (estado and cambio_real(git("diff", "HEAD", "-U0", "--", rel))):
        return date.today().isoformat()
    for linea in git("log", "--format=%H %cs", "--", rel).splitlines():
        commit, fecha = linea.split()
        if cambio_real(git("show", "--format=", "-U0", commit, "--", rel)):
            return fecha
    return date.today().isoformat()


def main() -> int:
    text = SITEMAP.read_text(encoding="utf-8")

    def update(m: re.Match) -> str:
        loc = m.group(2)
        rel = loc.removeprefix(BASE) + ".html" if loc != BASE else "index.html"
        if not (ROOT / rel).exists():
            print(f"[AVISO] {loc} no corresponde a ningún fichero (revisa con check-seo.py)")
            return m.group(0)
        bloque = re.sub(r"\n\s*<lastmod>.*?</lastmod>", "", m.group(0))
        return bloque.replace("</loc>", f"</loc>\n    <lastmod>{lastmod(rel)}</lastmod>", 1)

    new_text = re.sub(r"(<url>\s*<loc>(.*?)</loc>.*?</url>)", update, text, flags=re.S)
    if new_text != text:
        SITEMAP.write_text(new_text, encoding="utf-8", newline="\n")
        print("sitemap.xml actualizado.")
    else:
        print("sitemap.xml ya estaba al día.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
