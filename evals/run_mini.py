import sys
import os
import json
import time
from pathlib import Path

# Add backend directory to sys.path
backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from app.agents.graph import build_multi_agent_graph


def run_mini_benchmark():
    """
    Executes the 5-task benchmark against the multi-agent graph.
    Logs step counts, token usage, cost, and verifies success criteria.
    """
    dataset_path = Path(__file__).parent / "datasets" / "mini_tasks.json"
    with open(dataset_path, "r", encoding="utf-8") as f:
        tasks = json.load(f)

    # Compile graph for mini-eval
    graph = build_multi_agent_graph()

    print("\n" + "=" * 88)
    print("RUNNING 5-TASK MULTI-AGENT MINI-EVALUATION BENCHMARK")
    print("=" * 88)

    results = []
    total_tokens = 0
    total_cost = 0.0

    for task in tasks:
        task_id = task["id"]
        goal = task["goal"]
        start_time = time.time()
        config = {"configurable": {"thread_id": task_id}}

        initial_state = {
            "task_id": task_id,
            "goal": goal,
            "current_step": 0,
            "max_steps": 15,
            "max_rework_attempts": 3,
            "token_usage": 0,
            "estimated_cost_usd": 0.0,
            "messages": [],
            "subtasks": [],
            "current_subtask_index": 0,
            "is_completed": False,
        }

        final_state = graph.invoke(initial_state, config=config)
        latency = round(time.time() - start_time, 2)

        output_text = (
            str(final_state.get("final_output", "")) + " " +
            str(final_state.get("current_result", ""))
        ).lower()

        # Check required keywords
        passed_keywords = all(
            kw.lower() in output_text for kw in task.get("required_keywords", [])
        )
        success = final_state.get("is_completed", False) and passed_keywords

        steps = final_state.get("current_step", 0)
        tokens = final_state.get("token_usage", 0)
        cost = final_state.get("estimated_cost_usd", 0.0)

        total_tokens += tokens
        total_cost += cost

        results.append({
            "id": task_id,
            "name": task["name"],
            "success": success,
            "steps": steps,
            "tokens": tokens,
            "cost_usd": cost,
            "latency_s": latency,
        })

    # Print summary table
    print(f"\n{'ID':<8} | {'Task Name':<32} | {'Status':<6} | {'Steps':<5} | {'Tokens':<7} | {'Cost ($)':<8} | {'Latency'}")
    print("-" * 88)
    for r in results:
        status_str = "PASS" if r["success"] else "FAIL"
        print(f"{r['id']:<8} | {r['name']:<32} | {status_str:<6} | {r['steps']:<5} | {r['tokens']:<7} | ${r['cost_usd']:<7.4f} | {r['latency_s']}s")

    pass_count = sum(1 for r in results if r["success"])
    print("=" * 88)
    print(f"Summary: {pass_count}/{len(tasks)} Passed ({(pass_count/len(tasks))*100:.1f}%)")
    print(f"Total Cumulative Tokens: {total_tokens} | Total Cost: ${total_cost:.4f}\n")


if __name__ == "__main__":
    run_mini_benchmark()
