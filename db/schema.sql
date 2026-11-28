CREATE EXTENSION IF NOT EXISTS btree_gist;

CREATE TABLE usuarios (
    usuarioId       SERIAL PRIMARY KEY,
    nombre          VARCHAR(50) NOT NULL,
    correo          VARCHAR(35) NOT NULL,
    activo          BOOLEAN NOT NULL DEFAULT TRUE,

    CONSTRAINT uq_usuarios_correo UNIQUE (correo),
    CONSTRAINT ck_usuarios_nombre CHECK (BTRIM(nombre) <> ''),
    CONSTRAINT ck_usuarios_correo CHECK (BTRIM(correo) <> '')
);

CREATE TABLE estudiantes (
    estudianteId    SERIAL PRIMARY KEY,
    usuarioId       INT NOT NULL,
    carnet          VARCHAR(10) NOT NULL,
    activo          BOOLEAN NOT NULL DEFAULT TRUE,

    CONSTRAINT fk_estudiantes_usuario
        FOREIGN KEY (usuarioId) REFERENCES usuarios(usuarioId),
    CONSTRAINT uq_estudiantes_usuario UNIQUE (usuarioId),
    CONSTRAINT uq_estudiantes_carnet UNIQUE (carnet),
    CONSTRAINT ck_estudiantes_carnet CHECK (BTRIM(carnet) <> '')
);

CREATE TABLE coordinadores (
    coordinadorId   SERIAL PRIMARY KEY,
    usuarioId       INT NOT NULL,
    esDeSoporte     BOOLEAN NOT NULL DEFAULT FALSE,
    activo          BOOLEAN NOT NULL DEFAULT TRUE,

    CONSTRAINT fk_coordinadores_usuario
        FOREIGN KEY (usuarioId) REFERENCES usuarios(usuarioId),
    CONSTRAINT uq_coordinadores_usuario UNIQUE (usuarioId)
);

-- Solo puede existir un coordinador de soporte activo.
CREATE UNIQUE INDEX uq_un_coordinador_soporte_activo
    ON coordinadores (esDeSoporte)
    WHERE esDeSoporte = TRUE AND activo = TRUE;

CREATE TABLE convocatorias (
    convocatoriaId SERIAL PRIMARY KEY,
    semestre       VARCHAR(10) NOT NULL,
    fechaInicio    DATE NOT NULL,
    fechaFin       DATE NOT NULL,
    estado         VARCHAR(15) NOT NULL,

    CONSTRAINT uq_convocatorias_semestre UNIQUE (semestre),
    CONSTRAINT ck_convocatorias_fechas CHECK (fechaFin >= fechaInicio),
    CONSTRAINT ck_convocatorias_semestre CHECK (BTRIM(semestre) <> ''),
    CONSTRAINT ck_convocatorias_estado
        CHECK (estado IN ('PLANIFICADA', 'ABIERTA', 'CERRADA'))
);

CREATE TABLE estadosPostulacion (
    estadoPostulacionId SERIAL PRIMARY KEY,
    nombre              VARCHAR(15) NOT NULL,
    descripcion         VARCHAR(100) NOT NULL,
    activo              BOOLEAN NOT NULL DEFAULT TRUE,

    CONSTRAINT uq_estados_postulacion_nombre UNIQUE (nombre),
    CONSTRAINT ck_estados_postulacion_nombre CHECK (BTRIM(nombre) <> '')
);

CREATE TABLE postulaciones (
    postulacionId       SERIAL PRIMARY KEY,
    estudianteId        INT NOT NULL,
    convocatoriaId      INT NOT NULL,
    fechaPostulacion    DATE NOT NULL DEFAULT CURRENT_DATE,
    estadoPostulacionId INT NOT NULL,

    CONSTRAINT fk_postulaciones_estudiante
        FOREIGN KEY (estudianteId) REFERENCES estudiantes(estudianteId),
    CONSTRAINT fk_postulaciones_convocatoria
        FOREIGN KEY (convocatoriaId) REFERENCES convocatorias(convocatoriaId),
    CONSTRAINT fk_postulaciones_estado
        FOREIGN KEY (estadoPostulacionId)
        REFERENCES estadosPostulacion(estadoPostulacionId),
    CONSTRAINT uq_postulacion_estudiante_convocatoria
        UNIQUE (estudianteId, convocatoriaId)
);

