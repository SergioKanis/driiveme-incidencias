import pytest


def _base(**kw):
    d = {
        "tipo": "retraso", "resumen": "x", "emisor": "conductor", "matricula": "1234ABC",
        "conductor": "Ana", "cliente": "Rent Norte", "ubicacion": None,
        "vehiculo_inmovilizado": None, "hay_heridos": None,
        "posible_robo_o_fraude": False, "cliente_enfadado": False,
        "prioridad_sugerida": "baja", "confianza": 0.9,
    }
    d.update(kw)
    return d


@pytest.fixture
def base():
    """Fábrica de extracciones de ejemplo (lo que devolvería el LLM)."""
    return _base


@pytest.fixture(autouse=True)
def sin_api_key(monkeypatch):
    """Por defecto ningún test llama a la API real."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
