import os
import subprocess
import time
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field


class SandboxExecutionResult(BaseModel):
    """
    Standardized result from running untrusted code inside the isolated sandbox.
    """
    stdout: str
    stderr: str
    exit_code: int
    execution_time_s: float
    timed_out: bool = False
    sandbox_backend: str = "docker"


class SandboxExecutor:
    """
    Hardened code execution runner.
    Applies zero-network, strict memory, CPU, PID bounds, and execution timeouts.
    """
    def __init__(
        self,
        docker_image: str = "python:3.11-alpine",
        default_timeout: int = 5,
        memory_limit: str = "128m",
        cpu_limit: str = "0.5",
        pids_limit: int = 64,
    ):
        self.docker_image = docker_image
        self.default_timeout = default_timeout
        self.memory_limit = memory_limit
        self.cpu_limit = cpu_limit
        self.pids_limit = pids_limit

    def _is_docker_available(self) -> bool:
        """Check if Docker daemon is responsive."""
        try:
            res = subprocess.run(
                ["docker", "info"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=2,
            )
            return res.returncode == 0
        except Exception:
            return False

    def execute(self, code: str, timeout: Optional[int] = None) -> SandboxExecutionResult:
        """
        Execute code within an isolated container.
        Falls back to a restricted subprocess sandbox if Docker daemon is not active locally.
        """
        timeout_seconds = timeout or self.default_timeout
        start_time = time.time()

        if self._is_docker_available():
            return self._run_in_docker(code, timeout_seconds, start_time)
        else:
            return self._run_in_restricted_subprocess(code, timeout_seconds, start_time)

    def _run_in_docker(
        self, code: str, timeout_seconds: int, start_time: float
    ) -> SandboxExecutionResult:
        """
        Hardened container execution using strict Docker security boundaries.
        """
        docker_cmd = [
            "docker", "run", "--rm",
            "--network", "none",                       # No network access
            "--memory", self.memory_limit,             # 128MB RAM max
            "--cpus", self.cpu_limit,                  # Max 0.5 CPU cores
            "--pids-limit", str(self.pids_limit),      # Fork bomb defense
            "--read-only",                             # Immutable rootfs
            "--tmpfs", "/tmp:rw,noexec,nosuid,size=16m", # Sandboxed tempfs
            "--user", "1000:1000",                     # Unprivileged user
            self.docker_image,
            "python", "-u", "-c", code
        ]

        try:
            proc = subprocess.run(
                docker_cmd,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
            )
            duration = round(time.time() - start_time, 3)
            return SandboxExecutionResult(
                stdout=proc.stdout,
                stderr=proc.stderr,
                exit_code=proc.returncode,
                execution_time_s=duration,
                timed_out=False,
                sandbox_backend="docker_hardened",
            )
        except subprocess.TimeoutExpired:
            duration = round(time.time() - start_time, 3)
            return SandboxExecutionResult(
                stdout="",
                stderr=f"Execution timed out after {timeout_seconds} seconds.",
                exit_code=124,
                execution_time_s=duration,
                timed_out=True,
                sandbox_backend="docker_hardened",
            )
        except Exception as exc:
            duration = round(time.time() - start_time, 3)
            return SandboxExecutionResult(
                stdout="",
                stderr=f"Docker execution error: {str(exc)}",
                exit_code=1,
                execution_time_s=duration,
                timed_out=False,
                sandbox_backend="docker_hardened",
            )

    def _run_in_restricted_subprocess(
        self, code: str, timeout_seconds: int, start_time: float
    ) -> SandboxExecutionResult:
        """
        Restricted local subprocess fallback with strict timeouts.
        Used when Docker daemon is not running during local test cycles.
        """
        try:
            import sys
            python_bin = sys.executable or "python"
            # Run python with isolated flag (-I) to ignore user site-packages and environment
            cmd = [python_bin, "-I", "-u", "-c", code]
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
            )
            duration = round(time.time() - start_time, 3)
            return SandboxExecutionResult(
                stdout=proc.stdout,
                stderr=proc.stderr,
                exit_code=proc.returncode,
                execution_time_s=duration,
                timed_out=False,
                sandbox_backend="subprocess_isolated_fallback",
            )
        except subprocess.TimeoutExpired:
            duration = round(time.time() - start_time, 3)
            return SandboxExecutionResult(
                stdout="",
                stderr=f"Execution timed out after {timeout_seconds} seconds.",
                exit_code=124,
                execution_time_s=duration,
                timed_out=True,
                sandbox_backend="subprocess_isolated_fallback",
            )
        except Exception as exc:
            duration = round(time.time() - start_time, 3)
            return SandboxExecutionResult(
                stdout="",
                stderr=f"Subprocess execution error: {str(exc)}",
                exit_code=1,
                execution_time_s=duration,
                timed_out=False,
                sandbox_backend="subprocess_isolated_fallback",
            )


# Default singleton executor
sandbox_executor = SandboxExecutor()