CREATE TABLE disponibilidadPostulacion (
    disponibilidadPostulacionId SERIAL PRIMARY KEY,
    postulacionId               INT NOT NULL,
    dia                         INT NOT NULL,
    horaInicio                  TIME NOT NULL,
    horaFin                     TIME NOT NULL,

    CONSTRAINT fk_disponibilidad_postulacion
        FOREIGN KEY (postulacionId) REFERENCES postulaciones(postulacionId),
    CONSTRAINT ck_disponibilidad_dia CHECK (dia BETWEEN 0 AND 6),
    CONSTRAINT ck_disponibilidad_horas CHECK (horaFin > horaInicio),
    CONSTRAINT uq_disponibilidad_bloque
        UNIQUE (postulacionId, dia, horaInicio, horaFin)
);

-- Evita bloques de disponibilidad traslapados en una misma postulación.
ALTER TABLE disponibilidadPostulacion
    ADD CONSTRAINT ex_disponibilidad_sin_traslapes
    EXCLUDE USING gist (
        postulacionId WITH =,
        (tsrange(
            DATE '2000-01-02' + dia + horaInicio,
            DATE '2000-01-02' + dia + horaFin,
            '[)'
        )) WITH &&
    );

CREATE TABLE laboratorios (
    laboratorioId   SERIAL PRIMARY KEY,
    coordinadorId   INT NOT NULL,
    nombre          VARCHAR(100) NOT NULL,
    cantComputadoras INT NOT NULL,
    activo          BOOLEAN NOT NULL DEFAULT TRUE,

    CONSTRAINT fk_laboratorios_coordinador
        FOREIGN KEY (coordinadorId) REFERENCES coordinadores(coordinadorId),
    CONSTRAINT uq_laboratorios_coordinador UNIQUE (coordinadorId),
    CONSTRAINT uq_laboratorios_nombre UNIQUE (nombre),
    CONSTRAINT ck_laboratorios_nombre CHECK (BTRIM(nombre) <> ''),
    CONSTRAINT ck_laboratorios_cantidad CHECK (cantComputadoras >= 0)
);

CREATE TABLE laboratoriosPostulacion (
    laboratorioPostulacionId SERIAL PRIMARY KEY,
    postulacionId            INT NOT NULL,
    laboratorioId            INT NOT NULL,

    CONSTRAINT fk_lab_postulacion_postulacion
        FOREIGN KEY (postulacionId) REFERENCES postulaciones(postulacionId),
    CONSTRAINT fk_lab_postulacion_laboratorio
        FOREIGN KEY (laboratorioId) REFERENCES laboratorios(laboratorioId),
    CONSTRAINT uq_laboratorio_por_postulacion
        UNIQUE (postulacionId, laboratorioId)
);

CREATE TABLE entrevistas (
    entrevistaId    SERIAL PRIMARY KEY,
    coordinadorId   INT NOT NULL,
    postulacionId   INT NOT NULL,
    fecha           TIMESTAMP NOT NULL,
    resultado       VARCHAR(30) NOT NULL,
    comentarios     VARCHAR(255),

    CONSTRAINT fk_entrevistas_coordinador
        FOREIGN KEY (coordinadorId) REFERENCES coordinadores(coordinadorId),
    CONSTRAINT fk_entrevistas_postulacion
        FOREIGN KEY (postulacionId) REFERENCES postulaciones(postulacionId),
    CONSTRAINT ck_entrevistas_resultado
        CHECK (BTRIM(resultado) <> '')
);

