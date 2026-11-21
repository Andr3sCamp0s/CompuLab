# ADR-0001 · Monolito modular con Puertos y Adaptadores

**Estado:** Aceptado · **Fecha:** 2026-11-21 · **Sustituye a:** ninguno

## Contexto
- **Equipo:** 3 desarrolladores (Ley de Conway).
- **Alcance:** 4 laboratorios de cómputo en 2 campus con 4 dominios claros (`Reclutamiento`, `Horarios`, `Maquinas`, `Liquidacion`).
- **Restricciones (`R-01`, `R-02`, `R-03`, `R-04`):** Despliegue en contenedores Linux del TEC, PostgreSQL 14, sin nube externa ni licencias pagas.
- **Drivers (`QA-01`, `QA-03`):** Respuesta rápida (p95 < 500 ms), alta modificabilidad de tarifas y pruebas unitarias/de aceptación sin levantar base de datos ni red.

## Decisión
Adoptamos un **monolito modular** en Python 3.11+ estructurado internamente con **Puertos y Adaptadores (Arquitectura Hexagonal)**. Cada módulo de dominio vive separado por razón de cambio, las dependencias apuntan únicamente hacia el dominio puro y las fronteras se protegen con funciones de aptitud automatizadas (`tests/fitness/`).

## Alternativas descartadas
- **Microservicios (4 servicios desplegados aparte):** Descartado porque un equipo de 3 personas pagaría el costo de red, latencia entre llamadas, múltiples despliegues y transacciones distribuidas (Sagas) sin que exista una necesidad de escalado independiente que lo justifique para 4 laboratorios.
- **Capas técnicas tradicionales sin puertos (Controller → Service → ORM directo):** Descartado porque acopla el dominio a SQLAlchemy/PostgreSQL, impide ejecutar las pruebas sin base de datos y tiende a generar modelos anémicos.

## Consecuencias
- **Positivas (+):** Un único desplegable sencillo en contenedores Linux del TEC; comunicación entre módulos en memoria sin latencia de red; el 100 % de las pruebas del núcleo corren en menos de 1 segundo con dobles en memoria; si a futuro un módulo necesitara escalar aparte, ya está aislado por contratos (`Protocol`).
- **Negativas (-):** Exige disciplina para no romper fronteras entre módulos (mitigado con funciones de aptitud en el build) y agrega archivos de interfaces (`Protocol`) y dobles que un diseño más simple no tendría.
