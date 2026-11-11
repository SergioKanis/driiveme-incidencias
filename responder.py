"""
Paso 5: preparar la comunicación para el conductor o el cliente.

El mensaje se redacta DESPUÉS de que las reglas hayan decidido, para que el
texto sea coherente con la decisión (no prometer una solución automática en
un caso que se va a escalar, pedir exactamente los datos que faltan, etc.).
Con LLM queda más natural; sin él, se usan plantillas.
"""

import os

from .rules import NOMBRE_CAMPO, MENSAJE_AUTO
from .extractor import MODELO


def destinatario(extraccion: dict) -> str:
    return "cliente" if extraccion.get("emisor") == "cliente" else "conductor"


def mensaje_plantilla(extraccion: dict, decision: dict) -> str:
    nombre = extraccion.get("conductor") if destinatario(extraccion) == "conductor" else extraccion.get("cliente")
    saludo = f"Hola {nombre}," if nombre else "Hola,"
    faltan = [NOMBRE_CAMPO.get(c, c) for c in decision["informacion_faltante"]]

    if extraccion.get("hay_heridos") is True:
        cuerpo = ("Si hay alguna persona herida, llama ahora mismo al 112. "
                  "Un responsable de operaciones te va a llamar en unos minutos.")
    elif decision["decision"] == "escalar_a_persona":
        cuerpo = "Hemos recibido tu aviso y un responsable de operaciones se pondrá en contacto contigo en breve."
    elif decision["decision"] == "solicitar_informacion":
        cuerpo = "Hemos recibido tu aviso. Para poder ayudarte necesitamos que nos indiques: " + "; ".join(faltan) + "."
    else:
        cuerpo = MENSAJE_AUTO.get(extraccion.get("tipo"), MENSAJE_AUTO["otro"])

    if decision["decision"] == "escalar_a_persona" and faltan:
        cuerpo += " Mientras tanto, por favor envíanos: " + "; ".join(faltan) + "."
    return f"{saludo}\n\n{cuerpo}\n\nGracias,\nEquipo de Operaciones"


def mensaje_llm(extraccion: dict, decision: dict) -> str:
    import anthropic

    instrucciones = f"""Redacta un mensaje breve (máx. 90 palabras), en español, para el {destinatario(extraccion)}
de una empresa de movimiento de vehículos. Tono profesional y cercano, tuteo.
Incidencia: {extraccion.get('resumen')}
Decisión interna: {decision['decision']}
Datos que hay que pedir: {[NOMBRE_CAMPO.get(c, c) for c in decision['informacion_faltante']] or 'ninguno'}
Siguiente acción: {decision['siguiente_accion']}
Reglas: no prometas plazos concretos ni compensaciones; si se escala, di que un responsable contactará en breve;
si hay heridos, lo primero es indicar que llamen al 112. Firma: Equipo de Operaciones. Devuelve solo el mensaje."""
    respuesta = anthropic.Anthropic().messages.create(
        model=MODELO,
        max_tokens=400,
        messages=[{"role": "user", "content": instrucciones}],
    )
    return respuesta.content[0].text.strip()


def redactar(extraccion: dict, decision: dict, usar_llm: bool) -> str:
    if usar_llm and os.environ.get("ANTHROPIC_API_KEY"):
        try:
            return mensaje_llm(extraccion, decision)
        except Exception as e:
            print(f"[aviso] Fallo del LLM al redactar ({e}); se usa plantilla.", flush=True)
    return mensaje_plantilla(extraccion, decision)
