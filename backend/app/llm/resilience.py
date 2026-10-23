import time
import random
import logging
from typing import Optional, Type
from pydantic import BaseModel
from app.llm.base import (
    BaseLLMProvider,
    LLMResponse,
    LLMAuthenticationError,
    LLMTimeoutError,
    LLMRateLimitError,
    LLMProviderError,
)
from app.services.trace_service import record_execution_event

logger = logging.getLogger(__name__)


def generate_with_resilience(
    provider: BaseLLMProvider,
    prompt: str,
    system_prompt: Optional[str] = None,
    response_schema: Optional[Type[BaseModel]] = None,
    max_retries: int = 3,
    base_delay: float = 0.5,
    max_delay: float = 6.0,
    task_id: Optional[str] = None,
    step_index: int = 0,
    agent_name: str = "orchestrator",
) -> LLMResponse:
    """
    Executes model generation with bounded exponential backoff, jitter,
    schema validation recovery, and structured execution event auditing.
    Never retries authentication failures blindly.
    """
    attempt = 0
    current_prompt = prompt
    last_error: Optional[Exception] = None

    while attempt <= max_retries:
        try:
            response = provider.generate(
                prompt=current_prompt,
                system_prompt=system_prompt,
                response_schema=response_schema,
            )

            # If a structured schema was requested, verify that structured output was successfully parsed
            if response_schema and response.structured is None:
                raise ValueError("Model output failed structured schema validation (invalid or missing JSON).")

            return response

        except LLMAuthenticationError:
            # Authentication / credential errors must fail fast and never be retried
            logger.error("LLM authentication failure - aborting without retry.")
            raise

        except (LLMTimeoutError, LLMRateLimitError, LLMProviderError, ValueError) as exc:
            last_error = exc
            attempt += 1

            if attempt > max_retries:
                logger.error(f"Exhausted {max_retries} retries for agent '{agent_name}'. Last error: {exc}")
                break

            # Calculate bounded exponential backoff with jitter
            backoff = min(max_delay, base_delay * (2 ** (attempt - 1)))
            jitter = random.uniform(0.05, 0.3)
            delay = round(backoff + jitter, 3)

            logger.warning(
                f"Agent '{agent_name}' retry {attempt}/{max_retries} after {delay}s due to: {str(exc)}"
            )

            # Record retry event in execution traces
            if task_id and task_id != "unknown":
                record_execution_event(
                    task_id=task_id,
                    event_type="RETRY_ATTEMPTED",
                    message=f"Attempt {attempt}/{max_retries} for agent @{agent_name} after error: {str(exc)}",
                    agent_name=agent_name,
                    step_index=step_index,
                    status="RETRY",
                    details={
                        "attempt": attempt,
                        "max_retries": max_retries,
                        "backoff_seconds": delay,
                        "error_type": type(exc).__name__,
                        "error_message": str(exc),
                    },
                )

            # If error was a schema validation failure, guide model in the prompt
            if isinstance(exc, ValueError):
                current_prompt = (
                    f"{prompt}\n\n"
                    f"[CORRECTION NOTICE: Previous generation failed schema validation: {str(exc)}. "
                    f"Please output strictly valid, well-formed JSON conforming exactly to the required schema.]"
                )

            time.sleep(delay)

    raise LLMProviderError(
        f"Operation failed after {max_retries} attempts: {str(last_error)}"
    ) from last_error
