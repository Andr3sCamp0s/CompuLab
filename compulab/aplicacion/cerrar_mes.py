"""Controlador del caso de uso CU-3: Cerrar el mes y generar archivo para Becas."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from decimal import Decimal

from compulab.dominio.errores import (
    CierreInvalido,
    PeriodoNoFinalizado,
    TarifaNoEncontrada,
)
from compulab.dominio.liquidacion import (
    CERO,
    AsistenteLiquidacion,
    CierreMensual,
    LineaPago,
    MarcaAsistencia,
    PoliticaRecargo,
)
from compulab.dominio.puertos import (
    CatalogoTarifas,
    ExportadorBecas,
    Notificador,
    Reloj,
    RepositorioAsistentesLiquidacion,
    RepositorioCierres,
    RepositorioMarcas,
)

DESTINATARIO_SOPORTE = "coordinacion-soporte"


class CerrarMes:
    """Realiza el caso de uso «Cerrar el mes y generar archivo para Becas»."""

    def __init__(
        self,
        marcas: RepositorioMarcas,
        asistentes: RepositorioAsistentesLiquidacion,
        tarifas: CatalogoTarifas,
        cierres: RepositorioCierres,
        exportador: ExportadorBecas,
        reloj: Reloj,
        notificador: Notificador,
        politica_recargo: PoliticaRecargo | None = None,
    ) -> None:
        self._marcas = marcas
        self._asistentes = asistentes
        self._tarifas = tarifas
        self._cierres = cierres
        self._exportador = exportador
        self._reloj = reloj
        self._notificador = notificador
        self._politica_recargo = politica_recargo or PoliticaRecargo()

    def ejecutar(self, anno: int, mes: int) -> CierreMensual:
        """Consolida horas reales del mes, calcula pagos y genera el archivo para Becas."""
        if anno < 2000 or not (1 <= mes <= 12):
            raise CierreInvalido(f"Periodo inválido: {anno}-{mes:02d}.")

        ahora = self._reloj.ahora()
        # paso 1: verificar que el periodo solicitado ya concluyó
        if (ahora.year, ahora.month) <= (anno, mes):  # ext 1a
            raise PeriodoNoFinalizado(
                f"El mes {anno}-{mes:02d} todavía no ha finalizado."
            )

        # paso 2: idempotencia e inmutabilidad — si ya existe cierre, se devuelve intacto
        existente = self._cierres.por_periodo(anno, mes)
        if existente is not None:  # ext 2a
            return existente

        # paso 3: obtener asistentes y marcas reales del mes
        asistentes_por_id = {
            a.id_asistente: a for a in self._asistentes.listar_para_liquidacion()
        }
        marcas_mes = self._marcas.por_mes(anno, mes)
        marcas_por_asistente: dict[str, list[MarcaAsistencia]] = defaultdict(list)
        for marca in marcas_mes:
            marcas_por_asistente[marca.id_asistente].append(marca)

        fecha_referencia = datetime(anno, mes, 1, tzinfo=ahora.tzinfo)
        lineas: list[LineaPago] = []

        # paso 4: consolidar horas por semana, aplicar tope semanal, recargos y tarifa vigente
        for id_asistente in sorted(marcas_por_asistente.keys()):
            asistente = asistentes_por_id.get(id_asistente)
            if asistente is None:
                continue
            tarifa = self._tarifas.vigente_en(asistente.categoria, fecha_referencia)
            if tarifa is None:  # ext 3a
                raise TarifaNoEncontrada(
                    f"No hay tarifa vigente para {asistente.categoria.value} en {anno}-{mes:02d}."
                )

            horas_reg, horas_rec, horas_exceso = self._clasificar_horas_mes(
                asistente, marcas_por_asistente[id_asistente]
            )
            monto = tarifa.calcular_monto(horas_reg, horas_rec)
            lineas.append(
                LineaPago(
                    id_asistente=asistente.id_asistente,
                    carne=asistente.carne,
                    nombre=asistente.nombre,
                    categoria=asistente.categoria,
                    horas_regulares=horas_reg,
                    horas_con_recargo=horas_rec,
                    horas_sobre_tope_sin_pago=horas_exceso,
                    tarifa_aplicada=tarifa.tarifa_hora,
                    porcentaje_recargo=tarifa.porcentaje_recargo,
                    monto_total=monto,
                )
            )

        lineas_inmutables = tuple(lineas)

        # paso 5: generar el archivo en el formato que acepta la Oficina de Becas
        archivo_becas = self._exportador.generar_archivo(anno, mes, lineas_inmutables)

        # paso 6: persistir el cierre mensual inmutable
        cierre = CierreMensual(
            id_cierre=f"CIERRE-{anno}-{mes:02d}",
            anno=anno,
            mes=mes,
            emitido_en=ahora,
            lineas=lineas_inmutables,
            contenido_archivo_becas=archivo_becas,
        )
        self._cierres.guardar(cierre)

        # paso 7: avisar a Coordinación de Soporte si hubo horas sobre el tope semanal
        for linea in cierre.asistentes_con_exceso_tope():  # ext 4a
            self._notificador.notificar(
                destinatario=DESTINATARIO_SOPORTE,
                asunto=f"Horas sobre tope semanal en cierre {anno}-{mes:02d}",
                mensaje=(
                    f"El asistente {linea.nombre} ({linea.carne}) registró "
                    f"{linea.horas_sobre_tope_sin_pago} horas por encima de su tope semanal; "
                    f"quedaron registradas sin pago."
                ),
            )

        return cierre

    def _clasificar_horas_mes(
        self,
        asistente: AsistenteLiquidacion,
        marcas: list[MarcaAsistencia],
    ) -> tuple[Decimal, Decimal, Decimal]:
        """Separa horas regulares, con recargo y exceso no pagado respetando el tope semanal."""
        por_semana: dict[tuple[int, int], list[MarcaAsistencia]] = defaultdict(list)
        for marca in marcas:
            por_semana[marca.semana_iso()].append(marca)

        horas_regulares = CERO
        horas_con_recargo = CERO
        horas_sobre_tope = CERO

        for semana in sorted(por_semana.keys()):
            acumulado_semana = CERO
            marcas_ordenadas = sorted(por_semana[semana], key=lambda m: m.entrada)
            for marca in marcas_ordenadas:
                duracion = marca.duracion_horas()
                disponible = max(CERO, asistente.tope_semanal_horas - acumulado_semana)
                pagables = min(duracion, disponible)
                exceso = duracion - pagables

                if marca.es_con_recargo(self._politica_recargo):
                    horas_con_recargo += pagables
                else:
                    horas_regulares += pagables

                horas_sobre_tope += exceso
                acumulado_semana += duracion

        return horas_regulares, horas_con_recargo, horas_sobre_tope
