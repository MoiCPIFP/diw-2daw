#!/usr/bin/env python3
"""
Genera ejemplos.json recorriendo las carpetas del repositorio.

Estructura que reconoce:
  T02-css3-avanzado/                  ← tema     (empieza por T + número)
    C01-efectos-visuales/             ← capítulo (empieza por C + número)
      teoria/*.pdf                    ← apuntes
      ejemplos/                       ← los ejemplos, de cualquiera de estas formas:
        Cap1-3-4 Degradados.html      ·  archivo .html suelto  → un ejemplo
        Ejemplo Scroll-Video/         ·  carpeta con index.html → un ejemplo
        Ejemplo Parallax/             ·  carpeta sin index.html → cada .html de dentro
        Img/, css/, js/, video/...    ·  carpetas de recursos (se ignoran)
        Enlaces.txt                   ·  las URL que contenga se muestran como referencias
    ejercicios/*.pdf|*.html           ← ejercicios del tema
  extra/*/                            ← material complementario

Nombre de cada ejemplo:
  · El número de apartado sale del nombre del archivo: "Cap1-3-4 ..." → 1.3.4
    (y se agrupa por apartado: 1.3).
  · El título sale del resto del nombre del archivo ("Degradados").
  · Si el archivo no tiene nombre ("Cap2-1-1.html"), se usa la etiqueta <title>.
  · La etiqueta <title> se muestra además como subtítulo si aporta algo.
"""
import json
import re
from datetime import datetime, timezone
from html import unescape
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
TITULOS_GENERICOS = {"", "document", "documento", "documento sin título", "documento sin titulo",
                     "untitled", "sin título", "sin titulo", "index"}
CARPETAS_RECURSOS = {"img", "imgs", "image", "images", "imagen", "imagenes", "imágenes", "css", "js",
                     "script", "scripts", "video", "videos", "vídeos", "audio", "fonts", "fuentes",
                     "assets", "recursos", "media", "node_modules"}
PALABRAS_SOBRANTES = {"copy", "copia"}
RE_CODIGO = re.compile(r"^cap(?:itulo)?[\s._-]*(\d+(?:[\s._-]+\d+)*)", re.I)
RE_URL = re.compile(r"https?://[^\s<>\"']+")


# ---------- utilidades ----------
def orden_carpeta(p: Path):
    m = re.match(r"^[A-Za-z]*(\d+)", p.name)
    return (int(m.group(1)) if m else 9999, p.name.lower())


def ruta(p: Path) -> str:
    return p.relative_to(RAIZ).as_posix()


def capitalizar(t: str) -> str:
    return t[:1].upper() + t[1:] if t else t


def limpiar_nombre(texto: str) -> str:
    texto = re.sub(r"(?<=[a-záéíóúñ])(?=[A-ZÁÉÍÓÚÑ])", " ", texto)       # EfectoTexto → Efecto Texto
    texto = re.sub(r"[-_]+", " ", texto)
    palabras = [w for w in texto.split() if w.lower() not in PALABRAS_SOBRANTES]
    texto = " ".join(palabras).strip(" .-")
    texto = re.sub(r"\bia\b", "IA", texto, flags=re.I)
    return capitalizar(texto)


def nombre_bonito(carpeta: str) -> str:
    return limpiar_nombre(re.sub(r"^[A-Za-z]?\d+[-_ ]*", "", carpeta)) or carpeta


def leer_titulo(html_path: Path) -> str:
    try:
        html = html_path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""
    m = re.search(r"<title[^>]*>(.*?)</title>", html, re.I | re.S)
    titulo = unescape(re.sub(r"\s+", " ", m.group(1))).strip() if m else ""
    return "" if titulo.lower() in TITULOS_GENERICOS else titulo


def analizar_nombre(nombre: str):
    """'Cap1-3-4Degradados' → ([1, 3, 4], 'Degradados')"""
    m = RE_CODIGO.match(nombre)
    if not m:
        return [], limpiar_nombre(re.sub(r"^\d+[-_ ]*", "", nombre))
    numeros = [int(n) for n in re.findall(r"\d+", m.group(1))]
    return numeros, limpiar_nombre(nombre[m.end():])


