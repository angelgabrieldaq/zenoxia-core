# CLAUDE.md — zenoxia-core

> Este archivo da contexto persistente a Claude Code. Se lee al inicio de cada sesión.

---

## Parte de Zenoxia (ecosistema)

Este repo es el **core** del ecosistema clínico Zenoxia: la base de datos central
e interoperable (FHIR) por la que se comunican los módulos.

**Principio de oro — NO violar:**
> El core contiene SOLO lo genuinamente compartido entre módulos.
> Lo específico de un módulo vive en ese módulo, nunca acá.
> Regla práctica: si solo lo usa UN módulo, NO va en el core.

Visión completa del ecosistema: `docs/VISION_ECOSISTEMA_ZENOXIA.md` (este repo).
Léela antes de proponer cambios estructurales.

Módulos del ecosistema: Cordis (guardia), Kairos (quirófanos), Camas (a diseñar),
ICU (futuro), Gia (en revisión, probable baja).

---

## Qué es este repo

El vocabulario común del ecosistema: las entidades que más de un módulo necesita,
mapeadas a HL7 FHIR. Stack: Python / FastAPI / SQLAlchemy 2.0 async / PostgreSQL.

**Entidades del core** (en `database/models.py`): Patient, MedicalService,
LocationResource, Episodio, Traslado, HitoTiempo. (EpisodioObstetrico y la
clasificación FASGO están marcados como candidatos a salir — son lógica de un
solo módulo, ver visión.)

**HitoTiempo es append-only e inmutable.** La auditoría no se reescribe nunca.

---

## Reglas de trabajo

- Antes de agregar un campo o entidad: preguntarse "¿esto lo usa más de un módulo?".
  Si no, no va acá.
- No pushear sin OK visual/explícito.
- Mostrar git status y diff antes de commitear.
