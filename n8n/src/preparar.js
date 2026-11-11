// Construye la petición a la API de Claude con tool use forzado (salida JSON garantizada).
const texto = $json.body?.incidencia ?? $json.incidencia ?? '';
const esquema = {
  type: 'object',
  properties: {
    tipo: { type: 'string', enum: ['averia','accidente_danos','retraso','cliente_ausente','llaves_documentacion','combustible_carga','cambio_cita','otro'] },
    resumen: { type: 'string' },
    emisor: { type: 'string', enum: ['conductor','cliente','interno','desconocido'] },
    matricula: { type: ['string','null'] },
    modelo_vehiculo: { type: ['string','null'] },
    conductor: { type: ['string','null'] },
    telefono_contacto: { type: ['string','null'] },
    cliente: { type: ['string','null'] },
    referencia_trayecto: { type: ['string','null'] },
    ubicacion: { type: ['string','null'] },
    hora_estimada_llegada: { type: ['string','null'] },
    nueva_fecha: { type: ['string','null'] },
    vehiculo_inmovilizado: { type: ['boolean','null'] },
    hay_heridos: { type: ['boolean','null'] },
    descripcion_danos: { type: ['string','null'] },
    nivel_combustible_o_bateria: { type: ['string','null'] },
    posible_robo_o_fraude: { type: 'boolean' },
    cliente_enfadado: { type: 'boolean' },
    prioridad_sugerida: { type: 'string', enum: ['baja','media','alta','critica'] },
    confianza: { type: 'number' },
  },
  required: ['tipo','resumen','emisor','matricula','conductor','cliente','ubicacion','vehiculo_inmovilizado','hay_heridos','posible_robo_o_fraude','cliente_enfadado','prioridad_sugerida','confianza'],
};
const system = `Eres el clasificador de incidencias de una empresa de movimiento de vehículos con conductores profesionales.
Lee la incidencia y rellena la herramienta registrar_incidencia.
- No inventes datos: si algo no aparece, usa null.
- hay_heridos y vehiculo_inmovilizado: true/false solo si el texto lo deja claro; si no, null.
- Matrícula sin espacios ni guiones (1234ABC).
- confianza < 0.6 si el texto es ambiguo.`;
return [{ json: {
  incidencia: texto,
  body: {
    model: 'claude-sonnet-5-5',
    max_tokens: 1024,
    system,
    tools: [{ name: 'registrar_incidencia', description: 'Registra los datos estructurados de una incidencia operativa.', input_schema: esquema }],
    tool_choice: { type: 'tool', name: 'registrar_incidencia' },
    messages: [{ role: 'user', content: texto }],
  },
}}];
