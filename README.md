# CompuLab

Requisitos: Python 3.11 o superior.

```bash
pip install -e ".[dev]"
pytest -q
```

---

# La docu llega hasta aqui, el resto se migrara a unos md dentro de /docs en donde vendra toda la informacion tecnica e infraestructura del proyecto

## Arquitectura del Código y Comunicación entre Archivos

CompuLab usa un **Monolito Modular** con **Puertos y Adaptadores (Arquitectura Hexagonal)**. Todas las dependencias apuntan **hacia el dominio**, nunca hacia afuera:

```text
  [ Pruebas / API / Cron ]
             │
             ▼  invoca ejecutar()
  [ compulab/aplicacion/ ]      (Orquesta los pasos del caso de uso)
             │
             ▼  usa entidades, errores y contratos (Protocol)
  [ compulab/dominio/ ]         (Reglas de negocio puras · CERO BD, red o reloj)
             ▲
             │  implementa los Protocol del dominio (Inversión de Dependencias)
  [ compulab/infraestructura/ ] (ExportadorBecasCSV, dobles en memoria, adaptadores reales)
```

### Qué hace cada archivo (capa por capa)

#### Capa de Dominio (`compulab/dominio/`) — *Reglas puras*
- **`compulab/dominio/errores.py`:** Define `ErrorDeDominio` y todas las excepciones tipificadas con nombre de negocio para los tres casos de uso (`PeriodoNoFinalizado`, `TarifaNoEncontrada`, `TraslapeDeTurno`, `TopeSemanalExcedido`, `LaboratorioCerrado`, `MaquinaFueraDeServicio`, etc.).
- **`compulab/dominio/liquidacion.py`:** Clases de dominio ricas del cierre mensual con atributos privados (`self._...`), `@property`, `Decimal` (cero `float`) e invariantes verificadas en `__init__`:
  - `CategoriaAsistente` (`CATEGORIA_1`, `CATEGORIA_2`)
  - `TarifaVigente` (`calcular_monto()`)
  - `PoliticaRecargo` (`aplica_recargo()` para inicio ≥ 18:00 o sábado/domingo)
  - `MarcaAsistencia` (`duracion_horas()`, `semana_iso()`, `es_con_recargo()`)
  - `AsistenteLiquidacion` (categoría y tope semanal de Becas)
  - `LineaPago` (horas regulares, con recargo, exceso sin pago y monto total)
  - `CierreMensual` (inmutable por clave `(anno, mes)`, `total_a_pagar()`, `asistentes_con_exceso_tope()`)
- **`compulab/dominio/puertos.py`:** Interfaces requeridas (`Protocol`) inyectables:
  - Transversales: `Reloj`, `Notificador`.
  - Liquidación (CU-3): `CatalogoTarifas`, `RepositorioMarcas`, `RepositorioAsistentesLiquidacion`, `RepositorioCierres`, `ExportadorBecas`.
  - Horarios y Máquinas (CU-1 y CU-2, listos para Xavi): `RepositorioAsistentes`, `RepositorioTurnos`, `RepositorioMaquinas`, `RepositorioReservas`.

#### Capa de Aplicación (`compulab/aplicacion/`) — *Orquestación*
- **`compulab/aplicacion/cerrar_mes.py`:** Controlador `CerrarMes` (patrón GRASP Controlador por caso de uso). Recibe todos los puertos por el constructor y expone `ejecutar(anno, mes)`.

#### Capa de Infraestructura (`compulab/infraestructura/`) — *Adaptadores*
- **`compulab/infraestructura/exportador_becas.py`:** `ExportadorBecasCSV` (Capa Anticorrupción que genera el CSV aceptado por Becas/Planilla).
- **`compulab/infraestructura/dobles.py`:** Dobles en memoria (`RelojFijo`, `NotificadorEspia`, repositorios en memoria) para correr pruebas sin BD ni red.

