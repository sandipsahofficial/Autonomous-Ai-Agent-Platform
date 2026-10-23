import json
import re
import time
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from app.models.template import Template
from app.models.agent import CustomAgent
from app.models.workflow import Workflow
from app.schemas.workflow import WorkflowCreate, WorkflowDefinition
from app.services.agent_service import AgentService
from app.services.workflow_service import WorkflowService
from app.tools.registry import default_tool_registry

BUILTIN_TEMPLATES = [
    {
        "name": "Research and Report Agent",
        "slug": "research-report-agent",
        "template_type": "agent",
        "category": "research",
        "version": "1.0.0",
        "description": "Synthesizes multi-source factual dossiers with citations using web search and document inspection.",
        "tags": ["research", "fact-checking", "citations"],
        "content": {
            "role": "researcher",
            "permitted_tools": ["web_search", "doc_inspector", "text_summarizer"],
            "model_provider": "ollama",
            "model_name": "llama3",
            "temperature": 0.3,
            "max_steps": 10,
            "review_policy": "standard",
            "system_prompt": "You are a Research and Reporting Specialist. Extract verified findings, cite document pages/URLs, and provide objective executive summaries.",
        },
    },
    {
        "name": "Code Review Sentinel",
        "slug": "code-review-agent",
        "template_type": "agent",
        "category": "engineering",
        "version": "1.0.0",
        "description": "Analyzes code for security vulnerabilities, AST safety violations, edge cases, and algorithmic complexity.",
        "tags": ["code", "security", "ast", "review"],
        "content": {
            "role": "reviewer",
            "permitted_tools": ["json_validator", "doc_inspector"],
            "model_provider": "ollama",
            "model_name": "llama3",
            "temperature": 0.1,
            "max_steps": 8,
            "review_policy": "strict",
            "system_prompt": "You are a Senior Security Code Reviewer. Inspect proposed implementations for OWASP Top 10 vulnerabilities, path traversals, resource leaks, and style compliance.",
        },
    },
    {
        "name": "Document Analysis Agent",
        "slug": "document-analysis-agent",
        "template_type": "agent",
        "category": "analysis",
        "version": "1.0.0",
        "description": "Parses complex reports, extract key financial/operational metrics, and verifies table schemas.",
        "tags": ["documents", "analysis", "metrics"],
        "content": {
            "role": "researcher",
            "permitted_tools": ["doc_inspector", "text_summarizer", "calculator"],
            "model_provider": "ollama",
            "model_name": "llama3",
            "temperature": 0.2,
            "max_steps": 10,
            "review_policy": "standard",
            "system_prompt": "You are a Document Intelligence Analyst. Parse ingested document passages, extract numeric figures, and verify calculations using the safe calculator tool.",
        },
    },
    {
        "name": "Data Validation Workflow",
        "slug": "data-validation-workflow",
        "template_type": "workflow",
        "category": "data",
        "version": "1.0.0",
        "description": "Sequential workflow ingesting raw JSON, validating schemas, computing checks, and formatting clean data.",
        "tags": ["workflow", "validation", "json", "ast"],
        "content": {
            "nodes": [
                {"id": "node-start", "type": "start", "label": "Start Data Pipeline", "x": 50, "y": 100, "config": {}},
                {"id": "node-validator", "type": "tool", "label": "JSON Schema Check", "x": 220, "y": 100, "config": {"tool_name": "json_validator", "arguments": {}}},
                {"id": "node-calc", "type": "tool", "label": "Metric Verification", "x": 400, "y": 100, "config": {"tool_name": "calculator", "arguments": {"expression": "100 * 1.08"}}},
                {"id": "node-end", "type": "end", "label": "Verified Dataset", "x": 580, "y": 100, "config": {}},
            ],
            "edges": [
                {"id": "e1", "source": "node-start", "target": "node-validator"},
                {"id": "e2", "source": "node-validator", "target": "node-calc"},
                {"id": "e3", "source": "node-calc", "target": "node-end"},
            ],
        },
    },
    {
        "name": "College Management Assistant",
        "slug": "college-management-assistant",
        "template_type": "agent",
        "category": "education",
        "version": "1.0.0",
        "description": "Assists students and faculty with academic schedules, syllabus navigation, and administrative guidelines.",
        "tags": ["education", "campus", "faq"],
        "content": {
            "role": "custom",
            "permitted_tools": ["doc_inspector", "text_summarizer"],
            "model_provider": "ollama",
            "model_name": "llama3",
            "temperature": 0.4,
            "max_steps": 8,
            "review_policy": "standard",
            "system_prompt": "You are the Campus Academic & Administrative Advisor for Sandip Sah College Platform. Answer course catalog questions, summarize exam rules, and direct students to official policies.",
        },
    },
    {
        "name": "Multi-Agent Research & Verification Workflow",
        "slug": "multi-agent-research-workflow",
        "template_type": "workflow",
        "category": "research",
        "version": "1.0.0",
        "description": "Full multi-agent DAG: Research Scout gathers data, Risk Gate evaluates policy, and Reviewer finalizes.",
        "tags": ["multi-agent", "dag", "workflow", "safety"],
        "content": {
            "nodes": [
                {"id": "n-start", "type": "start", "label": "Mission Blueprint", "x": 60, "y": 120, "config": {}},
                {"id": "n-scout", "type": "agent", "label": "Research Scout", "x": 240, "y": 120, "config": {"role": "researcher"}},
                {"id": "n-tool", "type": "tool", "label": "Document Verification", "x": 420, "y": 120, "config": {"tool_name": "doc_inspector", "arguments": {"relative_path": "."}}},
                {"id": "n-review", "type": "review", "label": "Reviewer Quality Gate", "x": 600, "y": 120, "config": {"max_rework": 3}},
                {"id": "n-end", "type": "end", "label": "Published Deliverable", "x": 780, "y": 120, "config": {}},
            ],
            "edges": [
                {"id": "e1", "source": "n-start", "target": "n-scout"},
                {"id": "e2", "source": "n-scout", "target": "n-tool"},
                {"id": "e3", "source": "n-tool", "target": "n-review"},
                {"id": "e4", "source": "n-review", "target": "n-end"},
            ],
        },
    },
]


