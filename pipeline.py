"""Orquesta los pasos: extraer -> decidir (reglas) -> redactar -> salida estructurada."""

from datetime import datetime, timezone

from .extractor import extraer
from .rules import decidir
from .responder import redactar, destinatario

CAMPOS_ENTIDADES = [
    "matricula", "modelo_vehiculo", "conductor", "telefono_contacto", "cliente",
    "referencia_trayecto", "ubicacion", "origen", "destino",
    "hora_estimada_llegada", "nueva_fecha", "vehiculo_inmovilizado", "hay_heridos",
    "descripcion_danos", "nivel_combustible_o_bateria",
]


def procesar_incidencia(texto: str, extraccion: dict | None = None) -> dict:
    """
    Procesa una incidencia en texto libre.
    `extraccion` permite inyectar una extracción ya hecha (tests).
    """
    if extraccion is None:
        extraccion, metodo = extraer(texto)
    else:
        metodo = "inyectado"

    decision = decidir(extraccion)
    usar_llm = metodo.startswith("llm")

    return {
        "procesado_en": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "metodo_extraccion": metodo,
        "entrada": texto,
        "clasificacion": {
            "tipo": extraccion.get("tipo"),
            "resumen": extraccion.get("resumen"),
            "emisor": extraccion.get("emisor"),
            "confianza": extraccion.get("confianza"),
        },
        "entidades": {k: extraccion.get(k) for k in CAMPOS_ENTIDADES},
        "prioridad": decision["prioridad"],
        "informacion_faltante": decision["informacion_faltante"],
        "siguiente_accion": decision["siguiente_accion"],
        "decision": decision["decision"],
        "puede_resolverse_automaticamente": decision["decision"] != "escalar_a_persona",
        "motivos_escalado": decision["motivos_escalado"],
        "comunicacion": {
            "destinatario": destinatario(extraccion),
            "mensaje": redactar(extraccion, decision, usar_llm),
        },
    }
