"""Excepciones de dominio tipificadas para los casos de uso de CompuLab."""

from __future__ import annotations


class ErrorDeDominio(Exception):
    """Base de todos los errores de negocio del dominio CompuLab."""


# --- Errores de Horarios / Asignar Turno (CU-1) ---


class AsistenteInactivo(ErrorDeDominio):
    """El asistente renunció o fue dado de baja y no puede recibir turnos nuevos."""


class CoordinadorNoAutorizado(ErrorDeDominio):
    """El coordinador de laboratorio intenta modificar un laboratorio que no le corresponde."""


class TraslapeDeTurno(ErrorDeDominio):
    """El turno se traslapa con otro turno ya asignado al mismo asistente."""


class TopeSemanalExcedido(ErrorDeDominio):
    """Asignar el turno haría que el asistente supere su tope semanal de horas de Becas."""


class BloqueFueraDeDisponibilidad(ErrorDeDominio):
    """El bloque no fue declarado disponible por el asistente y no cuenta con su aceptación."""


class TurnoInvalido(ErrorDeDominio):
    """Los datos estructurales del turno incumplen una invariante del dominio."""


# --- Errores de Máquinas / Reservar Máquina (CU-2) ---


class LaboratorioCerrado(ErrorDeDominio):
    """La franja solicitada no está cubierta por ningún turno de asistente."""


class MaquinaFueraDeServicio(ErrorDeDominio):
    """La máquina está marcada fuera de servicio y no puede reservarse."""


class DuracionReservaExcedida(ErrorDeDominio):
    """La reserva supera el límite máximo permitido de dos horas."""


class LimiteReservasActivasExcedido(ErrorDeDominio):
    """El estudiante ya tiene una reserva activa en curso."""


class LimiteHorasSemanalesExcedido(ErrorDeDominio):
    """La reserva haría superar el límite de seis horas semanales del estudiante."""


class MaquinaYaReservada(ErrorDeDominio):
    """La máquina ya tiene otra reserva activa en el horario solicitado."""


class ReservaInvalida(ErrorDeDominio):
    """Los datos estructurales de la reserva incumplen una invariante del dominio."""


# --- Errores de Liquidación / Cerrar Mes (CU-3) ---


class PeriodoNoFinalizado(ErrorDeDominio):
    """No se puede cerrar un mes que aún está en curso o es futuro."""


class TarifaNoEncontrada(ErrorDeDominio):
    """No existe una tarifa vigente registrada para la categoría y fecha solicitadas."""


class CierreInvalido(ErrorDeDominio):
    """Los datos del periodo o del cierre mensual incumplen una invariante."""


class MarcaInvalida(ErrorDeDominio):
    """Una marca de asistencia o entidad de liquidación incumple una invariante."""
