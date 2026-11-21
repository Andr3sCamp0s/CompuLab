"""Modelo de dominio rico para el cierre mensual y cálculo de pagos de asistentes."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum

from compulab.dominio.errores import CierreInvalido, MarcaInvalida

DOS_DECIMALES = Decimal("0.01")
CERO = Decimal("0.00")
SEGUNDOS_POR_HORA = Decimal("3600")


def _validar_fecha_con_zona(valor: datetime, nombre_campo: str) -> None:
    if valor.tzinfo is None or valor.utcoffset() is None:
        raise MarcaInvalida(f"{nombre_campo} debe incluir zona horaria explícita.")


def _validar_texto_no_vacio(valor: str, nombre_campo: str) -> str:
    limpio = valor.strip()
    if not limpio:
        raise MarcaInvalida(f"{nombre_campo} no puede ser vacío.")
    return limpio


def _redondear(valor: Decimal) -> Decimal:
    return valor.quantize(DOS_DECIMALES, rounding=ROUND_HALF_UP)


class CategoriaAsistente(str, Enum):
    """Dos categorías oficiales definidas por la Coordinación de Soporte."""

    CATEGORIA_1 = "CATEGORIA_1"
    CATEGORIA_2 = "CATEGORIA_2"


class TarifaVigente:
    """Tarifa por hora y porcentaje de recargo vigentes para una categoría."""

    def __init__(
        self,
        categoria: CategoriaAsistente,
        tarifa_hora: Decimal,
        porcentaje_recargo: Decimal,
        vigente_desde: datetime,
    ) -> None:
        if not isinstance(categoria, CategoriaAsistente):
            raise MarcaInvalida("La categoría debe ser una CategoriaAsistente válida.")
        if not isinstance(tarifa_hora, Decimal) or tarifa_hora <= CERO:
            raise MarcaInvalida("La tarifa por hora debe ser un Decimal mayor a cero.")
        if not isinstance(porcentaje_recargo, Decimal) or porcentaje_recargo < CERO:
            raise MarcaInvalida("El porcentaje de recargo debe ser un Decimal mayor o igual a cero.")
        _validar_fecha_con_zona(vigente_desde, "vigente_desde")

        self._categoria = categoria
        self._tarifa_hora = _redondear(tarifa_hora)
        self._porcentaje_recargo = _redondear(porcentaje_recargo)
        self._vigente_desde = vigente_desde

    @property
    def categoria(self) -> CategoriaAsistente:
        return self._categoria

    @property
    def tarifa_hora(self) -> Decimal:
        return self._tarifa_hora

    @property
    def porcentaje_recargo(self) -> Decimal:
        return self._porcentaje_recargo

    @property
    def vigente_desde(self) -> datetime:
        return self._vigente_desde

    def calcular_monto(self, horas_regulares: Decimal, horas_con_recargo: Decimal) -> Decimal:
        """Calcula el monto total en colones aplicando recargo a las horas que corresponden."""
        if horas_regulares < CERO or horas_con_recargo < CERO:
            raise MarcaInvalida("Las horas a liquidar no pueden ser negativas.")
        factor_recargo = Decimal("1") + self._porcentaje_recargo
        pago_regular = horas_regulares * self._tarifa_hora
        pago_recargo = horas_con_recargo * self._tarifa_hora * factor_recargo
        return _redondear(pago_regular + pago_recargo)


class PoliticaRecargo:
    """Política de negocio que decide si un turno lleva recargo (nocturno >= 18:00 o fin de semana)."""

    def __init__(self, hora_inicio_nocturno: int = 18) -> None:
        if not (0 <= hora_inicio_nocturno <= 23):
            raise MarcaInvalida("La hora de inicio nocturno debe estar entre 0 y 23.")
        self._hora_inicio_nocturno = hora_inicio_nocturno

    @property
    def hora_inicio_nocturno(self) -> int:
        return self._hora_inicio_nocturno

    def aplica_recargo(self, inicio_turno: datetime) -> bool:
        """Devuelve True si el turno inicia a las 18:00 o después, o cae en sábado/domingo."""
        _validar_fecha_con_zona(inicio_turno, "inicio_turno")
        es_fin_de_semana = inicio_turno.weekday() >= 5
        es_nocturno = inicio_turno.hour >= self._hora_inicio_nocturno
        return es_fin_de_semana or es_nocturno


class MarcaAsistencia:
    """Registro real de entrada y salida de un asistente en un turno."""

    def __init__(
        self,
        id_marca: str,
        id_asistente: str,
        id_turno: str,
        entrada: datetime,
        salida: datetime,
    ) -> None:
        self._id_marca = _validar_texto_no_vacio(id_marca, "id_marca")
        self._id_asistente = _validar_texto_no_vacio(id_asistente, "id_asistente")
        self._id_turno = _validar_texto_no_vacio(id_turno, "id_turno")
        _validar_fecha_con_zona(entrada, "entrada")
        _validar_fecha_con_zona(salida, "salida")
        if salida <= entrada:
            raise MarcaInvalida("La marca de salida debe ser posterior a la de entrada.")
        self._entrada = entrada
        self._salida = salida

    @property
    def id_marca(self) -> str:
        return self._id_marca

    @property
    def id_asistente(self) -> str:
        return self._id_asistente

    @property
    def id_turno(self) -> str:
        return self._id_turno

    @property
    def entrada(self) -> datetime:
        return self._entrada

    @property
    def salida(self) -> datetime:
        return self._salida

    def duracion_horas(self) -> Decimal:
        """Devuelve la duración real trabajada en horas con precisión decimal."""
        segundos = Decimal(str(int((self._salida - self._entrada).total_seconds())))
        return _redondear(segundos / SEGUNDOS_POR_HORA)

    def semana_iso(self) -> tuple[int, int]:
        """Identificador (año_iso, semana_iso) para controlar el tope semanal de Becas."""
        calendario = self._entrada.isocalendar()
        return (calendario.year, calendario.week)

    def es_con_recargo(self, politica: PoliticaRecargo) -> bool:
        """Determina si las horas de esta marca llevan recargo según la política vigente."""
        return politica.aplica_recargo(self._entrada)


class AsistenteLiquidacion:
    """Datos contractuales de un asistente necesarios para consolidar su pago mensual."""

    def __init__(
        self,
        id_asistente: str,
        carne: str,
        nombre: str,
        categoria: CategoriaAsistente,
        tope_semanal_horas: Decimal,
    ) -> None:
        self._id_asistente = _validar_texto_no_vacio(id_asistente, "id_asistente")
        self._carne = _validar_texto_no_vacio(carne, "carne")
        self._nombre = _validar_texto_no_vacio(nombre, "nombre")
        if not isinstance(categoria, CategoriaAsistente):
            raise MarcaInvalida("La categoría del asistente es inválida.")
        if not isinstance(tope_semanal_horas, Decimal) or tope_semanal_horas <= CERO:
            raise MarcaInvalida("El tope semanal de horas debe ser un Decimal mayor a cero.")
        self._categoria = categoria
        self._tope_semanal_horas = _redondear(tope_semanal_horas)

    @property
    def id_asistente(self) -> str:
        return self._id_asistente

    @property
    def carne(self) -> str:
        return self._carne

    @property
    def nombre(self) -> str:
        return self._nombre

    @property
    def categoria(self) -> CategoriaAsistente:
        return self._categoria

    @property
    def tope_semanal_horas(self) -> Decimal:
        return self._tope_semanal_horas


class LineaPago:
    """Resumen consolidado de horas y monto a pagar de un asistente en un mes cerrado."""

    def __init__(
        self,
        id_asistente: str,
        carne: str,
        nombre: str,
        categoria: CategoriaAsistente,
        horas_regulares: Decimal,
        horas_con_recargo: Decimal,
        horas_sobre_tope_sin_pago: Decimal,
        tarifa_aplicada: Decimal,
        porcentaje_recargo: Decimal,
        monto_total: Decimal,
    ) -> None:
        self._id_asistente = _validar_texto_no_vacio(id_asistente, "id_asistente")
        self._carne = _validar_texto_no_vacio(carne, "carne")
        self._nombre = _validar_texto_no_vacio(nombre, "nombre")
        if not isinstance(categoria, CategoriaAsistente):
            raise CierreInvalido("La categoría de la línea de pago es inválida.")
        for nombre_campo, val in (
            ("horas_regulares", horas_regulares),
            ("horas_con_recargo", horas_con_recargo),
            ("horas_sobre_tope_sin_pago", horas_sobre_tope_sin_pago),
            ("tarifa_aplicada", tarifa_aplicada),
            ("porcentaje_recargo", porcentaje_recargo),
            ("monto_total", monto_total),
        ):
            if not isinstance(val, Decimal) or val < CERO:
                raise CierreInvalido(f"{nombre_campo} debe ser un Decimal mayor o igual a cero.")

        self._categoria = categoria
        self._horas_regulares = _redondear(horas_regulares)
        self._horas_con_recargo = _redondear(horas_con_recargo)
        self._horas_sobre_tope_sin_pago = _redondear(horas_sobre_tope_sin_pago)
        self._tarifa_aplicada = _redondear(tarifa_aplicada)
        self._porcentaje_recargo = _redondear(porcentaje_recargo)
        self._monto_total = _redondear(monto_total)

    @property
    def id_asistente(self) -> str:
        return self._id_asistente

    @property
    def carne(self) -> str:
        return self._carne

    @property
    def nombre(self) -> str:
        return self._nombre

    @property
    def categoria(self) -> CategoriaAsistente:
        return self._categoria

    @property
    def horas_regulares(self) -> Decimal:
        return self._horas_regulares

    @property
    def horas_con_recargo(self) -> Decimal:
        return self._horas_con_recargo

    @property
    def horas_sobre_tope_sin_pago(self) -> Decimal:
        return self._horas_sobre_tope_sin_pago

    @property
    def tarifa_aplicada(self) -> Decimal:
        return self._tarifa_aplicada

    @property
    def porcentaje_recargo(self) -> Decimal:
        return self._porcentaje_recargo

    @property
    def monto_total(self) -> Decimal:
        return self._monto_total

    @property
    def tuvo_exceso_tope(self) -> bool:
        return self._horas_sobre_tope_sin_pago > CERO


class CierreMensual:
    """Registro inmutable del cierre de un mes y su archivo para Becas/Planilla."""

    def __init__(
        self,
        id_cierre: str,
        anno: int,
        mes: int,
        emitido_en: datetime,
        lineas: tuple[LineaPago, ...],
        contenido_archivo_becas: str,
    ) -> None:
        if not id_cierre.strip():
            raise CierreInvalido("id_cierre no puede ser vacío.")
        if anno < 2000:
            raise CierreInvalido("El año del cierre debe ser mayor o igual a 2000.")
        if not (1 <= mes <= 12):
            raise CierreInvalido("El mes del cierre debe estar entre 1 y 12.")
        _validar_fecha_con_zona(emitido_en, "emitido_en")

        self._id_cierre = id_cierre.strip()
        self._anno = anno
        self._mes = mes
        self._emitido_en = emitido_en
        self._lineas = tuple(lineas)
        self._contenido_archivo_becas = contenido_archivo_becas

    @property
    def id_cierre(self) -> str:
        return self._id_cierre

    @property
    def anno(self) -> int:
        return self._anno

    @property
    def mes(self) -> int:
        return self._mes

    @property
    def emitido_en(self) -> datetime:
        return self._emitido_en

    @property
    def lineas(self) -> tuple[LineaPago, ...]:
        return self._lineas

    @property
    def contenido_archivo_becas(self) -> str:
        return self._contenido_archivo_becas

    @property
    def clave_periodo(self) -> tuple[int, int]:
        return (self._anno, self._mes)

    def total_a_pagar(self) -> Decimal:
        """Suma total en colones de todas las líneas de pago del cierre."""
        return _redondear(sum((linea.monto_total for linea in self._lineas), CERO))

    def asistentes_con_exceso_tope(self) -> tuple[LineaPago, ...]:
        """Devuelve las líneas de asistentes que registraron horas sobre el tope semanal."""
        return tuple(linea for linea in self._lineas if linea.tuvo_exceso_tope)
