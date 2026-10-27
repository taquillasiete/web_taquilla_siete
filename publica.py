#!/usr/bin/env python3
"""
Publica la web en un solo paso:
  1. git pull --rebase --autostash   (el Action de la agenda hace commits solos en main)
  2. sincroniza.py                   (cabecera, pie, Organization, ?v, FAQ)
  3. actualiza-agenda.py             (agenda.json; si falla la red, sigue: el Action lo regenera)
  4. actualiza-sitemap.py            (<lastmod>)
  5. check-seo.py                    (si falla, no se publica nada)
  6. git add -A, commit y push

Después del push no hay que hacer nada: el Action indexnow.yml avisa a Bing cuando
GitHub Pages termina de desplegar.

Uso: python publica.py "Mensaje del commit"
"""
import subprocess
import sys
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).parent


def paso(*cmd: str, obligatorio: bool = True) -> bool:
    print(f"\n$ {' '.join(cmd)}")
    ok = subprocess.run(cmd, cwd=ROOT).returncode == 0
    if not ok and obligatorio:
        print("\nParado: arregla lo de arriba y vuelve a lanzar publica.py.")
        sys.exit(1)
    return ok


def main() -> int:
    if len(sys.argv) < 2 or not sys.argv[1].strip():
        print('Uso: python publica.py "Mensaje del commit"')
        return 1
    mensaje = sys.argv[1]
    py = sys.executable

    paso("git", "pull", "--rebase", "--autostash")
    paso(py, "sincroniza.py")
    if not paso(py, "actualiza-agenda.py", obligatorio=False):
        print("[AVISO] No se pudo regenerar agenda.json; lo hará el Action al hacer push.")
    paso(py, "actualiza-sitemap.py")
    paso(py, "check-seo.py")

    paso("git", "add", "-A")
    if subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=ROOT).returncode == 0:
        print("\nNo hay cambios que publicar.")
        return 0
    cambiados = subprocess.run(["git", "diff", "--cached", "--name-only"], cwd=ROOT,
                               capture_output=True, text=True, encoding="utf-8").stdout.split()
    paso("git", "commit", "-m", mensaje)
    paso("git", "push")

    print("\nPublicado. GitHub Pages tarda 1-2 min; luego el Action indexnow.yml avisa a Bing.")
    if any(f.startswith("eventos/") for f in cambiados):
        print("Has tocado eventos: recuerda publicarlo también en Google Business (Novedad → Evento) y Meetup.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
