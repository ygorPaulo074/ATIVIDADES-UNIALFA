from invoke import task
from pathlib import Path
import shutil
import subprocess
import sys
import os
import json

ROOT = Path(__file__).resolve().parent


# ── Helpers ────────────────────────────────────────────────────────────────────

def _read_data_path() -> Path:
    env_file = ROOT / ".env"
    data_path = ROOT / "data"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if line.startswith("DATA_PATH="):
                val = line.split("=", 1)[1].strip()
                if val:
                    data_path = Path(val)
                break
    return data_path


def _clear_agents(data_path: Path) -> None:
    agents_path = data_path / "agents"
    if not agents_path.exists():
        print(f"[clear] Nothing to clear at {agents_path}")
        return
    try:
        shutil.rmtree(agents_path)
        agents_path.mkdir(parents=True)
        print(f"[clear] Cleared: {agents_path}")
    except Exception as e:
        print(f"[clear] Error: {e}", file=sys.stderr)


def _ensure_initialized() -> bool:
    flag = ROOT / ".initialized"
    if not flag.exists():
        flag.write_text("invoke")
        return True
    return False


# ── Tasks ──────────────────────────────────────────────────────────────────────

@task
def setup(c):
    """Run the interactive configuration wizard."""
    import sys
    sys.path.insert(0, str(ROOT))
    from tools.setup import run_setup
    run_setup()


@task
def run(c):
    """Start the FastAPI server with uvicorn in reload mode."""
    if not (ROOT / ".env").exists():
        print("[run] .env not found. Run 'python tools/setup.py' first.")
        sys.exit(1)
    _ensure_initialized()
    port = os.getenv("PORT", "8000")
    c.run(f"uvicorn main:app --reload --host 0.0.0.0 --port {port}", pty=True)


@task(help={"args": "Extra arguments for pytest (e.g. -k test_agent)"})
def test(c, args=""):
    """Run the test suite and clean up generated data afterwards."""
    flag = ROOT / ".initialized"
    flag_created = not flag.exists()
    if flag_created:
        flag.write_text("invoke test")

    cmd = ["python", "-m", "pytest", "tests/", "-v", "--tb=short"]
    if args:
        cmd += args.split()

    try:
        result = subprocess.run(cmd, cwd=str(ROOT))
    finally:
        if flag_created and flag.exists():
            flag.unlink()
        _clear_agents(_read_data_path())

    sys.exit(result.returncode)


@task(help={"path": "Alternative path to the data directory"})
def clear(c, path=None):
    """Clear development data (data/agents/)."""
    data_path = Path(path) if path else _read_data_path()
    _clear_agents(data_path)


@task
def lint(c):
    """Check code with ruff (install with: pip install ruff)."""
    c.run("ruff check src/ --statistics", warn=True)


@task
def docker_build(c):
    """Build the Docker image tagged with the current VERSION."""
    if not (ROOT / "Dockerfile").exists():
        print("[docker-build] Dockerfile not found. Run 'invoke setup' and choose Docker.")
        return
    version = (ROOT / "VERSION").read_text().strip() if (ROOT / "VERSION").exists() else "latest"
    c.run(f"docker build -t ai-chatbot-api:{version} .", pty=True)


@task(help={"agent_id": "Agent ID (reads from data/agents/{id}/context/current.json)"})
def prompt(c, agent_id):
    """Print the current system prompt for an agent from the local driver."""
    sys.path.insert(0, str(ROOT))
    from src.domain.agent import AgentContextRecord
    from src.application.context_builder import build_system_prompt

    data_path = _read_data_path()
    context_file = data_path / "agents" / agent_id / "context" / "current.json"

    if not context_file.exists():
        print(f"[prompt] Context not found: {context_file}")
        sys.exit(1)

    record = AgentContextRecord.model_validate_json(context_file.read_text())
    result = build_system_prompt(record.context)

    print("\n" + "─" * 60)
    print(f"  System prompt — agent: {agent_id}  (v{record.version})")
    print("─" * 60)
    print(result)
    print("─" * 60 + "\n")


@task(help={"file": "Path to a JSON file with AgentContext fields (omitted fields default to None)"})
def prompt_preview(c, file):
    """Print the system prompt from a context JSON file."""
    sys.path.insert(0, str(ROOT))
    from src.domain.agent import AgentContextBase
    from src.application.context_builder import build_system_prompt

    json_path = Path(file)
    if not json_path.exists():
        print(f"[prompt-preview] File not found: {json_path}")
        sys.exit(1)

    data = json.loads(json_path.read_text())
    context = AgentContextBase.model_validate(data)
    result = build_system_prompt(context)

    print("\n" + "─" * 60)
    print(f"  System prompt preview — {json_path.name}")
    print("─" * 60)
    print(result)
    print("─" * 60 + "\n")


@task(help={
    "iterations": "Timed runs per scenario, warm-up excluded (default: 5)",
    "real_ai": "Make actual LiteLLM calls (requires AI_API_KEY + AI_MODEL in .env)",
})
def benchmark(c, iterations=5, real_ai=False):
    """Measure pipeline latency (sanitize_pii + spellcheck + optional AI) across 5 scenarios."""
    cmd = f"python tools/latency_benchmark.py --iterations {iterations}"
    if real_ai:
        cmd += " --real-ai"
    c.run(cmd, pty=True)


@task
def purge(c, days=7):
    """Hard-delete agents and sessions soft-deleted more than N days ago (default: 7)."""
    import sys
    sys.path.insert(0, str(ROOT))
    _ensure_initialized()
    from datetime import datetime, timezone, timedelta
    from src.infrastructure.persistence.factory import get_driver

    cutoff = (datetime.now(timezone.utc) - timedelta(days=int(days))).isoformat()
    try:
        result = get_driver().purge_deleted(before=cutoff)
        print(f"[purge] Agents hard-deleted: {result['agents_purged']}")
        print(f"[purge] Sessions hard-deleted: {result['sessions_purged']}")
    except NotImplementedError:
        print("[purge] Current driver does not support purge.", file=sys.stderr)
        sys.exit(1)
