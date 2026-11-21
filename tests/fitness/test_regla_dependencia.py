"""Función de aptitud 1: verifica la Regla de Dependencia en la capa de dominio.

El dominio no puede importar capas externas (aplicación o infraestructura) ni
dependencias reales de base de datos, red, sistema de archivos o reloj del sistema.
"""

from __future__ import annotations

import ast
from pathlib import Path

RAIZ_DOMINIO = Path(__file__).resolve().parents[2] / "compulab" / "dominio"

PREFIJOS_IMPORT_PROHIBIDOS = (
    "compulab.aplicacion",
    "compulab.infraestructura",
    "psycopg2",
    "psycopg",
    "sqlalchemy",
    "sqlite3",
    "requests",
    "httpx",
    "urllib",
    "http",
    "socket",
    "pathlib",
    "os",
    "subprocess",
    "redis",
    "valkey",
)

LLAMADAS_RELOJ_PROHIBIDAS = {"now", "utcnow", "today"}


def verificar_regla_dependencia(directorio_dominio: Path) -> list[str]:
    """Recorre todos los .py del directorio y reporta violaciones a la Regla de Dependencia."""
    violaciones: list[str] = []

    for archivo in sorted(directorio_dominio.rglob("*.py")):
        arbol = ast.parse(archivo.read_text(encoding="utf-8"), filename=str(archivo))
        for nodo in ast.walk(arbol):
            if isinstance(nodo, ast.Import):
                for alias in nodo.names:
                    if _es_import_prohibido(alias.name):
                        violaciones.append(
                            f"{archivo.name}:{nodo.lineno} importa módulo prohibido '{alias.name}'"
                        )
            elif isinstance(nodo, ast.ImportFrom) and nodo.module:
                if _es_import_prohibido(nodo.module):
                    violaciones.append(
                        f"{archivo.name}:{nodo.lineno} importa desde módulo prohibido '{nodo.module}'"
                    )
            elif isinstance(nodo, ast.Call) and isinstance(nodo.func, ast.Attribute):
                if nodo.func.attr in LLAMADAS_RELOJ_PROHIBIDAS:
                    violaciones.append(
                        f"{archivo.name}:{nodo.lineno} invoca reloj del sistema '.{nodo.func.attr}()'"
                    )

    return violaciones


def _es_import_prohibido(nombre_modulo: str) -> bool:
    return any(
        nombre_modulo == prefijo or nombre_modulo.startswith(f"{prefijo}.")
        for prefijo in PREFIJOS_IMPORT_PROHIBIDOS
    )


def test_fitness_dominio_cumple_regla_de_dependencia():
    """El build falla si cualquier archivo en compulab/dominio viola la Regla de Dependencia."""
    violaciones = verificar_regla_dependencia(RAIZ_DOMINIO)
    assert violaciones == [], "Violaciones a la Regla de Dependencia:\n" + "\n".join(
        violaciones
    )


def test_fitness_regla_de_dependencia_detecta_violacion_plantada(tmp_path: Path):
    """Prueba de la función de aptitud: planta violaciones a propósito y exige detectarlas."""
    archivo_malo = tmp_path / "entidad_contaminada.py"
    archivo_malo.write_text(
        "import psycopg2\n"
        "from compulab.infraestructura.exportador_becas import ExportadorBecasCSV\n"
        "from datetime import datetime\n"
        "ahora = datetime.now()\n",
        encoding="utf-8",
    )

    violaciones = verificar_regla_dependencia(tmp_path)

    assert len(violaciones) == 3
    assert any("psycopg2" in v for v in violaciones)
    assert any("compulab.infraestructura" in v for v in violaciones)
    assert any(".now()" in v for v in violaciones)