def crear_ejemplo(nombre_base: str, ruta_web: str, html: Path, es_carpeta: bool, contexto: str = ""):
    numeros, nombre = analizar_nombre(nombre_base)
    titulo_html = leer_titulo(html)
    codigo = ".".join(map(str, numeros))
    if es_carpeta:
        nombre = limpiar_nombre(re.sub(r"^ejemplo\s+", "", nombre, flags=re.I)) or nombre
    if not numeros and contexto:
        # .html dentro de una subcarpeta sin número: mejor su <title> que el nombre del archivo
        titulo = titulo_html or f"{contexto} · {nombre}"
    elif nombre and len(nombre) < 4 and codigo:
        titulo = f"Ejemplo {codigo} · {nombre}"
    else:
        titulo = nombre or titulo_html or (f"Ejemplo {codigo}" if codigo else nombre_base)
    subtitulo = titulo_html if titulo_html and titulo_html.lower() != titulo.lower() else ""
    return {
        "titulo": titulo,
        "subtitulo": subtitulo,
        "codigo": codigo,
        "grupo": ".".join(map(str, numeros[:2])) if numeros else "",
        "archivo": ruta_web.split("/ejemplos/", 1)[-1].rstrip("/"),
        "ruta": ruta_web,
        "carpeta": es_carpeta,
        "_orden": (0 if numeros else 1, numeros, titulo.lower()),
    }


def recorrer_ejemplos(carpeta: Path, ejemplos: list, enlaces: list, contexto: str = "", nivel: int = 0):
    for f in sorted(carpeta.iterdir(), key=lambda x: x.name.lower()):
        if f.name.startswith("."):
            continue
        if f.is_file():
            if f.suffix.lower() == ".html":
                ejemplos.append(crear_ejemplo(f.stem, ruta(f), f, False, contexto))
            elif f.suffix.lower() == ".txt":
                texto = f.read_text(encoding="utf-8", errors="ignore")
                for url in RE_URL.findall(texto):
                    url = url.rstrip(").,;")
                    if url not in {e["url"] for e in enlaces}:
                        enlaces.append({"url": url, "origen": f.stem})
        elif f.is_dir() and f.name.lower() not in CARPETAS_RECURSOS and nivel < 3:
            index = f / "index.html"
            if index.is_file():
                ejemplos.append(crear_ejemplo(f.name, ruta(f) + "/", index, True))
            else:
                sub = limpiar_nombre(re.sub(r"^ejemplo\s+", "", f.name, flags=re.I))
                recorrer_ejemplos(f, ejemplos, enlaces, contexto or sub, nivel + 1)


def archivos(carpeta: Path, extensiones=(".pdf",)):
    if not carpeta.is_dir():
        return []
    return [
        {"nombre": f.name, "ruta": ruta(f)}
        for f in sorted(carpeta.iterdir(), key=lambda x: x.name.lower())
        if f.is_file() and f.suffix.lower() in extensiones
    ]


# ---------- programa principal ----------
def main():
    temas = []
    for t in sorted((x for x in RAIZ.iterdir() if x.is_dir() and re.match(r"^T\d+", x.name)), key=orden_carpeta):
        capitulos = []
        for c in sorted((x for x in t.iterdir() if x.is_dir() and re.match(r"^C\d+", x.name)), key=orden_carpeta):
            ejemplos, enlaces = [], []
            if (c / "ejemplos").is_dir():
                recorrer_ejemplos(c / "ejemplos", ejemplos, enlaces)
            ejemplos.sort(key=lambda e: e["_orden"])
            for e in ejemplos:
                del e["_orden"]
            capitulos.append({
                "carpeta": c.name,
                "ruta": ruta(c) + "/",
                "teoria": archivos(c / "teoria"),
                "ejemplos": ejemplos,
                "enlaces": enlaces,
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
        for d in sorted((x for x in carpeta_extra.iterdir() if x.is_dir()), key=orden_carpeta):
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
    (RAIZ / "ejemplos.json").write_text(json.dumps(datos, ensure_ascii=False, indent=2), encoding="utf-8")
    total = sum(len(c["ejemplos"]) for t in temas for c in t["capitulos"])
    print(f"ejemplos.json generado: {len(temas)} tema(s), {total} ejemplo(s)")


if __name__ == "__main__":
    main()
