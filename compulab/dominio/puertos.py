"""Puertos (interfaces requeridas) del núcleo de dominio CompuLab.

Todas las dependencias externas (persistencia, reloj, notificaciones, exportación)
se declaran como Protocol para mantener el dominio desacoplado y testeable con dobles.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Protocol

from compulab.dominio.liquidacion import (
    AsistenteLiquidacion,
    CategoriaAsistente,
    CierreMensual,
    LineaPago,
    MarcaAsistencia,
    TarifaVigente,
)


# --- Puertos transversales ---


class Reloj(Protocol):
    """Fuente oficial de hora institucional (inyectada para evitar datetime.now())."""

    def ahora(self) -> datetime: ...


class Notificador(Protocol):
    """Canal para enviar avisos operativos (coordinadores y estudiantes)."""

    def notificar(self, destinatario: str, asunto: str, mensaje: str) -> None: ...


# --- Puertos de Liquidación / Cierre Mensual (CU-3) ---


class CatalogoTarifas(Protocol):
    """Consulta las tarifas y recargos vigentes en una fecha dada."""

    def vigente_en(
        self, categoria: CategoriaAsistente, momento: datetime
    ) -> TarifaVigente | None: ...


class RepositorioMarcas(Protocol):
    """Acceso a las marcas reales de entrada y salida de los asistentes."""

    def por_mes(self, anno: int, mes: int) -> list[MarcaAsistencia]: ...


class RepositorioAsistentesLiquidacion(Protocol):
    """Consulta los datos contractuales de asistentes para el cierre mensual."""

    def listar_para_liquidacion(self) -> list[AsistenteLiquidacion]: ...


class RepositorioCierres(Protocol):
    """Persistencia inmutable e idempotente de cierres mensuales."""

    def por_periodo(self, anno: int, mes: int) -> CierreMensual | None: ...

    def guardar(self, cierre: CierreMensual) -> None: ...


class ExportadorBecas(Protocol):
    """Capa anticorrupción para generar el archivo que acepta la Oficina de Becas."""

    def generar_archivo(
        self, anno: int, mes: int, lineas: tuple[LineaPago, ...]
    ) -> str: ...


# --- Puertos base para Horarios (CU-1) y Reservas de Máquinas (CU-2) ---
# Contratos estructurales listos para que el módulo de horarios y máquinas los consuma.


class RepositorioAsistentes(Protocol):
    """Consulta de asistentes activos, su disponibilidad y su tope semanal."""

    def por_id(self, id_asistente: str) -> Any: ...


class RepositorioTurnos(Protocol):
    """Consulta y persistencia de turnos de laboratorio."""

    def de_asistente_en_semana(
        self, id_asistente: str, anno_iso: int, semana_iso: int
    ) -> list[Any]: ...

    def de_laboratorio_en_rango(
        self, id_laboratorio: str, inicio: datetime, fin: datetime
    ) -> list[Any]: ...

    def guardar(self, turno: Any) -> None: ...


class RepositorioMaquinas(Protocol):
    """Consulta de máquinas por identificador y estado de servicio."""

    def por_id(self, id_maquina: str) -> Any: ...


class RepositorioReservas(Protocol):
    """Consulta y persistencia de reservas de máquinas."""

    def activas_de_estudiante(self, carne_estudiante: str) -> list[Any]: ...

    def de_estudiante_en_semana(
        self, carne_estudiante: str, anno_iso: int, semana_iso: int
    ) -> list[Any]: ...

    def de_maquina_en_rango(
        self, id_maquina: str, inicio: datetime, fin: datetime
    ) -> list[Any]: ...

    def guardar(self, reserva: Any) -> None: ...