CREATE TABLE categorias (
    categoriaId       SERIAL PRIMARY KEY,
    nombre            VARCHAR(20) NOT NULL,
    pagoHora          NUMERIC(8,2) NOT NULL,
    porcentajeRecargo NUMERIC(4,2) NOT NULL,
    activo            BOOLEAN NOT NULL DEFAULT TRUE,

    CONSTRAINT uq_categorias_nombre UNIQUE (nombre),
    CONSTRAINT ck_categorias_nombre CHECK (BTRIM(nombre) <> ''),
    CONSTRAINT ck_categorias_pago CHECK (pagoHora >= 0),
    CONSTRAINT ck_categorias_recargo CHECK (porcentajeRecargo >= 0)
);

CREATE TABLE asistentes (
    asistenteId  SERIAL PRIMARY KEY,
    estudianteId INT NOT NULL,
    categoriaId  INT NOT NULL,
    maxHoras     INT NOT NULL,
    activo       BOOLEAN NOT NULL DEFAULT TRUE,

    CONSTRAINT fk_asistentes_estudiante
        FOREIGN KEY (estudianteId) REFERENCES estudiantes(estudianteId),
    CONSTRAINT fk_asistentes_categoria
        FOREIGN KEY (categoriaId) REFERENCES categorias(categoriaId),
    CONSTRAINT uq_asistentes_estudiante UNIQUE (estudianteId),
    CONSTRAINT ck_asistentes_max_horas CHECK (maxHoras BETWEEN 1 AND 168)
);

CREATE TABLE historialAsistentes (
    historialAsistenteId SERIAL PRIMARY KEY,
    asistenteId          INT NOT NULL,
    movimiento           VARCHAR(20) NOT NULL,
    coordinadorId        INT,
    motivo               VARCHAR(255),
    fecha                TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_historial_asistente
        FOREIGN KEY (asistenteId) REFERENCES asistentes(asistenteId),
    CONSTRAINT fk_historial_coordinador
        FOREIGN KEY (coordinadorId) REFERENCES coordinadores(coordinadorId),
    CONSTRAINT ck_historial_movimiento
        CHECK (movimiento IN ('ALTA', 'RENUNCIA', 'BAJA', 'REACTIVACION'))
);

CREATE TABLE laboratoriosPorAsistente (
    laboratorioPorAsistenteId SERIAL PRIMARY KEY,
    laboratorioId             INT NOT NULL,
    asistenteId               INT NOT NULL,
    activo                    BOOLEAN NOT NULL DEFAULT TRUE,

    CONSTRAINT fk_lpa_laboratorio
        FOREIGN KEY (laboratorioId) REFERENCES laboratorios(laboratorioId),
    CONSTRAINT fk_lpa_asistente
        FOREIGN KEY (asistenteId) REFERENCES asistentes(asistenteId),
    CONSTRAINT uq_laboratorio_asistente
        UNIQUE (laboratorioId, asistenteId)
);

CREATE TABLE horarios (
    horarioId   SERIAL PRIMARY KEY,
    asistenteId INT NOT NULL,
    dia         INT NOT NULL,
    horaInicio  TIME NOT NULL,
    horaFin     TIME NOT NULL,
    activo      BOOLEAN NOT NULL DEFAULT TRUE,

    CONSTRAINT fk_horarios_asistente
        FOREIGN KEY (asistenteId) REFERENCES asistentes(asistenteId),
    CONSTRAINT ck_horarios_dia CHECK (dia BETWEEN 0 AND 6),
    CONSTRAINT ck_horarios_horas CHECK (horaFin > horaInicio),
    CONSTRAINT uq_horario_bloque
        UNIQUE (asistenteId, dia, horaInicio, horaFin)
);

-- Evita traslapes en los bloques semanales registrados para un asistente.
ALTER TABLE horarios
    ADD CONSTRAINT ex_horarios_sin_traslapes
    EXCLUDE USING gist (
        asistenteId WITH =,
        (tsrange(
            DATE '2000-01-02' + dia + horaInicio,
            DATE '2000-01-02' + dia + horaFin,
            '[)'
        )) WITH &&
    )
    WHERE (activo = TRUE);

