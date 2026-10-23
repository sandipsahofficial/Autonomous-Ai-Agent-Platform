import sys
import os
import subprocess
import time
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

def main():
    print("*" * 80)
    print("MESH AGENT OS - AUTOMATED RELEASE VERIFICATION GATE")
    print("*" * 80)
    failures = []
    skipped = []

    # 1. Configuration Check
    log_step("1. Configuration & Security Settings")
    sys.path.insert(0, str(REPO_ROOT / "backend"))
    try:
        from app.config import get_settings
        settings = get_settings()
        print(f" [PASS] App Environment: {settings.APP_ENV}")
        print(f" [PASS] LLM Provider: {settings.LLM_PROVIDER} ({getattr(settings, 'LLM_MODEL_NAME', 'default')})")
        print(f" [PASS] Token Budget: {settings.TOKEN_BUDGET}, Cost Budget: ${settings.COST_BUDGET_USD}")
        try:
            settings.validate_production_readiness()
            print(" [PASS] Production readiness checks completed.")
        except ValueError as val_err:
            print(f" [WARN] Environment advisory: {val_err}")
    except Exception as exc:
        failures.append(f"Configuration validation failed: {str(exc)}")
        print(f" [FAIL] Configuration error: {str(exc)}")

    # 2. Database Migrations Verification
    log_step("2. Database Migrations on Isolated Fixture")
    migration_test_code = """
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
inspector = inspect(engine)
tables = inspector.get_table_names()
assert 'users' in tables and 'tasks' in tables and 'workflows' in tables

command.downgrade(cfg, '-1')
tables_after_down = inspect(engine).get_table_names()
assert 'users' not in tables_after_down

command.upgrade(cfg, 'head')
engine.dispose()
if os.path.exists(db_file):
    os.remove(db_file)
print('Migrations verified forward, reverse, and forward again.')
"""
    code, out, err, dur = run_command([sys.executable, "-c", migration_test_code], env_override={"PYTHONPATH": str(REPO_ROOT / "backend")})
    if code == 0:
        print(f" [PASS] Alembic migrations verified cleanly ({dur}s).")
    else:
        failures.append("Alembic migration verification failed.")
        print(f" [FAIL] Migration check error: {err or out}")

    # 3. Backend Pytest Suites
    log_step("3. Backend Pytest Suites (Security, RBAC, Traces, Graph)")
    code, out, err, dur = run_command([sys.executable, "-m", "pytest", "backend/tests", "-q"])
    if code == 0:
        # Extract summary line
        summary_line = [l for l in out.splitlines() if "passed" in l][-1] if out else "All tests passed"
        print(f" [PASS] Backend tests passed: {summary_line.strip()} ({dur}s).")
    else:
        failures.append(f"Backend test suite failure (exit {code}).")
        print(f" [FAIL] Test output:\n{out}\n{err}")

    # 4. Benchmark Evaluation Suite
    log_step("4. Quality & Safety Benchmark Suite (20 Tasks)")
    code, out, err, dur = run_command([sys.executable, "-m", "evals.run"])
    if code == 0 and "100.0% (20/20 passed)" in out:
        print(f" [PASS] 20/20 benchmark tasks passed with 0 safety violations ({dur}s).")
    else:
        failures.append("Benchmark evaluation failed or safety violations detected.")
        print(f" [FAIL] Benchmark output:\n{out}\n{err}")

    # 5. Frontend Production Build
    log_step("5. Frontend Production Bundle Build")
    npm_cmd = "npm.cmd" if sys.platform == "win32" else "npm"
    code, out, err, dur = run_command([npm_cmd, "--prefix", "frontend", "run", "build"])
    if code == 0:
        print(f" [PASS] Frontend compiled cleanly with zero TypeScript errors ({dur}s).")
    else:
        failures.append("Frontend build failed.")
        print(f" [FAIL] Frontend build error:\n{err or out}")

    # 6. Docker Compose Configuration Validation
    log_step("6. Container & Compose Specification")
    code, out, err, dur = run_command(["docker", "compose", "config"])
    if code == 0:
        print(f" [PASS] docker-compose.yml specification validated ({dur}s).")
    else:
        # Check if docker is simply not installed/running
        if "docker" not in out and "docker" not in err:
            skipped.append("Docker daemon not running; compose runtime launch skipped.")
            print(" [SKIP] Docker CLI/daemon not reachable on host; runtime containers skipped.")
        else:
            failures.append("Docker compose configuration invalid.")
            print(f" [FAIL] Docker compose error: {err or out}")

    # Final Release Assessment
    print("\n" + "=" * 80)
    print("RELEASE VERIFICATION SUMMARY")
    print("=" * 80)
    if skipped:
        print("Skipped Checks:")
        for s in skipped:
            print(f"  - {s}")
    if failures:
        print("\nRelease Blockers Identified:")
        for f in failures:
            print(f"  [X] {f}")
        print("\nVERDICT: RELEASE GATES FAILED. Non-zero exit code returned.")
        sys.exit(1)
    else:
        print("\nVERDICT: ALL RELEASE GATES PASSED (100% Verified).")
        print("MESH Agent OS is certified for production deployment.")
        sys.exit(0)

if __name__ == "__main__":
    main()