class TemplateService:
    @staticmethod
    def seed_builtin_templates(db: Session) -> None:
        """
        Seeds standard built-in templates into the database if not present.
        """
        for defn in BUILTIN_TEMPLATES:
            existing = db.query(Template).filter(Template.slug == defn["slug"]).first()
            if not existing:
                t = Template(
                    name=defn["name"],
                    slug=defn["slug"],
                    template_type=defn["template_type"],
                    category=defn["category"],
                    version=defn["version"],
                    description=defn["description"],
                    tags=defn["tags"],
                    content=defn["content"],
                    is_builtin=True,
                    author="MESH Engineering",
                )
                db.add(t)
        db.commit()

    @staticmethod
    def list_templates(
        db: Session,
        category: Optional[str] = None,
        template_type: Optional[str] = None,
        search: Optional[str] = None,
    ) -> List[Template]:
        TemplateService.seed_builtin_templates(db)
        query = db.query(Template)
        if category:
            query = query.filter(Template.category == category)
        if template_type:
            query = query.filter(Template.template_type == template_type)
        if search:
            kw = f"%{search}%"
            query = query.filter(Template.name.ilike(kw) | Template.description.ilike(kw))
        return query.order_by(Template.is_builtin.desc(), Template.created_at.desc()).all()

    @staticmethod
    def get_template(db: Session, template_id: str) -> Optional[Template]:
        return db.query(Template).filter(Template.id == template_id).first()

    @staticmethod
    def clone_template(
        db: Session,
        template_id: str,
        user_id: str,
        workspace_id: str,
        custom_name: Optional[str] = None,
    ) -> Tuple[bool, str, Optional[str], Optional[str]]:
        """
        Clones a template into user workspace as a new active Agent or Workflow.
        """
        template = TemplateService.get_template(db, template_id)
        if not template:
            return False, "Template not found", None, None

        name = custom_name or f"{template.name} (from template)"

        if template.template_type == "agent":
            cfg = template.content or {}
            agent, err = AgentService.create_agent(
                db=db,
                user_id=user_id,
                workspace_id=workspace_id,
                name=name,
                system_prompt=cfg.get("system_prompt", "Autonomous agent instructions."),
                role=cfg.get("role", "custom"),
                description=template.description,
                permitted_tools=cfg.get("permitted_tools", []),
                model_provider=cfg.get("model_provider", "ollama"),
                model_name=cfg.get("model_name", "llama3"),
                temperature=cfg.get("temperature", 0.7),
                max_steps=cfg.get("max_steps", 10),
                review_policy=cfg.get("review_policy", "standard"),
            )
            if err or not agent:
                return False, err or "Failed to clone agent template", None, None
            return True, f"Agent '{agent.name}' created successfully.", agent.id, "agent"

        elif template.template_type == "workflow":
            wf_payload = WorkflowCreate(
                name=name,
                description=template.description,
                definition=WorkflowDefinition(**(template.content or {})),
                is_enabled=True,
            )
            wf, val_err = WorkflowService.create_workflow(db, user_id, workspace_id, wf_payload)
            if val_err or not wf:
                msg = val_err.errors[0].message if val_err and val_err.errors else "Failed to clone workflow template"
                return False, msg, None, None
            return True, f"Workflow '{wf.name}' created successfully.", wf.id, "workflow"

        return False, "Unsupported template type", None, None

    @staticmethod
    def export_template_json(db: Session, template_id: str) -> Tuple[Optional[str], Optional[str]]:
        template = TemplateService.get_template(db, template_id)
        if not template:
            return None, "Template not found"

        export_dict = {
            "schema_version": "mesh.template.v1",
            "name": template.name,
            "slug": template.slug,
            "template_type": template.template_type,
            "category": template.category,
            "version": template.version,
            "description": template.description,
            "tags": template.tags,
            "content": template.content,
        }
        return json.dumps(export_dict, indent=2), None

    @staticmethod
    def import_template_json(db: Session, json_str: str) -> Tuple[Optional[Template], Optional[str]]:
        """
        Untrusted input security boundary:
        Validates structure, enforces schema version, rejects executable code strings,
        and verifies that all referenced tools exist in registry.
        """
        try:
            data = json.loads(json_str)
        except Exception as exc:
            return None, f"Invalid JSON format: {str(exc)}"

        if data.get("schema_version") != "mesh.template.v1":
            return None, "Unsupported template schema version. Expected 'mesh.template.v1'."

        # Security check: disallow executable code injection patterns
        raw_text = json_str.lower()
        prohibited = ["__import__", "exec(", "eval(", "os.system", "subprocess", "shutil.rmtree"]
        for p in prohibited:
            if p in raw_text:
                return None, f"Security violation: Template contains prohibited pattern '{p}'"

        # Validate tools in content
        content = data.get("content", {})
        if data.get("template_type") == "agent":
            tools = content.get("permitted_tools", [])
            _, err = AgentService.validate_permitted_tools(tools)
            if err:
                return None, f"Template contains unauthorized tools: {err}"

        slug = data.get("slug") or f"custom-imported-{int(time.time())}"
        # Ensure unique slug
        base_slug = slug
        idx = 1
        while db.query(Template).filter(Template.slug == slug).first() is not None:
            slug = f"{base_slug}-{idx}"
            idx += 1

        template = Template(
            name=data.get("name", "Imported Template"),
            slug=slug,
            template_type=data.get("template_type", "workflow"),
            category=data.get("category", "imported"),
            version=data.get("version", "1.0.0"),
            description=data.get("description", "Imported custom template"),
            tags=data.get("tags", ["imported"]),
            content=content,
            is_builtin=False,
            author="Imported",
        )
        db.add(template)
        db.commit()
        db.refresh(template)
        return template, None