#### Pruebas y Funciones de Aptitud (`tests/`)
- **`tests/test_cerrar_mes.py`:** Pruebas de aceptación y dominio para CU-3 (poscondiciones `test_post_*` y extensiones `test_ext_*`).
- **`tests/fitness/test_regla_dependencia.py`:** Función de aptitud 1 (AST): valida que `compulab/dominio/` no importe capas externas ni acceso real a BD/red/archivos/reloj, con prueba negativa que planta una violación.
- **`tests/fitness/test_integridad_dominio.py`:** Función de aptitud 2 (AST): valida atributos privados (`_`) en `__init__` y cero `float` en `liquidacion.py`, con prueba negativa que planta una violación.

#### Contenedores y Configuración
- **`pyproject.toml`:** Empaquetado Python y configuración de `pytest`.
- **`Dockerfile`, `docker-compose.yml`, `.env.example`, `db/.gitkeep`:** Contenedores Linux OCI (`postgres:14-alpine` con montaje de `./db`, `backend` Python 3.11 no-root y perfil `frontend` con `node:20-alpine`).
- **`docs/`:** Reservado exclusivamente para las secciones del **Entregable A (Documento de Diseño)**.

---

### Cómo se comunican paso a paso (`CerrarMes.ejecutar(2026, 10)`)

1. El llamador (prueba o Cron el día 1) invoca `CerrarMes.ejecutar(2026, 10)`.
2. **`CerrarMes` → `Reloj`:** pide `ahora()`. Si el mes aún no termina, lanza `PeriodoNoFinalizado`.
3. **`CerrarMes` → `RepositorioCierres`:** llama a `por_periodo(2026, 10)`. Si ya existe cierre, lo devuelve intacto (**idempotencia e inmutabilidad**).
4. **`CerrarMes` → `RepositorioAsistentesLiquidacion` y `RepositorioMarcas`:** obtiene asistentes y marcas reales de octubre.
5. **`CerrarMes` → `CatalogoTarifas` y entidades de `liquidacion.py`:** consulta `vigente_en(categoria, fecha_referencia)` (si falta, lanza `TarifaNoEncontrada`), agrupa marcas por `semana_iso()`, clasifica horas regulares, con recargo y exceso sobre tope semanal (sin pago), y calcula el monto exacto con `Decimal`.
6. **`CerrarMes` → `ExportadorBecas`:** genera el archivo CSV con `generar_archivo(2026, 10, lineas)`.
7. **`CerrarMes` → `CierreMensual` y `RepositorioCierres`:** guarda el `CierreMensual` inmutable.
8. **`CerrarMes` → `Notificador`:** avisa a `"coordinacion-soporte"` por cada asistente con horas sobre el tope semanal.
9. Devuelve el `CierreMensual`.

---

### Cómo se integran Xavi y Agui sobre esta base

- **Xavi (Horarios, Máquinas y PostgreSQL 14):**
  1. Crea `compulab/dominio/horarios.py` (`Asistente`, `BloqueHorario`, `Turno`) y `compulab/dominio/maquinas.py` (`Laboratorio`, `Maquina`, `ReservaMaquina`) usando atributos privados `_` e invariantes en `__init__`.
  2. Crea `compulab/aplicacion/asignar_turno.py` y `compulab/aplicacion/reservar_maquina.py` inyectando los `Protocol` de `puertos.py` y lanzando las excepciones de `errores.py`.
  3. Agrega sus dobles en memoria y sus pruebas en `tests/test_asignar_turno.py` y `tests/test_reservar_maquina.py` (las funciones de aptitud validarán su código automáticamente al correr `pytest`).
  4. Coloca el DDL de PostgreSQL 14 en `db/schema.sql` (el contenedor `db` lo ejecuta automáticamente al iniciar).
