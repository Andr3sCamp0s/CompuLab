"""Función de aptitud 2: verifica encapsulamiento y precisión monetaria en el dominio.

Exige que:
1. Las entidades de dominio (con __init__) solo asignen atributos privados (self._...)
   para evitar modelos anémicos con estado público mutable.
2. El módulo liquidacion.py nunca utilice 'float' para dinero ni horas (debe usar Decimal).
"""

from __future__ import annotations

import ast
from pathlib import Path

RAIZ_DOMINIO = Path(__file__).resolve().parents[2] / "compulab" / "dominio"


def verificar_integridad_dominio(directorio_dominio: Path) -> list[str]:
    """Inspecciona el AST del dominio en busca de atributos públicos en __init__ o uso de float."""
    violaciones: list[str] = []

    for archivo in sorted(directorio_dominio.rglob("*.py")):
        arbol = ast.parse(archivo.read_text(encoding="utf-8"), filename=str(archivo))

        # 1. Verificar atributos privados en __init__ de las clases de dominio
        for nodo in arbol.body:
            if isinstance(nodo, ast.ClassDef) and not _es_excepcion_o_protocolo(nodo):
                for miembro in nodo.body:
                    if isinstance(miembro, ast.FunctionDef) and miembro.name == "__init__":
                        violaciones.extend(
                            _revisar_atributos_privados(archivo.name, nodo.name, miembro)
                        )

        # 2. Prohibir float en el módulo de liquidación (dinero y horas deben usar Decimal)
        if archivo.name == "liquidacion.py":
            violaciones.extend(_revisar_sin_float(archivo.name, arbol))

    return violaciones


def _es_excepcion_o_protocolo(clase: ast.ClassDef) -> bool:
    nombres_bases = {
        base.id for base in clase.bases if isinstance(base, ast.Name)
    }
    return bool(nombres_bases & {"Exception", "ErrorDeDominio", "Protocol", "Enum"})


def _revisar_atributos_privados(
    nombre_archivo: str, nombre_clase: str, init_fn: ast.FunctionDef
) -> list[str]:
    errores: list[str] = []
    for sub in ast.walk(init_fn):
        objetivos: list[ast.expr] = []
        if isinstance(sub, ast.Assign):
            objetivos.extend(sub.targets)
        elif isinstance(sub, ast.AnnAssign):
            objetivos.append(sub.target)

        for objetivo in objetivos:
            if (
                isinstance(objetivo, ast.Attribute)
                and isinstance(objetivo.value, ast.Name)
                and objetivo.value.id == "self"
                and not objetivo.attr.startswith("_")
            ):
                errores.append(
                    f"{nombre_archivo}:{sub.lineno} {nombre_clase}.__init__ asigna "
                    f"atributo público 'self.{objetivo.attr}' (debe ser privado con '_')"
                )
    return errores


def _revisar_sin_float(nombre_archivo: str, arbol: ast.AST) -> list[str]:
    errores: list[str] = []
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Name) and nodo.id == "float":
            errores.append(
                f"{nombre_archivo}:{nodo.lineno} usa 'float' en liquidación (debe usar Decimal)"
            )
        elif isinstance(nodo, ast.Constant) and isinstance(nodo.value, float):
            errores.append(
                f"{nombre_archivo}:{nodo.lineno} usa literal flotante '{nodo.value}' (debe usar Decimal)"
            )
    return errores


def test_fitness_dominio_cumple_encapsulamiento_y_precision():
    """El build falla si el dominio expone atributos públicos en __init__ o usa float en dinero."""
    violaciones = verificar_integridad_dominio(RAIZ_DOMINIO)
    assert violaciones == [], "Violaciones de integridad en dominio:\n" + "\n".join(
        violaciones
    )


def test_fitness_integridad_dominio_detecta_violacion_plantada(tmp_path: Path):
    """Prueba de la función de aptitud: planta un atributo público y un float y exige detectarlos."""
    archivo_malo = tmp_path / "liquidacion.py"
    archivo_malo.write_text(
        "class PagoMalo:\n"
        "    def __init__(self, monto: float) -> None:\n"
        "        self.monto = monto + 0.5\n",
        encoding="utf-8",
    )

    violaciones = verificar_integridad_dominio(tmp_path)

    assert len(violaciones) == 3
    assert any("self.monto" in v for v in violaciones)
    assert any("usa 'float'" in v for v in violaciones)
    assert any("literal flotante '0.5'" in v for v in violaciones)
