"""Extractor heurístico (modo sin IA) y fallback cuando el LLM falla."""

import pytest

from agente import extractor
from agente.extractor import extraer_heuristico, extraer


@pytest.mark.parametrize("texto,matricula", [
    ("Llevo el coche 4821 LKP", "4821LKP"),
    ("matrícula 4821-lkp", "4821LKP"),
    ("matricula 4821LKP.", "4821LKP"),
    ("sin matrícula en el texto", None),
    ("referencia 4821 AEI", None),  # las vocales no existen en matrículas españolas
], ids=["con_espacio", "con_guion", "pegada", "sin_matricula", "con_vocales"])
def test_matricula(texto, matricula):
    assert extraer_heuristico(texto)["matricula"] == matricula


@pytest.mark.parametrize("texto,tipo", [
    ("He tenido un golpe en la puerta", "accidente_danos"),
    ("El coche no arranca", "averia"),
    ("Hay atasco, llegaré tarde", "retraso"),
    ("El cliente no contesta y no está", "cliente_ausente"),
    ("No encuentro las llaves", "llaves_documentacion"),
    ("Me quedo sin gasolina", "combustible_carga"),
    ("Quiero reprogramar la entrega", "cambio_cita"),
    ("Hola, una consulta", "otro"),
], ids=["golpe", "no_arranca", "atasco", "cliente_no_esta", "llaves", "gasolina", "reprogramar", "consulta"])
def test_tipo(texto, tipo):
    assert extraer_heuristico(texto)["tipo"] == tipo


def test_detecta_heridos_y_robo():
    ex = extraer_heuristico("Me han robado el coche y hay un herido")
    assert ex["hay_heridos"] is True
    assert ex["posible_robo_o_fraude"] is True


def test_heuristico_siempre_confianza_baja():
    assert extraer_heuristico("El coche no arranca")["confianza"] < 0.6


def test_sin_api_key_usa_heuristico():
    _, metodo = extraer("El coche no arranca")
    assert metodo == "heuristico"


def test_si_el_llm_falla_usa_heuristico(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "clave-falsa")

    def falla(_):
        raise ConnectionError("sin red")

    monkeypatch.setattr(extractor, "extraer_con_llm", falla)
    _, metodo = extraer("El coche no arranca")
    assert metodo == "heuristico"


def test_con_llm_disponible_usa_llm(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "clave-falsa")
    monkeypatch.setattr(extractor, "extraer_con_llm", lambda t: {"tipo": "retraso"})
    ex, metodo = extraer("Llegaré tarde")
    assert metodo.startswith("llm")
    assert ex["tipo"] == "retraso"
