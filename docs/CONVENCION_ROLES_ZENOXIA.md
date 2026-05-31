# Zenoxia — Convención de Roles-Actor
## Documento de ecosistema · vocabulario compartido de actores

Define cómo se nombran los actores que ejecutan eventos registrados en la auditoría
(`HitoTiempo.actor_rol` del core). Es vocabulario COMPARTIDO: todos los módulos
escriben los roles con esta convención para que la auditoría sea consistente entre
módulos. Subordinado a `VISION_ECOSISTEMA_ZENOXIA.md` y al principio de oro.

---

# 1. Por qué existe esta convención

Hoy `actor_rol` es un string libre en el core (decisión deliberada: no se creó una
tabla catálogo todavía, ver más abajo). El riesgo del string libre es la
inconsistencia entre módulos: que uno escriba `"hoteleria"`, otro `"Hotelería"` y
otro `"HOTELERIA"` para el mismo actor. Esta convención elimina ese riesgo mientras
el catálogo formal no exista.

---

# 2. Dos conceptos distintos que NO hay que confundir

- **Rol-actor** (este documento): quién EJECUTÓ un evento que quedó en la auditoría.
  Es lo que se cataloga acá. Vive en `HitoTiempo.actor_rol`.
- **Rol-permiso** (RBAC de cada módulo): quién puede ver qué pantalla y hacer qué en
  la interfaz. Es específico de cada módulo, NO se cataloga acá.

Un mismo sector puede tener varios roles-permiso pero figurar como un solo rol-actor.
Ejemplo: Admisión tiene pantallas distintas en Cordis y en Atlas (rol-permiso
distinto por módulo), pero es el mismo `ADMISION` como actor en la auditoría.

---

# 3. Formato del código (alineado a FHIR)

FHIR modela los roles de participante como CodeableConcept: un código que siempre
sabe de qué sistema de terminología viene (SNOMED u otro), más un texto legible.
Adoptamos esa FORMA de pensar sin implementar CodeableConcept completo todavía.

**Formato:** `sistema:CODIGO`
- `sistema` = de qué catálogo viene el código.
  - `snomed:` para roles clínicos con mapeo a SNOMED CT (cuando exista).
  - `zenoxia:` para roles operativos/logísticos que SNOMED no cubre con esta
    granularidad (propios del ecosistema).
- `CODIGO` = MAYÚSCULAS, sin tildes, en español, guión bajo como separador
  (consistente con los enums del core: CAMA_INTERNACION, FUERA_DE_SERVICIO).

Ejemplos: `zenoxia:HOTELERIA`, `zenoxia:CENTRAL_TRASLADOS`, `snomed:MEDICO`.

Cuando se cree la tabla catálogo formal (ver sección 6), este `sistema:CODIGO`
se promueve a un CodeableConcept completo (system + code + display) sin romper los
datos ya escritos.

---

# 4. Catálogo de roles-actor

## Clínicos
| Código | Quién es | Nota |
|---|---|---|
| `MEDICO` | Médico, cualquier servicio | Uno solo: el contexto (UCI, IG, guardia) sale de la ubicación, no del rol |
| `ENFERMERIA` | Enfermero/a asistencial | Uno solo, mismo criterio de contexto |
| `COORD_ENFERMERIA` | Coordinación/jefatura de enfermería | Decide pases; distinto del enfermero de a pie que ejecuta |
| `CIRCULANTE` | Enfermero circulante de quirófano | Código propio: documenta tiempos quirúrgicos y checklist OMS (hitos que ningún otro enfermero genera) |

## Operativos / logísticos
| Código | Quién es | Módulo principal |
|---|---|---|
| `ADMISION` | Equipo de admisión (todos los recepcionistas: urgencias, internaciones). Orquesta camas | Cordis, Atlas |
| `CAMILLERO` | Central de Traslado de Pacientes | Cordis, Kairos, Atlas |
| `HOTELERIA` | Hotelería: rastrea altas probables, valida documentación, dispara check-out físico | Atlas |
| `LIMPIEZA` | Ejecuta limpieza terminal; el supervisor aprueba el retorno a disponible | Atlas |
| `MANTENIMIENTO` | Reporta incidencias, bloquea/desbloquea camas por reparación | Atlas |

Nota sobre Hotelería/Limpieza: hoy ambas viven en Atlas porque hacen el recambio de
cama (parte del ciclo de la cama). Cuando exista el módulo de Servicios al Paciente
(ver visión), se reevaluará el reparto. Por ahora no se parten: en la operación real
Hotelería predomina sobre Limpieza, así que partirlas ahora inventaría una frontera
que la operación no tiene.

## Registrados pero fuera de uso actual
| Código | Quién es | Estado |
|---|---|---|
| `COCINA` | Cocina / dietas / requerimientos especiales | Reservado para el futuro módulo de Servicios al Paciente. NO se usa en Atlas v1 |

---

# 5. Qué NO es un rol-actor (no va en este catálogo)

- `ADMIN` (administrador del sistema) — rol-permiso: configura la app, no ejecuta
  hitos clínicos. Vive en el RBAC de cada módulo.
- `DIRECTOR` — rol-permiso: consume tableros/analytics, no ejecuta hitos. RBAC.
- **Paciente** — NO es un actor: es el sujeto de atención. Es el `Patient` del core,
  no un rol que ejecuta eventos.

---

# 6. Estado y evolución (deuda registrada)

- **Hoy:** `actor_rol` es string libre en `HitoTiempo`. Los módulos escriben
  `sistema:CODIGO` siguiendo esta convención.
- **Futuro:** cuando haya 2-3 módulos en producción y el uso real de roles esté
  mapeado con evidencia, se crea una tabla catálogo en el core (patrón CodeableConcept:
  system + code + display) y `actor_rol` migra de string a referencia. NO se hace
  ahora: crear la tabla con un solo módulo a la vista sería diseñar adivinando.
- Esta convención es el puente: garantiza que cuando llegue la tabla, los datos ya
  están escritos de forma consistente y la migración es directa.
