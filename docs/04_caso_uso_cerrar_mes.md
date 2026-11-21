# 4. Caso de Uso Completo · CU-3: Cerrar el mes y generar archivo para Becas

## 4.1 Especificación del Caso de Uso (Nivel del Mar)

| Campo | Contenido |
| :--- | :--- |
| **Nombre** | Cerrar el mes y generar archivo para Becas |
| **Actor principal** | Reloj / Planificador (día 1 de cada mes) o Coordinador de Soporte |
| **Alcance y nivel** | CompuLab · Objetivo de usuario (nivel del mar) |
| **Interesados** | **Coordinación de Soporte:** contar con el cálculo exacto, auditable y enterarse de excesos sobre el tope semanal.<br>**Asistentes:** recibir el pago exacto según las horas reales trabajadas y recargos correspondientes.<br>**Oficina de Becas / Planilla:** recibir un archivo mensual íntegro, sin duplicados y sin horas que superen el tope de beca. |
| **Precondición** | Existen asistentes admitidos con categoría y tope semanal definidos, y tarifas vigentes cargadas en el catálogo. |
| **Garantía mínima** | Nunca se guarda un cierre parcial ni se modifica un mes ya cerrado. Si ocurre un error (mes en curso o tarifa faltante), el estado del repositorio de cierres queda intacto. |
| **Garantía de éxito** | Existe exactamente un `CierreMensual` inmutable para `(anno, mes)` con el detalle consolidado por asistente, el archivo aceptado por Becas generado y las alertas enviadas a Coordinación de Soporte si hubo horas sobre el tope semanal. |
| **Disparador** | Llega el primer día del mes siguiente (00:01) o el Coordinador de Soporte solicita generar el cierre del mes ya finalizado. |

### Escenario Principal
1. El actor solicita cerrar el periodo `(anno, mes)`.
2. El sistema verifica que el periodo solicitado ya finalizó según la hora oficial.
3. El sistema comprueba que no exista un cierre previo para `(anno, mes)`.
4. El sistema obtiene las marcas reales de entrada/salida del mes, los asistentes y la tarifa vigente para cada categoría en ese periodo.
5. Para cada asistente con marcas, el sistema agrupa por semana ISO, separa horas regulares, horas con recargo (inicio ≥ 18:00 o sábado/domingo) y horas sobre el tope semanal (registradas sin pago), y calcula el monto exacto en `Decimal`.
6. El sistema genera el archivo en el formato aceptado por la Oficina de Becas y persiste el `CierreMensual` inmutable.
7. El sistema devuelve el cierre generado con su archivo listo para entrega.

### Extensiones
- **1a. El mes solicitado aún está en curso o es futuro:** El sistema rechaza la operación con `PeriodoNoFinalizado` y no crea ningún cierre.
- **2a. El mes ya fue cerrado anteriormente (idempotencia e inmutabilidad):** El sistema **no** recalcula ni modifica el cierre; devuelve intacto el `CierreMensual` previamente guardado.
- **3a. No existe tarifa vigente para la categoría de un asistente en ese periodo:** El sistema cancela el cierre, lanza `TarifaNoEncontrada` y no persiste ningún cierre parcial.
- **4a. Un asistente trabajó horas por encima de su tope semanal:** Esas horas excedentes quedan registradas en `horas_sobre_tope_sin_pago`, **no se suman al monto a pagar**, y el sistema envía una notificación a Coordinación de Soporte detallando el exceso.

---

## 4.2 Diagrama de Secuencia del Sistema (SSD · Caja Negra)

> **Vista:** SSD Caja Negra — CU-3 Cerrar Mes · **Fecha:** 2026-11-21  
> **Leyenda:** Solo participan el actor externo y CompuLab como caja negra. El caso de uso requiere una única operación pública: `cerrar_mes(anno, mes)`.

```mermaid
sequenceDiagram
    actor Actor as Planificador / Coord. Soporte
    participant Sys as :CompuLab

    Actor->>Sys: cerrar_mes(anno, mes)
    alt Mes finalizado y sin cierre previo (y tarifas completas)
        Sys-->>Actor: CierreMensual (lineas, total, archivo_becas)
    else Ext 1a: Mes en curso o futuro
        Sys-->>Actor: Error PeriodoNoFinalizado
    else Ext 2a: Mes ya cerrado
        Sys-->>Actor: CierreMensual existente (sin recalcular)
    else Ext 3a: Tarifa vigente ausente
        Sys-->>Actor: Error TarifaNoEncontrada
    end
```

---

## 4.3 Contrato de la Operación (Estilo Larman)

