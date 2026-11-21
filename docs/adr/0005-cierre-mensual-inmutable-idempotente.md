# ADR-0005 · Cierre mensual inmutable e idempotente por periodo

**Estado:** Aceptado · **Fecha:** 2026-11-21 · **Sustituye a:** ninguno

## Contexto
- **Requerimientos (`RF-16`, `RF-17`, `RF-18`):** El primer día de cada mes se cierra el mes anterior, se genera el archivo para Becas/Planilla y **un mes cerrado no se vuelve a calcular ni se corrige dentro del sistema** (cualquier ajuste excepcional se hace por fuera dejando constancia).
- **Riesgo operativo:** Si el planificador (Cron) reintenta por un fallo de red o el Coordinador de Soporte dispara dos veces el cierre del mismo mes, no deben generarse cierres duplicados ni montos distintos.

## Decisión
Cada `CierreMensual` se identifica por la clave única compuesta **`(anno, mes)`** (respaldada por `UNIQUE(anno, mes)` en PostgreSQL 14), se construye como objeto **inmutable** con sus líneas de pago y el contenido exacto del archivo generado para Becas, y la operación `CerrarMes.ejecutar(anno, mes)` es **idempotente**: si ya existe un cierre para ese periodo, devuelve el registro existente sin recalcular ni modificar nada.

## Alternativas descartadas
- **Permitir recalcular y sobrescribir un cierre existente:** Descartado porque viola directamente el requerimiento de negocio de inmutabilidad y rompe la conciliación con el archivo ya entregado a Planilla/Becas.
- **Lanzar un error fatal ante una segunda solicitud del mismo mes:** Descartado frente a la idempotencia porque complica los reintentos seguros del planificador mensual del día 1 (siguiendo el principio de idempotencia del curso: repetir una llamada con la misma clave devuelve el mismo resultado sin duplicar efectos).

## Consecuencias
- **Positivas (+):** Auditoría completa de lo que se entregó a Becas cada mes; seguridad ante reintentos del planificador; protección contra cambios posteriores de tarifas o marcas.
- **Negativas (-):** Cualquier error humano en una marca antes del cierre debe corregirse por fuera del sistema una vez cerrado el mes, exactamente como lo estableció la Coordinación de Soporte.
