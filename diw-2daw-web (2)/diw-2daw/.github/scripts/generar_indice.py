#!/usr/bin/env python3
"""
Genera ejemplos.json recorriendo las carpetas del repositorio.

Estructura que reconoce:
  T02-css3-avanzado/                 ← tema   (empieza por T + número)
    C01-efectos-visuales/            ← capítulo (empieza por C + número)
      teoria/*.pdf                   ← apuntes
      ejemplos/01-nombre/index.html  ← cada ejemplo, con su index.html
    ejercicios/*.pdf|*.html          ← ejercicios del tema
  extra/*/                           ← material complementario

El título de cada ejemplo se toma de la etiqueta <title> de su index.html.
Si no tiene, o es genérico ("Document"), se usa el nombre de la carpeta.
"""
import json
import re
from datetime import datetime, timezone
from html import unescape
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
TITULOS_GENERICOS = {"", "document", "documento", "untitled", "sin título", "index"}


def orden(p: Path):
    m = re.match(r"^[A-Za-z]*(\d+)", p.name)
    return (int(m.group(1)) if m else 9999, p.name.lower())


def nombre_bonito(carpeta: str) -> str:
    texto = re.sub(r"^[A-Za-z]?\d+[-_ ]*", "", carpeta)
    texto = texto.replace("-", " ").replace("_", " ").strip()
    texto = re.sub(r"\bia\b", "IA", texto, flags=re.I)
    return texto[:1].upper() + texto[1:] if texto else carpeta


def titulo_html(index: Path, carpeta: str) -> str:
    try:
        html = index.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        html = ""
    m = re.search(r"<title[^>]*>(.*?)</title>", html, re.I | re.S)
    titulo = unescape(re.sub(r"\s+", " ", m.group(1))).strip() if m else ""
    if titulo.lower() in TITULOS_GENERICOS:
        titulo = nombre_bonito(carpeta)
    return titulo


def ruta(p: Path) -> str:
    return p.relative_to(RAIZ).as_posix()


def archivos(carpeta: Path, extensiones=(".pdf",)):
    if not carpeta.is_dir():
        return []
    return [
        {"nombre": f.name, "ruta": ruta(f)}
        for f in sorted(carpeta.iterdir(), key=lambda x: x.name.lower())
        if f.is_file() and f.suffix.lower() in extensiones
    ]


def ejemplos(carpeta: Path):
    if not carpeta.is_dir():
        return []
    lista = []
    for d in sorted((x for x in carpeta.iterdir() if x.is_dir()), key=orden):
        index = d / "index.html"
        if index.is_file():
            lista.append({
                "carpeta": d.name,
                "titulo": titulo_html(index, d.name),
                "ruta": ruta(d) + "/",
            })
    return lista


def main():
    temas = []
    for t in sorted((x for x in RAIZ.iterdir() if x.is_dir() and re.match(r"^T\d+", x.name)), key=orden):
        capitulos = []
        for c in sorted((x for x in t.iterdir() if x.is_dir() and re.match(r"^C\d+", x.name)), key=orden):
            capitulos.append({
                "carpeta": c.name,
                "ruta": ruta(c) + "/",
                "teoria": archivos(c / "teoria"),
                "ejemplos": ejemplos(c / "ejemplos"),
            })
        temas.append({
            "carpeta": t.name,
            "ruta": ruta(t) + "/",
            "capitulos": capitulos,
            "ejercicios": archivos(t / "ejercicios", (".pdf", ".html")),
        })

    extra = []
    carpeta_extra = RAIZ / "extra"
    if carpeta_extra.is_dir():
        for d in sorted((x for x in carpeta_extra.iterdir() if x.is_dir()), key=orden):
            extra.append({
                "carpeta": d.name,
                "titulo": nombre_bonito(d.name),
                "ruta": ruta(d) + "/",
                "tieneIndex": (d / "index.html").is_file(),
                "archivos": archivos(d, (".pdf", ".html")),
            })

    datos = {
        "generado": datetime.now(timezone.utc).isoformat(timespec="minutes"),
        "temas": temas,
        "extra": extra,
    }
    salida = RAIZ / "ejemplos.json"
    salida.write_text(json.dumps(datos, ensure_ascii=False, indent=2), encoding="utf-8")
    total = sum(len(c["ejemplos"]) for t in temas for c in t["capitulos"])
    print(f"ejemplos.json generado: {len(temas)} tema(s), {total} ejemplo(s)")


if __name__ == "__main__":
    main()
