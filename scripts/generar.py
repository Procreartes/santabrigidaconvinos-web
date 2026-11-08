#!/usr/bin/env python3
"""Genera index.html de Santa Brígida con Vinos a partir de plantilla.html y de los datos.

Uso:  python3 scripts/generar.py
Datos editables (Gestor de webs del portal o a mano):
  data/edicion.json  · año, fechas, texto y foto de portada, aviso de inscripciones, PDF y correo
  data/eventos.json  · una ficha por actividad, con su cartel
No edites index.html a mano: se sobrescribe. El diseño está en plantilla.html.
"""
import html
import json
import pathlib
import re
import unicodedata

RAIZ = pathlib.Path(__file__).resolve().parent.parent
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
CATEGORIAS = {"cata", "bodega", "noche", "trad", "pro"}
ACCESOS = {"pago", "inscripcion", "libre"}


def datos(nombre, defecto):
    f = RAIZ / "data" / nombre
    try:
        return json.loads(f.read_text(encoding="utf-8")) if f.exists() else defecto
    except (ValueError, OSError):
        return defecto


def esc(t):
    return html.escape(str(t or ""), quote=True)


def slug(t):
    t = unicodedata.normalize("NFKD", str(t)).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", t).strip("-")[:40] or "evento"


def ruta_imagen(r):
    """Cartel: ruta con extensión (img/01-misa.jpg) o ruta base subida desde el Gestor (img/eventos/x → -800.webp)."""
    r = str(r or "").strip().strip("/")
    if not r:
        return ""
    if pathlib.PurePath(r).suffix:
        return r if (RAIZ / r).exists() else ""
    return f"{r}-800.webp" if (RAIZ / f"{r}-800.webp").exists() else ""


def js(v):
    return json.dumps(v, ensure_ascii=False).replace("</", "<\\/")


def main():
    ed = (datos("edicion.json", []) or [{}])[0]
    eventos = []
    for e in sorted(datos("eventos.json", []), key=lambda x: (x.get("fecha") or "", x.get("hora") or "")):
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(e.get("fecha") or "")) or not e.get("titulo"):
            continue
        precio = str(e.get("precio") or "").replace("€", "").replace(",", ".").strip()
        try:
            precio = float(precio) if precio else None
            precio = int(precio) if precio is not None and precio.is_integer() else precio
        except ValueError:
            precio = None
        acceso = e.get("acceso") if e.get("acceso") in ACCESOS else "libre"
        if acceso == "pago" and precio is None:
            acceso = "inscripcion"
        url = str(e.get("url") or "").strip()
        eventos.append({
            "id": slug(e.get("id")) if e.get("id") else f"{len(eventos) + 1:02d}-{slug(e['titulo'])}", "fecha": e["fecha"], "hora": e.get("hora") or "",
            "titulo": e["titulo"], "lugar": e.get("lugar") or "",
            "categoria": e.get("categoria") if e.get("categoria") in CATEGORIAS else "noche",
            "descripcion": e.get("descripcion") or "", "acceso": acceso, "precio": precio,
            "url": url if url.startswith("https://") else "", "imagen": ruta_imagen(e.get("imagen")),
        })

    anio = str(ed.get("anio") or (eventos[0]["fecha"][:4] if eventos else ""))
    mes = MESES[int(eventos[0]["fecha"][5:7]) - 1] if eventos else "noviembre"

    foto = str(ed.get("imagen") or "").strip().strip("/")
    if foto and (RAIZ / f"{foto}-800.webp").exists():
        grande = (RAIZ / f"{foto}-1600.webp").exists()
        srcset = f"{foto}-800.webp 800w" + (f", {foto}-1600.webp 1600w" if grande else "")
        hero = (f'<picture class="hero-bg"><img src="{foto}-{"1600" if grande else "800"}.webp" srcset="{srcset}" sizes="100vw" '
                f'alt="{esc(ed.get("imagen_alt"))}" fetchpriority="high"></picture>')
    else:
        hero = ('<picture class="hero-bg">\n    <source media="(max-width: 700px)" srcset="img/hero-m.jpg">\n'
                '    <img src="img/hero.jpg" alt="" fetchpriority="high">\n  </picture>')

    apertura = str(ed.get("apertura_inscripciones") or "").strip()
    apertura = apertura if re.fullmatch(r"\d{4}-\d{2}-\d{2}", apertura) else ""
    tit = ed.get("aviso_titulo") or (f"Inscripciones a partir del {int(apertura[8:])} de {MESES[int(apertura[5:7]) - 1]}" if apertura else "")
    txt = ed.get("aviso_texto") or "Catas, maridajes y visitas a bodega tienen plazas limitadas. Las actividades de entrada libre no necesitan inscripción."
    aviso_hero = (f'<div class="aviso aviso-hero" id="avisoHero" hidden><span class="ic" aria-hidden="true">{esc(int(apertura[8:]))}</span>'
                  f'<div><b id="avisoHeroTit">{esc(tit)}</b><span>{esc(txt)}</span></div></div>') if apertura else ""
    aviso_agenda = (f'<div class="aviso aviso-agenda" id="avisoAgenda" role="note" hidden><span class="ic" aria-hidden="true">{esc(int(apertura[8:]))}</span>'
                    f'<div><b>{esc(tit)}</b><span>Ese día se activarán aquí los botones para reservar plaza y pagar cada actividad.</span></div></div>') if apertura else ""

    pdf = str(ed.get("programa_pdf") or "").strip()
    s = (RAIZ / "plantilla.html").read_text(encoding="utf-8")
    for k, v in {
        "{{ANIO}}": esc(anio), "{{FECHAS}}": esc(ed.get("fechas") or ""), "{{ENTRADILLA}}": esc(ed.get("entradilla") or ""),
        "{{HERO}}": hero, "{{AVISO_HERO}}": aviso_hero, "{{AVISO_AGENDA}}": aviso_agenda,
        "{{MES}}": mes, "{{MES_MAY}}": mes.capitalize(),
        "/*EVENTOS*/": js(eventos), "/*CORREO*/": js(str(ed.get("correo") or "").strip()),
        "/*PDF*/": js(pdf if pdf.startswith("https://") or pdf.startswith("/") else ""), "/*APERTURA*/": js(apertura),
    }.items():
        s = s.replace(k, v)
    (RAIZ / "index.html").write_text(s, encoding="utf-8")
    print(f"index.html generado con {len(eventos)} actividades ({anio})")


if __name__ == "__main__":
    main()
