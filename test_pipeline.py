"""Pipeline completo, mensajes generados y ejemplos de la carpeta ejemplos/."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

from agente import procesar_incidencia
from agente.responder import mensaje_plantilla
from agente.rules import decidir

RAIZ = Path(__file__).resolve().parent.parent
CLAVES = ["procesado_en", "metodo_extraccion", "entrada", "clasificacion", "entidades",
          "prioridad", "informacion_faltante", "siguiente_accion", "decision",
          "puede_resolverse_automaticamente", "motivos_escalado", "comunicacion"]


# --- Estructura de salida ----------------------------------------------------

def test_salida_tiene_todas_las_claves(base):
    out = procesar_incidencia("texto", extraccion=base(hora_estimada_llegada="18:30"))
    assert set(CLAVES) <= set(out)


def test_salida_es_serializable_a_json(base):
    out = procesar_incidencia("texto", extraccion=base())
    json.loads(json.dumps(out, ensure_ascii=False))


def test_coherencia_decision_y_flag_automatico(base):
    for ex in [base(hora_estimada_llegada="18:30"), base(matricula=None), base(tipo="otro")]:
        out = procesar_incidencia("t", extraccion=ex)
        assert out["puede_resolverse_automaticamente"] == (out["decision"] != "escalar_a_persona")


# --- Mensajes ----------------------------------------------------------------

def test_mensaje_con_heridos_empieza_por_112(base):
    ex = base(tipo="accidente_danos", hay_heridos=True)
    msg = mensaje_plantilla(ex, decidir(ex))
    assert "112" in msg.split("\n\n")[1]


def test_mensaje_pide_los_datos_que_faltan(base):
    ex = base(matricula=None)
    msg = mensaje_plantilla(ex, decidir(ex))
    assert "matrícula" in msg
    assert "hora estimada" in msg


def test_mensaje_escalado_no_promete_solucion(base):
    ex = base(tipo="otro")
    msg = mensaje_plantilla(ex, decidir(ex))
    assert "responsable" in msg
    assert "ya estamos gestionándolo" not in msg


def test_mensaje_va_al_cliente_si_escribe_el_cliente(base):
    ex = base(emisor="cliente", cliente="Flotas Ibéricas", hora_estimada_llegada="18:30")
    out = procesar_incidencia("t", extraccion=ex)
    assert out["comunicacion"]["destinatario"] == "cliente"
    assert "Flotas Ibéricas" in out["comunicacion"]["mensaje"]


def test_saludo_generico_sin_nombre(base):
    ex = base(conductor=None, hora_estimada_llegada="18:30")
    assert mensaje_plantilla(ex, decidir(ex)).startswith("Hola,")


# --- Ejemplos reales (modo sin IA) -------------------------------------------

EJEMPLOS = sorted((RAIZ / "ejemplos").glob("*.txt"))


@pytest.mark.parametrize("fichero", EJEMPLOS, ids=lambda p: p.stem)
def test_ejemplos_sin_ia_se_escalan(fichero):
    """Sin API key la confianza es baja, así que todo debe ir a una persona (fallo seguro)."""
    out = procesar_incidencia(fichero.read_text(encoding="utf-8"))
    assert out["metodo_extraccion"] == "heuristico"
    assert out["decision"] == "escalar_a_persona"


def test_hay_ejemplos():
    assert len(EJEMPLOS) >= 3


# --- Línea de comandos -------------------------------------------------------

def test_cli_devuelve_json_valido():
    r = subprocess.run([sys.executable, "main.py", "El coche 4821LKP no arranca"],
                       cwd=RAIZ, capture_output=True, text=True, encoding="utf-8",
                       env={"PATH": "", "PYTHONIOENCODING": "utf-8"})
    assert r.returncode == 0, r.stderr
    out = json.loads(r.stdout)
    assert out["entidades"]["matricula"] == "4821LKP"
