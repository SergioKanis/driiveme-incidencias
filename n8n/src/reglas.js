// Misma lógica que agente/rules.py: el LLM extrae, el código decide.
const ex = ($json.content || []).find(b => b.type === 'tool_use')?.input || { tipo: 'otro', confianza: 0 };
const texto = $('Preparar petición a Claude').first().json.incidencia;

const OBLIG = {
  averia: ['ubicacion','vehiculo_inmovilizado'],
  accidente_danos: ['ubicacion','descripcion_danos','hay_heridos'],
  retraso: ['hora_estimada_llegada'],
  cliente_ausente: ['ubicacion','referencia_trayecto'],
  llaves_documentacion: ['ubicacion','referencia_trayecto'],
  combustible_carga: ['ubicacion','nivel_combustible_o_bateria'],
  cambio_cita: ['referencia_trayecto','nueva_fecha'],
  otro: [],
};
const PRIO = ['baja','media','alta','critica'];
const MINIMA = { averia:'media', accidente_danos:'alta', retraso:'media', cliente_ausente:'media', llaves_documentacion:'media', combustible_carga:'baja', cambio_cita:'baja', otro:'baja' };
const ACCION = {
  averia: 'Activar asistencia en carretera y coordinar con el conductor la espera o el traslado.',
  accidente_danos: 'Abrir parte de daños, solicitar fotos y parte amistoso, y avisar al cliente.',
  retraso: 'Notificar al cliente la nueva hora estimada de llegada y actualizar el trayecto.',
  cliente_ausente: 'Contactar con el cliente por teléfono y fijar un tiempo máximo de espera para el conductor.',
  llaves_documentacion: 'Localizar las llaves o la documentación con el punto de recogida y dar instrucciones al conductor.',
  combustible_carga: 'Indicar al conductor la gasolinera o punto de carga más cercano y registrar el gasto.',
  cambio_cita: 'Reprogramar el trayecto en la nueva fecha y confirmar con conductor y cliente.',
  otro: 'Revisión manual por el equipo de operaciones.',
};
const MENSAJE_AUTO = {
  averia: 'Vamos a activar la asistencia en carretera. Quédate en un lugar seguro, con el chaleco puesto, y te confirmamos cuándo llega la grúa.',
  accidente_danos: 'Hemos registrado el aviso de daños. Haz fotos del vehículo y no lo muevas hasta recibir instrucciones.',
  retraso: 'Gracias por avisar. Informamos al cliente de la nueva hora de llegada; continúa el trayecto con normalidad.',
  cliente_ausente: 'Vamos a contactar con el cliente. Espera en el punto de entrega y te damos instrucciones en cuanto sepamos algo.',
  llaves_documentacion: 'Estamos localizando las llaves o la documentación con el punto de recogida. Te escribimos en cuanto tengamos instrucciones.',
  combustible_carga: 'Puedes repostar o cargar en el punto más cercano. Guarda el ticket para que podamos registrar el gasto.',
  cambio_cita: 'Hemos registrado tu petición de cambio de fecha. Te confirmaremos la nueva cita en breve.',
  otro: 'Hemos recibido tu aviso y lo estamos revisando.',
};
const NOMBRE = {
  matricula: 'la matrícula del vehículo', ubicacion: 'la ubicación exacta',
  vehiculo_inmovilizado: 'si el vehículo puede seguir circulando', descripcion_danos: 'una descripción de los daños (y fotos)',
  hay_heridos: 'si hay alguna persona herida', hora_estimada_llegada: 'la nueva hora estimada de llegada',
  referencia_trayecto: 'la referencia del trayecto o reserva', nivel_combustible_o_bateria: 'el nivel de combustible o batería',
  nueva_fecha: 'la nueva fecha y hora deseada',
};
const presente = v => v !== null && v !== undefined && !(typeof v === 'string' && !v.trim());
const tipo = OBLIG[ex.tipo] ? ex.tipo : 'otro';

const faltan = ['matricula', ...OBLIG[tipo]].filter(c => !presente(ex[c]));

