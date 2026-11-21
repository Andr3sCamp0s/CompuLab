# ADR-0004 · Descarte de Redis como caché externo

**Estado:** Aceptado · **Fecha:** 2026-11-21 · **Sustituye a:** ninguno

## Contexto
- **Drivers (`QA-01`, `QA-02`):** El sistema debe responder rápido (p95 < 500 ms) y mantener alta disponibilidad aun cuando haya picos en matrícula o finales de semestre.
- **Restricciones (`R-01`, `R-02`, `R-04`):** Infraestructura local Linux del TEC, PostgreSQL 14, sin presupuesto para licencias (todo 100 % código abierto) y un equipo de 3 personas.

## Decisión
**Descartamos incorporar Redis** en la arquitectura de CompuLab. Para la carga real de 4 laboratorios en 2 campus, se utiliza **PostgreSQL 14** con índices adecuados y un **caché en memoria del proceso con TTL corto** para sesiones ya autenticadas y catálogos de lectura frecuente (como tarifas y laboratorios). El aislamiento frente a lentitud del Directorio Institucional se resuelve mediante **timeout (2 s) + circuit breaker** en el adaptador de autenticación.

## Alternativas descartadas
- **Agregar un contenedor de Redis:** Descartado por dos razones: (1) desde 2024 Redis cambió su esquema de licenciamiento alejándose de licencias open source permisivas tradicionales, lo que genera riesgo frente a `R-04`; (2) introducir otro servidor de datos agrega latencia de red, un punto adicional de operación/monitoreo y riesgo de inconsistencia entre caché y PostgreSQL sin un cuello de botella medido que lo justifique.
- **Agregar Valkey (fork open source BSD de Redis) desde el día 1:** Aunque resuelve el problema de licencia, se descarta para esta primera etapa porque con 4 laboratorios no existe necesidad de estado compartido entre decenas de réplicas; si en el futuro CompuLab escala horizontalmente, Valkey puede incorporarse detrás de un puerto `CacheSesiones` sin modificar el dominio.

## Consecuencias
- **Positivas (+):** Menor complejidad operativa en los contenedores del TEC, cumplimiento estricto de `R-04` (100 % código abierto sin ambigüedades) y fuente única de verdad en PostgreSQL 14.
- **Negativas (-):** Si en el futuro se despliegan múltiples réplicas simultáneas del monolito, el caché en memoria local no se comparte entre instancias y será necesario activar un adaptador distribuido (como Valkey).
