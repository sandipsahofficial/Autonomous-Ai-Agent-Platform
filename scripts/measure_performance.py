import time
import statistics
import platform
import os
from concurrent.futures import ThreadPoolExecutor
from fastapi.testclient import TestClient

from app.main import app
from app.database import Base, SessionLocal, engine
from app.models.task import Task, TaskStatus
from app.models.document import Document, DocumentChunk
from app.auth.security import create_access_token

client = TestClient(app)

def benchmark_endpoint(name: str, fn, sample_count: int = 50):
    latencies = []
    for _ in range(sample_count):
        t0 = time.perf_counter()
        fn()
        t1 = time.perf_counter()
        latencies.append((t1 - t0) * 1000.0) # ms

    latencies.sort()
    avg_l = statistics.mean(latencies)
    p50_l = statistics.median(latencies)
    p95_idx = min(int(len(latencies) * 0.95), len(latencies) - 1)
    p95_l = latencies[p95_idx]
    min_l = min(latencies)
    max_l = max(latencies)

    return {
        "name": name,
        "samples": sample_count,
        "avg_ms": round(avg_l, 2),
        "p50_ms": round(p50_l, 2),
        "p95_ms": round(p95_l, 2),
        "min_ms": round(min_l, 2),
        "max_ms": round(max_l, 2),
    }

def run_performance_suite():
    print("=" * 80)
    print("MESH AGENT OS - STAGE 10 PERFORMANCE AND RESOURCE BENCHMARK")
    print("=" * 80)

    # System telemetry
    uname = platform.uname()
    cpu_count = os.cpu_count() or 4

    print(f"Host OS: {uname.system} {uname.release} (Build {uname.version})")
    print(f"Architecture: {uname.machine}")
    print(f"Processor: {platform.processor() or 'x86_64 Compatible'}")
    print(f"Logical CPUs: {cpu_count}")
    print("-" * 80)

    token = create_access_token({"sub": "sandip_sah", "role": "admin"})
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Health Endpoint
    def check_health():
        res = client.get("/health")
        assert res.status_code == 200

    r_health = benchmark_endpoint("GET /health (Liveness)", check_health, 50)

    # 2. Database Task Listing
    def list_tasks():
        res = client.get("/api/v1/tasks?limit=20", headers=headers)
        if res.status_code != 200:
            print(f"Error list_tasks: {res.status_code} {res.text}")
        assert res.status_code == 200

    r_tasks = benchmark_endpoint("GET /api/v1/tasks (DB Listing)", list_tasks, 50)

    # 3. Mission Creation (FastAPI route overhead with non-blocking worker)
    mission_counter = 0
    from unittest.mock import patch
    def create_mission():
        nonlocal mission_counter
        mission_counter += 1
        req_headers = {**headers, "X-Forwarded-For": f"10.10.1.{mission_counter}"}
        with patch("app.api.tasks.run_agent_task_background", return_value=None):
            res = client.post("/api/v1/tasks", json={"goal": f"Perf test mission #{mission_counter}"}, headers=req_headers)
            assert res.status_code == 201

    r_create = benchmark_endpoint("POST /api/v1/tasks (Mission Ingestion)", create_mission, 25)

    # 4. SSE Stream Connect
    def sse_connect():
        # Get latest task id
        res = client.get("/api/v1/tasks?limit=1", headers=headers)
        if res.status_code == 200 and res.json().get("tasks"):
            tid = res.json()["tasks"][0]["id"]
            with client.stream("GET", f"/api/v1/tasks/{tid}/events/stream", headers=headers) as stream_resp:
                assert stream_resp.status_code == 200
                # Read initial event/comment
                for line in stream_resp.iter_lines():
                    if line:
                        break

    r_sse = benchmark_endpoint("GET /tasks/{id}/events/stream (SSE)", sse_connect, 10)

    # 5. Document Retrieval
    def search_docs():
        res = client.post("/api/v1/documents/search", json={"query": "security guardrails", "limit": 3}, headers=headers)
        assert res.status_code == 200

    r_docs = benchmark_endpoint("POST /api/v1/documents/search (Citation Retrieval)", search_docs, 30)

    # 6. Concurrent Read-Only Requests (10 concurrent threads)
    concurrency = 10
    total_reqs = 100
    t_start = time.perf_counter()
    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = [executor.submit(client.get, "/health") for _ in range(total_reqs)]
        for f in futures:
            resp = f.result()
            assert resp.status_code == 200
    total_time = time.perf_counter() - t_start
    throughput_rps = round(total_reqs / total_time, 1)

    results = [r_health, r_tasks, r_create, r_sse, r_docs]

    print(f"{'Endpoint / Operation':<35} | {'Samples':<7} | {'Avg (ms)':<9} | {'P50 (ms)':<9} | {'P95 (ms)':<9} | {'Min/Max (ms)'}")
    print("-" * 80)
    for r in results:
        print(f"{r['name']:<35} | {r['samples']:<7} | {r['avg_ms']:<9} | {r['p50_ms']:<9} | {r['p95_ms']:<9} | {r['min_ms']}/{r['max_ms']}")
    print("-" * 80)
    print(f"Concurrent Load Test ({concurrency} workers, {total_reqs} requests): {throughput_rps} req/sec in {round(total_time, 3)}s")
    print("=" * 80)

if __name__ == "__main__":
    run_performance_suite()
