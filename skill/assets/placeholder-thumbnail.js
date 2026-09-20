# =============================================================================
# assets/sample-video-thumbnail.png.js — Placeholder para asset de ejemplo
# =============================================================================
#
# Este archivo es un placeholder para un thumbnail de vídeo de ejemplo.
# En un entorno real, se generaría a partir de un vídeo procesado.
#
# Para generar un thumbnail de ejemplo, usar:
#   ffmpeg -i input.mp4 -vframes 1 -ss 00:00:01 output/thumbnail.png
#
# =============================================================================

const path = require("path");
const fs = require("fs");

// Este script genera un placeholder para un asset de thumbnail
// en caso de que no haya un vídeo de prueba disponible.

const OUTPUT_DIR = path.join(__dirname, "..", "..", "output", "assets");
const THUMBNAIL_PATH = path.join(OUTPUT_DIR, "sample-thumbnail.png");

// Asegurar que el directorio existe
if (!fs.existsSync(OUTPUT_DIR)) {
    fs.mkdirSync(OUTPUT_DIR, { recursive: true });
}

// Generar un placeholder simple (1x1 pixel PNG)
// En un caso real, esto se reemplazaría por un frame real del vídeo
const placeholder = Buffer.from([
    0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A, // PNG signature
    0x00, 0x00, 0x00, 0x0D, 0x49, 0x48, 0x44, 0x52, // IHDR chunk
    0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01,
    0x08, 0x02, 0x00, 0x00, 0x00, 0x90, 0x77, 0x53,
    0xDE, 0x00, 0x00, 0x00, 0x0C, 0x49, 0x44, 0x41, // IDAT chunk
    0x54, 0x08, 0xD7, 0x63, 0xF8, 0xCF, 0xC0, 0x00,
    0x00, 0x00, 0x02, 0x00, 0x01, 0xE2, 0x21, 0xBC,
    0x33, 0x00, 0x00, 0x00, 0x00, 0x49, 0x45, 0x4E, // IEND chunk
    0x44, 0xAE, 0x42, 0x60, 0x82
]);

fs.writeFileSync(THUMBNAIL_PATH, placeholder);

console.log(`✓ Placeholder generado: ${THUMBNAIL_PATH}`);
console.log(`  Tamaño: ${placeholder.length} bytes`);
console.log(`  NOTA: Este es un placeholder. Usar ffmpeg para generar thumbnails reales.`);
