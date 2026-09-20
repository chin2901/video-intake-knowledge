# =============================================================================
# pull_request_template.md — Plantilla de pull request para video-intake-knowledge
# =============================================================================

## Resumen

<!-- Describe brevemente qué hace este PR y por qué es necesario. -->

## Tipo de cambio

<!-- Marca las opciones aplicables con [x] -->

- [ ] 🐛 Bug fix (corrección de un error)
- [ ] ✨ Nueva funcionalidad
- [ ] 💥 Breaking change (cambio incompatimible con versiones anteriores)
- [ ] 📝 Mejora de documentación
- [ ] 🧹 Refactorización (sin cambios funcionales)
- [ ] ✅ Añadir pruebas
- [ ] 🔒 Mejora de seguridad
- [ ] ⚡ Mejora de rendimiento
- [ ] 🔧 Cambio de configuración o dependencias

## Descripción detallada

<!-- Explica los cambios en detalle. -->

## Pruebas ejecutadas

<!-- Describe las pruebas que ejecutaste para verificar los cambios. -->

- [ ] `video-intake doctor` — Verifica el entorno
- [ ] `video-intake self-test` — Pruebas de auto-diagnóstico
- [ ] `pytest tests/unit/` — Pruebas unitarias
- [ ] `pytest tests/contract/` — Pruebas de contrato
- [ ] `pytest tests/integration/` — Pruebas de integración
- [ ] `pytest tests/e2e/` — Pruebas end-to-end
- [ ] `pytest tests/security/` — Pruebas de seguridad
- [ ] Testing manual con vídeo de prueba (describir)

### Resultado de pruebas

```
<!-- Pega aquí el output de las pruebas si es relevante -->
```

## Checklist

<!-- Marca las opciones aplicables con [x] -->

- [ ] El código sigue las convenciones de estilo del proyecto
- [ ] He realizado una revisión de mi propio código
- [ ] He comentado secciones complejas del código
- [ ] He actualizado la documentación correspondiente
- [ ] No se han introducido secretos o credenciales en el código
- [ ] He considerado el impacto en la seguridad (SSRF, prompt injection, etc.)
- [ ] Los cambios son backward-compatible o he actualizado la documentación de breaking changes
- [ ] He actualizado los esquemas JSON si los contratos de datos han cambiado

## breaking changes (si aplican)

<!-- Si este PR incluye breaking changes, describe los impactos y cómo migrar. -->

## Screenshots o evidencias (si aplican)

<!-- Si el cambio es visual o puede ser demostrado, añade capturas o evidencias. -->

## Referencias

<!-- Enlaces a issues, discusiones, documentación relevante, etc. -->

- Issue: #
- Documentación:
- ADR relevante:
