#!/usr/bin/env python3
"""
Genera agenda.json, los datos de la página oculta agenda.html (QR para bares):
  - Sesiones: del Google Calendar público del club. Solo los eventos cuyo título
    lleva un año entre paréntesis, p. ej. "Las vírgenes suicidas (1999)"; se
    ignora todo lo demás (Live, Rewind, estrenos, "Club de cine", plazas...).
  - Live y Rewind: de las páginas de eventos de la web (eventos/*.html), leyendo
    su JSON-LD Event/ScreeningEvent.

Uso: python actualiza-agenda.py
Lo ejecuta solo un GitHub Action varias veces al día (.github/workflows/agenda.yml),
y conviene lanzarlo también antes de publicar si se ha tocado eventos/.
Sin dependencias externas.
"""
import json
import re
import sys
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).parent
CAL_ID = "3185436535f193d48b20a9884876d330f09a3f63dbd6de7959a3d1694471df22@group.calendar.google.com"
ICS_URL = f"https://calendar.google.com/calendar/ical/{CAL_ID.replace('@', '%40')}/public/basic.ics"
LUGAR_SESION = "Lolina Vintage Café"
MAX_SESIONES = 3


# ---------- Hora de Madrid (CET/CEST) sin depender de tzdata ----------

def _ultimo_domingo(anio: int, mes: int) -> date:
    d = date(anio, mes + 1, 1) - timedelta(days=1)
    return d - timedelta(days=(d.weekday() + 1) % 7)


def offset_madrid(instante_utc: datetime) -> timedelta:
    """Horario de verano de la UE: del último domingo de marzo al de octubre, a la 01:00 UTC."""
    a = instante_utc.year
    ini = datetime.combine(_ultimo_domingo(a, 3), datetime.min.time(), timezone.utc) + timedelta(hours=1)
    fin = datetime.combine(_ultimo_domingo(a, 10), datetime.min.time(), timezone.utc) + timedelta(hours=1)
    return timedelta(hours=2) if ini <= instante_utc < fin else timedelta(hours=1)


def hora_local(valor: str) -> datetime | None:
    """DTSTART del .ics -> hora de Madrid sin zona ("pared"). None si es de día completo."""
    if "T" not in valor:
        return None
    if valor.endswith("Z"):
        utc = datetime.strptime(valor, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
        return (utc + offset_madrid(utc)).replace(tzinfo=None)
    return datetime.strptime(valor, "%Y%m%dT%H%M%S")  # TZID Europe/Madrid o Brussels: misma hora


# ---------- Sesiones desde el calendario ----------

def sesiones(ahora: datetime) -> list[dict]:
    with urllib.request.urlopen(ICS_URL, timeout=30) as r:
        ics = re.sub(r"\r?\n[ \t]", "", r.read().decode("utf-8"))
    salida = []
    for bloque in re.findall(r"BEGIN:VEVENT(.*?)END:VEVENT", ics, re.S):
        campos = {}
        for linea in bloque.strip().splitlines():
            m = re.match(r"([A-Z-]+)(?:;[^:]*)?:(.*)", linea)
            if m:
                campos[m.group(1)] = m.group(2).replace("\\,", ",").replace("\\;", ";")
        titulo = campos.get("SUMMARY", "").strip()
        if (
            "RRULE" in campos or campos.get("STATUS") == "CANCELLED"
            or not re.search(r"\(\d{4}\)", titulo)
            or re.match(r"(?i)(live|rewind|estreno)\b", titulo)
        ):
            continue
        inicio = hora_local(campos.get("DTSTART", ""))
        if not inicio or inicio + timedelta(hours=3) < ahora:
            continue
        salida.append({"tipo": "sesion", "titulo": titulo, "inicio": inicio.strftime("%Y-%m-%dT%H:%M"),
                       "lugar": LUGAR_SESION})
    salida.sort(key=lambda e: e["inicio"])
    return salida[:MAX_SESIONES]


# ---------- Live y Rewind desde eventos/*.html ----------

def eventos_web(ahora: datetime) -> list[dict]:
    salida = []
    for pagina in sorted((ROOT / "eventos").glob("*.html")):
        texto = pagina.read_text(encoding="utf-8")
        for bloque in re.findall(r'<script type="application/ld\+json">(.*?)</script>', texto, re.S):
            datos = json.loads(bloque)
            if datos.get("@type") not in ("Event", "ScreeningEvent"):
                continue
            tipo = "rewind" if pagina.name.startswith("rewind-") else "live"
            inicio = datetime.fromisoformat(datos["startDate"]).replace(tzinfo=None)
            if inicio + timedelta(hours=3) < ahora:
                continue
            titulo = re.sub(r"^Taquilla Siete (Live|Rewind):\s*", "", datos["name"])
            evento = {"tipo": tipo, "titulo": titulo, "inicio": inicio.strftime("%Y-%m-%dT%H:%M"),
                      "lugar": datos.get("location", {}).get("name", "")}
            calle = datos.get("location", {}).get("address", {}).get("streetAddress")
            if calle:
                evento["lugar"] += f" ({calle})"
            imagen = datos.get("image", "")
            if imagen.startswith("https://taquillasiete.com/"):
                evento["cartel"] = imagen.removeprefix("https://taquillasiete.com/")
            url = datos.get("offers", {}).get("url")
            if url:
                evento["entradas"] = url
            salida.append(evento)
    return salida


def main() -> int:
    utc = datetime.now(timezone.utc)
    ahora = (utc + offset_madrid(utc)).replace(tzinfo=None)
    eventos = sorted(sesiones(ahora) + eventos_web(ahora), key=lambda e: e["inicio"])

    destino = ROOT / "agenda.json"
    anterior = json.loads(destino.read_text(encoding="utf-8")) if destino.exists() else {}
    if anterior.get("eventos") == eventos:
        print("agenda.json ya estaba al día.")
        return 0
    datos = {"actualizado": utc.isoformat(timespec="seconds"), "eventos": eventos}
    destino.write_text(json.dumps(datos, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"agenda.json actualizado ({len(eventos)} actividades):")
    for e in eventos:
        print(f"   {e['inicio']}  {e['tipo']:<7} {e['titulo']}  @ {e['lugar']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
