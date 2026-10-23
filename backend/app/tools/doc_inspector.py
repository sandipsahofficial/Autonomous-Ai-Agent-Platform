import os
from pathlib import Path
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from app.tools.base import BaseTool, ToolResult


class DocInspectorInput(BaseModel):
    relative_path: str = Field(
        default=".",
        description="Relative path to a file or directory within the permitted documentation/workspace boundary",
    )
    max_bytes: int = Field(
        default=16384,
        ge=512,
        le=32768,
        description="Maximum file bytes to read to prevent buffer exhaustion",
    )


class DocInspectorOutput(BaseModel):
    path: str
    is_directory: bool
    size_bytes: int
    content: Optional[str] = None
    entries: Optional[List[Dict[str, Any]]] = None


class DocumentInspectorTool(BaseTool):
    """
    Read-only document and directory inspection tool.
    Strictly restricted to explicitly permitted directories with hardened path traversal defense.
    """
    name = "doc_inspector"
    version = "1.1.0"
    description = "Safely inspects permitted workspace documents and directories with strict path boundary enforcement."
    args_schema = DocInspectorInput
    output_schema = DocInspectorOutput
    required_permissions = ["doc:read"]
    timeout_seconds = 4
    max_output_size_bytes = 32768
    is_enabled = True
    requires_approval = False
    idempotent = True

    def __init__(self, permitted_root: Optional[str] = None):
        if permitted_root:
            self.permitted_root = os.path.realpath(permitted_root)
        else:
            # Default to workspace directory under project root
            base_dir = Path(__file__).resolve().parents[2] / "workspace"
            os.makedirs(base_dir, exist_ok=True)
            self.permitted_root = os.path.realpath(str(base_dir))

    def _resolve_and_verify(self, user_path: str) -> str:
        """
        Hardened path resolution.
        Canonicalizes path and enforces that destination is strictly within permitted root.
        """
        # Strip leading slashes to prevent root-relative escapes
        cleaned = user_path.strip().lstrip("/\\")
        candidate = os.path.realpath(os.path.join(self.permitted_root, cleaned))

        # Check path containment
        common = os.path.commonpath([candidate, self.permitted_root])
        if common != self.permitted_root:
            raise PermissionError(f"Security Alert: Path traversal outside permitted root is prohibited ({user_path}).")

        return candidate

    def run(self, relative_path: str = ".", max_bytes: int = 16384) -> ToolResult:
        try:
            target_path = self._resolve_and_verify(relative_path)

            if not os.path.exists(target_path):
                return ToolResult(
                    success=False,
                    output=None,
                    error=f"Target path does not exist: {relative_path}",
                )

            if os.path.isdir(target_path):
                items = []
                for entry in os.scandir(target_path):
                    stat = entry.stat()
                    items.append({
                        "name": entry.name,
                        "is_dir": entry.is_dir(),
                        "size_bytes": stat.st_size if entry.is_file() else 0,
                    })
                    if len(items) >= 50:
                        break

                return ToolResult(
                    success=True,
                    output={
                        "path": relative_path,
                        "is_directory": True,
                        "size_bytes": 0,
                        "entries": items,
                        "content": None,
                    },
                    metadata={"item_count": len(items)},
                )

            elif os.path.isfile(target_path):
                size = os.path.getsize(target_path)
                with open(target_path, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read(max_bytes)

                truncated = size > max_bytes
                return ToolResult(
                    success=True,
                    output={
                        "path": relative_path,
                        "is_directory": False,
                        "size_bytes": size,
                        "content": content,
                        "entries": None,
                    },
                    metadata={"truncated": truncated, "bytes_read": len(content)},
                )
            else:
                return ToolResult(
                    success=False,
                    output=None,
                    error="Target is not a regular file or directory.",
                )

        except PermissionError as pe:
            return ToolResult(success=False, output=None, error=str(pe))
        except Exception as exc:
            return ToolResult(success=False, output=None, error=f"Inspection failed: {str(exc)}")
