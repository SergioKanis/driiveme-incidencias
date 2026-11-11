"""
Capa de reglas deterministas.

El LLM solo EXTRAE y CLASIFICA. Las decisiones de negocio (qué falta,
prioridad mínima, siguiente acción y si se escala) se toman aquí, en código:
son predecibles, auditables y se pueden testear sin llamar a ningún modelo.
"""

# Campos necesarios para poder actuar, por tipo de incidencia.
CAMPOS_COMUNES = ["matricula"]

CAMPOS_OBLIGATORIOS = {
    "averia": ["ubicacion", "vehiculo_inmovilizado"],
    "accidente_danos": ["ubicacion", "descripcion_danos", "hay_heridos"],
    "retraso": ["hora_estimada_llegada"],
    "cliente_ausente": ["ubicacion", "referencia_trayecto"],
    "llaves_documentacion": ["ubicacion", "referencia_trayecto"],
    "combustible_carga": ["ubicacion", "nivel_combustible_o_bateria"],
    "cambio_cita": ["referencia_trayecto", "nueva_fecha"],
    "otro": [],
}

# Orden de prioridades (de menor a mayor).
PRIORIDADES = ["baja", "media", "alta", "critica"]

# Prioridad mínima por tipo: el LLM puede subirla, nunca bajarla.
PRIORIDAD_MINIMA = {
    "averia": "media",
    "accidente_danos": "alta",
    "retraso": "media",
    "cliente_ausente": "media",
    "llaves_documentacion": "media",
    "combustible_carga": "baja",
    "cambio_cita": "baja",
    "otro": "baja",
}

# Siguiente acción por defecto cuando no falta información.
ACCION_POR_TIPO = {
    "averia": "Activar asistencia en carretera y coordinar con el conductor la espera o el traslado.",
    "accidente_danos": "Abrir parte de daños, solicitar fotos y parte amistoso, y avisar al cliente.",
    "retraso": "Notificar al cliente la nueva hora estimada de llegada y actualizar el trayecto.",
    "cliente_ausente": "Contactar con el cliente por teléfono y fijar un tiempo máximo de espera para el conductor.",
    "llaves_documentacion": "Localizar las llaves o la documentación con el punto de recogida y dar instrucciones al conductor.",
    "combustible_carga": "Indicar al conductor la gasolinera o punto de carga más cercano y registrar el gasto.",
    "cambio_cita": "Reprogramar el trayecto en la nueva fecha y confirmar con conductor y cliente.",
    "otro": "Revisión manual por el equipo de operaciones.",
}

# Mensaje al remitente cuando el caso se resuelve automáticamente.
MENSAJE_AUTO = {
    "averia": "Vamos a activar la asistencia en carretera. Quédate en un lugar seguro, con el chaleco puesto, y te confirmamos cuándo llega la grúa.",
    "accidente_danos": "Hemos registrado el aviso de daños. Haz fotos del vehículo y no lo muevas hasta recibir instrucciones.",
    "retraso": "Gracias por avisar. Informamos al cliente de la nueva hora de llegada; continúa el trayecto con normalidad.",
    "cliente_ausente": "Vamos a contactar con el cliente. Espera en el punto de entrega y te damos instrucciones en cuanto sepamos algo.",
    "llaves_documentacion": "Estamos localizando las llaves o la documentación con el punto de recogida. Te escribimos en cuanto tengamos instrucciones.",
    "combustible_carga": "Puedes repostar o cargar en el punto más cercano. Guarda el ticket para que podamos registrar el gasto.",
    "cambio_cita": "Hemos registrado tu petición de cambio de fecha. Te confirmaremos la nueva cita en breve.",
    "otro": "Hemos recibido tu aviso y lo estamos revisando.",
}

UMBRAL_CONFIANZA = 0.6