CREATE TABLE turnos (
    turnoId              SERIAL PRIMARY KEY,
    laboratorioId        INT NOT NULL,
    fecha                DATE NOT NULL,
    horaInicio           TIME NOT NULL,
    horaFin              TIME NOT NULL,
    horaInicioReportada  TIMESTAMP,
    horaFinReportada     TIMESTAMP,
    asistenteId          INT,
    disponible           BOOLEAN NOT NULL DEFAULT FALSE,
    reasignar            BOOLEAN NOT NULL DEFAULT FALSE,
    activo               BOOLEAN NOT NULL DEFAULT TRUE,

    CONSTRAINT fk_turnos_laboratorio
        FOREIGN KEY (laboratorioId) REFERENCES laboratorios(laboratorioId),
    CONSTRAINT fk_turnos_asistente
        FOREIGN KEY (asistenteId) REFERENCES asistentes(asistenteId),
    CONSTRAINT ck_turnos_horas CHECK (horaFin > horaInicio),
    CONSTRAINT ck_turnos_marcaciones
        CHECK (
            horaFinReportada IS NULL
            OR (
                horaInicioReportada IS NOT NULL
                AND horaFinReportada >= horaInicioReportada
            )
        ),
    CONSTRAINT ck_turnos_oferta_con_responsable
        CHECK (disponible = FALSE OR (asistenteId IS NOT NULL AND reasignar = FALSE)),
    CONSTRAINT ck_turnos_reasignacion
        CHECK (reasignar = FALSE OR asistenteId IS NULL)
);

-- EXCLUDE principal: un asistente no puede tener turnos traslapados
ALTER TABLE turnos
    ADD CONSTRAINT ex_turnos_asistente_sin_traslapes
    EXCLUDE USING gist (
        asistenteId WITH =,
        (tsrange(
            fecha + horaInicio,
            fecha + horaFin,
            '[)'
        )) WITH &&
    )
    WHERE (activo = TRUE AND asistenteId IS NOT NULL);

CREATE TABLE cambiosDeTurno (
    cambioDeTurnoID SERIAL PRIMARY KEY,
    turnoId         INT NOT NULL,
    asistenteActual INT NOT NULL,
    asistenteNuevo  INT,
    estado          BOOLEAN NOT NULL DEFAULT FALSE,

    CONSTRAINT fk_cambios_turno
        FOREIGN KEY (turnoId) REFERENCES turnos(turnoId),
    CONSTRAINT fk_cambios_asistente_actual
        FOREIGN KEY (asistenteActual) REFERENCES asistentes(asistenteId),
    CONSTRAINT fk_cambios_asistente_nuevo
        FOREIGN KEY (asistenteNuevo) REFERENCES asistentes(asistenteId),
    CONSTRAINT ck_cambio_asistentes_distintos
        CHECK (
            asistenteNuevo IS NULL
            OR asistenteNuevo <> asistenteActual
        )
);

CREATE TABLE computadoras (
    computadoraId SERIAL PRIMARY KEY,
    laboratorioId INT NOT NULL,
    estado        BOOLEAN NOT NULL DEFAULT TRUE,
    activo        BOOLEAN NOT NULL DEFAULT TRUE,

    CONSTRAINT fk_computadoras_laboratorio
        FOREIGN KEY (laboratorioId) REFERENCES laboratorios(laboratorioId),
    CONSTRAINT uq_computadora_laboratorio
        UNIQUE (computadoraId, laboratorioId)
);

CREATE TABLE historialComputadoras (
    historialComputadoraId SERIAL PRIMARY KEY,
    computadoraId          INT NOT NULL,
    estado                 BOOLEAN NOT NULL,
    fechaInicio            TIMESTAMP NOT NULL,
    fechaFin               TIMESTAMP,
    usuarioId              INT NOT NULL,

    CONSTRAINT fk_historial_computadora
        FOREIGN KEY (computadoraId) REFERENCES computadoras(computadoraId),
    CONSTRAINT fk_historial_computadora_usuario
        FOREIGN KEY (usuarioId) REFERENCES usuarios(usuarioId),
    CONSTRAINT ck_historial_computadora_fechas
        CHECK (fechaFin IS NULL OR fechaFin >= fechaInicio)
);