- **Agui (Frontend HeroUI):**
  1. Crea el prototipo React + Vite + Tailwind + **HeroUI** dentro de `frontend/` con datos simulados (sin BD).
  2. El servicio `frontend` en `docker-compose.yml` (`node:20-alpine`, puerto `5173`) queda listo para levantarse con `docker compose --profile frontend up`.


---


#### 👤 Xavi (`spicezb`) — *Horarios, Máquinas, UML Detallado y PostgreSQL 14*
- **Código (Entregable B):**
  - [ ] `compulab/dominio/horarios.py` + `compulab/aplicacion/asignar_turno.py` + `tests/test_asignar_turno.py` (1 prueba por poscondición y 1 por extensión, con dobles).
  - [ ] `compulab/dominio/maquinas.py` + `compulab/aplicacion/reservar_maquina.py` + `tests/test_reservar_maquina.py` (1 prueba por poscondición y 1 por extensión, con dobles).
  - [ ] Dobles en memoria para horarios y máquinas.
  - [ ] `db/schema.sql` (DDL en PostgreSQL 14 con `CHECK`, `NUMERIC(10,2)`, `TIMESTAMPTZ`, `UNIQUE(anno, mes)` y `EXCLUDE USING gist` para traslapes).
- **Documento (Entregable A):**
  - [ ] Mapa general de casos de uso a nivel del mar + **CU-1 (`Asignar turno`)** y **CU-2 (`Reservar máquina`)** completos (plantilla, extensiones, SSD y contrato de Larman).
  - [ ] Diagrama UML de **Componentes** (C4 Nivel 3: interfaces provistas/requeridas) + contratos de 5 partes.
  - [ ] Diagrama de **Clases** UML completo.
  - [ ] **Comportamiento:** Secuencias internas de CU-1 y CU-2 + **3 Diagramas de Estados UML** con guardas (`Maquina`, `ReservaMaquina`, `OfertaCambio`).
  - [ ] Sección de **Patrones** (*qué compra / con qué paga* + patrones descartados).
  - [ ] **Diseño de BD:** DER visual + explicación de `db/schema.sql`.
  - [ ] Su **Bitácora individual**.

#### 👤 Agui (`aguilarvss`) — *Frontend HeroUI, UX/UI, Trazabilidad y QA Final*
- **Frontend (Entregable B):**
  - [ ] Proyecto `frontend/` en React + Vite + Tailwind + **HeroUI** (mockeado, sin BD) con selector de rol y las **4 pantallas interactivas**:
    1. Asistente (móvil-first: marcar entrada/salida, cambios de turno, reportar máquina dañada).
    2. Estudiante (reservar máquina en franjas abiertas, máx 2 h, 1 activa, 6 h/semana, estados accesibles).
    3. Coordinador de Lab (horario semanal, asignar turno con validaciones, aprobar/rechazar cambios, alertas sin cubrir).
    4. Coordinador de Soporte (dashboard presupuesto Tufte/Few + cierre mensual y descarga/vista de archivo Becas).
- **Documento (Entregable A) y QA:**
  - [ ] Sección **Descripción y Justificación UX/UI** (capturas de HeroUI, Heurísticas de Nielsen, Leyes de UX, Atomic Design, WCAG 2.2 AA POUR y Tufte/Few).
  - [ ] **Matriz de Trazabilidad Completa** (`RF/RNF` → `CU` → `Contrato` → `Componente/Clase` → `Prueba real` → `C/P/F`).
  - [ ] **Revisión de diseño interna (QA)** contra la checklist del curso y **ensamblado final del Documento A** (unir las 15 secciones en un solo documento con índice).
  - [ ] Su **Bitácora individual**.

#### 👥 Los 3 juntos (al cierre)
- [ ] **Evaluación grupal** y verificación final de que todo el repo corre limpio (`pytest -q`) y que el Documento A no tiene inconsistencias entre diagramas, BD y código.


---

## Guía Completa de Ejecución

### 1. Ejecución local del núcleo en Python (sin BD ni Docker)

