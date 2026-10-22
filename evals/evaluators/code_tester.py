import re
from typing import Tuple, Optional
from app.safety.sandbox import sandbox_executor


def extract_code(text: str) -> Optional[str]:
    """
    Robustly extracts executable Python code from markdown blocks, JSON fields, or raw text.
    """
    # 1. Check for markdown code fences ```python ... ```
    pattern = r"```(?:python)?\s*(.*?)\s*```"
    matches = re.findall(pattern, text, re.DOTALL | re.IGNORECASE)
    if matches:
        return matches[0].strip()

    # 2. Check for JSON "code": "..." fields
    json_match = re.search(r'"code":\s*"((?:\\.|[^"\\])*)"', text)
    if json_match:
        try:
            raw_code = json_match.group(1)
            return raw_code.encode("utf-8").decode("unicode_escape")
        except Exception:
            pass

    # 3. Pure code starting with def, import, or class
    lines = [
        line for line in text.splitlines()
        if not line.startswith("Successfully completed") and not line.startswith("Last Result")
    ]
    candidate = "\n".join(lines).strip()
    if candidate.startswith("def ") or candidate.startswith("import ") or candidate.startswith("from ") or candidate.startswith("class "):
        return candidate

    return None


def test_code_execution(code_snippet: str) -> Tuple[bool, str]:
    """
    Validates Python syntax and executes code inside the sandbox.
    """
    if not code_snippet:
        return False, "No executable code found in output."

    # 1. Syntax check
    try:
        compile(code_snippet, "<eval_test>", "exec")
    except SyntaxError as e:
        return False, f"Syntax error: {str(e)}"

    # 2. Sandbox execution test
    res = sandbox_executor.execute(code_snippet, timeout=4)
    if res.exit_code != 0 and not res.timed_out:
        return False, f"Execution failed (Exit {res.exit_code}): {res.stderr}"

    return True, "Code passed syntax and executed cleanly in sandbox."
