# Zenoxia Core · Especificaciones del Pizarrón de Diseño
## Contexto de Arquitectura y Reglas de Negocio para Automatización (Mayo 2026)

Este documento unifica las definiciones de negocio, el viaje del paciente (Patient Journey) y las decisiones de arquitectura acordadas entre el Líder Clínico y el Arquitecto de Software Full Stack para el desarrollo de la suite transaccional de Zenoxia.

---

## 1. ESTRATEGIA COMERCIAL Y MODULARIDAD
* **Independencia absoluta:** `Cordis` (Guardia/Logística), `Kairos` (Quirófanos) y `Gia` (Obstetricia SaMD) son productos independientes con mercados y PMF separados. No deben depender entre sí para ser instalados.
* **Solución Arquitectónica:** Este repositorio (`zenoxia-core`) actúa como un paquete de cimientos compartidos. Mapea las entidades bajo el estándar HL7 FHIR para que todos los productos hablen el mismo idioma de datos si coexisten, pero permitiendo el despliegue autónomo de cualquiera de ellos.

---

## 2. EL VIAJE DEL PACIENTE (PATIENT JOURNEY) Y MÁQUINA DE ESTADOS
El flujo transaccional de la guardia de urgencias evita el sesgo de invisibilidad médica. Desde el ingreso, el paciente es visible en una pantalla general unificada.

### 2.1 Sub-zonas de Ubicación Física (Location Matrix)
El paciente se desplaza de forma automática por las siguientes áreas:
1. **INGRESO_RECEPCION:** Asignación automática a `SALA_ESPERA_PRE_TRIAGE`. Visible para todo el equipo médico para monitorear acumulación de pacientes sin clasificar.
2. **TRIAGE_INICIADO:** El enfermero toma signos vitales y el paciente pasa a estar `EN_TRIAGE`.
3. **TRIAGE_COMPLETADO:** Se define la urgencia (N1-N5), los tags de datos clínicos importantes de baja prioridad (ej. antecedentes críticos) y el servicio de derivación. El paciente pasa automáticamente a `SALA_ESPERA_EVALUADO`.

### 2.2 Lista de Espera Visual y Catálogo de Especialidades Extensible
* **Filtros Médicos:** Los médicos visualizan el tablero general con opciones de filtrado por servicio troncal: `CLIN` (Clínica Médica), `PEDI` (Pediatría), `TRAU` (Traumatología), `CIRU` (Cirugía General - Puente con Kairos), y `GINO` (Ginecología y Obstetricia - Puente con Gia).
* **Extensibilidad:** Las especialidades NO están hardcodeadas en las consultas de código. Se manejan mediante la tabla maestra `MedicalService` para permitir al administrador añadir o modificar servicios en el futuro (ej. Interconsultas de Cardiología) sin romper el backend.

---

## 3. LOGÍSTICA DE TRASLADOS Y FLEXIBILIDAD EN EL TERRENO (5 ESCENARIOS)
Los traslados físicos utilizan una lógica de origen y destino dinámicos (`origen_recurso_id` -> `destino_recurso_id`) apuntando a la tabla unificada de recursos físicos para cubrir las siguientes situaciones del terreno:

* **Escenario 1 (Autónomo):** El paciente se mueve por sus propios medios al servicio de imágenes. El sistema registra `equipo_requerido = 'CAMINA_SOLO'` y completa el hito de transporte sin saturar la cola de los camilleros.
* **Escenario 2 (Observación Transitoria en Consultorio):** Ante colapso de camas, el médico decide dejar al paciente acostado evolucionando en el propio consultorio de atención. El hito `OBSERVACION_TRANSITORIA_INICIADA` bloquea el recurso físico en la base de datos cambiando su caché a `OCUPADO` y deshabilitando el llamador de ese consultorio en la UI médica.
* **Escenario 3 (Traslado Asistido a Observación):** Se solicita un camillero para mover al paciente en silla/camilla desde el consultorio hacia un Box de Observación real o mantenerlo en silla asistido por familiares.
* **Escenario 4 (Retorno Inteligente Post-Estudio - RN-12):** Cuando el técnico de imágenes marca "Estudio Completado" en su Worklist, el motor de Cordis evalúa el episodio: si enfermería le asignó un Box físico libre en ese transcurso, el traslado de retorno automático se genera con destino a ese Box; si no, retorna a la Sala de Espera de Evaluados.
* **Escenario 5 (Egreso de Guardia a Áreas Críticas/Piso):** Conexión futura con gestión de camas. Al confirmar la recepción en UTI/UCO o Piso, el traslado se completa y el motor cierra automáticamente el episodio clínico de la guardia (`EGRESO_FISICO`).

---

## 4. LA LÓGICA DEL LLAMADOR DINÁMICO
* **Dilema Operativo Solucionado:** Coexistencia de hospitales estructurados (consultorios fijos) y hospitales dinámicos (médicos rotativos según disponibilidad).
* **Solución Técnica:** El consultorio físico (`LocationResource`) es una propiedad mutable que se asocia a la **Sesión Activa del Médico** al loguearse. Al presionar "Llamar", el endpoint hereda ese ID de consultorio para estamparlo en el hito `MEDICO_LLAMADO` y emitir el WebSocket a la pantalla de la sala de espera. El médico mantiene la flexibilidad de cambiar su consultorio desde la UI sobre la marcha si requiere mudarse.

---

## 5. ESTRUCTURA RECOMENDADA DE MODELOS EN EL CORE
Los modelos implementados en `database/models.py` deben responder a la siguiente estructura declarativa en SQLAlchemy 2.0 Async:
* `Patient`: Datos de identidad inmutables, DNI string indexado con restricción regex de 7-8 dígitos.
* `MedicalService`: Catálogo de especialidades (id, nombre, tipo_flujo, activo).
* `LocationResource`: Tabla unificada de infraestructura (boxes, camas, quirófanos, consultorios) mapeada bajo el concepto FHIR Location, con `estado_cache` para el ciclo de estados (Libre, Ocupado, Limpieza).
* `Episodio`: Transacción de la visita actual que conecta al Paciente con el `MedicalService` derivado.
* `Traslado`: Entidad dinámica de logística (origen, destino, equipo, prioridad, estado de máquina de estados de camilleros, timestamps de auditoría RTT/SLA).
* `HitoTiempo`: Tabla Append-Only e inmutable. Registra cada transición de estado almacenando `producto_origen` (Cordis/Kairos/Gia), `hito_codigo`, `actor_id`, `actor_rol`, `actor_nombre` y `metadata_evento` (JSONB para cargas útiles FHIR o signos vitales).

---

## 6. MÓDULO GIA - PROTOCOLO HIPERTENSIVO FASGO 2025

### 6.1 Fundamento Clínico y Cambio de Paradigma
El Consenso FASGO 2025 (Federación Argentina de Sociedades de Ginecología y Obstetricia) sobre Trastornos Hipertensivos en el Embarazo establece una ruptura conceptual con la clasificación anterior:

> **CONCEPTO ELIMINADO:** Las categorías "preeclampsia leve" y "preeclampsia severa" quedan abolidas del lenguaje clínico y del sistema. Toda preeclampsia se considera una condición potencialmente severa y se evalúa en función de la presencia o ausencia de signos de compromiso de órgano blanco.

### 6.2 Clasificación Vigente (enum `ClasificacionHTAFASGO2025`)
El sistema implementa cinco categorías diagnósticas excluyentes:

