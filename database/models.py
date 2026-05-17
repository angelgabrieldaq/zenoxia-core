"""
Modelos relacionales de Zenoxia Core — SQLAlchemy 2.0 Async / Mapped / typed.
Entidades alineadas al estándar HL7 FHIR para interoperabilidad entre módulos
Cordis (Guardia), Kairos (Quirófanos) y Gia (Obstetricia SaMD).
"""

from __future__ import annotations

import enum
import uuid
from datetime import date, datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    relationship,
)


# ---------------------------------------------------------------------------
# Base declarativa con soporte async (SQLAlchemy 2.0)
# ---------------------------------------------------------------------------

class Base(AsyncAttrs, DeclarativeBase):
    pass


# ---------------------------------------------------------------------------
# Enumeraciones de dominio
# ---------------------------------------------------------------------------

class TipoRecursoFHIR(str, enum.Enum):
    """FHIR Location.physicalType — infraestructura física del establecimiento."""
    CONSULTORIO = "CONSULTORIO"
    BOX_OBSERVACION = "BOX_OBSERVACION"
    CAMA_INTERNACION = "CAMA_INTERNACION"
    QUIROFANO = "QUIROFANO"
    SALA_ESPERA = "SALA_ESPERA"
    AREA_IMAGEN = "AREA_IMAGEN"
    UTI = "UTI"
    UCO = "UCO"


class EstadoCacheRecurso(str, enum.Enum):
    """Estado operativo del recurso físico; mutable para el llamador dinámico."""
    LIBRE = "LIBRE"
    OCUPADO = "OCUPADO"
    LIMPIEZA = "LIMPIEZA"
    FUERA_DE_SERVICIO = "FUERA_DE_SERVICIO"


class EstadoEpisodio(str, enum.Enum):
    """Máquina de estados del paciente en el viaje por la guardia (Cordis)."""
    INGRESO_RECEPCION = "INGRESO_RECEPCION"
    SALA_ESPERA_PRE_TRIAGE = "SALA_ESPERA_PRE_TRIAGE"
    EN_TRIAGE = "EN_TRIAGE"
    SALA_ESPERA_EVALUADO = "SALA_ESPERA_EVALUADO"
    MEDICO_LLAMADO = "MEDICO_LLAMADO"
    EN_ATENCION = "EN_ATENCION"
    PENDIENTE_ESTUDIO = "PENDIENTE_ESTUDIO"
    RETORNO_POST_ESTUDIO = "RETORNO_POST_ESTUDIO"
    OBSERVACION_TRANSITORIA = "OBSERVACION_TRANSITORIA"
    EN_OBSERVACION = "EN_OBSERVACION"
    EGRESO_FISICO = "EGRESO_FISICO"
    ALTA_MEDICA = "ALTA_MEDICA"


class NivelTriage(str, enum.Enum):
    """Escala de Manchester / prioridad de urgencia N1 (crítico) — N5 (no urgente)."""
    N1 = "N1"
    N2 = "N2"
    N3 = "N3"
    N4 = "N4"
    N5 = "N5"


class EstadoTraslado(str, enum.Enum):
    """Máquina de estados del camillero (RN-12)."""
    SOLICITADO = "SOLICITADO"
    ASIGNADO = "ASIGNADO"
    EN_CAMINO_ORIGEN = "EN_CAMINO_ORIGEN"
    PACIENTE_A_BORDO = "PACIENTE_A_BORDO"
    EN_CAMINO_DESTINO = "EN_CAMINO_DESTINO"
    COMPLETADO = "COMPLETADO"
    CANCELADO = "CANCELADO"


class EquipoTraslado(str, enum.Enum):
    """Escenarios de traslado físico — Escenarios 1-5 del diseño."""
    CAMINA_SOLO = "CAMINA_SOLO"           # Escenario 1 — autónomo
    SILLA_DE_RUEDAS = "SILLA_DE_RUEDAS"  # Escenario 3 — asistido
    CAMILLA = "CAMILLA"                   # Escenario 3 — asistido
    FAMILIAR_ASISTIDO = "FAMILIAR_ASISTIDO"
    AMBULANCIA_INTERNA = "AMBULANCIA_INTERNA"


class PrioridadTraslado(str, enum.Enum):
    URGENTE = "URGENTE"
    NORMAL = "NORMAL"
    PROGRAMADO = "PROGRAMADO"


