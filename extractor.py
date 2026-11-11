"""
Paso 1-2: leer, clasificar y extraer datos de la incidencia.

Se usa Claude con "tool use" forzado: el modelo está obligado a responder
rellenando el esquema JSON de la herramienta `registrar_incidencia`, así la
salida siempre es JSON válido y con los campos esperados.

Si no hay API key o la llamada falla, se usa un extractor heurístico muy
básico (regex + palabras clave) con confianza baja. Las reglas escalan
cualquier caso con confianza baja, así que sin LLM todo acaba en manos de
una persona: el sistema falla de forma segura.
"""

import json
import os
import re

TIPOS = [
    "averia",
    "accidente_danos",
    "retraso",
    "cliente_ausente",
    "llaves_documentacion",
    "combustible_carga",
    "cambio_cita",
    "otro",
]

ESQUEMA = {
    "type": "object",
    "properties": {
        "tipo": {"type": "string", "enum": TIPOS},
        "resumen": {"type": "string", "description": "Resumen de la incidencia en una frase."},
        "emisor": {"type": "string", "enum": ["conductor", "cliente", "interno", "desconocido"]},
        "matricula": {"type": ["string", "null"], "description": "Matrícula en formato 1234ABC, o null si no aparece."},
        "modelo_vehiculo": {"type": ["string", "null"]},
        "conductor": {"type": ["string", "null"], "description": "Nombre del conductor."},
        "telefono_contacto": {"type": ["string", "null"]},
        "cliente": {"type": ["string", "null"], "description": "Empresa o persona cliente del trayecto."},
        "referencia_trayecto": {"type": ["string", "null"]},
        "ubicacion": {"type": ["string", "null"]},
        "origen": {"type": ["string", "null"]},
        "destino": {"type": ["string", "null"]},
        "hora_estimada_llegada": {"type": ["string", "null"]},
        "nueva_fecha": {"type": ["string", "null"]},
        "vehiculo_inmovilizado": {"type": ["boolean", "null"], "description": "null si no se sabe."},
        "hay_heridos": {"type": ["boolean", "null"], "description": "null si no se menciona."},
        "descripcion_danos": {"type": ["string", "null"]},
        "nivel_combustible_o_bateria": {"type": ["string", "null"]},
        "posible_robo_o_fraude": {"type": "boolean"},
        "cliente_enfadado": {"type": "boolean"},
        "prioridad_sugerida": {"type": "string", "enum": ["baja", "media", "alta", "critica"]},
        "confianza": {"type": "number", "description": "0 a 1: seguridad en la clasificación."},
    },
    "required": [
        "tipo", "resumen", "emisor", "matricula", "conductor", "cliente",
        "ubicacion", "vehiculo_inmovilizado", "hay_heridos",
        "posible_robo_o_fraude", "cliente_enfadado", "prioridad_sugerida", "confianza",
    ],
}

PROMPT_SISTEMA = """Eres el clasificador de incidencias de una empresa de movimiento de vehículos
con conductores profesionales (traslados entre agencias, entregas a clientes, etc.).
Lee la incidencia y rellena la herramienta registrar_incidencia.
Reglas:
- No inventes datos. Si algo no aparece en el texto, usa null.
- hay_heridos y vehiculo_inmovilizado: true/false solo si el texto lo deja claro; si no, null.
- Normaliza la matrícula española sin espacios ni guiones (1234ABC).
- confianza: baja (<0.6) si el texto es ambiguo o mezcla varios problemas."""

MODELO = os.environ.get("CLAUDE_MODEL", "claude-sonnet-5-5")


def extraer_con_llm(texto: str) -> dict:
    import anthropic  # import local: el modo heurístico no necesita la librería

    cliente = anthropic.Anthropic()
    respuesta = cliente.messages.create(
        model=MODELO,
        max_tokens=1024,
        system=PROMPT_SISTEMA,
        tools=[{
            "name": "registrar_incidencia",
            "description": "Registra los datos estructurados de una incidencia operativa.",
            "input_schema": ESQUEMA,
        }],
        tool_choice={"type": "tool", "name": "registrar_incidencia"},
        messages=[{"role": "user", "content": texto}],
    )
    for bloque in respuesta.content:
        if bloque.type == "tool_use":
            return dict(bloque.input)
    raise RuntimeError("El modelo no devolvió la herramienta esperada")


PALABRAS_TIPO = [
    ("accidente_danos", ["golpe", "choque", "accidente", "rayón", "rayon", "abolladura", "daño"]),
    ("averia", ["avería", "averia", "no arranca", "pinchazo", "rueda", "testigo", "humo"]),
    ("cliente_ausente", ["no está", "no esta", "no contesta", "nadie", "no aparece"]),
    ("llaves_documentacion", ["llaves", "documentación", "documentacion", "papeles"]),
    ("combustible_carga", ["gasolina", "combustible", "batería", "bateria", "cargar", "depósito"]),
    ("cambio_cita", ["cambiar la fecha", "reprogramar", "otro día", "aplazar"]),
    ("retraso", ["retraso", "tarde", "atasco", "llegaré", "llegare"]),
]


def extraer_heuristico(texto: str) -> dict:
    t = texto.lower()
    tipo = "otro"
    for candidato, palabras in PALABRAS_TIPO:
        if any(p in t for p in palabras):
            tipo = candidato
            break
    matricula = re.search(r"\b(\d{4})[\s-]?([B-DF-HJ-NP-TV-Z]{3})\b", texto.upper())
    return {
        "tipo": tipo,
        "resumen": texto.strip()[:140],
        "emisor": "desconocido",
        "matricula": "".join(matricula.groups()) if matricula else None,
        "conductor": None,
        "cliente": None,
        "ubicacion": None,
        "vehiculo_inmovilizado": None,
        "hay_heridos": True if "herido" in t else None,
        "posible_robo_o_fraude": "robo" in t or "robado" in t,
        "cliente_enfadado": False,
        "prioridad_sugerida": "media",
        "confianza": 0.4,
    }


def extraer(texto: str) -> tuple[dict, str]:
    """Devuelve (extracción, método usado)."""
    if os.environ.get("ANTHROPIC_API_KEY"):
        try:
            return extraer_con_llm(texto), f"llm:{MODELO}"
        except Exception as e:  # red, cuota, respuesta inválida...
            print(f"[aviso] Fallo del LLM ({e}); se usa el extractor heurístico.", flush=True)
    return extraer_heuristico(texto), "heuristico"


if __name__ == "__main__":
    print(json.dumps(ESQUEMA, ensure_ascii=False, indent=2))
