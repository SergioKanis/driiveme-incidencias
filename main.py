"""
Uso:
  python main.py "texto de la incidencia"
  python main.py ejemplos/01_averia.txt
  python main.py --todos            # procesa ejemplos/*.txt y guarda en ejemplos/salidas/
"""

import json
import sys
from pathlib import Path

from agente import procesar_incidencia

RAIZ = Path(__file__).parent


def leer_entrada(arg: str) -> str:
    ruta = Path(arg)
    return ruta.read_text(encoding="utf-8") if ruta.is_file() else arg


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    if sys.argv[1] == "--todos":
        salidas = RAIZ / "ejemplos" / "salidas"
        salidas.mkdir(parents=True, exist_ok=True)
        for fichero in sorted((RAIZ / "ejemplos").glob("*.txt")):
            resultado = procesar_incidencia(fichero.read_text(encoding="utf-8"))
            destino = salidas / f"{fichero.stem}.json"
            destino.write_text(json.dumps(resultado, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"{fichero.name:35} -> {resultado['decision']:26} prioridad={resultado['prioridad']}")
        return

    resultado = procesar_incidencia(leer_entrada(" ".join(sys.argv[1:])))
    print(json.dumps(resultado, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
