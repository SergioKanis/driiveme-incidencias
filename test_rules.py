"""Capa de reglas: información faltante, prioridad y escalado."""

import pytest

from agente.rules import decidir, campos_faltantes, prioridad_final


# --- Decisión ---------------------------------------------------------------

def test_retraso_completo_se_resuelve_solo(base):
    r = decidir(base(hora_estimada_llegada="18:30"))
    assert r["decision"] == "resolver_automaticamente"
    assert r["informacion_faltante"] == []
    assert r["motivos_escalado"] == []


def test_falta_informacion_se_pide(base):
    r = decidir(base(matricula=None))
    assert r["decision"] == "solicitar_informacion"
    assert set(r["informacion_faltante"]) == {"matricula", "hora_estimada_llegada"}


def test_accidente_siempre_escala(base):
    r = decidir(base(tipo="accidente_danos", ubicacion="Parking",
                     descripcion_danos="golpe", hay_heridos=False))
    assert r["decision"] == "escalar_a_persona"


def test_accidente_escala_aunque_falten_datos_y_los_pide(base):
    r = decidir(base(tipo="accidente_danos", matricula=None))
    assert r["decision"] == "escalar_a_persona"
    assert "matricula" in r["informacion_faltante"]
    assert "pedir" in r["siguiente_accion"].lower()


@pytest.mark.parametrize("campo", ["posible_robo_o_fraude", "cliente_enfadado"])
def test_banderas_de_riesgo_escalan(base, campo):
    r = decidir(base(hora_estimada_llegada="18:30", **{campo: True}))
    assert r["decision"] == "escalar_a_persona"
    assert r["motivos_escalado"]


def test_tipo_otro_escala(base):
    assert decidir(base(tipo="otro"))["decision"] == "escalar_a_persona"


def test_tipo_desconocido_se_trata_como_otro_y_escala(base):
    r = decidir(base(tipo="inventado", hora_estimada_llegada="18:30"))
    assert r["decision"] == "escalar_a_persona"


def test_averia_inmovilizada_escala(base):
    r = decidir(base(tipo="averia", ubicacion="A-3", vehiculo_inmovilizado=True))
    assert r["decision"] == "escalar_a_persona"
    assert r["prioridad"] == "alta"


def test_averia_que_puede_circular_se_resuelve(base):
    r = decidir(base(tipo="averia", ubicacion="A-3 km 186", vehiculo_inmovilizado=False))
    assert r["decision"] == "resolver_automaticamente"


# --- Umbral de confianza -----------------------------------------------------

@pytest.mark.parametrize("confianza,escala", [(0.3, True), (0.59, True), (0.6, False), (0.95, False)])
def test_umbral_de_confianza(base, confianza, escala):
    r = decidir(base(hora_estimada_llegada="18:30", confianza=confianza))
    assert (r["decision"] == "escalar_a_persona") is escala


def test_confianza_ausente_escala(base):
    ex = base(hora_estimada_llegada="18:30")
    del ex["confianza"]
    assert decidir(ex)["decision"] == "escalar_a_persona"


# --- Prioridad ---------------------------------------------------------------

def test_prioridad_sube_a_la_minima_del_tipo(base):
    assert prioridad_final(base(prioridad_sugerida="baja")) == "media"


def test_el_llm_puede_subir_la_prioridad(base):
    assert prioridad_final(base(prioridad_sugerida="alta")) == "alta"


def test_el_llm_no_puede_bajar_la_prioridad(base):
    assert prioridad_final(base(tipo="accidente_danos", prioridad_sugerida="baja")) == "alta"


def test_heridos_prioridad_critica(base):
    assert prioridad_final(base(tipo="accidente_danos", hay_heridos=True)) == "critica"


def test_prioridad_invalida_del_llm_se_ignora(base):
    assert prioridad_final(base(prioridad_sugerida="urgentisima")) == "media"


# --- Información faltante ----------------------------------------------------

def test_false_cuenta_como_dato_presente(base):
    faltan = campos_faltantes(base(tipo="accidente_danos", ubicacion="x",
                                   descripcion_danos="x", hay_heridos=False))
    assert "hay_heridos" not in faltan


def test_null_en_heridos_cuenta_como_falta(base):
    faltan = campos_faltantes(base(tipo="accidente_danos", ubicacion="x", descripcion_danos="x"))
    assert faltan == ["hay_heridos"]


@pytest.mark.parametrize("vacio", ["", "   ", None], ids=["vacia", "espacios", "null"])
def test_cadena_vacia_cuenta_como_falta(base, vacio):
    assert "matricula" in campos_faltantes(base(matricula=vacio))


def test_cambio_cita_exige_referencia_y_fecha(base):
    faltan = campos_faltantes(base(tipo="cambio_cita"))
    assert set(faltan) == {"referencia_trayecto", "nueva_fecha"}
