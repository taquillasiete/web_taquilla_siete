#!/usr/bin/env python3
"""
Avisa a Bing (y al resto de buscadores con IndexNow) de las páginas que han
cambiado, para que las rastreen en minutos. Google no usa IndexNow.

Uso, después de hacer push y de que GitHub Pages haya desplegado (1-2 min):
  python indexnow.py              -> páginas HTML cambiadas en el último commit
  python indexnow.py --todas      -> todas las URLs del sitemap.xml
  python indexnow.py ruta.html .. -> páginas concretas

La clave es el fichero <clave>.txt de la raíz del repo; no lo borres ni lo renombres.
"""
import json
import re
import subprocess
import sys
import urllib.request
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).parent
HOST = "taquillasiete.com"
BASE = f"https://{HOST}/"
SKIP = {"_template.html", "plantilla.html"}


def url_de(rel: str) -> str:
    return BASE if rel == "index.html" else BASE + rel.removesuffix(".html")


def main() -> int:
    claves = [p for p in ROOT.glob("*.txt") if re.fullmatch(r"[0-9a-f]{32}", p.stem)]
    if len(claves) != 1:
        print("No encuentro un único fichero de clave <32 hex>.txt en la raíz.")
        return 1
    clave = claves[0].stem

    args = sys.argv[1:]
    if args == ["--todas"]:
        sitemap = (ROOT / "sitemap.xml").read_text(encoding="utf-8")
        urls = re.findall(r"<loc>(.*?)</loc>", sitemap)
    elif args:
        urls = [url_de(a.replace("\\", "/").lstrip("./")) for a in args]
    else:
        cambiados = subprocess.run(
            ["git", "diff", "--name-only", "HEAD~1", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True
        ).stdout.split()
        urls = [
            url_de(f) for f in cambiados
            if f.endswith(".html") and Path(f).name not in SKIP and (ROOT / f).exists()
            and 'content="noindex"' not in (ROOT / f).read_text(encoding="utf-8")  # páginas ocultas
        ]

    if not urls:
        print("No hay páginas que avisar.")
        return 0

    payload = {"host": HOST, "key": clave, "keyLocation": f"{BASE}{clave}.txt", "urlList": urls}
    req = urllib.request.Request(
        "https://api.indexnow.org/indexnow",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json; charset=utf-8"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            estado = resp.status
    except urllib.error.HTTPError as e:
        estado = e.code

    print(f"IndexNow respondió {estado} para {len(urls)} URL(s):")
    for u in urls:
        print(f"   - {u}")
    if estado in (200, 202):
        print("Aviso enviado.")
        return 0
    print("Fallo: 403 = la clave no está publicada o no coincide; 422 = URL fuera del dominio; 429 = demasiados avisos.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
