"""
Modelos relacionales de Zenoxia Core — SQLAlchemy 2.0 Async / Mapped / typed.
Entidades alineadas al estándar HL7 FHIR para interoperabilidad entre módulos
Cordis (Guardia), Kairos (Quirófanos), Camas y futuros módulos.

Principio de oro: este archivo contiene SOLO lo genuinamente compartido entre
dos o más módulos. Lo específico de un módulo vive en ese módulo, nunca acá.
Ver database/_candidatos_a_mover.py para el código que salió del core.
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
# Enumeraciones de dominio — CORE COMPARTIDO (categoría A)
# Criterio: usadas por 2+ módulos del ecosistema.
# ---------------------------------------------------------------------------

class TipoRecursoFHIR(str, enum.Enum):
    """
    FHIR Location.physicalType — infraestructura física del establecimiento.
    Compartido: Cordis (llamador, traslados), Kairos (quirófano, cama post-op),
    Camas (gestión de disponibilidad), ICU (cama UTI).
    """
    CONSULTORIO = "CONSULTORIO"
    BOX_OBSERVACION = "BOX_OBSERVACION"
    CAMA_INTERNACION = "CAMA_INTERNACION"
    QUIROFANO = "QUIROFANO"
    SALA_ESPERA = "SALA_ESPERA"
    AREA_IMAGEN = "AREA_IMAGEN"
    UTI = "UTI"
    UCO = "UCO"


class EstadoCacheRecurso(str, enum.Enum):
    """
    Estado operativo del recurso físico.
    Compartido: Cordis (llamador dinámico), Kairos (disponibilidad de quirófano),
    Camas (libre/ocupado), ICU.
    """
    LIBRE = "LIBRE"
    OCUPADO = "OCUPADO"
    LIMPIEZA = "LIMPIEZA"
    FUERA_DE_SERVICIO = "FUERA_DE_SERVICIO"


class EstadoEncounter(str, enum.Enum):
    """
    Estado genérico del encuentro clínico — alineado a FHIR Encounter.status.
    Compartido: todos los módulos que crean episodios (Cordis, Kairos, Gia, Camas).
    Los estados específicos del flujo de cada módulo (ej. EN_TRIAGE de Cordis,
    EN_QUIROFANO de Kairos) se registran en HitoTiempo, no acá.
    Ver _candidatos_a_mover.py → EstadoEpisodio para los estados Cordis-específicos.
    """
    ACTIVO = "ACTIVO"           # FHIR: in-progress — el episodio está en curso
    EN_ESPERA = "EN_ESPERA"     # FHIR: on-hold / planned — pendiente de inicio
    COMPLETADO = "COMPLETADO"   # FHIR: completed / discharged — cerrado exitosamente
    CANCELADO = "CANCELADO"     # FHIR: cancelled — anulado


class EstadoTraslado(str, enum.Enum):
    """
    Máquina de estados del traslado físico.
    Compartido: Cordis (camilleros en guardia), Kairos (movimiento a/desde quirófano),
    Camas (traslado a cama asignada), ICU.
    """
    SOLICITADO = "SOLICITADO"
    ASIGNADO = "ASIGNADO"
    EN_CAMINO_ORIGEN = "EN_CAMINO_ORIGEN"
    PACIENTE_A_BORDO = "PACIENTE_A_BORDO"
    EN_CAMINO_DESTINO = "EN_CAMINO_DESTINO"
    COMPLETADO = "COMPLETADO"
    CANCELADO = "CANCELADO"


class EquipoTraslado(str, enum.Enum):
    """
    Medio de traslado físico del paciente.
    Compartido: cualquier módulo que mueva pacientes entre ubicaciones.
    """
    CAMINA_SOLO = "CAMINA_SOLO"
    SILLA_DE_RUEDAS = "SILLA_DE_RUEDAS"
    CAMILLA = "CAMILLA"
    FAMILIAR_ASISTIDO = "FAMILIAR_ASISTIDO"
    AMBULANCIA_INTERNA = "AMBULANCIA_INTERNA"


class PrioridadTraslado(str, enum.Enum):
    """Compartido: toda solicitud de traslado en cualquier módulo tiene una prioridad."""
    URGENTE = "URGENTE"
    NORMAL = "NORMAL"
    PROGRAMADO = "PROGRAMADO"


# producto_origen es un String libre a propósito: cada módulo estampa su nombre
# ("Cordis", "Kairos", "Camas", "ICU", etc.) sin que el core deba conocerlos de
# antemano. Un enum cerrado obligaría a tocar el core cada vez que entra o sale
# un módulo del ecosistema — exactamente lo que el principio de oro prohíbe.

# ---------------------------------------------------------------------------
# Modelos — CORE COMPARTIDO (categoría A)
# ---------------------------------------------------------------------------

class Patient(Base):
    """
    FHIR Patient — identidad del paciente.
    Compartido: todos los módulos trabajan sobre el mismo paciente.
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
    # FHIR gender: male | female | other | unknown
    sexo: Mapped[str] = mapped_column(String(10), nullable=False)
    telefono: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

    # Antecedentes clínicos de fondo del paciente — transversal a todos los módulos.
    # Ejemplos: alergias conocidas, condiciones crónicas, medicación habitual.
    # NO incluye tags de una visita puntual (esos son de cada módulo).
    # Schema JSONB libre; el contenido específico lo define cada módulo al escribir.
    # Ver _candidatos_a_mover.py → MÓDULO: Cordis para los tags de visita de guardia.
    antecedentes_clinicos: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    episodios: Mapped[list[Episodio]] = relationship(
        back_populates="patient", cascade="all, delete-orphan"
    )