# Nombres legibles para pedir datos que faltan en el mensaje.
NOMBRE_CAMPO = {
    "matricula": "la matrícula del vehículo",
    "ubicacion": "la ubicación exacta (dirección o punto kilométrico)",
    "vehiculo_inmovilizado": "si el vehículo puede seguir circulando o está inmovilizado",
    "descripcion_danos": "una descripción de los daños (y fotos si es posible)",
    "hay_heridos": "si hay alguna persona herida",
    "hora_estimada_llegada": "la nueva hora estimada de llegada",
    "referencia_trayecto": "la referencia del trayecto o reserva",
    "nivel_combustible_o_bateria": "el nivel actual de combustible o batería",
    "nueva_fecha": "la nueva fecha y hora deseada",
}


def _tipo(extraccion: dict) -> str:
    """Un tipo desconocido se trata como "otro" (y por tanto se escala)."""
    tipo = extraccion.get("tipo")
    return tipo if tipo in CAMPOS_OBLIGATORIOS else "otro"


def _valor_presente(valor):
    """None y cadenas vacías cuentan como dato ausente; False es un dato válido."""
    if valor is None:
        return False
    if isinstance(valor, str) and not valor.strip():
        return False
    return True


def campos_faltantes(extraccion: dict) -> list[str]:
    tipo = _tipo(extraccion)
    requeridos = CAMPOS_COMUNES + CAMPOS_OBLIGATORIOS.get(tipo, [])
    return [c for c in requeridos if not _valor_presente(extraccion.get(c))]


def prioridad_final(extraccion: dict) -> str:
    tipo = _tipo(extraccion)
    sugerida = extraccion.get("prioridad_sugerida", "baja")
    if sugerida not in PRIORIDADES:
        sugerida = "baja"
    minima = PRIORIDAD_MINIMA.get(tipo, "baja")
    prioridad = max(sugerida, minima, key=PRIORIDADES.index)

    if extraccion.get("hay_heridos") is True:
        prioridad = "critica"
    elif extraccion.get("vehiculo_inmovilizado") is True:
        prioridad = max(prioridad, "alta", key=PRIORIDADES.index)
    return prioridad


def motivos_escalado(extraccion: dict, prioridad: str) -> list[str]:
    motivos = []
    tipo = _tipo(extraccion)

    if extraccion.get("hay_heridos") is True:
        motivos.append("Hay personas heridas: requiere atención humana inmediata.")
    if tipo == "accidente_danos":
        motivos.append("Accidente o daños en el vehículo: implica seguro y responsabilidad.")
    if extraccion.get("posible_robo_o_fraude") is True:
        motivos.append("Posible robo o fraude.")
    if extraccion.get("vehiculo_inmovilizado") is True:
        motivos.append("Vehículo inmovilizado: hay que coordinar asistencia y replanificar.")
    if extraccion.get("cliente_enfadado") is True:
        motivos.append("Cliente muy molesto o con amenaza de reclamación.")
    if tipo == "otro":
        motivos.append("Tipo de incidencia no reconocido.")
    if float(extraccion.get("confianza", 0)) < UMBRAL_CONFIANZA:
        motivos.append(f"Confianza de la clasificación baja (< {UMBRAL_CONFIANZA}).")
    if prioridad == "critica" and not motivos:
        motivos.append("Prioridad crítica.")
    return motivos


def decidir(extraccion: dict) -> dict:
    """Devuelve la decisión de negocio a partir de la extracción del LLM."""
    faltan = campos_faltantes(extraccion)
    prioridad = prioridad_final(extraccion)
    motivos = motivos_escalado(extraccion, prioridad)
    tipo = _tipo(extraccion)

    if motivos:
        decision = "escalar_a_persona"
        accion = ACCION_POR_TIPO.get(tipo, ACCION_POR_TIPO["otro"])
        if faltan:
            accion = f"Asignar a un agente de operaciones. Mientras tanto, pedir: {', '.join(faltan)}. " + accion
        else:
            accion = "Asignar a un agente de operaciones. " + accion
    elif faltan:
        decision = "solicitar_informacion"
        accion = "Pedir automáticamente los datos que faltan: " + ", ".join(faltan) + "."
    else:
        decision = "resolver_automaticamente"
        accion = ACCION_POR_TIPO.get(tipo, ACCION_POR_TIPO["otro"])

    return {
        "prioridad": prioridad,
        "informacion_faltante": faltan,
        "decision": decision,
        "motivos_escalado": motivos,
        "siguiente_accion": accion,
    }
