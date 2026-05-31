# Zenoxia — Visión del Ecosistema
## Documento maestro · fuente de verdad del proyecto

Define qué es Zenoxia, qué es el core, los módulos que lo componen, el principio
que gobierna qué vive dónde, y el roadmap. Todo lo demás (modelos, módulos,
prototipos) cuelga de este documento.

---

# 1. Qué es Zenoxia

Un ecosistema de software clínico **interoperable y modular**. Cada módulo:
- **Funciona solo** — tiene su propio mercado, su propio product-market fit, se
  vende y despliega de forma autónoma.
- **Se potencia con los otros** — cuando coexisten, comparten datos a través del
  core y resuelven juntos problemas que ninguno resuelve por separado.

Esta es la tesis central del producto: no es un monolito hospitalario, son piezas
independientes que suman cuando están juntas.

---

# 2. Qué es zenoxia-core (y qué NO es)

`zenoxia-core` es el **vocabulario común e interoperable** del ecosistema: las
entidades que más de un módulo necesita, mapeadas a HL7 FHIR para que todos hablen
el mismo idioma de datos.

## Modelo federado: el core sincroniza, no es una dependencia obligatoria
> **Cada módulo funciona solo, con su propia base de datos y su propia
> representación local de lo que necesita. El core es el PUNTO DE ENCUENTRO Y
> SINCRONIZACIÓN entre módulos cuando coexisten — no una dependencia que cada
> módulo necesite para arrancar.**

Por qué: nadie compra el ecosistema completo de entrada. La primera venta es un
módulo suelto a una institución que ya tiene su propio HIS y su mundo. Si un módulo
no pudiera vivir sin el core pegado a su base, no sería vendible solo — y "cada
módulo funciona solo" sería falso. Por eso el ecosistema es **federado**:

- Cada módulo tiene base propia y representación local de las entidades que usa
  (su propia noción de cama, de paciente/internación, etc.).
- Cuando un módulo corre solo, funciona con su representación local. No necesita
  el core.
- Cuando varios módulos coexisten, el core es la capa que los mantiene en acuerdo:
  cada módulo sincroniza su representación local con la entidad compartida del core.
- El core sigue siendo la fuente de verdad *compartida* cuando hay varios módulos;
  pero deja de ser un requisito de arranque de cada módulo por separado.

Esto es la versión arquitectónica del mismo principio que ya rige a nivel dato (ej.
Atlas funciona sin HIS): los módulos se paran solos y se enriquecen al conectarse.

## Principio de oro: compartido vs. específico de módulo
> **El core contiene SOLO lo que es genuinamente compartido entre módulos.
> Lo específico de un módulo vive en ese módulo, nunca en el core.**

Regla práctica: si solo lo usa UN módulo, NO va en el core.

Por qué importa: cuando lógica específica de un módulo se filtra al core, lo
contamina y obliga a desarmarlo después. (Caso real: la clasificación obstétrica
FASGO y los umbrales hepáticos terminaron en el core central siendo lógica de un
solo módulo — por eso hoy estorban.) El core debe envejecer bien; eso exige
disciplina sobre qué entra.

El modelo federado NO contradice el principio de oro: el core sigue siendo el dueño
del *vocabulario compartido* (qué es un Patient, qué es un LocationResource). Lo que
cambia es que un módulo puede tener una *representación local* de esas entidades para
funcionar solo, que sincroniza con el core cuando coexisten. La definición canónica
es del core; la copia operativa local es del módulo.

## Qué SÍ es del core (vocabulario común compartido)
- `Patient` — identidad del paciente (definición canónica compartida).
- `LocationResource` — infraestructura física unificada (camas, quirófanos, boxes,
  consultorios) bajo FHIR Location, con estado operativo.
- `Episodio` — la visita/transacción que conecta paciente con servicio.
- `Traslado` — logística de movimiento físico entre recursos.
- `HitoTiempo` — auditoría append-only inmutable de cada transición de estado.
- `MedicalService` — catálogo extensible de especialidades.

## Qué NO es del core (vive en su módulo)
- Estados de máquina específicos de un flujo (triage de guardia, preingreso QX).
- Lógica clínica de una especialidad (clasificaciones, umbrales, protocolos).
- Reglas de negocio que solo un módulo aplica (ventana 48-72hs de Kairos, etc.).
- La representación local que cada módulo mantiene para funcionar autónomo (se
  sincroniza con el core, no la define el core).

---

# 3. Los módulos

| Módulo | Dominio | Estado |
|---|---|---|
| **Cordis** | Guardia / urgencias / logística de traslados | Activo — modelado en core |
| **Kairos** | Quirófanos / trazabilidad quirúrgica | Activo — prototipo UI maduro, modelo de datos pendiente |
| **Camas** | Gestión de camas / disponibilidad / asignación | A diseñar — próximo foco |
| **ICU** | Monitoreo de paciente en terapia intensiva | Futuro — no construir aún |
| **Gia** | Obstetricia (SaMD, protocolo FASGO) | **En revisión — probable baja** |

## Cordis — Guardia
El flujo transaccional de la guardia: ingreso, triage N1-N5, sala de espera,
llamador dinámico, traslados (5 escenarios). Es el módulo más modelado hoy en el
core. El estado genérico del episodio vive en el core como `EstadoEncounter`
(4 valores FHIR: ACTIVO/EN_ESPERA/COMPLETADO/CANCELADO). La máquina de estados
fina de guardia (`EstadoEpisodio`, 12 estados) ya fue movida fuera del core en
Fase 1 — vive en `database/_candidatos_a_mover.py` pendiente de pasar al repo
de Cordis.

## Kairos — Quirófanos
Trazabilidad, coordinación y documentación quirúrgica. Tiene un prototipo de UI
maduro (11 pantallas) y un contrato de arquitectura propio ya escrito (preingreso
del paciente, ventana 48-72hs, empadronado/no empadronado, máquina de estados del
paciente). Ese dominio es ESPECÍFICO de Kairos: vive en Kairos, no en el core.
El core solo le da Patient, Location (el quirófano, la cama de destino), Episodio,
HitoTiempo.

## Camas — Gestión de camas (próximo foco)
El recurso compartido que hoy genera fricción en los otros dos módulos:
- En Kairos: cirugías suspendidas por "sin cama UTI disponible".
- En Cordis: egreso de guardia a UTI/UCO/Piso (Escenario 5 del pizarrón).
La cama es disputada por guardia Y quirófano. Un módulo que gestione disponibilidad,
reserva y liberación de camas —consultable por ambos— es la prueba viva de la tesis
del ecosistema: resuelve un problema que ningún módulo resuelve solo.
Cimiento ya presente: `LocationResource` con tipos CAMA_INTERNACION/UTI/UCO y
`estado_cache`. Falta la lógica de asignación/reserva/liberación como flujo propio.

## ICU — Monitoreo (futuro, influye el diseño hoy)
Monitoreo de paciente en terapia intensiva: series temporales de signos vitales,
escritura de alta frecuencia, alertas. NO se construye ahora. Pero se nombra en el
roadmap para que las decisiones de hoy no le cierren la puerta — ej.: que una cama
UTI pueda colgar monitoreo después, que HitoTiempo/metadata soporte payloads de
signos vitales. Influye el diseño; no consume esfuerzo todavía.

## Gia — Obstetricia (en revisión)
Módulo obstétrico con protocolo FASGO 2025. **Decisión en revisión: probable baja**,
posiblemente reemplazado en foco por el módulo de Camas. Hasta confirmar:
- No se construye nada nuevo sobre Gia.
- El módulo de Camas se diseña como pieza INDEPENDIENTE, no "encima de Gia" — si
  Gia finalmente se queda, conviven; si sale, no dejó deuda técnica.
- `EpisodioObstetrico` y la clasificación FASGO en el core quedan marcados como
  candidatos a salir (son lógica de un solo módulo — violan el principio de oro).

---

# 4. Roadmap

Ordenado por dependencia. Cada fase cierra y se valida antes de la siguiente.

**Fase 0 — Visión y principios** (este documento). Fija qué es el ecosistema, el
principio compartido/específico, los módulos y el roadmap.

**Fase 1 — Core depurado.** Revisar `models.py` entidad por entidad contra el
principio de oro. Identificar qué es genuinamente compartido y qué es lógica de
módulo infiltrada. Resolver el destino de Gia. Dejar el core limpio y justificado.

**Fase 2 — Módulo de gestión de camas.** Diseñar disponibilidad, reserva y
liberación de camas, articulado con guardia (egreso → cama) y quirófano (reserva
de cama de destino post-op). Es el módulo que prueba la interoperabilidad real.

**Fase 3 — Integración de módulos al core.** Conectar el prototipo Kairos (y
Cordis) al core real, reemplazando los mocks (ej. el mock-core de localStorage de
Kairos pasa a fetch() contra el core). Trabajo de integración; depende de core firme.

**Fase 4 — Monitoreo ICU.** Construir el módulo de terapia intensiva sobre los
cimientos ya preparados para soportarlo.

**Transversal — Prototipo Kairos (UI).** Sigue su propio camino de diseño de
pantallas en paralelo. NO se frena esperando al backend. Su contrato de
arquitectura propio gobierna ese trabajo.

---

# 5. Reglas que no se renegocian

1. Cada módulo debe poder desplegarse y venderse solo — con su propia base y
   representación local, sin depender del core para arrancar (modelo federado).
2. El core solo contiene lo compartido. Lo específico, en su módulo.
3. El core es punto de sincronización entre módulos, no dependencia de arranque.
   Cuando coexisten, cada módulo sincroniza su representación local con el core.
4. Interoperabilidad vía FHIR — los módulos hablan el mismo idioma de datos.
5. HitoTiempo es append-only e inmutable — la auditoría no se reescribe.
6. Las decisiones de diseño no le cierran la puerta a los módulos futuros del roadmap.