const mayor = (a, b) => (PRIO.indexOf(a) >= PRIO.indexOf(b) ? a : b);
let prioridad = mayor(PRIO.includes(ex.prioridad_sugerida) ? ex.prioridad_sugerida : 'baja', MINIMA[tipo]);
if (ex.hay_heridos === true) prioridad = 'critica';
else if (ex.vehiculo_inmovilizado === true) prioridad = mayor(prioridad, 'alta');

const motivos = [];
if (ex.hay_heridos === true) motivos.push('Hay personas heridas.');
if (tipo === 'accidente_danos') motivos.push('Accidente o daños: implica seguro y responsabilidad.');
if (ex.posible_robo_o_fraude === true) motivos.push('Posible robo o fraude.');
if (ex.vehiculo_inmovilizado === true) motivos.push('Vehículo inmovilizado.');
if (ex.cliente_enfadado === true) motivos.push('Cliente muy molesto o con amenaza de reclamación.');
if (tipo === 'otro') motivos.push('Tipo de incidencia no reconocido.');
if (Number(ex.confianza || 0) < 0.6) motivos.push('Confianza de la clasificación baja.');

let decision, accion;
if (motivos.length) {
  decision = 'escalar_a_persona';
  accion = 'Asignar a un agente de operaciones. ' + (faltan.length ? `Mientras tanto, pedir: ${faltan.join(', ')}. ` : '') + ACCION[tipo];
} else if (faltan.length) {
  decision = 'solicitar_informacion';
  accion = 'Pedir automáticamente los datos que faltan: ' + faltan.join(', ') + '.';
} else {
  decision = 'resolver_automaticamente';
  accion = ACCION[tipo];
}

const destinatario = ex.emisor === 'cliente' ? 'cliente' : 'conductor';
const nombre = destinatario === 'cliente' ? ex.cliente : ex.conductor;
const pedir = faltan.map(c => NOMBRE[c] || c).join('; ');
let cuerpo;
if (ex.hay_heridos === true) cuerpo = 'Si hay alguna persona herida, llama ahora mismo al 112. Un responsable de operaciones te va a llamar en unos minutos.';
else if (decision === 'escalar_a_persona') cuerpo = 'Hemos recibido tu aviso y un responsable de operaciones se pondrá en contacto contigo en breve.' + (pedir ? ` Mientras tanto, por favor envíanos: ${pedir}.` : '');
else if (decision === 'solicitar_informacion') cuerpo = `Hemos recibido tu aviso. Para poder ayudarte necesitamos que nos indiques: ${pedir}.`;
else cuerpo = MENSAJE_AUTO[tipo];

return [{ json: {
  procesado_en: new Date().toISOString(),
  entrada: texto,
  clasificacion: { tipo, resumen: ex.resumen, emisor: ex.emisor, confianza: ex.confianza },
  entidades: {
    matricula: ex.matricula ?? null, modelo_vehiculo: ex.modelo_vehiculo ?? null, conductor: ex.conductor ?? null,
    telefono_contacto: ex.telefono_contacto ?? null, cliente: ex.cliente ?? null, referencia_trayecto: ex.referencia_trayecto ?? null,
    ubicacion: ex.ubicacion ?? null, hora_estimada_llegada: ex.hora_estimada_llegada ?? null, nueva_fecha: ex.nueva_fecha ?? null,
    vehiculo_inmovilizado: ex.vehiculo_inmovilizado ?? null, hay_heridos: ex.hay_heridos ?? null,
    descripcion_danos: ex.descripcion_danos ?? null, nivel_combustible_o_bateria: ex.nivel_combustible_o_bateria ?? null,
  },
  prioridad,
  informacion_faltante: faltan,
  siguiente_accion: accion,
  decision,
  puede_resolverse_automaticamente: decision !== 'escalar_a_persona',
  motivos_escalado: motivos,
  comunicacion: { destinatario, mensaje: `${nombre ? 'Hola ' + nombre + ',' : 'Hola,'}\n\n${cuerpo}\n\nGracias,\nEquipo de Operaciones` },
}}];
