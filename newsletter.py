#!/usr/bin/env python3
"""
BoletÃ­n Diario de TecnologÃ­a Chile
Busca noticias con DuckDuckGo, analiza con Groq, envÃ­a por ntfy.sh
"""

import os
import json
import requests
from datetime import datetime, timezone, timedelta
from duckduckgo_search import DDGS
from groq import Groq

# ââ ConfiguraciÃ³n ââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ
GROQ_API_KEY  = os.environ["GROQ_API_KEY"]
NTFY_TOPIC    = "Tecno-Analisis"
NTFY_URL      = f"https://ntfy.sh/{NTFY_TOPIC}"
GROQ_MODEL    = "llama-3.3-70b-versatile"
MAX_RESULTS   = 6      # resultados por query
CHILE_TZ      = timezone(timedelta(hours=-4))   # UTC-4 (verano) / UTC-3 (invierno) â ntfy recibe UTC

# ââ Queries de bÃºsqueda ââââââââââââââââââââââââââââââââââââââââââââââââââââââ
QUERIES = {
    "resumen":         "tecnologÃ­a Chile noticias hoy",
    "ia_innovacion":   "inteligencia artificial IA Chile LatinoamÃ©rica innovaciÃ³n",
    "ciberseguridad":  "ciberseguridad Chile ataque hackeo vulnerabilidad",
    "banca_fintech":   "fintech banca digital Chile pagos CMF",
    "infraestructura": "data center conectividad infraestructura tecnolÃ³gica Chile inversiÃ³n",
}

def buscar_noticias(query: str, max_results: int = MAX_RESULTS) -> list[dict]:
    """Busca noticias recientes con DuckDuckGo."""
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
        print(f"[WARN] Error buscando '{query}': {e}")
    return resultados


def generar_boletin(noticias_por_seccion: dict) -> str:
    """Llama a Groq para generar el boletÃ­n estructurado."""
    client = Groq(api_key=GROQ_API_KEY)

    hoy = datetime.now(CHILE_TZ).strftime("%A %d de %B de %Y")

    prompt_sistema = """Eres un editor de boletÃ­n tecnolÃ³gico especializado en Chile y LatinoamÃ©rica.
Redactas resÃºmenes compactos, claros y Ãºtiles para leer en celular.
Usa emojis por secciÃ³n, lenguaje directo y mÃ¡ximo 3-4 lÃ­neas por Ã­tem.
NUNCA inventes noticias; solo sintetiza lo que se te entrega."""

    prompt_usuario = f"""Hoy es {hoy}. Genera un boletÃ­n diario de tecnologÃ­a para Chile con este material:

=== RESUMEN DEL DÃA ===
{json.dumps(noticias_por_seccion.get('resumen', []), ensure_ascii=False, indent=2)}

=== IA & INNOVACIÃN ===
{json.dumps(noticias_por_seccion.get('ia_innovacion', []), ensure_ascii=False, indent=2)}

=== CIBERSEGURIDAD ===
{json.dumps(noticias_por_seccion.get('ciberseguridad', []), ensure_ascii=False, indent=2)}

=== BANCA & FINTECH ===
{json.dumps(noticias_por_seccion.get('banca_fintech', []), ensure_ascii=False, indent=2)}

=== INFRAESTRUCTURA ===
{json.dumps(noticias_por_seccion.get('infraestructura', []), ensure_ascii=False, indent=2)}

Estructura del boletÃ­n (usa EXACTAMENTE estos encabezados con emojis):

ð° RESUMEN DEL DÃA
[2-3 titulares clave de las Ãºltimas 24h, cada uno en 1-2 lÃ­neas]

ð¤ IA & INNOVACIÃN
[2 novedades de IA con impacto en Chile/Latam, 1-2 lÃ­neas c/u]

ð CIBERSEGURIDAD
[1-2 alertas o incidentes relevantes, 1-2 lÃ­neas c/u]

ð¦ BANCA & FINTECH
[1-2 novedades del sector financiero digital chileno, 1-2 lÃ­neas c/u]

ðï¸ INFRAESTRUCTURA
[1-2 novedades de data centers, conectividad o inversiÃ³n tech en Chile]

ð¡ DATO DESTACADO
[Un hecho o cifra relevante y sorprendente del dÃ­a, 1-2 lÃ­neas]

---
BoletÃ­n compacto: mÃ¡ximo 400 palabras total. Sin bullets innecesarios. Sin URLs en el texto.
Si no hay noticias para una secciÃ³n, escribe "Sin novedades destacadas hoy."
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
    """EnvÃ­a el boletÃ­n a ntfy.sh."""
    headers = {
        "Title":    titulo,
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
    print(f"[OK] NotificaciÃ³n enviada â {NTFY_URL} (HTTP {resp.status_code})")


def main():
    fecha_str = datetime.now(CHILE_TZ).strftime("%d/%m/%Y")
    print(f"[INFO] Iniciando boletÃ­n para {fecha_str} â¦")

    # 1. Buscar noticias
    noticias = {}
    for seccion, query in QUERIES.items():
        print(f"[INFO] Buscando: {query}")
        noticias[seccion] = buscar_noticias(query)
        total = len(noticias[seccion])
        print(f"       â {total} resultado(s)")

    # 2. Generar boletÃ­n con IA
    print("[INFO] Generando boletÃ­n con Groqâ¦")
    boletin = generar_boletin(noticias)
    print("[INFO] BoletÃ­n generado:")
    print(boletin[:500] + "â¦")

    # 3. Enviar por ntfy.sh
    titulo = f"ð¨ð± Tech Chile Â· {fecha_str}"
    print(f"[INFO] Enviando a ntfy.sh/{NTFY_TOPIC}â¦")
    enviar_ntfy(titulo, boletin)

    print("[INFO] Â¡Listo! BoletÃ­n entregado correctamente.")


if __name__ == "__main__":
    main()