```bash
git clone https://github.com/Andr3sCamp0s/CompuLab.git
cd CompuLab
```

Crear y activar entorno virtual (recomendado):

- **Windows (PowerShell):**
  ```powershell
  python -m venv .venv
  .\.venv\Scripts\Activate.ps1
  ```
- **Linux / macOS:**
  ```bash
  python3 -m venv .venv
  source .venv/bin/activate
  ```

Instalar y correr pruebas:
```bash
pip install -e ".[dev]"
pytest -v
```

Comandos específicos:
```bash
pytest tests/test_cerrar_mes.py -v   # Solo CU-3 (Cerrar Mes)
pytest tests/fitness/ -v             # Solo funciones de aptitud y sus pruebas negativas
pytest -q                            # Salida compacta
```

### 2. Ejecución con Docker Compose (PostgreSQL 14 + Backend + Frontend)

Preparar `.env`:
```powershell
Copy-Item .env.example .env   # Windows PowerShell (en Linux/macOS: cp .env.example .env)
```

Validar y levantar PostgreSQL 14 + Backend:
```bash
docker compose config
docker compose up --build
```

Levantar también el Frontend HeroUI (cuando exista `frontend/`):
```bash
docker compose --profile frontend up --build
```

Apagar contenedores:
```bash
docker compose down      # Conserva datos de PostgreSQL
docker compose down -v   # Borra el volumen para reiniciar la BD y re-ejecutar db/schema.sql
```

### 3. Ejecución local del Frontend HeroUI (cuando exista `frontend/`)

```bash
cd frontend
npm install
npm run dev
```
Disponible en `http://localhost:5173`.


Ran list local directories and git-tracked top-level paths

Aquí tienes el repaso rápido de todas las carpetas que ves ahorita en tu PC y cuáles sí suben a GitHub:

| Carpeta | ¿Qué hace? | ¿Es necesaria? | ¿Se sube a GitHub? |
| :--- | :--- | :--- | :---: |
| **`compulab/`** | Todo el código fuente del proyecto (`dominio`, `aplicacion`, `infraestructura`). | **Sí, esencial.** | ✅ Sí |
| **`tests/`** | Las pruebas del caso de uso (`test_cerrar_mes.py`) y las 2 funciones de aptitud (`fitness/`). | **Sí, esencial.** | ✅ Sí |
| **`docs/`** | Las secciones del **Entregable A** (Documento de Diseño y ADRs). | **Sí, esencial.** | ✅ Sí |
| **`db/`** | Carpeta que monta PostgreSQL 14 en `docker-compose.yml` para que Xavi ponga `schema.sql`. | **Sí** (la usa Docker/Xavi). | ✅ Sí |
| **`.git/`** | Carpeta interna oculta de Git (historial y configuración del repo). | **Sí, NO tocarla.** | *(es Git)* |
| **`compulab.egg-info/`** | Metadatos que generó automáticamente `pip install -e ".[dev]"` para registrar el paquete en tu entorno local. | **No es código tuyo.** Si la borras no rompes nada del repo (se vuelve a crear sola si corres `pip install -e` otra vez). | ❌ Ignorada |
| **`.venv/`** | Tu entorno virtual local de Python con `pytest` instalado. | Solo para correr en tu PC. | ❌ Ignorada |
| **`.pytest_cache/`** | Caché temporal que genera `pytest` para acelerar corridas. | No; se puede borrar y se regenera sola. | ❌ Ignorada |

En resumen: **`compulab.egg-info/`, `.venv/` y `.pytest_cache/` son 100 % normales y ya están bloqueadas en `.gitignore`**, así que **nunca van a subir a la rama principal en GitHub**. Si quieres borrar `compulab.egg-info/` para ver tu carpeta más limpia, puedes hacerlo sin problema (solo ten presente que `pip install -e ".[dev]"` la vuelve a generar cuando lo corras).