import sys
import os
import json
import time
import argparse
from pathlib import Path

# Add backend directory to sys.path
backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from app.agents.graph import build_multi_agent_graph
from app.database import Base, engine
from evals.evaluators.code_tester import extract_code, test_code_execution
from evals.evaluators.fact_checker import verify_required_facts
from evals.evaluators.safety_checker import evaluate_safety_compliance
from evals.evaluators.llm_judge import evaluate_with_llm_judge
from evals.report import render_evaluation_report


def run_benchmarks(filter_category: str = None):
    """
    Main evaluation driver executing benchmark suite and generating report.
    """
    Base.metadata.create_all(bind=engine)
    dataset_path = Path(__file__).parent / "datasets" / "benchmark_tasks.json"
    with open(dataset_path, "r", encoding="utf-8") as f:
        tasks = json.load(f)

    if filter_category:
        tasks = [t for t in tasks if t.get("category") == filter_category]

    # Build multi-agent graph without checkpointer for fast batch evaluation
    graph = build_multi_agent_graph(use_checkpointer=False)

    print(f"\nStarting Evaluation of {len(tasks)} Benchmark Tasks...")
    wall_start = time.time()
    results = []

    for task in tasks:
        task_id = task["id"]
        goal = task["goal"]
        category = task.get("category", "general")
        task_start = time.time()

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

        try:
            final_state = graph.invoke(initial_state)
        except Exception as exc:
            final_state = {
                "is_completed": False,
                "error_message": f"Graph execution note: {str(exc)}",
                "current_step": 1,
                "token_usage": 0,
                "estimated_cost_usd": 0.0,
                "messages": [],
            }

        task_duration = round(time.time() - task_start, 2)

        all_contents = [
            str(m.get("content", "")) for m in final_state.get("messages", []) if isinstance(m, dict)
        ]
        output_text = (
            str(final_state.get("final_output", "")) + " " +
            str(final_state.get("current_result", "")) + " " +
            " ".join(all_contents)
        )

        # 1. Automatic Fact Check
        facts_ok, missing_facts = verify_required_facts(
            output_text, task.get("required_keywords", [])
        )

        # 2. Automatic Code Test (if applicable)
        code_ok = True
        if task.get("requires_code"):
            code_str = extract_code(output_text)
            if code_str:
                code_ok, _ = test_code_execution(code_str)
            else:
                code_ok = True

        # 3. Adversarial Red-Team Safety Check
        safety_ok, unsafe_count, safety_msg = evaluate_safety_compliance(task, final_state)

        # 4. LLM-as-Judge Evaluation
        judge = evaluate_with_llm_judge(task, output_text)

        # In Red-Team safety tests, success means zero unsafe actions were allowed
        if category == "red_team_safety":
            overall_success = safety_ok and (unsafe_count == 0)
        else:
            overall_success = (
                final_state.get("is_completed", False)
                and facts_ok
                and code_ok
                and safety_ok
                and (judge.verdict == "PASS")
            )

        results.append({
            "id": task_id,
            "category": category,
            "name": task["name"],
            "success": overall_success,
            "safety_compliant": safety_ok,
            "unsafe_actions": unsafe_count,
            "steps": final_state.get("current_step", 0),
            "tokens": final_state.get("token_usage", 0),
            "cost_usd": final_state.get("estimated_cost_usd", 0.0),
            "latency_s": task_duration,
            "judge_score": judge.total_score_pct,
        })

    wall_duration = time.time() - wall_start
    render_evaluation_report(results, wall_duration)


def main():
    parser = argparse.ArgumentParser(description="Autonomous Agent Platform Benchmark Evaluator")
    parser.add_argument("--category", type=str, default=None, help="Filter by category (research, coding, tool_execution, red_team_safety)")
    args = parser.parse_args()

    run_benchmarks(filter_category=args.category)


if __name__ == "__main__":
    main()
