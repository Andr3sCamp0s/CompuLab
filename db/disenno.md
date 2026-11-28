# Diseño de base de datos

## Tablas

### usuarios
- usuarioId serial PK
- nombre varchar(50) not null
- correo varchar(35) not null
- activo boolean not null default true

### convocatorias
- convocatoriaId serial PK
- semestre varchar(10) not null
- fechaInicio date not null
- fechaFin date not null
- estado varchar(15) not null

### estudiantes
- estudianteId serial PK
- usuarioId int FK not null
- carnet varchar(10) not null
- activo boolean not null default true

### laboratorios
- laboratorioId serial PK
- coordinadorId int FK not null
- nombre varchar(100) not null
- cantComputadoras int not null 
- activo boolean not null default true

### horarios
- horarioId serial PK
- asistenteId int FK not null
- dia int not null
- horaInicio time not null
- horaFin time not null
- activo boolean not null default true

### turnos
- turnoId serial PK
- laboratorioId int FK not null
- fecha date not null
- horaInicio time not null
- horaFin time not null
- horaInicioReportada timestamp default null
- horaFinReportada timestamp default null
- asistenteId int FK 
- disponible boolean not null default false
- reasignar boolean not null default false
- activo boolean not null default true

### cambiosDeTurno
- cambioDeTurnoID serial PK
- turnoId int FK not null
- asistenteActual int FK not null
- asistenteNuevo int FK not null
- estado boolean not null default false

### computadoras
- computadoraId serial PK
- laboratorioId int FK not null
- estado 
- activo boolean not null default true

### historialComputadoras
- historialComputadoraId serial PK
- computadoraId int FK not null
- estado boolean not null
- fechaInicio date not null
- fechaFin date
- usuarioId int FK not null

### estadosReserva
- estadoReservaId serial PK
- nombre varchar(15) not null
- descripcion varchar(100) not null
- activo boolean not null default true

### reservas
- reservaId serial PK
- fecha date not null
- laboratorioId int FK not null
- computadoraId int FK not null
- estudianteId int FK not null
- horaInicio time not null
- horaFin time not null
- estadoReservaId int FK not null

### categorias
- categoriaId serial PK
- nombre varchar(20) not null
- pagoHora numeric(8,2) not null
- porcentajeRecargo numeric(4,2) not null
- activo boolean not null default true

### asistentes
- asistenteId serial PK
- estudianteId int FK not null
- categoriaId int FK not null
- maxHoras int not null
- activo boolean not null default true

### historialAsistentes
- historialAsistenteId serial PK
- asistenteId int FK not null
- movimiento varchar(20) not null
- coordinadorId int FK
- motivo varchar(255)

### laboratoriosPorAsistente
- laboratorioPorAsistenteId serial PK 
- laboratorioId int FK not null
- asistenteId int FK not null
- activo boolean not null default true

### coordinadores
- coordinadorId serial Pk
- usuarioId int FK not null
- esDeSoporte boolean not null default false
- activo boolean not null default true

### reporte
- reporteId serial PK
- cierreMensualId int FK not null
- mes int not null
- anno int not null
- asistenteId int FK not null
- horasPagadas int not null
- horasExtra int not null
- porcentajeRecargo numeric(4,2) not null
- horasRecargo int not null
- pagoHora numeric(8,2) not null
- montoTotal numeric(10,2) not null

### cierresMensuales
- cierreMensualId serial PK
- mes int not null
- anno int not null
- fechaCierre timestamp not null
- cerrado boolean not null default false

### estadosPostulacion
- estadoPostulacionId serial PK
- nombre varchar(15) not null
- descripcion varchar(100) not null
- activo boolean not null default true

### postulaciones
- postulacionId serial PK
- estudianteId int FK not null
- convocatoriaId int FK not null
- fechaPostulacion date not null
- estadoPostulacionId int FK not null

### disponibilidadPostulacion
- disponibilidadPostulacionId serial PK
- postulacionId	int FK not null
- dia int not null
- horaInicio time not null
- horaFin time not null

### laboratoriosPostulacion
- laboratorioPostulacionId	serial	PK
- postulacionId	int	FK not null
- laboratorioId	int	FK not null

### entrevistas
- entrevistaId serial PK
- coordinadorId int FK not null
- postulacionId int FK not null
- fecha timestamp not null
- comentarios varchar(255)

### notificaciones
- notificacionId serial PK
- usuarioId int FK not null
- mensaje varchar(255) not null
- fechaCreacion timestamp not null