from __future__ import annotations

from pathlib import Path
import json
from jsonschema import validate as jsonschema_validate
from jsonschema.exceptions import ValidationError as JsonSchemaValidationError
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse

from .models import (
    TranscodeRequest,
    GenerateRequest,
    GenerateResponse,
    GenerateOpsRequest,
    GenerateOpsResponse,
)
from .spec import generate_spec
from .codegen import stub_generate_code
from .spec_generator import SpecGenerator
from .providers import generate_with_provider, get_provider_stats
from .prompts import prompt_registry
from .project_graph import ProjectGraphBuilder
from .rag_system import rag_enrichment
from .permissions import permission_manager
from .edit_engine import edit_engine
from .vcs_ops import vcs_ops
from .health_monitor import health_monitor


app = FastAPI(title="AEIOU Self-Transcoder Sidecar", version="0.1.0")


def _schema_path() -> Path:
    # repo_root / schemas / canonical_spec.schema.json
    return Path(__file__).resolve().parents[2] / "schemas" / "canonical_spec.schema.json"


def _load_schema() -> dict:
    schema_file = _schema_path()
    try:
        with schema_file.open("r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        raise RuntimeError(f"Schema not found at {schema_file}")


SCHEMA = _load_schema()


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/heartbeat")
def heartbeat(data: dict) -> dict:
    energy = data.get("energy", 0)
    analysis = data.get("analysis")

    # Process analysis data if provided
    if analysis:
        # TODO: Store analysis in database, check thresholds for alerts
        print(f"Heartbeat analysis: {analysis}")  # Debug logging

    # Could trigger watchers based on energy thresholds
    return {"status": "ok", "energy": energy}


@app.post("/event")
def handle_event(data: dict) -> dict:
    event_type = data.get("type")
    # TODO: Process different event types (FILE_SAVED, USER_IDLE, etc.)
    # Could trigger watchers or update internal state
    return {"status": "ok", "event_type": event_type}


@app.post("/transcode")
def transcode(req: TranscodeRequest) -> dict:
    spec = generate_spec(req)
    try:
        jsonschema_validate(instance=spec, schema=SCHEMA)
    except JsonSchemaValidationError as e:
        raise HTTPException(status_code=500, detail=f"Spec validation failed: {e.message}")
    return spec


@app.post("/generate", response_model=GenerateResponse)
def generate(req: GenerateRequest) -> GenerateResponse:
    # Validate incoming spec conforms to canonical schema before generation
    try:
        jsonschema_validate(instance=req.spec, schema=SCHEMA)
    except JsonSchemaValidationError as e:
        raise HTTPException(status_code=400, detail=f"Invalid spec: {e.message}")
    code = stub_generate_code(req.spec)
    return GenerateResponse(code=code)
@app.post("/generate_ops", response_model=GenerateOpsResponse)
def generate_ops(req: GenerateOpsRequest) -> GenerateOpsResponse:
    # Validate incoming spec
    try:
        jsonschema_validate(instance=req.spec, schema=SCHEMA)
    except JsonSchemaValidationError as e:
        raise HTTPException(status_code=400, detail=f"Invalid spec: {e.message}")
    # Stub: create a tests/ file with a minimal test
    goal = str(req.spec.get("goal", "task"))
    filename = "tests/test_generated.py"
    content = "\n".join([
        "# auto-generated test stub",
        f"def test_generated():",
        f"    assert {repr(goal)} is not None",
        "",
    ])
    return GenerateOpsResponse(ops=[{"action": "create", "path": filename, "content": content}])


spec_generator = SpecGenerator()
@app.post("/generate_taskspec")
def generate_taskspec(analysis_data: dict) -> dict:
    """Generate a TaskSpec from analysis data"""
    try:
        taskspec = spec_generator.cluster_signals_to_taskspec(analysis_data)
        # Validate against schema
        jsonschema_validate(instance=taskspec.dict(), schema=SCHEMA)
        return taskspec.dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"TaskSpec generation failed: {str(e)}")


