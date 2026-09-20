"""
Context generation module.

Generates structured knowledge documents from video transcripts
and visual content analysis.

Produces:
- Audio context: summary, table of contents, topics, concepts, tools,
  procedures, decisions, requirements, constraints, risks, warnings,
  recommendations, entities, tasks, open questions, quotes, facts/inferences.
- Visual context: diagrams, flows, architectures, interfaces, text extracted,
  visual summary, relationships, uncertainties.
- Extracted knowledge: consolidated document combining both.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from ..schemas import validate_against_schema
from ..utils import generate_id, sanitize_string, now_utc

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Audio context generation
# ---------------------------------------------------------------------------

def generate_audio_context(
    transcript_segments: list[dict[str, Any]],
    full_text: str,
    source_info: Optional[dict[str, Any]] = None,
    video_duration: Optional[float] = None,
) -> dict[str, Any]:
    """Generate structured audio context from transcript.

    Analyzes transcript text using rule-based NLP (no LLM) to extract
    structured knowledge.

    Args:
        transcript_segments: List of transcript segment dicts with
            start, end, text fields.
        full_text: Complete transcript text joined.
        source_info: Optional source metadata (title, uploader, etc.).
        video_duration: Optional video duration in seconds.

    Returns:
        AudioContext dict with all extracted knowledge.
    """
    text = full_text.strip()
    if not text:
        return _empty_audio_context(source_info)

    segments = [s for s in transcript_segments if s.get("text")]
    if not segments:
        segments = [{"start": "00:00:00.000", "end": "00:00:00.000", "text": text}]

    # Extract knowledge
    summary = _extract_summary(text, segments, video_duration)
    chapters = _extract_table_of_contents(segments, video_duration)
    topics = _extract_topics(text, segments)
    concepts = _extract_technical_concepts(text)
    tools = _extract_tools_mentioned(text)
    procedures = _extract_procedures(text, segments)
    decisions = _extract_decisions(text)
    requirements = _extract_requirements(text)
    constraints = _extract_constraints(text)
    risks = _extract_risks(text)
    warnings = _extract_warnings(text)
    recommendations = _extract_recommendations(text)
    entities = _extract_entities(text)
    tasks = _extract_potential_tasks(text, segments)
    open_questions = _extract_open_questions(text)
    quotes = _extract_quotes(segments)
    facts = _extract_facts(text, segments)
    inferences = _extract_inferences(text, segments, facts)

    confidence = _compute_confidence(
        len(segments), len(text), len(topics), len(concepts), len(tools)
    )

    return {
        "generated_at": now_utc().isoformat(),
        "source": source_info,
        "transcript_segments_count": len(segments),
        "transcript_text_length": len(text),
        "video_duration_seconds": video_duration,
        "language": source_info.get("language") if source_info else None,
        "confidence": confidence,
        "executive_summary": summary,
        "table_of_contents": chapters,
        "topics": topics,
        "technical_concepts": concepts,
        "tools_and_technologies": tools,
        "procedures": procedures,
        "decisions": decisions,
        "requirements": requirements,
        "constraints": constraints,
        "risks": risks,
        "warnings": warnings,
        "recommendations": recommendations,
        "entities": entities,
        "potential_tasks": tasks,
        "open_questions": open_questions,
        "quotes": quotes,
        "facts": facts,
        "inferences": inferences,
        "confidence_by_section": _confidence_by_section(
            summary, chapters, topics, concepts, tools,
            procedures, decisions, requirements, constraints,
            risks, warnings, recommendations, entities,
            tasks, open_questions, quotes, facts, inferences,
        ),
        "warnings_flags": _generate_warnings_flags(
            requirements, constraints, risks, warnings, open_questions
        ),
    }


def _empty_audio_context(source_info: Optional[dict[str, Any]]) -> dict[str, Any]:
    return {
        "generated_at": now_utc().isoformat(),
        "source": source_info,
        "transcript_segments_count": 0,
        "transcript_text_length": 0,
        "video_duration_seconds": None,
        "language": None,
        "confidence": 0.0,
        "executive_summary": "No se pudo generar resumen: transcripción vacía o no disponible.",
        "table_of_contents": [],
        "topics": [],
        "technical_concepts": [],
        "tools_and_technologies": [],
        "procedures": [],
        "decisions": [],
        "requirements": [],
        "constraints": [],
        "risks": [],
        "warnings": [],
        "recommendations": [],
        "entities": [],
        "potential_tasks": [],
        "open_questions": [],
        "quotes": [],
        "facts": [],
        "inferences": [],
        "confidence_by_section": {},
        "warnings_flags": {},
    }


def _extract_summary(
    text: str,
    segments: list[dict[str, Any]],
    video_duration: Optional[float],
) -> str:
    """Extract an executive summary from transcript text."""
    if not text:
        return ""

    first_segments = segments[:5] if len(segments) >= 5 else segments
    intro_text = " ".join(s["text"] for s in first_segments if s.get("text"))
    last_segments = segments[-3:] if len(segments) >= 3 else segments
    outro_text = " ".join(s["text"] for s in last_segments if s.get("text"))

    # Build summary from key parts
    parts = []

    # Intro summary
    if len(intro_text) > 50:
        # Take first 2 sentences
        sentences = _split_sentences(intro_text)
        parts.append(" ".join(sentences[:2]))
    else:
        parts.append(intro_text[:200])

    # Middle topics (if any)
    mid_topics = _extract_topics(text, segments)
    if mid_topics:
        topic_str = ", ".join(t["title"] for t in mid_topics[:5])
        parts.append(f"Temas principales: {topic_str}.")

    # Outro if significant
    if len(outro_text) > 50:
        sentences = _split_sentences(outro_text)
        parts.append(" ".join(sentences[-2:]))

    summary = " ".join(parts)
    summary = sanitize_string(summary)
    return summary[:2000] if summary else ""


def _extract_table_of_contents(
    segments: list[dict[str, Any]],
    video_duration: Optional[float],
) -> list[dict[str, Any]]:
    """Generate a temporal index (table of contents) from segments.

    Creates chapters based on semantic shifts in the transcript.
    """
    chapters: list[dict[str, Any]] = []
    if not segments:
        return chapters

    # Group segments into ~5-10 chapters based on time
    duration = video_duration or (
        max(s.get("end_seconds", 0) for s in segments) or 60
    )
    num_chapters = min(max(5, duration // 60), 15)

    # Calculate chapter boundaries based on time
    chapter_length = duration / num_chapters if num_chapters > 0 else duration

    for i in range(num_chapters):
        start_sec = i * chapter_length
        end_sec = (i + 1) * chapter_length

        # Find text for this chapter
        chapter_text = _get_segment_text_for_range(segments, start_sec, end_sec)

        if chapter_text:
            # Generate chapter title from first meaningful sentence
            sentences = _split_sentences(chapter_text)
            title = _generate_chapter_title(sentences[0] if sentences else chapter_text)
            chapters.append({
                "chapter_number": i + 1,
                "start_time": _seconds_to_time(start_sec),
                "end_time": _seconds_to_time(end_sec),
                "start_seconds": start_sec,
                "end_seconds": end_sec,
                "title": title,
                "summary": chapter_text[:300] + ("..." if len(chapter_text) > 300 else ""),
                "key_points": _extract_key_points(chapter_text),
            })

    return chapters


def _get_segment_text_for_range(
    segments: list[dict[str, Any]],
    start_sec: float,
    end_sec: float,
) -> str:
    """Get transcript text for a time range."""
    texts = []
    for seg in segments:
        s = seg.get("start_seconds", 0)
        e = seg.get("end_seconds", 0)
        if s < end_sec and e > start_sec:
            t = seg.get("text", "")
            if t:
                texts.append(t)
    return " ".join(texts)


def _generate_chapter_title(text: str) -> str:
    """Generate a descriptive chapter title from text."""
    text = text.strip()
    if not text:
        return "Capítulo sin título"

    # Take first meaningful sentence
    sentences = _split_sentences(text)
    first = sentences[0] if sentences else text

    # Remove leading filler words
    filler = ("este", "la", "lo", "un", "una", "los", "las", "en", "el", "la",
              "del", "al", "con", "que", "para", "por", "se", "su", "sus")
    words = first.split()
    meaningful = [w for w in words if w.lower().strip(",.;:!?¿¡") not in filler]
    if meaningful:
        first = " ".join(meaningful[:8])

    # Limit length
    title = first[:100]
    if len(title) >= 90:
        title = title[:87] + "..."

    return title.strip()


def _extract_topics(text: str, segments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Extract main topics from transcript text.

    Uses keyword frequency and phrase extraction to identify topics.
    """
    # Clean and tokenize
    words = _extract_words(text)
    if not words:
        return []

    # Remove common stopwords
    stopwords = _get_stopwords()
    filtered = [w for w in words if w.lower() not in stopwords and len(w) > 3]

    # Find frequent bigrams (2-word phrases)
    bigrams: dict[str, int] = {}
    trigrams: dict[str, int] = {}

    for i in range(len(filtered) - 1):
        bg = f"{filtered[i]} {filtered[i+1]}"
        bigrams[bg] = bigrams.get(bg, 0) + 1

    for i in range(len(filtered) - 2):
        tg = f"{filtered[i]} {filtered[i+1]} {filtered[i+2]}"
        trigrams[tg] = trigrams.get(tg, 0) + 1

    # Combine and rank
    all_phrases: dict[str, int] = {}
    for phrase, count in {**bigrams, **trigrams}.items():
        if count >= 2:
            all_phrases[phrase] = count

    # Get top phrases
    sorted_phrases = sorted(all_phrases.items(), key=lambda x: -x[1])[:15]

    topics: list[dict[str, Any]] = []
    seen_titles: set = set()

    for phrase, count in sorted_phrases:
        title = phrase.strip()
        if title and title.lower() not in seen_titles and len(title) > 5:
            seen_titles.add(title.lower())
            # Find timestamps for this topic
            timestamps = _find_phrase_timestamps(phrase, segments)
            topics.append({
                "title": title,
                "relevance": min(count / max(1, len(filtered)), 1.0),
                "mentions": count,
                "timestamps": timestamps,
                "description": f"Mencionado {count} veces en la transcripción.",
            })

    return topics[:10]


def _extract_words(text: str) -> list[str]:
    """Extract alphabetic words from text, lowercased."""
    import re
    words = re.findall(r"[a-zA-ZáéíóúüñÁÉÍÓÚÜÑ]+", text.lower())
    return [w for w in words if len(w) > 2]


def _get_stopwords() -> set[str]:
    """Basic Spanish/English stopwords set."""
    return {
        "el", "la", "los", "las", "de", "del", "al", "en", "un", "una", "unos",
        "unas", "y", "o", "e", "pero", "sin", "para", "por", "con", "sobre",
        "entre", "después", "antes", "durante", "bajo", "según", "que", "se",
        "su", "sus", "este", "esta", "estos", "estas", "aquel", "aquella",
        "es", "son", "era", "eran", "ser", "haber", "ha", "han", "he", "has",
        "se", "le", "les", "te", "me", "nos", "os", "lo", "la", "se", "me",
        "muy", "más", "menos", "tanto", "mucho", "poco", "hasta", "desde",
        "hace", "tener", "tengo", "tiene", "tenemos", "saber", "sé", "sabe",
        "poder", "puedo", "puede", "querer", "quiero", "quiere", "ir", "voy",
        "va", "vamos", "decir", "digo", "dice", "hacer", "hago", "hace",
        "dar", "doy", "da", "ver", "veo", "ve", "poner", "pongo", "pone",
        "pensar", "pienso", "piensa", "volver", "vuelvo", "vuelve",
        "pasar", "paso", "pasa", "llamar", "llamo", "llama",
        "and", "the", "a", "an", "is", "are", "was", "were", "be", "been",
        "being", "have", "has", "had", "do", "does", "did", "will", "would",
        "could", "should", "may", "might", "can", "this", "that", "these",
        "those", "i", "you", "he", "she", "it", "we", "they", "me", "him",
        "her", "us", "them", "my", "your", "his", "its", "our", "their",
        "what", "which", "who", "whom", "when", "where", "why", "how",
        "all", "each", "every", "both", "few", "more", "most", "other",
        "some", "such", "no", "nor", "not", "only", "own", "same", "so",
        "than", "too", "very", "s", "t", "just", "don", "now", "here",
    }