CREATE TABLE estadosReserva (
    estadoReservaId SERIAL PRIMARY KEY,
    nombre          VARCHAR(15) NOT NULL,
    descripcion     VARCHAR(100) NOT NULL,
    activo          BOOLEAN NOT NULL DEFAULT TRUE,

    CONSTRAINT uq_estados_reserva_nombre UNIQUE (nombre),
    CONSTRAINT ck_estados_reserva_nombre CHECK (BTRIM(nombre) <> '')
);

CREATE TABLE reservas (
    reservaId       SERIAL PRIMARY KEY,
    fecha           DATE NOT NULL,
    laboratorioId   INT NOT NULL,
    computadoraId   INT NOT NULL,
    estudianteId    INT NOT NULL,
    horaInicio      TIME NOT NULL,
    horaFin         TIME NOT NULL,
    estadoReservaId INT NOT NULL,
    activa          BOOLEAN NOT NULL DEFAULT TRUE,

    CONSTRAINT fk_reservas_computadora_laboratorio
        FOREIGN KEY (computadoraId, laboratorioId)
        REFERENCES computadoras(computadoraId, laboratorioId),
    CONSTRAINT fk_reservas_estudiante
        FOREIGN KEY (estudianteId) REFERENCES estudiantes(estudianteId),
    CONSTRAINT fk_reservas_estado
        FOREIGN KEY (estadoReservaId)
        REFERENCES estadosReserva(estadoReservaId),
    CONSTRAINT ck_reservas_horas
        CHECK (horaFin > horaInicio),
    CONSTRAINT ck_reservas_duracion
        CHECK ((horaFin - horaInicio) <= INTERVAL '2 hours')
);

-- Una computadora no puede tener dos reservas activas traslapadas.
ALTER TABLE reservas
    ADD CONSTRAINT ex_reservas_computadora_sin_traslapes
    EXCLUDE USING gist (
        computadoraId WITH =,
        (tsrange(
            fecha + horaInicio,
            fecha + horaFin,
            '[)'
        )) WITH &&
    )
    WHERE (activa = TRUE);

-- Un estudiante no puede tener dos reservas activas simultáneas.
ALTER TABLE reservas
    ADD CONSTRAINT ex_reservas_estudiante_sin_traslapes
    EXCLUDE USING gist (
        estudianteId WITH =,
        (tsrange(
            fecha + horaInicio,
            fecha + horaFin,
            '[)'
        )) WITH &&
    )
    WHERE (activa = TRUE);

CREATE TABLE cierresMensuales (
    cierreMensualId SERIAL PRIMARY KEY,
    mes             INT NOT NULL,
    anno            INT NOT NULL,
    fechaCierre     TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    cerrado         BOOLEAN NOT NULL DEFAULT FALSE,

    CONSTRAINT uq_cierre_mes_anno UNIQUE (mes, anno),
    CONSTRAINT ck_cierre_mes CHECK (mes BETWEEN 1 AND 12),
    CONSTRAINT ck_cierre_anno CHECK (anno >= 2000)
);