class MedicalService(Base):
    """
    Catálogo extensible de especialidades. No hardcodeado en queries.
    Compartido: Cordis (derivación en guardia), Kairos (servicio quirúrgico),
    Gia (obstetricia), Camas (asignación por especialidad).
    FHIR: HealthcareService / ServiceType CodeSystem.
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
    Compartido: Cordis (traslados, llamador), Kairos (quirófano, cama post-op),
    Camas (disponibilidad), ICU (cama UTI).
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
    FHIR Encounter — transacción de la visita/encuentro clínico.
    Compartido: todos los módulos registran encuentros (guardia, cirugía, obstetricia).

    Estado: usa EstadoEncounter (genérico FHIR). Los estados específicos de cada
    módulo (triage, llamado médico, etc.) se registran como HitoTiempo, no acá.
    El enum Cordis-específico EstadoEpisodio vive en _candidatos_a_mover.py.
    """
    __tablename__ = "episodio"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    patient_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("patient.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    medical_service_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("medical_service.id", ondelete="SET NULL"), nullable=True, index=True
    )
    # Ubicación física actual del paciente
    location_actual_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("location_resource.id", ondelete="SET NULL"), nullable=True
    )

    # Estado genérico FHIR — compartido por todos los módulos.
    estado: Mapped[EstadoEncounter] = mapped_column(
        Enum(EstadoEncounter, name="estado_encounter"),
        default=EstadoEncounter.ACTIVO,
        nullable=False,
        index=True,
    )

    # Módulo emisor — string libre, ver comentario sobre producto_origen arriba.
    producto_origen: Mapped[str] = mapped_column(String(20), nullable=False)

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
    Logística de movimiento físico entre LocationResources.
    Compartido: Cordis (camilleros en guardia), Kairos (traslado a/desde quirófano),
    Camas (traslado a cama asignada), ICU.
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

    # Quién ejecuta el traslado (camillero, enfermero, técnico, etc.).
    # Genérico: aplica a cualquier módulo que mueva pacientes.
    responsable_traslado_id: Mapped[Optional[uuid.UUID]] = mapped_column(nullable=True)

    # Timestamps de auditoría RTT/SLA — compartidos por todos los módulos.
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
    Compartido: todos los módulos registran transiciones de estado acá.
    `producto_origen` identifica el módulo emisor.
    `hito_codigo` es un string libre — cada módulo define sus propios códigos.
    `metadata_evento` acepta cualquier payload FHIR (signos vitales, lab, etc.).
    NUNCA se actualiza ni elimina; toda corrección es un hito compensatorio.
    """
    __tablename__ = "hito_tiempo"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    episodio_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("episodio.id", ondelete="CASCADE"), index=True, nullable=False
    )

    # Módulo emisor — string libre, ver comentario sobre producto_origen arriba.
    producto_origen: Mapped[str] = mapped_column(String(20), nullable=False)
    # String libre — cada módulo define su vocabulario de hitos sin tocar el core.
    # Cordis: TRIAGE_COMPLETADO, MEDICO_LLAMADO, etc.
    # Kairos: PREINGRESO_CONFIRMADO, CIRUGIA_INICIADA, etc.
    hito_codigo: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    actor_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    actor_rol: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    actor_nombre: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Payload libre: signos vitales, recursos FHIR, datos específicos del módulo.
    metadata_evento: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    registrado_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True, nullable=False
    )

    episodio: Mapped[Episodio] = relationship(back_populates="hitos")
