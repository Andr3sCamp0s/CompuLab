"""Dobles en memoria para ejecutar pruebas rápidas sin base de datos ni red."""

from __future__ import annotations

from datetime import datetime

from compulab.dominio.liquidacion import (
    AsistenteLiquidacion,
    CategoriaAsistente,
    CierreMensual,
    MarcaAsistencia,
    TarifaVigente,
)


class RelojFijo:
    """Reloj determinista para pruebas."""

    def __init__(self, instante: datetime) -> None:
        self._instante = instante

    def ahora(self) -> datetime:
        return self._instante

    def fijar(self, instante: datetime) -> None:
        self._instante = instante


class NotificadorEspia:
    """Guarda en memoria todas las notificaciones emitidas durante una prueba."""

    def __init__(self) -> None:
        self.enviadas: list[tuple[str, str, str]] = []

    def notificar(self, destinatario: str, asunto: str, mensaje: str) -> None:
        self.enviadas.append((destinatario, asunto, mensaje))


class CatalogoTarifasEnMemoria:
    """Devuelve la tarifa más reciente cuya vigencia sea <= momento solicitado."""

    def __init__(self, tarifas: list[TarifaVigente] | None = None) -> None:
        self._tarifas: list[TarifaVigente] = list(tarifas or [])

    def agregar(self, tarifa: TarifaVigente) -> None:
        self._tarifas.append(tarifa)

    def vigente_en(
        self, categoria: CategoriaAsistente, momento: datetime
    ) -> TarifaVigente | None:
        candidatas = [
            t
            for t in self._tarifas
            if t.categoria == categoria and t.vigente_desde <= momento
        ]
        if not candidatas:
            return None
        return max(candidatas, key=lambda t: t.vigente_desde)


class RepositorioMarcasEnMemoria:
    """Almacena marcas de asistencia en memoria filtrables por año y mes."""

    def __init__(self, marcas: list[MarcaAsistencia] | None = None) -> None:
        self._marcas: list[MarcaAsistencia] = list(marcas or [])

    def agregar(self, marca: MarcaAsistencia) -> None:
        self._marcas.append(marca)

    def por_mes(self, anno: int, mes: int) -> list[MarcaAsistencia]:
        return [
            m
            for m in self._marcas
            if m.entrada.year == anno and m.entrada.month == mes
        ]


class RepositorioAsistentesLiquidacionEnMemoria:
    """Almacena datos de asistentes para liquidación en memoria."""

    def __init__(self, asistentes: list[AsistenteLiquidacion] | None = None) -> None:
        self._asistentes: list[AsistenteLiquidacion] = list(asistentes or [])

    def agregar(self, asistente: AsistenteLiquidacion) -> None:
        self._asistentes.append(asistente)

    def listar_para_liquidacion(self) -> list[AsistenteLiquidacion]:
        return list(self._asistentes)


class RepositorioCierresEnMemoria:
    """Almacena cierres mensuales por clave (anno, mes)."""

    def __init__(self) -> None:
        self._cierres: dict[tuple[int, int], CierreMensual] = {}

    def por_periodo(self, anno: int, mes: int) -> CierreMensual | None:
        return self._cierres.get((anno, mes))

    def guardar(self, cierre: CierreMensual) -> None:
        self._cierres[cierre.clave_periodo] = cierre

    def total_guardados(self) -> int:
        return len(self._cierres)