CREATE TABLE reporte (
    reporteId          SERIAL PRIMARY KEY,
    cierreMensualId    INT NOT NULL,
    mes                INT NOT NULL,
    anno               INT NOT NULL,
    asistenteId        INT NOT NULL,
    horasPagadas       NUMERIC(8,2) NOT NULL,
    horasExtra         NUMERIC(8,2) NOT NULL,
    porcentajeRecargo  NUMERIC(4,2) NOT NULL,
    horasRecargo       NUMERIC(8,2) NOT NULL,
    pagoHora           NUMERIC(8,2) NOT NULL,
    montoTotal         NUMERIC(10,2) NOT NULL,

    CONSTRAINT fk_reporte_cierre
        FOREIGN KEY (cierreMensualId)
        REFERENCES cierresMensuales(cierreMensualId),
    CONSTRAINT fk_reporte_asistente
        FOREIGN KEY (asistenteId) REFERENCES asistentes(asistenteId),
    CONSTRAINT uq_reporte_asistente_cierre
        UNIQUE (cierreMensualId, asistenteId),
    CONSTRAINT ck_reporte_mes CHECK (mes BETWEEN 1 AND 12),
    CONSTRAINT ck_reporte_anno CHECK (anno >= 2000),
    CONSTRAINT ck_reporte_horas
        CHECK (
            horasPagadas >= 0
            AND horasExtra >= 0
            AND horasRecargo >= 0
        ),
    CONSTRAINT ck_reporte_valores
        CHECK (
            porcentajeRecargo >= 0
            AND pagoHora >= 0
            AND montoTotal >= 0
        )
);

-- Evita que se inserten, modifiquen o eliminen reportes de un mes cerrado.
CREATE OR REPLACE FUNCTION fn_proteger_reporte_cerrado()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    v_cierre_id INT;
    v_cerrado   BOOLEAN;
BEGIN
    IF TG_OP = 'DELETE' THEN
        v_cierre_id := OLD.cierreMensualId;
    ELSE
        v_cierre_id := NEW.cierreMensualId;
    END IF;

    SELECT cerrado
      INTO v_cerrado
      FROM cierresMensuales
     WHERE cierreMensualId = v_cierre_id
     FOR SHARE;

    IF v_cerrado = TRUE THEN
        RAISE EXCEPTION
            'No se puede modificar el reporte: el cierre mensual % ya está cerrado.',
            v_cierre_id;
    END IF;

    IF TG_OP = 'DELETE' THEN
        RETURN OLD;
    END IF;

    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_proteger_reporte_cerrado
BEFORE INSERT OR UPDATE OR DELETE ON reporte
FOR EACH ROW
EXECUTE FUNCTION fn_proteger_reporte_cerrado();

-- Los datos del reporte deben coincidir con el cierre al que pertenecen.
CREATE OR REPLACE FUNCTION fn_validar_periodo_reporte()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    v_mes  INT;
    v_anno INT;
BEGIN
    SELECT mes, anno
      INTO v_mes, v_anno
      FROM cierresMensuales
     WHERE cierreMensualId = NEW.cierreMensualId;

    IF NEW.mes <> v_mes OR NEW.anno <> v_anno THEN
        RAISE EXCEPTION
            'El mes y año del reporte deben coincidir con el cierre mensual.';
    END IF;

    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_validar_periodo_reporte
BEFORE INSERT OR UPDATE ON reporte
FOR EACH ROW
EXECUTE FUNCTION fn_validar_periodo_reporte();

CREATE TABLE notificaciones (
    notificacionId SERIAL PRIMARY KEY,
    usuarioId      INT NOT NULL,
    mensaje        VARCHAR(255) NOT NULL,
    fechaCreacion  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    leida          BOOLEAN NOT NULL DEFAULT FALSE,

    CONSTRAINT fk_notificaciones_usuario
        FOREIGN KEY (usuarioId) REFERENCES usuarios(usuarioId),
    CONSTRAINT ck_notificaciones_mensaje
        CHECK (BTRIM(mensaje) <> '')
);

CREATE OR REPLACE FUNCTION fn_validar_tope_semanal_reservas()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    v_inicio_semana DATE;
    v_horas_existentes NUMERIC(10,2);
    v_horas_nueva NUMERIC(10,2);
BEGIN
    IF NEW.activa = FALSE THEN
        RETURN NEW;
    END IF;

    PERFORM pg_advisory_xact_lock(1001, NEW.estudianteId);

    v_inicio_semana :=
        NEW.fecha - EXTRACT(DOW FROM NEW.fecha)::INT;

    SELECT COALESCE(
               SUM(EXTRACT(EPOCH FROM (horaFin - horaInicio)) / 3600.0),
               0
           )
      INTO v_horas_existentes
      FROM reservas
     WHERE estudianteId = NEW.estudianteId
       AND activa = TRUE
       AND fecha >= v_inicio_semana
       AND fecha < v_inicio_semana + 7
       AND reservaId <> NEW.reservaId;

    v_horas_nueva :=
        EXTRACT(EPOCH FROM (NEW.horaFin - NEW.horaInicio)) / 3600.0;

    IF v_horas_existentes + v_horas_nueva > 6 THEN
        RAISE EXCEPTION
            'La reserva excede el límite de 6 horas semanales del estudiante. Horas actuales: %, horas nuevas: %.',
            v_horas_existentes, v_horas_nueva;
    END IF;

    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_tope_semanal_reservas
BEFORE INSERT OR UPDATE OF
    estudianteId, fecha, horaInicio, horaFin, activa
ON reservas
FOR EACH ROW
EXECUTE FUNCTION fn_validar_tope_semanal_reservas();

CREATE OR REPLACE FUNCTION fn_validar_tope_semanal_asistente()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    v_inicio_semana DATE;
    v_max_horas INT;
    v_activo_asistente BOOLEAN;
    v_horas_existentes NUMERIC(10,2);
    v_horas_nuevas NUMERIC(10,2);
BEGIN
    IF NEW.asistenteId IS NULL OR NEW.activo = FALSE THEN
        RETURN NEW;
    END IF;

    PERFORM pg_advisory_xact_lock(1002, NEW.asistenteId);

    SELECT maxHoras, activo
      INTO v_max_horas, v_activo_asistente
      FROM asistentes
     WHERE asistenteId = NEW.asistenteId;

    IF v_activo_asistente IS DISTINCT FROM TRUE THEN
        RAISE EXCEPTION
            'No se pueden asignar turnos a un asistente inactivo.';
    END IF;

    v_inicio_semana :=
        NEW.fecha - EXTRACT(DOW FROM NEW.fecha)::INT;

    SELECT COALESCE(
               SUM(EXTRACT(EPOCH FROM (horaFin - horaInicio)) / 3600.0),
               0
           )
      INTO v_horas_existentes
      FROM turnos
     WHERE asistenteId = NEW.asistenteId
       AND activo = TRUE
       AND fecha >= v_inicio_semana
       AND fecha < v_inicio_semana + 7
       AND turnoId <> NEW.turnoId;

    v_horas_nuevas :=
        EXTRACT(EPOCH FROM (NEW.horaFin - NEW.horaInicio)) / 3600.0;

    IF v_horas_existentes + v_horas_nuevas > v_max_horas THEN
        RAISE EXCEPTION
            'La asignación excede el tope semanal del asistente. Tope: %, horas ya asignadas: %, horas del turno: %.',
            v_max_horas, v_horas_existentes, v_horas_nuevas;
    END IF;

    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_tope_semanal_asistente
BEFORE INSERT OR UPDATE OF
    asistenteId, fecha, horaInicio, horaFin, activo
ON turnos
FOR EACH ROW
EXECUTE FUNCTION fn_validar_tope_semanal_asistente();

CREATE INDEX ix_postulaciones_estudiante
    ON postulaciones(estudianteId);

CREATE INDEX ix_postulaciones_convocatoria
    ON postulaciones(convocatoriaId);

CREATE INDEX ix_turnos_laboratorio_fecha
    ON turnos(laboratorioId, fecha);

CREATE INDEX ix_turnos_asistente_fecha
    ON turnos(asistenteId, fecha);

CREATE INDEX ix_reservas_laboratorio_fecha
    ON reservas(laboratorioId, fecha);

CREATE INDEX ix_reservas_estudiante_fecha
    ON reservas(estudianteId, fecha);

CREATE INDEX ix_historial_computadora
    ON historialComputadoras(computadoraId, fechaInicio);

CREATE INDEX ix_notificaciones_usuario_fecha
    ON notificaciones(usuarioId, fechaCreacion);