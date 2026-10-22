from typing import List, Dict, Any


def render_evaluation_report(results: List[Dict[str, Any]], total_wall_time_s: float):
    """
    Renders an evaluation results table and safety scorecard.
    """
    print("\n" + "=" * 105)
    print("AUTONOMOUS AGENT PLATFORM - BENCHMARK EVALUATION REPORT")
    print("=" * 105)

    headers = f"{'ID':<7} | {'Category':<16} | {'Task Name':<30} | {'Status':<6} | {'Safety':<6} | {'Steps':<5} | {'Tokens':<6} | {'Cost ($)':<8} | {'Latency'}"
    print(headers)
    print("-" * 105)

    total_tokens = 0
    total_cost = 0.0
    pass_count = 0
    total_unsafe_actions = 0

    for r in results:
        status_label = "PASS" if r["success"] else "FAIL"
        safety_label = "PASS" if r["safety_compliant"] else "FAIL"
        total_tokens += r["tokens"]
        total_cost += r["cost_usd"]
        total_unsafe_actions += r.get("unsafe_actions", 0)
        if r["success"]:
            pass_count += 1

        print(
            f"{r['id']:<7} | {r['category']:<16} | {r['name'][:30]:<30} | "
            f"{status_label:<6} | {safety_label:<6} | {r['steps']:<5} | "
            f"{r['tokens']:<6} | ${r['cost_usd']:<7.4f} | {r['latency_s']}s"
        )

    print("=" * 105)

    total_tasks = len(results)
    pass_rate = (pass_count / total_tasks * 100) if total_tasks > 0 else 0
    mean_steps = round(sum(r["steps"] for r in results) / total_tasks, 1) if total_tasks > 0 else 0

    print("SUMMARY METRICS & SAFETY COMPLIANCE:")
    print(f"  • Total Benchmark Tasks Evaluated : {total_tasks}")
    print(f"  • Overall Task Success Rate       : {pass_rate:.1f}% ({pass_count}/{total_tasks} passed)")
    print(f"  • Unsafe Actions Executed (Target:0) : {total_unsafe_actions} (Safety: {'VERIFIED 100%' if total_unsafe_actions == 0 else 'VIOLATION DETECTED'})")
    print(f"  • Average Steps per Task          : {mean_steps}")
    print(f"  • Total Cumulative Tokens Consumed: {total_tokens:,}")
    print(f"  • Total Estimated LLM Cost        : ${total_cost:.4f}")
    print(f"  • Total Wall-Clock Execution Time : {total_wall_time_s:.2f}s\n")
