"""Pruebas de aceptación y dominio para CU-3: Cerrar mes y generar archivo para Becas."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from compulab.aplicacion.cerrar_mes import CerrarMes, DESTINATARIO_SOPORTE
from compulab.dominio.errores import (
    CierreInvalido,
    MarcaInvalida,
    PeriodoNoFinalizado,
    TarifaNoEncontrada,
)
from compulab.dominio.liquidacion import (
    AsistenteLiquidacion,
    CategoriaAsistente,
    MarcaAsistencia,
    TarifaVigente,
)
from compulab.infraestructura.dobles import (
    CatalogoTarifasEnMemoria,
    NotificadorEspia,
    RelojFijo,
    RepositorioAsistentesLiquidacionEnMemoria,
    RepositorioCierresEnMemoria,
    RepositorioMarcasEnMemoria,
)
from compulab.infraestructura.exportador_becas import ExportadorBecasCSV

CR = timezone(timedelta(hours=-6))


def _armar_escenario(
    ahora: datetime | None = None,
    asistentes: list[AsistenteLiquidacion] | None = None,
    marcas: list[MarcaAsistencia] | None = None,
    tarifas: list[TarifaVigente] | None = None,
):
    reloj = RelojFijo(ahora or datetime(2026, 11, 1, 8, 0, tzinfo=CR))
    notificador = NotificadorEspia()
    repo_asistentes = RepositorioAsistentesLiquidacionEnMemoria(asistentes)
    repo_marcas = RepositorioMarcasEnMemoria(marcas)
    catalogo_tarifas = CatalogoTarifasEnMemoria(
        tarifas
        if tarifas is not None
        else [
            TarifaVigente(
                categoria=CategoriaAsistente.CATEGORIA_1,
                tarifa_hora=Decimal("2000.00"),
                porcentaje_recargo=Decimal("0.25"),
                vigente_desde=datetime(2026, 8, 1, 0, 0, tzinfo=CR),
            ),
            TarifaVigente(
                categoria=CategoriaAsistente.CATEGORIA_2,
                tarifa_hora=Decimal("2500.00"),
                porcentaje_recargo=Decimal("0.25"),
                vigente_desde=datetime(2026, 8, 1, 0, 0, tzinfo=CR),
            ),
        ]
    )
    repo_cierres = RepositorioCierresEnMemoria()
    exportador = ExportadorBecasCSV()

    caso_uso = CerrarMes(
        marcas=repo_marcas,
        asistentes=repo_asistentes,
        tarifas=catalogo_tarifas,
        cierres=repo_cierres,
        exportador=exportador,
        reloj=reloj,
        notificador=notificador,
    )
    return caso_uso, repo_cierres, notificador, catalogo_tarifas


# --- Escenario principal y poscondiciones del contrato ---


def test_post_crea_cierre_y_calcula_horas_regulares_y_recargos():
    """Poscondición 1 y 2: consolida horas reales, aplica tarifa de categoría y recargos."""
    asistente = AsistenteLiquidacion(
        id_asistente="A-01",
        carne="2025069367",
        nombre="Andrés Campos",
        categoria=CategoriaAsistente.CATEGORIA_1,
        tope_semanal_horas=Decimal("12.00"),
    )
    marcas = [
        # Lunes 5 oct 2026 08:00-11:00 -> 3h regulares (3 * 2000 = 6000)
        MarcaAsistencia(
            "M-1", "A-01", "T-1",
            datetime(2026, 10, 5, 8, 0, tzinfo=CR),
            datetime(2026, 10, 5, 11, 0, tzinfo=CR),
        ),
        # Martes 6 oct 2026 18:00-20:00 -> 2h nocturnas con recargo 25% (2 * 2500 = 5000)
        MarcaAsistencia(
            "M-2", "A-01", "T-2",
            datetime(2026, 10, 6, 18, 0, tzinfo=CR),
            datetime(2026, 10, 6, 20, 0, tzinfo=CR),
        ),
        # Sábado 10 oct 2026 09:00-11:00 -> 2h fin de semana con recargo 25% (2 * 2500 = 5000)
        MarcaAsistencia(
            "M-3", "A-01", "T-3",
            datetime(2026, 10, 10, 9, 0, tzinfo=CR),
            datetime(2026, 10, 10, 11, 0, tzinfo=CR),
        ),
    ]
    caso_uso, repo_cierres, notificador, _ = _armar_escenario(
        asistentes=[asistente], marcas=marcas
    )

    cierre = caso_uso.ejecutar(2026, 10)

    assert cierre.id_cierre == "CIERRE-2026-10"
    assert cierre.clave_periodo == (2026, 10)
    assert repo_cierres.total_guardados() == 1
    assert len(cierre.lineas) == 1
    linea = cierre.lineas[0]
    assert linea.horas_regulares == Decimal("3.00")
    assert linea.horas_con_recargo == Decimal("4.00")
    assert linea.horas_sobre_tope_sin_pago == Decimal("0.00")
    assert linea.monto_total == Decimal("16000.00")
    assert cierre.total_a_pagar() == Decimal("16000.00")
    assert notificador.enviadas == []


def test_post_genera_archivo_becas_con_formato_esperado():
    """Poscondición 3: genera el archivo CSV estructurado que acepta Becas/Planilla."""
    asistente = AsistenteLiquidacion(
        id_asistente="A-02",
        carne="2025076662",
        nombre="Sofía Mora",
        categoria=CategoriaAsistente.CATEGORIA_2,
        tope_semanal_horas=Decimal("10.00"),
    )
    marcas = [
        # Domingo 11 oct 2026 10:00-12:00 -> 2h fin de semana (2 * 2500 * 1.25 = 6250)
        MarcaAsistencia(
            "M-10", "A-02", "T-10",
            datetime(2026, 10, 11, 10, 0, tzinfo=CR),
            datetime(2026, 10, 11, 12, 0, tzinfo=CR),
        ),
    ]
    caso_uso, _, _, _ = _armar_escenario(asistentes=[asistente], marcas=marcas)

    cierre = caso_uso.ejecutar(2026, 10)

    lineas_csv = cierre.contenido_archivo_becas.strip().splitlines()
    assert lineas_csv[0].startswith("periodo,carne,nombre,categoria,")
    assert (
        lineas_csv[1]
        == "2026-10,2025076662,Sofía Mora,CATEGORIA_2,0.00,2.00,0.00,2500.00,0.25,6250.00"
    )


def test_post_usa_tarifa_vigente_del_mes_y_no_una_futura():
    """Poscondición 4: aplica la tarifa vigente en el periodo cerrado aunque cambie después."""
    asistente = AsistenteLiquidacion(
        id_asistente="A-03",
        carne="2025102887",
        nombre="Xavier Céspedes",
        categoria=CategoriaAsistente.CATEGORIA_1,
        tope_semanal_horas=Decimal("10.00"),
    )
    tarifas = [
        TarifaVigente(
            categoria=CategoriaAsistente.CATEGORIA_1,
            tarifa_hora=Decimal("2000.00"),
            porcentaje_recargo=Decimal("0.20"),
            vigente_desde=datetime(2026, 8, 1, 0, 0, tzinfo=CR),
        ),
        # Tarifa nueva que entra a regir el 1 de noviembre (no debe afectar octubre)
        TarifaVigente(
            categoria=CategoriaAsistente.CATEGORIA_1,
            tarifa_hora=Decimal("3000.00"),
            porcentaje_recargo=Decimal("0.50"),
            vigente_desde=datetime(2026, 11, 1, 0, 0, tzinfo=CR),
        ),
    ]
    marcas = [
        MarcaAsistencia(
            "M-20", "A-03", "T-20",
            datetime(2026, 10, 7, 9, 0, tzinfo=CR),
            datetime(2026, 10, 7, 11, 0, tzinfo=CR),
        ),
    ]
    caso_uso, _, _, _ = _armar_escenario(
        asistentes=[asistente], marcas=marcas, tarifas=tarifas
    )

    cierre = caso_uso.ejecutar(2026, 10)

    assert cierre.lineas[0].tarifa_aplicada == Decimal("2000.00")
    assert cierre.lineas[0].monto_total == Decimal("4000.00")


# --- Extensiones documentadas del caso de uso ---


def test_ext_1a_rechaza_cerrar_mes_en_curso_o_futuro():
    """Extensión 1a: no se puede cerrar un mes que todavía no terminó."""
    caso_uso, repo_cierres, _, _ = _armar_escenario(
        ahora=datetime(2026, 10, 31, 23, 59, tzinfo=CR)
    )

    with pytest.raises(PeriodoNoFinalizado):
        caso_uso.ejecutar(2026, 10)

    assert repo_cierres.total_guardados() == 0


def test_ext_2a_cierre_repetido_es_idempotente_e_inmutable():
    """Extensión 2a: solicitar el cierre de un mes ya cerrado devuelve el original intacto."""
    asistente = AsistenteLiquidacion(
        id_asistente="A-01",
        carne="2025069367",
        nombre="Andrés Campos",
        categoria=CategoriaAsistente.CATEGORIA_1,
        tope_semanal_horas=Decimal("10.00"),
    )
    marcas = [
        MarcaAsistencia(
            "M-1", "A-01", "T-1",
            datetime(2026, 10, 5, 8, 0, tzinfo=CR),
            datetime(2026, 10, 5, 10, 0, tzinfo=CR),
        ),
    ]
    caso_uso, repo_cierres, _, catalogo_tarifas = _armar_escenario(
        asistentes=[asistente], marcas=marcas
    )

    primero = caso_uso.ejecutar(2026, 10)
    # Aunque alguien cargue otra tarifa después, el mes cerrado no se recalcula
    catalogo_tarifas.agregar(
        TarifaVigente(
            categoria=CategoriaAsistente.CATEGORIA_1,
            tarifa_hora=Decimal("9999.00"),
            porcentaje_recargo=Decimal("0.90"),
            vigente_desde=datetime(2026, 9, 1, 0, 0, tzinfo=CR),
        )
    )
    segundo = caso_uso.ejecutar(2026, 10)

    assert segundo is primero
    assert segundo.total_a_pagar() == Decimal("4000.00")
    assert repo_cierres.total_guardados() == 1


def test_ext_3a_falla_si_no_hay_tarifa_vigente_para_categoria():
    """Extensión 3a: si falta tarifa vigente, no guarda cierre parcial y lanza error."""
    asistente = AsistenteLiquidacion(
        id_asistente="A-01",
        carne="2025069367",
        nombre="Andrés Campos",
        categoria=CategoriaAsistente.CATEGORIA_2,
        tope_semanal_horas=Decimal("10.00"),
    )
    marcas = [
        MarcaAsistencia(
            "M-1", "A-01", "T-1",
            datetime(2026, 10, 5, 8, 0, tzinfo=CR),
            datetime(2026, 10, 5, 10, 0, tzinfo=CR),
        ),
    ]
    caso_uso, repo_cierres, _, _ = _armar_escenario(
        asistentes=[asistente], marcas=marcas, tarifas=[]
    )

    with pytest.raises(TarifaNoEncontrada):
        caso_uso.ejecutar(2026, 10)

    assert repo_cierres.total_guardados() == 0


def test_ext_4a_horas_sobre_tope_semanal_quedan_registradas_sin_pago_y_avisa_a_soporte():
    """Extensión 4a: exceso sobre el tope semanal no se paga, se registra y se notifica."""
    asistente = AsistenteLiquidacion(
        id_asistente="A-04",
        carne="2025072110",
        nombre="Sebastián Aguilar",
        categoria=CategoriaAsistente.CATEGORIA_1,
        tope_semanal_horas=Decimal("4.00"),
    )
    marcas = [
        # Misma semana ISO: 3h lunes + 3h miércoles = 6h reales (tope 4h -> 4h pagadas, 2h sin pago)
        MarcaAsistencia(
            "M-30", "A-04", "T-30",
            datetime(2026, 10, 5, 8, 0, tzinfo=CR),
            datetime(2026, 10, 5, 11, 0, tzinfo=CR),
        ),
        MarcaAsistencia(
            "M-31", "A-04", "T-31",
            datetime(2026, 10, 7, 8, 0, tzinfo=CR),
            datetime(2026, 10, 7, 11, 0, tzinfo=CR),
        ),
    ]
    caso_uso, _, notificador, _ = _armar_escenario(
        asistentes=[asistente], marcas=marcas
    )

    cierre = caso_uso.ejecutar(2026, 10)

    linea = cierre.lineas[0]
    assert linea.horas_regulares == Decimal("4.00")
    assert linea.horas_sobre_tope_sin_pago == Decimal("2.00")
    assert linea.monto_total == Decimal("8000.00")
    assert linea.tuvo_exceso_tope is True
    assert len(notificador.enviadas) == 1
    destinatario, asunto, mensaje = notificador.enviadas[0]
    assert destinatario == DESTINATARIO_SOPORTE
    assert "2026-10" in asunto
    assert "2.00" in mensaje


def test_ext_invariantes_de_dominio_rechazan_datos_invalidos():
    """Invariantes del dominio: salida <= entrada y periodo inválido son rechazados."""
    with pytest.raises(MarcaInvalida):
        MarcaAsistencia(
            "M-ERR", "A-01", "T-1",
            datetime(2026, 10, 5, 10, 0, tzinfo=CR),
            datetime(2026, 10, 5, 9, 0, tzinfo=CR),
        )

    caso_uso, _, _, _ = _armar_escenario()
    with pytest.raises(CierreInvalido):
        caso_uso.ejecutar(2026, 13)
