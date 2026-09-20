# =============================================================================
# ADR 002 — Arquitectura de adaptadores: núcleo + plugins de host
# =============================================================================

**Estado:** Aceptado | **Fecha:** 2026-09-20

## Decisión

El proyecto separa claramente entre:

- `packages/video_intake_core/` — núcleo portable, sin dependencia de Hermes ni de ningún host.
- `adapters/hermes/` — integración nativa con Hermes Agent (plugin + skill + tools + hooks + install/uninstall).
- `adapters/<host>/` — adaptadores para otros hosts: scripts de instalación, SKILL.md portable, flujo manual.
- `skill/SKILL.md` — skill portable de referencia para cualquier entorno compatible con SKILL.md.

## Justificación

1. **Reutilización del núcleo.** Si Hermes cambia su API o desaparece, el núcleo sigue funcionando. Si aparece un nuevo host, se escribe un adaptador sin tocar el núcleo.

2. **Hermes es prioritario, no exclusivo.** La integración con Hermes es la más profunda, pero no es la única vía de uso.

3. **Declaración honesta de capacidades.** Cada adaptador declara explícitamente qué soporta y qué no. No se afirma que un host sin hooks tiene hooks.

4. **Skill portable como puente.** `skill/SKILL.md` es la referencia común que cualquier entorno compatible puede usar.

## Consecuencias

- Mantener múltiples adaptadores es trabajo adicional. Se empieza con Hermes (nativo) y los demás como adaptadores ligeros.
- El núcleo no importa nada de Hermes. La integración se hace en el adaptador.

## Revisión

Revisar al añadir o retirar un host soportado, o cuando la API de Hermes cambie de forma rompedora.

---

# ADR 003 — Política de modelos: prioridad local, externos con aprobación
# =============================================================================

**Estado:** Aceptado | **Fecha:** 2026-09-20

## Decisión

La política de modelos sigue una jerarquía de preferencia:

1. **Estrategias deterministas.** Subtítulos originales, OCR, análisis de escenas con FFmpeg+OpenCV+PySceneDetect — sin modelos de lenguaje.
2. **Modelos locales gratuitos.** faster-whisper (medium), whisper.cpp, Tesseract para OCR.
3. **Modelos locales configurados por el usuario.** El usuario instala explícitamente los modelos que quiere usar.
4. **Modelos externos con aprobación.** Solo si la política lo permite y el usuario aprueba explícitamente cada uso de un modelo de pago o SaaS.

## Justificación

- **Coste.** Los modelos externos tienen coste por token. No se debe usar un modelo externo para algo que FFmpeg o OCR pueden hacer.
- **Privacidad.** Una transcripción puede contener información confidencial. No enviarla a un modelo externo sin autorización.
- **Robustez.** Si el servicio externo falla, se cae a la estrategia local. Si no hay modelo local, se reporta la limitación.
- **Control del usuario.** El usuario decide qué modelos instalar y qué nivel de aprobación requerir.

## Consecuencias

- La configuración incluye `models.policy`, `models.allow_external_providers`, `models.require_explicit_approval_for_paid`, `models.configured_providers`.
- El comando `video-intake models list/install/verify/remove` permite gestionar modelos locales sin tocar el código.
- Si un modelo externo es necesario, se registra en el manifest: modelo, proveedor, prompt versionado, coste estimado y motivo del fallback.

## Revisión

Revisar al añadir nuevos motores de transcripción/visual o cuando cambie la política de costes de los proveedores.

---

# ADR 004 — Privacidad y retención: datos como temporales por defecto
# =============================================================================

**Estado:** Aceptado | **Fecha:** 2026-09-20

## Decisión

- Los artefactos se almacenan en `artifacts/<job-id>/` con política de retención configurable (`config.storage.artifact_retention_days`, por defecto 90 días).
- La limpieza se ejecuta cuando el espacio supera `config.storage.max_storage_gb`.
- La memoria requiere confirmación explícita del usuario antes de crear un banco o añadir entradas.

## Justificación

- Los artefactos son voluminosos (transcripciones, frames, OCR, logs pueden ser decenas de MB).
- La memoria es un compromiso a largo plazo. No se debe hacer sin autorización.
- El usuario debe controlar qué contenido preservar.

## Consecuencias

- `video-intake cleanup` permite limpiar artefactos antiguos.
- Tras cada extracción, el usuario elige qué hacer con los resultados.
- Nunca se escribe en memoria sin selección explícita.

## Revisión

Revisar cuando cambie el modelo de memoria de Hermes o cuando se añadan políticas más granulares.

---

# ADR 005 — Seguridad frente a prompt injection
# =============================================================================

**Estado:** Aceptado | **Fecha:** 2026-09-20

## Decisión

Todo el contenido extraído se trata como **DATOS NO CONFIABLES**. Se sanitiza antes de usar y nunca se inyecta directamente como instrucciones al modelo.

Estrategias:
1. **Escapado estructurado.** Los textos se envuelven en bloques etiquetados.
2. **Detección de patrones peligrosos.** Se marcan en los logs las inyecciones comunes.
3. **Configuración `security.prompt_injection_protection`.** Activatable/desactivatable.
4. **Reporte explícito de incertidumbre.** Cuando no se puede interpretar sin riesgo, se reporta.

## Justificación

Un atacante puede incrustar instrucciones en un vídeo. Si el sistema trata la transcripción como confiable, el agente puede ser manipulado.

## Consecuencias

- Todos los módulos de extracción devuelven contenido marcado como datos.
- El módulo de contexto añade disclaimers cuando presenta contenido al modelo.
- Los análisis de build proposal nunca ejecutan contenido sin validación humana.

## Revisión

Revisar cuando aparezcan nuevas técnicas de prompt injection o cuando la API de los modelos provea mecanismos nativos de prevención.

---

# ADR 006 — Compatibilidad multi-host: núcleo + capas de adaptación
# =============================================================================

**Estado:** Aceptado | **Fecha:** 2026-09-20

## Decisión

Cada adaptador de host declara honestamente qué capacidades soporta, qué está degradado y cómo usar el fallback.

## Justificación

No todos los agentes tienen hooks, tools, memoria o jobs asíncronos. El proyecto debe funcionar en todos, declarando lo que cada uno puede y no puede hacer.

## Consecuencias

- `docs/portability.md` contiene la matriz de compatibilidad.
- Cada adaptador tiene su propio `README.md` con limitaciones.

## Revisión

Revisar al añadir o retirar un host soportado.

---

# ADR 007 — Memoria y confirmaciones explícitas
# =============================================================================

**Estado:** Aceptado | **Fecha:** 2026-09-20

## Decisión

El sistema nunca escribe en memoria sin confirmación explícita del usuario. Al elegir "añadir a memoria" o "crear banco nuevo":

1. Lista bancos existentes con nombre, descripción, ámbito, retención, permisos y número de entradas.
2. Pide selección explícita.
3. Para crear banco nuevo, pide nombre, descripción, ámbito, retención y sensibilidad, y muestra configuración antes de crear.
4. Solo crea tras confirmación.

## Justificación

La memoria es un compromiso a largo plazo. No debe crearse sin autorización.

## Consecuencias

- El flujo post-extracción siempre pregunta qué hacer con los resultados.
- La opción de memoria nunca es la predeterminada.

## Revisión

Revisar cuando la API de memoria de Hermes añada capacidades de almacenamiento automático o cuando el usuario prefiera un modo más automatizado.

---

# ADR 008 — Por qué una skill no basta sin plugin/hook en Hermes
# =============================================================================

**Estado:** Aceptado | **Fecha:** 2026-09-20

## Decisión

En Hermes, una `SKILL.md` portable es insuficiente para la integración nativa completa. Se requiere también un plugin con tools registradas, hooks de detección de mensajes y, cuando esté disponible, integración con memoria del host.

## Justificación

1. **Detección automática.** Un plugin con hook de `message.processed` detecta una URL o adjunto de vídeo antes de que el modelo responda, e inicia la interacción guiada.
2. **Estado por sesión.** El plugin mantiene estado por `session_id` y evita preguntar dos veces por el mismo vídeo.
3. **Tools nativas.** El plugin registra tools invocables por el modelo o el usuario en cualquier momento.
4. **Memoria del host.** El plugin puede integrarse nativamente con la memoria de Hermes.
5. **Degradación controlada.** Si Hermes no expone hooks o memoria en una versión dada, el plugin fallback a skills + CLI manual y marca la limitación con precisión.

## Consecuencias

- `adapters/hermes/plugin.yaml` registra el plugin.
- `adapters/hermes/hooks/` contiene los hooks de detección.
- `adapters/hermes/tools/` contiene las tools registradas.
- `skill/SKILL.md` es el fallback portable.

## Revisión

Revisar si Hermes cambia su modelo de plugins y hooks de forma que haga este enfoque obsoleto.

---

*Fin de los ADR iniciales. Se añadirán más ADRs según surjan decisiones arquitectónicas relevantes.*
