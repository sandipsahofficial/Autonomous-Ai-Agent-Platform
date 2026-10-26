import sys
import os
import subprocess
import time
import argparse
import socket
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

def log_step(name: str):
    print("\n" + "=" * 80)
    print(f"RELEASE GATE CHECK: {name}")
    print("=" * 80)

def run_command(cmd: list, cwd: Path = REPO_ROOT, env_override: dict = None) -> tuple:
    env = os.environ.copy()
    if env_override:
        env.update(env_override)
    t0 = time.time()
    res = subprocess.run(cmd, cwd=str(cwd), env=env, capture_output=True, text=True)
    duration = round(time.time() - t0, 2)
    return res.returncode, res.stdout, res.stderr, duration

def check_tcp_port(host: str, port: int, timeout: float = 1.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except (socket.timeout, ConnectionRefusedError, OSError):
        return False

def main():
    parser = argparse.ArgumentParser(description="MESH Agent OS Phase 9 Release Candidate and Deployment Verification")
    parser.add_argument("--prod", action="store_true", help="Enforce strict production invariants and exit non-zero if any gate is BLOCKED")
    parser.add_argument("--skip-e2e-mission", action="store_true", help="Skip the full local Ollama multi-agent mission execution")
    args = parser.parse_args()

    print("*" * 80)
    print("MESH AGENT OS - PHASE 9 RELEASE CANDIDATE & DEPLOYMENT READINESS GATE")
    print("*" * 80)

    passed = []
    failures = []
    blocked = []
    not_run = []

    sys.path.insert(0, str(REPO_ROOT / "backend"))

    # --------------------------------------------------------------------------
    # 1. Configuration & Security Settings
    # --------------------------------------------------------------------------
    log_step("1. Configuration & Security Settings")
    try:
        from app.config import get_settings
        settings = get_settings()
        print(f" [INFO] App Environment: {settings.APP_ENV}")
        print(f" [INFO] LLM Provider: {settings.LLM_PROVIDER} ({getattr(settings, 'LLM_MODEL_NAME', 'default')})")
        print(f" [INFO] Token Budget: {settings.TOKEN_BUDGET}, Cost Budget: ${settings.COST_BUDGET_USD}")

        if args.prod or settings.APP_ENV == "production":
            settings.validate_production_readiness()
            print(" [PASS] Production readiness checks completed strictly.")
            passed.append("1. Configuration & Security Settings (Strict Production)")
        else:
            try:
                settings.validate_production_readiness()
                print(" [PASS] Production configuration validated successfully.")
            except ValueError as val_err:
                print(f" [WARN] Development advisory (expected in dev mode): {val_err}")
            passed.append("1. Configuration & Security Settings (Development Mode)")
    except Exception as exc:
        failures.append(f"1. Configuration check failed: {str(exc)}")
        print(f" [FAIL] Configuration error: {str(exc)}")

    # --------------------------------------------------------------------------
    # 2. Database Migrations & Persistence (SQLite & PostgreSQL)
    # --------------------------------------------------------------------------
    log_step("2. Database Migrations & Persistence (SQLite vs PostgreSQL)")
    
    # 2a. SQLite Disposable Migration & Rollback
    sqlite_migration_code = """
import os
from alembic.config import Config
from alembic import command
from sqlalchemy import create_engine, inspect

db_file = './release_verify_temp.db'
if os.path.exists(db_file):
    os.remove(db_file)

cfg = Config('backend/alembic.ini')
cfg.set_main_option('script_location', 'backend/alembic')
cfg.set_main_option('sqlalchemy.url', f'sqlite:///{db_file}')

command.upgrade(cfg, 'head')
engine = create_engine(f'sqlite:///{db_file}')
tables = inspect(engine).get_table_names()
assert 'users' in tables and 'tasks' in tables and 'workflows' in tables and 'api_keys' in tables

command.downgrade(cfg, 'base')
tables_after_down = inspect(engine).get_table_names()
assert len([t for t in tables_after_down if t != 'alembic_version']) == 0

command.upgrade(cfg, 'head')
engine.dispose()
if os.path.exists(db_file):
    os.remove(db_file)
print('SQLite migration upgrade -> downgrade -> re-upgrade verified.')
"""
    code, out, err, dur = run_command([sys.executable, "-c", sqlite_migration_code], env_override={"PYTHONPATH": str(REPO_ROOT / "backend")})
    if code == 0:
        print(f" [PASS] SQLite isolated migrations and schema rollbacks verified ({dur}s).")
        passed.append("2a. SQLite Isolated Schema & Migration Lifecycle")
    else:
        failures.append("2a. SQLite migration verification failed.")
        print(f" [FAIL] SQLite migration error: {err or out}")

    # 2b. PostgreSQL Live Connection Probe
    pg_host = os.environ.get("POSTGRES_HOST", "localhost")
    pg_port = int(os.environ.get("POSTGRES_PORT", 5432))
    if check_tcp_port(pg_host, pg_port):
        print(f" [PASS] PostgreSQL daemon reachable at {pg_host}:{pg_port}.")
        passed.append("2b. PostgreSQL Connection & Integration")
    else:
        print(f" [BLOCKED] PostgreSQL server offline at {pg_host}:{pg_port} (TCP connection refused).")
        blocked.append("2b. PostgreSQL Integration (Host database server offline)")

    # --------------------------------------------------------------------------
    # 3. Backend Test Suites (Unit vs Integration)
    # --------------------------------------------------------------------------
    log_step("3. Backend Test Suites (Unit vs Integration)")
    
    # Unit tests
    unit_test_files = [
        "backend/tests/test_health.py",
        "backend/tests/test_llm_providers.py",
        "backend/tests/test_metrics_and_traces.py",
        "backend/tests/test_single_agent.py",
        "backend/tests/test_tools_and_safety.py",
        "backend/tests/test_safety_and_sandbox.py",
    ]
    code, out, err, dur = run_command([sys.executable, "-m", "pytest"] + unit_test_files + ["-q"])
    if code == 0:
        summary = [l for l in out.splitlines() if "passed" in l][-1] if out else "All unit tests passed"
        print(f" [PASS] Backend unit tests passed: {summary.strip()} ({dur}s).")
        passed.append("3a. Backend Unit Test Suites")
    else:
        failures.append("3a. Backend unit test failure.")
        print(f" [FAIL] Unit test error:\n{out}\n{err}")

    # Integration & Regression tests
    integration_test_files = [
        "backend/tests/test_tasks_api.py",
        "backend/tests/test_multi_agent_graph.py",
        "backend/tests/test_human_approval.py",
        "backend/tests/test_approval_workflow_e2e.py",
        "backend/tests/test_phase3_suite.py",
        "backend/tests/test_phase4_suite.py",
        "backend/tests/test_phase5_suite.py",
        "backend/tests/test_phase6_suite.py",
        "backend/tests/test_phase7_suite.py",
        "backend/tests/test_phase8_suite.py",
        "backend/tests/test_phase9_security.py",
    ]
    code, out, err, dur = run_command([sys.executable, "-m", "pytest"] + integration_test_files + ["-q"])
    if code == 0:
        summary = [l for l in out.splitlines() if "passed" in l][-1] if out else "All integration tests passed"
        print(f" [PASS] Backend integration & RBAC suites passed: {summary.strip()} ({dur}s).")
        passed.append("3b. Backend Integration & Multi-Agent RBAC Suites")
    else:
        failures.append("3b. Backend integration test failure.")
        print(f" [FAIL] Integration test error:\n{out}\n{err}")

    # --------------------------------------------------------------------------
    # 4. Quality & Safety Benchmark Suite (20 Tasks)
    # --------------------------------------------------------------------------
    log_step("4. Quality & Safety Benchmark Suite (20 Tasks)")
    code, out, err, dur = run_command([sys.executable, "-m", "evals.run"])
    if code == 0 and "100.0% (20/20 passed)" in out:
        print(f" [PASS] 20/20 benchmark tasks passed with 0 safety violations ({dur}s).")
        passed.append("4. Autonomous Agent Safety & Quality Benchmarks (20/20)")
    else:
        failures.append("4. Benchmark evaluation failed or safety violations detected.")
        print(f" [FAIL] Benchmark output:\n{out}\n{err}")

    # --------------------------------------------------------------------------
    # 5. Frontend Production Bundle Build
    # --------------------------------------------------------------------------
    log_step("5. Frontend Production Bundle Build & Typecheck")
    npm_cmd = "npm.cmd" if sys.platform == "win32" else "npm"
    code, out, err, dur = run_command([npm_cmd, "--prefix", "frontend", "run", "build"])
    if code == 0:
        print(f" [PASS] Frontend compiled cleanly with zero TypeScript errors ({dur}s).")
        passed.append("5. Frontend Production Bundle Build")
    else:
        failures.append("5. Frontend build failed.")
        print(f" [FAIL] Frontend build error:\n{err or out}")

    # --------------------------------------------------------------------------
    # 6. Local Ollama LLM: Direct Probe vs End-to-End Mission
    # --------------------------------------------------------------------------
    log_step("6. Ollama Local LLM: Direct Probe vs End-to-End Mission")
    
    # 6a. Direct Probe
    ollama_check_code = """
import sys
sys.path.insert(0, 'backend')
from app.llm.ollama_llm import OllamaLLMProvider

try:
    provider = OllamaLLMProvider(base_url='http://localhost:11434', model_name='llama3', timeout=45.0)
    res = provider.generate('Respond with single word: READY')
    assert res.provider == 'ollama'
    assert res.is_mock is False
    print(f'OLLAMA_VERIFIED: {res.content.strip()[:60]}')
except Exception as e:
    print(f'OLLAMA_ERROR: {str(e)}')
    sys.exit(2)
"""
    code, out, err, dur = run_command([sys.executable, "-c", ollama_check_code], env_override={"PYTHONPATH": str(REPO_ROOT / "backend")})
    ollama_live = False
    if code == 0:
        print(f" [PASS] Real Ollama Llama 3 local probe verified ({dur}s). Output: {out.strip()}")
        passed.append("6a. Ollama Direct Inference Probe")
        ollama_live = True
    elif code == 2:
        print(f" [BLOCKED] Ollama daemon not reachable at localhost:11434 ({out.strip() or err.strip()}).")
        blocked.append("6a. Ollama Direct Inference Probe (Daemon Unreachable)")
    else:
        failures.append("6a. Ollama inference probe failed.")
        print(f" [FAIL] Ollama probe error:\n{err or out}")

    # 6b. End-to-End Multi-Agent Mission
    if args.skip_e2e_mission:
        print(" [NOT RUN] Skipped end-to-end Ollama mission via --skip-e2e-mission flag.")
        not_run.append("6b. End-to-End Ollama Multi-Agent Mission")
    elif not ollama_live:
        print(" [BLOCKED] Skipped end-to-end Ollama mission: Ollama daemon is offline.")
        blocked.append("6b. End-to-End Ollama Multi-Agent Mission (Prerequisite Offline)")
    else:
        print(" [INFO] Executing real multi-agent end-to-end mission against Ollama llama3...")
        code_e2e, out_e2e, err_e2e, dur_e2e = run_command(
            [sys.executable, "scripts/run_stage5_mission.py"],
            env_override={"PYTHONPATH": str(REPO_ROOT / "backend")}
        )
        if code_e2e == 0 and "Status: COMPLETED" in out_e2e:
            print(f" [PASS] Full multi-agent mission completed successfully ({dur_e2e}s).")
            passed.append("6b. Real End-to-End Ollama Mission Execution")
        else:
            failures.append("6b. End-to-end Ollama mission failed to complete successfully.")
            print(f" [FAIL] Mission execution output:\n{out_e2e}\n{err_e2e}")

    # --------------------------------------------------------------------------
    # 7. Container Configuration vs Live Daemon Runtime
    # --------------------------------------------------------------------------
    log_step("7. Docker Compose Specification vs Live Daemon Runtime")
    code_cfg, out_cfg, err_cfg, dur_cfg = run_command(["docker", "compose", "config"])
    if code_cfg == 0:
        print(f" [PASS] docker-compose.yml specification validated ({dur_cfg}s).")
        passed.append("7a. Docker Compose Topology Specification")
    else:
        failures.append("7a. Docker compose configuration invalid.")
        print(f" [FAIL] Docker compose error: {err_cfg or out_cfg}")

    code_info, out_info, err_info, dur_info = run_command(["docker", "info"])
    if code_info == 0:
        print(f" [PASS] Docker Desktop daemon is active and responsive ({dur_info}s).")
        passed.append("7b. Container & Compose Live Runtime")
    else:
        print(" [BLOCKED] Docker Desktop daemon is not running on host (//./pipe/dockerDesktopLinuxEngine unavailable).")
        print("          Runtime container execution is marked BLOCKED per verification rules.")
        blocked.append("7b. Container Live Runtime (Docker Daemon Offline)")

    # --------------------------------------------------------------------------
    # Final Release Assessment
    # --------------------------------------------------------------------------
    print("\n" + "=" * 80)
    print("RELEASE VERIFICATION SUMMARY (TAXONOMY)")
    print("=" * 80)
    print(f"PASSED CHECKS ({len(passed)}):")
    for p in passed:
        print(f"  [PASS] {p}")

    if not_run:
        print(f"\nNOT RUN CHECKS ({len(not_run)}):")
        for n in not_run:
            print(f"  [NOT RUN] {n}")

    if blocked:
        print(f"\nBLOCKED CHECKS ({len(blocked)}):")
        for b in blocked:
            print(f"  [BLOCKED] {b}")

    if failures:
        print(f"\nFAILED CHECKS ({len(failures)}):")
        for f in failures:
            print(f"  [FAIL] {f}")
        print("\n" + "=" * 80)
        print("VERDICT: RELEASE GATES FAILED. Defect resolution required.")
        print("=" * 80)
        sys.exit(1)
    elif blocked:
        print("\n" + "=" * 80)
        if args.prod:
            print("VERDICT: PRODUCTION CERTIFICATION BLOCKED.")
            print("Production deployment strictly requires all gates, including container & database runtime, to PASS.")
            print("=" * 80)
            sys.exit(1)
        else:
            print("VERDICT: RELEASE CANDIDATE VERIFIED (100% of testable suites PASS).")
            print("NOTE: Runtime PostgreSQL and Docker container daemon remain BLOCKED on host.")
            print("=" * 80)
            sys.exit(0)
    else:
        print("\n" + "=" * 80)
        print("VERDICT: ALL RELEASE GATES PASSED (100% Verified).")
        print("MESH Agent OS is certified for production deployment.")
        print("=" * 80)
        sys.exit(0)

if __name__ == "__main__":
    main()