@app.post("/generate_clarifying_questions")
def generate_clarifying_questions(taskspec_data: dict) -> dict:
    """Generate clarifying questions for a TaskSpec"""
    try:
        # Convert dict to TaskSpec
        taskspec = TaskSpec(**taskspec_data)
        questions = spec_generator.generate_clarifying_questions(taskspec)
        return {"questions": questions}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Question generation failed: {str(e)}")
@app.post("/enhance_taskspec")
def enhance_taskspec(request: dict) -> dict:
    """Enhance TaskSpec with answers to clarifying questions"""
    try:
        taskspec_data = request.get("taskspec", {})
        answers = request.get("answers", {})

        taskspec = TaskSpec(**taskspec_data)
        enhanced = spec_generator.enhance_taskspec_with_answers(taskspec, answers)

        # Validate enhanced spec
        jsonschema_validate(instance=enhanced.dict(), schema=SCHEMA)
        return enhanced.dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"TaskSpec enhancement failed: {str(e)}")


@app.post("/parse_constraints")
def parse_constraints(request: dict) -> dict:
    """Parse explicit constraints from a prompt"""
    try:
        prompt = request.get("prompt", "")
        parsed = spec_generator.parse_explicit_constraints(prompt)
        return parsed
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Constraint parsing failed: {str(e)}")


@app.get("/provider_stats")
def provider_stats() -> dict:
    """Get usage statistics for all providers"""
    return get_provider_stats()
@app.post("/generate_with_provider")
async def generate_with_provider_endpoint(request: dict) -> dict:
    """Generate content using the provider abstraction"""
    try:
        prompt = request.get("prompt", "")
        provider = request.get("provider")
        max_tokens = request.get("max_tokens", 1000)

        result = await generate_with_provider(
            prompt,
            provider_name=provider,
            max_tokens=max_tokens
        )

        return {"result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")


@app.get("/prompts")
def list_prompts(tags: Optional[str] = None) -> dict:
    """List available prompts"""
    tag_list = [tag.strip() for tag in tags.split(",")] if tags else None
    prompts = prompt_registry.list_prompts(tag_list)
    return {"prompts": [p.__dict__ for p in prompts]}


@app.get("/prompts/{prompt_id}")
def get_prompt(prompt_id: str) -> dict:
    """Get a specific prompt"""
    prompt = prompt_registry.get_prompt(prompt_id)
    if not prompt:
        raise HTTPException(status_code=404, detail=f"Prompt {prompt_id} not found")
    return prompt.__dict__


@app.post("/project_profile")
def set_project_profile(request: dict) -> dict:
    """Set the active profile for a project"""
    project_path = request.get("project_path", "")
    profile = request.get("profile", {})

    if not project_path:
        raise HTTPException(status_code=400, detail="project_path is required")

    prompt_registry.set_project_profile(project_path, profile)
    return {"status": "ok"}
@app.get("/project_profile")
def get_project_profile(project_path: str) -> dict:
    """Get the active profile for a project"""
    profile = prompt_registry.get_project_profile(project_path)
    active_prompt = prompt_registry.get_active_prompt_for_project(project_path)

    return {
        "profile": profile,
        "active_prompt": active_prompt.__dict__ if active_prompt else None
    }


@app.post("/build_project_graph")
def build_project_graph(request: dict) -> dict:
    """Build project graph from source code analysis"""
    project_root = request.get("project_root", ".")
    builder = ProjectGraphBuilder(project_root)
    graph = builder.build_graph()
    return graph


@app.post("/enrich_taskspec")
def enrich_taskspec_endpoint(request: dict) -> dict:
    """Enrich TaskSpec with RAG-retrieved information"""
    taskspec = request.get("taskspec", {})
    project_context = request.get("project_context", "current_project")

    enriched = rag_enrichment.enrich_taskspec(taskspec, project_context)
    return enriched


@app.post("/store_successful_taskspec")
def store_successful_taskspec(request: dict):
    """Store a successful TaskSpec for future RAG retrieval"""
    taskspec = request.get("taskspec", {})
    project = request.get("project", "current_project")

    rag_enrichment.store_successful_taskspec(taskspec, project)
    return {"status": "stored"}
