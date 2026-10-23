import re
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from app.models.agent import CustomAgent
from app.models.workflow import Workflow
from app.models.task import Subtask, ExecutionEvent, TaskStatus
from app.tools.registry import default_tool_registry


def slugify(text: str) -> str:
    cleaned = re.sub(r"[^\w\s-]", "", text.lower()).strip()
    return re.sub(r"[-\s]+", "-", cleaned)


class AgentService:
    @staticmethod
    def validate_permitted_tools(tools: List[str]) -> Tuple[List[str], Optional[str]]:
        """
        Backend security gate: verifies that all requested tools exist in the tool registry.
        Rejects any unrecognized or disabled tools to prevent privilege escalation.
        """
        all_schemas = {t["name"]: t for t in default_tool_registry.list_all_tools()}
        validated = []
        for t in tools:
            if t not in all_schemas:
                return [], f"Tool '{t}' does not exist in the security tool registry."
            tool_meta = all_schemas[t]
            validated.append(t)
        return validated, None

    @staticmethod
    def seed_default_agents(db: Session, user_id: str = "sandip_sah", workspace_id: str = "default_workspace") -> None:
        """
        Seeds standard built-in system agent personas if they are not already registered.
        """
        system_agents = [
            {
                "name": "Planner Agent",
                "slug": "planner",
                "role": "planner",
                "description": "Decomposes complex objectives into discrete, dependency-aware subtasks.",
                "permitted_tools": ["doc_inspector", "calculator"],
                "model_provider": "ollama",
                "model_name": "llama3",
                "temperature": 0.2,
                "max_steps": 15,
                "system_prompt": "You are the Planner Agent. Analyze mission goals and produce discrete, verifiable subtasks with explicit dependencies.",
                "review_policy": "standard",
                "is_system": True,
            },
            {
                "name": "Research Scout",
                "slug": "researcher",
                "role": "researcher",
                "description": "Gathers facts, technical specifications, and citations using approved search and document tools.",
                "permitted_tools": ["web_search", "doc_inspector", "text_summarizer"],
                "model_provider": "ollama",
                "model_name": "llama3",
                "temperature": 0.3,
                "max_steps": 10,
                "system_prompt": "You are the Researcher Agent. Synthesize verified facts, documentation, and references for the assigned subtask.",
                "review_policy": "standard",
                "is_system": True,
            },
            {
                "name": "Executor Sentinel",
                "slug": "executor",
                "role": "executor",
                "description": "Performs computations, data parsing, and sandbox executions with strict security controls.",
                "permitted_tools": ["calculator", "json_validator", "doc_inspector", "execute_code_sandbox"],
                "model_provider": "ollama",
                "model_name": "llama3",
                "temperature": 0.2,
                "max_steps": 12,
                "system_prompt": "You are the Executor Agent. Perform calculations, code synthesis, data verification, and operation execution.",
                "review_policy": "strict",
                "is_system": True,
            },
            {
                "name": "Reviewer Guard",
                "slug": "reviewer",
                "role": "reviewer",
                "description": "Evaluates intermediate outputs against requirements and bounds rework cycles.",
                "permitted_tools": ["json_validator"],
                "model_provider": "ollama",
                "model_name": "llama3",
                "temperature": 0.1,
                "max_steps": 5,
                "system_prompt": "You are the Reviewer Guard. Rigorously critique intermediate outputs and verify all criteria are met.",
                "review_policy": "strict",
                "is_system": True,
            },
        ]

        for defn in system_agents:
            existing = db.query(CustomAgent).filter(
                CustomAgent.slug == defn["slug"],
                CustomAgent.user_id == user_id,
            ).first()
            if not existing:
                agent = CustomAgent(
                    user_id=user_id,
                    workspace_id=workspace_id,
                    name=defn["name"],
                    slug=defn["slug"],
                    role=defn["role"],
                    description=defn["description"],
                    permitted_tools=defn["permitted_tools"],
                    model_provider=defn["model_provider"],
                    model_name=defn["model_name"],
                    temperature=defn["temperature"],
                    max_steps=defn["max_steps"],
                    system_prompt=defn["system_prompt"],
                    review_policy=defn["review_policy"],
                    is_system=True,
                    is_enabled=True,
                )
                db.add(agent)
        db.commit()

    @staticmethod
    def create_agent(
        db: Session,
        user_id: str,
        workspace_id: str,
        name: str,
        system_prompt: str,
        role: str = "custom",
        description: Optional[str] = None,
        permitted_tools: Optional[List[str]] = None,
        model_provider: str = "ollama",
        model_name: str = "llama3",
        temperature: float = 0.7,
        max_steps: int = 10,
        review_policy: str = "standard",
        is_enabled: bool = True,
    ) -> Tuple[Optional[CustomAgent], Optional[str]]:
        tools = permitted_tools or []
        valid_tools, err = AgentService.validate_permitted_tools(tools)
        if err:
            return None, err

        slug_candidate = slugify(name)
        # Ensure unique slug for user
        base_slug = slug_candidate
        idx = 1
        while db.query(CustomAgent).filter(
            CustomAgent.slug == slug_candidate,
            CustomAgent.user_id == user_id,
        ).first() is not None:
            slug_candidate = f"{base_slug}-{idx}"
            idx += 1

        agent = CustomAgent(
            user_id=user_id,
            workspace_id=workspace_id,
            name=name,
            slug=slug_candidate,
            role=role,
            description=description,
            permitted_tools=valid_tools,
            model_provider=model_provider,
            model_name=model_name,
            temperature=temperature,
            max_steps=max_steps,
            system_prompt=system_prompt,
            review_policy=review_policy,
            is_enabled=is_enabled,
            is_system=False,
        )
        db.add(agent)
        db.commit()
        db.refresh(agent)
        return agent, None

    @staticmethod
    def list_agents(db: Session, user_id: str, workspace_id: Optional[str] = None) -> List[CustomAgent]:
        AgentService.seed_default_agents(db, user_id)
        query = db.query(CustomAgent).filter(CustomAgent.user_id == user_id)
        if workspace_id:
            query = query.filter(CustomAgent.workspace_id == workspace_id)
        return query.order_by(CustomAgent.is_system.desc(), CustomAgent.created_at.desc()).all()

    @staticmethod
    def get_agent(db: Session, agent_id: str, user_id: str) -> Optional[CustomAgent]:
        return db.query(CustomAgent).filter(
            CustomAgent.id == agent_id,
            CustomAgent.user_id == user_id,
        ).first()

    @staticmethod
    def duplicate_agent(db: Session, agent_id: str, user_id: str) -> Tuple[Optional[CustomAgent], Optional[str]]:
        original = AgentService.get_agent(db, agent_id, user_id)
        if not original:
            return None, "Original agent not found"

        dup_name = f"{original.name} (Copy)"
        return AgentService.create_agent(
            db=db,
            user_id=user_id,
            workspace_id=original.workspace_id,
            name=dup_name,
            system_prompt=original.system_prompt,
            role=original.role,
            description=original.description,
            permitted_tools=list(original.permitted_tools),
            model_provider=original.model_provider,
            model_name=original.model_name,
            temperature=original.temperature,
            max_steps=original.max_steps,
            review_policy=original.review_policy,
            is_enabled=original.is_enabled,
        )

    @staticmethod
    def delete_agent(db: Session, agent_id: str, user_id: str) -> Tuple[bool, Optional[str]]:
        agent = AgentService.get_agent(db, agent_id, user_id)
        if not agent:
            return False, "Agent not found"
        if agent.is_system:
            return False, "System agents cannot be deleted."

        # Check workflow dependencies
        workflows = db.query(Workflow).filter(Workflow.user_id == user_id).all()
        for wf in workflows:
            definition = wf.definition or {}
            nodes = definition.get("nodes", [])
            for node in nodes:
                if node.get("type") == "agent":
                    cfg = node.get("config", {})
                    if cfg.get("agent_id") == agent.id or cfg.get("agent_slug") == agent.slug:
                        return False, f"Cannot delete agent: Referenced in workflow '{wf.name}' (Node: {node.get('label')})."

        db.delete(agent)
        db.commit()
        return True, None
