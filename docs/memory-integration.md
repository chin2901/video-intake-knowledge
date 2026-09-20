# Integración de memoria con video-intake-knowledge

## Resumen

El sistema incluye una interfaz abstracta `MemoryProvider` que permite
almacenar y consultar conocimiento extraído de vídeos. El núcleo no está
acoplado a un proveedor único: se puede usar cualquiera que implemente la
interfaz.

## Interfaz MemoryProvider

```python
class MemoryProvider(ABC):
    @abstractmethod
    def list_memory_banks() -> list[MemoryBank]:
        """Lista los bancos de memoria disponibles."""

    @abstractmethod
    def describe_memory_bank(bank_id: str) -> MemoryBank:
        """Describe un banco de memoria: nombre, descripción, ámbito,
        política de retención, permisos, número de entradas."""

    @abstractmethod
    def add_entry(
        bank_id: str,
        content: str,
        source: str,
        extracted_at: str,
        content_type: str,
        confidence: float,
        tags: list[str],
        metadata: dict,
    ) -> str:
        """Añade una entrada a un banco de memoria."""

    @abstractmethod
    def create_memory_bank(
        name: str,
        description: str,
        scope: str,
        retention_days: int,
        sensitivity: str,
    ) -> str:
        """Crea un nuevo banco de memoria."""

    @abstractmethod
    def search(query: str, bank_id: str = None) -> list[MemoryEntry]:
        """Busca en la memoria por texto."""

    @abstractmethod
    def health_check() -> MemoryHealth:
        """Verifica el estado del proveedor de memoria."""
```

## Implementación local (por defecto)

`LocalSQLiteMemoryProvider` almacena en SQLite (`video_intake_memory.db` por
defecto). Es la implementación por defecto cuando no hay integración con un
agente anfitrión.

## Integración con Hermes

Cuando el adaptador de Hermes detecta que el host expone memoria programática,
se usa el `HermesMemoryProvider` que integra con la API de memoria de Hermes.

El flujo es:
1. Al elegir "banco de memoria existente", se listan los bancos reales
   disponibles en Hermes.
2. Se muestra para cada banco: nombre, descripción, ámbito, política de
   retención, permisos, número de entradas.
3. Se pide selección explícita del banco.
4. Se añade la entrada con contenido estructurado, fuente, timestamps,
   artefactos asociados, confianza, etiquetas, fecha y política de actualización.

## Cuando el host no tiene memoria programática

Si el agente anfitrión no expone memoria programática (AGY, OpenCode, Claude
Code, Codex, genérico), el sistema:

1. Ofrece exportar un paquete Markdown/JSON con el contenido extraído para
   importación manual.
2. No simula una integración inexistente.
3. Permite guardar los artefactos localmente con su política de retención.

## Flujo de confirmación

Las reglas de memoria son estrictas:

1. **Nunca escribir en memoria sin selección explícita.** Después de la
   extracción, el usuario elige qué hacer. La opción de memoria nunca es la
   predeterminada.
2. **Nunca crear un banco sin confirmación.** Se solicita nombre, descripción,
   ámbito, retención y sensibilidad, y se muestra la configuración resultante
   antes de crear.
3. **Listar bancos antes de añadir.** Si el usuario elige "banco existente",
   se listan y se pide selección.

## Exportación manual

Cuando no hay integración de memoria, el sistema exporta un paquete con:

```
memory_export_<job_id>_<timestamp>.zip
├── metadata.json          # Metadatos del job
├── transcript.md          # Transcripción formateada
├── audio_context.md       # Contexto de audio
├── visual_context.md     # Contexto visual
├── extracted_knowledge.md # Conocimiento extraído
└── manifest.json         # Referencias a artefactos
```

Este paquete puede ser importado manualmente al sistema de memoria del usuario.

## Retención y limpieza

Cada banco de memoria tiene una política de retención configurable. El sistema
puede limpiar automáticamente entradas antiguas según la política definida.