| Código | Descripción clínica |
|---|---|
| `HIPERTENSION_GESTACIONAL` | HTA de novo ≥ 20 semanas sin proteinuria ni signos de severidad |
| `PREECLAMPSIA` | HTA + proteinuria confirmada por uRPC (± signos de severidad) |
| `ECLAMPSIA` | Convulsiones en contexto de preeclampsia |
| `HIPERTENSION_CRONICA` | HTA preexistente o diagnosticada < 20 semanas |
| `HIPERTENSION_CRONICA_CON_PE_SOBREAGREGADA` | HTA crónica con aparición de proteinuria o signos de severidad |

### 6.3 Checklist de Signos de Severidad / Compromiso de Órgano Blanco
El modelo `EpisodioObstetrico` implementa campos booleanos independientes por sistema orgánico. La presencia de **al menos uno** activa la alerta clínica de severidad en la UI de Gia.

#### 6.3.1 Compromiso Neurológico
| Campo | Signo clínico |
|---|---|
| `sev_eclampsia` | Convulsión tónico-clónica generalizada |
| `sev_cefalea_persistente` | Cefalea intensa que no cede con analgésicos |
| `sev_escotomas` | Alteraciones visuales (escotomas, fosfenos, visión borrosa) |

#### 6.3.2 Compromiso Hepático
| Campo | Signo clínico | Umbral |
|---|---|---|
| `sev_epigastralgia` | Epigastralgia / dolor en hipocondrio derecho | — |
| `sev_got_elevada` | GOT (AST) elevada | > 2× valor normal (> 70 U/L) |
| `sev_gpt_elevada` | GPT (ALT) elevada | > 2× valor normal (> 56 U/L) |

Los campos `sev_got_valor_ul` y `sev_gpt_valor_ul` almacenan el valor numérico real para trazabilidad y auditoría.

#### 6.3.3 Compromiso Hematológico
| Campo | Signo clínico | Umbral |
|---|---|---|
| `sev_trombocitopenia` | Trombocitopenia / Plaquetopenia | < 100.000/mm³ |

El campo `sev_plaquetas_valor_mm3` almacena el recuento absoluto.

### 6.4 Estándar Confirmatorio de Proteinuria: Razón Proteínas/Creatinina Urinaria (uRPC)

**Decisión arquitectónica:** El sistema elimina la dependencia de tiras reactivas cualitativas (`1+`, `2+`, `3+`) como criterio diagnóstico principal.

| Campo | Tipo | Descripción |
|---|---|---|
| `urpc_valor_mg_mmol` | `Numeric(7,2)` | Valor cuantitativo de la muestra (mg/mmol) |
| `urpc_confirmatorio` | `Boolean` | `True` si `urpc_valor_mg_mmol >= 30` |
| `urpc_fecha_muestra` | `DateTime` | Timestamp de la toma de muestra |

**Punto de corte diagnóstico FASGO 2025:** `uRPC ≥ 30 mg/mmol` confirma proteinuria significativa.

El flag `urpc_confirmatorio` es calculado y persistido por la capa de servicio en el momento del registro, garantizando consistencia en consultas de alto volumen sin recalcular en cada lectura.

### 6.5 Modelo de Datos: `EpisodioObstetrico`
Entidad satélite con relación `one-to-one` con `Episodio` (FK con `unique=True`). Solo se crea cuando el episodio pertenece al módulo Gia (`producto_origen = 'Gia'`). Permite despliegue autónomo de Gia sin modificar las tablas troncales de Cordis o Kairos.

### 6.6 Hitos de Auditoría Específicos de Gia (tabla `HitoTiempo`)
Los siguientes códigos de hito (`hito_codigo`) están reservados para el módulo Gia:

* `GIA_CLASIFICACION_HTA_REGISTRADA`
* `GIA_SIGNO_SEVERIDAD_ACTIVADO`
* `GIA_URPC_CONFIRMATORIO_POSITIVO`
* `GIA_ECLAMPSIA_DECLARADA`
* `GIA_PROTOCOLO_MAGNESIO_INICIADO`
* `GIA_FINALIZACION_EMBARAZO_INDICADA`
