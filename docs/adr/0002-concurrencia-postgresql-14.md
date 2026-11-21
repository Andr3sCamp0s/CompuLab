# ADR-0002 · Control de concurrencia en turnos y reservas mediante PostgreSQL 14

**Estado:** Aceptado · **Fecha:** 2026-11-21 · **Sustituye a:** ninguno

## Contexto
- **Reglas (`RF-07`, `RF-09`, `RF-12`):** Ningún asistente puede tener turnos traslapados (aun entre laboratorios/campus), ninguna máquina puede tener dos reservas activas simultáneas y un estudiante no puede tener más de una reserva activa.
- **Driver (`QA-04`):** En semana de finales o matrícula, dos solicitudes simultáneas que solo ejecuten "leer → validar → guardar" sufrirían una condición de carrera y crearían registros duplicados.
- **Restricción (`R-02`):** La base de datos obligatoria es **PostgreSQL 14**.

## Decisión
La validación de negocio se expresa primero en el dominio y los casos de uso, y se garantiza de forma atómica en producción mediante **transacciones ACID en PostgreSQL 14** junto con restricciones de exclusión `EXCLUDE USING gist` (usando `btree_gist` y `tstzrange`) sobre `turnos` y `reservas_maquina`, además de índices únicos parciales para la restricción de una reserva activa por estudiante. Cuando PostgreSQL rechaza una colisión, el adaptador traduce el error a una excepción de dominio (`TraslapeDeTurno` o `MaquinaYaReservada`).

## Alternativas descartadas
- **Validar únicamente en memoria de la aplicación:** Descartado porque falla ante dos hilos o dos réplicas del contenedor procesando peticiones al mismo instante.
- **Bloqueos distribuidos en un servidor externo (Redis/Valkey):** Descartado porque agrega una dependencia distribuida adicional y no garantiza consistencia fuerte si el bloqueo expira antes de terminar el `COMMIT` en PostgreSQL.

## Consecuencias
- **Positivas (+):** Garantía matemática de cero traslapes incluso bajo alta concurrencia; aprovecha una capacidad nativa y open source de PostgreSQL 14 sin componentes extra.
- **Negativas (-):** El esquema DDL requiere la extensión estándar `btree_gist` y los adaptadores de persistencia deben capturar y traducir las violaciones de restricción a errores de negocio comprensibles.
