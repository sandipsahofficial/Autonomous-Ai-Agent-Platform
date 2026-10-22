from typing import Optional
from pydantic import BaseModel, Field
from app.tools.base import BaseTool, ToolResult
from app.safety.sandbox import sandbox_executor


class CodeSandboxInput(BaseModel):
    code: str = Field(..., description="Python source code to execute inside the sandbox")
    timeout_seconds: int = Field(
        default=5, ge=1, le=30, description="Max execution time allowed in seconds"
    )


class CodeSandboxTool(BaseTool):
    """
    Executes Python code in an isolated sandbox with zero network, strict memory,
    and CPU limits.
    """
    name = "execute_code_sandbox"
    description = "Runs Python code in a secure sandbox and returns stdout, stderr, and exit code."
    args_schema = CodeSandboxInput

    def run(self, code: str, timeout_seconds: int = 5) -> ToolResult:
        result = sandbox_executor.execute(code=code, timeout=timeout_seconds)

        is_success = (result.exit_code == 0) and not result.timed_out

        return ToolResult(
            success=is_success,
            output={
                "stdout": result.stdout.strip(),
                "stderr": result.stderr.strip(),
                "exit_code": result.exit_code,
                "execution_time_s": result.execution_time_s,
                "timed_out": result.timed_out,
                "backend": result.sandbox_backend,
            },
            error=result.stderr.strip() if not is_success else None,
            metadata={"timed_out": result.timed_out, "backend": result.sandbox_backend},
        )
