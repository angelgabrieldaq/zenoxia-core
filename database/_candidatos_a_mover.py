"""
database/_candidatos_a_mover.py
================================
ARCHIVO DE STAGING — No importar en producción.

Contiene código extraído de database/models.py durante la depuración del core
(feature/core-depuracion). Cada bloque está marcado con el módulo de destino.

Estas entidades violan el principio de oro: las usa UN SOLO módulo,
por lo tanto no pertenecen al core compartido.

Cuando cada módulo esté listo para recibirlos:
  1. Copiar el bloque al repo del módulo correspondiente.
  2. Reemplazar `from database.models import Base` por la Base del módulo.
  3. Eliminar este archivo del core.
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Numeric, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.models import Base, Episodio  # noqa: F401 — referencia para FK


# ===========================================================================
# MÓDULO: Cordis (guardia/urgencias)
# Razón: lógica y campos específicos del flujo de guardia.
# Destino: cordis/database/models.py o cordis/domain/
# ===========================================================================

# ---------------------------------------------------------------------------
# Campo: LocationResource.llamador_habilitado (Boolean, default=True)
# Razón: controla el botón "Llamar" del llamador dinámico — concepto exclusivo
# de Cordis. El core cubre disponibilidad del recurso solo con estado_cache.
# Destino: Cordis necesita extender LocationResource (o mantener una tabla
# propia) con este flag. Al leer estado_cache == OCUPADO puede inferir que
# el llamador debe estar deshabilitado, pero el flag explícito de UI es de Cordis.
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Campo: tags de visita puntual de guardia (ex Episodio.tags_clinicos)
# Razón: los antecedentes de fondo del paciente se movieron a Patient.antecedentes_clinicos.
# Lo que sean tags específicos de una visita de guardia (ej. motivo_consulta_tags,
# signos_vitales_iniciales, clasificación interna de triage) son de Cordis.
# Destino: Cordis debe definir su propia extensión del Episodio (tabla o JSONB
# en un modelo Cordis-específico) con los tags de visita que necesite.
# Nombre sugerido: CordisEpisodioExtension.tags_guardia (JSONB)
# ---------------------------------------------------------------------------

class EstadoEpisodio(str, enum.Enum):
    """
    Máquina de estados del paciente en el viaje por la guardia (Cordis).
    MÓDULO: Cordis — no compartido con otros módulos.
    En el core, Episodio.estado usa EstadoEncounter (genérico FHIR).
    """
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
    """
    Escala de Manchester N1-N5. Exclusivo de la guardia de urgencias (Cordis).
    MÓDULO: Cordis — Kairos, Camas e ICU no usan triage de manchesteriana.
    El valor se registra en HitoTiempo.metadata_evento al completar el triage.
    """
    N1 = "N1"
    N2 = "N2"
    N3 = "N3"
    N4 = "N4"
    N5 = "N5"


# ===========================================================================
# MÓDULO: Gia (Obstetricia SaMD — en revisión, probable baja)
# Razón: clasificación clínica obstétrica específica del protocolo FASGO 2025.
# Ningún otro módulo usa estos conceptos.
# Destino: gia/database/models.py — SOLO si Gia se confirma como módulo activo.
# Si Gia se da de baja, este bloque se elimina sin deuda en el core.
# ===========================================================================

class ClasificacionHTAFASGO2025(str, enum.Enum):
    """
    Clasificación FASGO 2025 de trastornos hipertensivos en el embarazo.
    Elimina los conceptos de PE 'leve' y 'severa'.
    MÓDULO: Gia — exclusivo del protocolo obstétrico.
    """
    HIPERTENSION_GESTACIONAL = "HIPERTENSION_GESTACIONAL"
    PREECLAMPSIA = "PREECLAMPSIA"
    ECLAMPSIA = "ECLAMPSIA"
    HIPERTENSION_CRONICA = "HIPERTENSION_CRONICA"
    HIPERTENSION_CRONICA_CON_PE_SOBREAGREGADA = "HIPERTENSION_CRONICA_CON_PE_SOBREAGREGADA"
    HIPERTENSION_NO_CLASIFICADA = "HIPERTENSION_NO_CLASIFICADA"


class EpisodioObstetrico(Base):
    """
    Extensión obstétrica del Episodio — protocolo FASGO 2025.
    MÓDULO: Gia — relación one-to-one con Episodio, solo existe para Gia.
    Ningún otro módulo crea ni lee esta tabla.
    """
    __tablename__ = "episodio_obstetrico"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    episodio_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("episodio.id", ondelete="CASCADE"),
        unique=True,
        index=True,
        nullable=False,
    )

    clasificacion_hta: Mapped[Optional[ClasificacionHTAFASGO2025]] = mapped_column(
        Enum(ClasificacionHTAFASGO2025, name="clasificacion_hta_fasgo2025"),
        nullable=True,
        index=True,
    )

    edad_gestacional_semanas: Mapped[Optional[int]] = mapped_column(nullable=True)
    presion_sistolica_mmhg: Mapped[Optional[int]] = mapped_column(nullable=True)
    presion_diastolica_mmhg: Mapped[Optional[int]] = mapped_column(nullable=True)

    # --- Signos de Severidad — Compromiso Neurológico ---
    sev_eclampsia: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    sev_cefalea_persistente: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    sev_escotomas: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # --- Signos de Severidad — Compromiso Hepático ---
    sev_epigastralgia: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    sev_got_elevada: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    sev_got_valor_ul: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 2), nullable=True)
    sev_gpt_elevada: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    sev_gpt_valor_ul: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 2), nullable=True)

    # --- Signos de Severidad — Compromiso Hematológico ---
    sev_trombocitopenia: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    sev_plaquetas_valor_mm3: Mapped[Optional[int]] = mapped_column(nullable=True)

    # --- Proteinuria — uRPC (>= 30 mg/mmol, punto de corte FASGO 2025) ---
    urpc_valor_mg_mmol: Mapped[Optional[Decimal]] = mapped_column(Numeric(7, 2), nullable=True)
    urpc_confirmatorio: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    urpc_fecha_muestra: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    registrado_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    episodio: Mapped[Episodio] = relationship(back_populates="episodio_obstetrico")
