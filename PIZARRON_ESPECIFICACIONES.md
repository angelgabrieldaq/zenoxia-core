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
* `HitoTiempo`: Tabla Append-Only e inmutable. Registra cada transición de estado almacenando `producto_origen` (Cordis/Kairos/Gia), `hito_codigo`, `actor_id`, `actor_rol`, `actor_nombre` y `meta# Zenoxia Core · Especificaciones del Pizarrón de Diseño
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
* `HitoTiempo`: Tabla Append-Only e inmutable. Registra cada transición de estado almacenando `producto_origen` (Cordis/Kairos/Gia), `hito_codigo`, `actor_id`, `actor_rol`, `actor_nombre` y `metadata_evento` (JSONB para cargas útiles FHIR o signos vitales).data_evento` (JSONB para cargas útiles FHIR o signos vitales).