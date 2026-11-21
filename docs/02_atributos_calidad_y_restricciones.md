# 2. Atributos de Calidad y Restricciones Tecnológicas

## 2.1 Escenarios de Calidad (Drivers Arquitectónicos)

Los objetivos de rapidez, alta disponibilidad, tolerancia a picos (matrícula y finales), integridad y cambios frecuentes de tarifas se traducen en **cuatro escenarios verificables de seis partes**:

| Parte | Escenario 1 · Desempeño (`QA-01`) | Escenario 2 · Disponibilidad y Resiliencia (`QA-02`) | Escenario 3 · Modificabilidad (`QA-03`) | Escenario 4 · Integridad y Concurrencia (`QA-04`) |
| :--- | :--- | :--- | :--- | :--- |
| **Fuente del estímulo** | Estudiantes y asistentes de los 2 campus. | Pico externo en el Directorio Institucional (semana de matrícula). | Coordinación de Soporte. | Dos estudiantes (o dos coordinadores) actuando simultáneamente. |
| **Estímulo** | 200 solicitudes por minuto de reserva de máquinas y marcaje de asistencia. | El Directorio Institucional responde con latencia > 3 s o queda temporalmente inaccesible. | Cambia las tarifas por categoría o el porcentaje de recargo nocturno/fin de semana al inicio del semestre. | Intentan reservar la misma máquina en el mismo horario (o asignar turnos traslapados al mismo asistente) en el mismo segundo. |
| **Artefacto** | Servicio web CompuLab (módulos de Máquinas y Horarios) y PostgreSQL 14. | Adaptador de autenticación (capa anticorrupción del Directorio) y sesión de CompuLab. | Componente `Liquidacion` y catálogo de tarifas versionado. | Módulos `Maquinas` / `Horarios` y PostgreSQL 14. |
| **Entorno** | Operación bajo carga pico (finales de semestre o matrícula). | Operación degradada por caída o saturación de dependencia externa. | Operación normal, con meses anteriores ya cerrados. | Operación normal con múltiples peticiones concurrentes. |
| **Respuesta** | El sistema valida reglas y acepta o rechaza cada solicitud sin degradar el servicio. | El *circuit breaker* abre tras fallos consecutivos; las sesiones ya emitidas y el marcaje/operación interna siguen activos sin caída en cascada. | Se registra una nueva versión de tarifa con fecha de vigencia; los cierres futuros la aplican y los cierres pasados permanecen intactos. | Exactamente una solicitud se confirma; la otra recibe un conflicto de negocio explícito sin corromper datos. |
| **Medida verificable** | **p95 < 500 ms** y tasa de error técnico **< 0.5 %** bajo 200 req/min sostenidas durante 15 min. | Disponibilidad operativa **≥ 99.5 %** mensual; fallo rápido del adaptador en **≤ 2 s** sin agotar hilos de CompuLab. | Cambio aplicado en **< 15 min**, tocando **0 archivos de código** y **0 redespliegues**; **0 cambios** en meses cerrados. | **0** reservas o turnos traslapados en pruebas de concurrencia (100 % de conflictos rechazados con código de negocio). |

---

## 2.2 Restricciones Tecnológicas No Negociables

| ID | Restricción del cliente | Implicación concreta en el diseño |
| :--- | :--- | :--- |
| **R-01** | **Infraestructura local del TEC (contenedores Linux).** | Empaquetado en contenedores OCI estándar (`Dockerfile` sobre `python:3.11-slim` y servidor web ligero), ejecutables en **Docker Engine** o **Podman** en Linux sin dependencias de nube externa. |
| **R-02** | **PostgreSQL versión 14.** | Toda la persistencia transaccional y el control de concurrencia de horarios/reservas se diseñan sobre capacidades nativas de PostgreSQL 14 (`TIMESTAMPTZ`, `NUMERIC(10,2)`, `UNIQUE`, `EXCLUDE USING gist`). |
| **R-03** | **Sin presupuesto para nube externa.** | Se descartan servicios administrados en AWS/GCP/Azure; copias de seguridad, monitoreo y ejecución de tareas programadas corren en los mismos nodos Linux del TEC. |
| **R-04** | **100 % código abierto (cero licencias pagas).** | Todo el stack elegido es open source con licencia permisiva: Python (PSF), `pytest` (MIT), PostgreSQL 14 (PostgreSQL License), React/Vite/Tailwind/HeroUI (MIT). Se descarta software propietario o con licencias restrictivas/ambiguas (como Redis comercial). |