class ProductoOrigen(str, enum.Enum):
    """Módulo emisor del evento — identifica el producto en entornos multi-módulo."""
    CORDIS = "Cordis"
    KAIROS = "Kairos"
    GIA = "Gia"


# ---------------------------------------------------------------------------
# Modelos
# ---------------------------------------------------------------------------

class Patient(Base):
    """
    FHIR Patient — datos de identidad inmutables del paciente.
    El DNI es el identificador primario de negocio (7-8 dígitos, indexado).
    """
    __tablename__ = "patient"
    __table_args__ = (
        CheckConstraint(r"dni ~ '^\d{7,8}$'", name="ck_patient_dni_format"),
        UniqueConstraint("dni", name="uq_patient_dni"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    dni: Mapped[str] = mapped_column(String(8), index=True, nullable=False)
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    apellido: Mapped[str] = mapped_column(String(100), nullable=False)
    fecha_nacimiento: Mapped[date] = mapped_column(Date, nullable=False)
    # FHIR gender: male | female | other | unknown → almacenado como código
    sexo: Mapped[str] = mapped_column(String(10), nullable=False)
    telefono: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

    episodios: Mapped[list[Episodio]] = relationship(
        back_populates="patient", cascade="all, delete-orphan"
    )


class MedicalService(Base):
    """
    Catálogo extensible de especialidades y servicios. No hardcodeado en queries.
    Permite al administrador añadir nuevos servicios (ej. Cardiología) sin tocar backend.
    FHIR equivalente: HealthcareService / ServiceType CodeSystem.
    """
    __tablename__ = "medical_service"
    __table_args__ = (
        UniqueConstraint("codigo", name="uq_medical_service_codigo"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    # Código corto operativo: CLIN, PEDI, TRAU, CIRU, GINO, etc.
    codigo: Mapped[str] = mapped_column(String(10), index=True, nullable=False)
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    # Flujo de derivación: GUARDIA, INTERNACION, QUIROFANO, OBSTETRICIA
    tipo_flujo: Mapped[str] = mapped_column(String(50), nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    episodios: Mapped[list[Episodio]] = relationship(back_populates="medical_service")


class LocationResource(Base):
    """
    FHIR Location — tabla unificada de infraestructura física del establecimiento.
    Cubre boxes, camas, consultorios, quirófanos y salas de espera.
    `estado_cache` es mutable y controla la visibilidad del llamador dinámico (Escenario 2).
    `llamador_habilitado` se deshabilita en UI cuando el recurso entra en observación transitoria.
    """
    __tablename__ = "location_resource"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    # Identificador FHIR externo (opcional, para interoperabilidad HIE)
    fhir_location_id: Mapped[Optional[str]] = mapped_column(
        String(100), unique=True, nullable=True
    )
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    tipo: Mapped[TipoRecursoFHIR] = mapped_column(
        Enum(TipoRecursoFHIR, name="tipo_recurso_fhir"), nullable=False
    )
    sector: Mapped[str] = mapped_column(String(50), nullable=False)
    estado_cache: Mapped[EstadoCacheRecurso] = mapped_column(
        Enum(EstadoCacheRecurso, name="estado_cache_recurso"),
        default=EstadoCacheRecurso.LIBRE,
        nullable=False,
        index=True,
    )
    # Habilitado = True por defecto; False bloquea el botón "Llamar" en la UI
    llamador_habilitado: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    traslados_como_origen: Mapped[list[Traslado]] = relationship(
        back_populates="origen",
        foreign_keys="Traslado.origen_recurso_id",
    )
    traslados_como_destino: Mapped[list[Traslado]] = relationship(
        back_populates="destino",
        foreign_keys="Traslado.destino_recurso_id",
    )
    episodios_activos: Mapped[list[Episodio]] = relationship(
        back_populates="location_actual",
        foreign_keys="Episodio.location_actual_id",
    )


class Episodio(Base):
    """
    FHIR Encounter — transacción de la visita actual.
    Conecta al Paciente con el MedicalService de derivación.
    `tags_clinicos` almacena antecedentes críticos de baja prioridad y metadatos de triage.
    """
    __tablename__ = "episodio"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    patient_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("patient.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    medical_service_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("medical_service.id", ondelete="SET NULL"), nullable=True, index=True
    )
    # Ubicación física actual del paciente según la Location Matrix
    location_actual_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("location_resource.id", ondelete="SET NULL"), nullable=True
    )

    estado: Mapped[EstadoEpisodio] = mapped_column(
        Enum(EstadoEpisodio, name="estado_episodio"),
        default=EstadoEpisodio.INGRESO_RECEPCION,
        nullable=False,
        index=True,
    )
    nivel_triage: Mapped[Optional[NivelTriage]] = mapped_column(
        Enum(NivelTriage, name="nivel_triage"), nullable=True
    )
    # JSONB: {antecedentes: [...], alergias: [...], tags_clinicos: [...]}
    tags_clinicos: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Módulo emisor; habilita filtrado multi-producto en entornos compartidos
    producto_origen: Mapped[ProductoOrigen] = mapped_column(
        Enum(ProductoOrigen, name="producto_origen"),
        default=ProductoOrigen.CORDIS,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )
    cerrado_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    patient: Mapped[Patient] = relationship(back_populates="episodios")
    medical_service: Mapped[Optional[MedicalService]] = relationship(
        back_populates="episodios"
    )
    location_actual: Mapped[Optional[LocationResource]] = relationship(
        back_populates="episodios_activos",
        foreign_keys=[location_actual_id],
    )
    traslados: Mapped[list[Traslado]] = relationship(
        back_populates="episodio", cascade="all, delete-orphan"
    )
    hitos: Mapped[list[HitoTiempo]] = relationship(
        back_populates="episodio", cascade="all, delete-orphan"
    )


class Traslado(Base):
    """
    Entidad de logística dinámica de camilleros.
    origen_recurso_id → destino_recurso_id cubren los 5 escenarios de terreno.
    Timestamps solicitado/asignado/inicio/completado permiten calcular RTT y SLA.
    """
    __tablename__ = "traslado"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    episodio_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("episodio.id", ondelete="CASCADE"), index=True, nullable=False
    )
    origen_recurso_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("location_resource.id", ondelete="SET NULL"), nullable=True
    )
    destino_recurso_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("location_resource.id", ondelete="SET NULL"), nullable=True
    )

    equipo_requerido: Mapped[EquipoTraslado] = mapped_column(
        Enum(EquipoTraslado, name="equipo_traslado"), nullable=False
    )
    prioridad: Mapped[PrioridadTraslado] = mapped_column(
        Enum(PrioridadTraslado, name="prioridad_traslado"),
        default=PrioridadTraslado.NORMAL,
        nullable=False,
    )
    estado: Mapped[EstadoTraslado] = mapped_column(
        Enum(EstadoTraslado, name="estado_traslado"),
        default=EstadoTraslado.SOLICITADO,
        nullable=False,
        index=True,
    )

    # FK a la tabla de usuarios/camilleros — se resolverá al integrar el módulo de RRHH
    camillero_id: Mapped[Optional[uuid.UUID]] = mapped_column(nullable=True)

    # Timestamps de auditoría RTT/SLA
    solicitado_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    asignado_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    inicio_traslado_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completado_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    episodio: Mapped[Episodio] = relationship(back_populates="traslados")
    origen: Mapped[Optional[LocationResource]] = relationship(
        back_populates="traslados_como_origen",
        foreign_keys=[origen_recurso_id],
    )
    destino: Mapped[Optional[LocationResource]] = relationship(
        back_populates="traslados_como_destino",
        foreign_keys=[destino_recurso_id],
    )


class HitoTiempo(Base):
    """
    FHIR AuditEvent / Provenance — tabla Append-Only e inmutable.
    Registra cada transición de estado del episodio con trazabilidad completa.
    `metadata_evento` acepta payloads FHIR arbitrarios (signos vitales, laboratorio, etc.).
    NUNCA se actualiza ni elimina; toda corrección se registra como hito compensatorio.
    """
    __tablename__ = "hito_tiempo"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    episodio_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("episodio.id", ondelete="CASCADE"), index=True, nullable=False
    )

    producto_origen: Mapped[ProductoOrigen] = mapped_column(
        Enum(ProductoOrigen, name="producto_origen"),
        nullable=False,
    )
    # Código de hito: TRIAGE_COMPLETADO, MEDICO_LLAMADO, OBSERVACION_TRANSITORIA_INICIADA, etc.
    hito_codigo: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    # Actor que generó el evento (puede ser un sistema automático o un usuario)
    actor_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    actor_rol: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    actor_nombre: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Payload libre: signos vitales, recursos FHIR serializados, datos de contexto
    metadata_evento: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    registrado_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True, nullable=False
    )

    episodio: Mapped[Episodio] = relationship(back_populates="hitos")
