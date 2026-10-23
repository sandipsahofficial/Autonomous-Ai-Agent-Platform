from typing import List, Optional, Literal, Any
from pydantic import BaseModel, Field


class SubtaskPlanItem(BaseModel):
    order_index: int = Field(..., ge=0, description="Sequential execution order")
    title: str = Field(..., min_length=2, description="Short subtask title")
    description: str = Field(..., min_length=5, description="Specific instructions for worker")
    assigned_agent: Literal["researcher", "executor", "coder"] = Field(
        ..., description="Designated specialist agent"
    )
    dependencies: List[int] = Field(
        default_factory=list, description="Order indices of prerequisites that must complete first"
    )


class PlannerOutput(BaseModel):
    plan_summary: str = Field(..., description="High-level strategy summary")
    subtasks: List[SubtaskPlanItem] = Field(..., min_length=1, description="List of discrete subtasks")


class ResearcherOutput(BaseModel):
    summary: str = Field(..., description="Synthesis of research findings")
    key_findings: List[str] = Field(default_factory=list, description="Bullet points of verified facts")
    recommended_action: str = Field(..., description="Next steps for executor or reviewer")


class ExecutorOutput(BaseModel):
    action_summary: str = Field(..., description="Summary of executed operations and calculations")
    details: str = Field(..., description="Detailed execution verification and observations")
    output_data: Optional[Any] = Field(None, description="Structured output payload or computation result")
    code: Optional[str] = Field(None, description="Optional executable code if applicable")


class CoderOutput(BaseModel):
    language: str = Field(default="python", description="Programming language")
    code: str = Field(..., description="Generated executable source code")
    explanation: str = Field(..., description="How the code works and handles edge cases")
    filename: Optional[str] = Field(None, description="Optional relative target file path in workspace")


class ReviewerOutput(BaseModel):
    status: Literal["APPROVED", "REWORK_NEEDED"] = Field(
        ..., description="Review outcome: approved or needs rework"
    )
    quality_score: int = Field(..., ge=0, le=100, description="Quality rating from 0 to 100")
    comments: str = Field(..., description="Specific feedback on correctness and completeness")
    rework_instructions: Optional[str] = Field(
        None, description="Actionable correction instructions if status is REWORK_NEEDED"
    )


class FinalizerOutput(BaseModel):
    executive_summary: str = Field(..., description="Unified synthesis of mission achievement")
    deliverables: str = Field(..., description="Final structured outputs, results, and artifacts")
    learnings_and_strategy: str = Field(
        ..., description="Valuable strategy insight or reusable pattern to record in persistent memory"
    )
    confidence_score: int = Field(..., ge=0, le=100, description="Final mission quality confidence (0-100)")
