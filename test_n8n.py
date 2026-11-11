"""Workflow de n8n: estructura válida y misma lógica que la versión Python."""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from agente.rules import decidir

RAIZ = Path(__file__).resolve().parent.parent
WORKFLOW = json.loads((RAIZ / "n8n" / "workflow_incidencias.json").read_text(encoding="utf-8"))
NODOS = {n["name"]: n for n in WORKFLOW["nodes"]}


def test_conexiones_apuntan_a_nodos_existentes():
    for origen, salidas in WORKFLOW["connections"].items():
        assert origen in NODOS
        for rama in salidas["main"]:
            for destino in rama:
                assert destino["node"] in NODOS


def test_flujo_empieza_en_webhook_y_responde_json():
    tipos = {n["type"] for n in WORKFLOW["nodes"]}
    assert "n8n-nodes-base.webhook" in tipos
    assert "n8n-nodes-base.respondToWebhook" in tipos


def test_switch_tiene_las_tres_decisiones():
    switch = NODOS["Según decisión"]
    valores = {r["conditions"]["conditions"][0]["rightValue"]
               for r in switch["parameters"]["rules"]["values"]}
    assert valores == {"resolver_automaticamente", "solicitar_informacion", "escalar_a_persona"}


def test_codigo_del_workflow_coincide_con_src():
    assert NODOS["Reglas de negocio"]["parameters"]["jsCode"] == \
        (RAIZ / "n8n" / "src" / "reglas.js").read_text(encoding="utf-8")


def test_no_hay_api_key_en_el_workflow():
    assert "sk-ant-" not in json.dumps(WORKFLOW)


# --- Paridad Python <-> JavaScript ------------------------------------------

CASOS = [
    dict(tipo="retraso", hora_estimada_llegada="18:30"),
    dict(tipo="retraso", matricula=None),
    dict(tipo="accidente_danos", hay_heridos=True),
    dict(tipo="accidente_danos", ubicacion="x", descripcion_danos="x", hay_heridos=False),
    dict(tipo="averia", ubicacion="A-3", vehiculo_inmovilizado=True),
    dict(tipo="averia", ubicacion="A-3", vehiculo_inmovilizado=False),
    dict(tipo="cliente_ausente", ubicacion="x", referencia_trayecto="R1", cliente_enfadado=True),
    dict(tipo="cambio_cita", referencia_trayecto="R1", nueva_fecha="lunes", prioridad_sugerida="alta"),
    dict(tipo="otro"),
    dict(tipo="inventado", hora_estimada_llegada="18:30"),
    dict(tipo="retraso", hora_estimada_llegada="18:30", confianza=0.4),
]

RUNNER = """
const code = require('fs').readFileSync(process.argv[1], 'utf8');
const casos = JSON.parse(process.argv[2]);
const fn = new Function('$json', '$', code);
const $ = () => ({ first: () => ({ json: { incidencia: 't' } }) });
console.log(JSON.stringify(casos.map(c => {
  const o = fn({ content: [{ type: 'tool_use', input: c }] }, $)[0].json;
  return [o.decision, o.prioridad, o.informacion_faltante];
})));
"""


@pytest.mark.skipif(shutil.which("node") is None, reason="Node.js no instalado")
def test_misma_decision_en_python_y_en_n8n(base):
    extracciones = [base(**c) for c in CASOS]
    r = subprocess.run(["node", "-e", RUNNER, str(RAIZ / "n8n" / "src" / "reglas.js"),
                        json.dumps(extracciones)], capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 0, r.stderr
    js = json.loads(r.stdout)
    for ex, (dec, prio, faltan) in zip(extracciones, js):
        py = decidir(ex)
        assert (py["decision"], py["prioridad"], py["informacion_faltante"]) == (dec, prio, faltan), ex
