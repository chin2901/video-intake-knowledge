"""
Tests para el orquestador y la ejecución de comandos CLI de video-intake-knowledge.
Verifica que cada comando ejecute realmente y devuelva 0 sin fallos de nombres o tipos.
"""

import argparse
from pathlib import Path

import pytest
from video_intake_core.acquisition import detect_video_sources
from video_intake_core.cli import (
    cmd_artifacts,
    cmd_cancel,
    cmd_cleanup,
    cmd_config_validate,
    cmd_doctor,
    cmd_export,
    cmd_extract,
    cmd_inspect,
    cmd_models_list,
    cmd_models_verify,
    cmd_self_test,
    cmd_status,
)
from video_intake_core.cli.memory import show_memory
from video_intake_core.cli.proposals import show_proposals
from video_intake_core.orchestrator import (
    check_and_extract,
    generate_asset_scaffold,
    parse_extraction_choices,
    route_extracted_knowledge,
)


@pytest.fixture
def sample_video_path() -> str:
    p = Path(__file__).parent.parent / "fixtures" / "video" / "sample.mp4"
    assert p.exists()
    return str(p.resolve())


def test_parse_extraction_choices():
    assert parse_extraction_choices("1, 3") == {1, 3}
    assert parse_extraction_choices("6") == {1, 2, 3, 4, 5}
    assert parse_extraction_choices("todo") == {1, 2, 3, 4, 5}
    assert parse_extraction_choices("all") == {1, 2, 3, 4, 5}
    assert parse_extraction_choices("2 4 5") == {2, 4, 5}
    assert parse_extraction_choices("") == {1, 2, 3, 4, 5}


