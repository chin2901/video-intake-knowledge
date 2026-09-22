from pathlib import Path

f = Path("packages/video_intake_core/cli/__init__.py")
c = f.read_text()

c = c.replace("PolicyResolver = _get_policies()", "from video_intake_core.policies import PolicyResolver")
c = c.replace("StorageManagerClass = _get_storage()", "from video_intake_core.storage import StorageManager as StorageManagerClass")
c = c.replace("ArtifactManagerClass, _ = _get_artifacts()", "from video_intake_core.artifacts import ArtifactManager as ArtifactManagerClass")
c = c.replace("MemoryProvider, LocalSQLiteMemoryProvider, _ = _get_memory()", "from video_intake_core.memory import MemoryProvider, LocalSQLiteMemoryProvider")

f.write_text(c)
