#!/usr/bin/env python3
"""
Tech Chile Daily Newsletter
Searches news with DuckDuckGo (ddgs), analyzes with Groq, sends via ntfy.sh
"""

import os
import json
import requests
from datetime import datetime, timezone, timedelta
from urllib.parse import quote
from ddgs import DDGS
from groq import Groq

# -- Config ------------------------------------------------------------------
GROQ_API_KEY  = os.environ["GROQ_API_KEY"]
NTFY_TOPIC    = "Tecno-Analisis"
NTFY_URL      = f"https://ntfy.sh/{NTFY_TOPIC}"
GROQ_MODEL    = "llama-3.3-70b-versatile"
MAX_RESULTS   = 6
CHILE_TZ      = timezone(timedelta(hours=-4))   # UTC-4 winter / UTC-3 summer

# -- Search queries ----------------------------------------------------------
QUERIES = {
    "resumen":         "tecnologia Chile noticias hoy",
    "ia_innovacion":   "inteligencia artificial IA Chile Latinoamerica innovacion",
    "ciberseguridad":  "ciberseguridad Chile ataque hackeo vulnerabilidad",
    "banca_fintech":   "fintech banca digital Chile pagos CMF",
    "infraestructura": "data center conectividad infraestructura tecnologica Chile inversion",
}

def buscar_noticias(query: str, max_results: int = MAX_RESULTS) -> list[dict]:
    """Search recent news with DuckDuckGo."""
    resultados = []
    try:
        with DDGS() as ddgs:
            for r in ddgs.news(query, region="cl-es", timelimit="d", max_results=max_results):
                resultados.append({
                    "titulo": r.get("title", ""),
                    "fuente": r.get("source", ""),
                    "fecha":  r.get("date", ""),
                    "url":    r.get("url", ""),
                    "resumen": r.get("body", "")[:300],
                })
    except Exception as e:
        print(f"[WARN] Error searching '{query}': {e}")
    return resultados


def generar_boletin(noticias_por_seccion: dict) -> str:
    """Call Groq to generate the structured newsletter."""
    client = Groq(api_key=GROQ_API_KEY)

    hoy = datetime.now(CHILE_TZ).strftime("%A %d de %B de %Y")

    prompt_sistema = """Eres un editor de boletin tecnologico especializado en Chile y Latinoamerica.
Redactas resumenes compactos, claros y utiles para leer en celular.
Usa emojis por seccion, lenguaje directo y maximo 3-4 lineas por item.
NUNCA inventes noticias; solo sintetiza lo que se te entrega."""

    prompt_usuario = f"""Hoy es {hoy}. Genera un boletin diario de tecnologia para Chile con este material:

=== RESUMEN DEL DIA ===
{json.dumps(noticias_por_seccion.get('resumen', []), ensure_ascii=False, indent=2)}

=== IA & INNOVACION ===
{json.dumps(noticias_por_seccion.get('ia_innovacion', []), ensure_ascii=False, indent=2)}

=== CIBERSEGURIDAD ===
{json.dumps(noticias_por_seccion.get('ciberseguridad', []), ensure_ascii=False, indent=2)}

=== BANCA & FINTECH ===
{json.dumps(noticias_por_seccion.get('banca_fintech', []), ensure_ascii=False, indent=2)}

=== INFRAESTRUCTURA ===
{json.dumps(noticias_por_seccion.get('infraestructura', []), ensure_ascii=False, indent=2)}

Estructura del boletin (usa EXACTAMENTE estos encabezados con emojis):

\U0001f4f0 RESUMEN DEL DIA
[2-3 titulares clave de las ultimas 24h, cada uno en 1-2 lineas]

\U0001f916 IA & INNOVACION
[2 novedades de IA con impacto en Chile/Latam, 1-2 lineas c/u]

\U0001f510 CIBERSEGURIDAD
[1-2 alertas o incidentes relevantes, 1-2 lineas c/u]

\U0001f3e6 BANCA & FINTECH
[1-2 novedades del sector financiero digital chileno, 1-2 lineas c/u]

\U0001f3d7 INFRAESTRUCTURA
[1-2 novedades de data centers, conectividad o inversion tech en Chile]

\U0001f4a1 DATO DESTACADO
[Un hecho o cifra relevante y sorprendente del dia, 1-2 lineas]

---
Boletin compacto: maximo 400 palabras total. Sin bullets innecesarios. Sin URLs en el texto.
Si no hay noticias para una seccion, escribe "Sin novedades destacadas hoy."
"""

    respuesta = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {"role": "system", "content": prompt_sistema},
            {"role": "user",   "content": prompt_usuario},
        ],
        temperature=0.5,
        max_tokens=1200,
    )
    return respuesta.choices[0].message.content.strip()


def enviar_ntfy(titulo: str, cuerpo: str) -> None:
    """Send the newsletter via ntfy.sh.
    Headers must be latin-1 safe; non-ASCII values must be percent-encoded.
    """
    headers = {
        "Title":    quote(titulo),   # percent-encode emoji/accents for HTTP header
        "Priority": "default",
        "Tags":     "newspaper,chile,tech",
        "Markdown": "yes",
        "Content-Type": "text/plain; charset=utf-8",
    }
    resp = requests.post(
        NTFY_URL,
        data=cuerpo.encode("utf-8"),
        headers=headers,
        timeout=15,
    )
    resp.raise_for_status()
    print(f"[OK] Notification sent -> {NTFY_URL} (HTTP {resp.status_code})")


def main():
    fecha_str = datetime.now(CHILE_TZ).strftime("%d/%m/%Y")
    print(f"[INFO] Starting newsletter for {fecha_str} ...")

    # 1. Search news
    noticias = {}
    for seccion, query in QUERIES.items():
        print(f"[INFO] Searching: {query}")
        noticias[seccion] = buscar_noticias(query)
        total = len(noticias[seccion])
        print(f"       -> {total} result(s)")

    # 2. Generate newsletter with AI
    print("[INFO] Generating newsletter with Groq...")
    boletin = generar_boletin(noticias)
    print("[INFO] Newsletter generated (preview):")
    print(boletin[:300] + "...")

    # 3. Send via ntfy.sh
    titulo = f"Tech Chile Daily - {fecha_str}"   # ASCII-safe title for HTTP header
    print(f"[INFO] Sending to ntfy.sh/{NTFY_TOPIC}...")
    enviar_ntfy(titulo, boletin)

    print("[INFO] Done! Newsletter delivered successfully.")


if __name__ == "__main__":
    main()