def test_detect_video_sources_relative_and_direct(sample_video_path: str):
    # Detección por ruta directa
    sources = detect_video_sources(sample_video_path)
    assert len(sources) >= 1
    assert sources[0].source_type == "local"
    assert Path(sources[0].resolved_path).exists()

    # Detección por URL
    yt_sources = detect_video_sources("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    assert len(yt_sources) == 1
    assert yt_sources[0].source_type == "youtube"


def test_check_and_extract_local_video(sample_video_path: str, tmp_path: Path):
    sources = [{
        "type": "local",
        "original_input": sample_video_path,
        "resolved_url": sample_video_path,
        "platform": "local",
        "title": "sample",
        "is_local": True,
    }]
    # Operaciones: 1 (video), 2 (audio), 5 (visual)
    artifacts = check_and_extract(sources, {1, 2, 5}, tmp_path)
    assert artifacts["job_id"].startswith("job_")
    assert Path(artifacts["job_dir"]).exists()
    assert "video" in artifacts["files"]
    assert "audio" in artifacts["files"]
    assert Path(artifacts["files"]["audio"]).exists()
    assert (Path(artifacts["job_dir"]) / "artifacts_manifest.json").exists()


def test_route_extracted_knowledge_all_options(sample_video_path: str, tmp_path: Path):
    sources = [{
        "type": "local",
        "resolved_url": sample_video_path,
        "platform": "local",
        "title": "sample_route",
        "is_local": True,
    }]
    artifacts = check_and_extract(sources, {1, 2}, tmp_path)

    # Opción 1: Mensaje a la sesión
    r1 = route_extracted_knowledge(artifacts, choice="1", interactive=False)
    assert r1["status"] == "completed"

    # Opción 2: Contexto de sesión
    r2 = route_extracted_knowledge(artifacts, choice="2", interactive=False)
    assert "context" in r2

    # Opción 3: Banco de memoria existente (o inicial)
    r3 = route_extracted_knowledge(artifacts, choice="3", interactive=False)
    assert "bank" in r3
    assert Path(r3["db_path"]).exists()

    # Opción 4: Nuevo banco de memoria
    r4 = route_extracted_knowledge(artifacts, choice="4", interactive=False, extra_input="test_bank_custom")
    assert r4["bank"] == "test_bank_custom"
    assert Path(r4["db_path"]).exists()

    # Opción 5: Propuesta de activos y generación
    r5_skill = route_extracted_knowledge(artifacts, choice="5", interactive=False, extra_input="1")
    assert "created_files" in r5_skill
    for f in r5_skill["created_files"]:
        assert Path(f).exists()

    r5_tool = route_extracted_knowledge(artifacts, choice="5", interactive=False, extra_input="2")
    assert "created_files" in r5_tool
    for f in r5_tool["created_files"]:
        assert Path(f).exists()

    r5_agent = route_extracted_knowledge(artifacts, choice="5", interactive=False, extra_input="3")
    assert "created_files" in r5_agent
    for f in r5_agent["created_files"]:
        assert Path(f).exists()


def test_asset_scaffolding(tmp_path: Path):
    artifacts = {
        "job_id": "test_job_123",
        "sources": [{"title": "Video de Prueba", "resolved_url": "file:///tmp/vid.mp4"}],
        "summary": "Resumen de prueba para generación de activos.",
        "audio_context": "Contexto de audio extraído.",
        "visual_context": "Contexto visual con diagramas.",
    }

    # Scaffold Skill
    skill_files = generate_asset_scaffold("SKILL", "skill-prueba", artifacts, output_base=tmp_path)
    assert len(skill_files) == 1
    assert skill_files[0].name == "SKILL.md"
    assert "Video de Prueba" in skill_files[0].read_text(encoding="utf-8")

    # Scaffold Tool
    tool_files = generate_asset_scaffold("TOOL", "tool_prueba", artifacts, output_base=tmp_path)
    assert len(tool_files) == 1
    assert tool_files[0].name == "tool.py"

    # Scaffold Agent
    agent_files = generate_asset_scaffold("AGENTE", "agente-prueba", artifacts, output_base=tmp_path)
    assert len(agent_files) == 2


def test_cli_doctor_execution():
    args = argparse.Namespace(json=False)
    ret = cmd_doctor(args)
    assert ret == 0


def test_cli_self_test_execution():
    args = argparse.Namespace()
    ret = cmd_self_test(args)
    assert ret == 0


def test_cli_inspect_execution(sample_video_path: str):
    # Texto
    args = argparse.Namespace(source=sample_video_path, json=False)
    ret = cmd_inspect(args)
    assert ret == 0

    # JSON
    args_json = argparse.Namespace(source=sample_video_path, json=True)
    ret_json = cmd_inspect(args_json)
    assert ret_json == 0


def test_cli_extract_and_followup(sample_video_path: str, tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    args = argparse.Namespace(
        source=sample_video_path,
        file=[],
        select="1,2",
        output=str(tmp_path / "artifacts"),
        config=None,
        json=True,
    )
    ret = cmd_extract(args)
    assert ret == 0

    # Obtener el job_id de los artefactos generados
    job_dirs = list((tmp_path / "artifacts").glob("job_*"))
    assert len(job_dirs) >= 1
    job_id = job_dirs[0].name

    # status
    args_status = argparse.Namespace(job_id=job_id, json=False)
    ret_status = cmd_status(args_status)
    assert ret_status == 0

    # artifacts
    args_artifacts = argparse.Namespace(job_id=job_id, json=False)
    ret_artifacts = cmd_artifacts(args_artifacts)
    assert ret_artifacts == 0

    # export
    args_export = argparse.Namespace(job_id=job_id, format="markdown", output=str(tmp_path / "exports"))
    ret_export = cmd_export(args_export)
    assert ret_export == 0
    assert (tmp_path / "exports" / "export.md").exists()

    # export json
    args_export_json = argparse.Namespace(job_id=job_id, format="json", output=str(tmp_path / "exports"))
    ret_export_json = cmd_export(args_export_json)
    assert ret_export_json == 0
    assert (tmp_path / "exports" / "export.json").exists()

    # cleanup dry run
    args_cleanup = argparse.Namespace(
        max_age_days=90,
        dry_run=True,
        config=None,
    )
    ret_cleanup = cmd_cleanup(args_cleanup)
    assert ret_cleanup == 0

    # cancel
    args_cancel = argparse.Namespace(job_id=job_id)
    ret_cancel = cmd_cancel(args_cancel)
    assert ret_cancel in {0, 1}


def test_cli_models_execution():
    args_list = argparse.Namespace(json=False)
    assert cmd_models_list(args_list) == 0

    args_verify = argparse.Namespace(json=False)
    assert cmd_models_verify(args_verify) == 0


def test_cli_config_validate_execution():
    args_val = argparse.Namespace(config=None, json=False)
    assert cmd_config_validate(args_val) == 0


def test_cli_proposals_execution(sample_video_path: str, tmp_path: Path):
    args_empty = argparse.Namespace(job_id="nonexistent_job_123", scaffold=None, output=str(tmp_path))
    assert show_proposals(args_empty) == 1

    # Extraer primero para tener un job válido
    sources = [{
        "type": "local",
        "resolved_url": sample_video_path,
        "platform": "local",
        "title": "sample_prop",
        "is_local": True,
    }]
    artifacts = check_and_extract(sources, {1}, tmp_path)
    job_id = artifacts["job_id"]

    # Ejecutar proposals con job_id
    args_job = argparse.Namespace(job_id=job_id, scaffold=None, output=str(tmp_path / "gen"), artifacts_dir=str(tmp_path))
    assert show_proposals(args_job) == 0

    # Ejecutar proposals con scaffold
    args_scaffold = argparse.Namespace(job_id=job_id, scaffold="skill", output=str(tmp_path / "gen"), artifacts_dir=str(tmp_path))
    assert show_proposals(args_scaffold) == 0
    assert (tmp_path / "gen" / "skill-sample-prop" / "SKILL.md").exists()


def test_cli_memory_execution(tmp_path: Path):
    db_file = str(tmp_path / "test_cli_memory.db")
    args_stats = argparse.Namespace(db_path=db_file, list=False, search=None, clear=False, stats=True, yes=False, limit=20, offset=0)
    assert show_memory(args_stats) == 0

    args_list = argparse.Namespace(db_path=db_file, list=True, search=None, clear=False, stats=False, yes=False, limit=20, offset=0)
    assert show_memory(args_list) == 0

    args_search = argparse.Namespace(db_path=db_file, list=False, search="prueba", clear=False, stats=False, yes=False, limit=20, offset=0)
    assert show_memory(args_search) == 0

    args_clear = argparse.Namespace(db_path=db_file, list=False, search=None, clear=True, stats=False, yes=True, limit=20, offset=0)
    assert show_memory(args_clear) == 0