def _find_phrase_timestamps(
    phrase: str, segments: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Find timestamps where a phrase appears in transcript."""
    phrase_lower = phrase.lower()
    timestamps: list[dict[str, Any]] = []

    for seg in segments:
        seg_text = seg.get("text", "").lower()
        if phrase_lower in seg_text:
            timestamps.append({
                "start": seg.get("start", ""),
                "end": seg.get("end", ""),
                "start_seconds": seg.get("start_seconds", 0),
                "end_seconds": seg.get("end_seconds", 0),
            })

    return timestamps[:5]


def _extract_technical_concepts(text: str) -> list[dict[str, Any]]:
    """Extract technical concepts from text using pattern matching."""
    concepts: list[dict[str, Any]] = []
    text_lower = text.lower()
    sentences = _split_sentences(text)

    # Patterns for technical terms
    tech_patterns = [
        (r"\b(api|API)\b", "API"),
        (r"\b(framework|framework)\b", "Framework"),
        (r"\b(library|libraries)\b", "Library"),
        (r"\b(database|base de datos|DB)\b", "Base de datos"),
        (r"\b(server|servidor|backend)\b", "Servidor/Backend"),
        (r"\b(client|cliente|frontend)\b", "Cliente/Frontend"),
        (r"\b(microservice|microservicios)\b", "Microservicios"),
        (r"\b(container|docker|contenedor)\b", "Contenedores"),
        (r"\b(cloud|nube)\b", "Nube/Cloud"),
        (r"\b(ci|cd|continuous integration|continuous deployment)\b", "CI/CD"),
        (r"\b(test|testing|pruebas|test automatizado)\b", "Testing"),
        (r"\b(deployment|despliegue)\b", "Despliegue"),
        (r"\b(monitoring|monitoreo|observabilidad)\b", "Monitoreo"),
        (r"\b(security|seguridad|ciberseguridad)\b", "Seguridad"),
        (r"\b(logger|logging|logs|registro)\b", "Logging"),
        (r"\b(configuration|configuración)\b", "Configuración"),
        (r"\b(algorithm|algoritmo)\b", "Algoritmos"),
        (r"\b(data structure|estructura de datos)\b", "Estructuras de datos"),
        (r"\b(version control|control de versiones|git)\b", "Control de versiones"),
        (r"\b(code| código|código fuente)\b", "Código"),
        (r"\b(repo|repositorio)\b", "Repositorio"),
        (r"\b(package|dependencia)\b", "Paquetes/Dependencias"),
        (r"\b(documentation|documentación)\b", "Documentación"),
        (r"\b(error|bug|excepción)\b", "Error/Bug"),
        (r"\b(performance|rendimiento)\b", "Rendimiento"),
        (r"\b(scalability|escalabilidad)\b", "Escalabilidad"),
        (r"\b(architecture|arquitectura)\b", "Arquitectura"),
        (r"\b(design|diseno|diseño|patrón|patrón de diseño)\b", "Diseño"),
        (r"\b(auth|autenticación|autorización|login)\b", "Autenticación"),
        (r"\b(cache|caché)\b", "Caché"),
        (r"\b(message queue|cola de mensajes|pubsub)\b", "Colas de mensajes"),
        (r"\b(api rest|rest api|restful)\b", "API REST"),
        (r"\b(graphql)\b", "GraphQL"),
        (r"\b(websocket|ws)\b", "WebSockets"),
        (r"\b(serverless)\b", "Serverless"),
        (r"\b(kubernetes|k8s|orquestación)\b", "Orquestación"),
        (r"\b(machine learning|ml|ia|inteligencia artificial)\b", "Machine Learning/IA"),
        (r"\b(big data|datos grandes)\b", "Big Data"),
        (r"\b(analytics|analítica|análisis de datos)\b", "Analítica"),
        (r"\b(mobile|móvil|app móvil)\b", "Apps móviles"),
        (r"\b(web|website|página web)\b", "Web"),
    ]

    found: set[str] = set()
    for pattern, concept_name in tech_patterns:
        if re.search(pattern, text_lower) and concept_name not in found:
            found.add(concept_name)
            # Find mentions
            mentions = [s for s in sentences if re.search(pattern, s.lower())]
            concepts.append({
                "concept": concept_name,
                "mentions": len(mentions),
                "description": _get_first_mention_description(mentions[:3]),
                "context_sentences": mentions[:2],
            })

    return sorted(concepts, key=lambda c: -c["mentions"])


def _get_first_mention_description(sentences: list[str]) -> str:
    """Get description from first mention sentence."""
    if sentences:
        return sentences[0].strip()[:200]
    return ""


def _extract_tools_mentioned(text: str) -> list[dict[str, Any]]:
    """Extract tools, software, and platforms mentioned in text."""
    tools: list[dict[str, Any]] = []
    text_lower = text.lower()
    sentences = _split_sentences(text)

    tool_patterns = [
        (r"\b(python| Python)\b", "Python", "Lenguaje de programación interpretado"),
        (r"\b(java| Java)\b", "Java", "Lenguaje de programación"),
        (r"\b(javascript| JS| JavaScript)\b", "JavaScript", "Lenguaje de programación web"),
        (r"\b(typescript| TS| TypeScript)\b", "TypeScript", "Superset tipado de JavaScript"),
        (r"\b(node\.?js| Node\.?js|nodejs)\b", "Node.js", "Runtime JavaScript"),
        (r"\b(react| React)\b", "React", "Librería UI"),
        (r"\b(vue| Vue)\b", "Vue.js", "Framework UI"),
        (r"\b(angular| Angular)\b", "Angular", "Framework UI"),
        (r"\b(next\.?js| Next\.?js)\b", "Next.js", "Framework React"),
        (r"\b(nest\.?js| Nest\.?js)\b", "NestJS", "Framework Node.js"),
        (r"\b(express| Express|express\.js)\b", "Express", "Framework web Node.js"),
        (r"\b(django| Django)\b", "Django", "Framework Python web"),
        (r"\b(flask| Flask)\b", "Flask", "Framework Python web"),
        (r"\b(fastapi| FastAPI)\b", "FastAPI", "Framework Python web async"),
        (r"\b(spring| Spring)\b", "Spring", "Framework Java"),
        (r"\b(laravel| Laravel)\b", "Laravel", "Framework PHP"),
        (r"\b(rails| Ruby on Rails)\b", "Ruby on Rails", "Framework Ruby"),
        (r"\b(.net| dotnet| .NET)\b", ".NET", "Framework Microsoft"),
        (r"\b(ruby| Ruby)\b", "Ruby", "Lenguaje de programación"),
        (r"\b(go| golang| Go)\b", "Go", "Lenguaje de programación"),
        (r"\b(rust| Rust)\b", "Rust", "Lenguaje de programación"),
        (r"\b(swift| Swift)\b", "Swift", "Lenguaje Apple"),
        (r"\b(kotlin| Kotlin)\b", "Kotlin", "Lenguaje Android/JVM"),
        (r"\b(scala| Scala)\b", "Scala", "Lenguaje JVM"),
        (r"\b(shell| bash| script de shell)\b", "Shell/Bash", "Scripting"),
        (r"\b(sql|database|postgresql|mysql|mariadb|sqlite)\b", "SQL/DB", "Bases de datos"),
        (r"\b(mongodb|mongo|NoSQL|firestore)\b", "MongoDB/NoSQL", "Base de datos NoSQL"),
        (r"\b(redis| memcached)\b", "Redis", "Caché en memoria"),
        (r"\b(elasticsearch|elastic)\b", "Elasticsearch", "Motor de búsqueda"),
        (r"\b(docker|docker-compose|compose)\b", "Docker", "Contenedores"),
        (r"\b(kubernetes|k8s|kubectl)\b", "Kubernetes", "Orquestación de contenedores"),
        (r"\b(terraform| terra)\b", "Terraform", "IaC"),
        (r"\b(aws|amazon web services|amazon)\b", "AWS", "Cloud provider"),
        (r"\b(gcp|google cloud|google cloud platform)\b", "Google Cloud", "Cloud provider"),
        (r"\b(azure| microsoft azure)\b", "Azure", "Cloud provider"),
        (r"\b(nginx|apache|httpd|web server)\b", "Nginx/Apache", "Servidor web"),
        (r"\b(linux| ubuntu| debian| fedora| centos)\b", "Linux", "Sistema operativo"),
        (r"\b(git|github|gitlab|bitbucket)\b", "Git/GitHub", "Control de versiones"),
        (r"\b(jenkins| ci|cd|github actions|gitlab ci)\b", "CI/CD", "Integración continua"),
        (r"\b(postman| insomnia)\b", "Postman/Insomnia", "API client"),
        (r"\b(figma| sketch| adobe xd)\b", "Figma/Sketch", "Diseño UI"),
        (r"\b(vscode| visual studio code|vs code)\b", "VS Code", "Editor de código"),
        (r"\b(intellij| pycharm| eclipse| idea)\b", "IntelliJ/PyCharm", "IDE"),
        (r"\b(docker| kubernetes| helm)\b", "Kubernetes/Helm", "Orquestación"),
        (r"\b(anaconda| conda)\b", "Anaconda/Conda", "Entorno Python"),
        (r"\b(poetry| pip| pipenv)\b", "Poetry/Pip", "Gestión de paquetes Python"),
        (r"\b(docker-compose| compose)\b", "Docker Compose", "Orquestación local Docker"),
        (r"\b(shell| bash| zsh| fish)\b", "Shell", "Terminal"),
        (r"\b(vim| neovim| emacs| nano| sublime)\b", "Editor de texto", "Editor de texto"),
        (r"\b(slack| teams| discord)\b", "Comunicación", "Herramienta de comunicación"),
        (r"\b(jira| trello| asana| linear| notion)\b", "Gestión de proyectos", "Herramienta de gestión"),
        (r"\b(aws |amazon |azure |gcp |google cloud )\b", "Cloud", "Proveedor cloud"),
        (r"\b(pytorch| tensorflow| keras| scikit)\b", "PyTorch/TensorFlow", "Machine Learning"),
        (r"\b(pandas| numpy| matplotlib| seaborn)\b", "Pandas/NumPy", "Análisis de datos Python"),
        (r"\b(docker| container| orchestrated)\b", "Docker", "Contenedores"),
        (r"\b(nginx|apache| caddy)\b", "Nginx/Caddy", "Reverse proxy"),
        (r"\b(traefik| haproxy| envoy)\b", "Traefik/Envoy", "Proxy/Service mesh"),
        (r"\b(letsencrypt| certbot| ssl|tls|https)\b", "TLS/Let's Encrypt", "Certificados SSL"),
        (r"\b(feedback| metric| analytics)\b", "Analytics", "Analítica"),
        (r"\b(robot| automation| automatización)\b", "Automatización", "Automatización"),
        (r"\b(open source| open-source| licencia| MIT| GPL)\b", "Open Source", "Software open source"),
        (r"\b(linux| unix| bsd)\b", "Linux/Unix", "Sistema operativo"),
    ]

    found_tools: set[str] = set()
    for pattern, tool_name, description in tool_patterns:
        if re.search(pattern, text_lower):
            if tool_name not in found_tools:
                found_tools.add(tool_name)
                mentions = [s for s in sentences if re.search(pattern, s.lower())]
                tools.append({
                    "tool": tool_name,
                    "description": description,
                    "category": _categorize_tool(tool_name),
                    "mentions": len(mentions),
                    "context_sentences": mentions[:2],
                })

    return sorted(tools, key=lambda t: -t["mentions"])


def _categorize_tool(tool_name: str) -> str:
    """Categorize a tool by its type."""
    categories = {
        "python": "Lenguaje",
        "java": "Lenguaje",
        "javascript": "Lenguaje",
        "typescript": "Lenguaje",
        "node.js": "Runtime/Framework",
        "react": "UI Framework",
        "vue.js": "UI Framework",
        "angular": "UI Framework",
        "next.js": "Fullstack Framework",
        "nestjs": "Backend Framework",
        "express": "Backend Framework",
        "django": "Backend Framework",
        "flask": "Backend Framework",
        "fastapi": "Backend Framework",
        "spring": "Backend Framework",
        "laravel": "Backend Framework",
        "ruby on rails": "Backend Framework",
        ".net": "Framework",
        "ruby": "Lenguaje",
        "go": "Lenguaje",
        "rust": "Lenguaje",
        "swift": "Lenguaje",
        "kotlin": "Lenguaje",
        "scala": "Lenguaje",
        "sql/database": "Base de datos",
        "mongodb/nosql": "Base de datos",
        "redis": "Caché",
        "elasticsearch": "Búsqueda",
        "docker": "Contenedores",
        "kubernetes": "Orquestación",
        "terraform": "IaC",
        "aws": "Cloud",
        "google cloud": "Cloud",
        "azure": "Cloud",
        "nginx/apache": "Servidor web",
        "linux": "Sistema operativo",
        "git/github": "Control de versiones",
        "ci/cd": "CI/CD",
        "postman/insomnia": "API Client",
        "figma/sketch": "Diseño",
        "vs code": "Editor",
        "intellij/pycharm": "IDE",
        "kubernetes/helm": "Orquestación",
        "anaconda/conda": "Entorno Python",
        "poetry/pip": "Gestión paquetes",
        "shell": "Terminal",
        "comunicación": "Comunicación",
        "gestión de proyectos": "Gestión",
        "cloud": "Cloud",
        "pytorch/tensorflow": "Machine Learning",
        "pandas/numpy": "Análisis de datos",
        "docker": "Contenedores",
        "nginx/caddy": "Proxy",
        "traefik/envoy": "Service Mesh",
        "tls/lets encrypt": "Seguridad",
        "analytics": "Analítica",
        "automatización": "Automatización",
        "open source": "Licencia",
        "linux/unix": "Sistema operativo",
    }
    return categories.get(tool_name, "Herramienta")


def _extract_procedures(text: str, segments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Extract step-by-step procedures from text."""
    procedures: list[dict[str, Any]] = []
    sentences = _split_sentences(text)

    step_patterns = [
        r"\b(paso|pasos|step|steps)\s*\d+[:.]?\s*",
        r"\b(1\.|2\.|3\.|4\.|5\.|6\.|7\.|8\.|9\.)\s*",
        r"\b(primero|primer|primero que|primero:|first)\s*",
        r"\b(segundo|segunda|segundo:|second)\s*",
        r"\b(tercero|tercera|tercer|tercero:|third)\s*",
        r"\b(cuarto|cuarta|cuarto:|fourth)\s*",
        r"\b(quinto|quinta|quinto:|fifth)\s*",
        r"\b(entonces|then|after|after that|next)\s*",
        r"\b(finalmente|finally|en resumen)\s*",
        r"\b(una vez|once|after doing)\s*",
        r"\b(para (instalar|configurar|ejecutar|correr|desplegar|deployar|wituar))\b",
        r"\b(como (instalar|configurar|ejecutar|correr|desplegar|deployar))\b",
        r"\b(cómo (instalar|configurar|ejecutar|correr|desplegar|deployar))\b",
        r"\b(instrucciones|instructions|comandos|commands)\b",
        r"\b(uninstall|desinstalar|remove|quitar)\b",
        r"\b(requirements|requisitos|dependencies|dependencias)\b",
        r"\b(install|instalar| instalación| setup|configuración)\b",
        r"\b(clone|clonar|download|descargar)\b",
        r"\b(run|ejecutar|correr|start|iniciar)\b",
        r"\b(build|compilar|construir)\b",
        r"\b(test|probar|testing)\b",
        r"\b(deploy|desplegar|publish|publicar)\b",
        r"\b(config|configurar|configuration)\b",
        r"\b(credentials|claves|secreto|secrets)\b",
        r"\b(environment|variables de entorno| .env)\b",
    ]

    # Find procedure sections
    current_procedure: list[str] = []
    current_steps: list[dict[str, Any]] = []
    in_procedure = False

    for i, sentence in enumerate(sentences):
        s_lower = sentence.lower()

        is_step = any(re.search(p, s_lower) for p in step_patterns)

        if is_step:
            if current_procedure and not in_procedure:
                # New procedure found
                if current_steps:
                    procedures.append({
                        "title": "Procedimiento",
                        "steps": current_steps,
                        "context_sentences": current_procedure[:5],
                        "estimated_complexity": _estimate_procedure_complexity(current_steps),
                    })
                current_steps = []
                current_procedure = []

            current_procedure.append(sentence)
            in_procedure = True

            # Extract step info
            step_info = {
                "step": len(current_steps) + 1,
                "text": sentence.strip(),
                "index": i,
            }

            # Try to extract command or action
            cmd_match = re.search(r"`([^`]+)`", sentence)
            if cmd_match:
                step_info["command"] = cmd_match.group(1)

            current_steps.append(step_info)
        else:
            if in_procedure and current_steps:
                current_procedure.append(sentence)
            else:
                current_procedure = []

    # Last procedure
    if current_steps:
        procedures.append({
            "title": "Procedimiento",
            "steps": current_steps,
            "context_sentences": current_procedure[:5],
            "estimated_complexity": _estimate_procedure_complexity(current_steps),
        })

    return procedures


def _estimate_procedure_complexity(steps: list[dict[str, Any]]) -> str:
    """Estimate procedure complexity from number of steps and content."""
    num_steps = len(steps)
    has_commands = any("command" in s for s in steps)
    has_config = any("config" in s.get("text", "").lower() for s in steps)

    if num_steps <= 2:
        return "Simple"
    elif num_steps <= 5:
        return "Moderado"
    elif num_steps <= 10:
        return "Complejo"
    else:
        return "Muy complejo"


def _extract_decisions(text: str) -> list[dict[str, Any]]:
    """Extract decisions mentioned in text."""
    decisions: list[dict[str, Any]] = []
    sentences = _split_sentences(text)

    decision_patterns = [
        r"\b(decidimos|decidido|decisión|decision)\b",
        r"\b(elegimos|elegido|elegir|elección|choice)\b",
        r"\b(optamos|opción|optar|option)\b",
        r"\b(elegí|elegiste|elegimos|elegieron)\b",
        r"\b(por eso|por lo tanto|therefore|así que|then)\b",
        r"\b(la solución|la decisión|la elección|the solution|the decision)\b",
        r"\b(hemos| hemos| we have| we chose)\b",
        r"\b(utilizamos|usamos|utilizamos|we use|we used)\b",
        r"\b(implementamos|implementado|we implemented)\b",
        r"\b(escogimos|chosen|we chose)\b",
        r"\b(resultado|result|outcome|conclusión|conclusion)\b",
        r"\b(advantage|ventaja|beneficio|benefit|pros)\b",
        r"\b(desventaja|desadvantage|downside|contras)\b",
        r"\b(comparar|comparison|compare| compared)\b",
        r"\b(alternativa|alternative|alternatives)\b",
        r"\b(porque|because|since|given that)\b",
        r"\b(razón|reasoning|reason| rationale)\b",
    ]

    for i, sentence in enumerate(sentences):
        s_lower = sentence.lower()
        is_decision = any(re.search(p, s_lower) for p in decision_patterns)

        if is_decision:
            decisions.append({
                "text": sentence.strip(),
                "rationale": _extract_rationale(sentences, i),
                "implication": _extract_implication(sentences, i),
                "context_index": i,
            })

    return decisions[:10]


def _extract_rationale(sentences: list[str], index: int) -> str:
    """Extract rationale from surrounding sentences."""
    context = sentences[max(0, index - 2):min(len(sentences), index + 3)]
    rationale_sents = [s for s in context if any(
        re.search(p, s.lower()) for p in [
            r"\b(porque|because|since|given that|due to)\b",
            r"\b(razón|reason|rationale)\b",
            r"\b(por esto|that's why|this is why)\b",
        ]
    )]
    return " ".join(rationale_sents[:2]) if rationale_sents else ""


def _extract_implication(sentences: list[str], index: int) -> str:
    """Extract implication/consequence from following sentences."""
    context = sentences[index:min(len(sentences), index + 5)]
    implication_sents = [s for s in context if any(
        re.search(p, s.lower()) for p in [
            r"\b(por eso|therefore|so|as a result|consequently)\b",
            r"\b(lo que significa|which means|meaning)\b",
            r"\b(impacto|impact|consecuencia|consequence)\b",
        ]
    )]
    return " ".join(implication_sents[:2]) if implication_sents else ""


def _extract_requirements(text: str) -> list[dict[str, Any]]:
    """Extract requirements from text."""
    requirements: list[dict[str, Any]] = []
    sentences = _split_sentences(text)

    req_patterns = [
        r"\b(requiere|requerido|required|need|needs|necesita|necesario)\b",
        r"\b(debe|should|has to|have to|must)\b",
        r"\b(prerequisite|prerequisito|pre-requisite)\b",
        r"\b(dependency|dependencia|dependencies)\b",
        r"\b(requirement|requisito|requirements)\b",
        r"\b(conditional|condición|condicional)\b",
        r"\b(version|versión|v\s*\d)\b",
        r"\b(minimum|mínimo|min|at least|al menos)\b",
        r"\b(hardware|sistema| sistema operativo| os)\b",
        r"\b(license|licencia|licenciamiento)\b",
        r"\b(acceso|access|permission|permiso)\b",
        r"\b(configuración|configuración inicial|setup)\b",
    ]

    for i, sentence in enumerate(sentences):
        s_lower = sentence.lower()
        is_req = any(re.search(p, s_lower) for p in req_patterns)

        if is_req:
            # Extract the requirement type
            req_type = _classify_requirement(s_lower)

            requirements.append({
                "text": sentence.strip(),
                "type": req_type,
                "context_index": i,
                "description": sentence.strip()[:200],
            })

    return requirements[:10]


def _classify_requirement(text: str) -> str:
    """Classify a requirement into a category."""
    text = text.lower()
    if re.search(r"\b(version|versión|v\s*\d)", text):
        return "Versión"
    if re.search(r"\b(hardware|sistema|os|sistema operativo)", text):
        return "Sistema/Hardware"
    if re.search(r"\b(license|licencia)", text):
        return "Licencia"
    if re.search(r"\b(dependency|dependencia)", text):
        return "Dependencia"
    if re.search(r"\b(configuración|setup|config)", text):
        return "Configuración"
    if re.search(r"\b(acceso|permission|permiso| credential)", text):
        return "Acceso/Credenciales"
    if re.search(r"\b(requirement|requisito)", text):
        return "Requisito"
    return "General"


def _extract_constraints(text: str) -> list[dict[str, Any]]:
    """Extract constraints and limitations from text."""
    constraints: list[dict[str, Any]] = []
    sentences = _split_sentences(text)

    constraint_patterns = [
        r"\b(limita|limitado|limitación|limitation|limited)\b",
        r"\b(restric|condición|condicionado|condicionada)\b",
        r"\b(only|solo|solamente| únicamente)\b",
        r"\b(can't|cannot|no puede|no se puede|no admite)\b",
        r"\b(unsupported|no soportado|no compatible)\b",
        r"\b(compatibility|compatibilidad)\b",
        r"\b(maximum|máximo|max|capacity|límite|límite de)\b",
        r"\b(rate limit|límite de requests|peticiones)\b",
        r"\b(timeout|time out|expiración|expira)\b",
        r"\b(requires|requiere|need| precisa)\b",
        r"\b(only works|solo funciona|únicamente funciona)\b",
        r"\b(can only|solo puede| únicamente puede)\b",
        r"\b(must be|debe ser|tiene que ser)\b",
        r"\b(has to be|tiene que estar)\b",
        r"\b(unless| a menos que| salvo que)\b",
        r"\b(if and only if|si y solo si)\b",
        r"\b(significantly| considerablemente| mucho)\b",
        r"\b(slow| lento| performance impact)\b",
        r"\b(overhead| sobrecarga)\b",
        r"\b(complex| complejo| difficulty|dificultad)\b",
        r"\b(cost| costo| precio| cuesta)\b",
        r"\b(scalability limit| limitación de escalabilidad)\b",
        r"\b(deprecated| obsoleto| ya no se usa)\b",
        r"\b(experimental|experimental|en experimentación)\b",
        r"\b(broken| roto| no funciona)\b",
        r"\b(known issue| problema conhecido| bug conocido)\b",
        r"\b(warning| advertencia| note| nota)\b",
        r"\b(single| único| only one| solo uno)\b",
    ]

    for i, sentence in enumerate(sentences):
        s_lower = sentence.lower()
        is_constraint = any(re.search(p, s_lower) for p in constraint_patterns)

        if is_constraint:
            constraints.append({
                "text": sentence.strip(),
                "type": _classify_constraint(s_lower),
                "severity": _classify_constraint_severity(s_lower),
                "context_index": i,
            })

    return constraints[:10]


def _classify_constraint(text: str) -> str:
    """Classify constraint type."""
    text = text.lower()
    if re.search(r"\b(limita|limitación|limitado|max| máximo|límite)", text):
        return "Límite"
    if re.search(r"\b(restric)", text):
        return "Restricción"
    if re.search(r"\b(compatibility|compatibilidad|incompatible)", text):
        return "Compatibilidad"
    if re.search(r"\b(performance|lento|overhead)", text):
        return "Rendimiento"
    if re.search(r"\b(cost|costo|precio)", text):
        return "Costo"
    if re.search(r"\b(deprecated|obsoleto)", text):
        return "Obsolescencia"
    if re.search(r"\b(experimental)", text):
        return "Estabilidad"
    return "General"


def _classify_constraint_severity(text: str) -> str:
    """Classify constraint severity."""
    text = text.lower()
    if re.search(r"\b(can't|cannot|no puede|no se puede|no funciona|broke)", text):
        return "Alto"
    if re.search(r"\b(only|solo|solamente| únicamente| única| max| máximo|límite)", text):
        return "Medio"
    return "Bajo"


def _extract_risks(text: str) -> list[dict[str, Any]]:
    """Extract risks mentioned in text."""
    risks: list[dict[str, Any]] = []
    sentences = _split_sentences(text)

    risk_patterns = [
        r"\b(risk|riesgo| risky|arriesgado)\b",
        r"\b(danger|dangerous|peligro|peligroso)\b",
        r"\b(threat|amenaza)\b",
        r"\b(problem|problema|issue|issue| bug| error)\b",
        r"\b(warning| advertencia| alerta)\b",
        r"\b(failure|fallo|falla|failed|fallo)\b",
        r"\b(vulnerable|vulnerabilidad)\b",
        r"\b(attack|ataque|exploit)\b",
        r"\b(data loss|pérdida de datos|data leakage)\b",
        r"\b(security|seguridad| insecure| inseguro)\b",
        r"\b(downtime| tiempo de inactividad| unavailability)\b",
        r"\b(crash|se cayó| se caugo| se crasheó)\b",
        r"\b(rollback|revertir|reverso)\b",
        r"\b(backup| copia de seguridad| restore| restaurar)\b",
        r"\b(migration| migración|migrar| migrate)\b",
        r"\b(compatibility issue| problema de compatibilidad)\b",
        r"\b(breaking change|cambio rompedor)\b",
        r"\b(upgrade| upgradear| actualizar| update)\b",
        r"\b(deprecated| obsoleto)\b",
        r"\b(experimental|experimental)\b",
        r"\b(unstable| inestable)\b",
        r"\b(untested| no probado)\b",
        r"\b(uncertainty| incertidumbre| unsure| no estoy seguro)\b",
        r"\b(caution| precaución| careful| cuidado)\b",
        r"\b(avoid|evitar| no hacer)\b",
        r"\b(do not|no|prohibido|forbidden)\b",
        r"\b(known issue| problema conocido)\b",
        r"\b(workaround| solución alternativa)\b",
    ]

    for i, sentence in enumerate(sentences):
        s_lower = sentence.lower()
        is_risk = any(re.search(p, s_lower) for p in risk_patterns)

        if is_risk:
            severity = "Medio"
            if re.search(r"\b(danger|peligro|security|ataque|data loss|crash|fallo|failed)", s_lower):
                severity = "Alto"
            elif re.search(r"\b(experimental|untested|uncertainty|caution)", s_lower):
                severity = "Bajo"

            risks.append({
                "text": sentence.strip(),
                "type": _classify_risk(s_lower),
                "severity": severity,
                "context_index": i,
                "mitigation": _extract_mitigation(sentences, i),
            })

    return risks[:10]


def _classify_risk(text: str) -> str:
    """Classify risk type."""
    text = text.lower()
    if re.search(r"\b(security|seguridad|ataque|exploit|vulnerable)", text):
        return "Seguridad"
    if re.search(r"\b(data loss|pérdida| data leakage)", text):
        return "Pérdida de datos"
    if re.search(r"\b(downtime|inactividad|unavailability)", text):
        return "Disponibilidad"
    if re.search(r"\b(compatibility|compatibilidad)", text):
        return "Compatibilidad"
    if re.search(r"\b(migration| migración|migrar)", text):
        return "Migración"
    if re.search(r"\b(performance|lento|overhead)", text):
        return "Rendimiento"
    if re.search(r"\b(rollback| revertir| reverso)", text):
        return "Operacional"
    if re.search(r"\b(bug|error|problema| issue)", text):
        return "Bug/Error"
    if re.search(r"\b(experimental|inestable|no probado)", text):
        return "Estabilidad"
    return "General"


def _extract_mitigation(sentences: list[str], index: int) -> str:
    """Extract potential mitigation from following sentences."""
    context = sentences[index:min(len(sentences), index + 4)]
    mitigation_sents = [s for s in context if any(
        re.search(p, s.lower()) for p in [
            r"\b(backup| copia| restore| restaurar)\b",
            r"\b(workaround| solución alternativa)\b",
            r"\b(avoid|evitar)\b",
            r"\b(test|probar|testing)\b",
            r"\b(monitor|monitoreo)\b",
            r"\b(prepare|preparar)\b",
        ]
    )]
    return " ".join(mitigation_sents[:2]) if mitigation_sents else ""


def _extract_warnings(text: str) -> list[dict[str, Any]]:
    """Extract warnings from text."""
    warnings_list: list[dict[str, Any]] = []
    sentences = _split_sentences(text)

    warning_patterns = [
        r"\b(warning|advertencia| warn| warning)\b",
        r"\b(caution|precaución| careful|cuidado)\b",
        r"\b(note|nota|notice|avisar)\b",
        r"\b(important|importante|critical| crítico)\b",
        r"\b(attention| atención)\b",
        r"\b(remember|recuerda|keep in mind|tener en cuenta)\b",
        r"\b(make sure|asegúrate| ensure|garantizar)\b",
        r"\b(do not|no|never|nunca| avoid|evitar)\b",
        r"\b(stop|detener| halt| parar)\b",
        r"\b(unless| a menos que| salvo que)\b",
        r"\b(only| solo| solamente| únicamente)\b",
        r"\b(may| puede| might| podría)\b",
        r"\b(could|could|podría| podria)\b",
        r"\b(should|should|debería| deberia)\b",
        r"\b(recommended|recomendado| recommendation| recomendación)\b",
        r"\b(advisory| advisory)\b",
        r"\b(declared| declared| declare)\b",
        r"\b(deprecated| deprecated| obsoleto)\b",
        r"\b(breaking| breaking| rompedor)\b",
    ]

    for i, sentence in enumerate(sentences):
        s_lower = sentence.lower()
        is_warning = any(re.search(p, s_lower) for p in warning_patterns)

        if is_warning:
            severity = "Normal"
            if re.search(r"\b(critical| crítico| danger|peligro| security|seguridad)", s_lower):
                severity = "Alto"
            elif re.search(r"\b(note|nota|notice|avisar)", s_lower):
                severity = "Bajo"

            warnings_list.append({
                "text": sentence.strip(),
                "type": _classify_warning_type(s_lower),
                "severity": severity,
                "context_index": i,
            })

    return warnings_list[:10]


def _classify_warning_type(text: str) -> str:
    """Classify warning type."""
    text = text.lower()
    if re.search(r"\b(security|seguridad)", text):
        return "Seguridad"
    if re.search(r"\b(deprecated|obsoleto)", text):
        return "Obsolescencia"
    if re.search(r"\b(compatibility|compatibilidad)", text):
        return "Compatibilidad"
    if re.search(r"\b(performance|rendimiento)", text):
        return "Rendimiento"
    if re.search(r"\b(backup|copia)", text):
        return "Datos"
    if re.search(r"\b(breaking|rompedor)", text):
        return "Cambio rompedor"
    return "General"


def _extract_recommendations(text: str) -> list[dict[str, Any]]:
    """Extract recommendations from text."""
    recommendations: list[dict[str, Any]] = []
    sentences = _split_sentences(text)

    rec_patterns = [
        r"\b(recomiendo|recomendar|recommend| recommendation)\b",
        r"\b(sugiero|sugerir|suggest|suggestion)\b",
        r"\b(te recomiendo| i recommend| we recommend)\b",
        r"\b(la mejor|the best| lo mejor| best)\b",
        r"\b(should|should|debería|deberia| ought to)\b",
        r"\b(good practice|buena practica|best practice|mejor practica)\b",
        r"\b(advisable| aconsejable| recommended| recomendado)\b",
        r"\b(consider|considerar| taking into account| teniendo en cuenta)\b",
        r"\b(idea|nice|buena idea| good idea)\b",
        r"\b(tip| tip| consejo| advice)\b",
        r"\b(use|use| utilizar| usar| employ)\b",
        r"\b(avoid|evitar| stay away|distance)\b",
        r"\b(prefer| preferir| preferably)\b",
        r"\b(alternative| alternativa| instead| en lugar de)\b",
        r"\b(better|mejor| improve| mejorar)\b",
        r"\b(optimize|optimizar|improvement|meglioramento)\b",
        r"\b(follow|follow| seguir|seguir)\b",
        r"\b(according to|según|according)\b",
        r"\b(standard| estándar| norm| norma)\b",
    ]

    for i, sentence in enumerate(sentences):
        s_lower = sentence.lower()
        is_rec = any(re.search(p, s_lower) for p in rec_patterns)

        if is_rec:
            strength = "Sugerencia"
            if re.search(r"\b(should|debería|deberia|need|necesita|must|debe|has to)", s_lower):
                strength = "Recomendación"
            elif re.search(r"\b(good practice|best practice|buena practica|mejor practica)", s_lower):
                strength = "Best Practice"
            elif re.search(r"\b(importante| critical| crítico)", s_lower):
                strength = "Importante"

            recommendations.append({
                "text": sentence.strip(),
                "type": _classify_recommendation_type(s_lower),
                "strength": strength,
                "context_index": i,
            })

    return recommendations[:10]


def _classify_recommendation_type(text: str) -> str:
    """Classify recommendation type."""
    text = text.lower()
    if re.search(r"\b(security|seguridad)", text):
        return "Seguridad"
    if re.search(r"\b(performance|rendimiento|optimize|optimizar)", text):
        return "Rendimiento"
    if re.search(r"\b(test|testing|probar|pruebas)", text):
        return "Testing"
    if re.search(r"\b(design|arquitectura)", text):
        return "Arquitectura"
    if re.search(r"\b(maintain|maintainability|mantener)", text):
        return "Mantenibilidad"
    if re.search(r"\b(deploy|desplegar|release)", text):
        return "Despliegue"
    return "General"


def _extract_entities(text: str) -> list[dict[str, Any]]:
    """Extract named entities from text (people, organizations, products)."""
    entities: list[dict[str, Any]] = []

    # People patterns
    person_patterns = [
        r"\b(profile| perfil| usuario| user| persona| people)\b",
        r"\b(el autor|the author| el creador| the creator| el desarrollador|the developer)\b",
        r"\b(el fundador|the founder| el CEO| the CTO| el ingeniero|the engineer)\b",
        r"\b( nombre| name| llamado| called| conocido| known as)\b",
    ]

    # Organization patterns
    org_patterns = [
        r"\b(company|empresa| organización|organization| startup| startup)\b",
        r"\b(equipo|team| grupo|group| comunidad|community)\b",
        r"\b(empresa|company| brand| marca)\b",
        r"\b(google|microsoft|apple| amazon|aws| meta|facebook| linkedin| twitter| x corp)\b",
        r"\b(tesla|spacex|openai|anthropic|google deepmind)\b",
        r"\b( github|gitlab| bitbucket| docker| kubernetes| redhat| canonical)\b",
        r"\b( verizon| att| comcast| sprint)\b",
        r"\b( bank| banco| financial| fintech)\b",
    ]

    # Product/Project patterns
    product_patterns = [
        r"\b(producto|product| app| aplicación| servicio|service| plataforma|platform| Herramienta| tool)\b",
        r"\b(software| programa| aplicación| app| system| sistema)\b",
        r"\b(website| web| página| site| blog| podcast)\b",
        r"\b(library|librería|package|paquete|framework|framework)\b",
        r"\b(api| servicio| endpoint|cliente| client| SDK)\b",
        r"\b(video| vídeo| canal| channel| serie| series)\b",
    ]

    text_lower = text.lower()

    for pattern in person_patterns:
        for match in re.finditer(pattern, text_lower):
            entity = match.group(0).strip()
            if entity and len(entity) > 4:
                entities.append({
                    "entity": entity,
                    "type": "Persona/Rol",
                    "context": _get_context_sentence(text, match),
                })

    for pattern in org_patterns:
        for match in re.finditer(pattern, text_lower):
            entity = match.group(0).strip()
            if entity and len(entity) > 3:
                entities.append({
                    "entity": entity,
                    "type": "Organización",
                    "context": _get_context_sentence(text, match),
                })

    for pattern in product_patterns:
        for match in re.finditer(pattern, text_lower):
            entity = match.group(0).strip()
            if entity and len(entity) > 3:
                entities.append({
                    "entity": entity,
                    "type": "Producto/Proyecto",
                    "context": _get_context_sentence(text, match),
                })

    # Deduplicate
    seen: set = set()
    unique: list[dict[str, Any]] = []
    for e in entities:
        key = (e["entity"], e["type"])
        if key not in seen:
            seen.add(key)
            unique.append(e)

    return unique[:15]


def _get_context_sentence(text: str, match: Any) -> str:
    """Extract context sentence around a match."""
    start = max(0, match.start() - 100)
    end = min(len(text), match.end() + 100)
    return text[start:end].strip()[:200]


def _extract_potential_tasks(text: str, segments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Extract potential tasks or action items from transcript."""
    tasks: list[dict[str, Any]] = []

    task_patterns = [
        r"\b(tarea|tareas|task|tasks|action item|action items)\b",
        r"\b(hacer|to do|to make|to implement|to build|to create|to develop)\b",
        r"\b(implementar|implement|implement|implement)\b",
        r"\b(crear|create| crear| to create)\b",
        r"\b(desarrollar|develop| develop|to develop)\b",
        r"\b(agregar|add| add|to add|adding)\b",
        r"\b(eliminar|remove|delete|delete|to remove)\b",
        r"\b(actualizar|update| update|to update|updating)\b",
        r"\b(revisar|review| review|to review|reviewing)\b",
        r"\b(probar|test| test|to test|testing)\b",
        r"\b(documentar|document|document|to document)\b",
        r"\b(subir|upload|upload|to upload|uploasing)\b",
        r"\b(publicar|publish| publish|to publish|publishing)\b",
        r"\b(encargar|assign|assign|to assign|assigning)\b",
        r"\b(completar|complete|complete|to complete|completing)\b",
        r"\b(resolver|solve|resolve|to solve|resolving)\b",
        r"\b(fix| solucionar| arreglar|to fix)\b",
        r"\b(mejorar|improve|improve|to improve|improving)\b",
        r"\b(optimizar|optimize|optimize|to optimize)\b",
        r"\b(configure|configurar|configure|to configure)\b",
        r"\b(establecer|set|set|to set|setting)\b",
        r"\b(instalar|install|install|to install|installing)\b",
        r"\b(perl|perl|learn|to learn|learning)\b",
        r"\b(leer|read|read|to read|reading)\b",
        r"\b(escribir|write|write|to write|writing)\b",
        r"\b(ahora| now| next| siguiente| siguiente paso)\b",
        r"\b(pronto|soon| próximamente|upcoming)\b",
        r"\b(próximo|next| upcoming| future)\b",
        r"\b(falta|faltan|missing|lacking)\b",
        r"\b(pendiente| pending| outstanding)\b",
        r"\b(seguir|follow| following|following up)\b",
    ]

    for i, sentence in enumerate(segments):
        if not isinstance(sentence, dict):
            continue
        s_text = sentence.get("text", "")
        if not s_text:
            continue
        s_lower = s_text.lower()

        is_task = any(re.search(p, s_lower) for p in task_patterns)
        if is_task:
            tasks.append({
                "text": s_text,
                "type": _classify_task_type(s_lower),
                "priority": _classify_task_priority(s_lower),
                "timestamp": sentence.get("start", ""),
                "start_seconds": sentence.get("start_seconds", 0),
                "index": i,
            })

    return tasks[:10]


def _classify_task_type(text: str) -> str:
    """Classify task type."""
    text = text.lower()
    if re.search(r"\b(implement|crear|desarrollar|build|develop)", text):
        return "Desarrollo"
    if re.search(r"\b(fix| arreglar| solucionar| resolver)", text):
        return "Corrección"
    if re.search(r"\b(test|probar|testing)", text):
        return "Testing"
    if re.search(r"\b(document|documentar| documentation)", text):
        return "Documentación"
    if re.search(r"\b(review|revisar| code review)", text):
        return "Revisión"
    if re.search(r"\b(configure|configurar|setup| configuración)", text):
        return "Configuración"
    if re.search(r"\b(deploy|desplegar|publicar|publish|upload)", text):
        return "Despliegue"
    if re.search(r"\b(learn|leer|estudiar|research|investigar)", text):
        return "Investigación"
    return "General"


def _classify_task_priority(text: str) -> str:
    """Classify task priority."""
    text = text.lower()
    if re.search(r"\b(urgent| urgente| asap| now| hoy| immediately)", text):
        return "Alta"
    if re.search(r"\b(soon| pronto| próximamente| next| siguiente| before)", text):
        return "Media"
    return "Baja"


def _extract_open_questions(text: str) -> list[dict[str, Any]]:
    """Extract open questions from transcript."""
    questions: list[dict[str, Any]] = []
    sentences = _split_sentences(text)

    question_patterns = [
        r"\?\s*$",
        r"\b(cuál|qué|who|what|where|when|how|why|como|por qué|para qué)\b",
        r"\b(quizá| quizás| tal vez| maybe| perhaps)\b",
        r"\b(no sé| I don't know| unsure| uncertain| no estoy seguro)\b",
        r"\b(pensar|think| to think| thinking| wondering)\b",
        r"\b(decidir|decide|to decide|deciding)\b",
        r"\b(ahora| now| what| what's next)\b",
        r"\b(qué hacer| what to do| next step)\b",
        r"\b(habría| there would|would it| would be)\b",
        r"\b(ya|yet| still| todavía)\b",
        r"\b( falta| missing| need| needed)\b",
        r"\b(se puede| can we|is it|is it possible| possible)\b",
        r"\b(qué pasa| what happens| what if)\b",
        r"\b(y qué| and what| and then)\b",
        r"\b(entonces|then|so|so then)\b",
    ]

    for i, sentence in enumerate(sentences):
        s_lower = sentence.lower()
        has_question_mark = sentence.strip().endswith("?")

        is_open = has_question_mark or any(
            re.search(p, s_lower) for p in question_patterns
        )

        if is_open:
            # Determine if genuinely open or rhetorical
            is_rhetorical = any(
                re.search(p, s_lower) for p in [
                    r"\b(por supuesto| of course| obviously| clearly)\b",
                    r"\b(por supuesto que|of course that)\b",
                ]
            )

            if not is_rhetorical:
                questions.append({
                    "text": sentence.strip(),
                    "type": _classify_question_type(s_lower),
                    "confidence_open": _assess_question_openness(s_lower),
                    "context_index": i,
                })

    return questions[:10]


def _classify_question_type(text: str) -> str:
    """Classify question type."""
    text = text.lower()
    if re.search(r"\b(cuál|qué|what|which)", text):
        return "Información"
    if re.search(r"\b(cómo|how|como)", text):
        return "Proceso"
    if re.search(r"\b(por qué|why|por que)", text):
        return "Razón"
    if re.search(r"\b(dónde|where|donde)", text):
        return "Ubicación"
    if re.search(r"\b(cuándo|when|cuando)", text):
        return "Tiempo"
    if re.search(r"\b(quién|who|quien)", text):
        return "Persona"
    return "Aberta"


def _assess_question_openness(text: str) -> float:
    """Assess how open-ended a question is (0-1)."""
    text = text.lower()
    score = 0.5  # Default neutral

    if re.search(r"\b(qué|what| cuál|which)\b", text) and not re.search(r"\b(sí|no|yes|no|verdad|true)", text):
        score = 0.8
    if re.search(r"\b(cómo|how|como|por qué|why)\b", text):
        score = 0.9
    if re.search(r"\b(sí|no|yes|no|verdad|true| falso| false)", text):
        score = 0.3
    if re.search(r"\b(quizá|quizás|tal vez|maybe|perhaps|no sé| I don't know)", text):
        score = 0.9

    return score


def _extract_quotes(
    segments: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Extract significant quotes from transcript segments."""
    quotes: list[dict[str, Any]] = []

    # Filter segments with substantial text
    substantial = [s for s in segments if s.get("text") and len(s["text"]) > 30]

    for seg in substantial:
        text = seg["text"]

        # Quotes that are notable (opinions, key statements, conclusions)
        if any(keyword in text.lower() for keyword in [
            "creo que", "pienso que", "en mi opinión", "a mi parecer",
            "la clave", "lo importante", "el problema", "la solución",
            "lo mejor", "lo peor", " lo difícil", "lo fácil",
            "conclusión", "resumen", "en resumen", "en conclusión",
            "principalmente", "principal", "fundamental",
            "es importante", "es crucial", "es clave",
            "note", "notice", "important", "key", "critical",
            "warning", "warning", "advertencia",
        ]):
            quotes.append({
                "text": text,
                "start": seg.get("start", ""),
                "end": seg.get("end", ""),
                "start_seconds": seg.get("start_seconds", 0),
                "end_seconds": seg.get("end_seconds", 0),
                "type": _classify_quote_type(text),
                "significance": _assess_quote_significance(text),
            })

    # Sort by significance
    quotes.sort(key=lambda q: -q["significance"])

    return quotes[:15]


def _classify_quote_type(text: str) -> str:
    """Classify quote type."""
    text_lower = text.lower()
    if re.search(r"\b(creo que|pienso que|en mi opinión|a mi parecer)", text_lower):
        return "Opinión"
    if re.search(r"\b(la clave|lo importante|el problema|la solución|conclusión|resumen)", text_lower):
        return "Concepto clave"
    if re.search(r"\b(es importante|es crucial|es clave|fundamental|principal)", text_lower):
        return "Enfoque"
    if re.search(r"\b(note|notice|important|key|critical|warning|advertencia)", text_lower):
        return "Advertencia/Nota"
    return "Observación"


def _assess_quote_significance(text: str) -> float:
    """Assess quote significance (0-1)."""
    text_lower = text.lower()
    score = 0.3

    if len(text) > 80:
        score += 0.2
    if re.search(r"\b(creo que|pienso que|en mi opinión|en mi experiencia)", text_lower):
        score += 0.2
    if re.search(r"\b(conclusión|resumen|en resumen|en conclusión|to sum up|in conclusion)", text_lower):
        score += 0.2
    if re.search(r"\b(es importante|es crucial|es fundamental|es clave)", text_lower):
        score += 0.15
    if re.search(r"\b(warning|advertencia|caution|precaución)", text_lower):
        score += 0.15

    return min(score, 1.0)


def _extract_facts(
    text: str,
    segments: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Extract factual statements from text (things that are stated as facts)."""
    facts_list: list[dict[str, Any]] = []
    sentences = _split_sentences(text)

    fact_indicators = [
        r"\bio\b",  # "is" — often factual
        r"\b(son|are)\b",
        r"\b(existe|exists|hay|there is|there are)\b",
        r"\b(tiene|has|have|tiene| tiene)\b",
        r"\b(está| is| está| está)\b",
        r"\b(funciona|works| works| funciona)\b",
        r"\b(da| gives| gives| da| da)\b",
        r"\b(permite|allows|allows| permite| permite)\b",
        r"\b(está disponible|is available| disponible)\b",
        r"\b(está hecho|is made| hecho)\b",
        r"\b(está compuesto|is composed| compuesto)\b",
        r"\blo que|sigue| luego|after|then)\b",
        r"\b(verdad|true|cierto|cierto| cierto| correcto| correct)\b",
        r"\b(está|is| está|está|está|está|está)\b",
        r"\b(se trata|it's about| trata| es| es)\b",
        r"\b(está articulado|is articulated| articulado)\b",
        r"\b(está diseñado|is designed| diseñado)\b",
        r"\b(funciona así| works like this| así| así)\b",
        r"\b(se compone| is composed| compone| compuesto)\b",
        r"\b(está compuesto|is composed| compuesto)\b",
        r"\b(es un|is a|un| es|es|es)\b",
        r"\b(es una|is a|una| es|es|es)\b",
        r"\b(representa|represents| representa)\b",
        r"\b(constituye|constitutes| constituye)\b",
        r"\b(equivale|equals| equivale| equivale)\b",
        r"\b(corresponde|corresponds|corresponde)\b",
        r"\b(significa|means| significa| significa)\b",
        r"\b(definen|define| define| define| define)\b",
        r"\b(se define|is defined| definido)\b",
        r"\b(se caracteriza|is characterized| caracterizado)\b",
        r"\b(está compuesto|is composed| compuesto)\b",
    ]

    for i, sentence in enumerate(sentences):
        s_lower = sentence.lower()

        is_fact = any(re.search(p, s_lower) for p in fact_indicators)
        has_numbers = bool(re.search(r"\d+(\.\d+)?", sentence))

        if is_fact and len(sentence.strip()) > 15:
            facts_list.append({
                "text": sentence.strip(),
                "type": _classify_fact_type(s_lower),
                "has_quantitative_data": has_numbers,
                "confidence": 0.7 if has_numbers else 0.5,
                "context_index": i,
            })

    return facts_list[:20]


def _classify_fact_type(text: str) -> str:
    """Classify fact type."""
    text = text.lower()
    if re.search(r"\b(version|versión|v\s*\d)", text):
        return "Versión"
    if re.search(r"\b( número| cantidad| cantidad|date|fecha| año|año| mes| mes| día|día| tiempo|time| duración| duracion| segundos| seconds| minutos|minutes)", text):
        return "datos numéricos"
    if re.search(r"\b(nombre|name| nombre|el nombre|la URL|la url|el enlace|el link| la dirección| la direccion)", text):
        return "Identificador"
    if re.search(r"\b(descripción| descripción| descripción| descripción| descripción| descripción| lo que hace| lo que es| lo que es| lo que es| lo que es)", text):
        return "Descripción"
    if re.search(r"\b(problema| problema| problema| problema| problema| problema| limitación|limitación| limitación| limitación| limitación| limitación)", text):
        return "Limitación"
    if re.search(r"\b(solución| solución| solución| solución| solución| solución| solución| solución)", text):
        return "Solución"
    return "General"


def _extract_inferences(
    text: str,
    segments: list[dict[str, Any]],
    facts: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Extract inferences (deductions from facts, explicitly labeled as inferences)."""
    inferences_list: list[dict[str, Any]] = []
    sentences = _split_sentences(text)

    inference_indicators = [
        r"\b(por lo tanto|therefore|así que|so|then|consequently)\b",
        r"\b(está claro|it's clear|se ve|se puede ver|se puede observar)\b",
        r"\b(se puede deducir|it can be deduced|se deduce|se puede inferir)\b",
        r"\b(esto implica|this implies|esto significa|this means)\b",
        r"\b(por ende|hence| ergo)\b",
        r"\b(es probable|it's likely| probablemente|probably| lo más seguro|most likely)\b",
        r"\b(se puede suponer|it can be assumed|se puede asumir|we can assume)\b",
        r"\b(lógicamente|logical| lógicamente)\b",
        r"\b(por consiguiente|accordingly)\b",
        r"\b( Tal vez| Perhaps| quizás| maybe)\b",
        r"\b(dado que|given that| ya que|since)\b",
        r"\b(no es casualidad|it's not a coincidence| no es coincidencia)\b",
        r"\b(tiene sentido|it makes sense| tiene sentido| tiene sentido)\b",
        r"\b(se infiere|it is inferred|se puede inferir)\b",
    ]

    for i, sentence in enumerate(sentences):
        s_lower = sentence.lower()

        is_inference = any(re.search(p, s_lower) for p in inference_indicators)

        if is_inference and len(sentence.strip()) > 15:
            # Find supporting facts
            supporting_facts = []
            for fact in facts:
                fact_text = fact.get("text", "").lower()
                sent_words = set(s_lower.split())
                fact_words = set(fact_text.split())
                overlap = len(sent_words & fact_words) / max(len(sent_words), 1)
                if overlap > 0.2:
                    supporting_facts.append(fact)

            inferences_list.append({
                "text": sentence.strip(),
                "type": _classify_inference_type(s_lower),
                "confidence": 0.6 if supporting_facts else 0.4,
                "supporting_facts_count": len(supporting_facts),
                "context_index": i,
                "is_system_inference": True,  # Explicit label
            })

    # Also generate some inferences from facts
    for fact in facts[:5]:
        inferred = _generate_inference_from_fact(fact, text, segments)
        if inferred:
            inferences_list.append(inferred)

    return inferences_list[:15]


def _classify_inference_type(text: str) -> str:
    """Classify inference type."""
    text = text.lower()
    if re.search(r"\b(probable|likely|probablemente|lo más seguro|most likely)", text):
        return "Probabilidad"
    if re.search(r"\b( implica|means|significa|implica)", text):
        return "Implicación"
    if re.search(r"\b(deducir|deducido|inferir|inferred|suponer|assume)", text):
        return "Deducción"
    if re.search(r"\b(alternativa|alternative| en cambio|instead|por otro lado|on the other hand)", text):
        return "Alternativa"
    return "General"


def _generate_inference_from_fact(
    fact: dict[str, Any],
    text: str,
    segments: list[dict[str, Any]],
) -> Optional[dict[str, Any]]:
    """Generate a system inference from a fact."""
    fact_text = fact.get("text", "")
    if len(fact_text) < 30:
        return None

    # Generate inference based on fact type
    fact_type = fact.get("type", "General")
    generated = f"Del hecho de que '{fact_text[:150]}', se puede inferir que..."

    return {
        "text": generated,
        "type": "Generada por sistema",
        "confidence": 0.5,
        "supporting_facts_count": 1,
        "context_index": -1,
        "is_system_inference": True,
        "source_fact": fact_text[:200],
    }


def _compute_confidence(
    num_segments: int,
    text_length: int,
    num_topics: int,
    num_concepts: int,
    num_tools: int,
) -> float:
    """Compute overall confidence score for the audio context."""
    score = 0.0

    # Based on content richness
    if num_segments >= 10:
        score += 0.2
    elif num_segments >= 5:
        score += 0.1
    elif num_segments > 0:
        score += 0.05

    if text_length > 1000:
        score += 0.2
    elif text_length > 500:
        score += 0.1
    elif text_length > 100:
        score += 0.05

    if num_topics >= 3:
        score += 0.15
    elif num_topics > 0:
        score += 0.05

    if num_concepts >= 3:
        score += 0.15
    elif num_concepts > 0:
        score += 0.05

    if num_tools >= 3:
        score += 0.15
    elif num_tools > 0:
        score += 0.05

    # Penalty for very short content
    if text_length < 50:
        score = max(0, score - 0.3)

    return min(score, 1.0)


def _confidence_by_section(
    summary: str,
    chapters: list[dict[str, Any]],
    topics: list[dict[str, Any]],
    concepts: list[dict[str, Any]],
    tools: list[dict[str, Any]],
    procedures: list[dict[str, Any]],
    decisions: list[dict[str, Any]],
    requirements: list[dict[str, Any]],
    constraints: list[dict[str, Any]],
    risks: list[dict[str, Any]],
    warnings: list[dict[str, Any]],
    recommendations: list[dict[str, Any]],
    entities: list[dict[str, Any]],
    tasks: list[dict[str, Any]],
    open_questions: list[dict[str, Any]],
    quotes: list[dict[str, Any]],
    facts: list[dict[str, Any]],
    inferences: list[dict[str, Any]],
) -> dict[str, float]:
    """Compute per-section confidence scores."""
    return {
        "executive_summary": _section_confidence(summary, 0.5),
        "table_of_contents": _section_confidence(chapters, 0.7),
        "topics": _section_confidence(topics, 0.6),
        "technical_concepts": _section_confidence(concepts, 0.7),
        "tools_and_technologies": _section_confidence(tools, 0.8),
        "procedures": _section_confidence(procedures, 0.5),
        "decisions": _section_confidence(decisions, 0.5),
        "requirements": _section_confidence(requirements, 0.6),
        "constraints": _section_confidence(constraints, 0.6),
        "risks": _section_confidence(risks, 0.5),
        "warnings": _section_confidence(warnings, 0.5),
        "recommendations": _section_confidence(recommendations, 0.5),
        "entities": _section_confidence(entities, 0.6),
        "potential_tasks": _section_confidence(tasks, 0.5),
        "open_questions": _section_confidence(open_questions, 0.7),
        "quotes": _section_confidence(quotes, 0.7),
        "facts": _section_confidence(facts, 0.8),
        "inferences": _section_confidence(inferences, 0.4),
    }


def _section_confidence(items: Any, default: float) -> float:
    """Calculate confidence for a section based on richness."""
    if not items:
        return 0.0
    count = len(items) if isinstance(items, (list, tuple)) else 1
    if count == 0:
        return 0.0
    return min(default + (count * 0.02), 1.0)


def _generate_warnings_flags(
    requirements: list[dict[str, Any]],
    constraints: list[dict[str, Any]],
    risks: list[dict[str, Any]],
    warnings: list[dict[str, Any]],
    open_questions: list[dict[str, Any]],
) -> dict[str, Any]:
    """Generate high-level warning flags from extracted knowledge."""
    flags: dict[str, Any] = {
        "has_high_severity_risks": any(
            r.get("severity") == "Alto" for r in risks
        ),
        "has_high_severity_constraints": any(
            c.get("severity") == "Alto" for c in constraints
        ),
        "has_deprecated_items": any(
            "deprecated" in r.get("text", "").lower()
            for r in warnings
        ),
        "has_open_questions": len(open_questions) > 0,
        "has_missing_information": any(
            r.get("type") == "General" for r in requirements
        ),
        "high_risk_count": sum(
            1 for r in risks if r.get("severity") == "Alto"
        ),
        "total_warnings": len(warnings),
        "total_risks": len(risks),
        "total_open_questions": len(open_questions),
    }
    return flags


def _split_sentences(text: str) -> list[str]:
    """Split text into sentences."""
    # Handle multiple sentence separators
    text = text.replace("?", "?§").replace("!", "!§").replace(".", ".§")
    sentences = text.split("§")
    return [s.strip() for s in sentences if s.strip() and len(s.strip()) > 5]


def _seconds_to_time(seconds: float) -> str:
    """Convert seconds float to HH:MM:SS.mmm string."""
    total_ms = int(seconds * 1000)
    ms = total_ms % 1000
    total_secs = total_ms // 1000
    hours = total_secs // 3600
    minutes = (total_secs % 3600) // 60
    secs = total_secs % 60
    return f"{hours:02d}:{minutes:02d}:{secs:02d}.{ms:03d}"


def _extract_key_points(text: str) -> list[str]:
    """Extract key points from text."""
    sentences = _split_sentences(text)
    points: list[str] = []

    for sentence in sentences[:5]:
        if len(sentence) > 15:
            points.append(sentence[:200])

    return points


# ---------------------------------------------------------------------------
# Visual context generation
# ---------------------------------------------------------------------------

def generate_visual_context(
    video_info: dict[str, Any],
    keyframes_metadata: list[dict[str, Any]],
    ocr_results: list[dict[str, Any]],
    scene_changes: list[dict[str, Any]],
    extracted_frames: list[dict[str, Any]],
) -> dict[str, Any]:
    """Generate structured visual context from video analysis.

    Args:
        video_info: Video metadata (duration, resolution, format, etc.).
        keyframes_metadata: Metadata for extracted keyframe images.
        ocr_results: OCR results from frames.
        scene_changes: Scene change detection results.
        extracted_frames: List of extracted frame info.

    Returns:
        VisualContext dict.
    """
    # Analyze scene changes
    scene_summary = _summarize_scenes(scene_changes, video_info)
    diagrams_detected = _detect_diagrams(ocr_results, keyframes_metadata)
    flows_detected = _detect_flows(ocr_results, scene_changes)
    architectures_detected = _detect_architectures(ocr_results, video_info)
    interfaces_catalogued = _catalog_interfaces(ocr_results, keyframes_metadata)
    text_content = _extract_visual_text(ocr_results)
    visual_summary = _generate_visual_summary(
        video_info, scene_changes, keyframes_metadata, ocr_results
    )
    relationships = _detect_relationships(ocr_results, scene_changes)
    uncertainties = _detect_uncertainties(ocr_results, scene_changes, video_info)

    confidence = _compute_visual_confidence(
        len(scene_changes), len(ocr_results), len(keyframes_metadata)
    )

    return {
        "generated_at": now_utc().isoformat(),
        "video_info": video_info,
        "scene_changes_count": len(scene_changes),
        "keyframes_count": len(keyframes_metadata),
        "ocr_blocks_count": sum(len(r.get("bounding_boxes", [])) for r in ocr_results),
        "confidence": confidence,
        "scene_summary": scene_summary,
        "diagrams_detected": diagrams_detected,
        "flows_detected": flows_detected,
        "architectures_detected": architectures_detected,
        "interfaces_catalogued": interfaces_catalogued,
        "visual_text": text_content,
        "visual_summary": visual_summary,
        "relationships_detected": relationships,
        "uncertainties_and_gaps": uncertainties,
        "evidence": _build_evidence_map(
            scene_changes, keyframes_metadata, ocr_results
        ),
    }


def _summarize_scenes(
    scenes: list[dict[str, Any]],
    video_info: dict[str, Any],
) -> dict[str, Any]:
    """Summarize scene changes."""
    duration = video_info.get("duration", 0)
    num_scenes = len(scenes)

    return {
        "total_scenes": num_scenes,
        "average_scene_duration": (
            duration / num_scenes if num_scenes > 0 and duration > 0 else 0
        ),
        "shortest_scene_seconds": (
            min((s.get("end_seconds", 0) - s.get("start_seconds", 0)) for s in scenes)
            if scenes else 0
        ),
        "longest_scene_seconds": (
            max((s.get("end_seconds", 0) - s.get("start_seconds", 0)) for s in scenes)
            if scenes else 0
        ),
    }


def _detect_diagrams(
    ocr_results: list[dict[str, Any]],
    keyframes: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Detect potential diagrams from OCR text and keyframes."""
    diagrams: list[dict[str, Any]] = []

    diagram_indicators = [
        "diagram", " Diagrama", " esquema", "arquitectura", "flujo",
        "flow", "process", "proceso", "sequence", "secuencia",
        "component", "componente", "module", "módulo", "system",
        "sistema", "structure", "estructura", "design", "diseño",
        "drawing", "dibujo", "illustration", "ilustración",
        "graph", "gráfico", "chart", "gráfica", "infographic",
        "plan", "map", "mapa", "network", "red", "connection",
        "conexión", "relationship", "relación", "dependency",
        "dependencia", "inheritance", "herencia", "interface",
        "interfaz", "class", "clase", "object", "objeto",
        "database", "base de datos", "table", "tabla",
        "endpoint", "puerto", "route", "ruta",
    ]

    for result in ocr_results:
        text = result.get("text", "")
        for indicator in diagram_indicators:
            if indicator.lower() in text.lower():
                diagrams.append({
                    "type": "Posible diagrama",
                    "evidence": text[:200],
                    "frame": result.get("frame_path", ""),
                    "confidence": 0.5,
                    "keywords": [indicator],
                })
                break

    return diagrams[:10]


def _detect_flows(
    ocr_results: list[dict[str, Any]],
    scenes: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Detect workflow/process flows from text and scene sequences."""
    flows: list[dict[str, Any]] = []

    flow_indicators = [
        "paso", "step", "flujo", "flow", "proceso", "proceso",
        "workflow", "pipeline", "ciclo", "cycle", "etapa", "stage",
        "fase", "phase", "secuencia", "sequence", "orden", "order",
        "primero", "first", "segundo", "second", "tercero", "third",
        "finalmente", "finally", "inicialmente", "initially",
        "entrada", "input", "salida", "output", "resultado", "result",
        "ejecución", "execution", "procesamiento", "processing",
        "validación", "validation", "transformación", "transformation",
    ]

    for i, result in enumerate(ocr_results):
        text = result.get("text", "")
        for j, indicator in enumerate(flow_indicators):
            if indicator.lower() in text.lower():
                flows.append({
                    "step": j + 1,
                    "evidence": text[:200],
                    "frame_index": i,
                    "confidence": 0.5 if j < 5 else 0.3,
                })
                break

    return flows[:15]


def _detect_architectures(
    ocr_results: list[dict[str, Any]],
    video_info: dict[str, Any],
) -> list[dict[str, Any]]:
    """Detect architectural elements mentioned in text."""
    architectures: list[dict[str, Any]] = []

    arch_patterns = [
        ("microservicios", "Microservicios", "Arquitectura de microservicios"),
        ("monolito", "Monolito", "Arquitectura monolítica"),
        ("servidor", "Servidor", "Arquitectura cliente-servidor"),
        ("clientes", "Clientes", "Arquitectura distribuida"),
        ("API", "APIs", "Arquitectura basada en APIs"),
        ("capas", "Capas", "Arquitectura por capas"),
        ("nubes", "Nube", "Arquitectura cloud/nativa"),
        ("contenedores", "Contenedores", "Arquitectura con contenedores"),
        ("base de datos", "Base de datos", "Arquitectura con persistencia"),
        ("cola", "Cola", "Arquitectura con colas de mensajes"),
        ("eventos", "Eventos", "Arquitectura orientada a eventos"),
        ("streaming", "Streaming", "Arquitectura de streaming"),
        ("serverless", "Serverless", "Arquitectura serverless"),
        ("edge", "Edge", "Arquitectura edge computing"),
        ("cached", "Caché", "Arquitectura con caching"),
        ("CDN", "CDN", "Arquitectura con CDN"),
        ("balance", "Balance", "Arquitectura con balanceo de carga"),
        ("proxy", "Proxy", "Arquitectura con proxy"),
        ("monitor", "Monitor", "Arquitectura con monitoring"),
        ("logs", "Logs", "Arquitectura con logging"),
        ("seguridad", "Seguridad", "Arquitectura segura"),
        ("autenticación", "Autenticación", "Arquitectura con auth"),
        ("autorización", "Autorización", "Arquitectura con authz"),
    ]

    for result in ocr_results:
        text = result.get("text", "")
        for pattern, name, arch_type in arch_patterns:
            if pattern in text.lower():
                architectures.append({
                    "architecture_type": arch_type,
                    "name": name,
                    "evidence": text[:200],
                    "confidence": 0.6,
                    "components_mentioned": _extract_components_from_text(text),
                })
                break

    return architectures[:10]


def _extract_components_from_text(text: str) -> list[str]:
    """Extract component names mentioned in text."""
    words = text.split()
    components: list[str] = []

    tech_words = [
        "API", "Web", "Server", "Client", "Database", "Cache",
        "Queue", "Service", "Module", "Component", "Interface",
        "Controller", "Repository", "Factory", "Singleton",
        "Observer", "Strategy", "Adapter", "Facade", "Decorator",
        "Middleware", "Gateway", "Proxy", "Broker", "Bus",
        "Microservice", "Monolith", "Lambda", "Function",
        "Container", "Pod", "Node", "Cluster", "Volume",
        "Config", "Secret", "Token", "Key", "Certificate",
        "Load Balancer", "DNS", "CDN", "Firewall", "WAF",
        "Route", "Endpoint", "Port", "Socket", "Stream",
        "Topic", "Subscription", "Event", "Message",
        "Job", "Task", "Worker", "Scheduler", "Cron",
        "Log", "Metric", "Dashboard", "Alert", "Monitor",
    ]

    for word in words:
        clean = word.strip(".,;:!?()[]{}\"'")
        if clean in tech_words and clean not in components:
            components.append(clean)

    return components[:15]


def _catalog_interfaces(
    ocr_results: list[dict[str, Any]],
    keyframes: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Catalog user interfaces detected in frames."""
    interfaces: list[dict[str, Any]] = []

    ui_indicators = [
        "login", "sign in", "register", "sign up", "logout",
        "dashboard", "panel", "admin", "settings", "configuración",
        "menu", "nav", "navigation", "sidebar", "header", "footer",
        "form", "button", "input", "search", "filter", "table",
        "list", "grid", "card", "modal", "popup", "dialog", "alert",
        "toast", "notification", "profile", "user", "account",
        "home", "about", "contact", "help", "support",
        "page", "view", "screen", "screen load", "loading",
        "loader", "spinner", "progress", "progress bar",
        "graph", "chart", "statistic", "metric", "kpi",
        "button", "cta", "call to action", "link", "href",
        "responsive", "mobile", "tablet", "desktop",
        "dark mode", "theme", "language", "locale",
    ]

    for result in ocr_results:
        text = result.get("text", "")
        for indicator in ui_indicators:
            if indicator.lower() in text.lower():
                interfaces.append({
                    "interface_type": indicator.title(),
                    "evidence": text[:200],
                    "frame_index": result.get("frame_path", ""),
                    "confidence": 0.5,
                })
                break

    return interfaces[:10]


def _extract_visual_text(ocr_results: list[dict[str, Any]]) -> dict[str, Any]:
    """Extract all visual text from OCR results."""
    all_text: list[str] = []
    all_boxes: list[dict[str, Any]] = []
    total_confidence = 0.0
    count = 0

    for result in ocr_results:
        text = result.get("text", "")
        if text and len(text.strip()) > 2:
            all_text.append(text.strip())
            total_confidence += result.get("confidence", 0)
            count += 1

        for box in result.get("bounding_boxes", []):
            all_boxes.append({
                "text": box.get("text", ""),
                "confidence": box.get("confidence", 0),
                "x": box.get("x", 0),
                "y": box.get("y", 0),
                "w": box.get("w", 0),
                "h": box.get("h", 0),
                "frame": result.get("frame_path", ""),
            })

    return {
        "full_text": " ".join(all_text),
        "text_by_frame": [
            {"frame": r.get("frame_path", ""), "text": r.get("text", "")}
            for r in ocr_results if r.get("text")
        ],
        "total_blocks": count,
        "average_confidence": total_confidence / max(count, 1),
        "bounding_boxes": all_boxes,
    }


def _generate_visual_summary(
    video_info: dict[str, Any],
    scenes: list[dict[str, Any]],
    keyframes: list[dict[str, Any]],
    ocr_results: list[dict[str, Any]],
) -> str:
    """Generate a visual summary text."""
    parts = []

    duration = video_info.get("duration", 0)
    resolution = video_info.get("resolution", "desconocida")
    num_scenes = len(scenes)
    num_frames = len(keyframes)
    num_ocr_blocks = sum(len(r.get("bounding_boxes", [])) for r in ocr_results)

    parts.append(
        f"Vídeo de {resolution} de {duration:.1f} segundos con "
        f"{num_scenes} cambios de escena detectados."
    )

    if num_frames > 0:
        parts.append(
            f"Se extrajeron {num_frames} fotogramas representativos."
        )

    if num_ocr_blocks > 0:
        parts.append(
            f"Se detectaron {num_ocr_blocks} bloques de texto mediante OCR."
        )

    if num_scenes > 0:
        avg_scene = duration / num_scenes if duration > 0 else 0
        parts.append(
            f"La duración promedio de escena es de {avg_scene:.1f} segundos."
        )

    return " ".join(parts)


def _detect_relationships(
    ocr_results: list[dict[str, Any]],
    scenes: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Detect relationships between elements mentioned in text."""
    relationships: list[dict[str, Any]] = []

    relationship_indicators = [
        ("conecta", "conecta con", "conexión", "connection"),
        ("usa", "usa", "consume", "uses", "consumes"),
        ("depende", "depende de", "depend", "depends on"),
        ("llam", "llama a", "calls", "calls", "invoca", "invokes"),
        ("envía", "envía a", "sends to", "sends", "emits"),
        ("recibe", "recibe de", "receives from", "receives", "listens"),
        ("procesa", "procesa", "processes", "processes"),
        ("almacena", "almacena", "stores", "stores", "persiste", "persists"),
        ("autentica", "autentica", "authenticates", "authenticates"),
        ("autoriza", "autoriza", "authorizes", "authorizes"),
        ("notifica", "notifica", "notifies", "notifies", "alert", "alert"),
        ("monitorea", "monitorea", "monitors", "monitors"),
        ("balancea", "balancea", "balances", "balances"),
        ("redirige", "redirige", "redirects", "redirects"),
        ("transforma", "transforma", "transforms", "transforms"),
        ("valida", "valida", "validates", "validates"),
        ("filtra", "filtra", "filters", "filters"),
        ("cachea", "cachea", "caches", "caches"),
    ]

    for result in ocr_results:
        text = result.get("text", "")
        for rel_type, rel_action_es, rel_action_en, rel_action_plural in relationship_indicators:
            if rel_action_es in text.lower() or rel_action_en in text.lower():
                relationships.append({
                    "relationship_type": rel_type,
                    "action": rel_action_es,
                    "evidence": text[:200],
                    "confidence": 0.6,
                })
                break

    return relationships[:10]


def _detect_uncertainties(
    ocr_results: list[dict[str, Any]],
    scenes: list[dict[str, Any]],
    video_info: dict[str, Any],
) -> list[dict[str, Any]]:
    """Detect uncertainties and gaps in visual analysis."""
    uncertainties: list[dict[str, Any]] = []

    if len(scenes) == 0:
        uncertainties.append({
            "type": "Detección de escenas",
            "issue": "No se detectaron cambios de escena. Posiblemente el vídeo es una toma fija o el umbral es muy alto.",
            "confidence": 0.8,
            "suggestion": "Ajustar umbral de detección o usar método alternativo.",
        })

    if len(ocr_results) == 0:
        uncertainties.append({
            "type": "OCR",
            "issue": "No se detectó texto en los fotogramas analizados. Posiblemente el vídeo es predominantemente visual/audio sin texto en pantalla.",
            "confidence": 0.9,
            "suggestion": "Incrementar número de fotogramas o analizar fotogramas específicos.",
        })

    if video_info.get("duration", 0) > 600:
        uncertainties.append({
            "type": "Duración",
            "issue": f"Vídeo de larga duración ({video_info['duration']:.0f}s). El análisis visual puede ser incompleto.",
            "confidence": 0.7,
            "suggestion": "Considerar análisis por segmentos o aumentar recursos de procesamiento.",
        })

    return uncertainties


def _build_evidence_map(
    scenes: list[dict[str, Any]],
    keyframes: list[dict[str, Any]],
    ocr_results: list[dict[str, Any]],
) -> dict[str, Any]:
    """Build an evidence map linking findings to timestamps and frames."""
    evidence: dict[str, Any] = {
        "scenes": [
            {
                "timestamp": s.get("start_seconds", 0),
                "timestamp_str": s.get("start", ""),
                "frame_path": s.get("frame_path", ""),
                "method": s.get("method", "unknown"),
            }
            for s in scenes
        ],
        "keyframes": [
            {
                "timestamp": k.get("timestamp", 0),
                "timestamp_str": k.get("timestamp_str", ""),
                "frame_path": k.get("frame_path", ""),
                "dimensions": f"{k.get('width', 0)}x{k.get('height', 0)}",
            }
            for k in keyframes
        ],
        "ocr_by_frame": [
            {
                "frame": r.get("frame_path", ""),
                "blocks": len(r.get("bounding_boxes", [])),
                "text": r.get("text", "")[:200],
                "confidence": r.get("confidence", 0),
            }
            for r in ocr_results
        ],
    }
    return evidence


def _compute_visual_confidence(
    num_scenes: int,
    num_ocr_results: int,
    num_keyframes: int,
) -> float:
    """Compute visual context confidence."""
    score = 0.0
    if num_scenes > 0:
        score += 0.3
    if num_ocr_results > 0:
        score += 0.3
    if num_keyframes > 0:
        score += 0.2
    if num_ocr_results > 10:
        score += 0.1
    if num_scenes > 5:
        score += 0.1
    return min(score, 1.0)


# ---------------------------------------------------------------------------
# Extracted knowledge (consolidated)
# ---------------------------------------------------------------------------

def generate_extracted_knowledge(
    audio_context: dict[str, Any],
    visual_context: dict[str, Any],
    source: dict[str, Any],
) -> dict[str, Any]:
    """Generate consolidated extracted knowledge from audio and visual contexts.

    Args:
        audio_context: AudioContext generated by generate_audio_context().
        visual_context: VisualContext generated by generate_visual_context().
        source: Source information.

    Returns:
        KnowledgeExtraction dict.
    """
    # Merge confidences
    audio_conf = audio_context.get("confidence", 0)
    visual_conf = visual_context.get("confidence", 0)
    combined_conf = (audio_conf * 0.7) + (visual_conf * 0.3)

    return {
        "generated_at": now_utc().isoformat(),
        "source": source,
        "audio_context": audio_context,
        "visual_context": visual_context,
        "confidence_combined": round(combined_conf, 3),
        "warnings_summary": _generate_warnings_summary(audio_context, visual_context),
    }


def _generate_warnings_summary(
    audio_context: dict[str, Any],
    visual_context: dict[str, Any],
) -> list[dict[str, Any]]:
    """Generate warnings summary from both contexts."""
    warnings_list: list[dict[str, Any]] = []

    audio_flags = audio_context.get("warnings_flags", {})
    if audio_flags.get("has_high_severity_risks"):
        warnings_list.append({
            "type": "Riesgo",
            "severity": "Alto",
            "message": "Se detectaron riesgos de alta severidad en la transcripción.",
        })

    if audio_flags.get("has_deprecated_items"):
        warnings_list.append({
            "type": "Obsolescencia",
            "severity": "Medio",
            "message": "Se mencionaron elementos obsoletos o deprecated en el contenido.",
        })

    visual_uncertainties = visual_context.get("uncertainties_and_gaps", [])
    for unc in visual_uncertainties[:3]:
        warnings_list.append({
            "type": "Análisis visual",
            "severity": "Bajo",
            "message": unc.get("issue", ""),
        })

    return warnings_list


# ---------------------------------------------------------------------------
# Export functions for context documents
# ---------------------------------------------------------------------------

def export_audio_context_markdown(
    context: dict[str, Any],
    output_path: Optional[str] = None,
) -> str:
    """Export audio context to Markdown."""
    lines: list[str] = []

    lines.append("# Contexto de Audio")
    lines.append("")
    lines.append(f"**Generado:** {context.get('generated_at', 'N/A')}")
    lines.append(f"**Fuente:** {context.get('source', {}).get('title', 'N/A')}")
    lines.append(f"**Idioma:** {context.get('language', 'N/A')}")
    lines.append(f"**Duración del vídeo:** {context.get('video_duration_seconds', 'N/A')}s")
    lines.append(f"**Segmentos transcritos:** {context.get('transcript_segments_count', 0)}")
    lines.append(f"**Confianza:** {context.get('confidence', 0) * 100:.0f}%")
    lines.append("")

    # Executive summary
    summary = context.get("executive_summary", "")
    if summary:
        lines.append("## Resumen Ejecutivo")
        lines.append("")
        lines.append(summary)
        lines.append("")

    # Table of contents
    chapters = context.get("table_of_contents", [])
    if chapters:
        lines.append("## Índice Temporal")
        lines.append("")
        for ch in chapters:
            lines.append(
                f"- [{ch['start_time']} → {ch['end_time']}] "
                f"**{ch['title']}** — {ch.get('summary', '')[:100]}"
            )
        lines.append("")

    # Topics
    topics = context.get("topics", [])
    if topics:
        lines.append("## Temas Principales")
        lines.append("")
        for t in topics[:10]:
            lines.append(f"- **{t['title']}** ({t['mentions']} menciones)")
        lines.append("")

    # Technical concepts
    concepts = context.get("technical_concepts", [])
    if concepts:
        lines.append("## Conceptos Técnicos")
        lines.append("")
        for c in concepts[:15]:
            lines.append(
                f"- **{c['concept']}** — {c.get('description', '')}"
            )
        lines.append("")

    # Tools and technologies
    tools = context.get("tools_and_technologies", [])
    if tools:
        lines.append("## Herramientas y Tecnologías")
        lines.append("")
        for t in tools[:15]:
            lines.append(
                f"- **{t['tool']}** — {t.get('description', '')}"
            )
        lines.append("")

    # Procedures
    procedures = context.get("procedures", [])
    if procedures:
        lines.append("## Procedimientos")
        lines.append("")
        for p in procedures:
            lines.append(f"### {p['title']}")
            lines.append("")
            for step in p.get("steps", []):
                cmd = step.get("command", "")
                lines.append(f"{step['step']}. {step['text']}")
                if cmd:
                    lines.append(f"   ```bash\n   {cmd}\n   ```")
            lines.append("")

    # Decisions
    decisions = context.get("decisions", [])
    if decisions:
        lines.append("## Decisiones")
        lines.append("")
        for d in decisions[:5]:
            lines.append(f"- **{d['text'][:100]}**")
        lines.append("")

    # Requirements
    requirements = context.get("requirements", [])
    if requirements:
        lines.append("## Requisitos")
        lines.append("")
        for r in requirements[:10]:
            lines.append(f"- [{r.get('type', 'General')}] {r['text'][:150]}")
        lines.append("")

    # Constraints
    constraints = context.get("constraints", [])
    if constraints:
        lines.append("## Restricciones")
        lines.append("")
        for c in constraints[:10]:
            lines.append(f"- [{c.get('severity', 'Bajo')}] [{c.get('type', 'General')}] {c['text'][:150]}")
        lines.append("")

    # Risks
    risks = context.get("risks", [])
    if risks:
        lines.append("## Riesgos")
        lines.append("")
        for r in risks[:10]:
            lines.append(f"- [{r.get('severity', 'Medio')}] [{r.get('type', 'General')}] {r['text'][:150]}")
            if r.get("mitigation"):
                lines.append(f"  - *Mitigación:* {r['mitigation'][:150]}")
        lines.append("")

    # Warnings
    warnings = context.get("warnings", [])
    if warnings:
        lines.append("## Advertencias")
        lines.append("")
        for w in warnings[:10]:
            lines.append(f"- [{w.get('severity', 'Normal')}] {w['text'][:150]}")
        lines.append("")

    # Recommendations
    recommendations = context.get("recommendations", [])
    if recommendations:
        lines.append("## Recomendaciones")
        lines.append("")
        for r in recommendations[:10]:
            lines.append(f"- **[{r.get('strength', 'Sugerencia')}]** {r['text'][:150]}")
        lines.append("")

    # Entities
    entities = context.get("entities", [])
    if entities:
        lines.append("## Entidades")
        lines.append("")
        for e in entities[:15]:
            lines.append(f"- **{e['entity']}** ({e['type']})")
        lines.append("")

    # Potential tasks
    tasks = context.get("potential_tasks", [])
    if tasks:
        lines.append("## Tareas Potenciales")
        lines.append("")
        for t in tasks[:10]:
            lines.append(f"- [{t.get('priority', 'Baja')}] [{t.get('type', 'General')}] {t['text'][:150]}")
        lines.append("")

    # Open questions
    open_questions = context.get("open_questions", [])
    if open_questions:
        lines.append("## Preguntas Abiertas")
        lines.append("")
        for q in open_questions[:10]:
            lines.append(f"- {q['text']}")
        lines.append("")

    # Quotes
    quotes = context.get("quotes", [])
    if quotes:
        lines.append("## Citas Destacadas")
        lines.append("")
        for q in quotes[:10]:
            lines.append(f"> {q['text'][:200]}")
            lines.append(f"> *[{q['start']} → {q['end']}] — {q['type']}*")
            lines.append("")
        lines.append("")

    # Facts
    facts = context.get("facts", [])
    if facts:
        lines.append("## Hechos Expresados")
        lines.append("")
        for f in facts[:10]:
            note = f"[{f.get('type', 'General')}]" if f.get("has_quantitative_data") else ""
            lines.append(f"- {f['text'][:200]} {note}")
        lines.append("")

    # Inferences
    inferences = context.get("inferences", [])
    if inferences:
        lines.append("## Inferencias")
        lines.append("")
        lines.append("*Las siguientes inferencias son deducciones del sistema a partir de los hechos expresados:*")
        lines.append("")
        for inf in inferences[:10]:
            lines.append(f"- {inf['text'][:200]}")
            if inf.get("supporting_facts_count", 0) > 0:
                lines.append(f"  *(Basado en {inf['supporting_facts_count']} hecho(s) expresado(s))*")
        lines.append("")

    # Confidence by section
    conf_by_section = context.get("confidence_by_section", {})
    if conf_by_section:
        lines.append("## Nivel de Confianza por Sección")
        lines.append("")
        for section, score in sorted(conf_by_section.items(), key=lambda x: -x[1]):
            lines.append(f"- **{section.replace('_', ' ').title()}:** {score * 100:.0f}%")
        lines.append("")

    if output_path:
        Path(output_path).write_text("\n".join(lines), encoding="utf-8")

    return "\n".join(lines)


def export_visual_context_markdown(
    context: dict[str, Any],
    output_path: Optional[str] = None,
) -> str:
    """Export visual context to Markdown."""
    lines: list[str] = []

    lines.append("# Contexto Visual")
    lines.append("")
    lines.append(f"**Generado:** {context.get('generated_at', 'N/A')}")
    lines.append(f"**Cambios de escena:** {context.get('scene_changes_count', 0)}")
    lines.append(f"**Fotogramas extraídos:** {context.get('keyframes_count', 0)}")
    lines.append(f"**Bloques OCR:** {context.get('ocr_blocks_count', 0)}")
    lines.append(f"**Confianza:** {context.get('confidence', 0) * 100:.0f}%")
    lines.append("")

    # Scene summary
    scene_summary = context.get("scene_summary", {})
    if scene_summary:
        lines.append("## Resumen de Escenas")
        lines.append("")
        lines.append(f"- Total de escenas: {scene_summary.get('total_scenes', 0)}")
        lines.append(
            f"- Duración promedio: {scene_summary.get('average_scene_duration', 0):.1f}s"
        )
        lines.append(
            f"- Escena más corta: {scene_summary.get('shortest_scene_seconds', 0):.1f}s"
        )
        lines.append(
            f"- Escena más larga: {scene_summary.get('longest_scene_seconds', 0):.1f}s"
        )
        lines.append("")

    # Diagrams
    diagrams = context.get("diagrams_detected", [])
    if diagrams:
        lines.append("## Diagramas Detectados")
        lines.append("")
        for d in diagrams:
            lines.append(f"- **{d['type']}**: {d['evidence'][:150]}")
            lines.append(f"  *Frame: {d.get('frame', '')}*")
        lines.append("")

    # Flows
    flows = context.get("flows_detected", [])
    if flows:
        lines.append("## Flujos de Trabajo")
        lines.append("")
        for f in flows:
            lines.append(f"-{f['step']}. {f['evidence'][:150]}")
        lines.append("")

    # Architectures
    architectures = context.get("architectures_detected", [])
    if architectures:
        lines.append("## Arquitecturas Detectadas")
        lines.append("")
        for a in architectures:
            lines.append(f"- **{a['architecture_type']}**: {a['evidence'][:150]}")
            if a.get("components_mentioned"):
                lines.append(f"  *Componentes: {', '.join(a['components_mentioned'][:5])}*")
        lines.append("")

    # Interfaces
    interfaces = context.get("interfaces_catalogued", [])
    if interfaces:
        lines.append("## Interfaces")
        lines.append("")
        for i in interfaces:
            lines.append(f"- **{i['interface_type']}**: {i['evidence'][:150]}")
        lines.append("")

    # Visual text
    visual_text = context.get("visual_text", {})
    if visual_text.get("full_text"):
        lines.append("## Texto Extraído del Vídeo")
        lines.append("")
        lines.append(visual_text["full_text"][:2000])
        lines.append("")

    # Summary
    summary = context.get("visual_summary", "")
    if summary:
        lines.append("## Resumen Visual")
        lines.append("")
        lines.append(summary)
        lines.append("")

    # Relationships
    relationships = context.get("relationships_detected", [])
    if relationships:
        lines.append("## Relaciones Detectadas")
        lines.append("")
        for r in relationships:
            lines.append(f"- **{r['relationship_type']}**: {r['evidence'][:150]}")
        lines.append("")

    # Uncertainties
    uncertainties = context.get("uncertainties_and_gaps", [])
    if uncertainties:
        lines.append("## Incertidumbres y Limitaciones")
        lines.append("")
        for u in uncertainties:
            lines.append(f"- **{u['type']}**: {u['issue'][:150]}")
            if u.get("suggestion"):
                lines.append(f"  *Sugerencia:* {u['suggestion'][:150]}")
        lines.append("")

    # Evidence
    evidence = context.get("evidence", {})
    if evidence.get("scenes"):
        lines.append("## Evidencia")
        lines.append("")
        lines.append("### Cambios de Escena")
        lines.append("")
        for ev in evidence["scenes"]:
            lines.append(f"- [{ev['timestamp_str']}] {ev.get('frame_path', '')}")
        lines.append("")

    if output_path:
        Path(output_path).write_text("\n".join(lines), encoding="utf-8")

    return "\n".join(lines)

def export_visual_context_mdx(
    context: dict,
    output_path: str = None,
    components: dict = None,
) -> str:
    """Export visual context to MDX (Markdown + JSX)."""
    lines = []
    lines.append("---")
    lines.append("title: Contexto Visual")
    lines.append("generated: " + str(context.get("generated_at", "N/A")))
    vi = context.get("video_info", {})
    lines.append("video_duration: " + str(vi.get("duration", 0)))
    lines.append("resolution: " + str(vi.get("resolution", "N/A")))
    lines.append("scene_changes: " + str(context.get("scene_changes_count", 0)))
    lines.append("keyframes: " + str(context.get("keyframes_count", 0)))
    lines.append("ocr_blocks: " + str(context.get("ocr_blocks_count", 0)))
    lines.append("confidence: " + str(context.get("confidence", 0)))
    lines.append("---")
    lines.append("")
    lines.append("import VideoFrame from './components/VideoFrame.tsx'")
    lines.append("import TimeMarker from './components/TimeMarker.tsx'")
    lines.append("import OCREdge from './components/OCREdge.tsx'")
    lines.append("import DiagramBlock from './components/DiagramBlock.tsx'")
    lines.append("import SceneTransition from './components/SceneTransition.tsx'")
    lines.append("import VisualEvidence from './components/VisualEvidence.tsx'")
    lines.append("")
    lines.append("# Contexto Visual")
    lines.append("")
    gen = str(context.get("generated_at", ""))
    sc = context.get("scene_changes_count", 0)
    kf = context.get("keyframes_count", 0)
    ob = context.get("ocr_blocks_count", 0)
    conf = context.get("confidence", 0)
    lines.append("**Generado:** <TimeMarker timestamp=\"" + gen + "\" />")
    lines.append("**Cambios de escena:** " + str(sc))
    lines.append("**Fotogramas extra\u00eddos:** " + str(kf))
    lines.append("**Bloques OCR:** " + str(ob))
    lines.append("**Confianza:** " + str(int(conf * 100)) + "%")
    lines.append("")

    scene_summary = context.get("scene_summary", {})
    if scene_summary:
        lines.append("## Resumen de Escenas")
        lines.append("")
        total = scene_summary.get("total_scenes", 0)
        avg = scene_summary.get("average_scene_duration", 0)
        mini = scene_summary.get("shortest_scene_seconds", 0)
        maxi = scene_summary.get("longest_scene_seconds", 0)
        lines.append("<SceneTransition total=" + str(total) + " avgDuration=" + str(avg) + " minDuration=" + str(mini) + " maxDuration=" + str(maxi) + " />")
        lines.append("")

    for d in context.get("diagrams_detected", []):
        lines.append("## Diagramas Detectados")
        lines.append("")
        ev = str(d.get("evidence", ""))[:200].replace('"', "'")
        lines.append("<DiagramBlock type=\"" + str(d.get("type", "")) + "\" evidence=\"" + ev + "\" frame=\"" + str(d.get("frame", "")) + "\" confidence=" + str(d.get("confidence", 0)) + " />")
        lines.append("")

    for f in context.get("flows_detected", []):
        lines.append("## Flujos de Trabajo")
        lines.append("")
        ev = str(f.get("evidence", ""))[:200].replace('"', "'")
        lines.append("<VisualEvidence frame=\"" + str(f.get("frame_index", "")) + "\" text=\"" + ev + "\" step=" + str(f.get("step", 0)) + " />")
        lines.append("")

    for a in context.get("architectures_detected", []):
        lines.append("## Arquitecturas Detectadas")
        lines.append("")
        comps = a.get("components_mentioned", [])
        comp_str = ", ".join(comps[:5]) if comps else ""
        ev = str(a.get("evidence", ""))[:200].replace('"', "'")
        lines.append("<DiagramBlock type=\"" + a.get("architecture_type", "") + "\" evidence=\"" + ev + "\" components=\"" + comp_str.replace('"', "'") + "\" confidence=" + str(a.get("confidence", 0)) + " />")
        lines.append("")

    for i_face in context.get("interfaces_catalogued", []):
        lines.append("## Interfaces Detectadas")
        lines.append("")
        ev = str(i_face.get("evidence", ""))[:200].replace('"', "'")
        lines.append("<VisualEvidence frame=\"" + str(i_face.get("frame_index", "")) + "\" text=\"" + ev + "\" type=\"" + i_face.get("interface_type", "") + "\" />")
        lines.append("")

    vtd = context.get("visual_text", {})
    if vtd.get("bounding_boxes"):
        lines.append("## Texto Extra\u00eddo \u2014 Coordenadas")
        lines.append("")
        for bb in vtd["bounding_boxes"][:20]:
            txt = str(bb.get("text", ""))[:100].replace('"', "'")
            lines.append("<OCREdge text=\"" + txt + "\" x=" + str(bb.get("x", 0)) + " y=" + str(bb.get("y", 0)) + " w=" + str(bb.get("w", 0)) + " h=" + str(bb.get("h", 0)) + " confidence=" + str(bb.get("confidence", 0)) + " frame=\"" + bb.get("frame", "") + "\" />")
        lines.append("")

    if vtd.get("full_text"):
        lines.append("## Texto Extra\u00eddo del V\u00eddeo")
        lines.append("")
        lines.append(str(vtd["full_text"])[:2000])
        lines.append("")

    if context.get("evidence", {}).get("keyframes"):
        lines.append("## Fotogramas Representativos")
        lines.append("")
        for kf in context["evidence"]["keyframes"]:
            ts = str(kf.get("timestamp_str", ""))
            fp = str(kf.get("frame_path", ""))
            w = kf.get("width", 0)
            h = kf.get("height", 0)
            lines.append("<VideoFrame timestamp=\"" + ts + "\" src=\"" + fp + "\" title=\"Frame " + ts + " (" + str(w) + "x" + str(h) + ")\" dimensions=\"" + str(w) + "x" + str(h) + "\" />")
        lines.append("")

    summary = context.get("visual_summary", "")
    if summary:
        lines.append("## Resumen Visual")
        lines.append("")
        lines.append(str(summary))
        lines.append("")

    score = context.get("confidence_by_section", {}).get("relationships_detected", 0.5)
    if context.get("relationships_detected", []):
        lines.append("## Relaciones Detectadas")
        lines.append("")
        lines.append("<SectionConfidence section=\"relationships_detected\" score=\"" + str(score) + "\" />")
        lines.append("")
        for r in context["relationships_detected"]:
            lines.append("- **" + str(r.get("relationship_type", "")) + "**: " + str(r.get("evidence", ""))[:150])
        lines.append("")

    for u in context.get("uncertainties_and_gaps", []):
        lines.append("## Incertidumbres y Limitaciones")
        lines.append("")
        lines.append("- **" + str(u.get("type", "")) + "**: " + str(u.get("issue", ""))[:150])
        sug = u.get("suggestion")
        if sug:
            lines.append("  *Sugerencia:* " + str(sug)[:150])
        lines.append("")

    if context.get("evidence", {}).get("scenes"):
        lines.append("## Evidencia de Escenas")
        lines.append("")
        for ev in context["evidence"]["scenes"]:
            lines.append("<SceneTransition timestamp=\"" + ev["timestamp_str"] + "\" frame=\"" + ev.get("frame_path", "") + "\" method=\"" + ev.get("method", "unknown") + "\" />")
        lines.append("")

    if output_path:
        Path(output_path).with_suffix(".mdx").write_text("\n".join(lines), encoding="utf-8")

    return "\n".join(lines)


def export_audio_context_mdx(
    context: dict,
    output_path: str = None,
    components: dict = None,
) -> str:
    """Export audio context to MDX (Markdown + JSX)."""
    lines = []
    source = context.get("source", {})
    lines.append("---")
    lines.append("title: Contexto de Audio")
    lines.append("generated: " + str(context.get("generated_at", "N/A")))
    lines.append("source_title: " + str(source.get("title", "N/A")))
    lines.append("source_url: " + str(source.get("url", "")))
    lines.append("transcript_segments: " + str(context.get("transcript_segments_count", 0)))
    lines.append("transcript_length: " + str(context.get("transcript_text_length", 0)))
    lines.append("language: " + str(context.get("language", "N/A")))
    lines.append("video_duration: " + str(context.get("video_duration_seconds", 0)))
    lines.append("confidence: " + str(context.get("confidence", 0)))
    lines.append("---")
    lines.append("")

    lines.append("import TranscriptSegment from './components/TranscriptSegment.tsx'")
    lines.append("import TimeMarker from './components/TimeMarker.tsx'")
    lines.append("import QuoteBlock from './components/QuoteBlock.tsx'")
    lines.append("import ConfidenceBadge from './components/ConfidenceBadge.tsx'")
    lines.append("import SectionConfidence from './components/SectionConfidence.tsx'")
    lines.append("import ChapterMarker from './components/ChapterMarker.tsx'")
    lines.append("import FactBlock from './components/FactBlock.tsx'")
    lines.append("import InferenceBlock from './components/InferenceBlock.tsx'")
    lines.append("import WarningBox from './components/WarningBox.tsx'")
    lines.append("import TaskItem from './components/TaskItem.tsx'")
    lines.append("import TopicTag from './components/TopicTag.tsx'")
    lines.append("import ToolCard from './components/ToolCard.tsx'")
    lines.append("")

    lines.append("# Contexto de Audio")
    lines.append("")
    gen = str(context.get("generated_at", ""))
    lines.append("**Generado:** <TimeMarker timestamp=\"" + gen + "\" />")
    lines.append("**Fuente:** " + str(source.get("title", source.get("url", "N/A"))))
    if source.get("uploader"):
        lines.append("**Canal:** " + str(source["uploader"]))
    if source.get("duration"):
        lines.append("**Duraci\u00f3n:** " + str(source["duration"]) + "s")
    lines.append("**Segmentos:** " + str(context.get("transcript_segments_count", 0)))
    lines.append("**Idioma:** " + str(context.get("language", "N/A")))
    conf = context.get("confidence", 0)
    lines.append("**Confianza:** <ConfidenceBadge score=\"" + str(conf) + "\" label=\"Confianza\" />")
    lines.append("")

    summary = context.get("executive_summary", "")
    if summary:
        lines.append("## Resumen Ejecutivo")
        lines.append("")
        cs = context.get("confidence_by_section", {}).get("executive_summary", 0)
        lines.append("<ConfidenceBadge score=\"" + str(cs) + "\" label=\"Secci\u00f3n resumen\" />")
        lines.append("")
        lines.append(str(summary))
        lines.append("")

    chapters = context.get("table_of_contents", [])
    if chapters:
        lines.append("## \u00cdndice Temporal")
        lines.append("")
        cs = context.get("confidence_by_section", {}).get("table_of_contents", 0)
        lines.append("<SectionConfidence section=\"table_of_contents\" score=\"" + str(cs) + "\" />")
        lines.append("")
        for ch in chapters:
            s = str(ch.get("summary", ""))[:200].replace('"', "'")
            lines.append("<ChapterMarker start=\"" + ch["start_time"] + "\" end=\"" + ch["end_time"] + "\" title=\"" + ch["title"] + "\" summary=\"" + s + "\" />")
        lines.append("")

    topics = context.get("topics", [])
    if topics:
        lines.append("## Temas Principales")
        lines.append("")
        cs = context.get("confidence_by_section", {}).get("topics", 0)
        lines.append("<SectionConfidence section=\"topics\" score=\"" + str(cs) + "\" />")
        lines.append("")
        lines.append("<div className=\"topic-grid\">")
        for t in topics[:10]:
            lines.append("  <TopicTag title=\"" + str(t["title"]) + "\" mentions=\"" + str(t["mentions"]) + "\" relevance=\"" + str(t.get("relevance", 0)) + "\" />")
        lines.append("</div>")
        lines.append("")

    for c in context.get("technical_concepts", [])[:15]:
        lines.append("## Conceptos T\u00e9cnicos")
        lines.append("")
        cs = context.get("confidence_by_section", {}).get("technical_concepts", 0)
        lines.append("<SectionConfidence section=\"technical_concepts\" score=\"" + str(cs) + "\" />")
        lines.append("")
        desc = str(c.get("description", ""))
        lines.append("- **" + c["concept"] + "** \u2014 " + desc + " (" + str(c["mentions"]) + " mentions)")
        lines.append("")

    for t in context.get("tools_and_technologies", [])[:15]:
        lines.append("## Herramientas y Tecnolog\u00edas")
        lines.append("")
        cs = context.get("confidence_by_section", {}).get("tools_and_technologies", 0)
        lines.append("<SectionConfidence section=\"tools_and_technologies\" score=\"" + str(cs) + "\" />")
        lines.append("")
        desc = str(t.get("description", ""))[:200].replace('"', "'")
        lines.append("<ToolCard name=\"" + t["tool"] + "\" description=\"" + desc + "\" category=\"" + t.get("category", "") + "\" mentions=\"" + str(t["mentions"]) + "\" />")
        lines.append("")

    for p in context.get("procedures", []):
        lines.append("## Procedimientos")
        lines.append("")
        cs = context.get("confidence_by_section", {}).get("procedures", 0)
        lines.append("<SectionConfidence section=\"procedures\" score=\"" + str(cs) + "\" />")
        lines.append("")
        lines.append("### " + p["title"] + " \u2014 Complejidad: " + str(p.get("estimated_complexity", "N/A")))
        lines.append("")
        for step in p.get("steps", []):
            cmd = str(step.get("command", ""))
            text_safe = str(step["text"])[:200].replace('"', "'")
            ts = str(step.get("timestamp", ""))
            lines.append("<TranscriptSegment start=\"" + ts + "\" text=\"" + text_safe + "\" />")
            if cmd:
                lines.append("```bash\\n" + cmd + "\\n```")
            lines.append("")

    for d in context.get("decisions", [])[:5]:
        lines.append("## Decisiones")
        lines.append("")
        cs = context.get("confidence_by_section", {}).get("decisions", 0)
        lines.append("<SectionConfidence section=\"decisions\" score=\"" + str(cs) + "\" />")
        lines.append("")
        lines.append("- **" + str(d["text"])[:100] + "**")
        if d.get("rationale"):
            lines.append("  - *Justificaci\u00f3n:* " + str(d["rationale"])[:150])
        if d.get("implication"):
            lines.append("  - *Implicaci\u00f3n:* " + str(d["implication"])[:150])
        lines.append("")

    for r in context.get("requirements", [])[:10]:
        lines.append("## Requisitos")
        lines.append("")
        cs = context.get("confidence_by_section", {}).get("requirements", 0)
        lines.append("<SectionConfidence section=\"requirements\" score=\"" + str(cs) + "\" />")
        lines.append("")
        lines.append("- [" + r.get("type", "General") + "] " + str(r["text"])[:150])
        lines.append("")

    for c in context.get("constraints", [])[:10]:
        lines.append("## Restricciones")
        lines.append("")
        cs = context.get("confidence_by_section", {}).get("constraints", 0)
        lines.append("<SectionConfidence section=\"constraints\" score=\"" + str(cs) + "\" />")
        lines.append("")
        text_safe = str(c["text"])[:200].replace('"', "'")
        lines.append("<WarningBox severity=\"" + c.get("severity", "Bajo") + "\" text=\"" + text_safe + "\" type=\"" + c.get("type", "General") + "\" />")
        lines.append("")

    for r in context.get("risks", [])[:10]:
        lines.append("## Riesgos")
        lines.append("")
        cs = context.get("confidence_by_section", {}).get("risks", 0)
        lines.append("<SectionConfidence section=\"risks\" score=\"" + str(cs) + "\" />")
        lines.append("")
        text_safe = str(r["text"])[:200].replace('"', "'")
        lines.append("<WarningBox severity=\"" + r.get("severity", "Medio") + "\" text=\"" + text_safe + "\" type=\"" + r.get("type", "General") + "\" />")
        if r.get("mitigation"):
            lines.append("  - *Mitigaci\u00f3n:* " + str(r["mitigation"])[:150])
        lines.append("")

    for w in context.get("warnings", [])[:10]:
        lines.append("## Advertencias")
        lines.append("")
        cs = context.get("confidence_by_section", {}).get("warnings", 0)
        lines.append("<SectionConfidence section=\"warnings\" score=\"" + str(cs) + "\" />")
        lines.append("")
        text_safe = str(w["text"])[:200].replace('"', "'")
        lines.append("<WarningBox severity=\"" + w.get("severity", "Normal") + "\" text=\"" + text_safe + "\" type=\"" + w.get("type", "General") + "\" />")
        lines.append("")

    for r in context.get("recommendations", [])[:10]:
        lines.append("## Recomendaciones")
        lines.append("")
        cs = context.get("confidence_by_section", {}).get("recommendations", 0)
        lines.append("<SectionConfidence section=\"recommendations\" score=\"" + str(cs) + "\" />")
        lines.append("")
        lines.append("- **[" + r.get("strength", "Sugerencia") + "]** " + str(r["text"])[:150])
        lines.append("")

    for e in context.get("entities", [])[:15]:
        lines.append("## Entidades")
        lines.append("")
        cs = context.get("confidence_by_section", {}).get("entities", 0)
        lines.append("<SectionConfidence section=\"entities\" score=\"" + str(cs) + "\" />")
        lines.append("")
        lines.append("- **" + e["entity"] + "** (" + e["type"] + ")")
        lines.append("")

    for t in context.get("potential_tasks", [])[:10]:
        lines.append("## Tareas Potenciales")
        lines.append("")
        cs = context.get("confidence_by_section", {}).get("potential_tasks", 0)
        lines.append("<SectionConfidence section=\"potential_tasks\" score=\"" + str(cs) + "\" />")
        lines.append("")
        text_safe = str(t["text"])[:200].replace('"', "'")
        lines.append("<TaskItem priority=\"" + t.get("priority", "Baja") + "\" type=\"" + t.get("type", "General") + "\" text=\"" + text_safe + "\" timestamp=\"" + t.get("timestamp", "") + "\" />")
        lines.append("")

    for q in context.get("open_questions", [])[:10]:
        lines.append("## Preguntas Abiertas")
        lines.append("")
        cs = context.get("confidence_by_section", {}).get("open_questions", 0)
        lines.append("<SectionConfidence section=\"open_questions\" score=\"" + str(cs) + "\" />")
        lines.append("")
        text_safe = str(q["text"])[:200].replace('"', "'")
        lines.append("<TranscriptSegment start=\"" + q.get("timestamp", "") + "\" text=\"" + text_safe + "\" />")
        openness = q.get("confidence_open", 0.5)
        lines.append("  *Confianza de apertura: " + str(round(openness * 100)) + "%*")
        lines.append("")

    for q in context.get("quotes", [])[:10]:
        lines.append("## Citas Destacadas")
        lines.append("")
        cs = context.get("confidence_by_section", {}).get("quotes", 0)
        lines.append("<SectionConfidence section=\"quotes\" score=\"" + str(cs) + "\" />")
        lines.append("")
        text_safe = str(q["text"])[:200].replace('"', "'")
        lines.append("<QuoteBlock text=\"" + text_safe + "\" start=\"" + q.get("start", "") + "\" end=\"" + q.get("end", "") + "\" type=\"" + q.get("type", "Observacion") + "\" significance=\"" + str(q.get("significance", 0)) + "\" />")
        lines.append("")

    for f in context.get("facts", [])[:10]:
        lines.append("## Hechos Expresados")
        lines.append("")
        cs = context.get("confidence_by_section", {}).get("facts", 0)
        lines.append("<SectionConfidence section=\"facts\" score=\"" + str(cs) + "\" />")
        lines.append("")
        lines.append("*Los siguientes hechos fueron extra\u00eddos directamente de la transcripci\u00f3n:*")
        lines.append("")
        text_safe = str(f["text"])[:200].replace('"', "'")
        lines.append("<FactBlock text=\"" + text_safe + "\" type=\"" + f.get("type", "General") + "\" hasData=\"" + str(f.get("has_quantitative_data", False)) + "\" confidence=\"" + str(f.get("confidence", 0.5)) + "\" />")
        lines.append("")

    for inf in context.get("inferences", [])[:10]:
        lines.append("## Inferencias")
        lines.append("")
        lines.append("*Estas inferencias son deducciones del sistema basadas en los hechos expresados anteriormente. No fueron dichas expl\u00edcitamente en el v\u00eddeo.*")
        lines.append("")
        cs = context.get("confidence_by_section", {}).get("inferences", 0)
        lines.append("<SectionConfidence section=\"inferences\" score=\"" + str(cs) + "\" />")
        lines.append("")
        text_safe = str(inf["text"])[:200].replace('"', "'")
        sf = str(inf.get("source_fact", ""))[:200].replace('"', "'")
        lines.append("<InferenceBlock text=\"" + text_safe + "\" supportingFacts=\"" + str(inf.get("supporting_facts_count", 0)) + "\" confidence=\"" + str(inf.get("confidence", 0.5)) + "\" isSystemInference=\"" + str(inf.get("is_system_inference", True)) + "\" sourceFact=\"" + sf + "\" />")
        lines.append("")

    conf_by_section = context.get("confidence_by_section", {})
    if conf_by_section:
        lines.append("## Nivel de Confianza por Secci\u00f3n")
        lines.append("")
        lines.append("*Resumen de confianza para cada secci\u00f3n del an\u00e1lisis:*")
        lines.append("")
        for section, score in sorted(conf_by_section.items(), key=lambda x: -x[1]):
            safe = str(section).replace(".", "_").replace(" ", "_")
            label = str(section).replace("_", " ").title()
            lines.append("<SectionConfidence section=\"" + safe + "\" score=\"" + str(score) + "\" label=\"" + label + "\" />")
        lines.append("")

    if output_path:
        Path(output_path).with_suffix(".mdx").write_text("\n".join(lines), encoding="utf-8")

    return "\n".join(lines)


def export_extracted_knowledge_mdx(
    knowledge: dict,
    output_path: str = None,
) -> str:
    """Export consolidated extracted knowledge to MDX."""
    audio_mdx = export_audio_context_mdx(knowledge.get("audio_context", {}), output_path=None)
    visual_mdx = export_visual_context_mdx(knowledge.get("visual_context", {}), output_path=None)

    source = knowledge.get("source", {})
    combined = []

    combined.append("---")
    combined.append("title: Conocimiento Extra\u00edo \u2014 " + str(source.get("title", "V\u00eddeo")))
    combined.append("generated: " + str(knowledge.get("generated_at", "N/A")))
    combined.append("source_title: " + str(source.get("title", "N/A")))
    combined.append("source_url: " + str(source.get("url", "")))
    combined.append("confidence_combined: " + str(knowledge.get("confidence_combined", 0)))
    combined.append("---")
    combined.append("")

    combined.append("import VideoFrame from './components/VideoFrame.tsx'")
    combined.append("import TranscriptSegment from './components/TranscriptSegment.tsx'")
    combined.append("import QuoteBlock from './components/QuoteBlock.tsx'")
    combined.append("import ConfidenceBadge from './components/ConfidenceBadge.tsx'")
    combined.append("import SectionConfidence from './components/SectionConfidence.tsx'")
    combined.append("import ChapterMarker from './components/ChapterMarker.tsx'")
    combined.append("import FactBlock from './components/FactBlock.tsx'")
    combined.append("import InferenceBlock from './components/InferenceBlock.tsx'")
    combined.append("import WarningBox from './components/WarningBox.tsx'")
    combined.append("import TaskItem from './components/TaskItem.tsx'")
    combined.append("import DiagramBlock from './components/DiagramBlock.tsx'")
    combined.append("import SceneTransition from './components/SceneTransition.tsx'")
    combined.append("import VisualEvidence from './components/VisualEvidence.tsx'")
    combined.append("import OCREdge from './components/OCREdge.tsx'")
    combined.append("import TopicTag from './components/TopicTag.tsx'")
    combined.append("import ToolCard from './components/ToolCard.tsx'")
    combined.append("")

    combined.append("# Conocimiento Extra\u00edo del V\u00eddeo")
    combined.append("")
    combined.append("**Generado:** " + str(knowledge.get("generated_at", "N/A")))
    combined.append("**Fuente:** " + str(source.get("title", source.get("url", "N/A"))))
    combined.append("")
    combined.append("**Confianza combinada:** <ConfidenceBadge score=\"" + str(knowledge.get("confidence_combined", 0)) + "\" label=\"Confianza general (audio 70% + visual 30%)\" />")
    combined.append("")

    combined.append("---")
    combined.append("")
    combined.append("# Parte 1: Contexto de Audio")
    combined.append("")

    audio_section = export_audio_context_mdx(knowledge.get("audio_context", {}), output_path=None)
    audio_lines = audio_section.split("\\n")
    content_start = 0
    for i, line in enumerate(audio_lines):
        if line.startswith("# Contexto de Audio"):
            content_start = i
            break
    combined.extend(audio_lines[content_start:])
    combined.append("")

    combined.append("---")
    combined.append("")
    combined.append("# Parte 2: Contexto Visual")
    combined.append("")

    visual_section = export_visual_context_mdx(knowledge.get("visual_context", {}), output_path=None)
    visual_lines = visual_section.split("\\n")
    content_start = 0
    for i, line in enumerate(visual_lines):
        if line.startswith("# Contexto Visual"):
            content_start = i
            break
    combined.extend(visual_lines[content_start:])
    combined.append("")

    for w in knowledge.get("warnings_summary", []):
        combined.append("---")
        combined.append("")
        combined.append("# Resumen de Advertencias")
        combined.append("")
        combined.append("<WarningBox severity=\"" + w.get("severity", "Normal") + "\" text=\"" + str(w.get("message", "")) + "\" type=\"" + w.get("type", "General") + "\" />")
        combined.append("")

    result = "\n".join(combined)
    if output_path:
        Path(output_path).with_suffix(".mdx").write_text(result, encoding="utf-8")

    return result
