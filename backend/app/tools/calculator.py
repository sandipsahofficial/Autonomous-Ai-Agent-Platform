import ast
import operator
from typing import Union
from pydantic import BaseModel, Field
from app.tools.base import BaseTool, ToolResult


class CalculatorInput(BaseModel):
    expression: str = Field(..., min_length=1, max_length=500, description="Mathematical expression to compute, e.g. '(15 * 4) / 3'")


class CalculatorOutput(BaseModel):
    result: Union[int, float]
    expression: str


# Safe operators mapping
SAFE_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}


def safe_eval_ast(node: ast.AST) -> Union[int, float]:
    """
    Safely evaluate mathematical expressions using AST walking with zero eval/exec.
    Strictly forbids variables, function calls, attribute access, and unsafe operations.
    """
    if isinstance(node, ast.Expression):
        return safe_eval_ast(node.body)

    elif isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)):
            return node.value
        raise ValueError(f"Unsupported constant type: {type(node.value).__name__}")

    elif isinstance(node, ast.BinOp):
        op_type = type(node.op)
        if op_type not in SAFE_OPERATORS:
            raise ValueError(f"Unsupported binary operator: {op_type.__name__}")

        left = safe_eval_ast(node.left)
        right = safe_eval_ast(node.right)

        # Defense against catastrophic exponentiation DOS (e.g. 9999**9999)
        if op_type is ast.Pow:
            if right > 1000 or left > 1000000:
                raise ValueError("Exponent or base exceeds safe arithmetic computation limits.")

        if op_type in (ast.Div, ast.FloorDiv, ast.Mod) and right == 0:
            raise ZeroDivisionError("Division by zero in arithmetic expression.")

        return SAFE_OPERATORS[op_type](left, right)

    elif isinstance(node, ast.UnaryOp):
        op_type = type(node.op)
        if op_type not in SAFE_OPERATORS:
            raise ValueError(f"Unsupported unary operator: {op_type.__name__}")
        operand = safe_eval_ast(node.operand)
        return SAFE_OPERATORS[op_type](operand)

    else:
        raise ValueError(f"Unsafe or unsupported syntax node in expression: {type(node).__name__}")


class CalculatorTool(BaseTool):
    """
    High-assurance arithmetic calculation tool.
    Uses AST validation with zero dynamic evaluation or shell access.
    """
    name = "calculator"
    version = "1.1.0"
    description = "Safely evaluates arithmetic expressions (addition, subtraction, multiplication, division, powers)."
    args_schema = CalculatorInput
    output_schema = CalculatorOutput
    required_permissions = ["math:compute"]
    timeout_seconds = 2
    max_output_size_bytes = 4096
    is_enabled = True
    requires_approval = False
    idempotent = True

    def run(self, expression: str) -> ToolResult:
        try:
            # Parse into abstract syntax tree
            parsed = ast.parse(expression.strip(), mode="eval")
            computed = safe_eval_ast(parsed)

            return ToolResult(
                success=True,
                output={
                    "expression": expression,
                    "result": computed,
                },
                metadata={"computed_type": type(computed).__name__},
            )
        except ZeroDivisionError as zde:
            return ToolResult(success=False, output=None, error=f"Arithmetic error: {str(zde)}")
        except Exception as exc:
            return ToolResult(
                success=False,
                output=None,
                error=f"Calculation failed: {str(exc)}",
            )
