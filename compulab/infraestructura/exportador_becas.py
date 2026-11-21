"""Adaptador de exportación para el archivo mensual que recibe la Oficina de Becas."""

from __future__ import annotations

import csv
import io

from compulab.dominio.liquidacion import LineaPago


class ExportadorBecasCSV:
    """Capa anticorrupción que formatea el cierre al CSV aceptado por Becas/Planilla."""

    ENCABEZADO = (
        "periodo",
        "carne",
        "nombre",
        "categoria",
        "horas_regulares",
        "horas_con_recargo",
        "horas_sobre_tope_sin_pago",
        "tarifa_hora_crc",
        "porcentaje_recargo",
        "monto_pagar_crc",
    )

    def generar_archivo(
        self, anno: int, mes: int, lineas: tuple[LineaPago, ...]
    ) -> str:
        buffer = io.StringIO()
        escritor = csv.writer(buffer, lineterminator="\n")
        escritor.writerow(self.ENCABEZADO)
        periodo = f"{anno}-{mes:02d}"
        for linea in lineas:
            escritor.writerow(
                (
                    periodo,
                    linea.carne,
                    linea.nombre,
                    linea.categoria.value,
                    f"{linea.horas_regulares:.2f}",
                    f"{linea.horas_con_recargo:.2f}",
                    f"{linea.horas_sobre_tope_sin_pago:.2f}",
                    f"{linea.tarifa_aplicada:.2f}",
                    f"{linea.porcentaje_recargo:.2f}",
                    f"{linea.monto_total:.2f}",
                )
            )
        return buffer.getvalue()
