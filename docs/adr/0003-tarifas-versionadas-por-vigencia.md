# ADR-0003 · Tarifas y recargos versionados por fecha de vigencia

**Estado:** Aceptado · **Fecha:** 2026-11-21 · **Sustituye a:** ninguno

## Contexto
- **Requerimientos (`RF-16`, `RF-18`):** Cada una de las dos categorías de asistente tiene su tarifa por hora, y los turnos que inician a las 18:00 o después, así como sábados y domingos, llevan un porcentaje de recargo.
- **Driver (`QA-03`):** Coordinación de Soporte advierte que las tarifas y el porcentaje de recargo cambian casi todos los semestres y casi nunca con anticipación. Además, un cambio de tarifa nunca debe alterar meses ya cerrados.

## Decisión
Las tarifas y porcentajes de recargo **no se queman en código**. Se modelan como registros versionados (`TarifaVigente`) con fecha de entrada en vigencia (`vigente_desde`), consultados a través del puerto `CatalogoTarifas.vigente_en(categoria, momento)`. El cierre mensual toma la tarifa vigente al periodo que se está cerrando y guarda la tarifa aplicada en cada `LineaPago`.

## Alternativas descartadas
- **Constantes o variables de entorno en código:** Descartado porque cada ajuste semestral obligaría a editar código o reiniciar/redesplegar contenedores y dificultaría auditar con qué tarifa se calculó un mes anterior.
- **Sobrescribir una sola fila de tarifa sin historial:** Descartado porque si Coordinación de Soporte actualiza la tarifa antes de auditar el mes anterior, se perdería el valor histórico y cualquier consulta posterior sería inconsistente.

## Consecuencias
- **Positivas (+):** Cumple `QA-03` (cambios en < 15 minutos sin tocar código ni redesplegar) y garantiza trazabilidad histórica de cada monto pagado.
- **Negativas (-):** Exige validar que siempre exista al menos una tarifa vigente para el periodo a cerrar (manejado explícitamente mediante el error tipificado `TarifaNoEncontrada`).