@app.get("/rag_stats")
def get_rag_stats() -> dict:
    """Get RAG system statistics"""
    return rag_enrichment.get_rag_stats()


@app.post("/check_permission")
def check_permission(request: dict) -> dict:
    """Check permission for a tool"""
    tool_name = request.get("tool_name", "")
    session_id = request.get("session_id")
    reason = request.get("reason", "")

    if not tool_name:
        raise HTTPException(status_code=400, detail="tool_name is required")

    return permission_manager.request_permission(tool_name, reason, session_id)


@app.post("/grant_elevation")
def grant_elevation(request: dict) -> dict:
    """Grant temporary permission elevation"""
    session_id = request.get("session_id", "")
    tools = request.get("tools", [])
    duration_minutes = request.get("duration_minutes", 30)
    reason = request.get("reason", "")
    granted_by = request.get("granted_by", "user")

    if not session_id or not tools:
        raise HTTPException(status_code=400, detail="session_id and tools are required")

    elevation = permission_manager.grant_elevation(session_id, tools, duration_minutes, reason, granted_by)
    return {
        "session_id": elevation.session_id,
        "elevated_tools": elevation.elevated_tools,
        "expires_at": elevation.expires_at
    }


@app.post("/apply_edits")
def apply_edits(request: dict) -> dict:
    """Apply atomic edit operations"""
    operations_data = request.get("operations", [])

    operations = []
    for op_data in operations_data:
        from .edit_engine import EditOperation
        operations.append(EditOperation(**op_data))

    result = edit_engine.apply_edits(operations)

    return {
        "success": result.success,
        "operations_applied": len(result.operations),
        "error_message": result.error_message,
        "diff": result.diff
    }


@app.post("/create_ephemeral_branch")
def create_ephemeral_branch(request: dict) -> dict:
    """Create an ephemeral branch for edits"""
    description = request.get("description", "AEIOU ephemeral branch")

    try:
        branch_name = vcs_ops.create_ephemeral_branch(description)
        return {"branch_name": branch_name, "status": "created"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create branch: {str(e)}")


@app.post("/commit_ephemeral_branch")
def commit_ephemeral_branch(request: dict) -> dict:
    """Commit changes on ephemeral branch"""
    branch_name = request.get("branch_name", "")
    message = request.get("message", "AEIOU: Apply changes")

    if not branch_name:
        raise HTTPException(status_code=400, detail="branch_name is required")

    success = vcs_ops.commit_ephemeral_changes(branch_name, message)
    return {"success": success}


@app.get("/diff_narration")
def get_diff_narration(from_ref: str = "HEAD~1", to_ref: str = "HEAD") -> dict:
    """Get diffs with narration"""
    diffs = vcs_ops.get_diffs_with_narration(from_ref, to_ref)

    return {
        "diffs": [{
            "file_path": d.file_path,
            "additions": d.additions,
            "deletions": d.deletions,
            "narration": d.narration,
            "risk_level": d.risk_level
        } for d in diffs]
    }
@app.get("/permission_stats")
def get_permission_stats() -> dict:
    """Get permission system statistics"""
    return permission_manager.get_permission_stats()


@app.get("/health_detailed")
def get_detailed_health() -> dict:
    """Get detailed health status"""
    return health_monitor.get_health_status()


@app.get("/performance_report")
def get_performance_report() -> dict:
    """Get performance report"""
    return health_monitor.get_performance_report()


@app.get("/metrics_history")
def get_metrics_history(hours: int = 24) -> dict:
    """Get historical metrics"""
    return {"metrics": health_monitor.get_metrics_history(hours)}


@app.post("/start_monitoring")
def start_monitoring(interval: int = 60) -> dict:
    """Start health monitoring"""
    health_monitor.start_monitoring(interval)
    return {"status": "monitoring_started", "interval_seconds": interval}


@app.post("/stop_monitoring")
def stop_monitoring() -> dict:
    """Stop health monitoring"""
    health_monitor.stop_monitoring()
    return {"status": "monitoring_stopped"}















if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)