- **Operación:** `CerrarMes.ejecutar(anno: int, mes: int) -> CierreMensual`
- **Caso de uso:** CU-3 · Cerrar el mes y generar archivo para Becas
- **Precondiciones:**
  - `anno >= 2000` y `1 <= mes <= 12`.
  - La fecha actual del reloj institucional corresponde a un mes posterior a `(anno, mes)`.
  - Existe una tarifa vigente para la categoría de cada asistente con marcas en `(anno, mes)`.
- **Poscondiciones (en pasado):**
  - **P1:** Se creó una instancia inmutable `c` de `CierreMensual` asociada a la clave única `(anno, mes)` (o se devolvió la existente si ya había sido cerrada).
  - **P2:** Se crearon las instancias de `LineaPago` asociadas a `c`, con `horas_regulares`, `horas_con_recargo`, `horas_sobre_tope_sin_pago` y `monto_total` calculados con precisión `Decimal` según la tarifa vigente en ese periodo.
  - **P3:** Se generó y asignó `c.contenido_archivo_becas` con el formato CSV aceptado por la Oficina de Becas.
  - **P4:** Se persistió `c` en `RepositorioCierres` y se registró una notificación a `coordinacion-soporte` por cada línea con `horas_sobre_tope_sin_pago > 0`.

---

## 4.4 Diagrama de Secuencia Interno (Colaboración)

> **Vista:** Secuencia interna — CU-3 Cerrar Mes · **Fecha:** 2026-11-21  
> **Leyenda:** Todos los colaboradores externos son puertos (`Protocol`) inyectados en el constructor de `CerrarMes`.

```mermaid
sequenceDiagram
    participant Actor as Planificador / Soporte
    participant UC as CerrarMes
    participant Rel as Reloj
    participant Cierres as RepositorioCierres
    participant Asist as RepoAsistentesLiq
    participant Marcas as RepoMarcas
    participant Tar as CatalogoTarifas
    participant Exp as ExportadorBecas
    participant Notif as Notificador

    Actor->>UC: ejecutar(anno, mes)
    UC->>Rel: ahora()
    Rel-->>UC: instante_actual
    UC->>Cierres: por_periodo(anno, mes)
    Cierres-->>UC: None (no existe cierre previo)
    UC->>Asist: listar_para_liquidacion()
    Asist-->>UC: asistentes
    UC->>Marcas: por_mes(anno, mes)
    Marcas-->>UC: marcas_reales
    loop Por cada asistente con marcas
        UC->>Tar: vigente_en(categoria, fecha_ref)
        Tar-->>UC: TarifaVigente
        Note over UC: Clasifica por semana ISO:<br/>regular, recargo (>=18h / fin sem),<br/>exceso sin pago; calcula Decimal
    end
    UC->>Exp: generar_archivo(anno, mes, lineas)
    Exp-->>UC: archivo_csv
    UC->>Cierres: guardar(cierre)
    opt Si hay lineas con exceso sobre tope
        UC->>Notif: notificar("coordinacion-soporte", ...)
    end
    UC-->>Actor: CierreMensual
```

---

## 4.5 Trazabilidad Directa al Código y Pruebas

| Paso / Extensión / Poscondición | Ubicación en código | Prueba que lo verifica (`tests/test_cerrar_mes.py`) |
| :--- | :--- | :--- |
| Escenario principal · P1, P2 | `compulab/aplicacion/cerrar_mes.py` (`ejecutar`, `_clasificar_horas_mes`) | `test_post_crea_cierre_y_calcula_horas_regulares_y_recargos` |
| Poscondición P3 (Archivo Becas) | `compulab/infraestructura/exportador_becas.py` (`ExportadorBecasCSV`) | `test_post_genera_archivo_becas_con_formato_esperado` |
| Poscondición P2 (Tarifa vigente) | `compulab/dominio/liquidacion.py` (`TarifaVigente`) | `test_post_usa_tarifa_vigente_del_mes_y_no_una_futura` |
| Extensión 1a (Mes no finalizado) | `cerrar_mes.py` (`# ext 1a`) | `test_ext_1a_rechaza_cerrar_mes_en_curso_o_futuro` |
| Extensión 2a (Idempotencia/Inmutabilidad) | `cerrar_mes.py` (`# ext 2a`) | `test_ext_2a_cierre_repetido_es_idempotente_e_inmutable` |
| Extensión 3a (Tarifa faltante) | `cerrar_mes.py` (`# ext 3a`) | `test_ext_3a_falla_si_no_hay_tarifa_vigente_para_categoria` |
| Extensión 4a (Exceso sobre tope + aviso) | `cerrar_mes.py` (`# ext 4a`) | `test_ext_4a_horas_sobre_tope_semanal_quedan_registradas_sin_pago_y_avisa_a_soporte` |
| Invariantes de dominio | `compulab/dominio/liquidacion.py` | `test_ext_invariantes_de_dominio_rechazan_datos_invalidos` |
