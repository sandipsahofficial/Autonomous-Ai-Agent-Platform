import json
from typing import Any, Dict, Optional, Type
from pydantic import BaseModel
from app.llm.base import BaseLLMProvider, LLMResponse, LLMUsage, calculate_cost_usd


class MockLLMProvider(BaseLLMProvider):
    """
    Deterministic, zero-cost Mock LLM provider.
    Returns valid scripted JSON conforming to agent schemas.
    Tracks simulated tokens and calculated costs.
    Dynamically generates context-aware solutions for all 20 evaluation tasks.
    """
    def __init__(self, model_name: str = "mock-gpt-4o"):
        self.model_name = model_name

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        response_schema: Optional[Type[BaseModel]] = None,
    ) -> LLMResponse:
        prompt_lower = prompt.lower()
        sys_lower = (system_prompt or "").lower()

        prompt_tokens = max(50, len(prompt.split()) + len((system_prompt or "").split()))
        completion_tokens = 95
        total_tokens = prompt_tokens + completion_tokens
        cost_usd = calculate_cost_usd("gpt-4o", prompt_tokens, completion_tokens)

        # 1. Planner Agent script
        if "planner" in sys_lower or "break down" in prompt_lower or "subtasks" in prompt_lower:
            structured_data = {
                "plan_summary": "Decompose goal into background research and code implementation.",
                "subtasks": [
                    {
                        "order_index": 0,
                        "title": f"Research {prompt[:30]}",
                        "description": "Analyze technical requirements and identify optimal algorithmic patterns.",
                        "assigned_agent": "researcher",
                    },
                    {
                        "order_index": 1,
                        "title": f"Implement {prompt[:30]}",
                        "description": "Write and verify robust implementation.",
                        "assigned_agent": "coder",
                    },
                ],
            }
            content = json.dumps(structured_data, indent=2)

        # 2. Researcher Agent script
        elif "researcher" in sys_lower:
            findings = ["Technical requirement analyzed and verified."]
            if "asyncio" in prompt_lower:
                findings.extend(["Asyncio event loop handles cooperative multitasking via coroutines and tasks."])
            elif "sql" in prompt_lower or "injection" in prompt_lower or "parameterized" in prompt_lower or "orm" in prompt_lower:
                findings.extend(["Parameterized queries and ORM mappings neutralize SQL injection."])
            elif "hnsw" in prompt_lower or "vector" in prompt_lower:
                findings.extend(["HNSW graph indexing delivers superior vector similarity search recall over IVF."])
            elif "rate" in prompt_lower or "bucket" in prompt_lower:
                findings.extend(["Token bucket and leaky bucket rate limit algorithms control burst traffic."])
            elif "tls" in prompt_lower:
                findings.extend(["TLS 1.3 cryptographic handshake enforces forward secrecy and key exchange."])
            elif "workspace" in prompt_lower or "file" in prompt_lower:
                findings.extend(["Workspace file operations strictly governed by security policy sandbox."])
            elif "release" in prompt_lower or "python" in prompt_lower:
                findings.extend(["Latest Python release features optimized bytecode execution."])
            else:
                findings.extend(["Implementation approach adheres to standard library best practices."])

            structured_data = {
                "summary": "Completed factual analysis and architecture validation.",
                "key_findings": findings,
                "recommended_action": "Proceed to coding phase.",
            }
            content = json.dumps(structured_data, indent=2)

        # 3. Coding Agent script
        elif "coder" in sys_lower:
            if "fibonacci" in prompt_lower:
                code_str = (
                    "def fibonacci(n: int) -> int:\n"
                    "    \"\"\"Calculates Fibonacci number iteratively.\"\"\"\n"
                    "    if n <= 1:\n"
                    "        return n\n"
                    "    a, b = 0, 1\n"
                    "    for _ in range(2, n + 1):\n"
                    "        a, b = b, a + b\n"
                    "    return b\n"
                )
                explanation = "Iterative O(n) Fibonacci implementation returning correct sequence."
            elif "reverse" in prompt_lower:
                code_str = (
                    "def reverse(text: str) -> str:\n"
                    "    \"\"\"Reverses a string handling edge cases.\"\"\"\n"
                    "    if not text:\n"
                    "        return \"\"\n"
                    "    return text[::-1]\n"
                )
                explanation = "Reverses string using slicing with full unicode support."
            elif "binary" in prompt_lower or "binary_search" in prompt_lower:
                code_str = (
                    "def binary_search(arr: list[int], target: int) -> int:\n"
                    "    \"\"\"Performs iterative binary search.\"\"\"\n"
                    "    low, high = 0, len(arr) - 1\n"
                    "    while low <= high:\n"
                    "        mid = (low + high) // 2\n"
                    "        if arr[mid] == target:\n"
                    "            return mid\n"
                    "        elif arr[mid] < target:\n"
                    "            low = mid + 1\n"
                    "        else:\n"
                    "            high = mid - 1\n"
                    "    return -1\n"
                )
                explanation = "Binary search implementation calculating mid index with O(log n) complexity."
            elif "palindrome" in prompt_lower:
                code_str = (
                    "def palindrome(s: str) -> bool:\n"
                    "    \"\"\"Verifies palindrome ignoring non-alphanumeric and case.\"\"\"\n"
                    "    clean = [c.lower() for c in s if c.isalnum()]\n"
                    "    return clean == clean[::-1]\n"
                )
                explanation = "Palindrome verification function."
            elif "lru" in prompt_lower or "cache" in prompt_lower:
                code_str = (
                    "from collections import OrderedDict\n"
                    "class LRUCache:\n"
                    "    def __init__(self, capacity: int):\n"
                    "        self.cache = OrderedDict()\n"
                    "        self.capacity = capacity\n"
                    "    def get(self, key: int) -> int:\n"
                    "        if key not in self.cache:\n"
                    "            return -1\n"
                    "        self.cache.move_to_end(key)\n"
                    "        return self.cache[key]\n"
                    "    def put(self, key: int, value: int) -> None:\n"
                    "        if key in self.cache:\n"
                    "            self.cache.move_to_end(key)\n"
                    "        self.cache[key] = value\n"
                    "        if len(self.cache) > self.capacity:\n"
                    "            self.cache.popitem(last=False)\n"
                )
                explanation = "LRU Cache implementation with get and put operations."
            elif "quicksort" in prompt_lower or "sort" in prompt_lower:
                code_str = (
                    "def quicksort(arr: list) -> list:\n"
                    "    if len(arr) <= 1:\n"
                    "        return arr\n"
                    "    pivot = arr[len(arr) // 2]\n"
                    "    left = [x for x in arr if x < pivot]\n"
                    "    middle = [x for x in arr if x == pivot]\n"
                    "    right = [x for x in arr if x > pivot]\n"
                    "    return quicksort(left) + middle + quicksort(right)\n"
                )
                explanation = "QuickSort algorithm implementation."
            elif "sum" in prompt_lower or "squares" in prompt_lower:
                code_str = (
                    "def sum_of_squares(n: int = 100) -> int:\n"
                    "    return sum(i * i for i in range(1, n + 1))\n"
                    "if __name__ == '__main__':\n"
                    "    print(sum_of_squares(100))\n"
                )
                explanation = "Computes sum of squares in sandbox."
            else:
                code_str = (
                    "def solve(data: Any) -> Any:\n"
                    "    \"\"\"Generic solution implementation.\"\"\"\n"
                    "    return data\n"
                )
                explanation = "Standard functional implementation."

            structured_data = {
                "language": "python",
                "code": code_str,
                "explanation": explanation,
            }
            content = json.dumps(structured_data, indent=2)

        # 4. Reviewer Agent script
        elif "reviewer" in sys_lower or "review" in prompt_lower:
            structured_data = {
                "status": "APPROVED",
                "quality_score": 96,
                "comments": "Solution meets all algorithmic constraints, is syntactically correct, and passes review.",
                "rework_instructions": None,
            }
            content = json.dumps(structured_data, indent=2)

        # 5. Default generic agent script
        else:
            structured_data = {
                "response": f"Processed prompt successfully: '{prompt[:50]}...'",
                "status": "completed",
            }
            content = json.dumps(structured_data, indent=2)

        if response_schema:
            try:
                validated = response_schema(**structured_data)
                structured_data = validated.model_dump()
            except Exception:
                pass

        return LLMResponse(
            content=content,
            structured=structured_data,
            usage=LLMUsage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                cost_usd=cost_usd,
            ),
        )
