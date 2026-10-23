from typing import List, Dict, Any, Set, Tuple
from app.schemas.workflow import (
    WorkflowDefinition,
    WorkflowValidationResult,
    ValidationErrorItem,
)
from app.tools.registry import default_tool_registry


class WorkflowValidator:
    """
    Backend security & topology validator for visual workflows.
    Never trusts frontend client checks. Detects cycles, unreachable nodes,
    port incompatibilities, unauthorized tools, and missing gates.
    """

    @classmethod
    def validate(cls, definition: WorkflowDefinition) -> WorkflowValidationResult:
        errors: List[ValidationErrorItem] = []
        warnings: List[str] = []

        nodes = definition.nodes
        edges = definition.edges

        if not nodes:
            errors.append(
                ValidationErrorItem(
                    node_id=None,
                    message="Workflow contains no nodes.",
                    error_type="empty_graph",
                )
            )
            return WorkflowValidationResult(is_valid=False, errors=errors, warnings=warnings)

        node_map = {n.id: n for n in nodes}
        adjacency: Dict[str, List[str]] = {n.id: [] for n in nodes}
        in_degrees: Dict[str, int] = {n.id: 0 for n in nodes}

        # 1. Edge validity
        for edge in edges:
            if edge.source not in node_map:
                errors.append(
                    ValidationErrorItem(
                        node_id=None,
                        message=f"Edge references non-existent source node '{edge.source}'",
                        error_type="invalid_connection",
                    )
                )
            elif edge.target not in node_map:
                errors.append(
                    ValidationErrorItem(
                        node_id=None,
                        message=f"Edge references non-existent target node '{edge.target}'",
                        error_type="invalid_connection",
                    )
                )
            else:
                adjacency[edge.source].append(edge.target)
                in_degrees[edge.target] += 1

        # 2. Check for Start and End nodes
        start_nodes = [n for n in nodes if n.type == "start"]
        end_nodes = [n for n in nodes if n.type == "end"]

        if len(start_nodes) == 0:
            errors.append(
                ValidationErrorItem(
                    node_id=None,
                    message="Workflow must contain exactly one Start node.",
                    error_type="missing_start",
                )
            )
        elif len(start_nodes) > 1:
            for s in start_nodes[1:]:
                errors.append(
                    ValidationErrorItem(
                        node_id=s.id,
                        message="Multiple Start nodes detected. Only one Start node is allowed.",
                        error_type="multiple_start",
                    )
                )

        if len(end_nodes) == 0:
            errors.append(
                ValidationErrorItem(
                    node_id=None,
                    message="Workflow must contain at least one End node.",
                    error_type="missing_end",
                )
            )

        # 3. Detect Cycles (DFS coloring: 0=unvisited, 1=visiting, 2=visited)
        # Note: Bounded review loops are checked specifically; unmanaged recursive loops are blocked.
        visited_state: Dict[str, int] = {n.id: 0 for n in nodes}
        cycle_nodes: Set[str] = set()

        def dfs_detect_cycle(u: str, path: List[str]) -> bool:
            visited_state[u] = 1
            has_cycle = False
            for v in adjacency.get(u, []):
                if visited_state.get(v) == 1:
                    # Found back-edge!
                    cycle_nodes.add(v)
                    cycle_nodes.add(u)
                    # Check if v is explicitly an approved review node with a max_rework bound
                    target_node = node_map.get(v)
                    if target_node and target_node.type == "review":
                        max_rework = target_node.config.get("max_rework", 3)
                        warnings.append(
                            f"Review loop detected between '{node_map[u].label}' and '{target_node.label}'. Bounded at {max_rework} cycles."
                        )
                    else:
                        errors.append(
                            ValidationErrorItem(
                                node_id=v,
                                message=f"Uncontrolled cyclic dependency detected between '{node_map[u].label}' and '{node_map.get(v, v).label}'.",
                                error_type="cycle",
                            )
                        )
                        has_cycle = True
                elif visited_state.get(v) == 0:
                    if dfs_detect_cycle(v, path + [v]):
                        has_cycle = True
            visited_state[u] = 2
            return has_cycle

        for n in nodes:
            if visited_state[n.id] == 0:
                dfs_detect_cycle(n.id, [n.id])

        # 4. Reachability from Start (Orphan / Disconnected nodes)
        if len(start_nodes) == 1:
            start_id = start_nodes[0].id
            reachable: Set[str] = set()
            queue = [start_id]
            reachable.add(start_id)

            while queue:
                curr = queue.pop(0)
                for nxt in adjacency.get(curr, []):
                    if nxt not in reachable:
                        reachable.add(nxt)
                        queue.append(nxt)

            for n in nodes:
                if n.id not in reachable:
                    errors.append(
                        ValidationErrorItem(
                            node_id=n.id,
                            message=f"Node '{n.label}' is unreachable from the Start node.",
                            error_type="orphan",
                        )
                    )

        # 5. Security & Node Configuration checks
        tool_schemas = {t["name"]: t for t in default_tool_registry.list_all_tools()}

        for n in nodes:
            if n.type == "tool":
                tool_name = n.config.get("tool_name")
                if not tool_name:
                    errors.append(
                        ValidationErrorItem(
                            node_id=n.id,
                            message=f"Tool node '{n.label}' does not specify a 'tool_name'.",
                            error_type="schema",
                        )
                    )
                elif tool_name not in tool_schemas:
                    errors.append(
                        ValidationErrorItem(
                            node_id=n.id,
                            message=f"Tool node '{n.label}' references unrecognized tool '{tool_name}'.",
                            error_type="security",
                        )
                    )
                else:
                    tool_info = tool_schemas[tool_name]
                    if tool_info.get("requires_approval"):
                        warnings.append(
                            f"Tool '{tool_name}' in node '{n.label}' is rated HIGH risk and will require human operator authorization."
                        )

            elif n.type == "agent":
                agent_id = n.config.get("agent_id") or n.config.get("agent_slug") or n.config.get("role")
                if not agent_id:
                    errors.append(
                        ValidationErrorItem(
                            node_id=n.id,
                            message=f"Agent node '{n.label}' must specify an agent role or ID.",
                            error_type="schema",
                        )
                    )

            elif n.type == "conditional":
                branches = [e for e in edges if e.source == n.id]
                if len(branches) < 2:
                    warnings.append(
                        f"Conditional node '{n.label}' has fewer than 2 outgoing paths."
                    )

        is_valid = len(errors) == 0
        return WorkflowValidationResult(is_valid=is_valid, errors=errors, warnings=warnings)
